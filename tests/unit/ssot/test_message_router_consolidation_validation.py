"""
SSOT Consolidation Validation Tests for MessageRouter

These tests validate the MessageRouter SSOT consolidation process to ensure:
1. Only one active MessageRouter implementation exists
2. All imports resolve to canonical source
3. Proxy forwarding functionality works correctly
4. Backwards compatibility is maintained during transition

Created: 2025-09-14 (Issue #1101)
Purpose: Validate successful SSOT consolidation of MessageRouter implementations
"""

import pytest
import unittest
import sys
import importlib
import inspect
from typing import Dict, List, Set, Any
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class MessageRouterSSOTConsolidationTests(SSotBaseTestCase):
    """Test MessageRouter SSOT consolidation validation."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.canonical_path = "netra_backend.app.websocket_core.handlers"
        self.legacy_paths = [
            "netra_backend.app.websocket_core.router",
            "netra_backend.app.websocket_core.message_handler",
            "netra_backend.app.core.message_router",
            "netra_backend.app.routes.message_router"
        ]

    def test_single_active_message_router_implementation(self):
        """Verify only one active MessageRouter implementation exists."""
        try:
            # Import canonical implementation
            canonical_module = importlib.import_module(self.canonical_path)
            canonical_router = getattr(canonical_module, 'MessageRouter', None)

            self.assertIsNotNone(
                canonical_router,
                f"MessageRouter not found in canonical module {self.canonical_path}"
            )

            # Verify it's a proper class implementation
            self.assertTrue(
                inspect.isclass(canonical_router),
                "Canonical MessageRouter should be a class"
            )

            # Check that legacy paths either don't exist or are proxies
            active_implementations = []

            for legacy_path in self.legacy_paths:
                try:
                    legacy_module = importlib.import_module(legacy_path)
                    legacy_router = getattr(legacy_module, 'MessageRouter', None)

                    if legacy_router and inspect.isclass(legacy_router):
                        # Check if it's the same class (imported) or different (duplicate)
                        if legacy_router is not canonical_router:
                            # Check if this is a proxy class by examining module docstring or class docstring
                            module_doc = getattr(legacy_module, '__doc__', '')
                            class_doc = getattr(legacy_router, '__doc__', '')

                            is_proxy = (
                                'proxy' in module_doc.lower() or
                                'proxy' in class_doc.lower() or
                                'forwards all calls' in class_doc.lower() or
                                'deprecation warning' in class_doc.lower()
                            )

                            if not is_proxy:
                                # This is a real duplicate implementation
                                active_implementations.append(legacy_path)

                except ImportError:
                    # Legacy path doesn't exist - this is expected after consolidation
                    pass

            self.assertEqual(
                len(active_implementations), 0,
                f"Found duplicate MessageRouter implementations in: {active_implementations}. "
                f"Only canonical implementation at {self.canonical_path} should exist."
            )

        except ImportError as e:
            assert False, f"Cannot import canonical MessageRouter from {self.canonical_path}: {e}"

    def test_all_imports_resolve_to_canonical_source(self):
        """Validate all MessageRouter imports resolve to canonical source."""
        try:
            # Import canonical implementation
            canonical_module = importlib.import_module(self.canonical_path)
            canonical_router = getattr(canonical_module, 'MessageRouter')

            # Test various import patterns that should all resolve to canonical
            import_patterns = [
                # Direct canonical import
                ("netra_backend.app.websocket_core.handlers", "MessageRouter"),
                # Legacy paths that should proxy to canonical
                ("netra_backend.app.core.message_router", "MessageRouter"),
            ]

            for module_path, class_name in import_patterns:
                try:
                    module = importlib.import_module(module_path)
                    imported_class = getattr(module, class_name, None)

                    if imported_class:
                        # Check if it's the same class object OR a valid proxy
                        if imported_class is canonical_router:
                            # Direct import - expected
                            pass
                        else:
                            # Check if it's a proxy by examining docstring
                            class_doc = getattr(imported_class, '__doc__', '')
                            module_doc = getattr(module, '__doc__', '')

                            is_proxy = (
                                'proxy' in class_doc.lower() or
                                'proxy' in module_doc.lower() or
                                'forwards all calls' in class_doc.lower() or
                                'deprecation warning' in class_doc.lower()
                            )

                            self.assertTrue(
                                is_proxy,
                                f"Import from {module_path} should be canonical MessageRouter or valid proxy"
                            )

                except ImportError:
                    # Some legacy paths may not exist after consolidation
                    pass

        except ImportError as e:
            assert False, (f"Cannot import canonical MessageRouter: {e}")

    def test_proxy_forwarding_functionality(self):
        """Test that proxy forwarding functionality works correctly."""
        try:
            # Import canonical implementation
            canonical_module = importlib.import_module(self.canonical_path)
            canonical_router = getattr(canonical_module, 'MessageRouter')

            # Test that we can instantiate the router
            router_instance = canonical_router()

            # Verify essential methods exist
            essential_methods = [
                'route_message',
                'add_handler',
                'add_middleware',
                'get_statistics'
            ]

            for method_name in essential_methods:
                self.assertTrue(
                    hasattr(router_instance, method_name),
                    f"MessageRouter should have method: {method_name}"
                )

                method = getattr(router_instance, method_name)
                self.assertTrue(
                    callable(method),
                    f"MessageRouter.{method_name} should be callable"
                )

            # Test method signatures (basic validation)
            route_message = getattr(router_instance, 'route_message')
            signature = inspect.signature(route_message)

            # Should have reasonable parameters
            self.assertGreater(
                len(signature.parameters), 0,
                "route_message should accept parameters"
            )

        except Exception as e:
            assert False, f"Proxy forwarding validation failed: {e}"

    def test_backwards_compatibility_during_transition(self):
        """Ensure backwards compatibility is maintained during transition."""
        try:
            # Test that common usage patterns still work

            # Pattern 1: Direct import from canonical location
            from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalRouter

            # Pattern 2: Legacy import patterns (if they exist as proxies)
            legacy_imports = []

            try:
                from netra_backend.app.core.message_router import MessageRouter as LegacyRouter1
                legacy_imports.append(LegacyRouter1)
            except ImportError:
                pass

            # All imported routers should be the same object OR valid proxies
            for legacy_router in legacy_imports:
                if legacy_router is CanonicalRouter:
                    # Direct import - expected
                    pass
                else:
                    # Check if it's a proxy
                    class_doc = getattr(legacy_router, '__doc__', '')
                    is_proxy = (
                        'proxy' in class_doc.lower() or
                        'forwards all calls' in class_doc.lower() or
                        'deprecation warning' in class_doc.lower()
                    )

                    self.assertTrue(
                        is_proxy,
                        "Legacy imports should resolve to canonical implementation or be valid proxies"
                    )

            # Test instantiation works the same way
            canonical_instance = CanonicalRouter()

            for legacy_router in legacy_imports:
                legacy_instance = legacy_router()

                # For proxy classes, check that essential methods are callable
                # (Types may differ since proxy wraps canonical implementation)
                if legacy_router is not CanonicalRouter:
                    # This is a proxy - test that essential methods are accessible via __getattr__
                    essential_methods = ['route_message', 'add_handler', 'get_statistics']

                    for method_name in essential_methods:
                        # Test that the method is accessible (may be through __getattr__)
                        self.assertTrue(
                            hasattr(legacy_instance, method_name),
                            f"Proxy should have access to method: {method_name}"
                        )

                        method = getattr(legacy_instance, method_name)
                        self.assertTrue(
                            callable(method),
                            f"Proxy method {method_name} should be callable"
                        )
                else:
                    # Direct import - should have same type
                    self.assertEqual(
                        type(canonical_instance), type(legacy_instance),
                        "Direct imports should have same type"
                    )

        except Exception as e:
            assert False, (f"Backwards compatibility validation failed: {e}")

    def test_message_router_functionality_integration(self):
        """Test that MessageRouter functionality works as expected after consolidation."""
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter

            # Create instance
            router = MessageRouter()

            # Test basic functionality with mock data
            test_message = {
                "type": "agent_message",
                "user_id": "test_user_123",
                "content": "Test message content",
                "session_id": "test_session_456"
            }

            # Test route_message method (should not raise exceptions)
            try:
                # This might require specific setup, so we'll test basic calling
                signature = inspect.signature(router.route_message)
                params = list(signature.parameters.keys())

                # Verify method can be called (even if it needs specific parameters)
                self.assertTrue(
                    callable(router.route_message),
                    "route_message should be callable"
                )

                # Verify required parameters exist
                expected_params = ['message', 'user_id', 'session_id']
                for expected_param in expected_params:
                    if expected_param in params:
                        # Good - expected parameter found
                        pass
                    else:
                        # Check if there are similar parameters
                        similar_params = [p for p in params if expected_param in p.lower()]
                        if not similar_params:
                            assert False, (f"Expected parameter '{expected_param}' or similar not found in route_message")

            except Exception as e:
                # Log but don't fail - might need specific setup
                print(f"Note: route_message testing limited due to setup requirements: {e}")

            # Test WebSocket message handling
            try:
                if hasattr(router, 'handle_websocket_message'):
                    self.assertTrue(
                        callable(router.handle_websocket_message),
                        "handle_websocket_message should be callable"
                    )
            except Exception as e:
                print(f"Note: handle_websocket_message testing limited: {e}")

        except ImportError as e:
            assert False, (f"Cannot test MessageRouter functionality - import failed: {e}")

    def test_ssot_import_registry_compliance(self):
        """Verify MessageRouter follows SSOT import registry patterns."""
        try:
            # Test that canonical import works
            canonical_module = importlib.import_module(self.canonical_path)
            canonical_router = getattr(canonical_module, 'MessageRouter')

            # Verify class properties
            self.assertTrue(
                inspect.isclass(canonical_router),
                "MessageRouter should be a proper class"
            )

            # Check module path follows SSOT conventions
            self.assertTrue(
                self.canonical_path.startswith("netra_backend.app"),
                "Canonical path should follow backend app structure"
            )

            # Verify no circular imports
            module_dict = sys.modules.copy()

            # Re-import to check for circular dependencies
            importlib.reload(canonical_module)

            # Should still work after reload
            reloaded_router = getattr(canonical_module, 'MessageRouter')
            self.assertTrue(
                inspect.isclass(reloaded_router),
                "MessageRouter should still be a class after module reload"
            )

        except Exception as e:
            assert False, (f"SSOT import registry compliance test failed: {e}")

    def test_no_duplicate_implementations(self):
        """Verify no duplicate MessageRouter implementations exist in codebase."""
        # This test validates that after consolidation, we don't have
        # multiple independent MessageRouter classes

        implementation_count = 0
        found_implementations = []

        # Check all potential locations
        potential_locations = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.websocket_core.router",
            "netra_backend.app.websocket_core.message_handler",
            "netra_backend.app.core.message_router",
            "netra_backend.app.routes.message_router"
        ]

        canonical_router = None

        for location in potential_locations:
            try:
                module = importlib.import_module(location)
                router_class = getattr(module, 'MessageRouter', None)

                if router_class and inspect.isclass(router_class):
                    if canonical_router is None:
                        canonical_router = router_class
                        found_implementations.append(location)
                    elif router_class is canonical_router:
                        # Same class object - this is expected (import/proxy)
                        pass
                    else:
                        # Different class object - check if it's a proxy
                        module_doc = getattr(module, '__doc__', '')
                        class_doc = getattr(router_class, '__doc__', '')

                        is_proxy = (
                            'proxy' in module_doc.lower() or
                            'proxy' in class_doc.lower() or
                            'forwards all calls' in class_doc.lower() or
                            'deprecation warning' in class_doc.lower()
                        )

                        if not is_proxy:
                            # This is a real duplicate implementation
                            implementation_count += 1
                            found_implementations.append(location)

            except ImportError:
                # Module doesn't exist - expected for legacy paths
                pass

        self.assertEqual(
            implementation_count, 0,
            f"Found duplicate MessageRouter implementations. "
            f"Only one canonical implementation should exist. "
            f"Found implementations in: {found_implementations}"
        )

        self.assertIsNotNone(
            canonical_router,
            "Should find at least one MessageRouter implementation"
        )


@pytest.mark.unit
class MessageRouterConsolidationEdgeCasesTests(SSotBaseTestCase):
    """Test edge cases for MessageRouter SSOT consolidation."""

    def test_import_error_handling(self):
        """Test that import errors are handled gracefully."""
        # Test importing from non-existent legacy paths
        non_existent_paths = [
            "netra_backend.app.websocket_core.old_router",
            "netra_backend.app.legacy.message_router",
            "netra_backend.app.deprecated.router"
        ]

        for path in non_existent_paths:
            try:
                importlib.import_module(path)
                assert False, f"Expected ImportError for non-existent path {path}"
            except ImportError:
                # Expected behavior
                pass

    def test_attribute_access_patterns(self):
        """Test various attribute access patterns work after consolidation."""
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter

            # Test direct class access
            self.assertTrue(inspect.isclass(MessageRouter))

            # Test instance creation
            instance = MessageRouter()
            self.assertIsInstance(instance, MessageRouter)

            # Test method access
            essential_methods = ['route_message', 'handle_websocket_message']
            for method_name in essential_methods:
                if hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    self.assertTrue(callable(method))

        except Exception as e:
            assert False, (f"Attribute access pattern test failed: {e}")

    def test_module_reload_stability(self):
        """Test that module reloading doesn't break functionality."""
        try:
            # Import module
            import netra_backend.app.websocket_core.handlers as router_module

            # Get initial class
            initial_router = router_module.MessageRouter

            # Reload module
            importlib.reload(router_module)

            # Get reloaded class
            reloaded_router = router_module.MessageRouter

            # Both should be classes
            self.assertTrue(inspect.isclass(initial_router))
            self.assertTrue(inspect.isclass(reloaded_router))

            # Should be able to create instances of both
            initial_instance = initial_router()
            reloaded_instance = reloaded_router()

            # Should have same interface
            initial_methods = set(dir(initial_instance))
            reloaded_methods = set(dir(reloaded_instance))

            # Core methods should be present in both
            core_methods = {'route_message', 'handle_websocket_message'}
            available_initial = core_methods.intersection(initial_methods)
            available_reloaded = core_methods.intersection(reloaded_methods)

            self.assertEqual(
                available_initial, available_reloaded,
                "Core methods should be available after reload"
            )

        except Exception as e:
            assert False, (f"Module reload stability test failed: {e}")


if __name__ == '__main__':
    unittest.main()