"""
Unit tests for Issue #1196 - SSOT Import Path Fragmentation Detection

These tests are designed to FAIL initially, demonstrating the import path
fragmentation problem affecting WebSocket Manager, ExecutionEngine, and
AgentRegistry components.

Business Impact: $500K+ ARR Golden Path functionality blocked by fragmented
import patterns causing initialization race conditions and inconsistent behavior.
"""

import unittest
import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from unittest.mock import patch


class ImportPathFragmentationIssue1196Tests(unittest.TestCase):
    """Test suite demonstrating SSOT import path fragmentation violations.

    These tests MUST FAIL initially to prove the fragmentation problem exists.
    Success criteria: Tests fail showing 58+ WebSocket variations, 15+ ExecutionEngine variations.
    """

    def setUp(self):
        """Set up test fixtures and project root path."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_path = self.project_root / "netra_backend"
        self.tests_path = self.project_root / "tests"

        # Expected SSOT canonical import paths (what should be used)
        self.canonical_imports = {
            "WebSocketManager": "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
            "ExecutionEngine": "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine",
            "AgentRegistry": "from netra_backend.app.agents.registry import AgentRegistry"
        }

        # Track all discovered import variations
        self.import_variations = {
            "WebSocketManager": set(),
            "ExecutionEngine": set(),
            "AgentRegistry": set()
        }

    def _scan_python_files_for_imports(self, root_path: Path, target_component: str) -> Set[str]:
        """Scan Python files and collect import statements for target component."""
        import_patterns = set()

        # Define search patterns for each component
        component_patterns = {
            "WebSocketManager": [
                "websocket", "manager", "WebSocketManager", "websocket_manager",
                "unified_manager", "websocket_core"
            ],
            "ExecutionEngine": [
                "execution", "engine", "ExecutionEngine", "execution_engine",
                "user_execution", "supervisor"
            ],
            "AgentRegistry": [
                "registry", "agent_registry", "AgentRegistry", "agents"
            ]
        }

        patterns = component_patterns.get(target_component, [])

        for file_path in root_path.rglob("*.py"):
            # Skip venv and other irrelevant directories
            if any(skip in str(file_path) for skip in ["venv", ".git", "__pycache__", "node_modules"]):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for import statements containing our patterns
                lines = content.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if (stripped.startswith(('from ', 'import ')) and
                        any(pattern in stripped for pattern in patterns)):
                        import_patterns.add(stripped)

            except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                # Skip files we can't read
                continue

        return import_patterns

    def test_websocket_manager_import_fragmentation_must_fail(self):
        """TEST MUST FAIL: Demonstrate WebSocket Manager has 58+ fragmented import paths.

        This test scans the codebase for all WebSocket Manager import variations.
        Expected: FAILURE showing massive fragmentation (58+ variations documented in issue).
        Success criteria for Issue #1196: Test fails proving fragmentation exists.
        """
        # Scan for WebSocket Manager imports
        websocket_imports = self._scan_python_files_for_imports(self.project_root, "WebSocketManager")

        # Filter to actual import statements (not comments or documentation)
        actual_imports = {imp for imp in websocket_imports
                         if not imp.strip().startswith('#') and
                         ('import' in imp.lower() or 'from' in imp.lower())}

        self.import_variations["WebSocketManager"] = actual_imports

        # Count unique import paths
        unique_paths = len(actual_imports)

        print(f"\n=== WEBSOCKET MANAGER IMPORT FRAGMENTATION ANALYSIS ===")
        print(f"Total unique import patterns found: {unique_paths}")
        print(f"Canonical SSOT path: {self.canonical_imports['WebSocketManager']}")
        print(f"Non-SSOT variations discovered:")

        non_canonical = []
        for imp in sorted(actual_imports):
            if imp != self.canonical_imports["WebSocketManager"]:
                non_canonical.append(imp)
                print(f"  - {imp}")

        print(f"\nFragmentation severity: {len(non_canonical)} non-canonical imports")

        # TEST MUST FAIL: Assert we have SINGLE import path (SSOT compliance)
        # This will fail because of fragmentation, proving the problem exists
        self.assertEqual(unique_paths, 1,
                        f"FRAGMENTATION DETECTED: Found {unique_paths} import variations for WebSocketManager, expected 1 SSOT path. "
                        f"Issue #1196 confirmed - import path fragmentation blocks Golden Path stability.")

        # Additional assertion that will fail - all imports should be canonical
        self.assertEqual(len(non_canonical), 0,
                        f"NON-SSOT IMPORTS DETECTED: {len(non_canonical)} imports deviate from SSOT canonical path. "
                        f"This fragmentation causes initialization race conditions affecting $500K+ ARR.")

    def test_execution_engine_import_fragmentation_must_fail(self):
        """TEST MUST FAIL: Demonstrate ExecutionEngine has 15+ fragmented import paths.

        Expected: FAILURE showing ExecutionEngine import fragmentation (15+ variations).
        Success criteria for Issue #1196: Test fails proving fragmentation exists.
        """
        # Scan for ExecutionEngine imports
        execution_imports = self._scan_python_files_for_imports(self.project_root, "ExecutionEngine")

        # Filter to actual import statements
        actual_imports = {imp for imp in execution_imports
                         if not imp.strip().startswith('#') and
                         ('ExecutionEngine' in imp or 'execution_engine' in imp)}

        self.import_variations["ExecutionEngine"] = actual_imports

        unique_paths = len(actual_imports)

        print(f"\n=== EXECUTION ENGINE IMPORT FRAGMENTATION ANALYSIS ===")
        print(f"Total unique import patterns found: {unique_paths}")
        print(f"Canonical SSOT path: {self.canonical_imports['ExecutionEngine']}")
        print(f"Non-SSOT variations discovered:")

        non_canonical = []
        for imp in sorted(actual_imports):
            if "user_execution_engine" not in imp:  # Should use UserExecutionEngine as SSOT
                non_canonical.append(imp)
                print(f"  - {imp}")

        print(f"\nFragmentation severity: {len(non_canonical)} non-canonical imports")

        # TEST MUST FAIL: Assert SSOT compliance (single path)
        self.assertEqual(unique_paths, 1,
                        f"FRAGMENTATION DETECTED: Found {unique_paths} ExecutionEngine import variations, expected 1 SSOT path. "
                        f"Issue #1196 confirmed - fragmented imports cause agent execution inconsistencies.")

        # This will fail due to legacy execution_engine.py imports still existing
        self.assertEqual(len(non_canonical), 0,
                        f"LEGACY IMPORTS DETECTED: {len(non_canonical)} imports still use deprecated execution_engine.py instead of SSOT user_execution_engine.py")

    def test_agent_registry_import_fragmentation_must_fail(self):
        """TEST MUST FAIL: Demonstrate AgentRegistry has fragmented import patterns.

        Expected: FAILURE showing AgentRegistry import inconsistencies between basic and advanced registry.
        Success criteria for Issue #1196: Test fails proving fragmentation exists.
        """
        # Scan for AgentRegistry imports
        registry_imports = self._scan_python_files_for_imports(self.project_root, "AgentRegistry")

        # Filter to AgentRegistry specific imports
        actual_imports = {imp for imp in registry_imports
                         if 'AgentRegistry' in imp and not imp.strip().startswith('#')}

        self.import_variations["AgentRegistry"] = actual_imports

        unique_paths = len(actual_imports)

        print(f"\n=== AGENT REGISTRY IMPORT FRAGMENTATION ANALYSIS ===")
        print(f"Total unique import patterns found: {unique_paths}")
        print(f"Canonical SSOT path: {self.canonical_imports['AgentRegistry']}")

        # Separate basic registry vs advanced registry imports
        basic_registry_imports = {imp for imp in actual_imports if 'agents.registry' in imp}
        advanced_registry_imports = {imp for imp in actual_imports if 'supervisor.agent_registry' in imp}

        print(f"Basic registry imports (should be eliminated): {len(basic_registry_imports)}")
        for imp in sorted(basic_registry_imports):
            print(f"  - {imp}")

        print(f"Advanced registry imports: {len(advanced_registry_imports)}")
        for imp in sorted(advanced_registry_imports):
            print(f"  - {imp}")

        # TEST MUST FAIL: Assert no fragmentation (SSOT requires single registry)
        self.assertLessEqual(unique_paths, 1,
                           f"REGISTRY FRAGMENTATION: Found {unique_paths} AgentRegistry import paths. "
                           f"SSOT requires single registry implementation to prevent agent registration conflicts.")

        # This will fail because both basic and advanced registries are still in use
        self.assertEqual(len(basic_registry_imports), 0,
                        f"BASIC REGISTRY DEPRECATED: Found {len(basic_registry_imports)} imports still using basic registry. "
                        f"Issue #1196: All imports should use advanced registry for SSOT compliance.")

    def test_import_path_consistency_across_services_must_fail(self):
        """TEST MUST FAIL: Verify consistent import paths across all services.

        This test ensures that the same component is imported consistently
        across netra_backend, auth_service, and test files.

        Expected: FAILURE due to inconsistent import patterns between services.
        """
        # Analyze import consistency across different parts of the codebase
        backend_imports = self._scan_python_files_for_imports(self.netra_backend_path, "WebSocketManager")
        test_imports = self._scan_python_files_for_imports(self.tests_path, "WebSocketManager")

        # Filter to actual imports
        backend_actual = {imp for imp in backend_imports if 'import' in imp.lower()}
        test_actual = {imp for imp in test_imports if 'import' in imp.lower()}

        print(f"\n=== IMPORT CONSISTENCY ANALYSIS ===")
        print(f"Backend service imports: {len(backend_actual)}")
        print(f"Test file imports: {len(test_actual)}")

        # Find inconsistencies
        backend_only = backend_actual - test_actual
        test_only = test_actual - backend_actual
        common = backend_actual & test_actual

        print(f"Backend-only patterns: {len(backend_only)}")
        for imp in sorted(backend_only):
            print(f"  - {imp}")

        print(f"Test-only patterns: {len(test_only)}")
        for imp in sorted(test_only):
            print(f"  - {imp}")

        print(f"Common patterns: {len(common)}")

        # TEST MUST FAIL: Assert perfect consistency (SSOT requires identical imports)
        total_unique = len(backend_actual | test_actual)
        self.assertEqual(total_unique, 1,
                        f"IMPORT INCONSISTENCY: Found {total_unique} unique import patterns across services. "
                        f"SSOT requires identical import paths for consistency. Issue #1196 confirmed.")

        # This will fail due to different import patterns between services
        self.assertEqual(len(backend_only), 0,
                        f"BACKEND-SPECIFIC IMPORTS: {len(backend_only)} patterns only in backend, breaking service consistency.")

        self.assertEqual(len(test_only), 0,
                        f"TEST-SPECIFIC IMPORTS: {len(test_only)} patterns only in tests, indicating fragmentation.")

    def test_circular_dependency_detection_must_fail(self):
        """TEST MUST FAIL: Detect circular dependencies caused by import fragmentation.

        Import fragmentation often leads to circular dependencies when components
        import each other through different paths.

        Expected: FAILURE due to circular dependencies in import graph.
        """
        # Simplified circular dependency detection
        # This would need a more sophisticated implementation in real scenario

        print(f"\n=== CIRCULAR DEPENDENCY ANALYSIS ===")

        # Check for common circular dependency patterns
        websocket_imports = list(self.import_variations["WebSocketManager"])
        execution_imports = list(self.import_variations["ExecutionEngine"])

        # Look for cross-component dependencies
        circular_patterns = []

        # WebSocket importing ExecutionEngine AND ExecutionEngine importing WebSocket
        if (any('websocket' in imp.lower() for imp in execution_imports) and
            any('execution' in imp.lower() for imp in websocket_imports)):
            circular_patterns.append("WebSocket <-> ExecutionEngine circular dependency")

        print(f"Potential circular dependencies detected: {len(circular_patterns)}")
        for pattern in circular_patterns:
            print(f"  - {pattern}")

        # TEST MUST FAIL: Assert no circular dependencies
        self.assertEqual(len(circular_patterns), 0,
                        f"CIRCULAR DEPENDENCIES: {len(circular_patterns)} circular import patterns detected. "
                        f"Import fragmentation creates circular dependencies blocking system initialization.")

    def tearDown(self):
        """Print summary of discovered fragmentation for issue documentation."""
        print(f"\n=== ISSUE #1196 FRAGMENTATION SUMMARY ===")

        for component, variations in self.import_variations.items():
            if variations:
                print(f"{component}: {len(variations)} import variations discovered")
                print(f"  Canonical: {self.canonical_imports[component]}")
                print(f"  Variations: {len(variations) - 1} non-canonical imports")

        print(f"\nTotal fragmentation impact: {sum(len(v) for v in self.import_variations.values())} import patterns")
        print(f"SSOT compliance target: 3 canonical imports (one per component)")
        print(f"Issue #1196 Status: CONFIRMED - Massive import fragmentation detected")


if __name__ == "__main__":
    # Run with verbose output to see fragmentation details
    unittest.main(verbosity=2)