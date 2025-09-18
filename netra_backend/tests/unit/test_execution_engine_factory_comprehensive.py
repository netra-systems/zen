"""
Comprehensive Unit Test Suite for Execution Engine Factory

Business Value Justification (BVJ):
- **Segment:** Platform/Enterprise (multi-tenant infrastructure)
- **Goal:** Stability and scalability of core execution infrastructure
- **Value Impact:** Ensures reliable user isolation and resource management
- **Revenue Impact:** Protects 500K+ ARR by enabling secure multi-tenant execution

This test suite validates the ExecutionEngineFactory SSOT implementation with focus on:
1. Factory pattern implementation and lifecycle management
2. User execution engine creation and isolation
3. Resource limits and cleanup automation
4. WebSocket integration for real-time updates
5. Context managers and scope management
6. Factory metrics and monitoring
7. Error handling and recovery patterns

Test Categories:
- Factory Creation: Engine factory instantiation and configuration
- Engine Lifecycle: Creation, management, and cleanup of execution engines
- User Isolation: Concurrent user execution without cross-contamination
- Resource Management: Limits, timeouts, and automatic cleanup
- Context Managers: Safe scope management with guaranteed cleanup
- Factory Metrics: Performance tracking and health monitoring
- Error Handling: Graceful degradation and recovery

Created: 2025-09-10
Last Updated: 2025-09-10
"""
import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, ExecutionEngineFactoryError, get_execution_engine_factory, configure_execution_engine_factory, user_execution_engine, create_request_scoped_engine
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.types.core_types import UserID, ThreadID, RunID

class MockWebSocketBridge(Mock):
    """Mock WebSocket bridge for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = True
        self.messages_sent = []

    async def send_message(self, message):
        """Mock send message method."""
        self.messages_sent.append(message)
        return True

    def is_connected(self):
        """Mock connection status."""
        return self.connected

class MockUserExecutionEngine(Mock):
    """Mock UserExecutionEngine for testing."""

    def __init__(self, context: UserExecutionContext, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine_id = f'engine_{uuid.uuid4().hex[:8]}'
        self.context = context
        self.created_at = datetime.now(timezone.utc)
        self.active_runs = []
        self._is_active = True
        self.database_session_manager = None
        self.redis_manager = None

    def get_user_context(self):
        """Get user context."""
        return self.context

    def is_active(self):
        """Check if engine is active."""
        return self._is_active

    async def cleanup(self):
        """Mock cleanup."""
        self._is_active = False

    def get_user_execution_stats(self):
        """Get execution stats."""
        return {'total_executions': len(self.active_runs), 'success_rate': 1.0, 'average_execution_time': 100.0}

class ExecutionEngineFactoryCreationTests(SSotAsyncTestCase):
    """Test suite for execution engine factory creation and configuration."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_websocket_bridge = MockWebSocketBridge()
        self.mock_db_manager = Mock()
        self.mock_redis_manager = Mock()

    def test_factory_initialization_with_websocket_bridge(self):
        """Test factory initializes correctly with WebSocket bridge."""
        factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge, database_session_manager=self.mock_db_manager, redis_manager=self.mock_redis_manager)
        self.assertEqual(factory._websocket_bridge, self.mock_websocket_bridge)
        self.assertEqual(factory._database_session_manager, self.mock_db_manager)
        self.assertEqual(factory._redis_manager, self.mock_redis_manager)
        self.assertIsInstance(factory._active_engines, dict)
        self.assertEqual(len(factory._active_engines), 0)
        self.assertIsInstance(factory._factory_metrics, dict)
        self.assertEqual(factory._max_engines_per_user, 2)
        self.assertEqual(factory._engine_timeout_seconds, 300)
        self.assertEqual(factory._cleanup_interval, 60)

    def test_factory_initialization_without_websocket_bridge(self):
        """Test factory initializes in compatibility mode without WebSocket bridge."""
        factory = ExecutionEngineFactory(websocket_bridge=None, database_session_manager=self.mock_db_manager, redis_manager=self.mock_redis_manager)
        self.assertIsNone(factory._websocket_bridge)
        self.assertEqual(factory._database_session_manager, self.mock_db_manager)
        self.assertEqual(factory._redis_manager, self.mock_redis_manager)
        self.assertIsInstance(factory._active_engines, dict)
        self.assertIsInstance(factory._factory_metrics, dict)

    def test_factory_metrics_initialization(self):
        """Test that factory metrics are properly initialized."""
        factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge)
        metrics = factory.get_factory_metrics()
        self.assertIn('total_engines_created', metrics)
        self.assertIn('total_engines_cleaned', metrics)
        self.assertIn('active_engines_count', metrics)
        self.assertIn('creation_errors', metrics)
        self.assertIn('cleanup_errors', metrics)
        self.assertIn('timeout_cleanups', metrics)
        self.assertIn('user_limit_rejections', metrics)
        self.assertEqual(metrics['total_engines_created'], 0)
        self.assertEqual(metrics['active_engines_count'], 0)
        self.assertEqual(metrics['max_engines_per_user'], 2)
        self.assertEqual(metrics['engine_timeout_seconds'], 300)

    def test_tool_dispatcher_factory_setting(self):
        """Test setting tool dispatcher factory."""
        factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge)
        mock_tool_factory = Mock()
        factory.set_tool_dispatcher_factory(mock_tool_factory)
        self.assertEqual(factory._tool_dispatcher_factory, mock_tool_factory)

class ExecutionEngineLifecycleTests(SSotAsyncTestCase):
    """Test suite for execution engine lifecycle management."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_websocket_bridge = MockWebSocketBridge()
        self.factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge, database_session_manager=Mock(), redis_manager=Mock())

    async def asyncTearDown(self):
        """Clean up after tests."""
        if hasattr(self.factory, 'shutdown'):
            await self.factory.shutdown()

    def create_test_context(self, user_id: str='test_user') -> UserExecutionContext:
        """Create test user execution context."""
        return UserExecutionContext(user_id=UserID(user_id), thread_id=ThreadID(f'thread_{user_id}'), run_id=RunID(f'run_{user_id}_{int(time.time())}'), request_id=f'req_{user_id}_{int(time.time())}', operation_depth=1, agent_context={'user_request': f'Test request from {user_id}'}, metadata={})

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine')
    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_create_for_user_success(self, mock_agent_factory_class, mock_engine_class):
        """Test successful creation of user execution engine."""
        mock_agent_factory = Mock()
        mock_agent_factory_class.return_value = mock_agent_factory
        context = self.create_test_context('user123')
        mock_engine = MockUserExecutionEngine(context)
        mock_engine_class.return_value = mock_engine
        result_engine = await self.factory.create_for_user(context)
        self.assertIsNotNone(result_engine)
        mock_agent_factory_class.assert_called_once()
        mock_engine_class.assert_called_once()
        self.assertEqual(len(self.factory._active_engines), 1)
        metrics = self.factory.get_factory_metrics()
        self.assertEqual(metrics['total_engines_created'], 1)
        self.assertEqual(metrics['active_engines_count'], 1)

    async def test_create_for_user_invalid_context(self):
        """Test engine creation with invalid user context."""
        with self.assertRaises(ExecutionEngineFactoryError):
            await self.factory.create_for_user(None)
        with self.assertRaises(ExecutionEngineFactoryError):
            await self.factory.create_for_user('invalid_context')

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine')
    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_user_engine_limits_enforcement(self, mock_agent_factory_class, mock_engine_class):
        """Test that per-user engine limits are enforced."""
        mock_agent_factory = Mock()
        mock_agent_factory_class.return_value = mock_agent_factory
        context1 = self.create_test_context('limited_user')
        context2 = self.create_test_context('limited_user')
        context3 = self.create_test_context('limited_user')
        mock_engine1 = MockUserExecutionEngine(context1)
        mock_engine2 = MockUserExecutionEngine(context2)
        mock_engine3 = MockUserExecutionEngine(context3)
        mock_engine_class.side_effect = [mock_engine1, mock_engine2, mock_engine3]
        engine1 = await self.factory.create_for_user(context1)
        self.assertIsNotNone(engine1)
        engine2 = await self.factory.create_for_user(context2)
        self.assertIsNotNone(engine2)
        with self.assertRaises(ExecutionEngineFactoryError) as context:
            await self.factory.create_for_user(context3)
        self.assertIn('maximum engine limit', str(context.exception))
        metrics = self.factory.get_factory_metrics()
        self.assertEqual(metrics['user_limit_rejections'], 1)

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine')
    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_cleanup_engine(self, mock_agent_factory_class, mock_engine_class):
        """Test engine cleanup functionality."""
        mock_agent_factory = Mock()
        mock_agent_factory_class.return_value = mock_agent_factory
        context = self.create_test_context('cleanup_user')
        mock_engine = MockUserExecutionEngine(context)
        mock_engine_class.return_value = mock_engine
        engine = await self.factory.create_for_user(context)
        self.assertEqual(len(self.factory._active_engines), 1)
        await self.factory.cleanup_engine(engine)
        self.assertEqual(len(self.factory._active_engines), 0)
        self.assertFalse(engine.is_active())
        metrics = self.factory.get_factory_metrics()
        self.assertEqual(metrics['total_engines_cleaned'], 1)
        self.assertEqual(metrics['active_engines_count'], 0)

    async def test_cleanup_user_context(self):
        """Test cleanup of all engines for a specific user."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_engine_class:
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory') as mock_agent_factory_class:
                mock_agent_factory = Mock()
                mock_agent_factory_class.return_value = mock_agent_factory
                context1 = self.create_test_context('user_to_cleanup')
                context2 = self.create_test_context('user_to_cleanup')
                context3 = self.create_test_context('other_user')
                mock_engine1 = MockUserExecutionEngine(context1)
                mock_engine2 = MockUserExecutionEngine(context2)
                mock_engine3 = MockUserExecutionEngine(context3)
                mock_engine_class.side_effect = [mock_engine1, mock_engine2, mock_engine3]
                await self.factory.create_for_user(context1)
                await self.factory.create_for_user(context2)
                await self.factory.create_for_user(context3)
                self.assertEqual(len(self.factory._active_engines), 3)
                result = await self.factory.cleanup_user_context('user_to_cleanup')
                self.assertTrue(result)
                self.assertEqual(len(self.factory._active_engines), 1)
                remaining_engine = list(self.factory._active_engines.values())[0]
                self.assertEqual(remaining_engine.get_user_context().user_id, 'other_user')

class ExecutionEngineContextManagersTests(SSotAsyncTestCase):
    """Test suite for context managers and scope management."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_websocket_bridge = MockWebSocketBridge()
        self.factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge)

    async def asyncTearDown(self):
        """Clean up after tests."""
        await self.factory.shutdown()

    def create_test_context(self, user_id: str='context_user') -> UserExecutionContext:
        """Create test user execution context."""
        return UserExecutionContext(user_id=UserID(user_id), thread_id=ThreadID(f'thread_{user_id}'), run_id=RunID(f'run_{user_id}_{int(time.time())}'), request_id=f'req_{user_id}_{int(time.time())}', operation_depth=1, agent_context={'user_request': f'Test request from {user_id}'}, metadata={})

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine')
    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_user_execution_scope_success(self, mock_agent_factory_class, mock_engine_class):
        """Test successful user execution scope with automatic cleanup."""
        mock_agent_factory = Mock()
        mock_agent_factory_class.return_value = mock_agent_factory
        context = self.create_test_context('scope_user')
        mock_engine = MockUserExecutionEngine(context)
        mock_engine_class.return_value = mock_engine
        async with self.factory.user_execution_scope(context) as engine:
            self.assertIsNotNone(engine)
            self.assertEqual(engine.get_user_context().user_id, 'scope_user')
            self.assertEqual(len(self.factory._active_engines), 1)
        self.assertEqual(len(self.factory._active_engines), 0)
        self.assertFalse(mock_engine.is_active())

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine')
    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_user_execution_scope_with_exception(self, mock_agent_factory_class, mock_engine_class):
        """Test user execution scope with exception ensures cleanup."""
        mock_agent_factory = Mock()
        mock_agent_factory_class.return_value = mock_agent_factory
        context = self.create_test_context('exception_user')
        mock_engine = MockUserExecutionEngine(context)
        mock_engine_class.return_value = mock_engine
        with self.assertRaises(ValueError):
            async with self.factory.user_execution_scope(context) as engine:
                self.assertIsNotNone(engine)
                self.assertEqual(len(self.factory._active_engines), 1)
                raise ValueError('Test exception')
        self.assertEqual(len(self.factory._active_engines), 0)
        self.assertFalse(mock_engine.is_active())

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_execution_engine_factory')
    async def test_user_execution_engine_function(self, mock_get_factory):
        """Test user_execution_engine convenience function."""
        mock_factory = AsyncMock()
        mock_engine = Mock()

        async def mock_scope(context):
            yield mock_engine
        mock_factory.user_execution_scope = mock_scope
        mock_get_factory.return_value = mock_factory
        context = self.create_test_context('convenience_user')
        async with user_execution_engine(context) as engine:
            self.assertEqual(engine, mock_engine)
        mock_get_factory.assert_called_once()

class ExecutionEngineFactoryMetricsTests(SSotAsyncTestCase):
    """Test suite for factory metrics and monitoring."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_websocket_bridge = MockWebSocketBridge()
        self.factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge)

    async def asyncTearDown(self):
        """Clean up after tests."""
        await self.factory.shutdown()

    def test_factory_metrics_structure(self):
        """Test that factory metrics have correct structure."""
        metrics = self.factory.get_factory_metrics()
        required_fields = ['total_engines_created', 'total_engines_cleaned', 'active_engines_count', 'creation_errors', 'cleanup_errors', 'timeout_cleanups', 'user_limit_rejections', 'max_engines_per_user', 'engine_timeout_seconds', 'cleanup_interval', 'active_engine_keys', 'cleanup_task_running', 'timestamp']
        for field in required_fields:
            self.assertIn(field, metrics)
        self.assertIsInstance(metrics['total_engines_created'], int)
        self.assertIsInstance(metrics['active_engines_count'], int)
        self.assertIsInstance(metrics['active_engine_keys'], list)
        self.assertIsInstance(metrics['cleanup_task_running'], bool)
        self.assertIsInstance(metrics['timestamp'], str)

    def test_active_engines_summary_structure(self):
        """Test that active engines summary has correct structure."""
        summary = self.factory.get_active_engines_summary()
        self.assertIn('total_active_engines', summary)
        self.assertIn('engines', summary)
        self.assertIn('summary_timestamp', summary)
        self.assertIsInstance(summary['total_active_engines'], int)
        self.assertIsInstance(summary['engines'], dict)
        self.assertIsInstance(summary['summary_timestamp'], str)
        self.assertEqual(summary['total_active_engines'], 0)
        self.assertEqual(len(summary['engines']), 0)

    def test_get_active_contexts(self):
        """Test getting active user contexts."""
        contexts = self.factory.get_active_contexts()
        self.assertIsInstance(contexts, dict)
        self.assertEqual(len(contexts), 0)

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine')
    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_metrics_update_on_engine_operations(self, mock_agent_factory_class, mock_engine_class):
        """Test that metrics are updated during engine operations."""
        mock_agent_factory = Mock()
        mock_agent_factory_class.return_value = mock_agent_factory
        context = self.create_test_context('metrics_user')
        mock_engine = MockUserExecutionEngine(context)
        mock_engine_class.return_value = mock_engine
        initial_metrics = self.factory.get_factory_metrics()
        self.assertEqual(initial_metrics['total_engines_created'], 0)
        self.assertEqual(initial_metrics['active_engines_count'], 0)
        engine = await self.factory.create_for_user(context)
        after_create_metrics = self.factory.get_factory_metrics()
        self.assertEqual(after_create_metrics['total_engines_created'], 1)
        self.assertEqual(after_create_metrics['active_engines_count'], 1)
        await self.factory.cleanup_engine(engine)
        after_cleanup_metrics = self.factory.get_factory_metrics()
        self.assertEqual(after_cleanup_metrics['total_engines_created'], 1)
        self.assertEqual(after_cleanup_metrics['total_engines_cleaned'], 1)
        self.assertEqual(after_cleanup_metrics['active_engines_count'], 0)

    def create_test_context(self, user_id: str='test_user') -> UserExecutionContext:
        """Create test user execution context."""
        return UserExecutionContext(user_id=UserID(user_id), thread_id=ThreadID(f'thread_{user_id}'), run_id=RunID(f'run_{user_id}_{int(time.time())}'), request_id=f'req_{user_id}_{int(time.time())}', operation_depth=1, agent_context={'user_request': f'Test request from {user_id}'}, metadata={})

class ExecutionEngineFactoryErrorHandlingTests(SSotAsyncTestCase):
    """Test suite for error handling and recovery patterns."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_websocket_bridge = MockWebSocketBridge()
        self.factory = ExecutionEngineFactory(websocket_bridge=self.mock_websocket_bridge)

    async def asyncTearDown(self):
        """Clean up after tests."""
        await self.factory.shutdown()

    def create_test_context(self, user_id: str='error_user') -> UserExecutionContext:
        """Create test user execution context."""
        return UserExecutionContext(user_id=UserID(user_id), thread_id=ThreadID(f'thread_{user_id}'), run_id=RunID(f'run_{user_id}_{int(time.time())}'), request_id=f'req_{user_id}_{int(time.time())}', operation_depth=1, agent_context={'user_request': f'Test request from {user_id}'}, metadata={})

    @patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory')
    async def test_engine_creation_failure_handling(self, mock_agent_factory_class):
        """Test handling of engine creation failures."""
        mock_agent_factory_class.side_effect = Exception('Factory creation failed')
        context = self.create_test_context('failing_user')
        with self.assertRaises(ExecutionEngineFactoryError) as exc_context:
            await self.factory.create_for_user(context)
        self.assertIn('Engine creation failed', str(exc_context.exception))
        metrics = self.factory.get_factory_metrics()
        self.assertEqual(metrics['creation_errors'], 1)
        self.assertEqual(metrics['total_engines_created'], 0)

    async def test_cleanup_error_handling(self):
        """Test handling of cleanup errors."""
        mock_engine = Mock()
        mock_engine.cleanup = AsyncMock(side_effect=Exception('Cleanup failed'))
        mock_engine.engine_id = 'failing_engine'
        self.factory._active_engines['test_key'] = mock_engine
        await self.factory.cleanup_engine(mock_engine)
        metrics = self.factory.get_factory_metrics()
        self.assertEqual(metrics['cleanup_errors'], 1)

    async def test_websocket_emitter_creation_failure(self):
        """Test handling of WebSocket emitter creation failures."""
        failing_bridge = Mock()
        failing_bridge.side_effect = Exception('WebSocket bridge failed')
        factory_with_failing_bridge = ExecutionEngineFactory(websocket_bridge=failing_bridge)
        context = self.create_test_context('websocket_fail_user')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter') as mock_emitter_class:
            mock_emitter_class.side_effect = Exception('Emitter creation failed')
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory') as mock_agent_factory_class:
                mock_agent_factory_class.return_value = Mock()
                with self.assertRaises(ExecutionEngineFactoryError) as exc_context:
                    await factory_with_failing_bridge.create_for_user(context)
                self.assertIn('WebSocket emitter creation failed', str(exc_context.exception))
        await factory_with_failing_bridge.shutdown()

    async def test_factory_shutdown_with_active_engines(self):
        """Test factory shutdown properly handles active engines."""
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_engine_class:
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory') as mock_agent_factory_class:
                mock_agent_factory = Mock()
                mock_agent_factory_class.return_value = mock_agent_factory
                context = self.create_test_context('shutdown_user')
                mock_engine = MockUserExecutionEngine(context)
                mock_engine_class.return_value = mock_engine
                await self.factory.create_for_user(context)
                self.assertEqual(len(self.factory._active_engines), 1)
                await self.factory.shutdown()
                self.assertEqual(len(self.factory._active_engines), 0)
                self.assertFalse(mock_engine.is_active())
                metrics = self.factory.get_factory_metrics()
                self.assertEqual(metrics['active_engines_count'], 0)

class ExecutionEngineFactoryCompatibilityTests(SSotAsyncTestCase):
    """Test suite for compatibility functions and aliases."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()

    async def test_create_request_scoped_engine_alias(self):
        """Test create_request_scoped_engine compatibility alias."""
        context = UserExecutionContext(user_id=UserID('alias_user'), thread_id=ThreadID('alias_thread'), run_id=RunID('alias_run'), request_id='alias_request', operation_depth=1, agent_context={}, metadata={})
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_execution_engine_factory') as mock_get_factory:
            mock_factory = AsyncMock()
            mock_engine = Mock()
            mock_factory.create_for_user.return_value = mock_engine
            mock_get_factory.return_value = mock_factory
            result = await create_request_scoped_engine(context)
            mock_get_factory.assert_called_once()
            mock_factory.create_for_user.assert_called_once_with(context)
            self.assertEqual(result, mock_engine)

    async def test_configure_execution_engine_factory(self):
        """Test factory configuration function."""
        mock_bridge = Mock()
        mock_db_manager = Mock()
        mock_redis_manager = Mock()
        factory = await configure_execution_engine_factory(websocket_bridge=mock_bridge, database_session_manager=mock_db_manager, redis_manager=mock_redis_manager)
        self.assertIsInstance(factory, ExecutionEngineFactory)
        self.assertEqual(factory._websocket_bridge, mock_bridge)
        self.assertEqual(factory._database_session_manager, mock_db_manager)
        self.assertEqual(factory._redis_manager, mock_redis_manager)
        await factory.shutdown()

    async def test_get_execution_engine_factory_not_configured(self):
        """Test get_execution_engine_factory when not configured."""
        import netra_backend.app.agents.supervisor.execution_engine_factory as factory_module
        factory_module._factory_instance = None
        with self.assertRaises(ExecutionEngineFactoryError) as exc_context:
            await get_execution_engine_factory()
        self.assertIn('not configured during startup', str(exc_context.exception))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')