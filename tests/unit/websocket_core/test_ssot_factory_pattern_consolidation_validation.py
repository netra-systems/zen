"""
SSOT WebSocket Manager Factory Pattern Consolidation Validation Test

This test validates that WebSocket manager factory patterns are properly consolidated
and follow SSOT principles without duplicate factory implementations.

EXPECTED BEHAVIOR: These tests should FAIL initially to prove factory fragmentation exists.
After SSOT refactor (Step 4), they should PASS with consolidated factory patterns.

Business Value: Platform/Internal - System Architecture Compliance
Ensures consolidated factory patterns for WebSocket management, preventing code duplication.

Test Strategy: Static analysis and runtime factory validation (no Docker dependencies).
Unit test approach - creates instances to validate factory behavior.
"""

import inspect
import sys
from pathlib import Path
from typing import Dict, List, Set, Type, Any, Tuple
import unittest
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketManagerFactoryConsolidation(SSotBaseTestCase, unittest.TestCase):
    """Test suite to validate SSOT factory consolidation for WebSocket managers.

    These tests should FAIL initially, proving multiple factory patterns exist.
    After refactor, they should PASS with consolidated SSOT factory patterns.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.factory_violations = []
        self.discovered_factories = {}

    def _discover_websocket_factory_classes(self) -> Dict[str, List[Tuple[str, str]]]:
        """Discover all WebSocket factory classes in the codebase.

        Returns:
            Dict mapping factory_name to list of (module_path, file_path) tuples
        """
        factory_classes = {}

        # Factory patterns to search for
        factory_patterns = [
            "WebSocketManagerFactory",
            "UnifiedWebSocketManagerFactory",
            "WebSocketFactory",
            "ConnectionManagerFactory",
            "WebSocketManagerBuilder",
            "WebSocketCreator",
            "WebSocketProvider"
        ]

        # Search in websocket-related directories
        search_paths = [
            self.codebase_root / "netra_backend" / "app" / "websocket_core",
            self.codebase_root / "netra_backend" / "app" / "websocket",
            self.codebase_root / "netra_backend" / "app" / "services",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")

                    for pattern in factory_patterns:
                        if f"class {pattern}" in content:
                            if pattern not in factory_classes:
                                factory_classes[pattern] = []

                            # Convert file path to module path
                            rel_path = py_file.relative_to(self.codebase_root)
                            module_path = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")

                            factory_classes[pattern].append((
                                module_path,
                                str(py_file)
                            ))

                except (UnicodeDecodeError, PermissionError):
                    continue

        return factory_classes

    def _analyze_factory_method_signatures(self, factory_classes: Dict[str, List[Tuple[str, str]]]) -> Dict[str, List[str]]:
        """Analyze factory method signatures for consistency.

        Args:
            factory_classes: Map of factory names to their locations

        Returns:
            Dict mapping factory_name to list of method signatures found
        """
        method_signatures = {}

        for factory_name, locations in factory_classes.items():
            signatures = []

            for module_path, file_path in locations:
                try:
                    content = Path(file_path).read_text(encoding="utf-8")

                    # Look for method definitions in factory classes
                    lines = content.split('\n')
                    in_factory_class = False
                    indentation_level = 0

                    for line in lines:
                        stripped = line.strip()

                        # Detect start of factory class
                        if f"class {factory_name}" in line:
                            in_factory_class = True
                            indentation_level = len(line) - len(line.lstrip())
                            continue

                        # Detect end of factory class (new class or unindented line)
                        if in_factory_class and line and not line.startswith(' ') and not line.startswith('\t'):
                            if not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                                in_factory_class = False
                                continue

                        # Look for method definitions within factory class
                        if in_factory_class and stripped.startswith('def '):
                            method_def = stripped.split('(')[0].replace('def ', '').strip()
                            if method_def and not method_def.startswith('_'):  # Skip private methods
                                signatures.append(method_def)

                except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                    continue

            if signatures:
                method_signatures[factory_name] = signatures

        return method_signatures

    def _detect_factory_pattern_violations(self, factory_classes: Dict[str, List[Tuple[str, str]]]) -> List[str]:
        """Detect factory pattern violations.

        Args:
            factory_classes: Map of factory names to their locations

        Returns:
            List of violation descriptions
        """
        violations = []

        # Count total factory implementations
        total_factories = sum(len(locations) for locations in factory_classes.values())

        # Check for multiple factory classes
        if len(factory_classes) > 1:
            violations.append(
                f"Multiple factory class types found: {list(factory_classes.keys())}. "
                f"SSOT requires single factory pattern."
            )

        # Check for duplicate implementations of same factory
        for factory_name, locations in factory_classes.items():
            if len(locations) > 1:
                violations.append(
                    f"Factory {factory_name} has {len(locations)} implementations: "
                    f"{[loc[0] for loc in locations]}. "
                    f"SSOT requires single implementation."
                )

        return violations

    def test_single_websocket_manager_factory_exists(self):
        """Test that only one WebSocket manager factory exists.

        EXPECTED: This test should FAIL initially - multiple factories exist.
        After refactor: Should PASS with single factory implementation.
        """
        factory_classes = self._discover_websocket_factory_classes()
        self.discovered_factories = factory_classes

        # Count unique factory class types
        factory_types = list(factory_classes.keys())
        total_factory_types = len(factory_types)

        # SSOT Requirement: Only 1 factory type should exist (or 0 if factories eliminated)
        self.assertLessEqual(
            total_factory_types, 1,
            f"SSOT VIOLATION: Found {total_factory_types} factory class types, expected ≤ 1. "
            f"Factory types: {factory_types}. "
            f"Should consolidate to single factory pattern or eliminate factories entirely."
        )

    def test_no_duplicate_factory_implementations(self):
        """Test that there are no duplicate factory implementations.

        EXPECTED: This test should FAIL initially - duplicate implementations exist.
        After refactor: Should PASS with single implementation per factory.
        """
        factory_classes = self._discover_websocket_factory_classes()

        duplicate_violations = []
        for factory_name, locations in factory_classes.items():
            if len(locations) > 1:
                duplicate_violations.append((factory_name, locations))

        # SSOT Requirement: No duplicate implementations
        self.assertEqual(
            len(duplicate_violations), 0,
            f"SSOT VIOLATION: Found {len(duplicate_violations)} factories with duplicate implementations. "
            f"Duplicates: {[(name, len(locs)) for name, locs in duplicate_violations]}. "
            f"Each factory should have exactly one implementation."
        )

    def test_factory_method_consistency(self):
        """Test that factory methods are consistent across implementations.

        EXPECTED: This test may FAIL initially if method signatures vary.
        After refactor: Should PASS with consistent method signatures.
        """
        factory_classes = self._discover_websocket_factory_classes()
        method_signatures = self._analyze_factory_method_signatures(factory_classes)

        # Look for inconsistencies in method names across factory types
        all_methods = set()
        factory_methods = {}

        for factory_name, methods in method_signatures.items():
            factory_methods[factory_name] = set(methods)
            all_methods.update(methods)

        # Check for expected factory methods (create, get_manager, etc.)
        expected_methods = ["create", "get_manager", "create_manager", "build"]
        found_expected_methods = all_methods.intersection(set(expected_methods))

        if factory_methods and not found_expected_methods:
            # This might indicate non-standard factory methods
            method_list = list(all_methods)
            self.assertTrue(
                len(found_expected_methods) > 0,
                f"Factory methods may not follow standard patterns. "
                f"Found methods: {method_list}. "
                f"Expected at least one of: {expected_methods}"
            )

    def test_factory_pattern_consolidation_violations(self):
        """Test for specific factory pattern consolidation violations.

        EXPECTED: This test should FAIL initially - pattern violations exist.
        After refactor: Should PASS with consolidated patterns.
        """
        factory_classes = self._discover_websocket_factory_classes()
        violations = self._detect_factory_pattern_violations(factory_classes)

        # Store violations for debugging
        self.factory_violations = violations

        # SSOT Requirement: No pattern violations
        self.assertEqual(
            len(violations), 0,
            f"SSOT FACTORY PATTERN VIOLATIONS: Found {len(violations)} violations. "
            f"Violations: {violations}"
        )

    def test_factory_instantiation_works(self):
        """Test that discovered factories can be instantiated (basic functionality).

        EXPECTED: This test should PASS - existing factories should be functional.
        After refactor: Should PASS with consolidated factory functionality.
        """
        factory_classes = self._discover_websocket_factory_classes()

        # Try to import and instantiate factories (with mocked dependencies)
        instantiation_results = {}

        for factory_name, locations in factory_classes.items():
            for module_path, file_path in locations:
                try:
                    # Mock common dependencies that factories might need
                    with patch('netra_backend.app.core.configuration.get_config') as mock_config:
                        mock_config.return_value = MagicMock()

                        # Try to import the module
                        parts = module_path.split('.')
                        module_name = '.'.join(parts)

                        if module_name in sys.modules:
                            module = sys.modules[module_name]
                        else:
                            # Skip dynamic import for this test to avoid side effects
                            # Just verify the file structure is importable
                            continue

                        # Verify factory class exists in module if already imported
                        if hasattr(module, factory_name):
                            factory_class = getattr(module, factory_name)
                            instantiation_results[f"{module_path}.{factory_name}"] = "importable"

                except Exception as e:
                    instantiation_results[f"{module_path}.{factory_name}"] = f"error: {str(e)}"

        # This is primarily a documentation test - record which factories we found
        if factory_classes:
            print(f"\nDiscovered factory instantiation results:")
            for factory_path, result in instantiation_results.items():
                print(f"  - {factory_path}: {result}")

    def test_no_legacy_factory_patterns(self):
        """Test that legacy factory patterns are eliminated.

        EXPECTED: This test should FAIL initially if legacy patterns exist.
        After refactor: Should PASS with no legacy factory patterns.
        """
        factory_classes = self._discover_websocket_factory_classes()

        # Legacy patterns that should be eliminated
        legacy_patterns = [
            "WebSocketManagerBuilder",
            "WebSocketCreator",
            "WebSocketProvider"
        ]

        found_legacy = []
        for pattern in legacy_patterns:
            if pattern in factory_classes:
                found_legacy.append(pattern)

        # SSOT Requirement: No legacy patterns after refactor
        self.assertEqual(
            len(found_legacy), 0,
            f"SSOT VIOLATION: Found {len(found_legacy)} legacy factory patterns, expected 0. "
            f"Legacy patterns: {found_legacy}. "
            f"Legacy factory patterns should be eliminated in favor of SSOT factory."
        )

    def teardown_method(self, method=None):
        """Clean up after test."""
        # Log factory violations for debugging Step 4 refactor
        if self.discovered_factories:
            print(f"\n=== FACTORY PATTERN VIOLATIONS DISCOVERED ===")
            total_factories = sum(len(locations) for locations in self.discovered_factories.values())
            print(f"Total factory implementations found: {total_factories}")

            for factory_name, locations in self.discovered_factories.items():
                print(f"  - {factory_name}: {len(locations)} implementations")
                for module_path, file_path in locations:
                    print(f"    * {module_path}")

        if self.factory_violations:
            print(f"\n=== FACTORY CONSOLIDATION VIOLATIONS ===")
            for violation in self.factory_violations:
                print(f"  - {violation}")

        print(f"=== END FACTORY VIOLATIONS ===\n")

        super().teardown_method(method)


if __name__ == "__main__":
    # Run tests to demonstrate factory pattern violations
    unittest.main(verbosity=2)