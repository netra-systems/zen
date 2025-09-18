"""Legacy Execution Engine Detection Test - SSOT Violation Detection

PURPOSE: Detect non-SSOT execution engines to prove violations exist
SHOULD FAIL NOW: 11+ legacy engines found
SHOULD PASS AFTER: Only UserExecutionEngine found

Business Value: Prevents $500K+ ARR user isolation vulnerabilities
"""

import ast
import os
import unittest
from pathlib import Path
from typing import List, Dict, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase


class LegacyExecutionEngineDetectionTests(SSotBaseTestCase):
    """Detect legacy execution engine implementations that violate SSOT."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"

        # SSOT: Only UserExecutionEngine should exist
        self.ssot_execution_engine = "UserExecutionEngine"

        # Expected legacy engines to detect (VIOLATIONS)
        self.expected_legacy_engines = {
            "UnifiedToolExecutionEngine",
            "ToolExecutionEngine",
            "RequestScopedExecutionEngine",
            "MCPEnhancedExecutionEngine",
            "UserExecutionEngineWrapper",
            "IsolatedExecutionEngine",
            "BaseExecutionEngine",
            "SupervisorExecutionEngineAdapter",
            "ConsolidatedExecutionEngineWrapper",
            "GenericExecutionEngineAdapter"
        }

    def test_legacy_execution_engine_filesystem_scan_fails(self):
        """SHOULD FAIL: Scan filesystem for legacy execution engines."""
        detected_engines = self._scan_filesystem_for_execution_engines()
        legacy_engines_found = detected_engines - {self.ssot_execution_engine}

        print(f"\n🔍 SSOT VIOLATION DETECTION:")
        print(f"   SSOT Engine: {self.ssot_execution_engine}")
        print(f"   Total Engines Found: {len(detected_engines)}")
        print(f"   Legacy Violations: {len(legacy_engines_found)}")
        print(f"   Expected Violations: {len(self.expected_legacy_engines)}")

        if legacy_engines_found:
            print(f"\nX LEGACY ENGINES DETECTED (VIOLATIONS):")
            for engine in sorted(legacy_engines_found):
                print(f"   - {engine}")

        # TEST SHOULD FAIL NOW - Legacy engines detected
        self.assertGreater(
            len(legacy_engines_found),
            0,
            f"X SSOT VIOLATION: Found {len(legacy_engines_found)} legacy execution engines. "
            f"Only {self.ssot_execution_engine} should exist."
        )

        # Verify expected violations are detected
        expected_found = self.expected_legacy_engines.intersection(legacy_engines_found)
        self.assertGreater(
            len(expected_found),
            5,  # Should find at least 5 expected violations
            f"X Expected to detect at least 5 violations, but only found {len(expected_found)}: {expected_found}"
        )

    def test_execution_engine_file_count_validation_fails(self):
        """SHOULD FAIL: Count execution engine implementation files."""
        engine_files = self._find_execution_engine_files()

        print(f"\n📁 EXECUTION ENGINE FILES:")
        print(f"   Total Files: {len(engine_files)}")

        if engine_files:
            print("   Files Found:")
            for file_path in sorted(engine_files):
                rel_path = file_path.relative_to(self.project_root)
                print(f"   - {rel_path}")

        # TEST SHOULD FAIL NOW - Multiple engine files found
        self.assertGreater(
            len(engine_files),
            1,  # Should find more than just UserExecutionEngine
            f"X SSOT VIOLATION: Found {len(engine_files)} execution engine files. "
            "Only user_execution_engine.py should contain implementations."
        )

    def test_execution_engine_class_definition_analysis_fails(self):
        """SHOULD FAIL: Analyze class definitions for SSOT compliance."""
        class_definitions = self._analyze_execution_engine_classes()

        print(f"\n🔬 CLASS DEFINITION ANALYSIS:")
        print(f"   Total Classes: {len(class_definitions)}")

        violation_count = 0
        for file_path, classes in class_definitions.items():
            if classes:  # Skip empty files
                rel_path = file_path.relative_to(self.project_root)
                print(f"   {rel_path}:")
                for class_name in classes:
                    if class_name != self.ssot_execution_engine:
                        print(f"   X {class_name} (VIOLATION)")
                        violation_count += 1
                    else:
                        print(f"   CHECK {class_name} (SSOT)")

        # TEST SHOULD FAIL NOW - Multiple class definitions found
        self.assertGreater(
            violation_count,
            0,
            f"X SSOT VIOLATION: Found {violation_count} non-SSOT execution engine classes. "
            f"Only {self.ssot_execution_engine} should be implemented."
        )

    def test_execution_engine_inheritance_chain_validation_fails(self):
        """SHOULD FAIL: Validate inheritance chains for SSOT compliance."""
        inheritance_violations = self._check_inheritance_violations()

        print(f"\n🔗 INHERITANCE CHAIN ANALYSIS:")
        print(f"   Violations Found: {len(inheritance_violations)}")

        if inheritance_violations:
            print("   Inheritance Violations:")
            for violation in inheritance_violations:
                print(f"   X {violation}")

        # TEST SHOULD FAIL NOW - Inheritance violations found
        self.assertGreater(
            len(inheritance_violations),
            0,
            f"X SSOT VIOLATION: Found {len(inheritance_violations)} inheritance violations. "
            "All engines should inherit from UserExecutionEngine SSOT pattern."
        )

    def _scan_filesystem_for_execution_engines(self) -> Set[str]:
        """Scan filesystem for execution engine class names."""
        execution_engines = set()

        # Scan netra_backend for execution engine classes
        for py_file in self.netra_backend_root.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse AST to find class definitions
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if "ExecutionEngine" in node.name:
                                execution_engines.add(node.name)

                except Exception as e:
                    # Skip files that can't be parsed
                    continue

        return execution_engines

    def _find_execution_engine_files(self) -> List[Path]:
        """Find files containing execution engine implementations."""
        engine_files = []

        for py_file in self.netra_backend_root.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for execution engine class definitions
                    if "class " in content and "ExecutionEngine" in content:
                        # Parse to confirm it's a class definition, not just a comment
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                if "ExecutionEngine" in node.name:
                                    engine_files.append(py_file)
                                    break

                except Exception:
                    # Skip files that can't be parsed
                    continue

        return engine_files

    def _analyze_execution_engine_classes(self) -> Dict[Path, List[str]]:
        """Analyze execution engine class definitions."""
        class_definitions = {}

        engine_files = self._find_execution_engine_files()
        for file_path in engine_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                classes = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if "ExecutionEngine" in node.name:
                            classes.append(node.name)

                class_definitions[file_path] = classes

            except Exception:
                class_definitions[file_path] = []

        return class_definitions

    def _check_inheritance_violations(self) -> List[str]:
        """Check for inheritance chain violations."""
        violations = []

        # Find classes that inherit from non-SSOT execution engines
        for py_file in self.netra_backend_root.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check base classes
                            for base in node.bases:
                                if isinstance(base, ast.Name):
                                    if ("ExecutionEngine" in base.id and
                                        base.id != self.ssot_execution_engine and
                                        base.id != "IExecutionEngine"):  # Interface is allowed
                                        violations.append(
                                            f"{node.name} inherits from {base.id} "
                                            f"(should inherit from {self.ssot_execution_engine})"
                                        )

                except Exception:
                    continue

        return violations


if __name__ == '__main__':
    unittest.main()
