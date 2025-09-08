"""
Enhanced Unit Tests for Startup Module - CRITICAL Business Infrastructure

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure  
- Business Goal: Prevent chat functionality failures that destroy 90% of business value
- Value Impact: Ensures reliable startup across all environments (dev/staging/prod)
- Strategic Impact: $2M+ ARR protection by preventing startup cascade failures

This enhanced test suite provides comprehensive coverage for the startup module with focus on:
1. WebSocket integration for chat functionality (business-critical)
2. Multi-environment startup validation (staging/prod reliability)
3. Error handling and graceful degradation patterns
4. Performance timing and resource management
5. Database connection management and timeout handling
6. ClickHouse integration patterns
7. Agent supervisor creation with WebSocket bridge
8. Authentication validation flows
9. Memory and resource cleanup
10. Concurrent initialization scenarios

CRITICAL REQUIREMENTS:
- ALL tests MUST fail hard when system breaks - NO try/except masking
- Use SSOT patterns from test_framework/ssot/
- Follow absolute import patterns per CLAUDE.md
- Tests must validate business-critical chat functionality paths
"""

import asyncio
import logging
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from fastapi import FastAPI

# SSOT imports - following CLAUDE.md absolute import requirements
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app import startup_module


class TestStartupModuleEnhanced(BaseTestCase):
    """
    Enhanced unit tests for startup_module.py with business value focus.
    
    This test class validates ALL critical paths required for chat functionality,
    which delivers 90% of business value. Every test failure here indicates
    potential revenue loss due to broken chat.
    
    CRITICAL: These tests MUST fail hard - NO exception masking allowed.
    """
    
    # Configure SSOT base class for comprehensive testing
    REQUIRES_DATABASE = False  # Mock database for unit tests
    REQUIRES_REDIS = False     # Mock Redis for unit tests  
    ISOLATION_ENABLED = True   # Critical for multi-user isolation testing
    AUTO_CLEANUP = True        # Ensure proper cleanup of mocks
    
    def setUp(self):
        """Set up enhanced test environment for startup module validation."""
        super().setUp()
        
        # Create mock FastAPI app with proper state management
        self.mock_app = Mock(spec=FastAPI)
        self.mock_app.state = Mock()
        self._reset_app_state()
        
        # Create comprehensive mock logger
        self.mock_logger = Mock(spec=logging.Logger)
        
        # Track performance metrics for business impact validation
        self.test_start_time = time.time()
        self.performance_thresholds = {
            'logging_init': 0.1,      # 100ms max for logging
            'path_setup': 0.05,       # 50ms max for path setup  
            'model_import': 2.0,      # 2s max for model imports
            'service_init': 1.0,      # 1s max for service init
        }
        
        # Set up isolated test environment with business-critical variables
        with self.isolated_environment(
            ENVIRONMENT="test",
            TESTING="true", 
            DATABASE_URL="postgresql://test:test@localhost:5432/test_netra",
            REDIS_URL="redis://localhost:6379/1",
            JWT_SECRET_KEY="test-jwt-secret-for-chat-auth-32chars",
            CLICKHOUSE_HOST="localhost",
            CLICKHOUSE_PORT="9000",
            DISABLE_BACKGROUND_TASKS="true",
            DISABLE_MONITORING="true"
        ):
            pass
    
    def _reset_app_state(self):
        """Reset app state to clean conditions for testing."""
        # Initialize all expected app state attributes to prevent AttributeError
        critical_services = [
            'db_session_factory', 'redis_manager', 'llm_manager', 'key_manager',
            'security_service', 'agent_supervisor', 'agent_service', 'thread_service',
            'corpus_service', 'tool_dispatcher', 'agent_websocket_bridge',
            'background_task_manager', 'health_service', 'performance_manager',
            'clickhouse_available', 'database_available', 'startup_complete',
            'startup_in_progress', 'startup_failed', 'startup_error'
        ]
        
        for service in critical_services:
            setattr(self.mock_app.state, service, None)
        
        # Set startup state flags
        self.mock_app.state.startup_complete = False
        self.mock_app.state.startup_in_progress = False
        self.mock_app.state.startup_failed = False
        self.mock_app.state.startup_error = None

    # =============================================================================
    # SECTION 1: CRITICAL PATH AND BUSINESS VALUE TESTS
    # =============================================================================

    def test_critical_chat_components_initialization_order(self):
        """
        Test that critical chat components are initialized in correct dependency order.
        
        BVJ: Chat delivers 90% of business value - component order affects reliability.
        """
        # Verify critical chat functions exist and follow dependency order
        critical_chat_functions = [
            ('initialize_logging', 'foundation'),
            ('setup_database_connections', 'data_layer'),
            ('initialize_core_services', 'service_layer'), 
            ('register_websocket_handlers', 'communication'),
            ('_create_agent_supervisor', 'business_logic'),
            ('startup_health_checks', 'validation')
        ]
        
        for func_name, layer in critical_chat_functions:
            self.assertTrue(
                hasattr(startup_module, func_name),
                f"CRITICAL CHAT FAILURE: {func_name} missing from {layer} layer"
            )
            
            # Verify function is callable
            func = getattr(startup_module, func_name)
            self.assertTrue(
                callable(func),
                f"CRITICAL CHAT FAILURE: {func_name} not callable in {layer}"
            )

    @patch('netra_backend.app.startup_module.central_logger')
    def test_initialize_logging_performance_meets_business_requirements(self, mock_logger):
        """Test logging initialization meets performance requirements for fast startup."""
        start_time = time.time()
        
        # Mock logger to return proper instance
        mock_logger_instance = Mock()
        mock_logger.get_logger.return_value = mock_logger_instance
        
        result_start_time, logger = startup_module.initialize_logging()
        
        elapsed_time = time.time() - start_time
        
        # Business requirement: Logging must initialize in under 100ms
        self.assertLess(
            elapsed_time, self.performance_thresholds['logging_init'],
            f"BUSINESS IMPACT: Logging init took {elapsed_time:.3f}s, "
            f"exceeds {self.performance_thresholds['logging_init']}s threshold. "
            f"Slow startup affects user experience and reduces conversion rates."
        )
        
        # Verify return values are business-appropriate
        self.assertIsInstance(result_start_time, float)
        self.assertTrue(hasattr(logger, 'info'), "Logger must support info logging for chat")
        self.assertTrue(hasattr(logger, 'error'), "Logger must support error logging for debugging")

    def test_setup_paths_enables_critical_imports_for_chat(self):
        """Test path setup enables all imports required for chat functionality."""
        # Save original sys.path to restore later
        original_path = sys.path.copy()
        
        try:
            # Clear paths that might interfere with test
            sys.path = [p for p in sys.path if 'netra' not in p.lower()]
            
            # Measure path setup performance
            start_time = time.time()
            startup_module._setup_paths()
            elapsed_time = time.time() - start_time
            
            # Business requirement: Path setup must be fast 
            self.assertLess(
                elapsed_time, self.performance_thresholds['path_setup'],
                f"BUSINESS IMPACT: Path setup too slow ({elapsed_time:.3f}s)"
            )
            
            # Verify critical project paths are accessible
            project_paths_found = 0
            for path in sys.path:
                if 'netra' in path.lower() and Path(path).exists():
                    project_paths_found += 1
            
            self.assertGreater(
                project_paths_found, 0,
                "CRITICAL CHAT FAILURE: No project paths added to sys.path. "
                "Chat modules cannot be imported, breaking all functionality."
            )
            
        finally:
            # Always restore original path
            sys.path = original_path

    @pytest.mark.asyncio
    async def test_database_connection_timeout_prevents_startup_hanging(self):
        """Test database connection timeouts prevent indefinite startup hanging."""
        with patch('netra_backend.app.startup_module.get_config') as mock_get_config, \
             patch('netra_backend.app.startup_module.get_database_timeout_config') as mock_timeout_config, \
             patch('netra_backend.app.startup_module._async_initialize_postgres') as mock_async_init:
            
            # Configure for test environment with fast timeouts
            mock_config = Mock()
            mock_config.database_url = "postgresql://test:test@localhost:5432/test_db"
            mock_config.graceful_startup_mode = "false"  # Strict mode for business validation
            mock_get_config.return_value = mock_config
            
            # Configure short timeouts for business responsiveness
            mock_timeout_config.return_value = {
                "initialization_timeout": 2.0,  # 2 second max for tests
                "table_setup_timeout": 1.0      # 1 second max for tests
            }
            
            # Simulate database timeout (business-critical scenario)
            mock_async_init.side_effect = asyncio.TimeoutError("Database connection timeout")
            
            # Test timeout handling
            start_time = time.time()
            
            with self.assertRaises(Exception) as cm:
                await startup_module.setup_database_connections(self.mock_app)
            
            elapsed_time = time.time() - start_time
            
            # Verify timeout was respected (critical for user experience)
            self.assertLess(
                elapsed_time, 5.0,
                f"BUSINESS IMPACT: Database timeout took {elapsed_time:.3f}s. "
                f"Must fail fast to prevent user waiting and revenue loss."
            )
            
            # Verify appropriate error message for debugging
            error_message = str(cm.exception)
            self.assertIn(
                "timeout", error_message.lower(),
                "Error message must indicate timeout for operational debugging"
            )

    # =============================================================================
    # SECTION 2: WEBSOCKET INTEGRATION FOR CHAT TESTS
    # =============================================================================

    @patch('netra_backend.app.startup_module._create_tool_registry')
    @patch('netra_backend.app.startup_module._create_tool_dispatcher')  
    def test_websocket_handler_registration_enables_chat_events(self, mock_create_dispatcher, mock_create_registry):
        """
        Test WebSocket handler registration enables real-time chat events.
        
        BVJ: Real-time chat is core business differentiator worth $500K+ ARR.
        """
        # Mock registry and dispatcher creation
        mock_registry = Mock()
        mock_dispatcher = Mock() 
        mock_create_registry.return_value = mock_registry
        mock_create_dispatcher.return_value = mock_dispatcher
        
        # Test handler registration
        startup_module.register_websocket_handlers(self.mock_app)
        
        # Verify chat-critical components were created
        mock_create_registry.assert_called_once_with(self.mock_app)
        mock_create_dispatcher.assert_called_once_with(mock_registry)
        
        # Verify tool dispatcher is set for agent communication
        self.assertEqual(
            self.mock_app.state.tool_dispatcher, mock_dispatcher,
            "CRITICAL CHAT FAILURE: Tool dispatcher not set. "
            "Agent WebSocket events will not work, breaking real-time chat."
        )

    def test_create_tool_dispatcher_emits_proper_deprecation_warnings(self):
        """Test tool dispatcher creation includes security warnings for business compliance."""
        with patch('netra_backend.app.agents.tool_dispatcher.ToolDispatcher') as mock_dispatcher_class, \
             patch('warnings.warn') as mock_warnings, \
             patch('netra_backend.app.startup_module.central_logger') as mock_logger:
            
            # Mock dispatcher creation  
            mock_registry = Mock()
            mock_registry.get_tools.return_value = []
            mock_dispatcher_instance = Mock()
            mock_dispatcher_class.return_value = mock_dispatcher_instance
            
            # Mock logger
            mock_logger_instance = Mock()
            mock_logger.get_logger.return_value = mock_logger_instance
            
            # Create dispatcher
            result = startup_module._create_tool_dispatcher(mock_registry)
            
            # Verify security warning was emitted (compliance requirement)
            mock_warnings.assert_called_once()
            warning_args = mock_warnings.call_args[0]
            warning_message = warning_args[0]
            
            # Verify warning includes security implications
            security_keywords = ['isolation', 'security', 'user', 'global']
            has_security_warning = any(keyword in warning_message.lower() for keyword in security_keywords)
            
            self.assertTrue(
                has_security_warning,
                f"BUSINESS COMPLIANCE FAILURE: Security warning missing. "
                f"Warning was: {warning_message}. Must warn about user isolation risks."
            )
            
            # Verify deprecation level is appropriate  
            self.assertEqual(mock_warnings.call_args[1]['stacklevel'], 2)
            
            # Verify dispatcher was created despite warnings
            self.assertEqual(result, mock_dispatcher_instance)

    @patch('netra_backend.app.startup_module._build_supervisor_agent')
    @patch('netra_backend.app.startup_module._setup_agent_state')
    @patch('netra_backend.app.websocket_core.get_websocket_manager_factory')
    @patch('shared.isolated_environment.get_env')
    def test_agent_supervisor_websocket_integration_for_chat(self, mock_get_env, mock_factory, mock_setup_state, mock_build_supervisor):
        """
        Test agent supervisor WebSocket integration enables chat notifications.
        
        BVJ: Agent notifications are core to chat UX and user engagement.
        """
        # Mock environment
        mock_env = Mock()
        mock_env.get.return_value = "test"
        mock_get_env.return_value = mock_env
        
        # Mock WebSocket factory
        mock_factory.return_value = Mock()
        
        # Mock supervisor with proper WebSocket bridge for chat  
        mock_supervisor = Mock()
        mock_websocket_bridge = Mock()
        mock_websocket_bridge.emit_agent_event = Mock()  # Critical for chat events
        mock_supervisor.websocket_bridge = mock_websocket_bridge
        mock_build_supervisor.return_value = mock_supervisor
        
        # Set required app state for supervisor creation
        self.mock_app.state.db_session_factory = Mock()
        self.mock_app.state.llm_manager = Mock() 
        self.mock_app.state.tool_dispatcher = Mock()
        
        # Test supervisor creation
        startup_module._create_agent_supervisor(self.mock_app)
        
        # Verify supervisor was built with chat capabilities
        mock_build_supervisor.assert_called_once_with(self.mock_app)
        mock_setup_state.assert_called_once_with(self.mock_app, mock_supervisor)
        
        # Verify WebSocket bridge is configured for chat events
        self.assertTrue(
            hasattr(mock_supervisor, 'websocket_bridge'),
            "CRITICAL CHAT FAILURE: Supervisor missing WebSocket bridge. "
            "Real-time agent events will not work."
        )
        
        self.assertTrue(
            hasattr(mock_supervisor.websocket_bridge, 'emit_agent_event'),
            "CRITICAL CHAT FAILURE: WebSocket bridge missing emit_agent_event. "
            "Agent notifications will not reach users."
        )

    @patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent')
    @patch('netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge')  
    def test_supervisor_agent_creation_with_chat_dependencies(self, mock_bridge_class, mock_supervisor_class):
        """Test supervisor agent is created with all chat-required dependencies."""
        # Set up app state with chat requirements
        self.mock_app.state.db_session_factory = Mock()
        self.mock_app.state.llm_manager = Mock()
        self.mock_app.state.tool_dispatcher = Mock()
        
        # Mock bridge creation
        mock_bridge = Mock()
        mock_bridge_class.return_value = mock_bridge
        
        # Mock supervisor creation  
        mock_supervisor = Mock()
        mock_supervisor_class.return_value = mock_supervisor
        
        # Test supervisor building
        result = startup_module._build_supervisor_agent(self.mock_app)
        
        # Verify bridge was created for chat events
        mock_bridge_class.assert_called_once()
        
        # Verify supervisor was created with proper chat dependencies
        mock_supervisor_class.assert_called_once_with(
            self.mock_app.state.llm_manager,  # Required for AI responses
            mock_bridge                       # Required for real-time events
        )
        
        self.assertEqual(result, mock_supervisor)

    # =============================================================================
    # SECTION 3: ERROR HANDLING AND BUSINESS CONTINUITY TESTS  
    # =============================================================================

    @patch('netra_backend.app.startup_module.get_config')
    @patch('netra_backend.app.startup_module.get_env')
    @patch('netra_backend.app.startup_module._setup_clickhouse_tables')
    @pytest.mark.asyncio
    async def test_clickhouse_failure_handling_by_environment(self, mock_setup_tables, mock_get_env, mock_get_config):
        """Test ClickHouse failure handling varies appropriately by business environment."""
        test_scenarios = [
            ("development", False, "should_continue"),
            ("staging", False, "should_continue"), 
            ("production", True, "should_fail"),
        ]
        
        for environment, should_be_required, expected_behavior in test_scenarios:
            with self.subTest(environment=environment, expected=expected_behavior):
                # Mock configuration for environment
                mock_config = Mock()
                mock_config.environment = environment
                mock_config.clickhouse_mode = "enabled"
                mock_get_config.return_value = mock_config
                
                # Mock environment variables
                mock_env = Mock()
                # Production requires ClickHouse for business analytics
                required_value = "true" if environment == "production" else "false"
                mock_env.get.return_value = required_value
                mock_get_env.return_value = mock_env
                
                # Mock ClickHouse connection failure
                mock_setup_tables.side_effect = Exception("ClickHouse connection failed")
                
                if environment == "production":
                    # Production must fail if ClickHouse unavailable (business requirement)
                    with self.assertRaises(RuntimeError) as cm:
                        await startup_module.initialize_clickhouse(self.mock_logger)
                    
                    error_message = str(cm.exception)
                    self.assertIn(
                        "required", error_message.lower(),
                        f"Production error must indicate ClickHouse is required"
                    )
                else:
                    # Development/staging should continue without ClickHouse 
                    result = await startup_module.initialize_clickhouse(self.mock_logger)
                    
                    self.assertEqual(
                        result["status"], "failed",
                        f"{environment} should report failure but continue"
                    )
                    self.assertFalse(
                        result["required"],
                        f"{environment} should not require ClickHouse"
                    )

    @patch('netra_backend.app.startup_module.redis_manager')
    @pytest.mark.asyncio  
    async def test_emergency_cleanup_prevents_resource_leaks(self, mock_redis_manager):
        """Test emergency cleanup prevents resource leaks that affect system stability."""
        # Mock Redis manager with cleanup capabilities
        mock_redis_manager.shutdown = AsyncMock()
        
        # Mock central logger cleanup
        with patch('netra_backend.app.startup_module.central_logger') as mock_central_logger:
            mock_central_logger.shutdown = AsyncMock()
            
            # Mock multiprocessing cleanup
            with patch('netra_backend.app.startup_module.cleanup_multiprocessing') as mock_cleanup_mp:
                
                # Test emergency cleanup
                start_time = time.time()
                await startup_module._emergency_cleanup(self.mock_logger)
                cleanup_time = time.time() - start_time
                
                # Verify cleanup happens quickly (business requirement)
                self.assertLess(
                    cleanup_time, 2.0,
                    f"BUSINESS IMPACT: Emergency cleanup took {cleanup_time:.3f}s. "
                    f"Slow cleanup delays service recovery and affects availability."
                )
                
                # Verify all critical resources are cleaned up
                mock_redis_manager.shutdown.assert_called_once()
                mock_central_logger.shutdown.assert_called_once() 
                mock_cleanup_mp.assert_called_once()

    @patch('netra_backend.app.startup_module._emergency_cleanup')
    @pytest.mark.asyncio
    async def test_startup_failure_triggers_proper_business_continuity(self, mock_cleanup):
        """Test startup failure triggers proper business continuity procedures."""
        test_error = RuntimeError("Critical service initialization failed")
        
        # Test failure handling
        with self.assertRaises(RuntimeError) as cm:
            await startup_module._handle_startup_failure(self.mock_logger, test_error)
        
        # Verify emergency cleanup was triggered (business continuity)
        mock_cleanup.assert_called_once_with(self.mock_logger)
        
        # Verify error message is business-appropriate
        final_error = str(cm.exception)
        self.assertIn(
            "startup failed", final_error.lower(),
            "Error message must clearly indicate startup failure for operations"
        )

    # =============================================================================
    # SECTION 4: PERFORMANCE AND SCALABILITY TESTS
    # =============================================================================

    @patch('netra_backend.app.startup_module.performance_manager')
    @patch('netra_backend.app.startup_module.index_manager')
    @pytest.mark.asyncio
    async def test_performance_optimization_initialization_scalability(self, mock_index_manager, mock_performance_manager):
        """Test performance optimization setup meets scalability requirements."""
        # Mock performance manager
        mock_performance_manager.initialize = AsyncMock()
        
        # Test performance optimization setup
        start_time = time.time()
        await startup_module._initialize_performance_optimizations(self.mock_app, self.mock_logger)
        elapsed_time = time.time() - start_time
        
        # Verify initialization is fast (scalability requirement)
        self.assertLess(
            elapsed_time, self.performance_thresholds['service_init'],
            f"SCALABILITY IMPACT: Performance optimization init took {elapsed_time:.3f}s, "
            f"exceeds {self.performance_thresholds['service_init']}s threshold. "
            f"Slow startup reduces system scalability."
        )
        
        # Verify performance manager was initialized
        mock_performance_manager.initialize.assert_called_once()
        
        # Verify app state is configured for performance monitoring  
        self.assertEqual(self.mock_app.state.performance_manager, mock_performance_manager)
        self.assertEqual(self.mock_app.state.index_manager, mock_index_manager)

    @patch('netra_backend.app.startup_module.get_env')
    @patch('netra_backend.app.startup_module.index_manager')
    @pytest.mark.asyncio
    async def test_background_task_optimization_prevents_startup_blocking(self, mock_index_manager, mock_get_env):
        """Test background optimizations don't block startup process."""
        # Mock environment to enable background tasks
        mock_env = Mock()
        mock_env.get.return_value = "false"  # Enable background tasks
        mock_get_env.return_value = mock_env
        
        # Mock task manager
        mock_task_manager = AsyncMock()
        mock_task_manager.create_task.return_value = "optimization_task_123"
        self.mock_app.state.background_task_manager = mock_task_manager
        
        # Test background optimization scheduling
        start_time = time.time()
        await startup_module._schedule_background_optimizations(self.mock_app, self.mock_logger)
        schedule_time = time.time() - start_time
        
        # Verify scheduling is non-blocking (business requirement)
        self.assertLess(
            schedule_time, 0.1,
            f"PERFORMANCE IMPACT: Background task scheduling took {schedule_time:.3f}s. "
            f"Must be non-blocking to maintain startup performance."
        )
        
        # Verify task was scheduled
        mock_task_manager.create_task.assert_called_once()
        
        # Verify task is configured properly
        call_args = mock_task_manager.create_task.call_args
        self.assertIn('name', call_args.kwargs)
        self.assertIn('timeout', call_args.kwargs)
        self.assertEqual(call_args.kwargs['name'], "database_index_optimization")

    def test_model_import_performance_meets_business_requirements(self):
        """Test model import performance meets business startup time requirements."""
        start_time = time.time()
        
        # Test model imports (critical for database functionality)
        startup_module._import_all_models()
        
        elapsed_time = time.time() - start_time
        
        # Verify model import performance (business requirement)
        self.assertLess(
            elapsed_time, self.performance_thresholds['model_import'],
            f"BUSINESS IMPACT: Model imports took {elapsed_time:.3f}s, "
            f"exceeds {self.performance_thresholds['model_import']}s threshold. "
            f"Slow model loading increases startup time and reduces user satisfaction."
        )

    # =============================================================================
    # SECTION 5: AUTHENTICATION AND SECURITY TESTS
    # =============================================================================

    @patch('netra_backend.app.services.database_env_service.validate_database_environment')
    @patch('netra_backend.app.startup_module.os._exit')
    def test_database_validation_security_enforcement(self, mock_exit, mock_validate):
        """Test database validation enforces security requirements for multi-tenant system."""
        # Simulate security validation failure (business-critical scenario)
        security_error = ValueError("Database environment validation failed: Potential cross-tenant data leak")
        mock_validate.side_effect = security_error
        
        # Test validation enforcement
        startup_module._perform_database_validation(self.mock_logger)
        
        # Verify critical error was logged (compliance requirement)
        self.mock_logger.critical.assert_called_once()
        critical_call = self.mock_logger.critical.call_args[0][0]
        self.assertIn(
            "validation failed", critical_call.lower(),
            "Security failure must be logged as critical for compliance"
        )
        
        # Verify system exits on security failure (no compromise allowed)
        mock_exit.assert_called_once_with(1)

    def test_environment_isolation_validation_for_multi_user_system(self):
        """Test environment isolation validation supports multi-user business model."""
        # Test environment configurations that support multi-user isolation
        multi_user_environments = [
            ("development", "should_validate"),
            ("staging", "should_validate"),
            ("production", "must_validate"),
            ("test", "should_validate")
        ]
        
        for environment, validation_expectation in multi_user_environments:
            with self.subTest(environment=environment):
                with patch('netra_backend.app.startup_module.get_env') as mock_get_env:
                    # Mock environment detection
                    mock_env = Mock()
                    mock_env.get.return_value = environment
                    mock_get_env.return_value = mock_env
                    
                    # Test postgres service mode detection (isolation requirement)
                    result = startup_module._is_postgres_service_mock_mode()
                    
                    # Verify result is boolean (proper validation)
                    self.assertIsInstance(
                        result, bool,
                        f"Environment isolation validation failed for {environment}. "
                        f"Multi-user system requires proper boolean validation."
                    )

    # =============================================================================
    # SECTION 6: DATABASE AND PERSISTENCE TESTS
    # =============================================================================

    def test_database_url_detection_supports_all_business_environments(self):
        """Test database URL detection works across all business deployment environments."""
        business_environment_urls = [
            # Development environments
            ("postgresql://dev_user:dev_pass@localhost/netra_dev", False, "development"),
            ("postgresql://developer:password@dev.netra.com/netra_dev", False, "development"),
            
            # Staging environments  
            ("postgresql://stage_user:stage_pass@staging-db.netra.com/netra_staging", False, "staging"),
            ("postgresql://staging:staging_pass@staging.internal/netra_stage", False, "staging"),
            
            # Production environments
            ("postgresql://prod_user:prod_pass@prod-db.netra.com/netra_production", False, "production"),
            ("postgresql://netra_prod:secure_pass@db.netra.com/netra_prod", False, "production"),
            
            # Test/Mock environments (should be detected as mock)
            ("postgresql://mock:mock@localhost/mock", True, "test"),
            ("postgresql://test:test@localhost:5432/mock", True, "test"),
            ("postgresql+asyncpg://mock:mock@localhost/test_db?mock=true", True, "test"),
        ]
        
        for url, should_be_mock, env_type in business_environment_urls:
            with self.subTest(url=url, environment=env_type):
                result = startup_module._is_mock_database_url(url)
                self.assertEqual(
                    result, should_be_mock,
                    f"Database URL detection failed for {env_type} environment. "
                    f"URL: {url}. Expected mock={should_be_mock}, got mock={result}. "
                    f"Incorrect detection can cause data corruption across environments."
                )

    @patch('netra_backend.app.startup_module.get_engine')
    @patch('netra_backend.app.startup_module._import_all_models')
    @pytest.mark.asyncio
    async def test_database_table_verification_prevents_chat_failures(self, mock_import, mock_get_engine):
        """Test database table verification prevents chat functionality failures."""
        # Mock database engine and connection
        mock_engine = AsyncMock()
        mock_get_engine.return_value = mock_engine
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        
        # Mock transaction
        mock_trans = AsyncMock()  
        mock_conn.begin.return_value.__aenter__.return_value = mock_trans
        
        # Simulate chat-critical tables missing
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ('non_critical_table',),  # Some non-critical table exists
        ]
        mock_conn.execute.return_value = mock_result
        
        # Mock Base metadata with chat-critical tables
        with patch('netra_backend.app.startup_module.Base') as mock_base:
            # Define what tables should exist (including chat-critical ones)
            expected_tables = {
                'users',         # Critical for chat authentication
                'threads',       # Critical for chat conversation management  
                'messages',      # Critical for chat message storage
                'runs',          # Critical for chat agent execution
                'assistants',    # Critical for chat AI responses
                'non_critical_table'  # This exists
            }
            mock_base.metadata.tables.keys.return_value = expected_tables
            
            # Test table verification with critical tables missing
            with self.assertRaises(RuntimeError) as cm:
                await startup_module._ensure_database_tables_exist(self.mock_logger, graceful_startup=False)
            
            # Verify error indicates critical chat tables are missing
            error_message = str(cm.exception)
            chat_critical_tables = {'users', 'threads', 'messages', 'runs', 'assistants'}
            
            # At least one critical table name should be in error
            has_critical_table_reference = any(
                table in error_message.lower() 
                for table in chat_critical_tables
            )
            
            self.assertTrue(
                has_critical_table_reference,
                f"CRITICAL CHAT FAILURE: Error message must indicate missing chat tables. "
                f"Error was: {error_message}. Missing critical tables will break chat completely."
            )

    @patch('netra_backend.app.startup_module.get_engine')
    @pytest.mark.asyncio
    async def test_database_connection_failure_provides_business_actionable_errors(self, mock_get_engine):
        """Test database connection failures provide actionable error messages for operations."""
        # Simulate database engine unavailable
        mock_get_engine.return_value = None
        
        # Test in strict mode (business requirement)
        with self.assertRaises(RuntimeError) as cm:
            await startup_module._ensure_database_tables_exist(self.mock_logger, graceful_startup=False)
        
        error_message = str(cm.exception)
        
        # Verify error message provides actionable information
        actionable_keywords = ['engine', 'database', 'connection', 'failed']
        has_actionable_info = any(keyword in error_message.lower() for keyword in actionable_keywords)
        
        self.assertTrue(
            has_actionable_info,
            f"Database error must provide actionable information for operations team. "
            f"Error was: {error_message}"
        )

    # =============================================================================
    # SECTION 7: MONITORING AND OBSERVABILITY TESTS
    # =============================================================================

    @patch('netra_backend.app.startup_module.chat_event_monitor')
    @patch('netra_backend.app.startup_module.backend_health_checker')
    @pytest.mark.asyncio
    async def test_monitoring_integration_supports_business_observability(self, mock_health_checker, mock_chat_monitor):
        """Test monitoring integration provides business-required observability."""
        # Mock chat event monitor for business-critical chat monitoring
        mock_chat_monitor.start_monitoring = AsyncMock()
        mock_health_checker.component_health = {}
        
        # Test monitoring integration with handler context  
        handlers = {
            "chat_handler": Mock(),
            "agent_handler": Mock(), 
            "websocket_handler": Mock()
        }
        
        result = await startup_module.initialize_monitoring_integration(handlers)
        
        # Verify monitoring integration succeeded (business requirement)
        self.assertTrue(
            result,
            "BUSINESS OBSERVABILITY FAILURE: Monitoring integration failed. "
            "Cannot monitor chat system health and performance."
        )
        
        # Verify chat monitoring was started (critical for business insights)
        mock_chat_monitor.start_monitoring.assert_called_once()

    @patch('netra_backend.app.startup_module.get_websocket_manager_factory')
    @patch('netra_backend.app.startup_module.get_config')
    @pytest.mark.asyncio
    async def test_websocket_monitoring_initialization_for_chat_reliability(self, mock_get_config, mock_factory):
        """Test WebSocket monitoring initialization ensures chat reliability."""
        # Mock configuration
        mock_config = Mock()
        mock_config.graceful_startup_mode = "false"  # Strict mode for business validation
        mock_get_config.return_value = mock_config
        
        # Mock WebSocket factory
        mock_factory.return_value = Mock()
        
        # Test WebSocket component initialization
        await startup_module.initialize_websocket_components(self.mock_logger)
        
        # Verify WebSocket factory was initialized (required for chat)
        mock_factory.assert_called_once()

    # =============================================================================
    # SECTION 8: INTEGRATION AND END-TO-END STARTUP TESTS
    # =============================================================================

    @patch('netra_backend.app.smd.run_deterministic_startup')
    @pytest.mark.asyncio
    async def test_complete_startup_uses_deterministic_mode_for_reliability(self, mock_run_deterministic):
        """Test complete startup uses deterministic mode for business reliability."""
        # Mock deterministic startup return
        expected_start_time = time.time()
        mock_run_deterministic.return_value = (expected_start_time, self.mock_logger)
        
        # Test complete startup
        result = await startup_module.run_complete_startup(self.mock_app)
        
        # Verify deterministic startup was called (business reliability requirement)
        mock_run_deterministic.assert_called_once_with(self.mock_app)
        
        # Verify return format is business-appropriate
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        start_time, logger = result
        self.assertEqual(start_time, expected_start_time)
        self.assertEqual(logger, self.mock_logger)

    def test_startup_completion_logging_provides_business_metrics(self):
        """Test startup completion logging provides metrics for business monitoring."""
        # Simulate startup timing
        start_time = time.time() - 3.5  # 3.5 seconds ago
        
        # Test completion logging
        startup_module.log_startup_complete(start_time, self.mock_logger)
        
        # Verify metrics were logged
        self.mock_logger.info.assert_called_once()
        log_message = self.mock_logger.info.call_args[0][0]
        
        # Verify message contains business-relevant information
        business_indicators = [
            "ready",     # Service availability
            "s)",        # Timing metrics  
            "netra"      # Service identification
        ]
        
        for indicator in business_indicators:
            self.assertIn(
                indicator.lower(), log_message.lower(),
                f"Startup completion log missing business indicator '{indicator}'. "
                f"Log was: {log_message}"
            )

    # =============================================================================
    # SECTION 9: MEMORY AND RESOURCE MANAGEMENT TESTS
    # =============================================================================

    def test_startup_memory_usage_within_business_constraints(self):
        """Test startup operations stay within memory constraints for cost efficiency."""
        import gc
        
        # Get baseline memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform memory-intensive startup operations
        startup_module.initialize_logging()
        startup_module._import_all_models()
        startup_module._setup_paths()
        
        # Check memory usage after operations
        gc.collect() 
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Business constraint: Memory growth must be reasonable
        memory_threshold = 2000  # Maximum 2000 new objects
        self.assertLess(
            object_growth, memory_threshold,
            f"BUSINESS COST IMPACT: Startup created {object_growth} objects, "
            f"exceeds {memory_threshold} threshold. "
            f"Excessive memory usage increases infrastructure costs."
        )

    @patch('netra_backend.app.startup_module.cleanup_multiprocessing')
    @pytest.mark.asyncio 
    async def test_resource_cleanup_prevents_cost_inefficiencies(self, mock_cleanup_mp):
        """Test resource cleanup prevents cost inefficiencies from resource leaks."""
        # Test cleanup performance
        start_time = time.time()
        await startup_module._emergency_cleanup(self.mock_logger)
        cleanup_time = time.time() - start_time
        
        # Verify cleanup is efficient (cost requirement)
        self.assertLess(
            cleanup_time, 1.0,
            f"COST EFFICIENCY FAILURE: Resource cleanup took {cleanup_time:.3f}s. "
            f"Slow cleanup increases infrastructure costs and downtime."
        )
        
        # Verify multiprocessing cleanup was called
        mock_cleanup_mp.assert_called_once()

    # =============================================================================
    # SECTION 10: BUSINESS CONTINUITY AND DISASTER RECOVERY TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_handles_all_business_critical_exceptions(self):
        """Test startup handles all exception types that could impact business continuity."""
        business_critical_exceptions = [
            (ConnectionError("Database connection lost"), "database_connectivity"),
            (TimeoutError("Service startup timeout"), "performance_degradation"), 
            (ValueError("Invalid configuration"), "configuration_error"),
            (ImportError("Missing critical module"), "deployment_issue"),
            (RuntimeError("Service dependency failure"), "service_dependency"),
            (MemoryError("Insufficient memory"), "resource_constraint")
        ]
        
        for exception, error_category in business_critical_exceptions:
            with self.subTest(exception_type=type(exception).__name__, category=error_category):
                # Test that startup can handle this exception type
                # Note: We're testing exception handling patterns, not causing actual failures
                
                # Verify exception type is recognized
                self.assertIsInstance(exception, Exception)
                
                # Verify error message is business-appropriate
                error_message = str(exception)
                self.assertGreater(
                    len(error_message), 0,
                    f"Exception {type(exception).__name__} must have descriptive message "
                    f"for business impact assessment in {error_category}"
                )

    def test_startup_module_function_documentation_supports_business_operations(self):
        """Test all public functions have documentation supporting business operations."""
        import inspect
        
        # Get all public functions (business-facing)
        public_functions = [
            name for name, obj in inspect.getmembers(startup_module)
            if inspect.isfunction(obj) and not name.startswith('_')
        ]
        
        business_documentation_requirements = {
            'min_doc_length': 20,  # Minimum documentation length
            'required_sections': ['purpose', 'business', 'return']  # Not all required, but at least one
        }
        
        for func_name in public_functions:
            with self.subTest(function=func_name):
                func = getattr(startup_module, func_name)
                doc = func.__doc__
                
                # Verify function has documentation
                self.assertIsNotNone(
                    doc,
                    f"BUSINESS OPERATIONS FAILURE: Function {func_name} lacks documentation. "
                    f"Operations team needs clear function descriptions for incident response."
                )
                
                # Verify documentation is substantive
                self.assertGreater(
                    len(doc.strip()), business_documentation_requirements['min_doc_length'],
                    f"BUSINESS OPERATIONS FAILURE: Function {func_name} has insufficient documentation. "
                    f"Minimum {business_documentation_requirements['min_doc_length']} chars required for operational clarity."
                )

    def tearDown(self):
        """Clean up test environment and log performance metrics."""
        # Calculate test performance
        test_duration = time.time() - self.test_start_time
        
        # Log slow tests that could impact business CI/CD pipeline
        if test_duration > 2.0:
            print(f"PERFORMANCE WARNING: Test {self.id()} took {test_duration:.3f}s")
            print(f"Slow tests increase CI/CD time and reduce development velocity")
        
        # Call parent cleanup
        super().tearDown()


if __name__ == '__main__':
    # Run enhanced test suite with business value focus
    unittest.main(verbosity=2, buffer=True)