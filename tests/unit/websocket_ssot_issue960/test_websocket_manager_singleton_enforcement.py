"""
WebSocket Manager Singleton Enforcement Tests - Issue #960

These tests are designed to FAIL with the current fragmented WebSocket manager system
and PASS after SSOT consolidation is completed.

CRITICAL: These tests prove SSOT violations exist by demonstrating:
1. Multiple WebSocket manager instances can be created simultaneously
2. Factory pattern creates new instances instead of using SSOT
3. Different import paths resolve to different manager instances
4. Events may be delivered through different manager instances

Business Value: $500K+ ARR depends on reliable WebSocket event delivery
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class TestWebSocketManagerSingletonEnforcement(SSotBaseTestCase):
    """Test WebSocket manager singleton enforcement - SHOULD FAIL before SSOT consolidation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()

    async def test_multiple_websocket_manager_imports_return_same_instance(self):
        """
        SHOULD FAIL: Currently different import paths return different instances.

        This test proves SSOT fragmentation exists by importing WebSocket managers
        from different paths and verifying they are NOT the same instance.
        After SSOT consolidation, all import paths should return the same instance.
        """
        logger.info('Testing WebSocket manager import path SSOT compliance - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as Manager1
            from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation as Manager2
            user_context = {'user_id': 'test_user_123', 'thread_id': 'test_thread_456'}
            manager1 = Manager1(user_context=user_context)
            manager2 = Manager2(user_context=user_context)
            self.assertIs(manager1, manager2, 'SSOT VIOLATION: Different import paths create different WebSocket manager instances. This proves fragmentation exists and threatens Golden Path reliability.')
        except ImportError as e:
            logger.error(f'Import error indicates WebSocket manager fragmentation: {e}')
            raise AssertionError(f'SSOT VIOLATION: Could not import WebSocket managers from expected paths: {e}')
        except Exception as e:
            logger.error(f'WebSocket manager instantiation failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket manager creation inconsistency: {e}')

    async def test_websocket_manager_factory_delegates_to_ssot(self):
        """
        SHOULD FAIL: Factory creates new instances instead of using SSOT.

        This test proves that factory functions create multiple instances instead
        of delegating to a single SSOT implementation.
        """
        logger.info('Testing WebSocket manager factory SSOT delegation - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            user_context = {'user_id': 'test_user_789', 'thread_id': 'test_thread_101'}
            factory_manager = await create_websocket_manager(user_context=user_context)
            direct_manager = get_websocket_manager(user_context=user_context)
            self.assertIs(factory_manager, direct_manager, 'SSOT VIOLATION: Factory creates separate instances instead of using SSOT. This causes WebSocket event delivery inconsistencies.')
        except ImportError as e:
            logger.error(f'Import error indicates factory fragmentation: {e}')
            raise AssertionError(f'SSOT VIOLATION: Factory import paths not properly consolidated: {e}')
        except Exception as e:
            logger.error(f'Factory delegation test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: Factory does not properly delegate to SSOT: {e}')

    async def test_websocket_manager_instance_sharing_across_contexts(self):
        """
        SHOULD FAIL: Multiple contexts create separate manager instances.

        This test validates that the WebSocket manager properly implements
        instance sharing for the same user across different execution contexts.
        """
        logger.info('Testing WebSocket manager instance sharing - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            user_context1 = {'user_id': 'test_user_shared', 'thread_id': 'thread_1'}
            user_context2 = {'user_id': 'test_user_shared', 'thread_id': 'thread_2'}
            manager1 = get_websocket_manager(user_context=user_context1)
            manager2 = get_websocket_manager(user_context=user_context2)
            self.assertEqual(id(manager1), id(manager2), 'SSOT VIOLATION: Same user gets different WebSocket manager instances. This can cause event delivery race conditions.')
        except Exception as e:
            logger.error(f'Instance sharing test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket manager instance sharing broken: {e}')

    async def test_websocket_manager_memory_isolation_enforcement(self):
        """
        SHOULD FAIL: Manager instances may share memory state inappropriately.

        This test validates that WebSocket managers properly isolate memory
        state between different users while maintaining SSOT compliance.
        """
        logger.info('Testing WebSocket manager memory isolation - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            context1 = {'user_id': 'user_isolation_1', 'thread_id': 'thread_1'}
            context2 = {'user_id': 'user_isolation_2', 'thread_id': 'thread_2'}
            manager1 = get_websocket_manager(user_context=context1)
            manager2 = get_websocket_manager(user_context=context2)
            if hasattr(manager1, 'connections'):
                manager1.connections['test_key'] = 'user1_data'
            if hasattr(manager2, 'connections'):
                self.assertNotIn('test_key', manager2.connections, 'SSOT VIOLATION: WebSocket managers share memory state between users. This violates user isolation and creates security risks.')
        except Exception as e:
            logger.error(f'Memory isolation test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket manager memory isolation broken: {e}')

    def test_websocket_manager_class_definition_uniqueness(self):
        """
        SHOULD FAIL: Multiple WebSocket manager classes exist with similar names.

        This test proves that multiple WebSocket manager class definitions exist,
        violating SSOT principles.
        """
        logger.info('Testing WebSocket manager class uniqueness - EXPECTING FAILURE')
        websocket_manager_classes = []
        try:
            class_imports = [('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'), ('netra_backend.app.websocket_core.unified_manager', '_UnifiedWebSocketManagerImplementation'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'IsolatedWebSocketManager'), ('test_framework.fixtures.websocket_manager_mock', 'MockWebSocketManager')]
            for module_path, class_name in class_imports:
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    if hasattr(module, class_name):
                        cls = getattr(module, class_name)
                        websocket_manager_classes.append((module_path, class_name, cls))
                except ImportError:
                    pass
        except Exception as e:
            logger.error(f'Class discovery failed: {e}')
        if len(websocket_manager_classes) > 1:
            class_info = [f'{path}.{name}' for path, name, _ in websocket_manager_classes]
            raise AssertionError(f'SSOT VIOLATION: Found {len(websocket_manager_classes)} WebSocket manager classes: {class_info}. SSOT requires exactly ONE canonical class definition.')
        logger.info(f"Found WebSocket manager classes: {[f'{p}.{n}' for p, n, _ in websocket_manager_classes]}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')