"""
Issue #1176 Remediation Validation Tests

This module validates that the fixes applied for Issue #1176 (test infrastructure
anti-recursive failure patterns) are working correctly.

Key validations:
1. Test runner no longer reports false success when no tests execute
2. Test count extraction correctly parses all pytest outcomes
3. Collection failures are properly detected and reported
4. Exit codes correctly reflect actual test execution status

Business Value: Platform/Internal - Test Infrastructure Reliability
Critical for maintaining confidence in test results and preventing false positives.
"""

import unittest
import subprocess
import sys
import tempfile
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class Issue1176RemediationValidation(SSotBaseTestCase):
    """Validate Issue #1176 remediation fixes."""

    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        self.unified_test_runner = PROJECT_ROOT / "tests" / "unified_test_runner.py"

    def test_phase1_fast_collection_no_longer_reports_false_success(self):
        """
        PHASE 1 FIX VALIDATION: Fast collection mode now fails when no tests execute.

        Before fix: Fast collection with no tests would return exit code 0
        After fix: Fast collection with no tests returns exit code 1
        """
        # Create empty directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Attempt to run tests on empty directory
            cmd = [
                sys.executable,
                str(self.unified_test_runner),
                "--category", "unit",
                "--test-paths", temp_dir,
                "--collect-only",  # Fast collection mode
                "--no-coverage"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60  # Prevent hanging
            )

            # CRITICAL: Must return failure exit code
            self.assertNotEqual(
                result.returncode, 0,
                f"Fast collection with no tests should fail (exit code != 0). "
                f"Got exit code: {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

            # Should contain appropriate failure message
            output = result.stdout + result.stderr
            failure_indicators = [
                "No tests were executed",
                "infrastructure failure",
                "no tests ran"
            ]

            has_failure_message = any(indicator in output for indicator in failure_indicators)
            self.assertTrue(
                has_failure_message,
                f"Should contain failure message. Output: {output[:500]}..."
            )

    def test_test_count_extraction_comprehensive_parsing(self):
        """Validate that test count extraction handles all pytest output patterns."""
        try:
            # Import the unified test runner
            sys.path.insert(0, str(PROJECT_ROOT / "tests"))
            from unified_test_runner import UnifiedTestRunner

            runner = UnifiedTestRunner()

            # Test cases covering various pytest output scenarios
            test_scenarios = [
                {
                    "name": "standard_pass_fail",
                    "output": "======= 5 passed, 2 failed, 1 skipped in 3.14s =======",
                    "expected_total": 8,
                    "expected_passed": 5,
                    "expected_failed": 2,
                    "expected_skipped": 1
                },
                {
                    "name": "all_passed",
                    "output": "======= 10 passed in 2.5s =======",
                    "expected_total": 10,
                    "expected_passed": 10,
                    "expected_failed": 0
                },
                {
                    "name": "with_errors",
                    "output": "======= 2 failed, 1 error in 1.2s =======",
                    "expected_total": 3,
                    "expected_failed": 2,
                    "expected_error": 1
                },
                {
                    "name": "xfail_xpass",
                    "output": "======= 1 passed, 1 xfailed, 1 xpassed in 0.8s =======",
                    "expected_total": 3,
                    "expected_passed": 1,
                    "expected_xfailed": 1,
                    "expected_xpassed": 1
                },
                {
                    "name": "collection_only_no_execution",
                    "output": "collected 5 items\n==== no tests ran ====",
                    "expected_total": 0,  # No tests actually executed
                    "expected_passed": 0
                },
                {
                    "name": "empty_output",
                    "output": "",
                    "expected_total": 0,
                    "expected_passed": 0
                }
            ]

            for scenario in test_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    result_dict = {"output": scenario["output"]}
                    counts = runner._extract_test_counts_from_result(result_dict)

                    # Validate total count
                    self.assertEqual(
                        counts["total"], scenario["expected_total"],
                        f"Total count mismatch for scenario '{scenario['name']}'. "
                        f"Expected: {scenario['expected_total']}, Got: {counts['total']}"
                    )

                    # Validate specific counts if expected
                    for count_type in ["passed", "failed", "skipped", "error", "xfailed", "xpassed"]:
                        expected_key = f"expected_{count_type}"
                        if expected_key in scenario:
                            self.assertEqual(
                                counts[count_type], scenario[expected_key],
                                f"{count_type} count mismatch for scenario '{scenario['name']}'. "
                                f"Expected: {scenario[expected_key]}, Got: {counts[count_type]}"
                            )

        except ImportError as e:
            self.skipTest(f"Could not import unified test runner: {e}")

    def test_collection_failure_detection(self):
        """Validate that collection failures are properly detected."""
        try:
            from unified_test_runner import UnifiedTestRunner

            runner = UnifiedTestRunner()

            # Test scenarios for collection failure detection
            failure_scenarios = [
                {
                    "name": "import_error",
                    "stdout": "ImportError: No module named 'nonexistent_module'",
                    "stderr": "ImportError: No module named 'nonexistent_module'",
                    "should_fail": True
                },
                {
                    "name": "module_not_found",
                    "stdout": "ModuleNotFoundError: No module named 'missing'",
                    "stderr": "ModuleNotFoundError: No module named 'missing'",
                    "should_fail": True
                },
                {
                    "name": "collection_failed",
                    "stdout": "COLLECTION ERROR: collection failed",
                    "stderr": "",
                    "should_fail": True
                },
                {
                    "name": "syntax_error",
                    "stdout": "SyntaxError: invalid syntax",
                    "stderr": "",
                    "should_fail": True
                },
                {
                    "name": "legitimate_success",
                    "stdout": "======= 5 passed in 2.1s =======",
                    "stderr": "",
                    "should_fail": False
                }
            ]

            for scenario in failure_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Test validation method
                    result = runner._validate_test_execution_success(
                        initial_success=True,  # pytest reported success
                        stdout=scenario["stdout"],
                        stderr=scenario["stderr"],
                        service="test_service",
                        category_name="test_category"
                    )

                    if scenario["should_fail"]:
                        self.assertFalse(
                            result,
                            f"Scenario '{scenario['name']}' should be detected as failure"
                        )
                    else:
                        self.assertTrue(
                            result,
                            f"Scenario '{scenario['name']}' should be validated as success"
                        )

        except ImportError as e:
            self.skipTest(f"Could not import unified test runner: {e}")

    def test_anti_recursive_pattern_prevention(self):
        """
        Validate that anti-recursive patterns are prevented.

        This test ensures that the test infrastructure cannot report success
        when tests haven't actually been executed.
        """
        # Create a test file that will cause collection issues
        with tempfile.TemporaryDirectory() as temp_dir:
            problematic_test = Path(temp_dir) / "test_collection_issue.py"
            problematic_test.write_text("""
# This file has import issues that prevent test collection
from this_module_does_not_exist import something

def test_that_will_never_run():
    assert True, "This test should never execute due to import error"
""")

            # Run test runner on the problematic directory
            cmd = [
                sys.executable,
                str(self.unified_test_runner),
                "--category", "unit",
                "--test-paths", str(temp_dir),
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )

            # ANTI-RECURSIVE CHECK: Must not report success when collection fails
            self.assertNotEqual(
                result.returncode, 0,
                f"Test runner must fail when collection has import errors. "
                f"Exit code: {result.returncode}\n"
                f"This would be a critical anti-recursive failure if exit code is 0."
            )

            # Check that error is properly reported
            output = result.stdout + result.stderr
            error_indicators = [
                "ImportError",
                "ModuleNotFoundError",
                "Collection issue detected",
                "import failures"
            ]

            has_error_reporting = any(indicator in output for indicator in error_indicators)
            self.assertTrue(
                has_error_reporting,
                f"Should report collection error details. Output: {output[:500]}..."
            )

    def test_legitimate_test_execution_passes(self):
        """Validate that legitimate test execution still passes correctly."""
        # Create a simple passing test
        with tempfile.TemporaryDirectory() as temp_dir:
            simple_test = Path(temp_dir) / "test_simple_pass.py"
            simple_test.write_text("""
def test_simple_assertion():
    assert 1 + 1 == 2, "Basic math should work"

def test_another_simple():
    assert "hello".upper() == "HELLO", "String operations should work"
""")

            # Run test runner on the simple test
            cmd = [
                sys.executable,
                str(self.unified_test_runner),
                "--category", "unit",
                "--test-paths", str(temp_dir),
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Should succeed when tests actually pass
            self.assertEqual(
                result.returncode, 0,
                f"Legitimate passing tests should succeed. "
                f"Exit code: {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

            # Should show test execution results
            output = result.stdout + result.stderr
            success_indicators = [
                "passed",
                "test session starts"
            ]

            has_success_indicators = any(indicator in output for indicator in success_indicators)
            self.assertTrue(
                has_success_indicators,
                f"Should show test execution indicators. Output: {output[:500]}..."
            )


if __name__ == "__main__":
    unittest.main()