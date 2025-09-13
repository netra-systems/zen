"""SSOT Violation Tests for Issue #821 - SupervisorAgent Consolidation



Business Value: Protect $500K+ ARR by ensuring single SupervisorAgent implementation

BVJ: ALL segments | Platform Stability | SSOT compliance prevents race conditions



MISSION: Create tests that FAIL when multiple SupervisorAgent implementations exist

REQUIREMENT: Tests must FAIL currently and PASS after SSOT consolidation

"""



import ast

import importlib

import inspect

import os

import sys

import unittest

from pathlib import Path

from typing import List, Dict, Any



# Test framework imports

from test_framework.ssot.base_test_case import SSotBaseTestCase





class TestSupervisorAgentSSOTViolations(SSotBaseTestCase):

    """Tests that expose SSOT violations in SupervisorAgent implementations.



    These tests are designed to FAIL when multiple SupervisorAgent implementations exist

    and PASS after proper SSOT consolidation to supervisor_ssot.py only.

    """



    def setUp(self):

        """Set up test environment."""

        super().setUp()

        self.project_root = Path(__file__).parent.parent.parent

        self.netra_backend_path = self.project_root / "netra_backend"

        # Ensure paths exist

        if not self.project_root.exists():

            self.fail(f"Project root not found at: {self.project_root}")

        if not self.netra_backend_path.exists():

            self.fail(f"Netra backend path not found at: {self.netra_backend_path}")



    def test_only_one_supervisor_agent_class_definition_exists(self):

        """TEST THAT MUST FAIL: Only one SupervisorAgent class should exist in active code.



        This test scans for SupervisorAgent class definitions and should FAIL if multiple exist.

        Expected to PASS only after SSOT consolidation to supervisor_ssot.py.

        """

        supervisor_classes = []

        project_root = Path(__file__).parent.parent.parent

        netra_backend_path = project_root / "netra_backend"



        # Scan for SupervisorAgent class definitions in active code (not backups)

        for py_file in netra_backend_path.rglob("*.py"):

            # Skip backup directories and test files

            if ("backup" in str(py_file).lower() or

                "test" in py_file.name or

                "__pycache__" in str(py_file)):

                continue



            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    content = f.read()



                # Parse the file to find class definitions

                try:

                    tree = ast.parse(content)

                    for node in ast.walk(tree):

                        if (isinstance(node, ast.ClassDef) and

                            node.name == "SupervisorAgent"):

                            supervisor_classes.append({

                                'file': str(py_file),

                                'line': node.lineno,

                                'name': node.name

                            })

                except SyntaxError:

                    # Skip files with syntax errors

                    continue



            except (UnicodeDecodeError, PermissionError):

                # Skip binary files or permission issues

                continue



        # Log findings for debugging

        print(f"\n=== SSOT VIOLATION SCAN RESULTS ===")

        print(f"SupervisorAgent classes found: {len(supervisor_classes)}")

        for cls in supervisor_classes:

            print(f"  - {cls['file']}:{cls['line']} -> {cls['name']}")

        print("="*50)



        # ASSERTION: Should have exactly ONE SupervisorAgent class

        # This test FAILS if multiple implementations exist

        self.assertEqual(

            len(supervisor_classes),

            1,

            f"SSOT VIOLATION: Found {len(supervisor_classes)} SupervisorAgent class definitions. "

            f"Expected exactly 1 in supervisor_ssot.py. Violations: {supervisor_classes}"

        )



        # Verify it's in the correct SSOT location

        if supervisor_classes:

            ssot_expected_path = "supervisor_ssot.py"

            actual_file = supervisor_classes[0]['file']

            self.assertIn(

                ssot_expected_path,

                actual_file,

                f"SSOT VIOLATION: SupervisorAgent found in {actual_file}, "

                f"expected only in {ssot_expected_path}"

            )



    def test_all_supervisor_agent_imports_use_ssot_path(self):

        """TEST THAT MUST FAIL: All imports should use the SSOT path.



        This test scans for SupervisorAgent imports and validates they use consistent path.

        Should FAIL if any imports use non-SSOT paths.

        """

        import_violations = []

        expected_ssot_path = "netra_backend.app.agents.supervisor_ssot"

        project_root = Path(__file__).parent.parent.parent

        netra_backend_path = project_root / "netra_backend"



        # Scan for SupervisorAgent imports in active code

        for py_file in netra_backend_path.rglob("*.py"):

            # Skip backup directories

            if "backup" in str(py_file).lower():

                continue



            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    content = f.read()

                    lines = content.splitlines()



                for line_num, line in enumerate(lines, 1):

                    line = line.strip()

                    # Check for SupervisorAgent imports

                    if ("SupervisorAgent" in line and

                        ("import" in line or "from" in line) and

                        not line.startswith("#")):  # Skip comments



                        # Check if it uses the correct SSOT path

                        if expected_ssot_path not in line:

                            import_violations.append({

                                'file': str(py_file),

                                'line': line_num,

                                'content': line,

                                'expected_path': expected_ssot_path

                            })



            except (UnicodeDecodeError, PermissionError):

                continue



        # Log findings for debugging

        print(f"\n=== IMPORT VIOLATION SCAN RESULTS ===")

        print(f"Non-SSOT SupervisorAgent imports found: {len(import_violations)}")

        for violation in import_violations:

            print(f"  - {violation['file']}:{violation['line']} -> {violation['content']}")

        print("="*50)



        # ASSERTION: Should have zero non-SSOT imports

        # This test FAILS if any imports don't use SSOT path

        self.assertEqual(

            len(import_violations),

            0,

            f"SSOT VIOLATION: Found {len(import_violations)} non-SSOT SupervisorAgent imports. "

            f"All imports must use path: {expected_ssot_path}. Violations: {import_violations}"

        )



    def test_no_duplicate_supervisor_agent_instances_in_registry(self):

        """TEST THAT MUST FAIL: Agent registry should not have duplicate SupervisorAgent registrations.



        This test checks the agent registry for duplicate SupervisorAgent instances.

        Should FAIL if multiple supervisor implementations are registered.

        """

        try:

            # Import agent registry

            from netra_backend.app.agents.registry import agent_registry



            # Check for SupervisorAgent registrations

            supervisor_registrations = []



            # Get all registered agents

            if hasattr(agent_registry, '_agents'):

                for agent_name, agent_class in agent_registry._agents.items():

                    if hasattr(agent_class, '__name__') and 'SupervisorAgent' in agent_class.__name__:

                        supervisor_registrations.append({

                            'name': agent_name,

                            'class': agent_class,

                            'module': getattr(agent_class, '__module__', 'unknown')

                        })



            # Log findings for debugging

            print(f"\n=== REGISTRY VIOLATION SCAN RESULTS ===")

            print(f"SupervisorAgent registrations found: {len(supervisor_registrations)}")

            for reg in supervisor_registrations:

                print(f"  - {reg['name']} -> {reg['class']} from {reg['module']}")

            print("="*50)



            # ASSERTION: Should have at most ONE supervisor registration

            # This test FAILS if multiple supervisor registrations exist

            self.assertLessEqual(

                len(supervisor_registrations),

                1,

                f"SSOT VIOLATION: Found {len(supervisor_registrations)} SupervisorAgent registrations. "

                f"Expected at most 1 SSOT registration. Duplicates: {supervisor_registrations}"

            )



            # If there is a registration, it should be from SSOT module

            if supervisor_registrations:

                ssot_module = "netra_backend.app.agents.supervisor_ssot"

                actual_module = supervisor_registrations[0]['module']

                self.assertEqual(

                    actual_module,

                    ssot_module,

                    f"SSOT VIOLATION: SupervisorAgent registered from {actual_module}, "

                    f"expected from {ssot_module}"

                )



        except ImportError as e:

            # If agent registry doesn't exist, that's not a violation for this test

            self.skipTest(f"Agent registry not available: {e}")



    def test_supervisor_agent_import_path_consistency(self):

        """TEST THAT MUST FAIL: SupervisorAgent should be importable only from SSOT path.



        This test attempts to import SupervisorAgent from different paths.

        Should FAIL if multiple import paths work.

        """

        ssot_path = "netra_backend.app.agents.supervisor_ssot"

        potential_violation_paths = [

            "netra_backend.app.agents.supervisor_consolidated",

            "netra_backend.app.agents.supervisor",

            "netra_backend.app.agents.supervisor_modern",

        ]



        # Test SSOT path works

        try:

            module = importlib.import_module(ssot_path)

            supervisor_class = getattr(module, "SupervisorAgent", None)

            self.assertIsNotNone(

                supervisor_class,

                f"SSOT path {ssot_path} should contain SupervisorAgent class"

            )

        except ImportError:

            self.fail(f"SSOT VIOLATION: Cannot import SupervisorAgent from SSOT path {ssot_path}")



        # Test that violation paths don't work (or if they do, it's a violation)

        working_violation_paths = []

        for violation_path in potential_violation_paths:

            try:

                module = importlib.import_module(violation_path)

                supervisor_class = getattr(module, "SupervisorAgent", None)

                if supervisor_class is not None:

                    working_violation_paths.append({

                        'path': violation_path,

                        'class': supervisor_class

                    })

            except ImportError:

                # This is expected - violation paths should not work

                pass



        # Log findings for debugging

        print(f"\n=== IMPORT PATH VIOLATION SCAN RESULTS ===")

        print(f"Working violation paths found: {len(working_violation_paths)}")

        for violation in working_violation_paths:

            print(f"  - {violation['path']} -> {violation['class']}")

        print("="*50)



        # ASSERTION: Should have zero working violation paths

        # This test FAILS if multiple import paths work

        self.assertEqual(

            len(working_violation_paths),

            0,

            f"SSOT VIOLATION: SupervisorAgent importable from {len(working_violation_paths)} "

            f"non-SSOT paths. Only {ssot_path} should work. Violations: {working_violation_paths}"

        )





if __name__ == "__main__":

    unittest.main(verbosity=2)

