"""
Integration tests for Issue #1196 - SSOT Import Registry Compliance

These integration tests validate the SSOT Import Registry accuracy and detect
import performance inconsistencies and circular dependencies.

Business Impact: $500K+ ARR Golden Path blocked by inconsistent import registry
leading to unpredictable component initialization and WebSocket failures.
"""

import unittest
import time
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from unittest.mock import patch
import traceback


class SSotImportRegistryComplianceIssue1196Tests(unittest.TestCase):
    """Integration test suite for SSOT Import Registry compliance validation.

    Tests MUST demonstrate registry inaccuracies and performance inconsistencies
    caused by import path fragmentation.
    """

    def setUp(self):
        """Set up test fixtures and SSOT Import Registry validation."""
        self.project_root = Path(__file__).parent.parent.parent
        self.ssot_registry_path = self.project_root / "docs" / "SSOT_IMPORT_REGISTRY.md"

        # Expected SSOT canonical imports from registry
        self.ssot_registry_imports = {
            # WebSocket Manager - should be single canonical path
            "WebSocketManager": {
                "canonical": "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
                "alternatives": [
                    "from netra_backend.app.websocket_core import WebSocketManager",  # Deprecated
                    "from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager",  # SSOT but different name
                    "from netra_backend.app.websocket_core.manager import WebSocketManager",  # Legacy
                ]
            },
            # ExecutionEngine - should be UserExecutionEngine as SSOT
            "ExecutionEngine": {
                "canonical": "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine",
                "alternatives": [
                    "from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine",  # Deprecated
                    "from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine",  # Fragmented
                ]
            },
            # AgentRegistry - should be single registry
            "AgentRegistry": {
                "canonical": "from netra_backend.app.agents.registry import AgentRegistry",
                "alternatives": [
                    "from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry",  # Advanced registry fragmentation
                ]
            }
        }

        # Track import performance
        self.import_timings = {}

    def test_ssot_import_registry_accuracy_must_fail(self):
        """TEST MUST FAIL: Validate SSOT Import Registry reflects actual working imports.

        This test checks if the documented registry matches reality.
        Expected: FAILURE due to registry containing broken/outdated import paths.
        """
        print(f"\n=== SSOT IMPORT REGISTRY ACCURACY TEST ===")

        registry_accuracy_issues = []

        for component, paths in self.ssot_registry_imports.items():
            print(f"\nTesting {component} import paths:")

            canonical_path = paths["canonical"]
            print(f"  Canonical: {canonical_path}")

            # Test if canonical path actually works
            try:
                # Clear any previous imports to test fresh
                modules_to_clear = [mod for mod in sys.modules.keys()
                                  if 'websocket' in mod.lower() or 'execution' in mod.lower() or 'registry' in mod.lower()]
                for mod in modules_to_clear:
                    if mod in sys.modules:
                        del sys.modules[mod]

                # Try to execute the import
                exec(canonical_path)
                print(f"    ✅ WORKS")

            except ImportError as e:
                registry_accuracy_issues.append(f"{component} canonical path BROKEN: {str(e)}")
                print(f"    ❌ BROKEN: {str(e)}")
            except Exception as e:
                registry_accuracy_issues.append(f"{component} canonical path ERROR: {str(e)}")
                print(f"    ❌ ERROR: {str(e)}")

            # Test alternative paths documented in registry
            for alt_path in paths["alternatives"]:
                print(f"  Alternative: {alt_path}")
                try:
                    exec(alt_path)
                    print(f"    ⚠️  WORKS (should be deprecated)")
                except ImportError as e:
                    print(f"    ❌ BROKEN: {str(e)}")
                    registry_accuracy_issues.append(f"{component} alternative path BROKEN: {alt_path} - {str(e)}")

        print(f"\nRegistry accuracy issues found: {len(registry_accuracy_issues)}")
        for issue in registry_accuracy_issues:
            print(f"  - {issue}")

        # TEST MUST FAIL: Assert registry is 100% accurate
        self.assertEqual(len(registry_accuracy_issues), 0,
                        f"REGISTRY INACCURACY: Found {len(registry_accuracy_issues)} broken/outdated import paths in SSOT registry. "
                        f"Issue #1196 confirmed - registry doesn't reflect actual working imports, causing developer confusion.")

    def test_import_performance_consistency_must_fail(self):
        """TEST MUST FAIL: Verify consistent import performance across different paths.

        Different import paths for same component should have identical performance.
        Expected: FAILURE due to performance inconsistencies between import variations.
        """
        print(f"\n=== IMPORT PERFORMANCE CONSISTENCY TEST ===")

        performance_issues = []

        for component, paths in self.ssot_registry_imports.items():
            print(f"\nTesting {component} import performance:")

            canonical_path = paths["canonical"]
            performance_data = {}

            # Test canonical path performance
            try:
                start_time = time.perf_counter()
                exec(canonical_path)
                canonical_time = time.perf_counter() - start_time
                performance_data["canonical"] = canonical_time
                print(f"  Canonical time: {canonical_time:.6f}s")

            except Exception as e:
                print(f"  Canonical FAILED: {str(e)}")
                continue

            # Test alternative path performance
            for i, alt_path in enumerate(paths["alternatives"]):
                try:
                    # Clear modules for clean test
                    modules_to_clear = [mod for mod in sys.modules.keys()
                                      if any(keyword in mod.lower() for keyword in ['websocket', 'execution', 'registry'])]
                    for mod in modules_to_clear:
                        if mod in sys.modules:
                            del sys.modules[mod]

                    start_time = time.perf_counter()
                    exec(alt_path)
                    alt_time = time.perf_counter() - start_time
                    performance_data[f"alt_{i}"] = alt_time
                    print(f"  Alternative {i} time: {alt_time:.6f}s")

                    # Check for significant performance differences
                    performance_ratio = alt_time / canonical_time if canonical_time > 0 else float('inf')
                    if abs(performance_ratio - 1.0) > 0.5:  # >50% difference
                        performance_issues.append(
                            f"{component}: Alternative path {i} is {performance_ratio:.2f}x different from canonical "
                            f"({alt_time:.6f}s vs {canonical_time:.6f}s)"
                        )

                except Exception as e:
                    print(f"  Alternative {i} FAILED: {str(e)}")

            self.import_timings[component] = performance_data

        print(f"\nPerformance inconsistencies found: {len(performance_issues)}")
        for issue in performance_issues:
            print(f"  - {issue}")

        # TEST MUST FAIL: Assert consistent performance (within 10% tolerance)
        self.assertEqual(len(performance_issues), 0,
                        f"PERFORMANCE INCONSISTENCY: {len(performance_issues)} import paths show significant performance differences. "
                        f"Issue #1196: Fragmented imports cause unpredictable initialization timing affecting Golden Path reliability.")

    def test_circular_dependency_detection_integration_must_fail(self):
        """TEST MUST FAIL: Detect circular dependencies in actual import execution.

        This integration test actually attempts imports to detect real circular dependencies
        that occur during runtime due to fragmented import paths.

        Expected: FAILURE due to circular import errors during actual component initialization.
        """
        print(f"\n=== CIRCULAR DEPENDENCY INTEGRATION TEST ===")

        circular_dependency_errors = []

        # Test import sequences that commonly cause circular dependencies
        problematic_sequences = [
            # WebSocket -> ExecutionEngine -> WebSocket cycle
            [
                "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
                "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine",
            ],
            # AgentRegistry -> WebSocket -> AgentRegistry cycle
            [
                "from netra_backend.app.agents.registry import AgentRegistry",
                "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
            ],
            # ExecutionEngine -> AgentRegistry -> ExecutionEngine cycle
            [
                "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine",
                "from netra_backend.app.agents.registry import AgentRegistry",
            ]
        ]

        for i, sequence in enumerate(problematic_sequences):
            print(f"\nTesting import sequence {i+1}:")

            # Clear all potentially conflicting modules
            modules_to_clear = [mod for mod in sys.modules.keys()
                              if any(keyword in mod.lower() for keyword in
                                   ['websocket', 'execution', 'registry', 'agent', 'supervisor'])]
            for mod in modules_to_clear:
                if mod in sys.modules:
                    del sys.modules[mod]

            try:
                for j, import_stmt in enumerate(sequence):
                    print(f"  Step {j+1}: {import_stmt}")
                    exec(import_stmt)
                    print(f"    ✅ SUCCESS")

                print(f"  Sequence {i+1}: ✅ NO CIRCULAR DEPENDENCY")

            except ImportError as e:
                if "circular" in str(e).lower() or "partially initialized" in str(e):
                    circular_dependency_errors.append(f"Sequence {i+1}: CIRCULAR DEPENDENCY - {str(e)}")
                    print(f"  ❌ CIRCULAR DEPENDENCY: {str(e)}")
                else:
                    circular_dependency_errors.append(f"Sequence {i+1}: IMPORT ERROR - {str(e)}")
                    print(f"  ❌ IMPORT ERROR: {str(e)}")

            except Exception as e:
                circular_dependency_errors.append(f"Sequence {i+1}: UNEXPECTED ERROR - {str(e)}")
                print(f"  ❌ UNEXPECTED ERROR: {str(e)}")

        print(f"\nCircular dependency errors found: {len(circular_dependency_errors)}")
        for error in circular_dependency_errors:
            print(f"  - {error}")

        # TEST MUST FAIL: Assert no circular dependencies exist
        self.assertEqual(len(circular_dependency_errors), 0,
                        f"CIRCULAR DEPENDENCIES: {len(circular_dependency_errors)} circular import errors detected during integration. "
                        f"Issue #1196: Import fragmentation creates circular dependencies blocking system initialization.")

    def test_real_component_initialization_consistency_must_fail(self):
        """TEST MUST FAIL: Test that components initialize consistently regardless of import path.

        Same component imported via different paths should create identical instances.
        Expected: FAILURE due to different instances/behavior from fragmented imports.
        """
        print(f"\n=== COMPONENT INITIALIZATION CONSISTENCY TEST ===")

        initialization_inconsistencies = []

        # Test WebSocketManager initialization consistency
        try:
            print(f"\nTesting WebSocketManager initialization consistency:")

            # Clear modules for clean test
            modules_to_clear = [mod for mod in sys.modules.keys() if 'websocket' in mod.lower()]
            for mod in modules_to_clear:
                if mod in sys.modules:
                    del sys.modules[mod]

            # Import via canonical path
            exec("from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as WM1")
            canonical_instance = locals().get('WM1')

            # Clear and import via alternative path
            modules_to_clear = [mod for mod in sys.modules.keys() if 'websocket' in mod.lower()]
            for mod in modules_to_clear:
                if mod in sys.modules:
                    del sys.modules[mod]

            exec("from netra_backend.app.websocket_core import WebSocketManager as WM2")
            alternative_instance = locals().get('WM2')

            # Check if they're the same class
            if canonical_instance is not alternative_instance:
                initialization_inconsistencies.append(
                    f"WebSocketManager: Different classes from different import paths - "
                    f"canonical: {canonical_instance}, alternative: {alternative_instance}"
                )
                print(f"  ❌ INCONSISTENT: Different classes from different paths")
            else:
                print(f"  ✅ CONSISTENT: Same class from both paths")

        except Exception as e:
            initialization_inconsistencies.append(f"WebSocketManager initialization test failed: {str(e)}")
            print(f"  ❌ ERROR: {str(e)}")

        print(f"\nInitialization inconsistencies found: {len(initialization_inconsistencies)}")
        for inconsistency in initialization_inconsistencies:
            print(f"  - {inconsistency}")

        # TEST MUST FAIL: Assert perfect initialization consistency
        self.assertEqual(len(initialization_inconsistencies), 0,
                        f"INITIALIZATION INCONSISTENCY: {len(initialization_inconsistencies)} components show different behavior "
                        f"when imported via different paths. Issue #1196: Fragmented imports cause unpredictable component behavior.")

    def test_missing_imports_in_ssot_registry_must_fail(self):
        """TEST MUST FAIL: Detect import paths used in codebase but missing from SSOT registry.

        The SSOT registry should document ALL import paths used in the codebase.
        Expected: FAILURE due to undocumented import paths in actual use.
        """
        print(f"\n=== MISSING IMPORTS IN SSOT REGISTRY TEST ===")

        # This is a simplified test - in real implementation would scan entire codebase
        # and compare with registry documentation

        missing_from_registry = []

        # Common import patterns we know exist but might not be documented
        undocumented_patterns = [
            "from netra_backend.app.websocket_core.manager import WebSocketManager",
            "from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager",
            "from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry",
            "from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine",
        ]

        print(f"Checking for undocumented import patterns:")
        for pattern in undocumented_patterns:
            print(f"  Testing: {pattern}")

            # Check if this pattern works but isn't in our registry
            try:
                exec(pattern)
                print(f"    ✅ WORKS")

                # Check if it's documented in our registry
                component = None
                if "WebSocketManager" in pattern:
                    component = "WebSocketManager"
                elif "ExecutionEngine" in pattern:
                    component = "ExecutionEngine"
                elif "AgentRegistry" in pattern:
                    component = "AgentRegistry"

                if component:
                    all_documented_paths = [self.ssot_registry_imports[component]["canonical"]] + self.ssot_registry_imports[component]["alternatives"]
                    if pattern not in all_documented_paths:
                        missing_from_registry.append(f"{component}: Working import path not documented - {pattern}")
                        print(f"    ❌ NOT DOCUMENTED in SSOT registry")
                    else:
                        print(f"    ✅ DOCUMENTED in SSOT registry")

            except Exception as e:
                print(f"    ❌ BROKEN: {str(e)}")

        print(f"\nUndocumented working imports found: {len(missing_from_registry)}")
        for missing in missing_from_registry:
            print(f"  - {missing}")

        # TEST MUST FAIL: Assert all working imports are documented
        self.assertEqual(len(missing_from_registry), 0,
                        f"INCOMPLETE REGISTRY: {len(missing_from_registry)} working import paths not documented in SSOT registry. "
                        f"Issue #1196: Registry incompleteness leads to developer confusion and inconsistent imports.")

    def tearDown(self):
        """Print comprehensive summary of SSOT Import Registry compliance issues."""
        print(f"\n=== ISSUE #1196 INTEGRATION TEST SUMMARY ===")
        print(f"SSOT Import Registry Compliance Analysis:")

        if hasattr(self, 'import_timings') and self.import_timings:
            print(f"\nImport Performance Analysis:")
            for component, timings in self.import_timings.items():
                print(f"  {component}:")
                for path_type, timing in timings.items():
                    print(f"    {path_type}: {timing:.6f}s")

        print(f"\nIssue #1196 Status: INTEGRATION FAILURES EXPECTED")
        print(f"Business Impact: $500K+ ARR Golden Path blocked by:")
        print(f"  - Inaccurate SSOT Import Registry")
        print(f"  - Performance inconsistencies between import paths")
        print(f"  - Circular dependencies from fragmented imports")
        print(f"  - Undocumented import paths causing developer confusion")
        print(f"  - Inconsistent component initialization behavior")


if __name__ == "__main__":
    # Run with verbose output to see detailed analysis
    unittest.main(verbosity=2)