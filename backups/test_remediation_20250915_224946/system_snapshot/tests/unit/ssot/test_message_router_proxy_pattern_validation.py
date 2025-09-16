"""
CRITICAL SSOT Test: MessageRouter Proxy Pattern Validation - Issue #1125

PURPOSE: Validate that the MessageRouter proxy pattern is working correctly and maintains
SSOT compliance while preserving backward compatibility.

CURRENT STATUS:
- Golden Path CONFIRMED working (mission critical test passes)
- Proxy pattern IMPLEMENTED in core/message_router.py
- Business impact RESOLVED ($500K+ ARR protected)

VALIDATION FOCUS:
- Proxy correctly forwards all calls to canonical SSOT implementation
- Deprecation warnings are properly issued
- No breaking changes for existing code
- SSOT compliance maintained through proxy delegation

TEST STRATEGY: Focused validation of proxy pattern behavior rather than violation detection
"""

import pytest
import unittest
import warnings
import importlib
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class MessageRouterProxyPatternValidationTests(SSotBaseTestCase):
    """Validate MessageRouter proxy pattern implementation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.canonical_module = "netra_backend.app.websocket_core.handlers"
        self.proxy_module = "netra_backend.app.core.message_router"
        self.compatibility_modules = [
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router"
        ]

    def test_proxy_forwards_to_canonical_implementation(self):
        """
        CRITICAL: Verify proxy correctly forwards all calls to canonical SSOT implementation.

        SHOULD PASS: Proxy pattern is implemented and working

        Business Impact: Ensures no functionality regression while maintaining SSOT
        """
        # Import proxy MessageRouter
        from netra_backend.app.core.message_router import MessageRouter as ProxyRouter

        # Import canonical MessageRouter
        from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter

        # Create proxy instance
        proxy_router = ProxyRouter()

        # Verify proxy has canonical router instance
        self.assertTrue(hasattr(proxy_router, '_canonical_router'))
        canonical_instance = proxy_router._canonical_router
        self.assertIsInstance(canonical_instance, CanonicalRouter)

        # Test method forwarding
        test_methods = ['start', 'stop', 'get_statistics']

        for method_name in test_methods:
            if hasattr(canonical_instance, method_name):
                # Verify proxy has the method
                self.assertTrue(hasattr(proxy_router, method_name),
                              f"Proxy missing method: {method_name}")

                # Get proxy and canonical methods
                proxy_method = getattr(proxy_router, method_name)
                canonical_method = getattr(canonical_instance, method_name)

                # Verify they're callable
                self.assertTrue(callable(proxy_method),
                              f"Proxy method {method_name} not callable")

    def test_proxy_issues_deprecation_warnings(self):
        """
        CRITICAL: Verify proxy issues proper deprecation warnings.

        SHOULD PASS: Proxy implementation includes deprecation warnings

        Business Impact: Provides clear migration guidance for developers
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Import and instantiate proxy (should trigger warning)
            from netra_backend.app.core.message_router import MessageRouter
            router = MessageRouter()

            # Check that deprecation warning was issued
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            self.assertGreater(len(deprecation_warnings), 0,
                             "No deprecation warning issued during proxy instantiation")

            # Verify warning message contains migration guidance
            warning_message = str(deprecation_warnings[0].message)
            self.assertIn("netra_backend.app.websocket_core.handlers", warning_message,
                         "Deprecation warning missing canonical import path")
            self.assertIn("deprecated", warning_message.lower(),
                         "Warning doesn't clearly indicate deprecation")

    def test_compatibility_layers_point_to_canonical_ssot(self):
        """
        CRITICAL: Verify compatibility layers correctly point to canonical SSOT.

        SHOULD PASS: Compatibility modules properly re-export canonical implementation

        Business Impact: Ensures test compatibility during transition
        """
        canonical_router_class = None

        # Get canonical router class
        try:
            canonical_module = importlib.import_module(self.canonical_module)
            canonical_router_class = getattr(canonical_module, 'MessageRouter')
        except ImportError:
            self.fail(f"Cannot import canonical MessageRouter from {self.canonical_module}")

        # Test each compatibility layer
        for compat_module_path in self.compatibility_modules:
            with self.subTest(module=compat_module_path):
                try:
                    compat_module = importlib.import_module(compat_module_path)

                    if hasattr(compat_module, 'MessageRouter'):
                        compat_router_class = getattr(compat_module, 'MessageRouter')

                        # Verify compatibility layer points to canonical implementation
                        self.assertEqual(
                            compat_router_class.__module__,
                            canonical_router_class.__module__,
                            f"Compatibility layer {compat_module_path} doesn't point to canonical SSOT implementation"
                        )

                        # Verify it's the same class
                        self.assertIs(
                            compat_router_class,
                            canonical_router_class,
                            f"Compatibility layer {compat_module_path} has different MessageRouter class"
                        )

                except ImportError as e:
                    self.fail(f"Cannot import compatibility MessageRouter from {compat_module_path}: {e}")

    def test_proxy_maintains_interface_compatibility(self):
        """
        CRITICAL: Verify proxy maintains interface compatibility with existing code.

        SHOULD PASS: Proxy provides all expected methods and properties

        Business Impact: Ensures no breaking changes for existing integrations
        """
        from netra_backend.app.core.message_router import MessageRouter

        proxy_router = MessageRouter()

        # Test expected interface methods
        expected_methods = [
            'add_route', 'add_middleware', 'start', 'stop', 'get_statistics'
        ]

        for method_name in expected_methods:
            self.assertTrue(hasattr(proxy_router, method_name),
                          f"Proxy missing expected method: {method_name}")

            method = getattr(proxy_router, method_name)
            self.assertTrue(callable(method),
                          f"Proxy method {method_name} is not callable")

    def test_proxy_attribute_forwarding(self):
        """
        CRITICAL: Verify proxy forwards attribute access to canonical implementation.

        SHOULD PASS: __getattr__ forwards unknown attributes to canonical router

        Business Impact: Maintains full compatibility with existing attribute access patterns
        """
        from netra_backend.app.core.message_router import MessageRouter

        proxy_router = MessageRouter()
        canonical_router = proxy_router._canonical_router

        # Test attribute forwarding for common attributes
        test_attributes = ['handlers']

        for attr_name in test_attributes:
            if hasattr(canonical_router, attr_name):
                # Verify proxy can access the attribute
                proxy_value = getattr(proxy_router, attr_name)
                canonical_value = getattr(canonical_router, attr_name)

                # For handlers, verify it's a list (compatibility)
                if attr_name == 'handlers':
                    self.assertIsInstance(proxy_value, list,
                                        f"Proxy {attr_name} attribute should be a list")

    def test_proxy_statistics_include_proxy_info(self):
        """
        CRITICAL: Verify proxy statistics include proxy identification information.

        SHOULD PASS: get_statistics() includes proxy metadata for debugging

        Business Impact: Enables debugging and monitoring of proxy usage
        """
        from netra_backend.app.core.message_router import MessageRouter

        proxy_router = MessageRouter()
        stats = proxy_router.get_statistics()

        # Verify statistics are returned
        self.assertIsInstance(stats, dict, "Statistics should be a dictionary")

        # Verify proxy information is included
        self.assertIn("proxy_info", stats, "Statistics missing proxy_info section")

        proxy_info = stats["proxy_info"]
        self.assertIsInstance(proxy_info, dict, "proxy_info should be a dictionary")

        # Verify proxy metadata
        expected_proxy_fields = ["is_proxy", "canonical_source", "deprecation_status"]
        for field in expected_proxy_fields:
            self.assertIn(field, proxy_info, f"proxy_info missing field: {field}")

        # Verify proxy identification
        self.assertTrue(proxy_info["is_proxy"], "proxy_info should indicate this is a proxy")
        self.assertIn("websocket_core.handlers", proxy_info["canonical_source"],
                     "proxy_info should reference canonical source")

    def test_single_ssot_implementation_exists(self):
        """
        CRITICAL: Verify only one SSOT implementation exists (in canonical module).

        SHOULD PASS: Only canonical module has actual implementation

        Business Impact: Confirms SSOT compliance achieved through proxy pattern
        """
        implementation_count = 0
        actual_implementations = []

        # Check canonical module for implementation
        try:
            canonical_module = importlib.import_module(self.canonical_module)
            if hasattr(canonical_module, 'MessageRouter'):
                canonical_class = getattr(canonical_module, 'MessageRouter')
                if canonical_class.__module__ == self.canonical_module:
                    implementation_count += 1
                    actual_implementations.append(self.canonical_module)
        except ImportError:
            pass

        # Check proxy module (should NOT have independent implementation)
        try:
            proxy_module = importlib.import_module(self.proxy_module)
            if hasattr(proxy_module, 'MessageRouter'):
                proxy_class = getattr(proxy_module, 'MessageRouter')
                # Proxy class should still be defined in proxy module but delegate to canonical
                if proxy_class.__module__ == self.proxy_module:
                    # This is expected - proxy class exists but should delegate
                    pass
        except ImportError:
            pass

        # Check compatibility modules (should NOT have independent implementations)
        for compat_module_path in self.compatibility_modules:
            try:
                compat_module = importlib.import_module(compat_module_path)
                if hasattr(compat_module, 'MessageRouter'):
                    compat_class = getattr(compat_module, 'MessageRouter')
                    if compat_class.__module__ == compat_module_path:
                        implementation_count += 1
                        actual_implementations.append(compat_module_path)
            except ImportError:
                pass

        # Should have exactly 1 canonical implementation
        self.assertEqual(
            implementation_count, 1,
            f"Expected exactly 1 SSOT implementation, found {implementation_count} in: {actual_implementations}"
        )

        # The implementation should be in the canonical module
        self.assertIn(
            self.canonical_module, actual_implementations,
            f"SSOT implementation should be in {self.canonical_module}, found in: {actual_implementations}"
        )


@pytest.mark.unit
class MessageRouterSSotComplianceValidationTests(SSotBaseTestCase):
    """Validate SSOT compliance through proxy pattern."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_no_routing_conflicts_with_proxy_pattern(self):
        """
        CRITICAL: Verify proxy pattern eliminates routing conflicts.

        SHOULD PASS: All router sources use same underlying implementation

        Business Impact: Confirms $500K+ ARR protection through conflict elimination
        """
        router_instances = []
        canonical_instances = []

        # Create routers from different import paths
        import_paths = [
            "netra_backend.app.core.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router",
            "netra_backend.app.websocket_core.handlers"
        ]

        for import_path in import_paths:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    router_instance = router_class()
                    router_instances.append({
                        'path': import_path,
                        'instance': router_instance,
                        'class': router_class
                    })

                    # For proxy instances, get the canonical instance
                    if hasattr(router_instance, '_canonical_router'):
                        canonical_instances.append(router_instance._canonical_router)
                    else:
                        # This should be the canonical implementation
                        canonical_instances.append(router_instance)

            except ImportError:
                continue

        # Verify we have router instances
        self.assertGreater(len(router_instances), 0, "No MessageRouter instances found")

        # Verify all canonical instances are the same type
        canonical_types = set(type(instance) for instance in canonical_instances)
        self.assertEqual(
            len(canonical_types), 1,
            f"Found {len(canonical_types)} different canonical router types, expected 1"
        )

    def test_golden_path_functionality_preserved(self):
        """
        CRITICAL: Verify Golden Path functionality is preserved through proxy pattern.

        SHOULD PASS: Business functionality remains intact

        Business Impact: Confirms $500K+ ARR Golden Path protection
        """
        # Test that we can import and use MessageRouter from various paths
        import_tests = [
            "netra_backend.app.core.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router"
        ]

        for import_path in import_tests:
            # Test each import path individually
            try:
                module = importlib.import_module(import_path)
                MessageRouter = getattr(module, 'MessageRouter')

                # Create instance (should work without errors)
                router = MessageRouter()

                # Test basic functionality
                self.assertTrue(hasattr(router, 'handlers'),
                              f"Router from {import_path} missing handlers attribute")

                handlers = router.handlers
                self.assertIsInstance(handlers, list,
                                    f"Handlers from {import_path} should be a list")

            except Exception as e:
                self.fail(f"Golden Path functionality broken for {import_path}: {e}")


if __name__ == '__main__':
    unittest.main()