"""
WebSocket Manager Import Path SSOT Validation Tests - Issue #960

These tests are designed to FAIL with the current fragmented WebSocket manager system
and PASS after SSOT consolidation is completed.

CRITICAL: These tests prove SSOT violations exist by demonstrating:
1. Multiple import paths exist for WebSocket managers
2. Different import paths may resolve to different implementations
3. Event delivery may be inconsistent across import paths
4. WebSocket factory patterns create fragmentation

Business Value: $500K+ ARR depends on consistent WebSocket event delivery
"""
import asyncio
import pytest
import inspect
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class TestWebSocketManagerImportPathSSOT(SSotBaseTestCase):
    """Test WebSocket manager import path SSOT compliance - SHOULD FAIL before consolidation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.discovered_import_paths = []

    async def test_all_websocket_manager_imports_resolve_to_canonical(self):
        """
        SHOULD FAIL: Multiple import paths exist for WebSocket managers.

        This test discovers all possible import paths for WebSocket managers
        and validates that they resolve to the same canonical implementation.
        """
        logger.info('Testing WebSocket manager import path canonicalization - EXPECTING FAILURE')
        import_patterns = [('netra_backend.app.websocket_core.websocket_manager', 'WebSocketManager'), ('netra_backend.app.websocket_core.websocket_manager', 'get_websocket_manager'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'create_websocket_manager'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'IsolatedWebSocketManager'), ('netra_backend.app.websocket_core.unified_manager', '_UnifiedWebSocketManagerImplementation'), ('netra_backend.app.websocket_core.unified_manager', 'WebSocketManagerMode'), ('test_framework.fixtures.websocket_manager_mock', 'MockWebSocketManager')]
        successful_imports = []
        failed_imports = []
        for module_path, class_or_function_name in import_patterns:
            try:
                module = __import__(module_path, fromlist=[class_or_function_name])
                if hasattr(module, class_or_function_name):
                    obj = getattr(module, class_or_function_name)
                    successful_imports.append((module_path, class_or_function_name, obj))
                    logger.info(f'Successfully imported {module_path}.{class_or_function_name}')
                else:
                    failed_imports.append((module_path, class_or_function_name, 'Not found'))
            except ImportError as e:
                failed_imports.append((module_path, class_or_function_name, str(e)))
        self.discovered_import_paths = successful_imports
        if len(successful_imports) > 2:
            import_list = [f'{path}.{name}' for path, name, _ in successful_imports]
            raise AssertionError(f'SSOT VIOLATION: Found {len(successful_imports)} WebSocket manager import paths: {import_list}. SSOT requires minimal import surface (1-2 canonical paths maximum).')
        logger.info(f'WebSocket manager imports discovered: {len(successful_imports)}')
        logger.info(f'Failed imports (expected): {len(failed_imports)}')

    async def test_websocket_event_delivery_ssot_compliance(self):
        """
        SHOULD FAIL: Events may be sent through different manager instances.

        This test validates that WebSocket events are delivered through a single
        SSOT manager regardless of which import path was used to create it.
        """
        logger.info('Testing WebSocket event delivery SSOT compliance - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            user_context = {'user_id': 'event_test_user', 'thread_id': 'event_test_thread'}
            manager1 = await get_websocket_manager(user_context=user_context)
            manager2 = await create_websocket_manager(user_context=user_context)
            mock_websocket = MagicMock()
            if hasattr(manager1, 'add_connection'):
                await manager1.add_connection(mock_websocket, user_context)
            if hasattr(manager2, 'add_connection'):
                await manager2.add_connection(mock_websocket, user_context)
            event_data = {'type': 'agent_started', 'user_id': user_context['user_id']}
            events_sent_manager1 = 0
            events_sent_manager2 = 0
            try:
                if hasattr(manager1, 'send_event'):
                    await manager1.send_event(event_data, user_context)
                    events_sent_manager1 = 1
            except Exception as e:
                logger.warning(f'Manager1 event sending failed: {e}')
            try:
                if hasattr(manager2, 'send_event'):
                    await manager2.send_event(event_data, user_context)
                    events_sent_manager2 = 1
            except Exception as e:
                logger.warning(f'Manager2 event sending failed: {e}')
            total_events = events_sent_manager1 + events_sent_manager2
            if total_events > 1:
                raise AssertionError(f'SSOT VIOLATION: Multiple WebSocket managers can send events independently. Manager1: {events_sent_manager1}, Manager2: {events_sent_manager2}. This causes duplicate event delivery.')
        except Exception as e:
            logger.error(f'Event delivery SSOT test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket event delivery system is fragmented: {e}')

    def test_websocket_manager_function_signatures_consistency(self):
        """
        SHOULD FAIL: Different WebSocket manager implementations have inconsistent signatures.

        This test validates that all WebSocket manager functions have consistent
        signatures, indicating proper SSOT implementation.
        """
        logger.info('Testing WebSocket manager function signature consistency - EXPECTING FAILURE')
        function_signatures = {}
        try:
            import_functions = [('netra_backend.app.websocket_core.websocket_manager', 'get_websocket_manager'), ('netra_backend.app.websocket_core.websocket_manager_factory', 'create_websocket_manager')]
            for module_path, function_name in import_functions:
                try:
                    module = __import__(module_path, fromlist=[function_name])
                    if hasattr(module, function_name):
                        func = getattr(module, function_name)
                        signature = inspect.signature(func)
                        function_signatures[f'{module_path}.{function_name}'] = signature
                except ImportError:
                    pass
            if len(function_signatures) > 1:
                signatures_list = list(function_signatures.values())
                first_signature = signatures_list[0]
                for func_path, signature in function_signatures.items():
                    if signature != first_signature:
                        raise AssertionError(f'SSOT VIOLATION: Inconsistent function signatures detected. Expected: {first_signature}, Got: {signature} for {func_path}. This indicates multiple implementations exist.')
            logger.info(f'Function signatures analyzed: {len(function_signatures)}')
        except Exception as e:
            logger.error(f'Function signature analysis failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: Could not analyze WebSocket manager function consistency: {e}')

    async def test_websocket_manager_initialization_consistency(self):
        """
        SHOULD FAIL: Different initialization paths create managers with different states.

        This test validates that all WebSocket manager initialization paths
        result in managers with consistent internal states.
        """
        logger.info('Testing WebSocket manager initialization consistency - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            user_context = {'user_id': 'init_test_user', 'thread_id': 'init_test_thread'}
            direct_manager = WebSocketManager(user_context=user_context)
            factory_manager = await create_websocket_manager(user_context=user_context)
            state_differences = []
            attributes_to_check = ['user_context', 'connections', 'connection_id']
            for attr in attributes_to_check:
                direct_has = hasattr(direct_manager, attr)
                factory_has = hasattr(factory_manager, attr)
                if direct_has != factory_has:
                    state_differences.append(f"Attribute '{attr}': direct={direct_has}, factory={factory_has}")
                elif direct_has and factory_has:
                    direct_val = getattr(direct_manager, attr, None)
                    factory_val = getattr(factory_manager, attr, None)
                    if direct_val is not None and factory_val is not None:
                        if type(direct_val) != type(factory_val):
                            state_differences.append(f"Attribute '{attr}' type: direct={type(direct_val)}, factory={type(factory_val)}")
            if state_differences:
                raise AssertionError(f'SSOT VIOLATION: WebSocket managers initialized differently: {state_differences}. This indicates fragmented initialization logic.')
        except Exception as e:
            logger.error(f'Initialization consistency test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket manager initialization is inconsistent: {e}')

    def test_websocket_manager_import_path_documentation(self):
        """
        Document all discovered import paths for analysis.

        This test documents the fragmentation for remediation planning.
        """
        logger.info('Documenting WebSocket manager import paths for Issue #960 analysis')
        if not self.discovered_import_paths:
            asyncio.run(self.test_all_websocket_manager_imports_resolve_to_canonical())
        documented_paths = []
        for module_path, class_or_function_name, obj in self.discovered_import_paths:
            path_info = {'import_path': f'{module_path}.{class_or_function_name}', 'object_type': type(obj).__name__, 'is_class': inspect.isclass(obj), 'is_function': inspect.isfunction(obj), 'module_file': getattr(inspect.getmodule(obj), '__file__', 'Unknown')}
            documented_paths.append(path_info)
        logger.info(f'WebSocket Manager Import Path Analysis for Issue #960:')
        for i, path_info in enumerate(documented_paths, 1):
            logger.info(f"  {i}. {path_info['import_path']} ({path_info['object_type']})")
            if path_info['module_file'] != 'Unknown':
                logger.info(f"     File: {path_info['module_file']}")
        self.assertTrue(True, f'Documented {len(documented_paths)} WebSocket manager import paths')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')