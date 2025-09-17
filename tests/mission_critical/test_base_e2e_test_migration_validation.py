"""
BaseE2ETest to SSotAsyncTestCase Migration Validation Test

CRITICAL MISSION: Track and validate the migration from BaseE2ETest to SSotAsyncTestCase
ensuring SSOT compliance across all E2E test files.

This test will initially FAIL (expected) and will pass as migration progresses.

Purpose:
- Scan codebase for remaining BaseE2ETest imports
- Count files that still need migration
- Validate migrated files follow SSOT patterns
- Detect anti-patterns (direct os.environ usage, etc.)
- Provide actionable feedback on migration progress

Business Value: Ensures test infrastructure follows SSOT patterns for reliability
and maintains the 94.5% SSOT compliance target.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestBaseE2ETestMigrationValidation(SSotAsyncTestCase):
    """Validates BaseE2ETest to SSotAsyncTestCase migration progress."""

    def setUp(self):
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.test_directories = [
            self.project_root / "tests",
            self.project_root / "netra_backend" / "tests",
            self.project_root / "auth_service" / "tests",
            self.project_root / "frontend" / "tests",
            self.project_root / "test_framework" / "tests"
        ]
        
    def test_scan_for_base_e2e_test_imports(self):
        """
        Scan codebase for remaining BaseE2ETest imports.
        
        This test will FAIL initially (expected) and pass as migration progresses.
        """
        base_e2e_imports = self._scan_for_base_e2e_imports()
        
        if base_e2e_imports:
            files_list = "\n".join([f"  - {file}: {imports}" for file, imports in base_e2e_imports.items()])
            self.fail(
                f"MIGRATION REQUIRED: Found {len(base_e2e_imports)} files still importing BaseE2ETest.\n"
                f"Files requiring migration:\n{files_list}\n\n"
                f"ACTION REQUIRED:\n"
                f"1. Replace 'from tests.test_framework.base_test_case import BaseE2ETest' with "
                f"'from test_framework.ssot.base_test_case import SSotAsyncTestCase'\n"
                f"2. Update class inheritance: 'class YourTest(BaseE2ETest)' → 'class YourTest(SSotAsyncTestCase)'\n"
                f"3. Update async test methods to follow SSOT patterns\n"
                f"4. Remove direct os.environ usage if present\n\n"
                f"MIGRATION PROGRESS: {len(base_e2e_imports)} files remaining"
            )
        
        # Test passes when no BaseE2ETest imports remain
        self.assertEqual(len(base_e2e_imports), 0, "All BaseE2ETest imports have been migrated to SSotAsyncTestCase")

    def test_validate_ssot_async_test_case_adoption(self):
        """
        Validate that E2E test files are properly using SSotAsyncTestCase.
        """
        e2e_test_files = self._find_e2e_test_files()
        ssot_compliant_files = self._scan_for_ssot_compliance(e2e_test_files)
        non_compliant_files = e2e_test_files - ssot_compliant_files
        
        if non_compliant_files:
            files_list = "\n".join([f"  - {file}" for file in sorted(non_compliant_files)])
            compliance_percentage = (len(ssot_compliant_files) / len(e2e_test_files)) * 100 if e2e_test_files else 100
            
            self.fail(
                f"SSOT COMPLIANCE VIOLATION: Found {len(non_compliant_files)} E2E test files not using SSotAsyncTestCase.\n"
                f"Non-compliant files:\n{files_list}\n\n"
                f"COMPLIANCE STATUS: {compliance_percentage:.1f}% ({len(ssot_compliant_files)}/{len(e2e_test_files)} files)\n"
                f"TARGET: 100% SSOT compliance required\n\n"
                f"ACTION REQUIRED:\n"
                f"1. Import SSotAsyncTestCase: 'from test_framework.ssot.base_test_case import SSotAsyncTestCase'\n"
                f"2. Update class inheritance to extend SSotAsyncTestCase\n"
                f"3. Use SSOT test utilities and patterns"
            )
        
        # Calculate and report compliance metrics
        total_files = len(e2e_test_files)
        compliant_files = len(ssot_compliant_files)
        compliance_percentage = (compliant_files / total_files) * 100 if total_files > 0 else 100
        
        self.assertEqual(
            len(non_compliant_files), 0,
            f"All E2E test files must use SSotAsyncTestCase. "
            f"Current compliance: {compliance_percentage:.1f}% ({compliant_files}/{total_files})"
        )

    def test_detect_direct_environ_usage_in_tests(self):
        """
        Detect direct os.environ usage in test files (SSOT violation).
        """
        environ_violations = self._scan_for_environ_usage()
        
        if environ_violations:
            violations_list = "\n".join([
                f"  - {file}:{line}: {code.strip()}" 
                for file, line, code in environ_violations
            ])
            
            self.fail(
                f"SSOT VIOLATION: Found {len(environ_violations)} direct os.environ usages in test files.\n"
                f"Violations:\n{violations_list}\n\n"
                f"ACTION REQUIRED:\n"
                f"1. Replace 'import os' + 'os.environ' with 'from dev_launcher.isolated_environment import IsolatedEnvironment'\n"
                f"2. Use 'env = IsolatedEnvironment()' and 'env.get(\"KEY\")' instead of 'os.environ[\"KEY\"]'\n"
                f"3. Follow SSOT environment management patterns\n\n"
                f"SPECIFICATION: See SPEC/unified_environment_management.xml"
            )
        
        self.assertEqual(
            len(environ_violations), 0,
            "Test files must use IsolatedEnvironment instead of direct os.environ access"
        )

    def test_validate_ssot_import_patterns(self):
        """
        Validate that migrated files use proper SSOT import patterns.
        """
        import_violations = self._scan_for_import_violations()
        
        if import_violations:
            violations_list = "\n".join([
                f"  - {file}: {violation}" 
                for file, violation in import_violations.items()
            ])
            
            self.fail(
                f"SSOT IMPORT VIOLATIONS: Found {len(import_violations)} files with incorrect import patterns.\n"
                f"Violations:\n{violations_list}\n\n"
                f"ACTION REQUIRED:\n"
                f"1. Use absolute imports only (no relative imports)\n"
                f"2. Import from SSOT locations: test_framework.ssot.*\n"
                f"3. Follow SSOT import registry patterns\n\n"
                f"REFERENCE: See SSOT_IMPORT_REGISTRY.md"
            )
        
        self.assertEqual(
            len(import_violations), 0,
            "All test files must follow SSOT import patterns"
        )

    def test_migration_progress_metrics(self):
        """
        Report comprehensive migration progress metrics.
        """
        # Gather all metrics
        base_e2e_imports = self._scan_for_base_e2e_imports()
        e2e_test_files = self._find_e2e_test_files()
        ssot_compliant_files = self._scan_for_ssot_compliance(e2e_test_files)
        environ_violations = self._scan_for_environ_usage()
        import_violations = self._scan_for_import_violations()
        
        # Calculate metrics
        total_e2e_files = len(e2e_test_files)
        legacy_imports = len(base_e2e_imports)
        ssot_compliant = len(ssot_compliant_files)
        environ_violating = len(environ_violations)
        import_violating = len(import_violations)
        
        # Calculate compliance percentage
        if total_e2e_files > 0:
            ssot_compliance = (ssot_compliant / total_e2e_files) * 100
            migration_progress = ((total_e2e_files - legacy_imports) / total_e2e_files) * 100
        else:
            ssot_compliance = 100.0
            migration_progress = 100.0
        
        # Create comprehensive report
        report = f"""
BASETEST TO SSOT MIGRATION STATUS REPORT
=========================================

OVERALL PROGRESS: {migration_progress:.1f}%
SSOT COMPLIANCE: {ssot_compliance:.1f}%

DETAILED METRICS:
- Total E2E test files: {total_e2e_files}
- Files with BaseE2ETest imports: {legacy_imports}
- Files using SSotAsyncTestCase: {ssot_compliant}
- Files with os.environ violations: {environ_violating}
- Files with import violations: {import_violating}

MIGRATION TARGETS:
- Legacy imports: {legacy_imports} → 0 (TARGET)
- SSOT compliance: {ssot_compliance:.1f}% → 100% (TARGET)
- Environment violations: {environ_violating} → 0 (TARGET)
- Import violations: {import_violating} → 0 (TARGET)

NEXT ACTIONS:
1. Migrate {legacy_imports} files from BaseE2ETest to SSotAsyncTestCase
2. Fix {environ_violating} environment access violations
3. Resolve {import_violating} import pattern violations
4. Achieve 100% SSOT compliance in E2E test infrastructure
"""
        
        # Test will pass only when migration is complete
        migration_complete = (
            legacy_imports == 0 and
            environ_violating == 0 and
            import_violating == 0 and
            ssot_compliance >= 100.0
        )
        
        if not migration_complete:
            self.fail(f"Migration not complete. Current status:\n{report}")
        
        # Log success when migration is complete
        print(f"✅ MIGRATION COMPLETE: All E2E tests successfully migrated to SSOT patterns.\n{report}")

    # Helper methods
    
    def _scan_for_base_e2e_imports(self) -> Dict[str, List[str]]:
        """Scan for files importing BaseE2ETest."""
        base_e2e_imports = {}
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    imports = []
                    
                    # Check for various BaseE2ETest import patterns
                    patterns = [
                        r'from\s+.*base_test_case\s+import\s+.*BaseE2ETest',
                        r'from\s+tests\.test_framework\.base_test_case\s+import\s+BaseE2ETest',
                        r'import\s+.*BaseE2ETest',
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, content):
                            imports.append(pattern)
                    
                    if imports:
                        base_e2e_imports[str(py_file.relative_to(self.project_root))] = imports
                        
                except (UnicodeDecodeError, IOError):
                    continue
                    
        return base_e2e_imports

    def _find_e2e_test_files(self) -> Set[str]:
        """Find all E2E test files in the codebase."""
        e2e_files = set()
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob("*.py"):
                file_path = str(py_file.relative_to(self.project_root))
                
                # Identify E2E test files by name patterns and content
                if (
                    "e2e" in file_path.lower() or
                    "end_to_end" in file_path.lower() or
                    "integration" in file_path.lower() or
                    file_path.startswith("tests/e2e/") or
                    "test_" in py_file.name
                ):
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        # Check if it's actually a test file
                        if ("class Test" in content or "def test_" in content) and "unittest" not in content:
                            e2e_files.add(file_path)
                    except (UnicodeDecodeError, IOError):
                        continue
                        
        return e2e_files

    def _scan_for_ssot_compliance(self, e2e_files: Set[str]) -> Set[str]:
        """Check which files are using SSotAsyncTestCase."""
        compliant_files = set()
        
        for file_path in e2e_files:
            try:
                full_path = self.project_root / file_path
                content = full_path.read_text(encoding='utf-8')
                
                # Check for SSotAsyncTestCase usage
                ssot_patterns = [
                    r'from\s+test_framework\.ssot\.base_test_case\s+import\s+.*SSotAsyncTestCase',
                    r'class\s+\w+\(.*SSotAsyncTestCase.*\)',
                ]
                
                for pattern in ssot_patterns:
                    if re.search(pattern, content):
                        compliant_files.add(file_path)
                        break
                        
            except (IOError, UnicodeDecodeError):
                continue
                
        return compliant_files

    def _scan_for_environ_usage(self) -> List[Tuple[str, int, str]]:
        """Scan for direct os.environ usage in test files."""
        violations = []
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        # Check for os.environ usage patterns
                        if re.search(r'os\.environ', line) and 'IsolatedEnvironment' not in line:
                            file_path = str(py_file.relative_to(self.project_root))
                            violations.append((file_path, line_num, line))
                            
                except (UnicodeDecodeError, IOError):
                    continue
                    
        return violations

    def _scan_for_import_violations(self) -> Dict[str, str]:
        """Scan for import pattern violations in test files."""
        violations = {}
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    file_path = str(py_file.relative_to(self.project_root))
                    
                    # Check for relative imports (anti-pattern)
                    if re.search(r'from\s+\.', content):
                        violations[file_path] = "Uses relative imports (should be absolute)"
                    
                    # Check for non-SSOT test framework imports
                    elif re.search(r'from\s+tests\.test_framework', content) and 'BaseE2ETest' in content:
                        violations[file_path] = "Uses legacy test framework imports"
                    
                    # Check for direct unittest imports in E2E tests
                    elif 'e2e' in file_path and re.search(r'import\s+unittest', content):
                        violations[file_path] = "E2E test should use SSOT test framework, not unittest"
                        
                except (UnicodeDecodeError, IOError):
                    continue
                    
        return violations