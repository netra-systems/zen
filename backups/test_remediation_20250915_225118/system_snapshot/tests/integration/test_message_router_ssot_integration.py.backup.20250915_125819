"""
Integration Test: MessageRouter SSOT Integration Validation - Issue #1125

PURPOSE: Validate MessageRouter SSOT implementation works correctly in integration scenarios.
This focuses on testing the actual functionality rather than detecting violations.

SCOPE: Non-Docker integration test that validates:
- Proxy pattern works correctly
- All import paths lead to same functionality
- No routing conflicts occur
- Business functionality is preserved

EXECUTION: python -m pytest tests/integration/test_message_router_ssot_integration.py -v
"""

import pytest
import unittest
import asyncio
import warnings
from typing import Dict, List, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.integration
class TestMessageRouterSSOTIntegration(SSotAsyncTestCase):
    """Integration tests for MessageRouter SSOT compliance."""

    async def test_multiple_import_paths_same_functionality(self):
        """
        Integration Test: Verify all import paths provide same functionality.

        SHOULD PASS: Proxy pattern ensures consistent behavior across import paths

        Business Impact: Confirms existing code continues working during SSOT transition
        """
        # Test different import paths that should all work
        import_paths = [
            ("core", "netra_backend.app.core.message_router"),
            ("services", "netra_backend.app.services.message_router"),
            ("agents", "netra_backend.app.agents.message_router"),
            ("canonical", "netra_backend.app.websocket_core.handlers")
        ]

        routers = {}

        for name, import_path in import_paths:
            try:
                # Import and create router
                exec(f"from {import_path} import MessageRouter")
                router_class = locals()['MessageRouter']
                router = router_class()

                routers[name] = {
                    'router': router,
                    'import_path': import_path,
                    'handlers_count': len(router.handlers) if hasattr(router, 'handlers') else 0
                }

            except ImportError as e:
                self.fail(f"Failed to import MessageRouter from {import_path}: {e}")

        # Verify all routers have handlers
        for name, router_info in routers.items():
            self.assertGreater(
                router_info['handlers_count'], 0,
                f"Router from {name} ({router_info['import_path']}) has no handlers"
            )

        # Verify consistent handler counts (they should be same or similar)
        handler_counts = [info['handlers_count'] for info in routers.values()]
        unique_counts = set(handler_counts)

        # Allow for slight variation but should be mostly consistent
        self.assertLessEqual(
            len(unique_counts), 2,  # Allow up to 2 different counts (some variation acceptable)
            f"Too much variation in handler counts across routers: {dict((name, info['handlers_count']) for name, info in routers.items())}"
        )

    async def test_proxy_pattern_deprecation_warnings(self):
        """
        Integration Test: Verify proxy pattern issues appropriate warnings.

        SHOULD PASS: Proxy implementation includes proper deprecation warnings

        Business Impact: Ensures developers get migration guidance
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Import from deprecated path (should trigger warning)
            from netra_backend.app.core.message_router import MessageRouter
            router = MessageRouter()

            # Check for deprecation warnings
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            message_router_warnings = [
                w for w in deprecation_warnings
                if 'MessageRouter' in str(w.message) and 'deprecated' in str(w.message)
            ]

            self.assertGreater(
                len(message_router_warnings), 0,
                "No deprecation warning found for MessageRouter proxy usage"
            )

            # Verify warning provides migration guidance
            warning_message = str(message_router_warnings[0].message)
            self.assertIn(
                "netra_backend.app.websocket_core.handlers", warning_message,
                "Deprecation warning doesn't include canonical import path"
            )

    async def test_router_basic_functionality_integration(self):
        """
        Integration Test: Verify basic router functionality works across all import paths.

        SHOULD PASS: All routers provide basic functionality

        Business Impact: Confirms core business functionality is preserved
        """
        import_paths = [
            "netra_backend.app.core.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router"
        ]

        for import_path in import_paths:
            with self.subTest(import_path=import_path):
                # Import router
                module_parts = import_path.split('.')
                module_name = module_parts[-1]

                exec(f"from {import_path} import MessageRouter")
                router_class = locals()['MessageRouter']
                router = router_class()

                # Test basic functionality
                # 1. Has handlers
                self.assertTrue(
                    hasattr(router, 'handlers'),
                    f"Router from {import_path} missing handlers attribute"
                )

                handlers = router.handlers
                self.assertIsInstance(
                    handlers, list,
                    f"Router handlers from {import_path} should be a list"
                )

                # 2. Has expected methods
                expected_methods = ['start', 'stop']
                for method_name in expected_methods:
                    if hasattr(router, method_name):
                        method = getattr(router, method_name)
                        self.assertTrue(
                            callable(method),
                            f"Router method {method_name} from {import_path} is not callable"
                        )

                # 3. Can get statistics
                if hasattr(router, 'get_statistics'):
                    stats = router.get_statistics()
                    self.assertIsInstance(
                        stats, dict,
                        f"Router statistics from {import_path} should be a dictionary"
                    )

    async def test_no_routing_conflicts_integration(self):
        """
        Integration Test: Verify no routing conflicts occur with multiple router instances.

        SHOULD PASS: Proxy pattern eliminates routing conflicts

        Business Impact: Confirms $500K+ ARR protection through conflict elimination
        """
        # Create multiple router instances from different paths
        router_instances = []

        import_configs = [
            ("core", "netra_backend.app.core.message_router"),
            ("services", "netra_backend.app.services.message_router"),
            ("canonical", "netra_backend.app.websocket_core.handlers")
        ]

        for name, import_path in import_configs:
            try:
                exec(f"from {import_path} import MessageRouter")
                router_class = locals()['MessageRouter']
                router = router_class()

                router_instances.append({
                    'name': name,
                    'router': router,
                    'import_path': import_path,
                    'router_id': id(router),
                    'class_type': type(router).__name__
                })

            except ImportError:
                continue

        # Verify we have multiple router instances
        self.assertGreaterEqual(
            len(router_instances), 2,
            "Need at least 2 router instances to test for conflicts"
        )

        # Check for underlying canonical router consistency
        canonical_router_types = set()

        for router_info in router_instances:
            router = router_info['router']

            # For proxy routers, check the canonical router
            if hasattr(router, '_canonical_router'):
                canonical_router = router._canonical_router
                canonical_router_types.add(type(canonical_router).__name__)
            else:
                # This should be the canonical router itself
                canonical_router_types.add(type(router).__name__)

        # All canonical routers should be the same type
        self.assertEqual(
            len(canonical_router_types), 1,
            f"Found {len(canonical_router_types)} different canonical router types: {canonical_router_types}. "
            f"This indicates routing conflicts may exist."
        )

    async def test_handler_consistency_across_imports(self):
        """
        Integration Test: Verify handler consistency across different import paths.

        SHOULD PASS: All import paths provide access to same underlying handlers

        Business Impact: Ensures consistent message processing behavior
        """
        import_paths = [
            "netra_backend.app.core.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.websocket_core.handlers"
        ]

        handler_analyses = {}

        for import_path in import_paths:
            try:
                exec(f"from {import_path} import MessageRouter")
                router_class = locals()['MessageRouter']
                router = router_class()

                if hasattr(router, 'handlers'):
                    handlers = router.handlers
                    handler_types = [type(handler).__name__ for handler in handlers]

                    handler_analyses[import_path] = {
                        'handler_count': len(handlers),
                        'handler_types': set(handler_types),
                        'has_handlers': True
                    }
                else:
                    handler_analyses[import_path] = {
                        'handler_count': 0,
                        'handler_types': set(),
                        'has_handlers': False
                    }

            except ImportError:
                continue

        # Verify all routers have handlers
        for import_path, analysis in handler_analyses.items():
            self.assertTrue(
                analysis['has_handlers'],
                f"Router from {import_path} missing handlers"
            )

            self.assertGreater(
                analysis['handler_count'], 0,
                f"Router from {import_path} has no handlers"
            )

        # Check for reasonable consistency in handler types
        # (Allow some variation but should have core common handlers)
        if len(handler_analyses) > 1:
            all_handler_types = [analysis['handler_types'] for analysis in handler_analyses.values()]

            # Find common handlers across all router instances
            common_handlers = set.intersection(*all_handler_types) if all_handler_types else set()

            # Should have at least some common handlers
            self.assertGreater(
                len(common_handlers), 0,
                f"No common handlers found across router imports. Handler types: {dict((path, analysis['handler_types']) for path, analysis in handler_analyses.items())}"
            )


if __name__ == '__main__':
    unittest.main()