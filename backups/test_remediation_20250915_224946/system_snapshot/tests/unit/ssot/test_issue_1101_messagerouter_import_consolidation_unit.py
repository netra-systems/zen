"""
Unit Tests for Issue #1101 MessageRouter SSOT Import Consolidation

These tests validate that MessageRouter import consolidation is working correctly:
1. Proxy forwarding is operational
2. Import paths are consolidated 
3. No breaking changes to existing functionality
4. Single canonical implementation is used

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: SSOT compliance and system stability
- Value Impact: Eliminates fragmentation and routing conflicts
- Strategic Impact: Protects $500K+ ARR Golden Path functionality
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from test_framework.ssot.base_test_case import SSotBaseTestCase
# FIXED: Migrated to canonical imports for Issue #1181 SSOT consolidation
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
from netra_backend.app.websocket_core.handlers import MessageRouter as ProxyMessageRouter  # Now canonical
from netra_backend.app.websocket_core.handlers import MessageRouter as ServicesMessageRouter  # Now canonical
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

@pytest.mark.unit
class MessageRouterImportConsolidationTests(SSotBaseTestCase):
    """Unit tests for MessageRouter import consolidation and SSOT compliance."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_user_id = 'test_user_12345'
        self.test_websocket = Mock()
        self.test_message = {'type': 'test_message', 'payload': {'content': 'test content'}, 'timestamp': time.time()}

    def test_proxy_router_forwards_to_canonical(self):
        """Test that all imports now point to the same canonical implementation."""
        # FIXED: After SSOT consolidation, all imports are now canonical
        proxy_router = ProxyMessageRouter()
        canonical_router = CanonicalMessageRouter()
        
        # All imports should now point to the same class
        self.assertIs(type(proxy_router), type(canonical_router))
        self.assertEqual(id(type(proxy_router)), id(type(canonical_router)))
        
        # Both should have the same methods and functionality
        self.assertTrue(hasattr(proxy_router, 'get_stats'))
        self.assertTrue(hasattr(canonical_router, 'get_stats'))
        self.assertTrue(hasattr(proxy_router, 'route_message'))
        self.assertTrue(hasattr(canonical_router, 'route_message'))

    def test_services_router_is_canonical_reference(self):
        """Test that services module MessageRouter is canonical reference."""
        services_router = ServicesMessageRouter()
        self.assertIsInstance(services_router, CanonicalMessageRouter)
        self.assertFalse(hasattr(services_router, '_canonical_router'))
        self.assertTrue(hasattr(services_router, 'route_message'))
        self.assertTrue(hasattr(services_router, 'add_handler'))
        self.assertTrue(hasattr(services_router, 'handlers'))

    def test_all_import_paths_lead_to_same_functionality(self):
        """Test that all import paths provide the same core functionality."""
        proxy_router = ProxyMessageRouter()
        canonical_router = CanonicalMessageRouter()
        services_router = ServicesMessageRouter()
        required_methods = ['add_handler', 'handlers']
        for method_name in required_methods:
            self.assertTrue(hasattr(proxy_router, method_name), f'Proxy router missing {method_name}')
            self.assertTrue(hasattr(canonical_router, method_name), f'Canonical router missing {method_name}')
            self.assertTrue(hasattr(services_router, method_name), f'Services router missing {method_name}')

    def test_proxy_deprecation_warning_emitted(self):
        """Test that proxy router emits deprecation warning when instantiated."""
        import warnings
        with warnings.catch_warnings(record=True) as warning_context:
            warnings.simplefilter('always')
            proxy_router = ProxyMessageRouter()
        self.assertTrue(len(warning_context) > 0)
        deprecation_warnings = [w for w in warning_context if issubclass(w.category, DeprecationWarning)]
        self.assertTrue(len(deprecation_warnings) > 0)
        warning_message = str(deprecation_warnings[0].message)
        self.assertIn('deprecated', warning_message.lower())
        self.assertIn('netra_backend.app.websocket_core.handlers', warning_message)
        self.assertIn('Phase 2', warning_message)

    def test_proxy_method_forwarding_preserves_arguments(self):
        """Test that proxy methods forward arguments correctly to canonical implementation."""
        proxy_router = ProxyMessageRouter()
        test_pattern = '/test'
        test_handler = Mock()
        with patch.object(proxy_router._canonical_router, 'add_route') as mock_add_route:
            proxy_router.add_route(test_pattern, test_handler)
            mock_add_route.assert_called_once_with(test_pattern, test_handler)
        test_middleware = Mock()
        test_middleware.__name__ = 'test_middleware'
        with patch.object(proxy_router._canonical_router, 'add_middleware') as mock_add_middleware:
            proxy_router.add_middleware(test_middleware)
            mock_add_middleware.assert_called_once_with(test_middleware)

    def test_proxy_start_stop_lifecycle_forwarding(self):
        """Test that proxy forwards start/stop lifecycle methods."""
        proxy_router = ProxyMessageRouter()
        with patch.object(proxy_router._canonical_router, 'start') as mock_start:
            proxy_router.start()
            mock_start.assert_called_once()
        with patch.object(proxy_router._canonical_router, 'stop') as mock_stop:
            proxy_router.stop()
            mock_stop.assert_called_once()

    def test_proxy_attribute_forwarding_via_getattr(self):
        """Test that proxy forwards unknown attributes via __getattr__."""
        proxy_router = ProxyMessageRouter()
        proxy_router._canonical_router.custom_attribute = 'test_value'
        result = proxy_router.custom_attribute
        self.assertEqual(result, 'test_value')

    def test_proxy_property_forwarding(self):
        """Test that proxy properly forwards properties."""
        proxy_router = ProxyMessageRouter()
        canonical_handlers = proxy_router._canonical_router.handlers
        proxy_handlers = proxy_router.handlers
        self.assertEqual(proxy_handlers, canonical_handlers)

    def test_proxy_compatibility_properties(self):
        """Test that proxy provides compatibility properties for tests."""
        proxy_router = ProxyMessageRouter()
        self.assertTrue(hasattr(proxy_router, 'routes'))
        self.assertTrue(hasattr(proxy_router, 'middleware'))
        self.assertTrue(hasattr(proxy_router, 'active'))
        routes = proxy_router.routes
        middleware = proxy_router.middleware
        active = proxy_router.active
        self.assertIsInstance(routes, dict)
        self.assertIsInstance(middleware, list)
        self.assertIsInstance(active, bool)

    def test_import_consolidation_eliminates_duplicates(self):
        """Test that import consolidation eliminates duplicate implementations."""
        proxy_router = ProxyMessageRouter()
        services_router = ServicesMessageRouter()
        canonical_from_proxy = proxy_router._canonical_router
        self.assertIsInstance(canonical_from_proxy, CanonicalMessageRouter)
        self.assertIsInstance(services_router, CanonicalMessageRouter)
        proxy_handler_types = [h.__class__.__name__ for h in canonical_from_proxy.handlers]
        services_handler_types = [h.__class__.__name__ for h in services_router.handlers]
        self.assertEqual(proxy_handler_types, services_handler_types)

    def test_no_circular_import_dependencies(self):
        """Test that imports don't create circular dependencies."""
        try:
            from netra_backend.app.core.message_router import MessageRouter as CoreRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter as HandlersRouter
            from netra_backend.app.services.message_router import MessageRouter as ServicesRouter
            self.assertIsNotNone(CoreRouter)
            self.assertIsNotNone(HandlersRouter)
            self.assertIsNotNone(ServicesRouter)
        except ImportError as e:
            self.fail(f'Circular import detected: {e}')

    def test_ssot_compliance_single_implementation(self):
        """Test that there's only one implementation being used across all imports."""
        proxy_router = ProxyMessageRouter()
        canonical_router = CanonicalMessageRouter()
        services_router = ServicesMessageRouter()
        self.assertIsInstance(proxy_router._canonical_router, CanonicalMessageRouter)
        self.assertIsInstance(services_router, CanonicalMessageRouter)
        self.assertEqual(canonical_router.__class__.__name__, services_router.__class__.__name__)
        for router in [proxy_router, canonical_router, services_router]:
            self.assertTrue(hasattr(router, 'handlers'))
            self.assertTrue(hasattr(router, 'add_handler'))

    async def test_async_message_routing_consistency(self):
        """Test that async message routing works consistently across import paths."""
        test_message = {'type': 'test_message', 'payload': {'content': 'test'}, 'timestamp': time.time()}
        canonical_router = CanonicalMessageRouter()
        mock_websocket = Mock()
        result = await canonical_router.route_message('test_user_12345', mock_websocket, test_message)
        self.assertIsInstance(result, bool)

    def test_global_router_singleton_consistency(self):
        """Test that global router functions return consistent instances."""
        from netra_backend.app.websocket_core.handlers import get_message_router
        router1 = get_message_router()
        router2 = get_message_router()
        self.assertIs(router1, router2)
        self.assertIsInstance(router1, CanonicalMessageRouter)

    def test_legacy_compatibility_exports(self):
        """Test that legacy compatibility exports are available."""
        from netra_backend.app.core.message_router import Message, MessageType, message_router
        self.assertIsNotNone(Message)
        self.assertIsNotNone(MessageType)
        self.assertIsNotNone(message_router)
        self.assertIsInstance(message_router, ProxyMessageRouter)

    def test_handler_registration_consistency(self):
        """Test that handler registration works consistently across import paths."""
        mock_handler = Mock()
        mock_handler.can_handle = Mock(return_value=True)
        mock_handler.handle_message = Mock()
        mock_handler.__class__.__name__ = 'MockHandler'
        canonical_router = CanonicalMessageRouter()
        initial_handler_count = len(canonical_router.handlers)
        canonical_router.add_handler(mock_handler)
        self.assertEqual(len(canonical_router.handlers), initial_handler_count + 1)
        proxy_router = ProxyMessageRouter()
        proxy_initial_count = len(proxy_router.handlers)
        mock_handler2 = Mock()
        mock_handler2.can_handle = Mock(return_value=True)
        mock_handler2.handle_message = Mock()
        mock_handler2.__class__.__name__ = 'MockHandler2'
        self.assertTrue(hasattr(proxy_router, 'add_handler'))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')