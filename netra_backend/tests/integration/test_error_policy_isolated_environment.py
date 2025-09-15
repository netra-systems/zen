"""
IsolatedEnvironment Integration Tests for ErrorPolicy Class

This test suite validates the integration between ErrorPolicy and IsolatedEnvironment,
ensuring proper SSOT compliance and environment detection behavior.

CRITICAL: These tests verify that ErrorPolicy can work seamlessly with the SSOT
IsolatedEnvironment pattern for all environment detection scenarios.

Test Coverage:
1. ErrorPolicy + IsolatedEnvironment integration for production detection
2. ErrorPolicy + IsolatedEnvironment integration for staging detection
3. ErrorPolicy + IsolatedEnvironment integration for testing detection

Business Value: Platform/Internal - SSOT Integration & Environment Detection
Ensures ErrorPolicy properly integrates with unified environment management patterns.

Expected Behavior BEFORE Remediation:
- Integration tests may show inconsistencies due to direct os.getenv() usage
- Environment detection may not respect IsolatedEnvironment isolation

Expected Behavior AFTER Remediation:
- All integration tests pass with seamless IsolatedEnvironment compatibility
- Environment detection respects SSOT isolation patterns
"""

import os
from unittest.mock import patch, MagicMock

# SSOT BaseTestCase import
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Target classes under test
from netra_backend.app.core.exceptions.error_policy import ErrorPolicy, EnvironmentType
from shared.isolated_environment import IsolatedEnvironment


class TestErrorPolicyIsolatedEnvironmentIntegration(SSotBaseTestCase):
    """
    Integration tests for ErrorPolicy and IsolatedEnvironment SSOT compliance.

    These tests validate that ErrorPolicy properly integrates with the unified
    environment management system and respects isolation patterns.
    """

    def setup_method(self, method=None):
        """Setup test environment for integration testing."""
        super().setup_method(method)

        # Reset ErrorPolicy singleton state for clean testing
        ErrorPolicy._instance = None
        ErrorPolicy._environment_type = None
        ErrorPolicy._policy_overrides = {}

        # Store original environment state
        self.original_env_vars = {}
        env_vars_to_backup = [
            'ENVIRONMENT', 'NETRA_ENV', 'GCP_PROJECT', 'DATABASE_URL',
            'REDIS_URL', 'SERVICE_ENV', 'POSTGRES_PORT', 'REDIS_PORT',
            'CI', 'TESTING', '_'
        ]

        for var in env_vars_to_backup:
            self.original_env_vars[var] = os.getenv(var)

    def teardown_method(self, method=None):
        """Cleanup test environment."""
        # Reset ErrorPolicy singleton state
        ErrorPolicy._instance = None
        ErrorPolicy._environment_type = None
        ErrorPolicy._policy_overrides = {}

        # Restore original environment state
        for var, value in self.original_env_vars.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

        super().teardown_method(method)

    def test_error_policy_production_detection_isolated_environment_integration(self):
        """
        INTEGRATION TEST: Validates ErrorPolicy production detection with IsolatedEnvironment.

        This test ensures that ErrorPolicy can correctly detect production environment
        when using IsolatedEnvironment for variable access instead of direct os.getenv().

        Expected Behavior:
        - BEFORE Remediation: May show inconsistencies due to os.getenv() bypass
        - AFTER Remediation: Perfect integration with IsolatedEnvironment isolation
        """
        # Test production detection scenarios with IsolatedEnvironment
        production_scenarios = [
            {
                'name': 'explicit_environment_production',
                'env_vars': {'ENVIRONMENT': 'production'},
                'expected': EnvironmentType.PRODUCTION
            },
            {
                'name': 'explicit_netra_env_production',
                'env_vars': {'NETRA_ENV': 'prod'},
                'expected': EnvironmentType.PRODUCTION
            },
            {
                'name': 'gcp_production_project',
                'env_vars': {'GCP_PROJECT': 'netra-production'},
                'expected': EnvironmentType.PRODUCTION
            },
            {
                'name': 'production_database_url',
                'env_vars': {'DATABASE_URL': 'postgresql://user:pass@prod-db:5432/netra'},
                'expected': EnvironmentType.PRODUCTION
            },
            {
                'name': 'production_redis_url',
                'env_vars': {'REDIS_URL': 'redis://prod-redis:6379/0'},
                'expected': EnvironmentType.PRODUCTION
            },
            {
                'name': 'production_service_env',
                'env_vars': {'SERVICE_ENV': 'production'},
                'expected': EnvironmentType.PRODUCTION
            }
        ]

        integration_results = {}
        ssot_compliance_issues = []

        for scenario in production_scenarios:
            # Reset ErrorPolicy for each scenario
            ErrorPolicy._instance = None
            ErrorPolicy._environment_type = None

            try:
                # Use IsolatedEnvironment through SSOT base test case
                with self.temp_env_vars(**scenario['env_vars']):
                    # Get isolated environment to verify SSOT usage
                    isolated_env = self.get_env()

                    # Verify IsolatedEnvironment sees the values
                    for key, expected_value in scenario['env_vars'].items():
                        actual_value = isolated_env.get(key)
                        if actual_value != expected_value:
                            ssot_compliance_issues.append(
                                f"Scenario {scenario['name']}: IsolatedEnvironment.get('{key}') "
                                f"returned '{actual_value}', expected '{expected_value}'"
                            )

                    # Test ErrorPolicy environment detection
                    detected_env = ErrorPolicy.detect_environment()

                    # Record results
                    integration_results[scenario['name']] = {
                        'detected_environment': detected_env.value if detected_env else None,
                        'expected_environment': scenario['expected'].value,
                        'detection_correct': detected_env == scenario['expected'],
                        'isolation_working': True
                    }

                    # Check if ErrorPolicy respects IsolatedEnvironment isolation
                    if detected_env != scenario['expected']:
                        ssot_compliance_issues.append(
                            f"Scenario {scenario['name']}: ErrorPolicy detected {detected_env}, "
                            f"expected {scenario['expected']} - possible os.getenv() bypass"
                        )

            except Exception as e:
                integration_results[scenario['name']] = {
                    'error': str(e),
                    'detection_correct': False,
                    'isolation_working': False
                }
                ssot_compliance_issues.append(
                    f"Scenario {scenario['name']} failed: {e}"
                )

        # Record test metrics
        self.record_metric('production_integration_results', integration_results)
        self.record_metric('ssot_compliance_issues', ssot_compliance_issues)
        self.record_metric('production_scenarios_tested', len(production_scenarios))
        self.record_metric('production_scenarios_passed',
                          sum(1 for r in integration_results.values() if r.get('detection_correct', False)))

        # ASSERTION: ErrorPolicy should work seamlessly with IsolatedEnvironment
        if ssot_compliance_issues:
            issue_details = "\n".join([f"  - {issue}" for issue in ssot_compliance_issues])

            assert False, (
                f"SSOT INTEGRATION ISSUES: ErrorPolicy production detection not fully compatible with IsolatedEnvironment.\n"
                f"Issues detected:\n{issue_details}\n\n"
                f"This indicates ErrorPolicy may be using direct os.getenv() instead of IsolatedEnvironment.\n\n"
                f"Required Remediation:\n"
                f"1. Replace all os.getenv() calls in ErrorPolicy with IsolatedEnvironment.get()\n"
                f"2. Inject IsolatedEnvironment instance into ErrorPolicy constructor\n"
                f"3. Ensure all environment detection methods use SSOT pattern\n"
                f"4. Validate integration works seamlessly with test isolation"
            )

    def test_error_policy_staging_detection_isolated_environment_integration(self):
        """
        INTEGRATION TEST: Validates ErrorPolicy staging detection with IsolatedEnvironment.

        This test ensures that ErrorPolicy can correctly detect staging environment
        when using IsolatedEnvironment for variable access.

        Expected Behavior:
        - BEFORE Remediation: May show inconsistencies due to os.getenv() bypass
        - AFTER Remediation: Perfect integration with IsolatedEnvironment isolation
        """
        # Test staging detection scenarios with IsolatedEnvironment
        staging_scenarios = [
            {
                'name': 'explicit_environment_staging',
                'env_vars': {'ENVIRONMENT': 'staging'},
                'expected': EnvironmentType.STAGING
            },
            {
                'name': 'explicit_netra_env_staging',
                'env_vars': {'NETRA_ENV': 'stage'},
                'expected': EnvironmentType.STAGING
            },
            {
                'name': 'gcp_staging_project',
                'env_vars': {'GCP_PROJECT': 'netra-staging'},
                'expected': EnvironmentType.STAGING
            },
            {
                'name': 'staging_database_url',
                'env_vars': {'DATABASE_URL': 'postgresql://user:pass@staging-db:5432/netra'},
                'expected': EnvironmentType.STAGING
            },
            {
                'name': 'staging_redis_url',
                'env_vars': {'REDIS_URL': 'redis://staging-redis:6379/0'},
                'expected': EnvironmentType.STAGING
            },
            {
                'name': 'staging_service_env',
                'env_vars': {'SERVICE_ENV': 'staging'},
                'expected': EnvironmentType.STAGING
            }
        ]

        integration_results = {}
        ssot_compliance_issues = []

        for scenario in staging_scenarios:
            # Reset ErrorPolicy for each scenario
            ErrorPolicy._instance = None
            ErrorPolicy._environment_type = None

            try:
                # Use IsolatedEnvironment through SSOT base test case
                with self.temp_env_vars(**scenario['env_vars']):
                    # Get isolated environment to verify SSOT usage
                    isolated_env = self.get_env()

                    # Verify IsolatedEnvironment sees the values
                    for key, expected_value in scenario['env_vars'].items():
                        actual_value = isolated_env.get(key)
                        if actual_value != expected_value:
                            ssot_compliance_issues.append(
                                f"Scenario {scenario['name']}: IsolatedEnvironment.get('{key}') "
                                f"returned '{actual_value}', expected '{expected_value}'"
                            )

                    # Test ErrorPolicy environment detection
                    detected_env = ErrorPolicy.detect_environment()

                    # Record results
                    integration_results[scenario['name']] = {
                        'detected_environment': detected_env.value if detected_env else None,
                        'expected_environment': scenario['expected'].value,
                        'detection_correct': detected_env == scenario['expected'],
                        'isolation_working': True
                    }

                    # Check if ErrorPolicy respects IsolatedEnvironment isolation
                    if detected_env != scenario['expected']:
                        ssot_compliance_issues.append(
                            f"Scenario {scenario['name']}: ErrorPolicy detected {detected_env}, "
                            f"expected {scenario['expected']} - possible os.getenv() bypass"
                        )

            except Exception as e:
                integration_results[scenario['name']] = {
                    'error': str(e),
                    'detection_correct': False,
                    'isolation_working': False
                }
                ssot_compliance_issues.append(
                    f"Scenario {scenario['name']} failed: {e}"
                )

        # Record test metrics
        self.record_metric('staging_integration_results', integration_results)
        self.record_metric('staging_ssot_compliance_issues', ssot_compliance_issues)
        self.record_metric('staging_scenarios_tested', len(staging_scenarios))
        self.record_metric('staging_scenarios_passed',
                          sum(1 for r in integration_results.values() if r.get('detection_correct', False)))

        # ASSERTION: ErrorPolicy should work seamlessly with IsolatedEnvironment
        if ssot_compliance_issues:
            issue_details = "\n".join([f"  - {issue}" for issue in ssot_compliance_issues])

            assert False, (
                f"SSOT INTEGRATION ISSUES: ErrorPolicy staging detection not fully compatible with IsolatedEnvironment.\n"
                f"Issues detected:\n{issue_details}\n\n"
                f"This indicates ErrorPolicy may be using direct os.getenv() instead of IsolatedEnvironment.\n\n"
                f"Required Remediation:\n"
                f"1. Replace all os.getenv() calls in ErrorPolicy with IsolatedEnvironment.get()\n"
                f"2. Inject IsolatedEnvironment instance into ErrorPolicy constructor\n"
                f"3. Ensure all environment detection methods use SSOT pattern\n"
                f"4. Validate integration works seamlessly with test isolation"
            )

    def test_error_policy_testing_detection_isolated_environment_integration(self):
        """
        INTEGRATION TEST: Validates ErrorPolicy testing detection with IsolatedEnvironment.

        This test ensures that ErrorPolicy can correctly detect testing environment
        when using IsolatedEnvironment for variable access.

        Expected Behavior:
        - BEFORE Remediation: May show inconsistencies due to os.getenv() bypass
        - AFTER Remediation: Perfect integration with IsolatedEnvironment isolation
        """
        # Test testing detection scenarios with IsolatedEnvironment
        testing_scenarios = [
            {
                'name': 'explicit_environment_testing',
                'env_vars': {'ENVIRONMENT': 'testing'},
                'expected': EnvironmentType.TESTING
            },
            {
                'name': 'explicit_netra_env_testing',
                'env_vars': {'NETRA_ENV': 'test'},
                'expected': EnvironmentType.TESTING
            },
            {
                'name': 'pytest_indicator',
                'env_vars': {'_': 'pytest'},
                'expected': EnvironmentType.TESTING
            },
            {
                'name': 'test_postgres_port',
                'env_vars': {'POSTGRES_PORT': '5434'},
                'expected': EnvironmentType.TESTING
            },
            {
                'name': 'test_redis_port',
                'env_vars': {'REDIS_PORT': '6381'},
                'expected': EnvironmentType.TESTING
            },
            {
                'name': 'ci_environment',
                'env_vars': {'CI': 'true'},
                'expected': EnvironmentType.TESTING
            },
            {
                'name': 'testing_flag',
                'env_vars': {'TESTING': 'true'},
                'expected': EnvironmentType.TESTING
            }
        ]

        integration_results = {}
        ssot_compliance_issues = []

        for scenario in testing_scenarios:
            # Reset ErrorPolicy for each scenario
            ErrorPolicy._instance = None
            ErrorPolicy._environment_type = None

            try:
                # Use IsolatedEnvironment through SSOT base test case
                with self.temp_env_vars(**scenario['env_vars']):
                    # Get isolated environment to verify SSOT usage
                    isolated_env = self.get_env()

                    # Verify IsolatedEnvironment sees the values
                    for key, expected_value in scenario['env_vars'].items():
                        actual_value = isolated_env.get(key)
                        if actual_value != expected_value:
                            ssot_compliance_issues.append(
                                f"Scenario {scenario['name']}: IsolatedEnvironment.get('{key}') "
                                f"returned '{actual_value}', expected '{expected_value}'"
                            )

                    # Test ErrorPolicy environment detection
                    detected_env = ErrorPolicy.detect_environment()

                    # Record results
                    integration_results[scenario['name']] = {
                        'detected_environment': detected_env.value if detected_env else None,
                        'expected_environment': scenario['expected'].value,
                        'detection_correct': detected_env == scenario['expected'],
                        'isolation_working': True
                    }

                    # Check if ErrorPolicy respects IsolatedEnvironment isolation
                    if detected_env != scenario['expected']:
                        ssot_compliance_issues.append(
                            f"Scenario {scenario['name']}: ErrorPolicy detected {detected_env}, "
                            f"expected {scenario['expected']} - possible os.getenv() bypass"
                        )

            except Exception as e:
                integration_results[scenario['name']] = {
                    'error': str(e),
                    'detection_correct': False,
                    'isolation_working': False
                }
                ssot_compliance_issues.append(
                    f"Scenario {scenario['name']} failed: {e}"
                )

        # Record test metrics
        self.record_metric('testing_integration_results', integration_results)
        self.record_metric('testing_ssot_compliance_issues', ssot_compliance_issues)
        self.record_metric('testing_scenarios_tested', len(testing_scenarios))
        self.record_metric('testing_scenarios_passed',
                          sum(1 for r in integration_results.values() if r.get('detection_correct', False)))

        # ASSERTION: ErrorPolicy should work seamlessly with IsolatedEnvironment
        if ssot_compliance_issues:
            issue_details = "\n".join([f"  - {issue}" for issue in ssot_compliance_issues])

            assert False, (
                f"SSOT INTEGRATION ISSUES: ErrorPolicy testing detection not fully compatible with IsolatedEnvironment.\n"
                f"Issues detected:\n{issue_details}\n\n"
                f"This indicates ErrorPolicy may be using direct os.getenv() instead of IsolatedEnvironment.\n\n"
                f"Required Remediation:\n"
                f"1. Replace all os.getenv() calls in ErrorPolicy with IsolatedEnvironment.get()\n"
                f"2. Inject IsolatedEnvironment instance into ErrorPolicy constructor\n"
                f"3. Ensure all environment detection methods use SSOT pattern\n"
                f"4. Validate integration works seamlessly with test isolation"
            )

    def test_error_policy_environment_isolation_boundaries(self):
        """
        INTEGRATION TEST: Validates ErrorPolicy respects IsolatedEnvironment isolation boundaries.

        This test ensures that ErrorPolicy environment detection properly respects
        the isolation boundaries provided by IsolatedEnvironment and doesn't leak
        state between isolated environments.

        Expected Behavior:
        - BEFORE Remediation: May show state leakage due to direct os.getenv() usage
        - AFTER Remediation: Perfect isolation boundary respect
        """
        isolation_test_results = []

        # Test isolation boundaries with different environment combinations
        test_sequences = [
            {
                'name': 'production_to_staging_isolation',
                'sequence': [
                    {'ENVIRONMENT': 'production', 'expected': EnvironmentType.PRODUCTION},
                    {'ENVIRONMENT': 'staging', 'expected': EnvironmentType.STAGING}
                ]
            },
            {
                'name': 'staging_to_testing_isolation',
                'sequence': [
                    {'NETRA_ENV': 'staging', 'expected': EnvironmentType.STAGING},
                    {'NETRA_ENV': 'testing', 'expected': EnvironmentType.TESTING}
                ]
            },
            {
                'name': 'testing_to_development_isolation',
                'sequence': [
                    {'TESTING': 'true', 'expected': EnvironmentType.TESTING},
                    {'ENVIRONMENT': 'development', 'expected': EnvironmentType.DEVELOPMENT}
                ]
            }
        ]

        isolation_violations = []

        for test_sequence in test_sequences:
            sequence_results = []

            for step_idx, step in enumerate(test_sequence['sequence']):
                # Reset ErrorPolicy for each step
                ErrorPolicy._instance = None
                ErrorPolicy._environment_type = None

                try:
                    # Create isolated environment for this step
                    env_vars = {k: v for k, v in step.items() if k != 'expected'}
                    expected_env = step['expected']

                    with self.temp_env_vars(**env_vars):
                        # Verify isolation is working
                        isolated_env = self.get_env()

                        # Check that only current step's variables are visible
                        for key, value in env_vars.items():
                            actual_value = isolated_env.get(key)
                            if actual_value != value:
                                isolation_violations.append(
                                    f"Sequence {test_sequence['name']}, Step {step_idx}: "
                                    f"IsolatedEnvironment.get('{key}') returned '{actual_value}', expected '{value}'"
                                )

                        # Test ErrorPolicy environment detection
                        detected_env = ErrorPolicy.detect_environment()

                        step_result = {
                            'step': step_idx,
                            'env_vars': env_vars,
                            'expected': expected_env.value,
                            'detected': detected_env.value if detected_env else None,
                            'isolation_respected': detected_env == expected_env
                        }

                        sequence_results.append(step_result)

                        # Check for isolation violations
                        if detected_env != expected_env:
                            isolation_violations.append(
                                f"Sequence {test_sequence['name']}, Step {step_idx}: "
                                f"ErrorPolicy detected {detected_env}, expected {expected_env} - "
                                f"possible state leakage or os.getenv() bypass"
                            )

                except Exception as e:
                    isolation_violations.append(
                        f"Sequence {test_sequence['name']}, Step {step_idx} failed: {e}"
                    )

            isolation_test_results.append({
                'sequence_name': test_sequence['name'],
                'results': sequence_results
            })

        # Record test metrics
        self.record_metric('isolation_test_results', isolation_test_results)
        self.record_metric('isolation_violations', isolation_violations)
        self.record_metric('isolation_sequences_tested', len(test_sequences))

        # ASSERTION: No isolation boundary violations should occur
        if isolation_violations:
            violation_details = "\n".join([f"  - {violation}" for violation in isolation_violations])

            assert False, (
                f"ISOLATION BOUNDARY VIOLATIONS: ErrorPolicy does not respect IsolatedEnvironment isolation.\n"
                f"Violations detected:\n{violation_details}\n\n"
                f"This indicates ErrorPolicy is using direct os.getenv() which bypasses isolation boundaries.\n\n"
                f"Required Remediation:\n"
                f"1. Replace ALL os.getenv() calls with IsolatedEnvironment.get()\n"
                f"2. Ensure ErrorPolicy constructor accepts IsolatedEnvironment instance\n"
                f"3. Verify environment detection methods use injected IsolatedEnvironment\n"
                f"4. Test isolation boundaries work correctly after remediation\n"
                f"5. Add proper SSOT compliance validation to prevent regressions"
            )

    def test_error_policy_development_fallback_isolated_environment_integration(self):
        """
        INTEGRATION TEST: Validates ErrorPolicy development fallback with IsolatedEnvironment.

        This test ensures that ErrorPolicy correctly falls back to development
        environment when no specific environment indicators are present,
        and that this works properly with IsolatedEnvironment isolation.

        Expected Behavior:
        - BEFORE Remediation: May not respect isolation for fallback detection
        - AFTER Remediation: Proper fallback through IsolatedEnvironment
        """
        # Reset ErrorPolicy state
        ErrorPolicy._instance = None
        ErrorPolicy._environment_type = None

        fallback_test_issues = []

        try:
            # Test with completely clean environment (no environment indicators)
            with self.temp_env_vars():
                # Clear all potential environment indicators
                env_vars_to_clear = [
                    'ENVIRONMENT', 'NETRA_ENV', 'GCP_PROJECT', 'DATABASE_URL',
                    'REDIS_URL', 'SERVICE_ENV', 'POSTGRES_PORT', 'REDIS_PORT',
                    'CI', 'TESTING', '_'
                ]

                for var in env_vars_to_clear:
                    self.delete_env_var(var)

                # Verify environment is clean through IsolatedEnvironment
                isolated_env = self.get_env()
                for var in env_vars_to_clear:
                    if isolated_env.get(var) is not None:
                        fallback_test_issues.append(
                            f"Environment variable '{var}' not properly cleared in IsolatedEnvironment"
                        )

                # Test ErrorPolicy fallback behavior
                detected_env = ErrorPolicy.detect_environment()

                # Should fallback to DEVELOPMENT
                if detected_env != EnvironmentType.DEVELOPMENT:
                    fallback_test_issues.append(
                        f"ErrorPolicy fallback failed: detected {detected_env}, "
                        f"expected {EnvironmentType.DEVELOPMENT} - "
                        f"possible os.getenv() interference"
                    )

                # Test that fallback is consistent on repeated calls
                detected_env_2 = ErrorPolicy.detect_environment()
                if detected_env != detected_env_2:
                    fallback_test_issues.append(
                        f"ErrorPolicy fallback inconsistent: first call {detected_env}, "
                        f"second call {detected_env_2} - possible state issues"
                    )

        except Exception as e:
            fallback_test_issues.append(f"Fallback test failed: {e}")

        # Record test metrics
        self.record_metric('fallback_test_issues', fallback_test_issues)
        self.record_metric('fallback_detection_working', len(fallback_test_issues) == 0)

        # ASSERTION: Fallback should work properly with IsolatedEnvironment
        if fallback_test_issues:
            issue_details = "\n".join([f"  - {issue}" for issue in fallback_test_issues])

            assert False, (
                f"FALLBACK INTEGRATION ISSUES: ErrorPolicy development fallback not working with IsolatedEnvironment.\n"
                f"Issues detected:\n{issue_details}\n\n"
                f"This indicates ErrorPolicy may be using direct os.getenv() for fallback detection.\n\n"
                f"Required Remediation:\n"
                f"1. Ensure fallback logic uses IsolatedEnvironment.get() instead of os.getenv()\n"
                f"2. Verify fallback behavior works correctly with environment isolation\n"
                f"3. Test fallback consistency across multiple calls\n"
                f"4. Ensure fallback doesn't interfere with other environment detection"
            )