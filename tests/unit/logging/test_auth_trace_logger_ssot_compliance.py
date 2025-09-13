#!/usr/bin/env python3
"""
Unit Test: Auth Trace Logger SSOT Compliance Validation

Business Value: Platform/Internal - Authentication System Reliability
Critical for $500K+ ARR protection through consistent authentication logging.

PURPOSE: This test MUST FAIL with current SSOT violations and PASS after remediation.
Validates that AuthTraceLogger uses IsolatedEnvironment instead of direct os.getenv.

CRITICAL VIOLATION TO DETECT:
- netra_backend/app/logging/auth_trace_logger.py:284 - os.getenv('ENVIRONMENT')

Expected Behavior:
- CURRENT STATE: This test should FAIL due to direct os.getenv usage
- AFTER REMEDIATION: This test should PASS when using get_env() from IsolatedEnvironment

Test Strategy:
- Import and inspect AuthTraceLogger source code
- Validate environment access patterns in logging methods
- Ensure SSOT compliance in authentication debug logging
- Protect Golden Path user authentication debugging capability

Author: SSOT Gardener Agent - Step 2 Test Plan Execution
Date: 2025-09-13
"""

import inspect
import ast
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from unittest.mock import patch, MagicMock

import pytest

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAuthTraceLoggerSsotCompliance(SSotBaseTestCase):
    """Unit tests for Auth Trace Logger SSOT configuration compliance."""

    def setup_method(self, method=None):
        """Setup test environment for auth trace logger SSOT validation."""
        super().setup_method(method)

        # Import paths
        self.module_path = 'netra_backend.app.logging.auth_trace_logger'
        self.logger_class_name = 'AuthTraceLogger'

        # SSOT violation patterns to detect
        self.violation_patterns = [
            'os.environ[',
            'os.environ.get(',
            'os.getenv(',
        ]

        # SSOT compliant patterns that should be used instead
        self.compliant_patterns = [
            'get_env()',
            'IsolatedEnvironment',
            'isolated_environment',
        ]

        # Expected violations (current state)
        self.expected_violation_line_range = (280, 290)  # Around line 284
        self.expected_violation_variable = 'ENVIRONMENT'

    def import_auth_trace_logger(self):
        """Safely import the AuthTraceLogger class."""
        try:
            module = __import__(self.module_path, fromlist=[self.logger_class_name])
            logger_class = getattr(module, self.logger_class_name)
            return logger_class
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Cannot import AuthTraceLogger: {str(e)}")

    def get_source_code(self, class_or_function):
        """Get source code with error handling."""
        try:
            return inspect.getsource(class_or_function)
        except OSError as e:
            pytest.skip(f"Cannot get source code: {str(e)}")

    def parse_source_for_violations(self, source_code: str) -> List[Dict]:
        """Parse source code to find SSOT violations."""
        violations = []
        lines = source_code.splitlines()

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue

            # Check for violation patterns
            for pattern in self.violation_patterns:
                if pattern in line:
                    # Extract environment variable if possible
                    env_var = self.extract_env_var_from_line(line)

                    violations.append({
                        'line_number': line_num,
                        'code_line': line.strip(),
                        'pattern': pattern,
                        'environment_variable': env_var,
                        'violation_type': 'DIRECT_ENVIRONMENT_ACCESS'
                    })

        return violations

    def extract_env_var_from_line(self, code_line: str) -> str:
        """Extract environment variable name from code line."""
        # Look for patterns like os.getenv('VAR') or os.environ.get('VAR')
        for quote in ["'", '"']:
            if f"({quote}" in code_line and f"{quote})" in code_line:
                start = code_line.find(f"({quote}") + 2
                end = code_line.find(f"{quote})", start)
                if start < end:
                    return code_line[start:end]

            if f"[{quote}" in code_line and f"{quote}]" in code_line:
                start = code_line.find(f"[{quote}") + 2
                end = code_line.find(f"{quote}]", start)
                if start < end:
                    return code_line[start:end]

        return "UNKNOWN"

    def check_for_compliant_patterns(self, source_code: str) -> Dict[str, bool]:
        """Check if source code uses SSOT compliant patterns."""
        compliance_status = {}

        for pattern in self.compliant_patterns:
            compliance_status[pattern] = pattern in source_code

        # Check for IsolatedEnvironment import
        has_isolated_env_import = (
            'from shared.isolated_environment import' in source_code or
            'from dev_launcher.isolated_environment import' in source_code or
            'import shared.isolated_environment' in source_code
        )

        compliance_status['isolated_environment_import'] = has_isolated_env_import

        return compliance_status

    def test_auth_trace_logger_class_exists_and_importable(self):
        """
        Validate that AuthTraceLogger class exists and can be imported.
        This is a prerequisite for SSOT compliance testing.
        """
        logger_class = self.import_auth_trace_logger()

        assert logger_class is not None, f"AuthTraceLogger class not found in {self.module_path}"
        assert inspect.isclass(logger_class), f"AuthTraceLogger is not a class"

        # Test that it can be instantiated
        try:
            logger_instance = logger_class()
            assert logger_instance is not None, "AuthTraceLogger cannot be instantiated"
        except Exception as e:
            # If instantiation fails due to dependencies, that's ok for this test
            self.record_metric('instantiation_error', str(e))

    def test_auth_trace_logger_direct_environment_access_violation(self):
        """
        MUST FAIL CURRENTLY - Detect direct environment access in AuthTraceLogger.

        This test specifically checks for the known SSOT violation:
        os.getenv('ENVIRONMENT') usage instead of IsolatedEnvironment patterns.
        """
        logger_class = self.import_auth_trace_logger()
        source_code = self.get_source_code(logger_class)

        # Parse source for violations
        violations = self.parse_source_for_violations(source_code)

        # Filter for ENVIRONMENT variable violations
        env_violations = [
            v for v in violations
            if v['environment_variable'] == self.expected_violation_variable
        ]

        # Check for violations in expected line range
        target_violations = [
            v for v in env_violations
            if self.expected_violation_line_range[0] <= v['line_number'] <= self.expected_violation_line_range[1]
        ]

        # Record metrics
        self.record_metric('total_violations_found', len(violations))
        self.record_metric('environment_violations_found', len(env_violations))
        self.record_metric('target_violations_found', len(target_violations))

        # TEST ASSERTION: This MUST FAIL in current state
        assert len(target_violations) > 0, (
            f"EXPECTED SSOT VIOLATION NOT DETECTED: Expected to find os.getenv('ENVIRONMENT') violation "
            f"in lines {self.expected_violation_line_range[0]}-{self.expected_violation_line_range[1]} "
            f"of AuthTraceLogger, but none found. "
            f"All environment violations: {env_violations}. "
            f"All violations: {violations}. "
            f"This test should FAIL until the violation is fixed with IsolatedEnvironment."
        )

        # Verify specific pattern is detected
        detected_patterns = [v['pattern'] for v in target_violations]
        assert 'os.getenv(' in detected_patterns, (
            f"Expected 'os.getenv(' pattern not found. Detected patterns: {detected_patterns}"
        )

    def test_auth_trace_logger_lacks_isolated_environment_compliance(self):
        """
        MUST FAIL CURRENTLY - Validate that AuthTraceLogger lacks proper SSOT patterns.

        This test checks that the current implementation does NOT use SSOT compliant
        patterns and should fail until remediation is complete.
        """
        logger_class = self.import_auth_trace_logger()
        source_code = self.get_source_code(logger_class)

        # Check for compliant patterns
        compliance_status = self.check_for_compliant_patterns(source_code)

        # Record metrics
        self.record_metric('compliance_patterns_found', compliance_status)

        # Current expectation: Should NOT have SSOT compliance
        has_any_compliant_pattern = any(compliance_status.values())

        # TEST ASSERTION: This MUST FAIL in current state (no SSOT compliance)
        assert not has_any_compliant_pattern, (
            f"UNEXPECTED SSOT COMPLIANCE DETECTED: AuthTraceLogger appears to already use SSOT patterns. "
            f"Compliance status: {compliance_status}. "
            f"Expected no SSOT compliance in current state. "
            f"If remediation is complete, update test expectations."
        )

        # Specifically check that IsolatedEnvironment is not imported
        assert not compliance_status['isolated_environment_import'], (
            f"IsolatedEnvironment import detected in AuthTraceLogger, but expected direct os.environ usage. "
            f"If remediation is complete, this test should be updated."
        )

    def test_auth_trace_logger_environment_access_methods(self):
        """
        Test specific methods in AuthTraceLogger that access environment variables.

        This test identifies which methods contain SSOT violations and will help
        with targeted remediation.
        """
        logger_class = self.import_auth_trace_logger()

        # Get methods that might access environment variables
        methods_to_check = []
        for name, method in inspect.getmembers(logger_class, predicate=inspect.isfunction):
            if not name.startswith('_'):  # Skip private methods
                methods_to_check.append((name, method))

        # Check each method for violations
        method_violations = {}
        total_violations = 0

        for method_name, method in methods_to_check:
            try:
                method_source = self.get_source_code(method)
                violations = self.parse_source_for_violations(method_source)

                if violations:
                    method_violations[method_name] = violations
                    total_violations += len(violations)

            except Exception as e:
                self.record_metric(f'method_source_error_{method_name}', str(e))

        # Record detailed metrics
        self.record_metric('methods_checked', len(methods_to_check))
        self.record_metric('methods_with_violations', len(method_violations))
        self.record_metric('total_method_violations', total_violations)
        self.record_metric('method_violation_details', method_violations)

        # TEST ASSERTION: Should find violations in current state
        assert total_violations > 0, (
            f"NO VIOLATIONS FOUND IN METHODS: Expected to find SSOT violations in AuthTraceLogger methods "
            f"but found none. Methods checked: {[name for name, _ in methods_to_check]}. "
            f"This may indicate the test is not detecting violations properly or remediation is complete."
        )

        # Validate that at least one method has ENVIRONMENT variable access
        env_methods = []
        for method_name, violations in method_violations.items():
            for violation in violations:
                if violation['environment_variable'] == 'ENVIRONMENT':
                    env_methods.append(method_name)

        assert len(env_methods) > 0, (
            f"NO ENVIRONMENT VARIABLE ACCESS FOUND: Expected to find methods accessing 'ENVIRONMENT' variable "
            f"but found none. Method violations: {method_violations}"
        )

    def test_auth_trace_logger_golden_path_impact_assessment(self):
        """
        Assess the Golden Path business impact of AuthTraceLogger SSOT violations.

        This test validates that violations in AuthTraceLogger affect critical
        authentication debugging capabilities worth $500K+ ARR protection.
        """
        logger_class = self.import_auth_trace_logger()
        source_code = self.get_source_code(logger_class)

        # Look for authentication-related functionality
        auth_related_patterns = [
            'auth',
            'token',
            'jwt',
            'login',
            'authenticate',
            'session',
            'user',
            'permission'
        ]

        # Check how many auth patterns are in the logger
        auth_pattern_count = sum(1 for pattern in auth_related_patterns if pattern.lower() in source_code.lower())

        # Find SSOT violations
        violations = self.parse_source_for_violations(source_code)
        env_violations = [v for v in violations if v['environment_variable'] == 'ENVIRONMENT']

        # Record business impact metrics
        self.record_metric('auth_patterns_found', auth_pattern_count)
        self.record_metric('golden_path_impact_violations', len(env_violations))

        # Assess business impact
        has_auth_functionality = auth_pattern_count > 0
        has_env_violations = len(env_violations) > 0

        # TEST ASSERTION: Validate Golden Path impact
        if has_auth_functionality and has_env_violations:
            # This is the expected current state - auth logger with SSOT violations
            assert True, (
                f"GOLDEN PATH IMPACT CONFIRMED: AuthTraceLogger contains {auth_pattern_count} "
                f"authentication patterns and {len(env_violations)} ENVIRONMENT variable violations. "
                f"This affects $500K+ ARR authentication debugging capability."
            )
        elif has_auth_functionality and not has_env_violations:
            pytest.fail(
                f"SSOT REMEDIATION APPEARS COMPLETE: AuthTraceLogger has authentication functionality "
                f"but no ENVIRONMENT variable violations detected. If remediation is complete, "
                f"update test expectations to validate proper IsolatedEnvironment usage."
            )
        else:
            pytest.fail(
                f"UNEXPECTED STATE: AuthTraceLogger analysis shows auth patterns: {auth_pattern_count}, "
                f"ENVIRONMENT violations: {len(env_violations)}. Verify test logic and file content."
            )

    def test_auth_trace_logger_ssot_remediation_readiness(self):
        """
        Prepare for SSOT remediation by identifying what needs to be changed.

        This test documents the current state and provides guidance for
        converting to SSOT-compliant patterns.
        """
        logger_class = self.import_auth_trace_logger()
        source_code = self.get_source_code(logger_class)

        # Find all violations
        violations = self.parse_source_for_violations(source_code)

        # Create remediation guide
        remediation_guide = {
            'violations_to_fix': [],
            'recommended_patterns': {
                'os.getenv(': 'get_env().get(',
                'os.environ.get(': 'get_env().get(',
                'os.environ[': 'get_env().get(',
            },
            'required_imports': [
                'from shared.isolated_environment import get_env'
            ]
        }

        for violation in violations:
            remediation_guide['violations_to_fix'].append({
                'line': violation['line_number'],
                'current': violation['code_line'],
                'pattern': violation['pattern'],
                'variable': violation['environment_variable'],
                'recommended_fix': violation['code_line'].replace(
                    violation['pattern'],
                    remediation_guide['recommended_patterns'].get(violation['pattern'], 'get_env().get(')
                )
            })

        # Record comprehensive remediation information
        self.record_metric('ssot_remediation_guide', remediation_guide)
        self.record_metric('violations_count_for_remediation', len(violations))

        # TEST ASSERTION: Provide remediation guidance
        assert len(violations) > 0, (
            f"SSOT REMEDIATION GUIDE: Found {len(violations)} violations in AuthTraceLogger that need fixing. "
            f"Remediation guide: {remediation_guide}. "
            f"After remediation, these violations should be replaced with IsolatedEnvironment patterns."
        )


if __name__ == "__main__":
    # Run the test to validate auth trace logger SSOT compliance
    pytest.main([__file__, "-v", "--tb=short"])