"""Unit tests for Issue #686: Execution Engine SSOT Duplication Detection.

This test suite validates the multiple execution engine implementations issue
and ensures proper SSOT (Single Source of Truth) patterns are enforced.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Performance
- Value Impact: Protects $500K+ ARR chat functionality from Golden Path degradation
- Strategic Impact: Ensures single authoritative execution path for all agent operations

Key SSOT Requirements Being Tested:
1. UserExecutionEngine should be the ONLY active execution engine
2. All other execution engines should be adapters/facades to UserExecutionEngine
3. No duplicate execution logic across multiple classes
4. Proper migration paths from legacy implementations
5. WebSocket event routing through single channel

Test Strategy:
- Create INITIALLY FAILING tests to PROVE duplication exists
- Validate SSOT consolidation target (UserExecutionEngine)
- Detect legacy execution engines that should be removed/adapted
- Verify proper adapter patterns are in place
"""

import importlib
import inspect
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Set, Type
from unittest import TestCase

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestExecutionEngineDuplicationDetection(SSotBaseTestCase):
    """Unit tests to detect and validate execution engine SSOT violations."""

    def setUp(self):
        """Set up test fixtures for execution engine analysis."""
        super().setUp()

        # Define expected SSOT target and acceptable adapters
        self.ssot_target = "UserExecutionEngine"
        self.acceptable_adapters = {
            "SupervisorExecutionEngineAdapter",
            "ConsolidatedExecutionEngineWrapper",
            "GenericExecutionEngineAdapter",
            "ExecutionEngineAdapter",  # Base adapter class
            "MCPEnhancedExecutionEngine"  # MCP-specific extension
        }

        # Legacy engines that should redirect to SSOT
        self.expected_legacy_redirects = {
            "ExecutionEngine",  # Should redirect to UserExecutionEngine
            "ToolExecutionEngine"  # Should delegate to UnifiedToolExecutionEngine
        }

        self.discovered_execution_engines = {}
        self.ssot_violations = []

    def test_01_detect_multiple_execution_engine_implementations(self):
        """INITIALLY FAILING TEST: Detect multiple execution engine implementations.

        This test SHOULD FAIL initially to prove Issue #686 exists.
        Multiple execution engines indicate SSOT violations.
        """
        execution_engines = self._discover_execution_engine_classes()

        # Log discovered engines for debugging
        print(f"\nDISCOVERED EXECUTION ENGINES ({len(execution_engines)}):")
        for name, info in execution_engines.items():
            print(f"  {name}: {info['file_path']} (line {info['line_number']})")

        # EXPECTED TO FAIL: Should have only UserExecutionEngine + acceptable adapters
        expected_total = 1 + len(self.acceptable_adapters) + len(self.expected_legacy_redirects)

        self.assertLessEqual(
            len(execution_engines),
            expected_total,
            f"SSOT VIOLATION: Found {len(execution_engines)} execution engines, "
            f"expected max {expected_total} (1 SSOT + {len(self.acceptable_adapters)} adapters + "
            f"{len(self.expected_legacy_redirects)} legacy redirects). "
            f"Extra engines indicate Issue #686 duplication problem."
        )

        # Store for other tests
        self.discovered_execution_engines = execution_engines

    def test_02_validate_ssot_target_exists_and_is_primary(self):
        """Validate that UserExecutionEngine exists and has primary implementation."""
        execution_engines = self._discover_execution_engine_classes()

        # SSOT target must exist
        self.assertIn(
            self.ssot_target,
            execution_engines,
            f"SSOT target '{self.ssot_target}' not found. Available engines: {list(execution_engines.keys())}"
        )

        # Get UserExecutionEngine details
        user_engine_info = execution_engines[self.ssot_target]

        # Load the actual class to analyze
        user_engine_class = self._load_execution_engine_class(user_engine_info)

        if user_engine_class:
            # Verify it has substantial implementation (not just a redirect)
            method_count = len([method for method in dir(user_engine_class)
                              if not method.startswith('_') and callable(getattr(user_engine_class, method, None))])

            self.assertGreater(
                method_count,
                5,  # Should have multiple execution methods
                f"SSOT target {self.ssot_target} appears to be a facade/redirect with only {method_count} methods. "
                f"Primary implementation should have substantial method count."
            )

    def test_03_detect_execution_engines_with_duplicate_logic(self):
        """INITIALLY FAILING TEST: Detect execution engines with duplicate business logic.

        This test SHOULD FAIL to prove duplicate execution logic exists.
        """
        execution_engines = self._discover_execution_engine_classes()
        engines_with_logic = {}

        for engine_name, engine_info in execution_engines.items():
            engine_class = self._load_execution_engine_class(engine_info)
            if not engine_class:
                continue

            # Check for substantial implementation vs adapter pattern
            has_execute_methods = any(
                method_name.startswith(('execute', 'run', 'process'))
                for method_name in dir(engine_class)
                if not method_name.startswith('_')
            )

            if has_execute_methods:
                # Check if it's doing real work vs delegation
                source_lines = self._get_class_source_lines(engine_class)
                has_substantial_logic = any(
                    any(keyword in line.lower() for keyword in ['await', 'async', 'return', 'if', 'for', 'while'])
                    for line in source_lines
                    if not line.strip().startswith('#')
                )

                if has_substantial_logic:
                    engines_with_logic[engine_name] = {
                        'class': engine_class,
                        'methods': [m for m in dir(engine_class) if m.startswith(('execute', 'run', 'process')) and not m.startswith('_')],
                        'source_lines': len(source_lines)
                    }

        # Log findings
        print(f"\nENGINES WITH EXECUTION LOGIC ({len(engines_with_logic)}):")
        for name, info in engines_with_logic.items():
            print(f"  {name}: {info['methods']} ({info['source_lines']} lines)")

        # EXPECTED TO FAIL: Should have only SSOT + necessary adapters doing real work
        acceptable_engines_with_logic = {self.ssot_target} | self.acceptable_adapters

        actual_engines_with_logic = set(engines_with_logic.keys())
        violating_engines = actual_engines_with_logic - acceptable_engines_with_logic

        self.assertEqual(
            len(violating_engines),
            0,
            f"SSOT VIOLATION: Found execution engines with duplicate logic: {violating_engines}. "
            f"Only {acceptable_engines_with_logic} should contain substantial execution logic. "
            f"Other engines should be thin adapters/facades."
        )

    def test_04_validate_legacy_engines_are_proper_redirects(self):
        """Validate that legacy execution engines properly redirect to SSOT."""
        execution_engines = self._discover_execution_engine_classes()

        for legacy_engine in self.expected_legacy_redirects:
            if legacy_engine not in execution_engines:
                continue  # Skip if legacy engine doesn't exist

            legacy_info = execution_engines[legacy_engine]
            legacy_class = self._load_execution_engine_class(legacy_info)

            if not legacy_class:
                continue

            # Check if it's a proper redirect/import alias
            source_lines = self._get_class_source_lines(legacy_class)

            # Look for import redirection patterns
            has_import_redirect = any(
                'import' in line and (self.ssot_target in line or 'UserExecutionEngine' in line)
                for line in source_lines[:10]  # Check top of file for imports
            )

            # Or check if it inherits from/delegates to SSOT
            has_delegation = any(
                self.ssot_target in line or 'UserExecutionEngine' in line
                for line in source_lines
            )

            self.assertTrue(
                has_import_redirect or has_delegation,
                f"Legacy engine {legacy_engine} should redirect to SSOT {self.ssot_target} "
                f"but no redirection pattern found in source. File: {legacy_info['file_path']}"
            )

    def test_05_validate_execution_engine_factory_ssot_compliance(self):
        """Validate that execution engine factories create SSOT instances."""
        factory_patterns = self._discover_execution_engine_factories()

        print(f"\nDISCOVERED EXECUTION ENGINE FACTORIES ({len(factory_patterns)}):")
        for factory_name, factory_info in factory_patterns.items():
            print(f"  {factory_name}: {factory_info['file_path']}")

        # Check each factory creates UserExecutionEngine instances
        for factory_name, factory_info in factory_patterns.items():
            factory_class = self._load_execution_engine_class(factory_info)
            if not factory_class:
                continue

            source_lines = self._get_class_source_lines(factory_class)

            # Look for UserExecutionEngine creation
            creates_user_engine = any(
                'UserExecutionEngine' in line and ('(' in line or 'return' in line)
                for line in source_lines
            )

            # Allow some flexibility for factory patterns
            if not creates_user_engine:
                # Check for indirect creation patterns
                creates_ssot_engine = any(
                    any(pattern in line for pattern in [self.ssot_target, 'execution_engine', 'ExecutionEngine'])
                    for line in source_lines
                    if 'return' in line or 'create' in line or '__init__' in line
                )

                self.assertTrue(
                    creates_ssot_engine,
                    f"Factory {factory_name} should create SSOT execution engines "
                    f"but no creation pattern found. File: {factory_info['file_path']}"
                )

    def test_06_validate_websocket_event_routing_ssot(self):
        """Validate WebSocket events are routed through single execution channel."""
        execution_engines = self._discover_execution_engine_classes()
        websocket_engines = {}

        for engine_name, engine_info in execution_engines.items():
            engine_class = self._load_execution_engine_class(engine_info)
            if not engine_class:
                continue

            source_lines = self._get_class_source_lines(engine_class)

            # Check for WebSocket event handling
            has_websocket_events = any(
                any(event in line.lower() for event in ['websocket', 'socket', 'emit', 'send_event', 'notify'])
                for line in source_lines
            )

            if has_websocket_events:
                websocket_engines[engine_name] = engine_info

        print(f"\nENGINES WITH WEBSOCKET INTEGRATION ({len(websocket_engines)}):")
        for name, info in websocket_engines.items():
            print(f"  {name}: {info['file_path']}")

        # WebSocket integration should be in SSOT + specific tools
        acceptable_websocket_engines = {
            self.ssot_target,
            "UnifiedToolExecutionEngine",  # Tool-specific WebSocket notifications
            "MCPEnhancedExecutionEngine"   # MCP-specific WebSocket handling
        }

        actual_websocket_engines = set(websocket_engines.keys())
        violating_websocket_engines = actual_websocket_engines - acceptable_websocket_engines

        self.assertEqual(
            len(violating_websocket_engines),
            0,
            f"SSOT VIOLATION: Found execution engines with duplicate WebSocket handling: {violating_websocket_engines}. "
            f"WebSocket events should be routed through SSOT channels only: {acceptable_websocket_engines}"
        )

    def _discover_execution_engine_classes(self) -> Dict[str, Dict]:
        """Discover all execution engine classes in the codebase."""
        execution_engines = {}

        # Define search paths relative to project root
        search_paths = [
            Path("netra_backend/app/agents"),
            Path("netra_backend/app/core"),
            Path("netra_backend/app/services"),
            Path("netra_backend/app/tools")
        ]

        # Get project root (3 levels up from this test file)
        project_root = Path(__file__).parent.parent.parent.parent

        for search_path in search_paths:
            full_path = project_root / search_path
            if not full_path.exists():
                continue

            for py_file in full_path.rglob("*.py"):
                if py_file.name.startswith("test_"):
                    continue  # Skip test files

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        if 'class ' in line and 'ExecutionEngine' in line:
                            # Extract class name
                            class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                            if 'ExecutionEngine' in class_name:
                                execution_engines[class_name] = {
                                    'file_path': str(py_file),
                                    'line_number': line_num,
                                    'class_definition': line.strip()
                                }

                except (IOError, UnicodeDecodeError):
                    continue  # Skip files that can't be read

        return execution_engines

    def _discover_execution_engine_factories(self) -> Dict[str, Dict]:
        """Discover all execution engine factory classes."""
        factories = {}

        # Define search paths
        search_paths = [
            Path("netra_backend/app/agents"),
            Path("netra_backend/app/core/managers"),
        ]

        project_root = Path(__file__).parent.parent.parent.parent

        for search_path in search_paths:
            full_path = project_root / search_path
            if not full_path.exists():
                continue

            for py_file in full_path.rglob("*.py"):
                if py_file.name.startswith("test_"):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        if 'class ' in line and ('ExecutionEngine' in line and 'Factory' in line):
                            class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                            factories[class_name] = {
                                'file_path': str(py_file),
                                'line_number': line_num,
                                'class_definition': line.strip()
                            }

                except (IOError, UnicodeDecodeError):
                    continue

        return factories

    def _load_execution_engine_class(self, engine_info: Dict) -> Type:
        """Load an execution engine class for analysis."""
        try:
            file_path = Path(engine_info['file_path'])

            # Convert file path to module path
            project_root = Path(__file__).parent.parent.parent.parent
            relative_path = file_path.relative_to(project_root)

            # Convert to module path
            module_path = str(relative_path.with_suffix('')).replace('/', '.').replace('\\', '.')

            # Import module
            module = importlib.import_module(module_path)

            # Find class in module by name
            class_name = engine_info['class_definition'].split('class ')[1].split('(')[0].split(':')[0].strip()

            if hasattr(module, class_name):
                return getattr(module, class_name)

        except (ImportError, ValueError, AttributeError):
            pass  # Failed to load class

        return None

    def _get_class_source_lines(self, cls: Type) -> List[str]:
        """Get source code lines for a class."""
        try:
            return inspect.getsourcelines(cls)[0]
        except (OSError, TypeError):
            return []


if __name__ == '__main__':
    unittest.main()