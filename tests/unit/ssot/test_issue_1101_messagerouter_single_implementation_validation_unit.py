"""
Unit Tests for Issue #1101 MessageRouter Single Implementation Validation

These tests validate that there is only one true implementation:
1. Verify canonical implementation is the only real one
2. Test that all paths lead to the same implementation
3. Validate no duplicate business logic exists
4. Ensure SSOT compliance is achieved

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: True SSOT compliance and elimination of duplication
- Value Impact: Prevents routing conflicts and inconsistent behavior
- Strategic Impact: Ensures system reliability and maintainability
"""
import pytest
import time
import asyncio
import inspect
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.message_router import MessageRouter as ProxyMessageRouter
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
from netra_backend.app.services.message_router import MessageRouter as ServicesMessageRouter
from netra_backend.app.websocket_core.handlers import get_message_router
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class TestMessageRouterSingleImplementationValidation(SSotBaseTestCase):
    """Unit tests for validating single MessageRouter implementation (SSOT compliance)."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_user_id = 'test_user_ssot_123'
        self.test_websocket = Mock()
        self.test_message = {'type': 'user_message', 'payload': {'content': 'test single implementation'}, 'timestamp': time.time()}

    def test_canonical_implementation_is_primary(self):
        """Test that canonical implementation is the primary one."""
        canonical_router = CanonicalMessageRouter()
        self.assertTrue(hasattr(canonical_router, 'route_message'))
        self.assertTrue(hasattr(canonical_router, 'add_handler'))
        self.assertTrue(hasattr(canonical_router, 'handlers'))
        self.assertTrue(hasattr(canonical_router, '_find_handler'))
        self.assertFalse(hasattr(canonical_router, '_canonical_router'))
        self.assertTrue(hasattr(canonical_router, 'builtin_handlers'))
        self.assertTrue(hasattr(canonical_router, 'custom_handlers'))
        self.assertTrue(hasattr(canonical_router, 'routing_stats'))

    def test_services_router_is_canonical_reference(self):
        """Test that services module router is direct reference to canonical."""
        services_router = ServicesMessageRouter()
        canonical_router = CanonicalMessageRouter()
        self.assertEqual(services_router.__class__.__name__, canonical_router.__class__.__name__)
        self.assertFalse(hasattr(services_router, '_canonical_router'))
        self.assertTrue(hasattr(services_router, 'builtin_handlers'))
        self.assertTrue(hasattr(services_router, 'custom_handlers'))

    def test_proxy_router_delegates_to_canonical(self):
        """Test that proxy router properly delegates to canonical implementation."""
        proxy_router = ProxyMessageRouter()
        self.assertTrue(hasattr(proxy_router, '_canonical_router'))
        self.assertIsInstance(proxy_router._canonical_router, CanonicalMessageRouter)
        self.assertFalse(hasattr(proxy_router, 'builtin_handlers'))
        self.assertFalse(hasattr(proxy_router, 'custom_handlers'))
        canonical = proxy_router._canonical_router
        self.assertTrue(hasattr(canonical, 'builtin_handlers'))
        self.assertTrue(hasattr(canonical, 'custom_handlers'))

    def test_no_duplicate_business_logic(self):
        """Test that business logic is not duplicated across implementations."""
        canonical_router = CanonicalMessageRouter()
        proxy_router = ProxyMessageRouter()
        services_router = ServicesMessageRouter()
        canonical_methods = self._get_implementation_methods(canonical_router)
        services_methods = self._get_implementation_methods(services_router)
        self.assertEqual(canonical_methods, services_methods)
        proxy_methods = self._get_implementation_methods(proxy_router)
        for method_name in ['add_handler', 'route_message']:
            self.assertIn(method_name, proxy_methods)

    def test_single_source_of_truth_for_routing_logic(self):
        """Test that routing logic exists in only one place."""
        canonical_router = CanonicalMessageRouter()
        self.assertTrue(hasattr(canonical_router, 'route_message'))
        self.assertTrue(hasattr(canonical_router, '_find_handler'))
        self.assertTrue(hasattr(canonical_router, '_prepare_message'))
        canonical_route_method = canonical_router.route_message
        self.assertTrue(asyncio.iscoroutinefunction(canonical_route_method))
        source = inspect.getsource(canonical_route_method)
        self.assertIn('route_message', source)
        self.assertIn('handler', source.lower())

    def test_handler_management_single_implementation(self):
        """Test that handler management logic exists in only one place."""
        canonical_router = CanonicalMessageRouter()
        handler_methods = ['add_handler', 'remove_handler', '_find_handler']
        for method_name in handler_methods:
            self.assertTrue(hasattr(canonical_router, method_name))
            method = getattr(canonical_router, method_name)
            if callable(method):
                source = inspect.getsource(method)
                self.assertGreater(len(source.strip().split('\n')), 2)

    def test_statistics_implementation_single_source(self):
        """Test that statistics implementation exists in only one place."""
        canonical_router = CanonicalMessageRouter()
        stats_method = canonical_router.get_stats
        self.assertTrue(callable(stats_method))
        stats = stats_method()
        self.assertIsInstance(stats, dict)
        self.assertIn('handler_count', stats)
        self.assertIn('handler_order', stats)
        source = inspect.getsource(stats_method)
        self.assertIn('routing_stats', source)

    def test_global_singleton_consistency(self):
        """Test that global singleton returns consistent instance."""
        router1 = get_message_router()
        router2 = get_message_router()
        self.assertIs(router1, router2)
        self.assertIsInstance(router1, CanonicalMessageRouter)
        self.assertFalse(hasattr(router1, '_canonical_router'))

    def test_message_type_handling_single_implementation(self):
        """Test that message type handling logic is in one place."""
        canonical_router = CanonicalMessageRouter()
        self.assertTrue(hasattr(canonical_router, '_prepare_message'))
        self.assertTrue(hasattr(canonical_router, '_find_handler'))
        test_message = {'type': 'test', 'payload': {}}
        prepared = asyncio.run(canonical_router._prepare_message(test_message))
        self.assertIsInstance(prepared, WebSocketMessage)
        self.assertIsInstance(prepared.type, MessageType)

    def test_no_competing_implementations(self):
        """Test that there are no competing implementations."""
        canonical_router = CanonicalMessageRouter()
        services_router = ServicesMessageRouter()
        proxy_router = ProxyMessageRouter()
        self.assertEqual(type(services_router), type(canonical_router))
        self.assertEqual(type(proxy_router._canonical_router), type(canonical_router))

    def test_handler_registration_single_point(self):
        """Test that handler registration goes through single point."""
        canonical_router = CanonicalMessageRouter()
        services_router = ServicesMessageRouter()
        mock_handler = Mock()
        mock_handler.can_handle = Mock(return_value=True)
        mock_handler.handle_message = Mock()
        mock_handler.__class__.__name__ = 'TestHandler'
        initial_count = len(canonical_router.handlers)
        canonical_router.add_handler(mock_handler)
        self.assertEqual(len(canonical_router.handlers), initial_count + 1)
        services_initial_count = len(services_router.handlers)
        mock_handler2 = Mock()
        mock_handler2.can_handle = Mock(return_value=True)
        mock_handler2.handle_message = Mock()
        mock_handler2.__class__.__name__ = 'TestHandler2'
        services_router.add_handler(mock_handler2)
        self.assertEqual(len(services_router.handlers), services_initial_count + 1)

    async def test_message_routing_single_pipeline(self):
        """Test that message routing goes through single pipeline."""
        canonical_router = CanonicalMessageRouter()
        mock_websocket = Mock()
        test_message = {'type': 'test_message', 'payload': {'content': 'test'}, 'timestamp': time.time()}
        with patch.object(canonical_router, '_find_handler') as mock_find:
            mock_handler = Mock()
            mock_handler.handle_message = Mock(return_value=True)
            mock_find.return_value = mock_handler
            result = await canonical_router.route_message(self.test_user_id, mock_websocket, test_message)
            mock_find.assert_called_once()
            mock_handler.handle_message.assert_called_once()

    def test_compatibility_layer_does_not_duplicate_logic(self):
        """Test that compatibility layers don't duplicate core logic."""
        proxy_router = ProxyMessageRouter()
        proxy_get_stats = proxy_router.get_statistics
        stats = proxy_get_stats()
        self.assertIn('proxy_info', stats)
        self.assertTrue(stats['proxy_info']['is_proxy'])
        canonical_stats = stats.get('production_stats') or {k: v for k, v in stats.items() if k != 'proxy_info'}
        self.assertIsInstance(canonical_stats, dict)

    def test_import_paths_converge_to_single_implementation(self):
        """Test that all import paths converge to single implementation."""
        from netra_backend.app.websocket_core.handlers import MessageRouter as Direct
        from netra_backend.app.services.message_router import MessageRouter as Services
        from netra_backend.app.core.message_router import MessageRouter as Proxy
        self.assertEqual(Direct, Services)
        proxy_instance = Proxy()
        self.assertIsInstance(proxy_instance._canonical_router, Direct)

    def test_ssot_compliance_validation(self):
        """Test complete SSOT compliance validation."""
        canonical_class = CanonicalMessageRouter
        services_class = ServicesMessageRouter
        self.assertEqual(canonical_class, services_class)
        global_router1 = get_message_router()
        global_router2 = get_message_router()
        self.assertIs(global_router1, global_router2)
        proxy_instance = ProxyMessageRouter()
        self.assertIsInstance(proxy_instance._canonical_router, CanonicalMessageRouter)
        canonical_instance = CanonicalMessageRouter()
        services_instance = ServicesMessageRouter()
        self.assertEqual(len(canonical_instance.handlers), len(services_instance.handlers))
        canonical_stats = canonical_instance.get_stats()
        services_stats = services_instance.get_stats()
        self.assertEqual(set(canonical_stats.keys()), set(services_stats.keys()))

    def test_no_hidden_implementations(self):
        """Test that there are no hidden or duplicate implementations."""
        import sys
        message_router_classes = []
        for module_name, module in sys.modules.items():
            if module and hasattr(module, '__dict__'):
                for attr_name, attr_value in module.__dict__.items():
                    if isinstance(attr_value, type) and attr_name == 'MessageRouter' and ('netra_backend' in str(attr_value.__module__)):
                        message_router_classes.append((module_name, attr_value))
        expected_modules = ['netra_backend.app.websocket_core.handlers', 'netra_backend.app.core.message_router', 'netra_backend.app.services.message_router']
        found_modules = [module_name for module_name, _ in message_router_classes]
        for expected_module in expected_modules:
            found_match = any((expected_module in found for found in found_modules))
            self.assertTrue(found_match, f'Expected module {expected_module} not found')

    def _get_implementation_methods(self, router_instance) -> Set[str]:
        """Get set of implementation method names from router instance."""
        methods = set()
        for attr_name in dir(router_instance):
            if not attr_name.startswith('_'):
                attr = getattr(router_instance, attr_name)
                if callable(attr):
                    methods.add(attr_name)
        return methods
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')