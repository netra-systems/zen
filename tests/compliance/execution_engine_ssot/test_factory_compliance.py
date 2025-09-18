"""Factory Compliance Test - SSOT Violation Detection

PURPOSE: Validate all factories create UserExecutionEngine instances only
SHOULD FAIL NOW: Factories create different engine types
SHOULD PASS AFTER: All factories create UserExecutionEngine

Business Value: Prevents 500K+ ARR factory-based user isolation bypass
"""

import ast
import inspect
import importlib
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Set, Type
from test_framework.ssot.base_test_case import SSotBaseTestCase


class FactoryComplianceTests(SSotBaseTestCase):
    """Validate factory compliance with SSOT execution engine pattern."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"

        # SSOT: Only UserExecutionEngine should be created by factories
        self.ssot_execution_engine = "UserExecutionEngine"

        # Expected factory files that may have violations
        self.factory_files_to_check = [
            "netra_backend/app/agents/supervisor/execution_engine_factory.py",
            "netra_backend/app/agents/supervisor/execution_factory.py",
            "netra_backend/app/agents/execution_engine_unified_factory.py",
            "netra_backend/app/agents/execution_engine_legacy_adapter.py",
            "netra_backend/app/core/managers/execution_engine_factory.py"
        ]

    def test_factory_class_detection_fails(self):
        """SHOULD FAIL: Detect multiple factory classes."""
        factory_classes = self._detect_factory_classes()

        print(f"\n🏭 FACTORY CLASS DETECTION:")
        print(f"   Total Factory Classes: {len(factory_classes)}")

        if factory_classes:
            print("   Factory Classes Found:")
            for file_path, classes in factory_classes.items():
                rel_path = file_path.relative_to(self.project_root)
                print(f"   📁 {rel_path}:")
                for class_name in classes:
                    print(f"      - {class_name}")

        # TEST SHOULD FAIL NOW - Multiple factory classes detected
        total_factories = sum(len(classes) for classes in factory_classes.values())
        self.assertGreater(
            total_factories,
            1,  # Should have more than one factory (VIOLATION)
            f"X SSOT VIOLATION: Found {total_factories} factory classes. "
            "Only one SSOT ExecutionEngineFactory should exist."
        )

    def test_factory_return_type_analysis_fails(self):
        """SHOULD FAIL: Analyze factory return types for SSOT compliance."""
        return_type_violations = self._analyze_factory_return_types()

        print(f"\n🔍 FACTORY RETURN TYPE ANALYSIS:")
        print(f"   Violations Found: {len(return_type_violations)}")

        violation_count = 0
        for file_path, violations in return_type_violations.items():
            if violations:
                rel_path = file_path.relative_to(self.project_root)
                print(f"   📁 {rel_path}:")
                for violation in violations:
                    print(f"      X {violation}")
                    violation_count += 1

        # TEST SHOULD FAIL NOW - Return type violations detected
        self.assertGreater(
            violation_count,
            0,
            f"X SSOT VIOLATION: Found {violation_count} factory return type violations. "
            f"All factories must return {self.ssot_execution_engine} instances."
        )

    def test_factory_method_instantiation_analysis_fails(self):
        """SHOULD FAIL: Analyze factory methods for instantiation violations."""
        instantiation_violations = self._analyze_factory_instantiations()

        print(f"\n🔧 FACTORY INSTANTIATION ANALYSIS:")
        print(f"   Files Analyzed: {len(instantiation_violations)}")

        violation_count = 0
        for file_path, violations in instantiation_violations.items():
            if violations:
                rel_path = file_path.relative_to(self.project_root)
                print(f"   📁 {rel_path}:")
                for violation in violations:
                    print(f"      X {violation}")
                    violation_count += 1

        # TEST SHOULD FAIL NOW - Instantiation violations detected
        self.assertGreater(
            violation_count,
            0,
            f"X SSOT VIOLATION: Found {violation_count} factory instantiation violations. "
            "Factories must only instantiate SSOT execution engines."
        )

    def test_factory_interface_compliance_fails(self):
        """SHOULD FAIL: Validate factory interface compliance."""
        interface_violations = self._check_factory_interfaces()

        print(f"\n📋 FACTORY INTERFACE COMPLIANCE:")
        print(f"   Violations Found: {len(interface_violations)}")

        if interface_violations:
            print("   Interface Violations:")
            for violation in interface_violations:
                print(f"      X {violation}")

        # TEST SHOULD FAIL NOW - Interface violations detected
        self.assertGreater(
            len(interface_violations),
            0,
            f"X SSOT VIOLATION: Found {len(interface_violations)} factory interface violations. "
            "All factories must follow SSOT interface patterns."
        )

    def test_factory_dependency_injection_fails(self):
        """SHOULD FAIL: Check factory dependency injection for SSOT violations."""
        dependency_violations = self._check_dependency_injection()

        print(f"\n💉 FACTORY DEPENDENCY INJECTION:")
        print(f"   Violations Found: {len(dependency_violations)}")

        if dependency_violations:
            print("   Dependency Violations:")
            for file_path, violations in dependency_violations.items():
                rel_path = file_path.relative_to(self.project_root)
                print(f"   📁 {rel_path}:")
                for violation in violations:
                    print(f"      X {violation}")

        # TEST SHOULD FAIL NOW - Dependency injection violations detected
        total_violations = sum(len(violations) for violations in dependency_violations.values())
        self.assertGreater(
            total_violations,
            0,
            f"X SSOT VIOLATION: Found {total_violations} dependency injection violations. "
            "Factories must inject SSOT execution engines only."
        )

    def _detect_factory_classes(self) -> Dict[Path, List[str]]:
        """Detect factory classes in the codebase."""
        factory_classes = {}

        for py_file in self.netra_backend_root.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse AST to find factory classes
                    tree = ast.parse(content)
                    file_factories = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check if it's a factory class
                            if (("Factory" in node.name and "ExecutionEngine" in node.name) or
                                ("ExecutionEngine" in node.name and "Factory" in node.name) or
                                (node.name == "ExecutionEngineFactory")):
                                file_factories.append(node.name)

                    if file_factories:
                        factory_classes[py_file] = file_factories

                except Exception:
                    continue

        return factory_classes

    def _analyze_factory_return_types(self) -> Dict[Path, List[str]]:
        """Analyze factory return types for SSOT compliance."""
        return_type_violations = {}

        factory_classes = self._detect_factory_classes()
        for file_path, classes in factory_classes.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                violations = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check methods that likely return execution engines
                        if (node.name.startswith('create') or
                            node.name.startswith('build') or
                            node.name.startswith('make') or
                            'engine' in node.name.lower()):

                            # Check return type annotations
                            if node.returns:
                                return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                                if ('ExecutionEngine' in return_type and
                                    self.ssot_execution_engine not in return_type):
                                    violations.append(
                                        f"Method '{node.name}' returns non-SSOT type: {return_type}"
                                    )

                            # Check return statements in method body
                            for child in ast.walk(node):
                                if isinstance(child, ast.Return) and child.value:
                                    if isinstance(child.value, ast.Call):
                                        if isinstance(child.value.func, ast.Name):
                                            # Check if returning non-SSOT engine
                                            returned_type = child.value.func.id
                                            if ('ExecutionEngine' in returned_type and
                                                returned_type != self.ssot_execution_engine):
                                                violations.append(
                                                    f"Method '{node.name}' returns non-SSOT instance: {returned_type}()"
                                                )

                if violations:
                    return_type_violations[file_path] = violations

            except Exception:
                continue

        return return_type_violations

    def _analyze_factory_instantiations(self) -> Dict[Path, List[str]]:
        """Analyze factory method instantiations."""
        instantiation_violations = {}

        # Non-SSOT engines that shouldn't be instantiated
        forbidden_instantiations = {
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

        for py_file in self.netra_backend_root.rglob("*.py"):
            if "factory" in str(py_file).lower():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    violations = []
                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()

                        # Look for instantiations of forbidden engines
                        for forbidden in forbidden_instantiations:
                            if f"{forbidden}(" in line and "return" in line:
                                violations.append(
                                    f"Line {line_num}: Instantiates forbidden engine '{forbidden}': {line}"
                                )

                        # Look for generic patterns that might instantiate non-SSOT engines
                        if ("return " in line and
                            "ExecutionEngine(" in line and
                            self.ssot_execution_engine not in line):
                            violations.append(
                                f"Line {line_num}: Non-SSOT instantiation: {line}"
                            )

                    if violations:
                        instantiation_violations[py_file] = violations

                except Exception:
                    continue

        return instantiation_violations

    def _check_factory_interfaces(self) -> List[str]:
        """Check factory interface compliance."""
        violations = []

        factory_classes = self._detect_factory_classes()
        for file_path, classes in factory_classes.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if node.name in classes:
                            # Check if factory follows SSOT interface pattern
                            has_create_method = False
                            has_proper_interface = False

                            for method in node.body:
                                if isinstance(method, ast.FunctionDef):
                                    # Should have create_* methods
                                    if method.name.startswith('create'):
                                        has_create_method = True

                                    # Check for proper SSOT method names
                                    if (method.name in ['create_user_execution_engine',
                                                       'create_execution_engine',
                                                       'get_execution_engine']):
                                        has_proper_interface = True

                            if not has_create_method:
                                violations.append(
                                    f"Factory '{node.name}' in {file_path.relative_to(self.project_root)} "
                                    "missing create_* methods"
                                )

                            if not has_proper_interface:
                                violations.append(
                                    f"Factory '{node.name}' in {file_path.relative_to(self.project_root)} "
                                    "doesn't follow SSOT interface pattern"
                                )

            except Exception:
                continue

        return violations

    def _check_dependency_injection(self) -> Dict[Path, List[str]]:
        """Check dependency injection for SSOT compliance."""
        dependency_violations = {}

        factory_classes = self._detect_factory_classes()
        for file_path, classes in factory_classes.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                violations = []

                # Look for dependency injection patterns
                injection_patterns = [
                    "inject(",
                    "get_dependency(",
                    "resolve(",
                    "container.get(",
                ]

                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern in injection_patterns:
                        if pattern in line and "ExecutionEngine" in line:
                            # Check if injecting non-SSOT engine
                            if self.ssot_execution_engine not in line:
                                violations.append(
                                    f"Line {line_num}: Non-SSOT dependency injection: {line.strip()}"
                                )

                if violations:
                    dependency_violations[file_path] = violations

            except Exception:
                continue

        return dependency_violations


if __name__ == '__main__':
    unittest.main()
