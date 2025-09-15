#!/usr/bin/env python3
"""
Unit tests to expose remaining SSOT environment access violations.
These tests are designed to FAIL initially to demonstrate the violations.

Issue #711: Execute test plan to detect remaining SSOT environment access violations
Target: secret_manager_core.py line 47 and other direct os.environ assignments
"""

import os
import sys
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import pytest

# Import paths for test framework
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
except ImportError:
    # Fallback to basic unittest if SSOT framework unavailable
    import unittest
    SSotAsyncTestCase = unittest.TestCase


class TestSSotEnvironmentAccessViolations(SSotAsyncTestCase):
    """Test suite to expose remaining SSOT environment access violations."""

    def setup_method(self):
        """Set up test environment (pytest style)."""
        self.original_environ = os.environ.copy()
        self.detected_violations = []

    def teardown_method(self):
        """Clean up test environment (pytest style)."""
        if hasattr(self, 'original_environ') and self.original_environ is not None:
            # Restore original environment
            os.environ.clear()
            os.environ.update(self.original_environ)

    def _mock_os_environ_setitem(self, key: str, value: str) -> None:
        """Mock os.environ.__setitem__ to detect direct assignments."""
        violation = {
            'key': key,
            'value': value,
            'stack_trace': self._get_caller_info()
        }
        self.detected_violations.append(violation)
        # Still perform the actual assignment for functionality
        self.original_environ[key] = value

    def _get_caller_info(self) -> str:
        """Get caller information for violation tracking."""
        import traceback
        stack = traceback.extract_stack()
        # Find the first non-test frame
        for frame in reversed(stack[:-1]):
            if not frame.filename.endswith('test_ssot_environment_access_violations.py'):
                return f"{frame.filename}:{frame.lineno} in {frame.name}"
        return "Unknown caller"

    def test_secret_manager_core_direct_environ_assignment(self):
        """
        Test to expose direct os.environ assignment in secret_manager_core.py line 47.
        This test should FAIL initially to demonstrate the violation.
        """
        # Mock os.environ.__setitem__ to detect direct assignments
        with patch.object(os.environ, '__setitem__', side_effect=self._mock_os_environ_setitem):
            try:
                # Import and use the EnhancedSecretManager
                from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
                from netra_backend.app.schemas.config_types import EnvironmentType

                # Create secret manager instance
                secret_manager = EnhancedSecretManager(EnvironmentType.TESTING)

                # Trigger the violation by calling set_secret
                test_secret_name = "TEST_SECRET_VIOLATION"
                test_secret_value = "violation_test_value"

                # This should trigger the direct os.environ assignment on line 47
                secret_manager.set_secret(test_secret_name, test_secret_value)

                # Check if violation was detected
                violations_found = [v for v in self.detected_violations if v['key'] == test_secret_name]

                # This assertion should FAIL initially - the violation exists
                self.assertEqual(len(violations_found), 0,
                    f"SSOT VIOLATION DETECTED: secret_manager_core.py directly assigns os.environ['{test_secret_name}'] = '{test_secret_value}'. "
                    f"Violation details: {violations_found[0] if violations_found else 'None'}")

            except ImportError as e:
                self.fail(f"Could not import EnhancedSecretManager: {e}")

    def test_broad_environ_assignment_detection(self):
        """
        Broader test to detect any direct os.environ assignments in the codebase.
        This test scans for the pattern and should FAIL if violations exist.
        """
        # Mock os.environ.__setitem__ to catch all direct assignments
        with patch.object(os.environ, '__setitem__', side_effect=self._mock_os_environ_setitem):
            try:
                # Test various modules that might have violations
                test_modules = [
                    'netra_backend.app.core.secret_manager_core',
                    'netra_backend.app.core.secret_manager_factory',
                    'netra_backend.app.core.secret_manager_loading',
                ]

                for module_name in test_modules:
                    try:
                        module = __import__(module_name, fromlist=[''])

                        # Try to trigger any environment assignments in the module
                        if hasattr(module, 'EnhancedSecretManager'):
                            from netra_backend.app.schemas.config_types import EnvironmentType
                            instance = module.EnhancedSecretManager(EnvironmentType.TESTING)
                            if hasattr(instance, 'set_secret'):
                                instance.set_secret(f"TEST_VIOLATION_{module_name.split('.')[-1]}", "test_value")

                    except (ImportError, AttributeError) as e:
                        # Skip modules that can't be imported or don't have expected classes
                        continue

                # Check for any violations detected
                if self.detected_violations:
                    violation_summary = "\n".join([
                        f"  - {v['stack_trace']}: os.environ['{v['key']}'] = '{v['value']}'"
                        for v in self.detected_violations
                    ])

                    # This assertion should FAIL initially if violations exist
                    self.fail(f"SSOT VIOLATIONS DETECTED: Direct os.environ assignments found:\n{violation_summary}\n"
                             f"These should be replaced with IsolatedEnvironment.set() calls.")

            except Exception as e:
                self.fail(f"Test execution failed: {e}")

    def test_remaining_violations_from_grep_scan(self):
        """
        Test based on actual grep scan results to detect remaining violations.
        This validates specific files mentioned in the Issue #711 analysis.
        """
        violation_patterns = []

        # Mock os.environ.__setitem__ to detect direct assignments
        with patch.object(os.environ, '__setitem__', side_effect=self._mock_os_environ_setitem):
            try:
                # Test the specific violation: secret_manager_core.py line 47
                from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
                from netra_backend.app.schemas.config_types import EnvironmentType

                secret_manager = EnhancedSecretManager(EnvironmentType.TESTING)
                secret_manager.set_secret("VIOLATION_TEST", "test_value")

                # Check for specific patterns that indicate SSOT violations
                secret_manager_violations = [
                    v for v in self.detected_violations
                    if 'secret_manager_core.py' in v['stack_trace']
                ]

                if secret_manager_violations:
                    violation_patterns.extend(secret_manager_violations)

                # Additional checks for other common violation patterns
                # Test any modules that might be setting environment variables
                test_cases = [
                    ("JWT_SECRET_KEY", "test_jwt_secret"),
                    ("DATABASE_URL", "test_db_url"),
                    ("REDIS_HOST", "test_redis_host"),
                ]

                for key, value in test_cases:
                    # Clear previous violations for this test
                    self.detected_violations.clear()

                    # Try to trigger environment setting in secret manager
                    secret_manager.set_secret(key, value)

                    if self.detected_violations:
                        violation_patterns.extend(self.detected_violations)

                # This assertion should FAIL initially if violations exist
                if violation_patterns:
                    violation_summary = "\n".join([
                        f"  - {v['stack_trace']}: os.environ['{v['key']}'] = '{v['value']}'"
                        for v in violation_patterns
                    ])

                    self.fail(f"SSOT ENVIRONMENT ACCESS VIOLATIONS DETECTED:\n{violation_summary}\n"
                             f"Total violations: {len(violation_patterns)}\n"
                             f"These direct os.environ assignments should be replaced with IsolatedEnvironment.set() calls.")

            except ImportError as e:
                self.fail(f"Could not import required modules: {e}")

    def test_isolated_environment_compliance_check(self):
        """
        Test to verify that IsolatedEnvironment is being used instead of direct os.environ.
        This test should PASS if SSOT patterns are correctly implemented.
        """
        try:
            # Import IsolatedEnvironment
            from dev_launcher.isolated_environment import IsolatedEnvironment

            # Create isolated environment instance
            isolated_env = IsolatedEnvironment()

            # Test setting environment variable through SSOT pattern
            test_key = "SSOT_COMPLIANCE_TEST"
            test_value = "compliance_test_value"

            # This should NOT trigger our violation detector
            with patch.object(os.environ, '__setitem__', side_effect=self._mock_os_environ_setitem):
                isolated_env.set(test_key, test_value, "test_source")

                # Check that the value was set correctly
                retrieved_value = isolated_env.get(test_key)
                self.assertEqual(retrieved_value, test_value)

                # Verify no direct os.environ violations were detected
                direct_violations = [
                    v for v in self.detected_violations
                    if v['key'] == test_key and 'isolated_environment.py' not in v['stack_trace']
                ]

                self.assertEqual(len(direct_violations), 0,
                    f"IsolatedEnvironment should not trigger direct os.environ violations, but detected: {direct_violations}")

        except ImportError as e:
            self.fail(f"Could not import IsolatedEnvironment: {e}")

    def test_fake_test_validation(self):
        """
        Validation test to ensure this test file is properly structured.
        This should always PASS to confirm the test framework is working.
        """
        # This test should always pass to confirm the test framework is working
        self.assertTrue(True, "Test framework validation passed")

        # Verify we can detect violations in our mock
        with patch.object(os.environ, '__setitem__', side_effect=self._mock_os_environ_setitem):
            # Directly assign to os.environ to test our detection mechanism
            os.environ['FAKE_TEST_VALIDATION'] = 'test_value'

            # Verify our violation detection is working
            validation_violations = [v for v in self.detected_violations if v['key'] == 'FAKE_TEST_VALIDATION']
            self.assertEqual(len(validation_violations), 1,
                "Violation detection mechanism should catch direct os.environ assignments")


if __name__ == '__main__':
    import unittest

    # Run the test suite
    print("="*80)
    print("EXECUTING SSOT ENVIRONMENT ACCESS VIOLATION DETECTION TESTS")
    print("="*80)
    print("These tests are designed to FAIL initially to expose SSOT violations.")
    print("SUCCESS means violations were detected and need remediation.")
    print("="*80)

    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestSSotEnvironmentAccessViolations)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)

    print("\n" + "="*80)
    print("TEST EXECUTION SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFAILURES (Expected - these expose SSOT violations):")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'Unknown failure'}")

    if result.errors:
        print("\nERRORS (Unexpected - these need investigation):")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'Unknown error'}")

    print("="*80)

    # Exit with appropriate code
    exit_code = 0 if not result.errors else 1  # Failures are expected, errors are not
    sys.exit(exit_code)
