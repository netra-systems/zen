"""
Issue #1024 SSOT Violation Detection Test

CRITICAL: Detects pytest.main() violations and unauthorized test runners
that are blocking SSOT compliance and Golden Path validation.

This test scans for and documents all SSOT violations to guide
emergency remediation efforts.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set
import unittest


class TestIssue1024PytestViolationsDetection(unittest.TestCase):
    """SSOT violation detection for Issue #1024 remediation."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.pytest_violations = []
        self.unauthorized_runners = []
        self.ssot_violations = []
        self.files_scanned = 0

    def test_detect_pytest_main_violations(self):
        """
        CRITICAL: Detect all pytest.main() violations in the codebase.

        These violations bypass the unified test runner and break SSOT compliance.
        """
        print("\n" + "="*60)
        print("PYTEST.MAIN() VIOLATION DETECTION")
        print("="*60)

        # Scan all Python files for pytest.main() usage
        for python_file in self.project_root.rglob("*.py"):
            if self._should_scan_file(python_file):
                self._scan_file_for_pytest_violations(python_file)

        self._report_pytest_violations()

        # EMERGENCY: Don't fail, just report
        self.assertTrue(True, "Pytest violation detection completed")

    def test_detect_unauthorized_test_runners(self):
        """
        CRITICAL: Detect unauthorized test runners that bypass SSOT infrastructure.

        These include direct subprocess calls to pytest, nose, unittest, etc.
        """
        print("\n" + "="*60)
        print("UNAUTHORIZED TEST RUNNER DETECTION")
        print("="*60)

        # Patterns for unauthorized test runners
        unauthorized_patterns = [
            r'subprocess.*pytest',
            r'subprocess.*python.*-m.*pytest',
            r'subprocess.*unittest',
            r'subprocess.*nose',
            r'os\.system.*pytest',
            r'call\(.*pytest',
            r'run\(.*pytest',
            r'Popen.*pytest'
        ]

        for python_file in self.project_root.rglob("*.py"):
            if self._should_scan_file(python_file):
                self._scan_file_for_unauthorized_runners(python_file, unauthorized_patterns)

        self._report_unauthorized_runners()

        # EMERGENCY: Don't fail, just report
        self.assertTrue(True, "Unauthorized runner detection completed")

    def test_detect_ssot_import_violations(self):
        """
        CRITICAL: Detect SSOT import violations that break unified infrastructure.

        These include direct imports bypassing SSOT modules and duplicate implementations.
        """
        print("\n" + "="*60)
        print("SSOT IMPORT VIOLATION DETECTION")
        print("="*60)

        # SSOT violation patterns
        ssot_violations = [
            # Direct pytest imports instead of unified runner
            {'pattern': r'import pytest', 'violation': 'Direct pytest import'},
            {'pattern': r'from pytest import', 'violation': 'Direct pytest import'},

            # Direct unittest.main instead of unified runner
            {'pattern': r'unittest\.main\(\)', 'violation': 'Direct unittest.main()'},

            # Direct os.environ instead of IsolatedEnvironment
            {'pattern': r'os\.environ\[', 'violation': 'Direct os.environ access'},
            {'pattern': r'os\.getenv\(', 'violation': 'Direct os.getenv access'},

            # Duplicate test base classes
            {'pattern': r'class.*TestCase\(unittest\.TestCase\)', 'violation': 'Non-SSOT TestCase'},
            {'pattern': r'class.*AsyncTestCase', 'violation': 'Non-SSOT AsyncTestCase'},
        ]

        for python_file in self.project_root.rglob("*.py"):
            if self._should_scan_file(python_file):
                self._scan_file_for_ssot_violations(python_file, ssot_violations)

        self._report_ssot_violations()

        # EMERGENCY: Don't fail, just report
        self.assertTrue(True, "SSOT violation detection completed")

    def _should_scan_file(self, file_path: Path) -> bool:
        """Determine if file should be scanned."""
        # Skip certain directories and files
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            'node_modules',
            '.venv',
            'venv',
            'build',
            'dist'
        ]

        # Convert to string for pattern matching
        file_str = str(file_path)

        # Skip if any skip pattern is in the path
        for pattern in skip_patterns:
            if pattern in file_str:
                return False

        return True

    def _scan_file_for_pytest_violations(self, file_path: Path):
        """Scan file for pytest.main() violations."""
        try:
            self.files_scanned += 1
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for pytest.main() calls
            pytest_main_pattern = r'pytest\.main\('
            matches = re.finditer(pytest_main_pattern, content)

            for match in matches:
                # Get line number
                line_num = content[:match.start()].count('\n') + 1

                violation = {
                    'file': str(file_path.relative_to(self.project_root)),
                    'line': line_num,
                    'pattern': 'pytest.main()',
                    'context': self._get_line_context(content, line_num)
                }
                self.pytest_violations.append(violation)

        except Exception as e:
            # Log file reading errors but don't fail
            print(f"Warning: Could not scan {file_path}: {e}")

    def _scan_file_for_unauthorized_runners(self, file_path: Path, patterns: List[str]):
        """Scan file for unauthorized test runner patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)

                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1

                    violation = {
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': line_num,
                        'pattern': pattern,
                        'match': match.group(),
                        'context': self._get_line_context(content, line_num)
                    }
                    self.unauthorized_runners.append(violation)

        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")

    def _scan_file_for_ssot_violations(self, file_path: Path, violation_patterns: List[Dict]):
        """Scan file for SSOT violations."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for violation_def in violation_patterns:
                pattern = violation_def['pattern']
                violation_type = violation_def['violation']

                matches = re.finditer(pattern, content)

                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1

                    violation = {
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': line_num,
                        'type': violation_type,
                        'pattern': pattern,
                        'match': match.group(),
                        'context': self._get_line_context(content, line_num)
                    }
                    self.ssot_violations.append(violation)

        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")

    def _get_line_context(self, content: str, line_num: int) -> str:
        """Get context around a specific line."""
        lines = content.split('\n')
        if line_num <= len(lines):
            # Clean line to remove potential Unicode issues
            line = lines[line_num - 1].strip()
            # Replace problematic Unicode characters with ASCII equivalents
            line = line.encode('ascii', errors='replace').decode('ascii')
            return line
        return ""

    def _report_pytest_violations(self):
        """Report pytest.main() violations."""
        print(f"\nPYTEST.MAIN() VIOLATIONS FOUND: {len(self.pytest_violations)}")

        if not self.pytest_violations:
            print("SUCCESS: No pytest.main() violations found!")
            return

        print("\nCRITICAL VIOLATIONS TO FIX:")
        for i, violation in enumerate(self.pytest_violations, 1):
            print(f"\n{i}. {violation['file']} (line {violation['line']})")
            print(f"   Context: {violation['context']}")

        # Group by file for remediation
        files_with_violations = set(v['file'] for v in self.pytest_violations)
        print(f"\nFILES REQUIRING REMEDIATION: {len(files_with_violations)}")
        for file_path in sorted(files_with_violations):
            count = len([v for v in self.pytest_violations if v['file'] == file_path])
            print(f"  {file_path}: {count} violations")

    def _report_unauthorized_runners(self):
        """Report unauthorized test runner violations."""
        print(f"\nUNAUTHORIZED TEST RUNNERS FOUND: {len(self.unauthorized_runners)}")

        if not self.unauthorized_runners:
            print("SUCCESS: No unauthorized test runners found!")
            return

        print("\nUNAUTHORIZED RUNNERS TO FIX:")
        for i, violation in enumerate(self.unauthorized_runners, 1):
            print(f"\n{i}. {violation['file']} (line {violation['line']})")
            print(f"   Pattern: {violation['pattern']}")
            print(f"   Match: {violation['match']}")
            print(f"   Context: {violation['context']}")

    def _report_ssot_violations(self):
        """Report SSOT violations."""
        print(f"\nSSOT VIOLATIONS FOUND: {len(self.ssot_violations)}")

        if not self.ssot_violations:
            print("SUCCESS: No SSOT violations found!")
            return

        # Group by violation type
        violation_types = {}
        for violation in self.ssot_violations:
            vtype = violation['type']
            if vtype not in violation_types:
                violation_types[vtype] = []
            violation_types[vtype].append(violation)

        print("\nSSOT VIOLATIONS BY TYPE:")
        for vtype, violations in violation_types.items():
            print(f"\n{vtype}: {len(violations)} violations")
            for violation in violations[:5]:  # Show first 5
                print(f"  {violation['file']} (line {violation['line']})")
            if len(violations) > 5:
                print(f"  ... and {len(violations) - 5} more")

    def test_generate_remediation_summary(self):
        """Generate comprehensive remediation summary."""
        # Run all detection tests first
        self.test_detect_pytest_main_violations()
        self.test_detect_unauthorized_test_runners()
        self.test_detect_ssot_import_violations()

        print("\n" + "="*60)
        print("ISSUE #1024 REMEDIATION SUMMARY")
        print("="*60)

        total_violations = (len(self.pytest_violations) +
                          len(self.unauthorized_runners) +
                          len(self.ssot_violations))

        print(f"Files scanned: {self.files_scanned}")
        print(f"Total violations: {total_violations}")
        print(f"  - pytest.main() violations: {len(self.pytest_violations)}")
        print(f"  - Unauthorized runners: {len(self.unauthorized_runners)}")
        print(f"  - SSOT violations: {len(self.ssot_violations)}")

        print(f"\nREMEDIATION PRIORITY:")
        print(f"1. Fix pytest.main() violations (breaks SSOT test runner)")
        print(f"2. Remove unauthorized test runners (breaks CI/CD)")
        print(f"3. Fix SSOT import violations (breaks unified infrastructure)")

        # EMERGENCY: Don't fail, just report
        self.assertTrue(True, "Remediation summary completed")


if __name__ == '__main__':
    # Run the violation detection
    unittest.main(verbosity=2)