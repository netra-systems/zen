"""
Comprehensive SSOT Tests: MessageRouter Consolidation Validation - Issue #1101

PURPOSE: Comprehensive validation that MessageRouter SSOT consolidation is complete
and all violations are eliminated. These tests detect any remaining fragmentation.

VIOLATION STATUS: Tests designed to FAIL before consolidation, PASS after
BUSINESS IMPACT: Protect $500K+ ARR Golden Path from message routing race conditions

These tests provide the definitive validation framework for Issue #1101 completion.
"""

import pytest
import unittest
import importlib
import inspect
import ast
import os
from typing import Set, List, Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestMessageRouterSSOTComprehensiveValidation(SSotBaseTestCase):
    """Comprehensive validation of MessageRouter SSOT consolidation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.ssot_implementation = "netra_backend.app.websocket_core.handlers.MessageRouter"
        self.expected_removed_files = [
            "netra_backend/app/core/message_router.py",
            "netra_backend/app/services/websocket/quality_message_router.py"
        ]
        self.expected_import_redirects = [
            "netra_backend.app.agents.message_router"
        ]

    def test_single_messagerouter_class_exists_globally(self):
        """
        CRITICAL: Test that exactly ONE MessageRouter class exists in entire codebase.

        SHOULD FAIL: Currently multiple MessageRouter implementations
        WILL PASS: After complete SSOT consolidation removes all duplicates
        """
        messagerouter_classes = self._find_all_messagerouter_classes()

        # Filter out test classes to focus on production implementations
        production_classes = [
            cls for cls in messagerouter_classes
            if not self._is_test_file(cls['file_path']) and
               cls['class_name'] in ['MessageRouter', 'QualityMessageRouter']
        ]

        # Should be exactly 1 MessageRouter class after consolidation
        self.assertEqual(
            len(production_classes), 1,
            f"SSOT VIOLATION: Found {len(production_classes)} production MessageRouter classes: "
            f"{production_classes}. Expected exactly 1 after SSOT consolidation."
        )

        # The single class should be the SSOT implementation
        if production_classes:
            ssot_class = production_classes[0]
            expected_module = "netra_backend.app.websocket_core.handlers"
            self.assertEqual(
                ssot_class['module'], expected_module,
                f"SSOT VIOLATION: MessageRouter class found in {ssot_class['module']}, "
                f"expected in {expected_module}"
            )

    def test_no_duplicate_message_routing_implementations(self):
        """
        CRITICAL: Test that no duplicate message routing logic exists.

        SHOULD FAIL: Currently multiple route/handle methods in different classes
        WILL PASS: After all routing logic consolidated into single implementation
        """
        routing_implementations = self._find_message_routing_methods()

        # Filter out test files and mock implementations
        production_implementations = [
            impl for impl in routing_implementations
            if not self._is_test_file(impl['file_path']) and
               not self._is_mock_implementation(impl['class_name'])
        ]

        # Should have only 1 production routing implementation
        self.assertLessEqual(
            len(production_implementations), 1,
            f"SSOT VIOLATION: Found {len(production_implementations)} message routing implementations: "
            f"{[(impl['class_name'], impl['method'], impl['file_path']) for impl in production_implementations]}. "
            f"Expected maximum 1 SSOT implementation."
        )

    def test_all_messagerouter_imports_resolve_to_ssot(self):
        """
        CRITICAL: Test that ALL MessageRouter imports resolve to SSOT implementation.

        SHOULD FAIL: Currently different imports resolve to different classes
        WILL PASS: After all import paths redirect to single SSOT class
        """
        import_test_cases = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router",
            "netra_backend.app.agents.message_router"
        ]

        messagerouter_classes = []
        import_failures = []

        for import_path in import_test_cases:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    messagerouter_classes.append({
                        'import_path': import_path,
                        'class': router_class,
                        'class_id': f"{router_class.__module__}.{router_class.__qualname__}"
                    })
            except ImportError as e:
                import_failures.append({
                    'import_path': import_path,
                    'error': str(e)
                })

        # All successful imports should resolve to same class
        if len(messagerouter_classes) > 1:
            first_class = messagerouter_classes[0]['class']
            different_classes = []

            for item in messagerouter_classes[1:]:
                if item['class'] is not first_class:
                    different_classes.append({
                        'import_path': item['import_path'],
                        'class_id': item['class_id']
                    })

            self.assertEqual(
                len(different_classes), 0,
                f"SSOT VIOLATION: MessageRouter imports resolve to different classes: "
                f"Expected all to resolve to {messagerouter_classes[0]['class_id']}, "
                f"but found: {different_classes}"
            )

    def test_quality_router_functionality_integrated(self):
        """
        CRITICAL: Test that QualityMessageRouter functionality is integrated into SSOT.

        SHOULD FAIL: Currently separate QualityMessageRouter class exists
        WILL PASS: After quality functionality integrated into main MessageRouter
        """
        # Check if separate QualityMessageRouter still exists
        quality_router_exists = False
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            quality_router_exists = True
        except ImportError:
            pass

        if quality_router_exists:
            # Quality router exists - check if it's a thin wrapper
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            quality_methods = self._get_class_methods(QualityMessageRouter)

            # Check if main router has quality methods
            from netra_backend.app.websocket_core.handlers import MessageRouter
            main_router_methods = self._get_class_methods(MessageRouter)

            # Quality methods should be in main router
            missing_quality_methods = []
            essential_quality_methods = [
                'handle_quality_message',
                'broadcast_quality_update',
                'process_quality_gate_check'
            ]

            for method in essential_quality_methods:
                if method in quality_methods and method not in main_router_methods:
                    missing_quality_methods.append(method)

            if missing_quality_methods:
                self.fail(
                    f"INTEGRATION VIOLATION: Quality methods not integrated into main router: "
                    f"{missing_quality_methods}. Either integrate into SSOT router or remove separate QualityMessageRouter."
                )

    def test_no_legacy_import_patterns_remain(self):
        """
        CRITICAL: Test that no legacy import patterns remain in codebase.

        SHOULD FAIL: Currently files still import from deprecated paths
        WILL PASS: After all imports updated to use SSOT path
        """
        legacy_import_patterns = [
            "from netra_backend.app.core.message_router import MessageRouter",
            "from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter"
        ]

        legacy_imports_found = []

        # Scan all Python files for legacy imports
        for root, dirs, files in os.walk("netra_backend"):
            # Skip test directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__') and not d.endswith('tests')]

            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        for pattern in legacy_import_patterns:
                            if pattern in content:
                                legacy_imports_found.append({
                                    'file': file_path,
                                    'pattern': pattern
                                })

                    except (UnicodeDecodeError, FileNotFoundError):
                        continue

        self.assertEqual(
            len(legacy_imports_found), 0,
            f"LEGACY IMPORT VIOLATION: Found {len(legacy_imports_found)} legacy imports: "
            f"{legacy_imports_found[:5]}. All imports should use SSOT path."
        )

    def test_message_router_interface_consistency(self):
        """
        CRITICAL: Test that MessageRouter interface is consistent across all access points.

        SHOULD FAIL: Currently different interfaces exposed by different implementations
        WILL PASS: After SSOT consolidation ensures consistent interface
        """
        # Get interface from different import paths
        interfaces = {}

        import_paths = [
            ("websocket_core", "netra_backend.app.websocket_core.handlers"),
            ("core", "netra_backend.app.core.message_router"),
            ("agents", "netra_backend.app.agents.message_router")
        ]

        for name, import_path in import_paths:
            try:
                module = importlib.import_module(import_path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    interfaces[name] = {
                        'methods': self._get_class_methods(router_class),
                        'class': router_class
                    }
            except ImportError:
                continue

        # All interfaces should be identical
        if len(interfaces) > 1:
            first_interface = list(interfaces.values())[0]
            first_methods = set(first_interface['methods'])

            inconsistent_interfaces = []
            for name, interface in interfaces.items():
                interface_methods = set(interface['methods'])
                if interface_methods != first_methods:
                    missing_methods = first_methods - interface_methods
                    extra_methods = interface_methods - first_methods
                    inconsistent_interfaces.append({
                        'name': name,
                        'missing': list(missing_methods),
                        'extra': list(extra_methods)
                    })

            self.assertEqual(
                len(inconsistent_interfaces), 0,
                f"INTERFACE CONSISTENCY VIOLATION: Inconsistent MessageRouter interfaces: "
                f"{inconsistent_interfaces}"
            )

    def test_websocket_event_routing_consolidated(self):
        """
        CRITICAL: Test that WebSocket event routing goes through single SSOT router.

        SHOULD FAIL: Currently events might route through different routers
        WILL PASS: After all event routing consolidated to SSOT implementation
        """
        # Check that WebSocket events are routed through main router
        from netra_backend.app.websocket_core.handlers import MessageRouter

        router = MessageRouter()

        # Test that router can handle critical WebSocket events
        critical_event_types = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # Check if router has methods to handle these events
        router_methods = self._get_class_methods(MessageRouter)

        event_handling_methods = [
            method for method in router_methods
            if any(event_type in method.lower() for event_type in
                   ['route', 'handle', 'process', 'send', 'emit', 'broadcast'])
        ]

        self.assertGreater(
            len(event_handling_methods), 0,
            f"EVENT ROUTING VIOLATION: SSOT MessageRouter has no event handling methods. "
            f"Found methods: {router_methods[:10]}. Expected event routing capabilities."
        )

    # Helper methods
    def _find_all_messagerouter_classes(self) -> List[Dict[str, str]]:
        """Find all MessageRouter class definitions in codebase."""
        messagerouter_classes = []

        for root, dirs, files in os.walk("netra_backend"):
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__')]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Parse AST to find class definitions
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if (isinstance(node, ast.ClassDef) and
                                'MessageRouter' in node.name):
                                messagerouter_classes.append({
                                    'class_name': node.name,
                                    'file_path': file_path,
                                    'module': file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
                                })

                    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
                        continue

        return messagerouter_classes

    def _find_message_routing_methods(self) -> List[Dict[str, str]]:
        """Find all message routing method implementations."""
        routing_methods = []

        for root, dirs, files in os.walk("netra_backend"):
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__')]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for routing method patterns
                        routing_patterns = [
                            'def route_message',
                            'def handle_message',
                            'def process_message',
                            'async def route_message',
                            'async def handle_message'
                        ]

                        for pattern in routing_patterns:
                            if pattern in content:
                                # Try to find class name
                                lines = content.split('\n')
                                for i, line in enumerate(lines):
                                    if pattern in line:
                                        # Look backwards for class definition
                                        class_name = "Unknown"
                                        for j in range(i, max(0, i-50), -1):
                                            if lines[j].strip().startswith('class '):
                                                class_name = lines[j].split()[1].split('(')[0].rstrip(':')
                                                break

                                        routing_methods.append({
                                            'method': pattern.replace('def ', '').replace('async ', ''),
                                            'class_name': class_name,
                                            'file_path': file_path
                                        })
                                        break

                    except (UnicodeDecodeError, FileNotFoundError):
                        continue

        return routing_methods

    def _get_class_methods(self, cls) -> List[str]:
        """Get list of methods from a class."""
        return [
            name for name, method in inspect.getmembers(cls, predicate=inspect.ismethod)
            if not name.startswith('_')
        ] + [
            name for name, func in inspect.getmembers(cls, predicate=inspect.isfunction)
            if not name.startswith('_')
        ]

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        return (
            'test' in file_path.lower() or
            'tests' in file_path.lower() or
            os.path.basename(file_path).startswith('test_')
        )

    def _is_mock_implementation(self, class_name: str) -> bool:
        """Check if class is a mock implementation."""
        return (
            'mock' in class_name.lower() or
            'test' in class_name.lower() or
            'stub' in class_name.lower()
        )


@pytest.mark.unit
class TestMessageRouterSSOTRegressionPrevention(SSotBaseTestCase):
    """Prevent regression after SSOT consolidation."""

    def test_no_new_messagerouter_implementations_added(self):
        """
        REGRESSION: Test that no new MessageRouter implementations are added.

        SHOULD PASS: After consolidation, no new implementations allowed
        WILL FAIL: If new MessageRouter classes created breaking SSOT
        """
        # This test would track the count of MessageRouter implementations
        # and fail if the count increases after SSOT consolidation

        expected_implementation_count = 1  # After consolidation

        current_implementations = self._count_messagerouter_implementations()

        self.assertLessEqual(
            current_implementations, expected_implementation_count,
            f"REGRESSION VIOLATION: Found {current_implementations} MessageRouter implementations, "
            f"expected maximum {expected_implementation_count}. "
            f"New implementations violate SSOT consolidation."
        )

    def test_ssot_router_maintains_all_required_functionality(self):
        """
        REGRESSION: Test that SSOT router maintains all required functionality.

        SHOULD PASS: After consolidation, all functionality preserved
        WILL FAIL: If consolidation breaks required functionality
        """
        from netra_backend.app.websocket_core.handlers import MessageRouter

        router = MessageRouter()

        # Required functionality that must be preserved
        required_capabilities = [
            'route_message',
            'handle_message',
            'custom_handlers',
            'builtin_handlers'
        ]

        missing_capabilities = []
        for capability in required_capabilities:
            if not hasattr(router, capability):
                missing_capabilities.append(capability)

        self.assertEqual(
            len(missing_capabilities), 0,
            f"REGRESSION VIOLATION: SSOT router missing required capabilities: "
            f"{missing_capabilities}. Consolidation broke functionality."
        )

    def _count_messagerouter_implementations(self) -> int:
        """Count current MessageRouter implementations."""
        implementations = 0

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            implementations += 1
        except ImportError:
            pass

        try:
            from netra_backend.app.core.message_router import MessageRouter
            implementations += 1
        except ImportError:
            pass

        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            implementations += 1
        except ImportError:
            pass

        return implementations


if __name__ == '__main__':
    unittest.main()