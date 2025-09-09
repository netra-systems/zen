"""Comprehensive Unit Tests for ExecutionEngineFactory SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal (ALL user tiers depend on this)
- Business Goal: Ensure multi-user system stability and prevent cascade failures
- Value Impact: ExecutionEngineFactory is CRITICAL for user isolation - prevents data leakage between users
- Strategic Impact: Foundation for production multi-tenant deployment - failure cascades to all users

CRITICAL IMPORTANCE:
- ExecutionEngineFactory creates isolated UserExecutionEngine instances for each user request
- Prevents shared state contamination between concurrent users (10+ users simultaneously)
- Manages resource limits to prevent resource exhaustion attacks
- Handles WebSocket manager integration for real-time agent events (mission critical for chat value)
- Provides automatic lifecycle management and cleanup to prevent memory leaks
- Enforces per-user concurrency limits to maintain system stability

This comprehensive test suite validates ALL factory methods, user isolation patterns,
resource management, error conditions, and factory lifecycle management.
"""

import asyncio
import time
import uuid
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, MagicMock, patch

# SSOT imports following test_framework patterns
from test_framework.base import BaseTestCase, AsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Target module and dependencies
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError,
    get_execution_engine_factory,
    configure_execution_engine_factory,
    user_execution_engine
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    validate_user_context
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineFactoryInitialization(AsyncTestCase):
    """Test ExecutionEngineFactory initialization and dependency validation."""
    
    @pytest.mark.unit
    def test_factory_initialization_success(self):
        """Test factory initializes correctly with valid dependencies."""
        # Setup
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        database_session_manager = Mock()
        redis_manager = Mock()
        
        # Execute
        factory = ExecutionEngineFactory(
            websocket_bridge=websocket_bridge,
            database_session_manager=database_session_manager,
            redis_manager=redis_manager
        )
        
        # Verify initialization
        assert factory._websocket_bridge is websocket_bridge
        assert factory._database_session_manager is database_session_manager
        assert factory._redis_manager is redis_manager
        assert factory._max_engines_per_user == 2
        assert factory._engine_timeout_seconds == 300
        assert factory._cleanup_interval == 60
        assert len(factory._active_engines) == 0
        assert factory._cleanup_task is None
        
        # Verify metrics initialization
        expected_metrics = {
            'total_engines_created': 0,
            'total_engines_cleaned': 0,
            'active_engines_count': 0,
            'creation_errors': 0,
            'cleanup_errors': 0,
            'timeout_cleanups': 0,
            'user_limit_rejections': 0
        }
        assert factory._factory_metrics == expected_metrics

    @pytest.mark.unit
    def test_factory_initialization_missing_websocket_bridge(self):
        """Test factory initialization fails without websocket bridge (critical dependency)."""
        # Execute & Verify
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory(websocket_bridge=None)
        
        assert "ExecutionEngineFactory requires websocket_bridge" in str(exc_info.value)
        assert "WebSocket events that enable chat business value" in str(exc_info.value)

    @pytest.mark.unit
    def test_factory_initialization_with_minimal_dependencies(self):
        """Test factory can initialize with just websocket bridge."""
        # Setup
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Execute
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        # Verify
        assert factory._websocket_bridge is websocket_bridge
        assert factory._database_session_manager is None
        assert factory._redis_manager is None
        assert factory._tool_dispatcher_factory is None

    @pytest.mark.unit
    def test_set_tool_dispatcher_factory(self):
        """Test tool dispatcher factory integration."""
        # Setup
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        tool_dispatcher_factory = Mock()
        
        # Execute
        factory.set_tool_dispatcher_factory(tool_dispatcher_factory)
        
        # Verify
        assert factory._tool_dispatcher_factory is tool_dispatcher_factory


class TestUserEngineCreation(AsyncTestCase):
    """Test user execution engine creation and isolation patterns."""
    
    @pytest.fixture
    def websocket_bridge(self):
        """Mock WebSocket bridge for testing."""
        return Mock(spec=AgentWebSocketBridge)
    
    @pytest.fixture
    def factory(self, websocket_bridge):
        """Create factory instance for testing."""
        return ExecutionEngineFactory(
            websocket_bridge=websocket_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
    
    @pytest.fixture
    def user_context(self):
        """Create valid user execution context."""
        return UserExecutionContext.from_request_supervisor(
            user_id="test-user-123",
            thread_id="thread-456",
            run_id="run-789",
            metadata={"source": "test"}
        )

    @pytest.mark.unit
    async def test_create_for_user_success(self, factory, user_context):
        """Test successful user engine creation with proper isolation."""
        # Mock dependencies
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
                mock_emitter = Mock()
                mock_emitter_class.return_value = mock_emitter
                
                with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_engine_class:
                    mock_engine = Mock()
                    mock_engine.engine_id = "engine-test-123"
                    mock_engine_class.return_value = mock_engine
                    
                    # Execute
                    result = await factory.create_for_user(user_context)
                    
                    # Verify engine creation
                    assert result is mock_engine
                    mock_engine_class.assert_called_once_with(
                        context=user_context,
                        agent_factory=mock_agent_factory,
                        websocket_emitter=mock_emitter
                    )
                    
                    # Verify infrastructure managers attached
                    assert mock_engine.database_session_manager == factory._database_session_manager
                    assert mock_engine.redis_manager == factory._redis_manager
                    
                    # Verify metrics updated
                    assert factory._factory_metrics['total_engines_created'] == 1
                    assert factory._factory_metrics['active_engines_count'] == 1
                    
                    # Verify engine registered
                    assert len(factory._active_engines) == 1
                    assert mock_engine in factory._active_engines.values()

    @pytest.mark.unit
    async def test_create_for_user_invalid_context(self, factory):
        """Test engine creation fails with invalid user context."""
        # Setup invalid context
        invalid_context = Mock()
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.validate_user_context') as mock_validate:
            mock_validate.side_effect = TypeError("Invalid context")
            
            # Execute & Verify
            with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                await factory.create_for_user(invalid_context)
            
            assert "Invalid user context" in str(exc_info.value)
            # Note: The validation error happens before the metrics tracking try-catch block
            # so creation_errors is not incremented for validation errors

    @pytest.mark.unit
    async def test_create_for_user_agent_factory_unavailable(self, factory, user_context):
        """Test engine creation fails when agent factory is unavailable."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = None
            
            # Execute & Verify
            with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                await factory.create_for_user(user_context)
            
            assert "AgentInstanceFactory not available" in str(exc_info.value)
            assert factory._factory_metrics['creation_errors'] == 1

    @pytest.mark.unit
    async def test_create_for_user_websocket_emitter_failure(self, factory, user_context):
        """Test engine creation fails when WebSocket emitter creation fails."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
                mock_emitter_class.side_effect = Exception("WebSocket creation failed")
                
                # Execute & Verify
                with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                    await factory.create_for_user(user_context)
                
                assert "WebSocket emitter creation failed" in str(exc_info.value)
                assert factory._factory_metrics['creation_errors'] == 1

    @pytest.mark.unit
    async def test_create_for_user_engine_creation_failure(self, factory, user_context):
        """Test engine creation fails when UserExecutionEngine construction fails."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
                mock_emitter = Mock()
                mock_emitter_class.return_value = mock_emitter
                
                with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_engine_class:
                    mock_engine_class.side_effect = Exception("Engine creation failed")
                    
                    # Execute & Verify
                    with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                        await factory.create_for_user(user_context)
                    
                    assert "Engine creation failed" in str(exc_info.value)
                    assert factory._factory_metrics['creation_errors'] == 1


class TestUserEngineLimitsAndIsolation(AsyncTestCase):
    """Test user engine limits and complete user isolation."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for testing limits."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)
    
    @pytest.fixture
    def user_context_1(self):
        """Create user context for user 1."""
        return UserExecutionContext.from_request_supervisor(
            user_id="user-1",
            thread_id="thread-1",
            run_id="run-1",
            metadata={"source": "test"}
        )
    
    @pytest.fixture
    def user_context_2(self):
        """Create user context for user 2."""
        return UserExecutionContext.from_request_supervisor(
            user_id="user-2", 
            thread_id="thread-2",
            run_id="run-2",
            metadata={"source": "test"}
        )

    @pytest.mark.unit
    async def test_enforce_user_engine_limits_under_limit(self, factory):
        """Test user engine limit enforcement when under limit."""
        # No engines exist, should pass
        await factory._enforce_user_engine_limits("test-user")
        
        # Should not increment rejection metrics
        assert factory._factory_metrics['user_limit_rejections'] == 0

    @pytest.mark.unit
    async def test_enforce_user_engine_limits_at_limit(self, factory):
        """Test user engine limit enforcement at exact limit."""
        # Setup: Create mock engines at limit for user
        user_id = "test-user"
        
        # Create mock engines
        for i in range(factory._max_engines_per_user):
            mock_engine = Mock()
            mock_engine.is_active.return_value = True
            mock_engine.get_user_context.return_value = Mock(user_id=user_id)
            factory._active_engines[f"engine-{i}"] = mock_engine
        
        # Execute & Verify
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            await factory._enforce_user_engine_limits(user_id)
        
        assert f"User {user_id} has reached maximum engine limit" in str(exc_info.value)
        assert f"({factory._max_engines_per_user}/{factory._max_engines_per_user})" in str(exc_info.value)
        assert factory._factory_metrics['user_limit_rejections'] == 1

    @pytest.mark.unit
    async def test_user_isolation_different_users_separate_limits(self, factory):
        """Test that different users have separate engine limits (critical isolation)."""
        # Setup: User 1 has max engines, User 2 has none
        user1_id = "user-1"
        user2_id = "user-2"
        
        # Fill user 1's limit
        for i in range(factory._max_engines_per_user):
            mock_engine = Mock()
            mock_engine.is_active.return_value = True
            mock_engine.get_user_context.return_value = Mock(user_id=user1_id)
            factory._active_engines[f"user1-engine-{i}"] = mock_engine
        
        # Verify user 1 is at limit
        with pytest.raises(ExecutionEngineFactoryError):
            await factory._enforce_user_engine_limits(user1_id)
        
        # Verify user 2 can still create engines (complete isolation)
        await factory._enforce_user_engine_limits(user2_id)  # Should not raise
        
        assert factory._factory_metrics['user_limit_rejections'] == 1

    @pytest.mark.unit
    async def test_user_isolation_inactive_engines_not_counted(self, factory):
        """Test that inactive engines don't count towards user limits."""
        user_id = "test-user"
        
        # Create inactive engines (should not count)
        for i in range(factory._max_engines_per_user + 1):
            mock_engine = Mock()
            mock_engine.is_active.return_value = False  # Inactive
            mock_engine.get_user_context.return_value = Mock(user_id=user_id)
            factory._active_engines[f"inactive-engine-{i}"] = mock_engine
        
        # Should not raise - inactive engines don't count
        await factory._enforce_user_engine_limits(user_id)
        assert factory._factory_metrics['user_limit_rejections'] == 0


class TestWebSocketEmitterCreation(AsyncTestCase):
    """Test WebSocket emitter creation with validated bridge."""
    
    @pytest.fixture
    def factory(self):
        """Create factory with WebSocket bridge."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)
    
    @pytest.fixture
    def user_context(self):
        """Create user context for testing."""
        return UserExecutionContext.from_request_supervisor(
            user_id="test-user",
            thread_id="test-thread", 
            run_id="test-run",
            metadata={"source": "test"}
        )

    @pytest.mark.unit
    async def test_create_user_websocket_emitter_success(self, factory, user_context):
        """Test successful WebSocket emitter creation."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
            mock_emitter = Mock()
            mock_emitter_class.return_value = mock_emitter
            
            # Execute
            result = await factory._create_user_websocket_emitter(user_context, Mock())
            
            # Verify
            assert result is mock_emitter
            mock_emitter_class.assert_called_once_with(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                websocket_bridge=factory._websocket_bridge
            )

    @pytest.mark.unit
    async def test_create_user_websocket_emitter_failure(self, factory, user_context):
        """Test WebSocket emitter creation failure handling."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
            mock_emitter_class.side_effect = Exception("Emitter creation failed")
            
            # Execute & Verify
            with pytest.raises(ExecutionEngineFactoryError) as exc_info:
                await factory._create_user_websocket_emitter(user_context, Mock())
            
            assert "WebSocket emitter creation failed" in str(exc_info.value)


class TestUserExecutionScope(AsyncTestCase):
    """Test user execution scope context manager."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)
    
    @pytest.fixture
    def user_context(self):
        """Create user context."""
        return UserExecutionContext.from_request_supervisor(
            user_id="scope-user",
            thread_id="scope-thread",
            run_id="scope-run", 
            metadata={"source": "test"}
        )

    @pytest.mark.unit
    async def test_user_execution_scope_success(self, factory, user_context):
        """Test user execution scope context manager success path."""
        mock_engine = Mock()
        mock_engine.engine_id = "scope-engine-123"
        
        with patch.object(factory, 'create_for_user') as mock_create:
            mock_create.return_value = mock_engine
            
            with patch.object(factory, 'cleanup_engine') as mock_cleanup:
                # Execute
                async with factory.user_execution_scope(user_context) as engine:
                    assert engine is mock_engine
                
                # Verify cleanup called
                mock_cleanup.assert_called_once_with(mock_engine)

    @pytest.mark.unit
    async def test_user_execution_scope_exception_still_cleans_up(self, factory, user_context):
        """Test user execution scope cleans up even when exception occurs."""
        mock_engine = Mock()
        mock_engine.engine_id = "scope-engine-123"
        
        with patch.object(factory, 'create_for_user') as mock_create:
            mock_create.return_value = mock_engine
            
            with patch.object(factory, 'cleanup_engine') as mock_cleanup:
                # Execute with exception
                with pytest.raises(ValueError):
                    async with factory.user_execution_scope(user_context) as engine:
                        raise ValueError("Test exception")
                
                # Verify cleanup still called
                mock_cleanup.assert_called_once_with(mock_engine)

    @pytest.mark.unit
    async def test_user_execution_scope_create_failure(self, factory, user_context):
        """Test user execution scope handles create failure."""
        with patch.object(factory, 'create_for_user') as mock_create:
            mock_create.side_effect = ExecutionEngineFactoryError("Create failed")
            
            # Execute & Verify
            with pytest.raises(ExecutionEngineFactoryError):
                async with factory.user_execution_scope(user_context) as engine:
                    pass  # Should not reach here

    @pytest.mark.unit 
    async def test_user_execution_scope_cleanup_error_logged(self, factory, user_context):
        """Test user execution scope handles cleanup errors gracefully."""
        mock_engine = Mock()
        mock_engine.engine_id = "cleanup-error-engine"
        
        with patch.object(factory, 'create_for_user') as mock_create:
            mock_create.return_value = mock_engine
            
            with patch.object(factory, 'cleanup_engine') as mock_cleanup:
                mock_cleanup.side_effect = Exception("Cleanup error")
                
                # Should not raise - cleanup errors are logged
                async with factory.user_execution_scope(user_context) as engine:
                    assert engine is mock_engine


class TestEngineCleanup(AsyncTestCase):
    """Test engine cleanup and lifecycle management."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for cleanup testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)

    @pytest.mark.unit
    async def test_cleanup_engine_success(self, factory):
        """Test successful engine cleanup."""
        # Setup
        mock_engine = Mock()
        mock_engine.engine_id = "cleanup-engine-123"
        mock_engine.cleanup = AsyncMock()
        engine_key = "test-engine-key"
        factory._active_engines[engine_key] = mock_engine
        
        initial_created = factory._factory_metrics['total_engines_created'] = 5
        
        # Execute
        await factory.cleanup_engine(mock_engine)
        
        # Verify
        mock_engine.cleanup.assert_called_once()
        assert engine_key not in factory._active_engines
        assert factory._factory_metrics['total_engines_cleaned'] == 1
        assert factory._factory_metrics['active_engines_count'] == 0

    @pytest.mark.unit
    async def test_cleanup_engine_not_found(self, factory):
        """Test cleanup of engine not in active engines."""
        mock_engine = Mock()
        mock_engine.engine_id = "unknown-engine"
        
        # Execute (should not raise)
        await factory.cleanup_engine(mock_engine)
        
        # Verify no changes
        assert factory._factory_metrics['total_engines_cleaned'] == 0
        assert factory._factory_metrics['cleanup_errors'] == 0

    @pytest.mark.unit
    async def test_cleanup_engine_none_input(self, factory):
        """Test cleanup with None engine input."""
        # Execute (should not raise)
        await factory.cleanup_engine(None)
        
        # Verify no changes
        assert factory._factory_metrics['total_engines_cleaned'] == 0

    @pytest.mark.unit
    async def test_cleanup_engine_cleanup_error(self, factory):
        """Test cleanup handles engine cleanup errors."""
        # Setup
        mock_engine = Mock()
        mock_engine.engine_id = "error-engine-123"
        mock_engine.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        engine_key = "error-engine-key"
        factory._active_engines[engine_key] = mock_engine
        
        # Execute (should not raise)
        await factory.cleanup_engine(mock_engine)
        
        # Verify error metrics
        assert factory._factory_metrics['cleanup_errors'] == 1
        # Engine should still be removed from registry despite cleanup error
        assert engine_key not in factory._active_engines


class TestBackgroundCleanup(AsyncTestCase):
    """Test background cleanup loop and inactive engine cleanup."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for cleanup testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)

    @pytest.mark.unit
    async def test_cleanup_inactive_engines_inactive_engine(self, factory):
        """Test cleanup of inactive engines."""
        # Setup inactive engine
        mock_engine = Mock()
        mock_engine.engine_id = "inactive-engine"
        mock_engine.is_active.return_value = False
        mock_engine.cleanup = AsyncMock()
        engine_key = "inactive-key"
        factory._active_engines[engine_key] = mock_engine
        
        # Execute
        await factory._cleanup_inactive_engines()
        
        # Verify
        mock_engine.cleanup.assert_called_once()
        assert engine_key not in factory._active_engines
        assert factory._factory_metrics['total_engines_cleaned'] == 1

    @pytest.mark.unit
    async def test_cleanup_inactive_engines_timeout_engine(self, factory):
        """Test cleanup of timed-out engines."""
        # Setup timed-out engine
        mock_engine = Mock()
        mock_engine.engine_id = "timeout-engine"
        mock_engine.is_active.return_value = True
        mock_engine.cleanup = AsyncMock()
        
        # Set created_at to be older than timeout
        old_time = datetime.now(timezone.utc)
        old_timestamp = old_time.timestamp() - factory._engine_timeout_seconds - 100
        old_datetime = datetime.fromtimestamp(old_timestamp, timezone.utc)
        mock_engine.created_at = old_datetime
        
        engine_key = "timeout-key"
        factory._active_engines[engine_key] = mock_engine
        
        # Execute
        await factory._cleanup_inactive_engines()
        
        # Verify
        mock_engine.cleanup.assert_called_once()
        assert engine_key not in factory._active_engines
        assert factory._factory_metrics['timeout_cleanups'] == 1

    @pytest.mark.unit
    async def test_cleanup_inactive_engines_active_engine_kept(self, factory):
        """Test that active engines within timeout are kept."""
        # Setup active engine
        mock_engine = Mock()
        mock_engine.engine_id = "active-engine"
        mock_engine.is_active.return_value = True
        mock_engine.created_at = datetime.now(timezone.utc)  # Recent
        engine_key = "active-key"
        factory._active_engines[engine_key] = mock_engine
        
        # Execute
        await factory._cleanup_inactive_engines()
        
        # Verify engine kept
        assert engine_key in factory._active_engines
        assert factory._factory_metrics['total_engines_cleaned'] == 0

    @pytest.mark.unit
    async def test_cleanup_inactive_engines_error_handling(self, factory):
        """Test cleanup handles errors during engine inspection."""
        # Setup engine that throws error during is_active check
        mock_engine = Mock()
        mock_engine.engine_id = "error-engine"
        mock_engine.is_active.side_effect = Exception("Check error")
        mock_engine.cleanup = AsyncMock()
        engine_key = "error-key"
        factory._active_engines[engine_key] = mock_engine
        
        # Execute
        await factory._cleanup_inactive_engines()
        
        # Verify error engine is cleaned up
        mock_engine.cleanup.assert_called_once()
        assert engine_key not in factory._active_engines

    @pytest.mark.unit
    async def test_cleanup_inactive_engines_no_engines(self, factory):
        """Test cleanup with no engines."""
        # Execute (should not raise)
        await factory._cleanup_inactive_engines()
        
        # Verify no changes
        assert factory._factory_metrics['total_engines_cleaned'] == 0


class TestFactoryMetrics(AsyncTestCase):
    """Test factory metrics and monitoring functionality."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for metrics testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)

    @pytest.mark.unit
    def test_get_factory_metrics_initial_state(self, factory):
        """Test factory metrics in initial state."""
        metrics = factory.get_factory_metrics()
        
        # Verify initial metrics
        assert metrics['total_engines_created'] == 0
        assert metrics['total_engines_cleaned'] == 0
        assert metrics['active_engines_count'] == 0
        assert metrics['creation_errors'] == 0
        assert metrics['cleanup_errors'] == 0
        assert metrics['timeout_cleanups'] == 0
        assert metrics['user_limit_rejections'] == 0
        
        # Verify configuration included
        assert metrics['max_engines_per_user'] == 2
        assert metrics['engine_timeout_seconds'] == 300
        assert metrics['cleanup_interval'] == 60
        assert metrics['active_engine_keys'] == []
        assert metrics['cleanup_task_running'] is False
        assert 'timestamp' in metrics

    @pytest.mark.unit
    def test_get_factory_metrics_with_active_engines(self, factory):
        """Test factory metrics with active engines."""
        # Setup active engines
        mock_engine1 = Mock()
        mock_engine2 = Mock()
        factory._active_engines['engine-1'] = mock_engine1
        factory._active_engines['engine-2'] = mock_engine2
        factory._factory_metrics['active_engines_count'] = 2
        
        # Execute
        metrics = factory.get_factory_metrics()
        
        # Verify
        assert metrics['active_engines_count'] == 2
        assert set(metrics['active_engine_keys']) == {'engine-1', 'engine-2'}

    @pytest.mark.unit
    def test_get_active_engines_summary_empty(self, factory):
        """Test active engines summary with no engines."""
        summary = factory.get_active_engines_summary()
        
        assert summary['total_active_engines'] == 0
        assert summary['engines'] == {}
        assert 'summary_timestamp' in summary

    @pytest.mark.unit
    def test_get_active_engines_summary_with_engines(self, factory):
        """Test active engines summary with active engines."""
        # Setup mock engines
        mock_engine = Mock()
        mock_engine.engine_id = "test-engine-123"
        mock_engine.is_active.return_value = True
        mock_engine.created_at = datetime.now(timezone.utc)
        mock_engine.active_runs = ["run1", "run2"]
        
        # Setup user context
        mock_context = Mock()
        mock_context.user_id = "test-user"
        mock_context.run_id = "test-run"
        mock_engine.get_user_context.return_value = mock_context
        mock_engine.get_user_execution_stats.return_value = {"executions": 5}
        
        factory._active_engines['engine-key'] = mock_engine
        
        # Execute
        summary = factory.get_active_engines_summary()
        
        # Verify
        assert summary['total_active_engines'] == 1
        assert 'engine-key' in summary['engines']
        engine_summary = summary['engines']['engine-key']
        assert engine_summary['engine_id'] == "test-engine-123"
        assert engine_summary['user_id'] == "test-user"
        assert engine_summary['run_id'] == "test-run"
        assert engine_summary['is_active'] is True
        assert engine_summary['active_runs'] == 2
        assert engine_summary['stats'] == {"executions": 5}

    @pytest.mark.unit
    def test_get_active_engines_summary_with_error(self, factory):
        """Test active engines summary handles engine errors."""
        # Setup engine that throws error
        mock_engine = Mock()
        mock_engine.engine_id = "error-engine"
        mock_engine.get_user_context.side_effect = Exception("Context error")
        
        factory._active_engines['error-key'] = mock_engine
        
        # Execute
        summary = factory.get_active_engines_summary()
        
        # Verify error handled
        assert summary['total_active_engines'] == 1
        assert 'error-key' in summary['engines']
        assert 'error' in summary['engines']['error-key']

    @pytest.mark.unit
    def test_get_active_contexts_empty(self, factory):
        """Test get active contexts with no engines."""
        contexts = factory.get_active_contexts()
        assert contexts == {}

    @pytest.mark.unit
    def test_get_active_contexts_multiple_users(self, factory):
        """Test get active contexts with multiple users."""
        # Setup engines for different users
        mock_engine1 = Mock()
        mock_engine1.get_user_context.return_value = Mock(user_id="user-1")
        
        mock_engine2 = Mock() 
        mock_engine2.get_user_context.return_value = Mock(user_id="user-1")
        
        mock_engine3 = Mock()
        mock_engine3.get_user_context.return_value = Mock(user_id="user-2")
        
        factory._active_engines['eng1'] = mock_engine1
        factory._active_engines['eng2'] = mock_engine2
        factory._active_engines['eng3'] = mock_engine3
        
        # Execute
        contexts = factory.get_active_contexts()
        
        # Verify
        assert contexts['user-1'] == 2
        assert contexts['user-2'] == 1


class TestFactoryShutdown(AsyncTestCase):
    """Test factory shutdown and resource cleanup."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for shutdown testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)

    @pytest.mark.unit
    async def test_shutdown_no_active_engines(self, factory):
        """Test shutdown with no active engines."""
        # Execute
        await factory.shutdown()
        
        # Verify state cleared
        assert len(factory._active_engines) == 0
        assert factory._shutdown_event.is_set()
        assert factory._factory_metrics['active_engines_count'] == 0

    @pytest.mark.unit
    async def test_shutdown_with_active_engines(self, factory):
        """Test shutdown cleans up active engines."""
        # Setup active engines
        mock_engine1 = Mock()
        mock_engine1.cleanup = AsyncMock()
        mock_engine2 = Mock()
        mock_engine2.cleanup = AsyncMock()
        
        factory._active_engines['eng1'] = mock_engine1
        factory._active_engines['eng2'] = mock_engine2
        
        # Execute
        await factory.shutdown()
        
        # Verify all engines cleaned up
        mock_engine1.cleanup.assert_called_once()
        mock_engine2.cleanup.assert_called_once()
        assert len(factory._active_engines) == 0
        assert factory._factory_metrics['active_engines_count'] == 0

    @pytest.mark.unit
    async def test_shutdown_with_cleanup_task(self, factory):
        """Test shutdown stops cleanup task."""
        # Setup cleanup task - Create a proper Task-like mock
        async def dummy_task():
            await asyncio.sleep(0)
        
        mock_task = asyncio.create_task(dummy_task())
        factory._cleanup_task = mock_task
        
        # Execute
        await factory.shutdown()
        
        # Verify shutdown event set
        assert factory._shutdown_event.is_set()
        
        # Cleanup the created task
        mock_task.cancel()
        try:
            await mock_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.unit
    async def test_shutdown_handles_engine_cleanup_errors(self, factory):
        """Test shutdown handles individual engine cleanup errors."""
        # Setup engine that fails cleanup
        mock_engine = Mock()
        mock_engine.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        factory._active_engines['error-engine'] = mock_engine
        
        # Execute (should not raise)
        await factory.shutdown()
        
        # Verify shutdown completed despite error
        assert len(factory._active_engines) == 0
        assert factory._shutdown_event.is_set()

    @pytest.mark.unit
    async def test_cleanup_user_context_success(self, factory):
        """Test cleanup all engines for specific user."""
        # Setup engines for different users
        user1_engine1 = Mock()
        user1_engine1.cleanup = AsyncMock()
        user1_engine1.get_user_context.return_value = Mock(user_id="user-1")
        
        user1_engine2 = Mock()
        user1_engine2.cleanup = AsyncMock()  
        user1_engine2.get_user_context.return_value = Mock(user_id="user-1")
        
        user2_engine = Mock()
        user2_engine.get_user_context.return_value = Mock(user_id="user-2")
        
        factory._active_engines['u1e1'] = user1_engine1
        factory._active_engines['u1e2'] = user1_engine2
        factory._active_engines['u2e1'] = user2_engine
        
        # Execute
        result = await factory.cleanup_user_context("user-1")
        
        # Verify only user-1 engines cleaned
        assert result is True
        user1_engine1.cleanup.assert_called_once()
        user1_engine2.cleanup.assert_called_once()
        # user2_engine should not have cleanup called
        assert not hasattr(user2_engine, 'cleanup') or not user2_engine.cleanup.called

    @pytest.mark.unit
    async def test_cleanup_user_context_error_handling(self, factory):
        """Test cleanup user context handles errors gracefully."""
        # Setup engine that fails cleanup
        mock_engine = Mock()
        mock_engine.get_user_context.side_effect = Exception("Context error")
        factory._active_engines['error-engine'] = mock_engine
        
        # Execute
        result = await factory.cleanup_user_context("test-user")
        
        # Verify returns False on error
        assert result is False


class TestFactorySingleton(AsyncTestCase):
    """Test factory singleton pattern and global access."""
    
    @pytest.mark.unit
    async def test_get_execution_engine_factory_not_configured(self):
        """Test get factory fails when not configured."""
        # Clear singleton
        from netra_backend.app.agents.supervisor.execution_engine_factory import _factory_instance, _factory_lock
        async with _factory_lock:
            import netra_backend.app.agents.supervisor.execution_engine_factory as factory_module
            factory_module._factory_instance = None
        
        # Execute & Verify
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            await get_execution_engine_factory()
        
        assert "ExecutionEngineFactory not configured during startup" in str(exc_info.value)
        assert "WebSocket bridge for proper agent execution" in str(exc_info.value)

    @pytest.mark.unit 
    async def test_configure_execution_engine_factory_success(self):
        """Test factory configuration success."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        db_manager = Mock()
        redis_manager = Mock()
        
        # Execute
        factory = await configure_execution_engine_factory(
            websocket_bridge=websocket_bridge,
            database_session_manager=db_manager,
            redis_manager=redis_manager
        )
        
        # Verify
        assert factory._websocket_bridge is websocket_bridge
        assert factory._database_session_manager is db_manager
        assert factory._redis_manager is redis_manager
        
        # Verify can be retrieved
        retrieved_factory = await get_execution_engine_factory()
        assert retrieved_factory is factory

    @pytest.mark.unit
    async def test_configure_execution_engine_factory_reconfigure(self):
        """Test factory can be reconfigured."""
        # First configuration
        websocket_bridge1 = Mock(spec=AgentWebSocketBridge)
        factory1 = await configure_execution_engine_factory(websocket_bridge=websocket_bridge1)
        
        # Second configuration
        websocket_bridge2 = Mock(spec=AgentWebSocketBridge)
        factory2 = await configure_execution_engine_factory(websocket_bridge=websocket_bridge2)
        
        # Verify new factory created
        assert factory2 is not factory1
        assert factory2._websocket_bridge is websocket_bridge2
        
        # Verify new factory is returned
        retrieved_factory = await get_execution_engine_factory()
        assert retrieved_factory is factory2

    @pytest.mark.unit
    async def test_user_execution_engine_context_manager(self):
        """Test module-level context manager function."""
        # Setup configured factory
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        await configure_execution_engine_factory(websocket_bridge=websocket_bridge)
        
        # Setup user context
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="ctx-user",
            thread_id="ctx-thread",
            run_id="ctx-run",
            metadata={"source": "test"}
        )
        
        mock_engine = Mock()
        mock_engine.engine_id = "ctx-engine"
        
        # Mock the factory methods
        factory = await get_execution_engine_factory()
        with patch.object(factory, 'user_execution_scope') as mock_scope:
            async def mock_context_manager():
                yield mock_engine
            mock_scope.return_value.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_scope.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Execute
            async with user_execution_engine(user_context) as engine:
                assert engine is mock_engine
            
            # Verify factory method called
            mock_scope.assert_called_once_with(user_context)


class TestFactoryAliasMethodsCompatibility(AsyncTestCase):
    """Test factory alias methods for backward compatibility."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for compatibility testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)
    
    @pytest.fixture
    def user_context(self):
        """Create user context."""
        return UserExecutionContext.from_request_supervisor(
            user_id="compat-user",
            thread_id="compat-thread", 
            run_id="compat-run",
            metadata={"source": "test"}
        )

    @pytest.mark.unit
    async def test_create_execution_engine_alias(self, factory, user_context):
        """Test create_execution_engine is alias for create_for_user."""
        mock_engine = Mock()
        
        with patch.object(factory, 'create_for_user') as mock_create:
            mock_create.return_value = mock_engine
            
            # Execute
            result = await factory.create_execution_engine(user_context)
            
            # Verify
            assert result is mock_engine
            mock_create.assert_called_once_with(user_context)

    @pytest.mark.unit
    async def test_cleanup_all_contexts_alias(self, factory):
        """Test cleanup_all_contexts is alias for shutdown."""
        with patch.object(factory, 'shutdown') as mock_shutdown:
            # Execute
            await factory.cleanup_all_contexts()
            
            # Verify
            mock_shutdown.assert_called_once()


class TestFactoryPerformanceBenchmarks(AsyncTestCase):
    """Test factory performance benchmarks and resource usage."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for performance testing."""
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        return ExecutionEngineFactory(websocket_bridge=websocket_bridge)

    @pytest.mark.unit
    def test_factory_initialization_performance(self):
        """Test factory initialization is fast (< 10ms)."""
        import time
        
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        start_time = time.time()
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        end_time = time.time()
        
        initialization_time_ms = (end_time - start_time) * 1000
        assert initialization_time_ms < 10, f"Factory initialization took {initialization_time_ms:.2f}ms, should be < 10ms"

    @pytest.mark.unit
    async def test_user_engine_creation_performance(self, factory):
        """Test user engine creation performance (< 100ms)."""
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="perf-user",
            thread_id="perf-thread",
            run_id="perf-run", 
            metadata={"source": "test"}
        )
        
        mock_engine = Mock()
        mock_engine.engine_id = "perf-engine"
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = Mock()
            mock_get_factory.return_value = mock_agent_factory
            
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
                mock_emitter = Mock()
                mock_emitter_class.return_value = mock_emitter
                
                with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_engine_class:
                    mock_engine_class.return_value = mock_engine
                    
                    # Measure performance
                    start_time = time.time()
                    result = await factory.create_for_user(user_context)
                    end_time = time.time()
                    
                    creation_time_ms = (end_time - start_time) * 1000
                    assert creation_time_ms < 100, f"Engine creation took {creation_time_ms:.2f}ms, should be < 100ms"
                    assert result is mock_engine

    @pytest.mark.unit
    async def test_cleanup_performance(self, factory):
        """Test engine cleanup performance (< 50ms)."""
        mock_engine = Mock()
        mock_engine.engine_id = "cleanup-perf-engine"
        mock_engine.cleanup = AsyncMock()
        
        factory._active_engines['perf-key'] = mock_engine
        
        # Measure performance
        start_time = time.time()
        await factory.cleanup_engine(mock_engine)
        end_time = time.time()
        
        cleanup_time_ms = (end_time - start_time) * 1000
        assert cleanup_time_ms < 50, f"Engine cleanup took {cleanup_time_ms:.2f}ms, should be < 50ms"

    @pytest.mark.unit
    def test_metrics_collection_performance(self, factory):
        """Test metrics collection is fast (< 5ms)."""
        # Add some engines
        for i in range(10):
            mock_engine = Mock()
            mock_engine.engine_id = f"metrics-engine-{i}"
            mock_engine.is_active.return_value = True
            mock_engine.created_at = datetime.now(timezone.utc)
            mock_engine.active_runs = []
            mock_engine.get_user_context.return_value = Mock(user_id=f"user-{i}", run_id=f"run-{i}")
            mock_engine.get_user_execution_stats.return_value = {"executions": i}
            factory._active_engines[f"key-{i}"] = mock_engine
        
        # Measure performance
        start_time = time.time()
        metrics = factory.get_factory_metrics()
        summary = factory.get_active_engines_summary()
        contexts = factory.get_active_contexts()
        end_time = time.time()
        
        metrics_time_ms = (end_time - start_time) * 1000
        assert metrics_time_ms < 5, f"Metrics collection took {metrics_time_ms:.2f}ms, should be < 5ms"
        
        # Verify data collected
        assert len(metrics['active_engine_keys']) == 10
        assert summary['total_active_engines'] == 10
        assert len(contexts) == 10


# Run all tests when file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])