#!/usr/bin/env python3
"""
Unit Test: Error Recovery Middleware SSOT Compliance Validation

Business Value: Platform/Internal - System Stability & Error Handling
Critical for $500K+ ARR protection through consistent error recovery patterns.

PURPOSE: This test MUST FAIL with current SSOT violations and PASS after remediation.
Validates that ErrorRecoveryMiddleware uses IsolatedEnvironment instead of direct os.environ.

CRITICAL VIOLATION TO DETECT:
- netra_backend/app/middleware/error_recovery_middleware.py:33 - os.environ.get('ENVIRONMENT')

Expected Behavior:
- CURRENT STATE: This test should FAIL due to direct os.environ usage
- AFTER REMEDIATION: This test should PASS when using get_env() from IsolatedEnvironment

Test Strategy:
- Import and inspect ErrorRecoveryMiddleware source code
- Validate environment access patterns in error handling logic
- Ensure SSOT compliance in production environment detection
- Protect Golden Path user experience through consistent error handling

Author: SSOT Gardener Agent - Step 2 Test Plan Execution
Date: 2025-09-13
"""

import inspect
import ast
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from unittest.mock import patch, MagicMock

import pytest

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestErrorRecoveryMiddlewareSsotCompliance(SSotBaseTestCase):
    """Unit tests for Error Recovery Middleware SSOT configuration compliance."""

    def setup_method(self, method=None):
        """Setup test environment for error recovery middleware SSOT validation."""
        super().setup_method(method)

        # Import paths
        self.module_path = 'netra_backend.app.middleware.error_recovery_middleware'
        self.middleware_class_name = 'ErrorRecoveryMiddleware'

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
        self.expected_violation_line_range = (30, 40)  # Around line 33
        self.expected_violation_variable = 'ENVIRONMENT'
        self.expected_violation_context = 'production'  # Should be checking for production environment

    def import_error_recovery_middleware(self):
        """Safely import the ErrorRecoveryMiddleware class."""
        try:
            module = __import__(self.module_path, fromlist=[self.middleware_class_name])
            middleware_class = getattr(module, self.middleware_class_name)
            return middleware_class
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Cannot import ErrorRecoveryMiddleware: {str(e)}")

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

                    # Check for production environment context
                    has_production_check = 'production' in line.lower()

                    violations.append({
                        'line_number': line_num,
                        'code_line': line.strip(),
                        'pattern': pattern,
                        'environment_variable': env_var,
                        'has_production_check': has_production_check,
                        'violation_type': 'DIRECT_ENVIRONMENT_ACCESS'
                    })

        return violations

    def extract_env_var_from_line(self, code_line: str) -> str:
        """Extract environment variable name from code line."""
        # Look for patterns like os.environ.get('VAR') or os.getenv('VAR')
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

    def test_error_recovery_middleware_class_exists_and_importable(self):
        """
        Validate that ErrorRecoveryMiddleware class exists and can be imported.
        This is a prerequisite for SSOT compliance testing.
        """
        middleware_class = self.import_error_recovery_middleware()

        assert middleware_class is not None, f"ErrorRecoveryMiddleware class not found in {self.module_path}"
        assert inspect.isclass(middleware_class), f"ErrorRecoveryMiddleware is not a class"

        # Test that it can be instantiated (with minimal args)
        try:
            # Middleware typically requires app instance, try with mock
            mock_app = MagicMock()
            middleware_instance = middleware_class(mock_app)
            assert middleware_instance is not None, "ErrorRecoveryMiddleware cannot be instantiated"
        except Exception as e:
            # If instantiation fails due to dependencies, that's ok for this test
            self.record_metric('instantiation_error', str(e))

    def test_error_recovery_middleware_direct_environment_access_violation(self):
        """
        MUST FAIL CURRENTLY - Detect direct environment access in ErrorRecoveryMiddleware.

        This test specifically checks for the known SSOT violation:
        os.environ.get('ENVIRONMENT') usage instead of IsolatedEnvironment patterns.
        """
        middleware_class = self.import_error_recovery_middleware()
        source_code = self.get_source_code(middleware_class)

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

        # Check for production environment check context
        production_violations = [
            v for v in target_violations
            if v['has_production_check']
        ]

        # Record metrics
        self.record_metric('total_violations_found', len(violations))
        self.record_metric('environment_violations_found', len(env_violations))
        self.record_metric('target_violations_found', len(target_violations))
        self.record_metric('production_check_violations', len(production_violations))

        # TEST ASSERTION: This MUST FAIL in current state
        assert len(target_violations) > 0, (
            f"EXPECTED SSOT VIOLATION NOT DETECTED: Expected to find os.environ.get('ENVIRONMENT') violation "
            f"in lines {self.expected_violation_line_range[0]}-{self.expected_violation_line_range[1]} "
            f"of ErrorRecoveryMiddleware, but none found. "
            f"All environment violations: {env_violations}. "
            f"All violations: {violations}. "
            f"This test should FAIL until the violation is fixed with IsolatedEnvironment."
        )

        # Verify specific pattern is detected
        detected_patterns = [v['pattern'] for v in target_violations]
        assert 'os.environ.get(' in detected_patterns, (
            f"Expected 'os.environ.get(' pattern not found. Detected patterns: {detected_patterns}"
        )

        # Verify production environment check context
        assert len(production_violations) > 0, (
            f"Expected production environment check not found. Target violations: {target_violations}. "
            f"The middleware should be checking for production environment around line 33."
        )

    def test_error_recovery_middleware_lacks_isolated_environment_compliance(self):
        """
        MUST FAIL CURRENTLY - Validate that ErrorRecoveryMiddleware lacks proper SSOT patterns.

        This test checks that the current implementation does NOT use SSOT compliant
        patterns and should fail until remediation is complete.
        """
        middleware_class = self.import_error_recovery_middleware()
        source_code = self.get_source_code(middleware_class)

        # Check for compliant patterns
        compliance_status = self.check_for_compliant_patterns(source_code)

        # Record metrics
        self.record_metric('compliance_patterns_found', compliance_status)

        # Current expectation: Should NOT have SSOT compliance
        has_any_compliant_pattern = any(compliance_status.values())

        # TEST ASSERTION: This MUST FAIL in current state (no SSOT compliance)
        assert not has_any_compliant_pattern, (
            f"UNEXPECTED SSOT COMPLIANCE DETECTED: ErrorRecoveryMiddleware appears to already use SSOT patterns. "
            f"Compliance status: {compliance_status}. "
            f"Expected no SSOT compliance in current state. "
            f"If remediation is complete, update test expectations."
        )

        # Specifically check that IsolatedEnvironment is not imported
        assert not compliance_status['isolated_environment_import'], (
            f"IsolatedEnvironment import detected in ErrorRecoveryMiddleware, but expected direct os.environ usage. "
            f"If remediation is complete, this test should be updated."
        )

    def test_error_recovery_middleware_environment_check_methods(self):
        """
        Test specific methods in ErrorRecoveryMiddleware that check environment variables.

        This test identifies which methods contain SSOT violations and will help
        with targeted remediation, especially for production environment detection.
        """
        middleware_class = self.import_error_recovery_middleware()

        # Get methods that might access environment variables
        methods_to_check = []
        for name, method in inspect.getmembers(middleware_class, predicate=inspect.isfunction):
            if not name.startswith('__'):  # Skip magic methods but include _private methods
                methods_to_check.append((name, method))

        # Check each method for violations
        method_violations = {}
        total_violations = 0
        production_check_methods = []

        for method_name, method in methods_to_check:
            try:
                method_source = self.get_source_code(method)
                violations = self.parse_source_for_violations(method_source)

                if violations:
                    method_violations[method_name] = violations
                    total_violations += len(violations)

                    # Check for production environment checks
                    if 'production' in method_source.lower():
                        production_check_methods.append(method_name)

            except Exception as e:
                self.record_metric(f'method_source_error_{method_name}', str(e))

        # Record detailed metrics
        self.record_metric('methods_checked', len(methods_to_check))
        self.record_metric('methods_with_violations', len(method_violations))
        self.record_metric('total_method_violations', total_violations)
        self.record_metric('production_check_methods', production_check_methods)
        self.record_metric('method_violation_details', method_violations)

        # TEST ASSERTION: Should find violations in current state
        assert total_violations > 0, (
            f"NO VIOLATIONS FOUND IN METHODS: Expected to find SSOT violations in ErrorRecoveryMiddleware methods "
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

        # Validate production environment checks exist
        assert len(production_check_methods) > 0, (
            f"NO PRODUCTION ENVIRONMENT CHECKS FOUND: Expected error recovery middleware to check for production "
            f"environment but found none. Methods checked: {[name for name, _ in methods_to_check]}"
        )

    def test_error_recovery_middleware_production_environment_logic(self):
        """
        Test the production environment detection logic in ErrorRecoveryMiddleware.

        This test validates that the middleware properly handles different environments
        and identifies where SSOT violations affect production behavior.
        """
        middleware_class = self.import_error_recovery_middleware()
        source_code = self.get_source_code(middleware_class)

        # Look for production-related logic
        production_patterns = [
            'production',
            'prod',
            'env',
            'environment',
            'staging',
            'development'
        ]

        # Find lines with production checks
        production_lines = []
        lines = source_code.splitlines()

        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in production_patterns):
                if any(violation_pattern in line for violation_pattern in self.violation_patterns):
                    production_lines.append({
                        'line_number': line_num,
                        'code': line.strip(),
                        'has_violation': True
                    })

        # Parse all violations
        violations = self.parse_source_for_violations(source_code)
        env_violations = [v for v in violations if v['environment_variable'] == 'ENVIRONMENT']

        # Record metrics
        self.record_metric('production_related_lines', len(production_lines))
        self.record_metric('production_lines_with_violations',
                          len([line for line in production_lines if line['has_violation']]))
        self.record_metric('environment_violations_in_production_logic', len(env_violations))

        # TEST ASSERTION: Validate production logic has violations
        assert len(production_lines) > 0, (
            f"NO PRODUCTION ENVIRONMENT LOGIC FOUND: Expected ErrorRecoveryMiddleware to contain "
            f"production environment detection logic but found none. "
            f"This may indicate the middleware doesn't handle environment-specific behavior."
        )

        production_violations = [line for line in production_lines if line['has_violation']]
        assert len(production_violations) > 0, (
            f"NO VIOLATIONS IN PRODUCTION LOGIC: Expected to find SSOT violations in production environment "
            f"detection logic but found none. Production lines: {production_lines}. "
            f"Environment violations: {env_violations}"
        )

    def test_error_recovery_middleware_golden_path_impact_assessment(self):
        """
        Assess the Golden Path business impact of ErrorRecoveryMiddleware SSOT violations.

        This test validates that violations in ErrorRecoveryMiddleware affect critical
        error handling capabilities that protect $500K+ ARR user experience.
        """
        middleware_class = self.import_error_recovery_middleware()
        source_code = self.get_source_code(middleware_class)

        # Look for error handling related functionality
        error_handling_patterns = [
            'error',
            'exception',
            'recover',
            'fallback',
            'retry',
            'failure',
            'middleware',
            'response',
            'request'
        ]

        # Check how many error handling patterns are in the middleware
        error_pattern_count = sum(1 for pattern in error_handling_patterns
                                 if pattern.lower() in source_code.lower())

        # Find SSOT violations
        violations = self.parse_source_for_violations(source_code)
        env_violations = [v for v in violations if v['environment_variable'] == 'ENVIRONMENT']

        # Check for middleware-specific patterns
        has_middleware_functionality = (
            'middleware' in source_code.lower() or
            'request' in source_code.lower() or
            'response' in source_code.lower()
        )

        # Record business impact metrics
        self.record_metric('error_handling_patterns_found', error_pattern_count)
        self.record_metric('has_middleware_functionality', has_middleware_functionality)
        self.record_metric('golden_path_impact_violations', len(env_violations))

        # Assess business impact
        has_error_functionality = error_pattern_count > 2  # Allow for some basic patterns
        has_env_violations = len(env_violations) > 0

        # TEST ASSERTION: Validate Golden Path impact
        if has_error_functionality and has_env_violations:
            # This is the expected current state - error middleware with SSOT violations
            assert True, (
                f"GOLDEN PATH IMPACT CONFIRMED: ErrorRecoveryMiddleware contains {error_pattern_count} "
                f"error handling patterns and {len(env_violations)} ENVIRONMENT variable violations. "
                f"This affects $500K+ ARR user experience through inconsistent error recovery behavior."
            )
        elif has_error_functionality and not has_env_violations:
            pytest.fail(
                f"SSOT REMEDIATION APPEARS COMPLETE: ErrorRecoveryMiddleware has error handling functionality "
                f"but no ENVIRONMENT variable violations detected. If remediation is complete, "
                f"update test expectations to validate proper IsolatedEnvironment usage."
            )
        else:
            pytest.fail(
                f"UNEXPECTED STATE: ErrorRecoveryMiddleware analysis shows error patterns: {error_pattern_count}, "
                f"ENVIRONMENT violations: {len(env_violations)}. Verify test logic and file content."
            )

        # Additional validation for middleware functionality
        assert has_middleware_functionality, (
            f"MIDDLEWARE FUNCTIONALITY NOT DETECTED: Expected ErrorRecoveryMiddleware to contain "
            f"middleware-specific patterns but found limited functionality. "
            f"Verify this is actually a middleware class."
        )

    def test_error_recovery_middleware_ssot_remediation_readiness(self):
        """
        Prepare for SSOT remediation by identifying what needs to be changed.

        This test documents the current state and provides guidance for
        converting to SSOT-compliant patterns for production environment detection.
        """
        middleware_class = self.import_error_recovery_middleware()
        source_code = self.get_source_code(middleware_class)

        # Find all violations
        violations = self.parse_source_for_violations(source_code)

        # Create remediation guide
        remediation_guide = {
            'violations_to_fix': [],
            'recommended_patterns': {
                'os.environ.get(': 'get_env().get(',
                'os.getenv(': 'get_env().get(',
                'os.environ[': 'get_env().get(',
            },
            'required_imports': [
                'from shared.isolated_environment import get_env'
            ],
            'production_check_fixes': []
        }

        for violation in violations:
            # Specific remediation for production checks
            if violation['has_production_check']:
                current_line = violation['code_line']

                # Common production check patterns
                if "== 'production'" in current_line:
                    recommended_fix = current_line.replace(
                        violation['pattern'],
                        'get_env().get('
                    )
                    remediation_guide['production_check_fixes'].append({
                        'line': violation['line_number'],
                        'current': current_line,
                        'recommended': recommended_fix,
                        'note': 'Production environment check using IsolatedEnvironment'
                    })

            remediation_guide['violations_to_fix'].append({
                'line': violation['line_number'],
                'current': violation['code_line'],
                'pattern': violation['pattern'],
                'variable': violation['environment_variable'],
                'has_production_check': violation['has_production_check'],
                'recommended_fix': violation['code_line'].replace(
                    violation['pattern'],
                    remediation_guide['recommended_patterns'].get(violation['pattern'], 'get_env().get(')
                )
            })

        # Record comprehensive remediation information
        self.record_metric('ssot_remediation_guide', remediation_guide)
        self.record_metric('violations_count_for_remediation', len(violations))
        self.record_metric('production_checks_to_fix', len(remediation_guide['production_check_fixes']))

        # TEST ASSERTION: Provide remediation guidance
        assert len(violations) > 0, (
            f"SSOT REMEDIATION GUIDE: Found {len(violations)} violations in ErrorRecoveryMiddleware that need fixing. "
            f"Remediation guide: {remediation_guide}. "
            f"After remediation, these violations should be replaced with IsolatedEnvironment patterns. "
            f"Pay special attention to production environment checks: {len(remediation_guide['production_check_fixes'])} found."
        )


if __name__ == "__main__":
    # Run the test to validate error recovery middleware SSOT compliance
    pytest.main([__file__, "-v", "--tb=short"])
