"""
Issue #1097 SSOT Migration Completion Validation Test

This test validates that all mission-critical files have been migrated
from unittest.TestCase to SSotBaseTestCase patterns.

BUSINESS IMPACT: $500K+ ARR depends on SSOT test infrastructure
compliance for reliable testing and deployment confidence.

SHOULD PASS: When all mission-critical files use SSOT patterns
SHOULD FAIL: When unittest.TestCase patterns are detected
"""

import os
import re
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotMigrationValidationTests(SSotBaseTestCase):
    """Validate SSOT migration completion for mission-critical files."""

    def setup_method(self, method):
        """Set up SSOT migration validation."""
        super().setup_method(method)

        # Files identified for Issue #1097 migration
        self.mission_critical_files = [
            "tests/mission_critical/test_server_message_validation_fixed.py",
            "tests/mission_critical/test_server_message_validator_integration.py",
            "tests/mission_critical/test_user_execution_engine_isolation.py",
            "tests/mission_critical/test_websocket_factory_user_isolation_ssot_compliance.py",
            "auth_service/test_golden_path_integration.py"
        ]

        self.project_root = Path(__file__).parent.parent.parent
        self.violations = []

    def test_mission_critical_files_use_ssot_base_test_case(self):
        """Test that all mission-critical files use SSotBaseTestCase."""
        print("\n" + "="*70)
        print("ISSUE #1097 SSOT MIGRATION VALIDATION")
        print("="*70)

        for file_path in self.mission_critical_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                self.violations.append({
                    'file': file_path,
                    'type': 'missing_file',
                    'details': f"File does not exist: {full_path}"
                })
                continue

            self._validate_file_ssot_compliance(file_path, full_path)

        # Report results
        self._report_validation_results()

        # Assert compliance
        self.assertEqual(
            len(self.violations), 0,
            f"Found {len(self.violations)} SSOT compliance violations in mission-critical files. "
            f"All files must use SSotBaseTestCase for Issue #1097 completion. "
            f"Violations: {[v['file'] for v in self.violations]}"
        )

    def _validate_file_ssot_compliance(self, file_path: str, full_path: Path):
        """Validate a single file for SSOT compliance."""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for SSOT import
            has_ssot_import = self._check_ssot_import(content)

            # Check for unittest.TestCase usage
            has_unittest_testcase = self._check_unittest_testcase_usage(content)

            # Check for SSotBaseTestCase usage
            has_ssot_base_testcase = self._check_ssot_base_testcase_usage(content)

            # Determine compliance status
            is_compliant = has_ssot_import and has_ssot_base_testcase and not has_unittest_testcase

            if not is_compliant:
                violation_details = []
                if not has_ssot_import:
                    violation_details.append("Missing SSOT import")
                if has_unittest_testcase:
                    violation_details.append("Uses unittest.TestCase directly")
                if not has_ssot_base_testcase:
                    violation_details.append("Does not use SSotBaseTestCase")

                self.violations.append({
                    'file': file_path,
                    'type': 'ssot_compliance_violation',
                    'details': "; ".join(violation_details),
                    'has_ssot_import': has_ssot_import,
                    'has_unittest_testcase': has_unittest_testcase,
                    'has_ssot_base_testcase': has_ssot_base_testcase
                })

            # Log status
            status = "✅ COMPLIANT" if is_compliant else "❌ NON-COMPLIANT"
            print(f"{status}: {file_path}")
            if not is_compliant:
                print(f"  Issues: {'; '.join(violation_details)}")

        except Exception as e:
            self.violations.append({
                'file': file_path,
                'type': 'file_read_error',
                'details': f"Error reading file: {str(e)}"
            })
            print(f"❌ ERROR: {file_path} - {str(e)}")

    def _check_ssot_import(self, content: str) -> bool:
        """Check if file imports SSOT base test case."""
        patterns = [
            r'from test_framework\.ssot\.base_test_case import',
            r'from test_framework\.ssot import',
            r'import.*SSotBaseTestCase',
            r'import.*SSotAsyncTestCase'
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _check_unittest_testcase_usage(self, content: str) -> bool:
        """Check if file uses unittest.TestCase directly."""
        patterns = [
            r'class.*\(unittest\.TestCase\)',
            r'class.*\(TestCase\)',
            r'unittest\.TestCase',
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _check_ssot_base_testcase_usage(self, content: str) -> bool:
        """Check if file uses SSotBaseTestCase."""
        patterns = [
            r'class.*\(SSotBaseTestCase\)',
            r'class.*\(SSotAsyncTestCase\)',
            r'SSotBaseTestCase',
            r'SSotAsyncTestCase'
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _report_validation_results(self):
        """Report validation results."""
        total_files = len(self.mission_critical_files)
        compliant_files = total_files - len(self.violations)
        compliance_rate = (compliant_files / total_files) * 100

        print("\n" + "-"*70)
        print("SSOT MIGRATION VALIDATION RESULTS")
        print("-"*70)
        print(f"Total mission-critical files: {total_files}")
        print(f"SSOT compliant files: {compliant_files}")
        print(f"Non-compliant files: {len(self.violations)}")
        print(f"Compliance rate: {compliance_rate:.1f}%")

        if self.violations:
            print("\nVIOLATIONS DETECTED:")
            for i, violation in enumerate(self.violations, 1):
                print(f"  {i}. {violation['file']}")
                print(f"     Type: {violation['type']}")
                print(f"     Details: {violation['details']}")
        else:
            print("\n✅ ALL FILES ARE SSOT COMPLIANT!")

        print("-"*70)

    def test_ssot_import_patterns_detection(self):
        """Test that SSOT import pattern detection works correctly."""
        # Test valid SSOT imports
        valid_imports = [
            "from test_framework.ssot.base_test_case import SSotBaseTestCase",
            "from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase",
            "from test_framework.ssot import base_test_case"
        ]

        for import_line in valid_imports:
            self.assertTrue(
                self._check_ssot_import(import_line),
                f"Should detect SSOT import: {import_line}"
            )

        # Test invalid imports
        invalid_imports = [
            "import unittest",
            "from unittest import TestCase",
            "from test_framework import something_else"
        ]

        for import_line in invalid_imports:
            self.assertFalse(
                self._check_ssot_import(import_line),
                f"Should NOT detect SSOT import: {import_line}"
            )

    def test_unittest_testcase_pattern_detection(self):
        """Test that unittest.TestCase pattern detection works correctly."""
        # Test patterns that should be detected
        unittest_patterns = [
            "class TestSomething(unittest.TestCase):",
            "class MyTest(TestCase):",
            "inherit from unittest.TestCase"
        ]

        for pattern in unittest_patterns:
            self.assertTrue(
                self._check_unittest_testcase_usage(pattern),
                f"Should detect unittest.TestCase usage: {pattern}"
            )

        # Test patterns that should NOT be detected
        non_unittest_patterns = [
            "class TestSomething(SSotBaseTestCase):",
            "class MyTest(SSotAsyncTestCase):",
            "from test_framework.ssot.base_test_case import SSotBaseTestCase"
        ]

        for pattern in non_unittest_patterns:
            self.assertFalse(
                self._check_unittest_testcase_usage(pattern),
                f"Should NOT detect unittest.TestCase usage: {pattern}"
            )


if __name__ == '__main__':
    import unittest
    unittest.main(verbosity=2)