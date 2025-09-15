"""
SSOT WebSocket Manager Import Path Consistency Validation Test

This test validates that all WebSocket manager imports follow SSOT patterns
and there are no inconsistent import paths across the codebase.

EXPECTED BEHAVIOR: These tests should FAIL initially to prove import inconsistency exists.
After SSOT refactor (Step 4), they should PASS with consistent import paths.

Business Value: Platform/Internal - System Architecture Compliance
Ensures consistent import patterns for WebSocket management, preventing fragmentation.

Test Strategy: Static analysis of import statements (no runtime dependencies).
NO DOCKER required - pure Python import analysis.
"""

import pytest
import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import unittest

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class TestWebSocketManagerImportConsistency(SSotBaseTestCase, unittest.TestCase):
    """Test suite to validate SSOT import consistency for WebSocket managers.

    These tests should FAIL initially, proving inconsistent import paths exist.
    After refactor, they should PASS with consistent SSOT import patterns.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.import_violations = []
        self.expected_canonical_imports = {
            "WebSocketManager": "netra_backend.app.websocket_core.websocket_manager.WebSocketManager",
            "UnifiedWebSocketManager": "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager",
            "WebSocketManagerFactory": "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory",
            "AgentWebSocketBridge": "netra_backend.app.services.agent_websocket_bridge.AgentWebSocketBridge"
        }

    def _discover_websocket_imports(self) -> Dict[str, List[Tuple[str, int, str]]]:
        """Discover all WebSocket manager imports in the codebase.

        Returns:
            Dict mapping import_name to list of (file_path, line_number, import_statement) tuples
        """
        import_map = {}

        # Search in key directories
        search_paths = [
            self.codebase_root / "netra_backend" / "app",
            self.codebase_root / "tests" / "mission_critical",
            self.codebase_root / "tests" / "integration",
            self.codebase_root / "tests" / "unit" / "websocket_core"
        ]

        websocket_import_patterns = [
            "WebSocketManager",
            "UnifiedWebSocketManager",
            "IsolatedWebSocketManager",
            "WebSocketConnectionManager",
            "ConnectionManager",
            "EmergencyWebSocketManager",
            "DegradedWebSocketManager",
            "WebSocketManagerFactory",
            "AgentWebSocketBridge"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()

                        # Skip comments
                        if line.startswith("#"):
                            continue

                        # Look for import statements containing WebSocket patterns
                        if ("import" in line and
                            any(pattern in line for pattern in websocket_import_patterns)):

                            # Extract the specific import pattern found
                            for pattern in websocket_import_patterns:
                                if pattern in line:
                                    if pattern not in import_map:
                                        import_map[pattern] = []

                                    file_path = str(py_file.relative_to(self.codebase_root))
                                    import_map[pattern].append((
                                        file_path,
                                        line_num,
                                        line
                                    ))

                except (UnicodeDecodeError, PermissionError):
                    continue

        return import_map

    def _analyze_import_inconsistencies(self, import_map: Dict[str, List[Tuple[str, int, str]]]) -> Dict[str, List[str]]:
        """Analyze discovered imports for inconsistencies.

        Args:
            import_map: Map of import patterns to their occurrences

        Returns:
            Dict mapping import_name to list of unique import paths found
        """
        inconsistencies = {}

        for import_name, occurrences in import_map.items():
            unique_paths = set()

            for file_path, line_num, import_statement in occurrences:
                # Extract the module path from the import statement
                if "from " in import_statement:
                    # from module.path import ClassName
                    parts = import_statement.split("from ")[1].split(" import ")
                    if len(parts) == 2:
                        module_path = parts[0].strip()
                        unique_paths.add(module_path)
                elif "import " in import_statement and "." in import_statement:
                    # import module.path.ClassName
                    module_part = import_statement.split("import ")[1].strip()
                    if "." in module_part:
                        # Extract the module portion (everything except the class name)
                        path_parts = module_part.split(".")
                        if len(path_parts) > 1:
                            module_path = ".".join(path_parts[:-1])
                            unique_paths.add(module_path)

            if len(unique_paths) > 1:
                inconsistencies[import_name] = list(unique_paths)

        return inconsistencies

    def test_websocket_manager_import_consistency(self):
        """Test that WebSocketManager imports use consistent paths.

        EXPECTED: This test should FAIL initially - multiple import paths exist.
        After refactor: Should PASS with single canonical import path.
        """
        import_map = self._discover_websocket_imports()
        inconsistencies = self._analyze_import_inconsistencies(import_map)

        # Store violations for debugging
        self.import_violations = inconsistencies

        # Check for WebSocketManager import inconsistencies specifically
        if "WebSocketManager" in inconsistencies:
            unique_paths = inconsistencies["WebSocketManager"]
            self.assertEqual(
                len(unique_paths), 1,
                f"SSOT VIOLATION: WebSocketManager imported from {len(unique_paths)} different paths, expected 1. "
                f"Import paths found: {unique_paths}. "
                f"Should only import from: {self.expected_canonical_imports.get('WebSocketManager', 'TBD')}"
            )

    def test_unified_websocket_manager_import_consistency(self):
        """Test that UnifiedWebSocketManager imports use consistent paths.

        EXPECTED: This test should FAIL initially if multiple paths exist.
        After refactor: Should PASS with single canonical import path.
        """
        import_map = self._discover_websocket_imports()
        inconsistencies = self._analyze_import_inconsistencies(import_map)

        # Check for UnifiedWebSocketManager import inconsistencies
        if "UnifiedWebSocketManager" in inconsistencies:
            unique_paths = inconsistencies["UnifiedWebSocketManager"]
            self.assertEqual(
                len(unique_paths), 1,
                f"SSOT VIOLATION: UnifiedWebSocketManager imported from {len(unique_paths)} different paths, expected 1. "
                f"Import paths found: {unique_paths}. "
                f"Should only import from: {self.expected_canonical_imports.get('UnifiedWebSocketManager', 'TBD')}"
            )

    def test_no_legacy_websocket_manager_imports(self):
        """Test that legacy WebSocket manager imports are eliminated.

        EXPECTED: This test should FAIL initially - legacy imports exist.
        After refactor: Should PASS with no legacy imports.
        """
        import_map = self._discover_websocket_imports()

        # Legacy patterns that should not exist after refactor
        legacy_patterns = [
            "IsolatedWebSocketManager",
            "WebSocketConnectionManager",
            "EmergencyWebSocketManager",
            "DegradedWebSocketManager"
        ]

        found_legacy_imports = []
        for pattern in legacy_patterns:
            if pattern in import_map and import_map[pattern]:
                found_legacy_imports.append(pattern)

        # This should PASS after refactor (no legacy imports)
        self.assertEqual(
            len(found_legacy_imports), 0,
            f"SSOT VIOLATION: Found {len(found_legacy_imports)} legacy WebSocket manager imports, expected 0. "
            f"Legacy imports found: {found_legacy_imports}. "
            "Legacy managers should be eliminated after SSOT refactor."
        )

    def test_websocket_factory_import_consolidation(self):
        """Test that WebSocket factory imports are consolidated.

        EXPECTED: This test should FAIL initially if multiple factory patterns exist.
        After refactor: Should PASS with single factory import pattern.
        """
        import_map = self._discover_websocket_imports()
        inconsistencies = self._analyze_import_inconsistencies(import_map)

        # Check for WebSocketManagerFactory import inconsistencies
        if "WebSocketManagerFactory" in inconsistencies:
            unique_paths = inconsistencies["WebSocketManagerFactory"]
            self.assertEqual(
                len(unique_paths), 1,
                f"SSOT VIOLATION: WebSocketManagerFactory imported from {len(unique_paths)} different paths, expected 1. "
                f"Import paths found: {unique_paths}. "
                f"Should only import from: {self.expected_canonical_imports.get('WebSocketManagerFactory', 'TBD')}"
            )

    def test_agent_websocket_bridge_import_consistency(self):
        """Test that AgentWebSocketBridge imports use consistent paths.

        EXPECTED: This test should PASS or FAIL depending on current state.
        After refactor: Should PASS with single canonical import path.
        """
        import_map = self._discover_websocket_imports()
        inconsistencies = self._analyze_import_inconsistencies(import_map)

        # Check for AgentWebSocketBridge import inconsistencies
        if "AgentWebSocketBridge" in inconsistencies:
            unique_paths = inconsistencies["AgentWebSocketBridge"]
            self.assertEqual(
                len(unique_paths), 1,
                f"SSOT VIOLATION: AgentWebSocketBridge imported from {len(unique_paths)} different paths, expected 1. "
                f"Import paths found: {unique_paths}. "
                f"Should only import from: {self.expected_canonical_imports.get('AgentWebSocketBridge', 'TBD')}"
            )

    def test_mission_critical_tests_use_canonical_imports(self):
        """Test that mission critical tests use canonical WebSocket imports.

        EXPECTED: This test should PASS if mission critical tests already use SSOT imports.
        After refactor: Should PASS with verified canonical imports.
        """
        # Check mission critical test file specifically
        mission_critical_file = (
            self.codebase_root /
            "tests" / "mission_critical" / "test_websocket_agent_events_suite.py"
        )

        if not mission_critical_file.exists():
            self.skipTest("Mission critical WebSocket test file not found")

        content = mission_critical_file.read_text(encoding="utf-8")
        lines = content.split('\n')

        websocket_imports = []
        for line_num, line in enumerate(lines, 1):
            if "import" in line and "WebSocket" in line:
                websocket_imports.append((line_num, line.strip()))

        # Verify that mission critical tests use expected canonical imports
        # This is a documentation/verification test rather than a failure test
        canonical_import_found = False
        for line_num, import_line in websocket_imports:
            if "websocket_core.websocket_manager" in import_line:
                canonical_import_found = True
                break

        # This test documents current state - should pass if using canonical imports
        if websocket_imports and not canonical_import_found:
            self.fail(
                f"Mission critical tests may not be using canonical WebSocket imports. "
                f"Found imports: {[imp for _, imp in websocket_imports]}. "
                f"Expected canonical path: netra_backend.app.websocket_core.websocket_manager"
            )

    def teardown_method(self, method=None):
        """Clean up after test."""
        # Log import violations for debugging Step 4 refactor
        if self.import_violations:
            print(f"\n=== IMPORT INCONSISTENCY VIOLATIONS DISCOVERED ===")
            for import_name, paths in self.import_violations.items():
                print(f"  - {import_name} imported from {len(paths)} different paths:")
                for path in sorted(paths):
                    print(f"    * {path}")
            print(f"=== END IMPORT VIOLATIONS ===\n")

        super().teardown_method(method)


if __name__ == "__main__":
    # Run tests to demonstrate import inconsistency violations
    unittest.main(verbosity=2)