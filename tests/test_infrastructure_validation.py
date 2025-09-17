"""
Test Infrastructure Validation Suite

This module contains tests that validate the test infrastructure itself works correctly.
Created as part of Issue #1176 remediation to prevent test runner false successes.

Business Value: Platform/Internal - Test Infrastructure Reliability
Ensures test infrastructure correctly reports failures and successes.
"""

import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

# Setup path to ensure imports work
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestInfrastructureValidation(SSotBaseTestCase):
    """Validate that test infrastructure correctly handles various scenarios."""

    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        self.test_runner_path = PROJECT_ROOT / "tests" / "unified_test_runner.py"

    def test_runner_reports_failure_when_no_tests_found(self):
        """Test that the runner correctly fails when no tests are found."""
        # Create a temporary directory with no test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run the test runner on the empty directory
            cmd = [
                sys.executable,
                str(self.test_runner_path),
                "--category", "unit",
                "--test-paths", temp_dir,
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )

            # Should return non-zero exit code
            self.assertNotEqual(result.returncode, 0,
                              "Test runner should fail when no tests found")

            # Should contain failure message
            output = result.stdout + result.stderr
            self.assertIn("No tests were executed", output,
                         "Should report that no tests were executed")

    def test_runner_reports_failure_on_collection_errors(self):
        """Test that the runner correctly fails when test collection fails."""
        # Create a temporary test file with import errors
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_test_file = Path(temp_dir) / "test_bad_import.py"
            bad_test_file.write_text("""
import nonexistent_module  # This will cause ImportError

def test_dummy():
    assert True
""")

            cmd = [
                sys.executable,
                str(self.test_runner_path),
                "--category", "unit",
                "--test-paths", temp_dir,
                "--no-coverage",
                "--fast-fail"
            ]

            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )

            # Should return non-zero exit code
            self.assertNotEqual(result.returncode, 0,
                              "Test runner should fail on collection errors")

            # Should contain import error information
            output = result.stdout + result.stderr
            self.assertIn("ImportError", output,
                         "Should report import error")

    def test_count_extraction_handles_all_pytest_outcomes(self):
        """Test that test count extraction handles all pytest outcomes."""
        # Import the test runner to access its methods
        sys.path.insert(0, str(PROJECT_ROOT / "tests"))

        try:
            from unified_test_runner import UnifiedTestRunner

            runner = UnifiedTestRunner()

            # Test various pytest output formats
            test_cases = [
                {
                    "output": "5 passed, 2 failed, 1 skipped in 2.3s",
                    "expected": {"total": 8, "passed": 5, "failed": 2, "skipped": 1}
                },
                {
                    "output": "3 passed in 1.2s",
                    "expected": {"total": 3, "passed": 3, "failed": 0, "skipped": 0}
                },
                {
                    "output": "2 failed, 1 error in 0.5s",
                    "expected": {"total": 3, "passed": 0, "failed": 2, "error": 1}
                },
                {
                    "output": "1 xfailed, 2 xpassed in 1.0s",
                    "expected": {"total": 3, "passed": 0, "failed": 0, "xfailed": 1, "xpassed": 2}
                },
                {
                    "output": "collected 5 items\n\n==== no tests ran ====",
                    "expected": {"total": 0}  # Collection without execution should show 0
                }
            ]

            for case in test_cases:
                result = {"output": case["output"]}
                counts = runner._extract_test_counts_from_result(result)

                for key, expected_value in case["expected"].items():
                    self.assertEqual(counts[key], expected_value,
                                   f"Failed for output: {case['output']}, key: {key}")

        except ImportError as e:
            self.skipTest(f"Could not import test runner: {e}")

    def test_validation_detects_false_success(self):
        """Test that validation correctly detects false success scenarios."""
        try:
            from unified_test_runner import UnifiedTestRunner

            runner = UnifiedTestRunner()

            # Test case: pytest reports success but no tests actually ran
            test_cases = [
                {
                    "initial_success": True,
                    "stdout": "collected 0 items\n\n==== no tests ran ====",
                    "stderr": "",
                    "should_pass": False,
                    "reason": "No tests executed should fail validation"
                },
                {
                    "initial_success": True,
                    "stdout": "ImportError: No module named 'nonexistent'",
                    "stderr": "ImportError: No module named 'nonexistent'",
                    "should_pass": False,
                    "reason": "Import errors should fail validation"
                },
                {
                    "initial_success": True,
                    "stdout": "3 passed in 1.2s",
                    "stderr": "",
                    "should_pass": True,
                    "reason": "Legitimate success should pass validation"
                }
            ]

            for case in test_cases:
                result = runner._validate_test_execution_success(
                    case["initial_success"],
                    case["stdout"],
                    case["stderr"],
                    "test_service",
                    "test_category"
                )

                if case["should_pass"]:
                    self.assertTrue(result, case["reason"])
                else:
                    self.assertFalse(result, case["reason"])

        except ImportError as e:
            self.skipTest(f"Could not import test runner: {e}")

    def test_base_test_case_environment_isolation(self):
        """Test that base test case properly isolates environment."""
        # Test that environment is properly setup
        self.assertIsNotNone(self.env, "Environment should be initialized")

        # Test that we can set and get environment variables
        test_key = "TEST_INFRASTRUCTURE_VALIDATION"
        test_value = "test_value_123"

        self.env.set(test_key, test_value, "test_validation")
        retrieved_value = self.env.get(test_key)

        self.assertEqual(retrieved_value, test_value,
                        "Environment should preserve set values")

    def test_base_test_case_test_context(self):
        """Test that base test case provides proper test context."""
        # Test that test context is initialized
        self.assertIsNotNone(self.test_context, "Test context should be initialized")
        self.assertIsNotNone(self.test_context.test_id, "Test ID should be set")
        self.assertIsNotNone(self.test_context.user_id, "User ID should be set")
        self.assertIsNotNone(self.test_context.session_id, "Session ID should be set")

    def test_async_test_compatibility(self):
        """Test that async test compatibility works correctly."""
        # This is run on sync test case, but we test that the imports work
        try:
            from test_framework.ssot.base_test_case import SSotAsyncTestCase

            # Test that the class can be instantiated
            async_test = SSotAsyncTestCase()
            self.assertIsNotNone(async_test, "Async test case should be instantiable")

        except ImportError as e:
            self.skipTest(f"Could not import async test case: {e}")


if __name__ == "__main__":
    unittest.main()