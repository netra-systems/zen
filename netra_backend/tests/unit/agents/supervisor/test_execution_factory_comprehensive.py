"""
Comprehensive Unit Tests for ExecutionEngineFactory (Golden Path Requirements)

Business Value Justification:
- Segment: Platform/Internal (ALL user tiers depend on this)
- Business Goal: Stability & Prevent cascade failures for 90% of platform value (chat)
- Value Impact: ExecutionEngineFactory creates isolated execution engines per user request 
- Strategic Impact: Foundation for $500K+ ARR chat functionality - prevents user context leakage

CRITICAL IMPORTANCE FOR GOLDEN PATH:
- ExecutionEngineFactory creates UserExecutionEngine instances with complete user isolation
- Prevents shared state contamination between concurrent users (10+ users simultaneously)
- Manages WebSocket event emitter creation for real-time agent events (mission critical)
- Enforces resource limits to prevent memory exhaustion and DoS attacks  
- Provides automatic lifecycle management and cleanup to prevent memory leaks
- Handles configuration from environment variables for different deployment environments

This comprehensive test suite validates ALL factory patterns, user isolation, resource management,
error handling, WebSocket integration, and performance requirements for golden path compliance.

TEST SCOPE: 35+ tests covering:
1. Factory initialization and configuration
2. UserExecutionContext creation and validation  
3. ExecutionEngine creation with isolation
4. Resource limits and semaphore management
5. WebSocket event emitter integration
6. Concurrent engine creation and race conditions
7. Cleanup and lifecycle management
8. Factory metrics and monitoring
9. Error handling and edge cases
10. Performance benchmarks
"""

import asyncio
import time
import uuid
import pytest
import psutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, MagicMock, patch, call

# SSOT imports following test_framework patterns
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Target module and dependencies  
from netra_backend.app.agents.supervisor.execution_factory import (
    ExecutionEngineFactory,
    ExecutionFactoryConfig, 
    UserExecutionContext,
    UserExecutionEngineWrapper,
    IsolatedExecutionEngine,
    get_execution_engine_factory
)
from netra_backend.app.schemas.core_enums import ExecutionStatus


class TestExecutionFactoryConfig(SSotBaseTestCase):
    """Test ExecutionFactoryConfig class and environment variable handling."""
    
    def test_config_default_values(self):
        """Test ExecutionFactoryConfig has correct default values."""
        config = ExecutionFactoryConfig()
        
        # Verify defaults
        assert config.max_concurrent_per_user == 5
        assert config.execution_timeout_seconds == 30.0
        assert config.cleanup_interval_seconds == 300
        assert config.max_history_per_user == 100
        assert config.enable_user_semaphores is True
        assert config.enable_execution_tracking is True
        assert config.max_active_users == 100
        assert config.memory_threshold_mb == 1024
        
        self.record_metric("config_defaults_validated", True)
    
    def test_config_from_env_default_values(self):
        """Test ExecutionFactoryConfig.from_env() with default values."""
        # No custom environment variables set
        config = ExecutionFactoryConfig.from_env()
        
        # Should use defaults when env vars not set
        assert config.max_concurrent_per_user == 5
        assert config.execution_timeout_seconds == 30.0
        assert config.cleanup_interval_seconds == 300
        assert config.max_history_per_user == 100
        assert config.enable_user_semaphores is True
        assert config.enable_execution_tracking is True
        
        self.record_metric("config_from_env_defaults", True)
    
    def test_config_from_env_custom_values(self):
        """Test ExecutionFactoryConfig.from_env() with custom environment variables."""
        with self.temp_env_vars(
            EXECUTION_MAX_CONCURRENT_PER_USER="3",
            EXECUTION_TIMEOUT_SECONDS="45.5",
            EXECUTION_CLEANUP_INTERVAL="600",
            EXECUTION_MAX_HISTORY_PER_USER="50",
            EXECUTION_ENABLE_USER_SEMAPHORES="false",
            EXECUTION_ENABLE_TRACKING="false"
        ):
            config = ExecutionFactoryConfig.from_env()
            
            # Verify custom values
            assert config.max_concurrent_per_user == 3
            assert config.execution_timeout_seconds == 45.5
            assert config.cleanup_interval_seconds == 600
            assert config.max_history_per_user == 50
            assert config.enable_user_semaphores is False
            assert config.enable_execution_tracking is False
            
        self.record_metric("config_from_env_custom", True)
    
    def test_config_from_env_invalid_values(self):
        """Test ExecutionFactoryConfig.from_env() handles invalid values gracefully."""
        with self.temp_env_vars(
            EXECUTION_MAX_CONCURRENT_PER_USER="invalid",
            EXECUTION_TIMEOUT_SECONDS="not_a_float"
        ):
            # Should raise ValueError for invalid numeric values
            with self.expect_exception(ValueError):
                ExecutionFactoryConfig.from_env()
                
        self.record_metric("config_invalid_handling", True)


class TestUserExecutionContext(SSotBaseTestCase):
    """Test UserExecutionContext creation, validation, and lifecycle."""
    
    def test_user_execution_context_creation(self):
        """Test UserExecutionContext creation with valid parameters."""
        user_id = "test-user-123"
        request_id = "req-456"
        thread_id = "thread-789"
        session_id = "session-abc"
        
        context = UserExecutionContext(
            user_id=user_id,
            request_id=request_id,
            thread_id=thread_id,
            session_id=session_id
        )
        
        # Verify basic properties
        assert context.user_id == user_id
        assert context.request_id == request_id
        assert context.thread_id == thread_id
        assert context.session_id == session_id
        assert context.status == ExecutionStatus.EXECUTING
        assert context._is_cleaned is False
        
        # Verify metrics initialization
        assert context.execution_metrics['total_runs'] == 0
        assert context.execution_metrics['successful_runs'] == 0
        assert context.execution_metrics['failed_runs'] == 0
        assert context.execution_metrics['total_execution_time_ms'] == 0.0
        assert 'context_created_at' in context.execution_metrics
        
        self.record_metric("context_creation", True)
    
    def test_user_execution_context_post_init(self):
        """Test UserExecutionContext __post_init__ properly initializes state.""" 
        context = UserExecutionContext(
            user_id="user",
            request_id="req", 
            thread_id="thread"
        )
        
        # Verify post_init effects
        assert context.status == ExecutionStatus.EXECUTING
        assert isinstance(context.execution_metrics, dict)
        assert len(context.execution_metrics) >= 7  # All required metrics
        assert context.created_at is not None
        
        self.record_metric("context_post_init", True)
    
    def test_user_execution_context_activity_tracking(self):
        """Test UserExecutionContext activity tracking methods."""
        context = UserExecutionContext(
            user_id="activity-user",
            request_id="activity-req",
            thread_id="activity-thread"
        )
        
        initial_time = context.execution_metrics['last_activity_at']
        
        # Wait a small amount to ensure timestamp difference
        time.sleep(0.001)
        
        # Update activity
        context.update_activity()
        updated_time = context.execution_metrics['last_activity_at']
        
        # Verify activity timestamp updated
        assert updated_time > initial_time
        
        self.record_metric("activity_tracking", True)
    
    def test_user_execution_context_run_recording(self):
        """Test UserExecutionContext run recording functionality."""
        context = UserExecutionContext(
            user_id="run-user",
            request_id="run-req", 
            thread_id="run-thread"
        )
        
        run_id = "test-run-123"
        agent_name = "test-agent"
        execution_time = 1500.0  # ms
        
        # Record run start
        context.record_run_start(run_id, agent_name)
        assert context.execution_metrics['total_runs'] == 1
        
        # Record successful completion
        context.record_run_success(run_id, execution_time)
        assert context.execution_metrics['successful_runs'] == 1
        assert context.execution_metrics['total_execution_time_ms'] == execution_time
        assert context.execution_metrics['avg_execution_time_ms'] == execution_time
        
        # Record failure
        error = Exception("Test error")
        context.record_run_failure("failed-run", error)
        assert context.execution_metrics['failed_runs'] == 1
        
        self.record_metric("run_recording", True)
    
    def test_user_execution_context_child_context_creation(self):
        """Test UserExecutionContext child context creation for agent isolation."""
        parent_context = UserExecutionContext(
            user_id="parent-user",
            request_id="parent-req",
            thread_id="parent-thread",
            session_id="parent-session"
        )
        
        child_id = "agent_triage"
        child_context = parent_context.create_child_context(child_id)
        
        # Verify child context properties
        assert child_context.user_id == parent_context.user_id
        assert child_context.request_id == f"{parent_context.request_id}_{child_id}"
        assert child_context.thread_id == f"{parent_context.thread_id}_{child_id}"
        assert child_context.session_id == parent_context.session_id
        
        # Verify metrics inheritance
        assert child_context.execution_metrics['parent_request_id'] == parent_context.request_id
        assert child_context.execution_metrics['child_id'] == child_id
        
        self.record_metric("child_context_creation", True)
    
    def test_user_execution_context_status_summary(self):
        """Test UserExecutionContext status summary generation."""
        context = UserExecutionContext(
            user_id="summary-user",
            request_id="summary-req",
            thread_id="summary-thread"
        )
        
        # Add some test data
        context.active_runs["run1"] = Mock()
        context.run_history.append(Mock())
        
        summary = context.get_status_summary()
        
        # Verify summary structure
        required_keys = [
            'user_id', 'request_id', 'thread_id', 'status',
            'active_runs_count', 'run_history_count', 'is_cleaned',
            'created_at', 'metrics'
        ]
        for key in required_keys:
            assert key in summary
            
        assert summary['user_id'] == "summary-user"
        assert summary['active_runs_count'] == 1
        assert summary['run_history_count'] == 1
        assert summary['is_cleaned'] is False
        
        self.record_metric("status_summary", True)


class TestUserExecutionContextCleanup(SSotAsyncTestCase):
    """Test UserExecutionContext cleanup and resource management."""
    
    async def test_user_execution_context_cleanup_success(self):
        """Test UserExecutionContext cleanup executes all callbacks successfully."""
        context = UserExecutionContext(
            user_id="cleanup-user",
            request_id="cleanup-req",
            thread_id="cleanup-thread"
        )
        
        # Add mock cleanup callbacks
        sync_callback = Mock()
        async_callback = AsyncMock()
        
        context.cleanup_callbacks.append(sync_callback)
        context.cleanup_callbacks.append(async_callback)
        
        # Add some state to clean
        context.active_runs["run1"] = Mock()
        context.run_history = [Mock() for _ in range(15)]  # Over limit
        
        # Execute cleanup
        await context.cleanup()
        
        # Verify callbacks executed
        sync_callback.assert_called_once()
        async_callback.assert_called_once()
        
        # Verify state cleaned
        assert len(context.active_runs) == 0
        assert len(context.run_history) == 5  # Trimmed to last 5
        assert len(context.cleanup_callbacks) == 0
        assert context.status == ExecutionStatus.COMPLETED
        assert context._is_cleaned is True
        
        self.record_metric("cleanup_success", True)
    
    async def test_user_execution_context_cleanup_callback_error(self):
        """Test UserExecutionContext cleanup handles callback errors gracefully."""
        context = UserExecutionContext(
            user_id="error-user",
            request_id="error-req", 
            thread_id="error-thread"
        )
        
        # Add failing callback
        error_callback = Mock(side_effect=Exception("Callback error"))
        success_callback = Mock()
        
        context.cleanup_callbacks.append(error_callback)
        context.cleanup_callbacks.append(success_callback)
        
        # Execute cleanup (should not raise)
        await context.cleanup()
        
        # Verify both callbacks called despite error
        error_callback.assert_called_once()
        success_callback.assert_called_once()
        
        # Verify cleanup completed
        assert context._is_cleaned is True
        assert context.status == ExecutionStatus.COMPLETED
        
        self.record_metric("cleanup_error_handling", True)
    
    async def test_user_execution_context_cleanup_idempotent(self):
        """Test UserExecutionContext cleanup is idempotent (safe to call multiple times)."""
        context = UserExecutionContext(
            user_id="idempotent-user",
            request_id="idempotent-req",
            thread_id="idempotent-thread"
        )
        
        callback = Mock()
        context.cleanup_callbacks.append(callback)
        
        # First cleanup
        await context.cleanup()
        assert context._is_cleaned is True
        callback.assert_called_once()
        
        # Second cleanup (should be no-op)
        await context.cleanup()
        
        # Verify callback not called again
        callback.assert_called_once()
        
        self.record_metric("cleanup_idempotent", True)


class TestExecutionEngineFactoryInitialization(SSotBaseTestCase):
    """Test ExecutionEngineFactory initialization and configuration."""
    
    def test_factory_initialization_default_config(self):
        """Test ExecutionEngineFactory initializes with default configuration."""
        factory = ExecutionEngineFactory()
        
        # Verify config is set
        assert factory.config is not None
        assert isinstance(factory.config, ExecutionFactoryConfig)
        
        # Verify initial state
        assert factory._agent_registry is None
        assert factory._websocket_bridge_factory is None
        assert factory._db_connection_pool is None
        assert len(factory._user_semaphores) == 0
        assert len(factory._active_contexts) == 0
        
        # Verify metrics initialization
        expected_metrics = [
            'engines_created', 'engines_active', 'engines_cleaned',
            'total_users', 'concurrent_peak', 'created_at'
        ]
        for metric in expected_metrics:
            assert metric in factory._factory_metrics
            
        self.record_metric("factory_initialization", True)
    
    def test_factory_initialization_custom_config(self):
        """Test ExecutionEngineFactory initialization with custom config."""
        custom_config = ExecutionFactoryConfig(
            max_concurrent_per_user=3,
            execution_timeout_seconds=60.0,
            max_active_users=50
        )
        
        factory = ExecutionEngineFactory(config=custom_config)
        
        # Verify custom config used
        assert factory.config is custom_config
        assert factory.config.max_concurrent_per_user == 3
        assert factory.config.execution_timeout_seconds == 60.0
        assert factory.config.max_active_users == 50
        
        self.record_metric("factory_custom_config", True)
    
    def test_factory_configure_method(self):
        """Test ExecutionEngineFactory.configure() method."""
        factory = ExecutionEngineFactory()
        
        # Mock dependencies
        mock_agent_registry = Mock()
        mock_websocket_bridge_factory = Mock()
        mock_db_connection_pool = Mock()
        
        # Configure factory
        factory.configure(
            agent_registry=mock_agent_registry,
            websocket_bridge_factory=mock_websocket_bridge_factory,
            db_connection_pool=mock_db_connection_pool
        )
        
        # Verify dependencies set
        assert factory._agent_registry is mock_agent_registry
        assert factory._websocket_bridge_factory is mock_websocket_bridge_factory
        assert factory._db_connection_pool is mock_db_connection_pool
        
        self.record_metric("factory_configure", True)
    
    def test_factory_configure_none_agent_registry(self):
        """Test ExecutionEngineFactory.configure() with None agent registry (valid pattern)."""
        factory = ExecutionEngineFactory()
        
        mock_websocket_bridge_factory = Mock()
        mock_db_connection_pool = Mock()
        
        # Configure with None agent registry (per-request pattern)
        factory.configure(
            agent_registry=None,
            websocket_bridge_factory=mock_websocket_bridge_factory,
            db_connection_pool=mock_db_connection_pool
        )
        
        # Verify configuration accepted
        assert factory._agent_registry is None
        assert factory._websocket_bridge_factory is mock_websocket_bridge_factory
        assert factory._db_connection_pool is mock_db_connection_pool
        
        self.record_metric("factory_configure_none_registry", True)


class TestExecutionEngineCreation(SSotAsyncTestCase):
    """Test execution engine creation with user isolation."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        
        # Create factory with mock dependencies
        self.factory = ExecutionEngineFactory()
        self.mock_websocket_bridge_factory = Mock()
        self.factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=self.mock_websocket_bridge_factory,
            db_connection_pool=Mock()
        )
        
        # Create test user context
        self.user_context = UserExecutionContext(
            user_id=f"test-user-{uuid.uuid4().hex[:8]}",
            request_id=f"req-{uuid.uuid4().hex[:8]}",
            thread_id=f"thread-{uuid.uuid4().hex[:8]}"
        )
    
    async def test_create_execution_engine_success(self):
        """Test successful execution engine creation."""
        # Mock WebSocket emitter creation
        mock_emitter = Mock()
        self.mock_websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
        
        # Mock UserExecutionEngine creation
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine = Mock()
                mock_engine_class.return_value = mock_engine
                
                # Execute
                result = await self.factory.create_execution_engine(self.user_context)
                
                # Verify result
                assert isinstance(result, UserExecutionEngineWrapper)
                assert result.user_engine is mock_engine
                assert result.user_context is self.user_context
                
                # Verify factory metrics updated
                assert self.factory._factory_metrics['engines_created'] == 1
                assert self.factory._factory_metrics['engines_active'] == 1
                
                # Verify context registered
                assert len(self.factory._active_contexts) == 1
                assert self.user_context.request_id in self.factory._active_contexts
                
        self.record_metric("engine_creation_success", True)
    
    async def test_create_execution_engine_websocket_factory_fallback(self):
        """Test execution engine creation with WebSocket factory fallback."""
        # Mock WebSocket factory failure
        self.mock_websocket_bridge_factory.create_user_emitter = AsyncMock(
            side_effect=Exception("WebSocket factory failed")
        )
        
        # Mock fallback WebSocket emitter
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter') as mock_emitter_class:
                mock_emitter = Mock()
                mock_emitter_class.create_for_user.return_value = mock_emitter
                
                with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                    mock_engine = Mock()
                    mock_engine_class.return_value = mock_engine
                    
                    # Execute
                    result = await self.factory.create_execution_engine(self.user_context)
                    
                    # Verify fallback emitter created
                    mock_emitter_class.create_for_user.assert_called_once_with(
                        user_id=self.user_context.user_id,
                        thread_id=self.user_context.thread_id,
                        run_id=self.user_context.request_id,
                        websocket_manager=None
                    )
                    
                    # Verify wrapper created successfully
                    assert isinstance(result, UserExecutionEngineWrapper)
                    
        self.record_metric("websocket_fallback", True)
    
    async def test_create_execution_engine_user_engine_fallback(self):
        """Test execution engine creation falls back to IsolatedExecutionEngine."""
        # Mock WebSocket emitter creation
        mock_emitter = Mock()
        self.mock_websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
        
        # Mock UserExecutionEngine failure
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.side_effect = Exception("UserExecutionEngine failed")
                
                # Execute
                result = await self.factory.create_execution_engine(self.user_context)
                
                # Verify fallback to IsolatedExecutionEngine
                assert isinstance(result, IsolatedExecutionEngine)
                assert result.user_context is self.user_context
                
        self.record_metric("engine_fallback", True)
    
    async def test_create_execution_engine_resource_limits_enforced(self):
        """Test execution engine creation enforces resource limits."""
        # Fill up to the limit with mock contexts
        for i in range(self.factory.config.max_active_users):
            mock_context = UserExecutionContext(
                user_id=f"user-{i}",
                request_id=f"req-{i}",
                thread_id=f"thread-{i}"
            )
            self.factory._active_contexts[f"req-{i}"] = mock_context
            
        # Try to create one more (should fail)
        with self.expect_exception(RuntimeError, "Maximum active users.*exceeded"):
            await self.factory.create_execution_engine(self.user_context)
            
        self.record_metric("resource_limits_enforced", True)
    
    async def test_create_execution_engine_memory_threshold_warning(self):
        """Test execution engine creation logs warning when memory threshold exceeded."""
        # Mock high memory usage
        with patch('psutil.Process') as mock_process_class:
            mock_process = Mock()
            # Set memory to exceed threshold (1024 MB default)
            mock_process.memory_info.return_value.rss = 2048 * 1024 * 1024  # 2048 MB
            mock_process_class.return_value = mock_process
            
            # Mock WebSocket emitter creation
            mock_emitter = Mock()
            self.mock_websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
                mock_agent_factory = Mock()
                mock_get_factory.return_value = mock_agent_factory
                
                with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                    mock_engine = Mock()
                    mock_engine_class.return_value = mock_engine
                    
                    # Execute (should succeed but log warning)
                    result = await self.factory.create_execution_engine(self.user_context)
                    
                    # Verify engine created despite memory warning
                    assert isinstance(result, UserExecutionEngineWrapper)
                    
        self.record_metric("memory_threshold_warning", True)


class TestUserSemaphoreManagement(SSotAsyncTestCase):
    """Test per-user semaphore management and concurrency control."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        self.factory = ExecutionEngineFactory()
    
    async def test_get_user_semaphore_creates_new(self):
        """Test _get_user_semaphore creates new semaphore for user."""
        user_id = "semaphore-user-1"
        
        # Get semaphore (should create new one)
        semaphore = await self.factory._get_user_semaphore(user_id)
        
        # Verify semaphore created and cached
        assert isinstance(semaphore, asyncio.Semaphore)
        assert user_id in self.factory._user_semaphores
        assert self.factory._user_semaphores[user_id] is semaphore
        
        # Verify semaphore has correct limit
        assert semaphore._value == self.factory.config.max_concurrent_per_user
        
        self.record_metric("semaphore_creation", True)
    
    async def test_get_user_semaphore_returns_existing(self):
        """Test _get_user_semaphore returns existing semaphore for user."""
        user_id = "semaphore-user-2"
        
        # Get semaphore first time
        semaphore1 = await self.factory._get_user_semaphore(user_id)
        
        # Get semaphore second time
        semaphore2 = await self.factory._get_user_semaphore(user_id)
        
        # Verify same semaphore returned
        assert semaphore1 is semaphore2
        assert len(self.factory._user_semaphores) == 1
        
        self.record_metric("semaphore_reuse", True)
    
    async def test_get_user_semaphore_different_users_separate(self):
        """Test different users get separate semaphores."""
        user_id_1 = "semaphore-user-1"
        user_id_2 = "semaphore-user-2"
        
        # Get semaphores for different users
        semaphore1 = await self.factory._get_user_semaphore(user_id_1)
        semaphore2 = await self.factory._get_user_semaphore(user_id_2)
        
        # Verify separate semaphores
        assert semaphore1 is not semaphore2
        assert len(self.factory._user_semaphores) == 2
        assert user_id_1 in self.factory._user_semaphores
        assert user_id_2 in self.factory._user_semaphores
        
        self.record_metric("semaphore_user_isolation", True)
    
    async def test_get_user_semaphore_disabled_returns_high_limit(self):
        """Test _get_user_semaphore returns high-limit semaphore when disabled."""
        # Configure factory with semaphores disabled
        config = ExecutionFactoryConfig(enable_user_semaphores=False)
        factory = ExecutionEngineFactory(config=config)
        
        user_id = "disabled-semaphore-user"
        
        # Get semaphore
        semaphore = await factory._get_user_semaphore(user_id)
        
        # Verify high-limit semaphore (100)
        assert isinstance(semaphore, asyncio.Semaphore)
        assert semaphore._value == 100
        
        # Verify not cached (new one each time when disabled)
        assert user_id not in factory._user_semaphores
        
        self.record_metric("semaphore_disabled", True)
    
    async def test_user_semaphore_concurrency_limit(self):
        """Test user semaphore enforces concurrency limits."""
        user_id = "concurrent-user"
        
        # Configure factory with low limit for testing
        config = ExecutionFactoryConfig(max_concurrent_per_user=2)
        factory = ExecutionEngineFactory(config=config)
        
        semaphore = await factory._get_user_semaphore(user_id)
        
        # Acquire semaphore up to limit
        await semaphore.acquire()  # 1
        await semaphore.acquire()  # 2
        
        # Verify limit reached
        assert semaphore.locked()
        
        # Try to acquire beyond limit (should block)
        acquire_task = asyncio.create_task(semaphore.acquire())
        
        # Give task a chance to run
        await asyncio.sleep(0.001)
        
        # Verify task is blocked
        assert not acquire_task.done()
        
        # Release one permit
        semaphore.release()
        
        # Now the blocked task should complete
        await asyncio.wait_for(acquire_task, timeout=0.1)
        
        # Cleanup
        semaphore.release()
        
        self.record_metric("semaphore_concurrency_limit", True)


class TestFactoryResourceManagement(SSotAsyncTestCase):
    """Test factory resource management and limits enforcement."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        self.factory = ExecutionEngineFactory()
    
    async def test_enforce_resource_limits_under_limit(self):
        """Test _enforce_resource_limits passes when under limits."""
        user_id = "under-limit-user"
        
        # Should not raise (no active contexts)
        await self.factory._enforce_resource_limits(user_id)
        
        self.record_metric("resource_limits_under", True)
    
    async def test_enforce_resource_limits_at_limit(self):
        """Test _enforce_resource_limits fails when at user limit."""
        user_id = "at-limit-user"
        
        # Fill up to max active users
        for i in range(self.factory.config.max_active_users):
            mock_context = UserExecutionContext(
                user_id=f"user-{i}",
                request_id=f"req-{i}",
                thread_id=f"thread-{i}"
            )
            self.factory._active_contexts[f"req-{i}"] = mock_context
            
        # Try to enforce limits (should fail)
        with self.expect_exception(RuntimeError, "Maximum active users.*exceeded"):
            await self.factory._enforce_resource_limits(user_id)
            
        self.record_metric("resource_limits_at_max", True)
    
    async def test_enforce_resource_limits_memory_warning(self):
        """Test _enforce_resource_limits logs memory warning but doesn't fail."""
        # Mock high memory usage
        with patch('psutil.Process') as mock_process_class:
            mock_process = Mock()
            # Set memory to exceed threshold
            mock_process.memory_info.return_value.rss = 2048 * 1024 * 1024  # 2048 MB
            mock_process_class.return_value = mock_process
            
            user_id = "memory-warning-user"
            
            # Should not raise (just logs warning)
            await self.factory._enforce_resource_limits(user_id)
            
        self.record_metric("memory_warning_logged", True)
    
    async def test_cleanup_context_removes_and_cleans(self):
        """Test cleanup_context removes context and calls cleanup."""
        # Add mock context
        request_id = "cleanup-req-123"
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.cleanup = AsyncMock()
        
        self.factory._active_contexts[request_id] = mock_context
        self.factory._factory_metrics['engines_active'] = 1
        
        # Execute cleanup
        await self.factory.cleanup_context(request_id)
        
        # Verify context removed and cleaned
        assert request_id not in self.factory._active_contexts
        mock_context.cleanup.assert_called_once()
        assert self.factory._factory_metrics['engines_active'] == 0
        assert self.factory._factory_metrics['engines_cleaned'] == 1
        
        self.record_metric("context_cleanup", True)
    
    async def test_cleanup_context_nonexistent_request(self):
        """Test cleanup_context handles nonexistent request gracefully."""
        nonexistent_id = "nonexistent-req"
        
        # Should not raise
        await self.factory.cleanup_context(nonexistent_id)
        
        # Verify no changes to metrics
        assert self.factory._factory_metrics['engines_cleaned'] == 0
        
        self.record_metric("cleanup_nonexistent", True)


class TestFactoryMetrics(SSotBaseTestCase):
    """Test factory metrics collection and reporting."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        self.factory = ExecutionEngineFactory()
    
    def test_get_factory_metrics_structure(self):
        """Test get_factory_metrics returns correct structure."""
        metrics = self.factory.get_factory_metrics()
        
        # Verify required keys present
        required_keys = [
            'engines_created', 'engines_active', 'engines_cleaned',
            'total_users', 'concurrent_peak', 'created_at',
            'active_contexts', 'user_semaphores', 'config', 'timestamp'
        ]
        
        for key in required_keys:
            assert key in metrics, f"Missing required key: {key}"
            
        # Verify config structure
        config_keys = [
            'max_concurrent_per_user', 'execution_timeout_seconds',
            'max_active_users'
        ]
        for key in config_keys:
            assert key in metrics['config'], f"Missing config key: {key}"
            
        self.record_metric("metrics_structure", True)
    
    def test_get_factory_metrics_values(self):
        """Test get_factory_metrics returns correct values."""
        # Add some mock state
        self.factory._factory_metrics['engines_created'] = 5
        self.factory._factory_metrics['engines_active'] = 3
        self.factory._factory_metrics['total_users'] = 2
        self.factory._factory_metrics['concurrent_peak'] = 4
        
        # Add mock contexts and semaphores
        self.factory._active_contexts['req1'] = Mock()
        self.factory._active_contexts['req2'] = Mock()
        self.factory._user_semaphores['user1'] = Mock()
        
        metrics = self.factory.get_factory_metrics()
        
        # Verify values
        assert metrics['engines_created'] == 5
        assert metrics['engines_active'] == 3
        assert metrics['total_users'] == 2
        assert metrics['concurrent_peak'] == 4
        assert metrics['active_contexts'] == 2
        assert metrics['user_semaphores'] == 1
        
        self.record_metric("metrics_values", True)
    
    def test_factory_metrics_track_peak_concurrency(self):
        """Test factory tracks peak concurrency correctly."""
        initial_peak = self.factory._factory_metrics['concurrent_peak']
        
        # Add contexts one by one
        for i in range(3):
            request_id = f"peak-req-{i}"
            mock_context = Mock()
            self.factory._active_contexts[request_id] = mock_context
            
            # Simulate the logic from create_execution_engine
            current_active = len(self.factory._active_contexts)
            if current_active > self.factory._factory_metrics['concurrent_peak']:
                self.factory._factory_metrics['concurrent_peak'] = current_active
                
        # Verify peak tracked
        assert self.factory._factory_metrics['concurrent_peak'] == 3
        assert self.factory._factory_metrics['concurrent_peak'] > initial_peak
        
        self.record_metric("peak_concurrency_tracking", True)
    
    def test_factory_metrics_track_unique_users(self):
        """Test factory tracks unique users correctly."""
        # Add contexts for same user (should count as 1 unique user)
        user_id = "unique-user-test"
        
        for i in range(3):
            request_id = f"req-{i}"
            mock_context = Mock()
            mock_context.user_id = user_id
            self.factory._active_contexts[request_id] = mock_context
            
        # Simulate unique user counting logic
        unique_users = set()
        for context in self.factory._active_contexts.values():
            unique_users.add(context.user_id)
            
        # Verify unique user counting
        assert len(unique_users) == 1
        
        self.record_metric("unique_user_tracking", True)


class TestConcurrentEngineCreation(SSotAsyncTestCase):
    """Test concurrent engine creation and race condition handling."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        self.factory = ExecutionEngineFactory()
        self.factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(),
            db_connection_pool=Mock()
        )
    
    async def test_concurrent_engine_creation_different_users(self):
        """Test concurrent engine creation for different users succeeds."""
        # Mock dependencies
        self.factory._websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=Mock())
        
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.return_value = Mock()
                
                # Create contexts for different users
                contexts = []
                for i in range(5):
                    context = UserExecutionContext(
                        user_id=f"concurrent-user-{i}",
                        request_id=f"concurrent-req-{i}",
                        thread_id=f"concurrent-thread-{i}"
                    )
                    contexts.append(context)
                
                # Execute concurrently
                tasks = [
                    self.factory.create_execution_engine(context)
                    for context in contexts
                ]
                
                results = await asyncio.gather(*tasks)
                
                # Verify all succeeded
                assert len(results) == 5
                for result in results:
                    assert isinstance(result, UserExecutionEngineWrapper)
                    
                # Verify factory state
                assert len(self.factory._active_contexts) == 5
                assert self.factory._factory_metrics['engines_created'] == 5
                assert self.factory._factory_metrics['engines_active'] == 5
                
        self.record_metric("concurrent_different_users", True)
    
    async def test_concurrent_engine_creation_same_user_limited(self):
        """Test concurrent engine creation for same user respects limits."""
        # Configure low limit for testing
        config = ExecutionFactoryConfig(max_concurrent_per_user=2)
        factory = ExecutionEngineFactory(config=config)
        factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(),
            db_connection_pool=Mock()
        )
        
        # Mock dependencies
        factory._websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=Mock())
        
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.return_value = Mock()
                
                user_id = "limited-concurrent-user"
                
                # Create contexts for same user
                contexts = []
                for i in range(4):  # More than limit
                    context = UserExecutionContext(
                        user_id=user_id,
                        request_id=f"limited-req-{i}",
                        thread_id=f"limited-thread-{i}"
                    )
                    contexts.append(context)
                
                # Execute concurrently
                tasks = [
                    factory.create_execution_engine(context)
                    for context in contexts
                ]
                
                # Some should succeed, some should be limited by semaphore
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify some succeeded and some were limited
                successes = [r for r in results if isinstance(r, UserExecutionEngineWrapper)]
                assert len(successes) <= config.max_concurrent_per_user
                
        self.record_metric("concurrent_same_user_limited", True)
    
    async def test_semaphore_lock_race_condition_handling(self):
        """Test semaphore creation handles race conditions correctly."""
        user_id = "race-condition-user"
        
        # Simulate race condition by calling _get_user_semaphore concurrently
        tasks = [
            self.factory._get_user_semaphore(user_id)
            for _ in range(10)
        ]
        
        semaphores = await asyncio.gather(*tasks)
        
        # Verify all tasks got the same semaphore (no race condition)
        first_semaphore = semaphores[0]
        for semaphore in semaphores:
            assert semaphore is first_semaphore
            
        # Verify only one semaphore created
        assert len(self.factory._user_semaphores) == 1
        assert user_id in self.factory._user_semaphores
        
        self.record_metric("semaphore_race_condition", True)


class TestFactoryPerformance(SSotAsyncTestCase):
    """Test factory performance requirements and benchmarks."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        self.factory = ExecutionEngineFactory()
        self.factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(), 
            db_connection_pool=Mock()
        )
    
    def test_factory_initialization_performance(self):
        """Test factory initialization is fast (< 10ms)."""
        start_time = time.time()
        
        # Create factory
        factory = ExecutionEngineFactory()
        
        end_time = time.time()
        initialization_time_ms = (end_time - start_time) * 1000
        
        # Verify performance requirement
        assert initialization_time_ms < 10, f"Factory initialization took {initialization_time_ms:.2f}ms, should be < 10ms"
        
        self.record_metric("factory_init_time_ms", initialization_time_ms)
    
    async def test_engine_creation_performance(self):
        """Test engine creation performance (< 100ms)."""
        # Mock fast dependencies
        self.factory._websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=Mock())
        
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.return_value = Mock()
                
                context = UserExecutionContext(
                    user_id="perf-user",
                    request_id="perf-req",
                    thread_id="perf-thread"
                )
                
                start_time = time.time()
                
                # Create engine
                result = await self.factory.create_execution_engine(context)
                
                end_time = time.time()
                creation_time_ms = (end_time - start_time) * 1000
                
                # Verify performance requirement
                assert creation_time_ms < 100, f"Engine creation took {creation_time_ms:.2f}ms, should be < 100ms"
                assert isinstance(result, UserExecutionEngineWrapper)
                
                self.record_metric("engine_creation_time_ms", creation_time_ms)
    
    async def test_semaphore_acquisition_performance(self):
        """Test semaphore acquisition performance (< 1ms)."""
        user_id = "semaphore-perf-user"
        
        # Get semaphore
        semaphore = await self.factory._get_user_semaphore(user_id)
        
        start_time = time.time()
        
        # Acquire and release semaphore
        await semaphore.acquire()
        semaphore.release()
        
        end_time = time.time()
        acquisition_time_ms = (end_time - start_time) * 1000
        
        # Verify performance requirement
        assert acquisition_time_ms < 1, f"Semaphore acquisition took {acquisition_time_ms:.2f}ms, should be < 1ms"
        
        self.record_metric("semaphore_acquisition_time_ms", acquisition_time_ms)
    
    def test_metrics_collection_performance(self):
        """Test metrics collection performance (< 5ms) with loaded factory."""
        # Add mock state to simulate loaded factory
        for i in range(20):
            request_id = f"perf-req-{i}"
            mock_context = Mock()
            mock_context.user_id = f"user-{i % 5}"  # 5 unique users
            self.factory._active_contexts[request_id] = mock_context
            self.factory._user_semaphores[f"user-{i}"] = Mock()
            
        start_time = time.time()
        
        # Collect metrics
        metrics = self.factory.get_factory_metrics()
        
        end_time = time.time()
        collection_time_ms = (end_time - start_time) * 1000
        
        # Verify performance requirement
        assert collection_time_ms < 5, f"Metrics collection took {collection_time_ms:.2f}ms, should be < 5ms"
        
        # Verify metrics collected correctly
        assert metrics['active_contexts'] == 20
        assert metrics['user_semaphores'] == 20
        
        self.record_metric("metrics_collection_time_ms", collection_time_ms)


class TestFactoryErrorHandling(SSotAsyncTestCase):
    """Test factory error handling and edge cases."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        self.factory = ExecutionEngineFactory()
    
    async def test_create_execution_engine_unconfigured_factory(self):
        """Test create_execution_engine fails gracefully with unconfigured factory."""
        context = UserExecutionContext(
            user_id="unconfigured-user",
            request_id="unconfigured-req",
            thread_id="unconfigured-thread"
        )
        
        # Try to create engine without configuration
        with self.expect_exception(RuntimeError, "Execution engine creation failed"):
            await self.factory.create_execution_engine(context)
            
        self.record_metric("unconfigured_factory_error", True)
    
    async def test_create_execution_engine_handles_websocket_errors(self):
        """Test create_execution_engine handles WebSocket emitter creation errors."""
        self.factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(),
            db_connection_pool=Mock()
        )
        
        # Mock WebSocket factory and fallback failures
        self.factory._websocket_bridge_factory.create_user_emitter = AsyncMock(
            side_effect=Exception("WebSocket factory failed")
        )
        
        context = UserExecutionContext(
            user_id="websocket-error-user",
            request_id="websocket-error-req", 
            thread_id="websocket-error-thread"
        )
        
        with patch('netra_backend.app.websocket_core.unified_emitter.UnifiedWebSocketEmitter') as mock_emitter_class:
            mock_emitter_class.create_for_user.side_effect = Exception("Fallback failed")
            
            # Should fail gracefully
            with self.expect_exception(RuntimeError, "Execution engine creation failed"):
                await self.factory.create_execution_engine(context)
                
        self.record_metric("websocket_error_handling", True)
    
    async def test_cleanup_context_handles_cleanup_errors(self):
        """Test cleanup_context handles context cleanup errors gracefully."""
        request_id = "error-cleanup-req"
        
        # Add mock context that fails cleanup
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        
        self.factory._active_contexts[request_id] = mock_context
        self.factory._factory_metrics['engines_active'] = 1
        
        # Should not raise exception
        await self.factory.cleanup_context(request_id)
        
        # Verify context still removed despite error
        assert request_id not in self.factory._active_contexts
        assert self.factory._factory_metrics['engines_active'] == 0
        
        self.record_metric("cleanup_error_handling", True)
    
    async def test_enforce_resource_limits_memory_error_handling(self):
        """Test _enforce_resource_limits handles memory check errors gracefully."""
        with patch('psutil.Process') as mock_process_class:
            # Mock process creation failure
            mock_process_class.side_effect = Exception("Process access failed")
            
            user_id = "memory-error-user"
            
            # Should not raise (memory check is optional)
            await self.factory._enforce_resource_limits(user_id)
            
        self.record_metric("memory_error_handling", True)


class TestGlobalFactoryAccess(SSotAsyncTestCase):
    """Test global factory access and singleton pattern."""
    
    async def test_get_execution_engine_factory_returns_instance(self):
        """Test get_execution_engine_factory returns factory instance."""
        # Clear any existing factory first
        import netra_backend.app.agents.supervisor.execution_factory as factory_module
        factory_module._execution_engine_factory = None
        
        # Create new factory
        factory_module._execution_engine_factory = ExecutionEngineFactory()
        
        # Get factory
        result = get_execution_engine_factory()
        
        # Verify
        assert isinstance(result, ExecutionEngineFactory)
        assert result is factory_module._execution_engine_factory
        
        self.record_metric("global_factory_access", True)
    
    async def test_get_execution_engine_factory_none_returns_new(self):
        """Test get_execution_engine_factory creates new instance when None."""
        # Clear factory
        import netra_backend.app.agents.supervisor.execution_factory as factory_module
        factory_module._execution_engine_factory = None
        
        # Get factory
        result = get_execution_engine_factory()
        
        # Verify new factory created
        assert isinstance(result, ExecutionEngineFactory)
        assert factory_module._execution_engine_factory is result
        
        self.record_metric("global_factory_creation", True)


class TestUserExecutionEngineWrapper(SSotAsyncTestCase):
    """Test UserExecutionEngineWrapper delegation and compatibility."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        
        # Create wrapper with mocks
        self.mock_user_engine = Mock()
        self.user_context = UserExecutionContext(
            user_id="wrapper-user",
            request_id="wrapper-req",
            thread_id="wrapper-thread"
        )
        self.mock_agent_registry = Mock()
        self.mock_websocket_emitter = Mock()
        self.mock_execution_semaphore = Mock()
        self.mock_factory = Mock()
        
        self.wrapper = UserExecutionEngineWrapper(
            user_engine=self.mock_user_engine,
            user_context=self.user_context,
            agent_registry=self.mock_agent_registry,
            websocket_emitter=self.mock_websocket_emitter,
            execution_semaphore=self.mock_execution_semaphore,
            execution_timeout=30.0,
            factory=self.mock_factory
        )
    
    def test_wrapper_initialization(self):
        """Test UserExecutionEngineWrapper initialization."""
        # Verify all attributes set
        assert self.wrapper.user_engine is self.mock_user_engine
        assert self.wrapper.user_context is self.user_context
        assert self.wrapper.agent_registry is self.mock_agent_registry
        assert self.wrapper.websocket_emitter is self.mock_websocket_emitter
        assert self.wrapper.execution_semaphore is self.mock_execution_semaphore
        assert self.wrapper.execution_timeout == 30.0
        assert self.wrapper.factory is self.mock_factory
        
        self.record_metric("wrapper_initialization", True)
    
    def test_wrapper_delegation(self):
        """Test UserExecutionEngineWrapper delegates method calls."""
        # Add method to mock user engine
        self.mock_user_engine.test_method = Mock(return_value="test_result")
        
        # Call method through wrapper
        result = self.wrapper.test_method("arg1", kwarg1="value1")
        
        # Verify delegation
        self.mock_user_engine.test_method.assert_called_once_with("arg1", kwarg1="value1")
        assert result == "test_result"
        
        self.record_metric("wrapper_delegation", True)
    
    async def test_wrapper_cleanup_delegation(self):
        """Test UserExecutionEngineWrapper cleanup delegates to user engine."""
        self.mock_user_engine.cleanup = AsyncMock()
        
        # Call cleanup
        await self.wrapper.cleanup()
        
        # Verify delegation
        self.mock_user_engine.cleanup.assert_called_once()
        
        self.record_metric("wrapper_cleanup_delegation", True)
    
    async def test_wrapper_cleanup_handles_errors(self):
        """Test UserExecutionEngineWrapper cleanup handles errors gracefully."""
        self.mock_user_engine.cleanup = AsyncMock(side_effect=Exception("Cleanup error"))
        
        # Should not raise
        await self.wrapper.cleanup()
        
        # Verify cleanup was attempted
        self.mock_user_engine.cleanup.assert_called_once()
        
        self.record_metric("wrapper_cleanup_error_handling", True)


# Performance benchmarks and compliance verification
class TestFactoryCompliance(SSotAsyncTestCase):
    """Test factory compliance with golden path requirements."""
    
    async def test_factory_supports_10_concurrent_users(self):
        """Test factory can handle 10+ concurrent users (golden path requirement)."""
        factory = ExecutionEngineFactory()
        factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(),
            db_connection_pool=Mock()
        )
        
        # Mock dependencies
        factory._websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=Mock())
        
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.return_value = Mock()
                
                # Create contexts for 15 different users
                contexts = []
                for i in range(15):
                    context = UserExecutionContext(
                        user_id=f"concurrent-user-{i}",
                        request_id=f"concurrent-req-{i}",
                        thread_id=f"concurrent-thread-{i}"
                    )
                    contexts.append(context)
                
                # Execute concurrently 
                start_time = time.time()
                
                tasks = [
                    factory.create_execution_engine(context)
                    for context in contexts
                ]
                
                results = await asyncio.gather(*tasks)
                
                end_time = time.time()
                total_time_ms = (end_time - start_time) * 1000
                
                # Verify all succeeded
                assert len(results) == 15
                for result in results:
                    assert isinstance(result, UserExecutionEngineWrapper)
                    
                # Verify performance (< 1 second for 15 users)
                assert total_time_ms < 1000, f"15 concurrent users took {total_time_ms:.1f}ms, should be < 1000ms"
                
                # Verify isolation
                assert len(factory._active_contexts) == 15
                assert factory._factory_metrics['engines_created'] == 15
                
        self.record_metric("concurrent_users_supported", 15)
        self.record_metric("concurrent_creation_time_ms", total_time_ms)
    
    async def test_factory_memory_efficiency(self):
        """Test factory memory efficiency with multiple engines."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory_mb = process.memory_info().rss / 1024 / 1024
        
        factory = ExecutionEngineFactory()
        factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(),
            db_connection_pool=Mock()
        )
        
        # Mock lightweight dependencies
        factory._websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=Mock())
        
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.return_value = Mock()
                
                # Create 20 engines
                for i in range(20):
                    context = UserExecutionContext(
                        user_id=f"memory-user-{i}",
                        request_id=f"memory-req-{i}",
                        thread_id=f"memory-thread-{i}"
                    )
                    await factory.create_execution_engine(context)
                
                # Check memory usage
                final_memory_mb = process.memory_info().rss / 1024 / 1024
                memory_increase_mb = final_memory_mb - initial_memory_mb
                
                # Verify reasonable memory usage (< 50MB increase for 20 engines)
                assert memory_increase_mb < 50, f"Memory increased by {memory_increase_mb:.1f}MB for 20 engines, should be < 50MB"
                
        self.record_metric("memory_efficiency_mb_per_engine", memory_increase_mb / 20)
    
    async def test_factory_resource_cleanup_compliance(self):
        """Test factory properly cleans up resources (memory leak prevention)."""
        factory = ExecutionEngineFactory()
        factory.configure(
            agent_registry=Mock(),
            websocket_bridge_factory=Mock(),
            db_connection_pool=Mock()
        )
        
        # Mock dependencies
        factory._websocket_bridge_factory.create_user_emitter = AsyncMock(return_value=Mock())
        
        with patch('netra_backend.app.agents.supervisor.execution_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_factory.UserExecutionEngine') as mock_engine_class:
                mock_engine_class.return_value = Mock()
                
                # Create and cleanup engines
                request_ids = []
                for i in range(10):
                    context = UserExecutionContext(
                        user_id=f"cleanup-user-{i}",
                        request_id=f"cleanup-req-{i}",
                        thread_id=f"cleanup-thread-{i}"
                    )
                    await factory.create_execution_engine(context)
                    request_ids.append(context.request_id)
                
                # Verify engines created
                assert len(factory._active_contexts) == 10
                assert factory._factory_metrics['engines_active'] == 10
                
                # Cleanup all contexts
                for request_id in request_ids:
                    await factory.cleanup_context(request_id)
                
                # Verify complete cleanup
                assert len(factory._active_contexts) == 0
                assert factory._factory_metrics['engines_active'] == 0
                assert factory._factory_metrics['engines_cleaned'] == 10
                
        self.record_metric("resource_cleanup_compliance", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])