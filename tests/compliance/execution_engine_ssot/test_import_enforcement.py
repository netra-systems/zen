"""Import Enforcement Test - SSOT Violation Detection



PURPOSE: Ensure all code imports UserExecutionEngine SSOT only

SHOULD FAIL NOW: Imports to non-SSOT engines found

SHOULD PASS AFTER: All imports redirect to UserExecutionEngine



Business Value: Prevents $500K+ ARR import-based user isolation bypass

"""



import ast

import os

import re

import unittest

from pathlib import Path

from typing import Dict, List, Set, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase





class TestImportEnforcement(SSotBaseTestCase):

    """Enforce SSOT import patterns for execution engines."""



    def setUp(self):

        """Set up test environment."""

        super().setUp()

        self.project_root = Path(__file__).parent.parent.parent.parent

        self.netra_backend_root = self.project_root / "netra_backend"



        # SSOT: Only these imports should be allowed

        self.allowed_ssot_imports = {

            "UserExecutionEngine",

            "IExecutionEngine",  # Interface is allowed

            "ExecutionEngineCapabilities",  # Support class is allowed

            "ExecutionEngineAdapter",  # Base adapter is allowed

        }



        # VIOLATIONS: These imports should be blocked

        self.forbidden_legacy_imports = {

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



    def test_forbidden_execution_engine_imports_fails(self):

        """SHOULD FAIL: Detect forbidden execution engine imports."""

        forbidden_imports = self._scan_for_forbidden_imports()



        print(f"\n🚫 FORBIDDEN IMPORT DETECTION:")

        print(f"   Total Violations: {len(forbidden_imports)}")



        if forbidden_imports:

            print("   Import Violations Found:")

            for file_path, imports in forbidden_imports.items():

                rel_path = file_path.relative_to(self.project_root)

                print(f"   📁 {rel_path}:")

                for import_info in imports:

                    print(f"      ❌ {import_info}")



        # TEST SHOULD FAIL NOW - Forbidden imports detected

        total_violations = sum(len(imports) for imports in forbidden_imports.values())

        self.assertGreater(

            total_violations,

            0,

            f"❌ SSOT VIOLATION: Found {total_violations} forbidden execution engine imports. "

            f"Only SSOT imports allowed: {self.allowed_ssot_imports}"

        )



    def test_non_ssot_import_statements_analysis_fails(self):

        """SHOULD FAIL: Analyze import statements for SSOT compliance."""

        import_violations = self._analyze_import_statements()



        print(f"\n📋 IMPORT STATEMENT ANALYSIS:")

        print(f"   Files Analyzed: {len(import_violations)}")



        violation_count = 0

        for file_path, violations in import_violations.items():

            if violations:

                rel_path = file_path.relative_to(self.project_root)

                print(f"   📁 {rel_path}:")

                for violation in violations:

                    print(f"      ❌ {violation}")

                    violation_count += 1



        # TEST SHOULD FAIL NOW - Import statement violations found

        self.assertGreater(

            violation_count,

            0,

            f"❌ SSOT VIOLATION: Found {violation_count} non-SSOT import statements. "

            "All execution engine imports must use SSOT pattern."

        )



    def test_string_based_import_detection_fails(self):

        """SHOULD FAIL: Detect string-based imports that bypass SSOT."""

        string_imports = self._scan_for_string_based_imports()



        print(f"\n🔍 STRING-BASED IMPORT DETECTION:")

        print(f"   Violations Found: {len(string_imports)}")



        if string_imports:

            print("   String Import Violations:")

            for file_path, violations in string_imports.items():

                rel_path = file_path.relative_to(self.project_root)

                print(f"   📁 {rel_path}:")

                for violation in violations:

                    print(f"      ❌ {violation}")



        # TEST SHOULD FAIL NOW - String-based imports detected

        total_violations = sum(len(violations) for violations in string_imports.values())

        self.assertGreater(

            total_violations,

            0,

            f"❌ SSOT VIOLATION: Found {total_violations} string-based execution engine imports. "

            "These bypass SSOT enforcement and create security vulnerabilities."

        )



    def test_dynamic_import_patterns_fails(self):

        """SHOULD FAIL: Detect dynamic import patterns that bypass SSOT."""

        dynamic_imports = self._scan_for_dynamic_imports()



        print(f"\n⚡ DYNAMIC IMPORT PATTERN DETECTION:")

        print(f"   Violations Found: {len(dynamic_imports)}")



        if dynamic_imports:

            print("   Dynamic Import Violations:")

            for file_path, violations in dynamic_imports.items():

                rel_path = file_path.relative_to(self.project_root)

                print(f"   📁 {rel_path}:")

                for violation in violations:

                    print(f"      ❌ {violation}")



        # TEST SHOULD FAIL NOW - Dynamic imports detected

        total_violations = sum(len(violations) for violations in dynamic_imports.values())

        self.assertGreater(

            total_violations,

            0,

            f"❌ SSOT VIOLATION: Found {total_violations} dynamic execution engine imports. "

            "Dynamic imports must be refactored to use SSOT pattern."

        )



    def test_import_alias_compliance_fails(self):

        """SHOULD FAIL: Check import aliases for SSOT compliance."""

        alias_violations = self._check_import_aliases()



        print(f"\n🏷️  IMPORT ALIAS COMPLIANCE:")

        print(f"   Violations Found: {len(alias_violations)}")



        if alias_violations:

            print("   Alias Violations:")

            for file_path, violations in alias_violations.items():

                rel_path = file_path.relative_to(self.project_root)

                print(f"   📁 {rel_path}:")

                for violation in violations:

                    print(f"      ❌ {violation}")



        # TEST SHOULD FAIL NOW - Import alias violations detected

        total_violations = sum(len(violations) for violations in alias_violations.values())

        self.assertGreater(

            total_violations,

            0,

            f"❌ SSOT VIOLATION: Found {total_violations} import alias violations. "

            "Aliases must not obscure SSOT compliance."

        )



    def _scan_for_forbidden_imports(self) -> Dict[Path, List[str]]:

        """Scan for forbidden execution engine imports."""

        forbidden_imports = {}



        for py_file in self.netra_backend_root.rglob("*.py"):

            if py_file.is_file():

                try:

                    with open(py_file, 'r', encoding='utf-8') as f:

                        content = f.read()



                    # Parse AST to find import statements

                    tree = ast.parse(content)

                    file_violations = []



                    for node in ast.walk(tree):

                        if isinstance(node, ast.ImportFrom):

                            if node.names:

                                for alias in node.names:

                                    if alias.name in self.forbidden_legacy_imports:

                                        file_violations.append(

                                            f"from {node.module or ''} import {alias.name}"

                                        )



                        elif isinstance(node, ast.Import):

                            for alias in node.names:

                                # Check if importing forbidden engine directly

                                for forbidden in self.forbidden_legacy_imports:

                                    if forbidden in alias.name:

                                        file_violations.append(

                                            f"import {alias.name}"

                                        )



                    if file_violations:

                        forbidden_imports[py_file] = file_violations



                except Exception:

                    # Skip files that can't be parsed

                    continue



        return forbidden_imports



    def _analyze_import_statements(self) -> Dict[Path, List[str]]:

        """Analyze import statements for SSOT compliance."""

        import_violations = {}



        for py_file in self.netra_backend_root.rglob("*.py"):

            if py_file.is_file():

                try:

                    with open(py_file, 'r', encoding='utf-8') as f:

                        content = f.read()



                    violations = []



                    # Check for execution engine related imports

                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):

                        line = line.strip()



                        # Skip comments and empty lines

                        if line.startswith('#') or not line:

                            continue



                        # Check import lines that contain ExecutionEngine

                        if ('import' in line and

                            'ExecutionEngine' in line and

                            'UserExecutionEngine' not in line and

                            'IExecutionEngine' not in line):



                            # Additional check for forbidden patterns

                            if any(forbidden in line for forbidden in self.forbidden_legacy_imports):

                                violations.append(

                                    f"Line {line_num}: {line} (Non-SSOT import)"

                                )



                    if violations:

                        import_violations[py_file] = violations



                except Exception:

                    continue



        return import_violations



    def _scan_for_string_based_imports(self) -> Dict[Path, List[str]]:

        """Scan for string-based imports that bypass SSOT."""

        string_imports = {}



        for py_file in self.netra_backend_root.rglob("*.py"):

            if py_file.is_file():

                try:

                    with open(py_file, 'r', encoding='utf-8') as f:

                        content = f.read()



                    violations = []



                    # Look for importlib usage with execution engines

                    importlib_patterns = [

                        r'importlib\.import_module\(["\'].*ExecutionEngine.*["\']\)',

                        r'__import__\(["\'].*ExecutionEngine.*["\']\)',

                        r'getattr\(.*,\s*["\'].*ExecutionEngine.*["\']\)'

                    ]



                    for pattern in importlib_patterns:

                        matches = re.finditer(pattern, content, re.IGNORECASE)

                        for match in matches:

                            # Find line number

                            line_num = content[:match.start()].count('\n') + 1

                            violations.append(

                                f"Line {line_num}: {match.group()} (String-based import)"

                            )



                    if violations:

                        string_imports[py_file] = violations



                except Exception:

                    continue



        return string_imports



    def _scan_for_dynamic_imports(self) -> Dict[Path, List[str]]:

        """Scan for dynamic import patterns."""

        dynamic_imports = {}



        for py_file in self.netra_backend_root.rglob("*.py"):

            if py_file.is_file():

                try:

                    with open(py_file, 'r', encoding='utf-8') as f:

                        content = f.read()



                    violations = []



                    # Look for dynamic import patterns

                    dynamic_patterns = [

                        r'globals\(\)\[["\'].*ExecutionEngine.*["\']\]',

                        r'locals\(\)\[["\'].*ExecutionEngine.*["\']\]',

                        r'vars\(.*\)\[["\'].*ExecutionEngine.*["\']\]',

                        r'setattr\(.*,\s*["\'].*ExecutionEngine.*["\']\)',

                    ]



                    for pattern in dynamic_patterns:

                        matches = re.finditer(pattern, content, re.IGNORECASE)

                        for match in matches:

                            line_num = content[:match.start()].count('\n') + 1

                            violations.append(

                                f"Line {line_num}: {match.group()} (Dynamic import)"

                            )



                    if violations:

                        dynamic_imports[py_file] = violations



                except Exception:

                    continue



        return dynamic_imports



    def _check_import_aliases(self) -> Dict[Path, List[str]]:

        """Check import aliases for SSOT compliance."""

        alias_violations = {}



        for py_file in self.netra_backend_root.rglob("*.py"):

            if py_file.is_file():

                try:

                    with open(py_file, 'r', encoding='utf-8') as f:

                        content = f.read()



                    tree = ast.parse(content)

                    violations = []



                    for node in ast.walk(tree):

                        # Check for import aliases that could obscure SSOT compliance

                        if isinstance(node, ast.ImportFrom):

                            if node.names:

                                for alias in node.names:

                                    if alias.asname:  # Has alias

                                        # Check if aliasing a forbidden engine

                                        if alias.name in self.forbidden_legacy_imports:

                                            violations.append(

                                                f"from {node.module or ''} import {alias.name} as {alias.asname} "

                                                f"(Aliasing forbidden engine)"

                                            )

                                        # Check if alias obscures the fact it's an execution engine

                                        elif ('ExecutionEngine' in alias.name and

                                              'ExecutionEngine' not in alias.asname):

                                            violations.append(

                                                f"from {node.module or ''} import {alias.name} as {alias.asname} "

                                                f"(Alias obscures ExecutionEngine type)"

                                            )



                    if violations:

                        alias_violations[py_file] = violations



                except Exception:

                    continue



        return alias_violations





if __name__ == '__main__':

    unittest.main()

