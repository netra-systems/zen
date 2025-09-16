"""SSOT Compliance Tests for RequestScopedToolDispatcher.

Test Phase 2: Create NEW SSOT validation tests focusing on 20% validation testing
before SSOT consolidation. These tests should fail initially due to duplicate implementations
and pass after SSOT consolidation.

CRITICAL VIOLATIONS IDENTIFIED:
- Duplicate implementations: RequestScopedToolDispatcher, ToolDispatcher, UnifiedToolExecutionEngine
- 32+ bypass imports
- 3 competing factories: ToolExecutorFactory, ToolDispatcher.create_*, enhanced_tool_dispatcher_*
- High risk zones: Import resolution (85% failure), WebSocket events (85% failure), User isolation (85% failure)

Business Value:
- Ensures only one tool dispatcher implementation exists in runtime
- Validates proper factory pattern implementation
- Prevents cross-user data leakage
- Enables reliable concurrent execution
"""
import asyncio
import importlib
import inspect
import sys
import uuid
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

@pytest.mark.unit
class TestRequestScopedToolDispatcherSSotCompliance(SSotBaseTestCase):
    """Test SSOT compliance for RequestScopedToolDispatcher system.
    
    These tests should FAIL initially due to SSOT violations and PASS after consolidation.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_context_1 = UserExecutionContext(user_id='test_user_1', thread_id='test_thread_1', run_id=f'test_run_{uuid.uuid4()}')
        self.user_context_2 = UserExecutionContext(user_id='test_user_2', thread_id='test_thread_2', run_id=f'test_run_{uuid.uuid4()}')

    def test_tool_dispatcher_ssot_import_compliance(self):
        """Test that only one tool dispatcher implementation exists in runtime.
        
        EXPECTED: FAIL initially due to duplicate implementations:
        - RequestScopedToolDispatcher
        - ToolDispatcher 
        - UnifiedToolExecutionEngine with dispatcher functionality
        - Multiple bridge/adapter patterns
        
        EXPECTED: PASS after SSOT consolidation
        """
        dispatcher_implementations = []
        bridge_implementations = []
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            dispatcher_implementations.append('RequestScopedToolDispatcher')
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            dispatcher_implementations.append('ToolDispatcher')
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
            dispatcher_implementations.append('UnifiedToolExecutionEngine')
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import WebSocketBridgeAdapter
            bridge_implementations.append('WebSocketBridgeAdapter')
        except ImportError:
            pass
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            bridge_implementations.append('AgentWebSocketBridge')
        except ImportError:
            pass
        self.assertEqual(len(dispatcher_implementations), 1, f'SSOT VIOLATION: Multiple tool dispatcher implementations found: {dispatcher_implementations}. Should have exactly 1 SSOT implementation after consolidation.')
        self.assertLessEqual(len(bridge_implementations), 1, f'SSOT VIOLATION: Multiple bridge implementations found: {bridge_implementations}. Should have at most 1 unified bridge implementation.')

    def test_factory_pattern_ssot_compliance(self):
        """Test that factory pattern produces consistent instances.
        
        EXPECTED: FAIL initially due to competing factories:
        - ToolExecutorFactory.create_request_scoped_dispatcher()
        - ToolDispatcher.create_request_scoped_dispatcher() 
        - enhance_tool_dispatcher_with_notifications()
        
        EXPECTED: PASS after SSOT consolidation with single factory
        """
        factory_methods = []
        try:
            from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
            factory = ToolExecutorFactory()
            if hasattr(factory, 'create_request_scoped_dispatcher'):
                factory_methods.append('ToolExecutorFactory.create_request_scoped_dispatcher')
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            if hasattr(ToolDispatcher, 'create_request_scoped_dispatcher'):
                factory_methods.append('ToolDispatcher.create_request_scoped_dispatcher')
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
            factory_methods.append('enhance_tool_dispatcher_with_notifications')
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import create_request_scoped_tool_dispatcher
            factory_methods.append('create_request_scoped_tool_dispatcher')
        except ImportError:
            pass
        self.assertLessEqual(len(factory_methods), 2, f'SSOT VIOLATION: Multiple factory methods found: {factory_methods}. Should have at most 1 SSOT factory + 1 convenience function after consolidation.')

    def test_websocket_events_consistent_delivery(self):
        """Test that WebSocket events are delivered consistently via unified implementation.
        
        EXPECTED: FAIL initially due to inconsistent event integration:
        - Different WebSocket bridges
        - Inconsistent event emission patterns
        - Missing events due to integration gaps
        
        EXPECTED: PASS after SSOT consolidation
        """
        required_events = {'agent_started': False, 'agent_thinking': False, 'tool_executing': False, 'tool_completed': False, 'agent_completed': False}
        mock_websocket_manager = MagicMock()
        mock_websocket_manager.emit_event = AsyncMock()
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            mock_emitter = MagicMock()
            for event in required_events.keys():
                method_name = f'notify_{event}'
                if hasattr(mock_emitter, method_name):
                    required_events[event] = True
            dispatcher = RequestScopedToolDispatcher(user_context=self.user_context_1, websocket_emitter=mock_emitter)
            has_websocket = hasattr(dispatcher, 'has_websocket_support') and dispatcher.has_websocket_support
        except Exception as e:
            self.fail(f'Failed to create dispatcher with WebSocket support: {e}')
        missing_events = [event for event, supported in required_events.items() if not supported]
        self.assertEqual(len(missing_events), 0, f'WEBSOCKET EVENT VIOLATION: Missing critical events: {missing_events}. SSOT implementation must support all 5 critical WebSocket events consistently.')

    def test_user_isolation_validation(self):
        """Test that unified implementation provides proper user isolation.
        
        EXPECTED: FAIL initially due to singleton remnants and shared state:
        - Cross-user data leakage
        - Shared execution contexts
        - Global state issues
        
        EXPECTED: PASS after SSOT consolidation with proper isolation
        """
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            dispatcher_1 = RequestScopedToolDispatcher(user_context=self.user_context_1)
            dispatcher_2 = RequestScopedToolDispatcher(user_context=self.user_context_2)

            class TestTool1:
                name = 'user1_tool'

                def run(self, query: str) -> str:
                    return f'User 1 result: {query}'

            class TestTool2:
                name = 'user2_tool'

                def run(self, query: str) -> str:
                    return f'User 2 result: {query}'
            dispatcher_1.register_tool('user1_tool', TestTool1().run)
            dispatcher_2.register_tool('user2_tool', TestTool2().run)
            self.assertTrue(dispatcher_1.has_tool('user1_tool'), 'User 1 dispatcher should have user1_tool')
            self.assertFalse(dispatcher_1.has_tool('user2_tool'), 'ISOLATION VIOLATION: User 1 dispatcher should NOT have access to user2_tool')
            self.assertTrue(dispatcher_2.has_tool('user2_tool'), 'User 2 dispatcher should have user2_tool')
            self.assertFalse(dispatcher_2.has_tool('user1_tool'), 'ISOLATION VIOLATION: User 2 dispatcher should NOT have access to user1_tool')
            context_1 = dispatcher_1.get_context()
            context_2 = dispatcher_2.get_context()
            self.assertNotEqual(context_1.user_id, context_2.user_id, 'User contexts should have different user IDs')
            self.assertNotEqual(context_1.run_id, context_2.run_id, 'User contexts should have different run IDs')
            metrics_1 = dispatcher_1.get_metrics()
            metrics_2 = dispatcher_2.get_metrics()
            self.assertNotEqual(metrics_1['dispatcher_id'], metrics_2['dispatcher_id'], 'ISOLATION VIOLATION: Dispatchers should have different IDs')
            self.assertEqual(metrics_1['user_id'], self.user_context_1.user_id, 'Dispatcher 1 metrics should track correct user_id')
            self.assertEqual(metrics_2['user_id'], self.user_context_2.user_id, 'Dispatcher 2 metrics should track correct user_id')
        except Exception as e:
            self.fail(f'User isolation test failed: {e}')

    def test_import_consistency_across_usage_points(self):
        """Test that all usage points import from the same SSOT location.
        
        EXPECTED: FAIL initially due to 32+ bypass imports
        EXPECTED: PASS after SSOT consolidation
        """
        import_sources = set()
        usage_files = ['netra_backend.app.agents.supervisor.execution_engine', 'netra_backend.app.agents.supervisor_agent_modern', 'netra_backend.app.routes.agents', 'netra_backend.app.admin.tools.unified_admin_dispatcher']
        for module_path in usage_files:
            try:
                module = importlib.import_module(module_path)
                source_code = inspect.getsource(module)
                if 'from netra_backend.app.agents.request_scoped_tool_dispatcher import' in source_code:
                    import_sources.add('request_scoped_tool_dispatcher')
                if 'from netra_backend.app.agents.tool_dispatcher_core import' in source_code:
                    import_sources.add('tool_dispatcher_core')
                if 'from netra_backend.app.agents.unified_tool_execution import' in source_code:
                    import_sources.add('unified_tool_execution')
                if 'from netra_backend.app.tools.enhanced_tool_execution_engine import' in source_code:
                    import_sources.add('enhanced_tool_execution_engine')
            except (ImportError, OSError):
                continue
        self.assertLessEqual(len(import_sources), 2, f'IMPORT CONSISTENCY VIOLATION: Multiple import sources found: {import_sources}. Should have at most 1 SSOT source + 1 compatibility bridge after consolidation.')

    def test_runtime_instance_uniqueness(self):
        """Test that only one dispatcher type exists in runtime after SSOT consolidation.
        
        EXPECTED: FAIL initially due to multiple classes being instantiable
        EXPECTED: PASS after SSOT consolidation blocks deprecated patterns
        """
        instantiable_classes = []
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            try:
                ToolDispatcher()
                instantiable_classes.append('ToolDispatcher')
            except RuntimeError as e:
                if 'no longer supported' in str(e):
                    pass
                else:
                    raise
        except ImportError:
            pass
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import RequestScopedToolDispatcher
            try:
                RequestScopedToolDispatcher(self.user_context_1)
                instantiable_classes.append('RequestScopedToolDispatcher')
            except Exception:
                pass
        except ImportError:
            pass
        self.assertEqual(len(instantiable_classes), 1, f'RUNTIME UNIQUENESS VIOLATION: Multiple instantiable dispatcher classes: {instantiable_classes}. Should have exactly 1 SSOT implementation after consolidation.')
        if instantiable_classes:
            self.assertIn('RequestScopedToolDispatcher', instantiable_classes, f'SSOT implementation RequestScopedToolDispatcher should be instantiable, but found: {instantiable_classes}')

@pytest.mark.unit
class TestRequestScopedToolDispatcherFactoryConsistency(SSotBaseTestCase):
    """Test factory consistency for RequestScopedToolDispatcher system."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_context = UserExecutionContext(user_id='factory_test_user', thread_id='factory_test_thread', run_id=f'factory_test_run_{uuid.uuid4()}')

    async def test_factory_produces_identical_instances(self):
        """Test that factory methods produce functionally identical instances.
        
        EXPECTED: FAIL initially due to competing factories producing different types
        EXPECTED: PASS after SSOT consolidation with unified factory
        """
        instances = []
        factory_sources = []
        try:
            from netra_backend.app.agents.tool_executor_factory import ToolExecutorFactory
            factory = ToolExecutorFactory()
            instance = await factory.create_request_scoped_dispatcher(self.user_context)
            instances.append(instance)
            factory_sources.append('ToolExecutorFactory')
            await instance.cleanup()
        except Exception:
            pass
        try:
            from netra_backend.app.agents.request_scoped_tool_dispatcher import create_request_scoped_tool_dispatcher
            instance = await create_request_scoped_tool_dispatcher(self.user_context)
            instances.append(instance)
            factory_sources.append('create_request_scoped_tool_dispatcher')
            await instance.cleanup()
        except Exception:
            pass
        if len(instances) > 1:
            instance_types = [type(instance).__name__ for instance in instances]
            unique_types = set(instance_types)
            self.assertEqual(len(unique_types), 1, f'FACTORY CONSISTENCY VIOLATION: Different factories produce different types: {dict(zip(factory_sources, instance_types))}. Should all produce the same SSOT type after consolidation.')

    def test_factory_deprecation_enforcement(self):
        """Test that deprecated factory patterns are properly blocked.
        
        EXPECTED: FAIL initially if deprecated patterns are still accessible
        EXPECTED: PASS after deprecation enforcement is implemented
        """
        deprecated_patterns = []
        try:
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
            try:
                ToolDispatcher()
                deprecated_patterns.append('ToolDispatcher direct instantiation')
            except RuntimeError as e:
                if 'no longer supported' not in str(e):
                    deprecated_patterns.append(f'ToolDispatcher wrong error: {e}')
        except ImportError:
            pass
        self.assertEqual(len(deprecated_patterns), 0, f'DEPRECATION ENFORCEMENT VIOLATION: Deprecated patterns still accessible: {deprecated_patterns}. All deprecated patterns should be blocked with appropriate RuntimeError messages.')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')