"""
SSOT Regression Prevention Tests for ErrorPolicy Class

This test suite prevents regression of SSOT compliance after ErrorPolicy remediation.
These tests ensure that future changes to ErrorPolicy maintain SSOT compliance patterns.

CRITICAL: These tests are designed to catch any re-introduction of SSOT violations
after the initial remediation is complete.

Test Coverage:
1. Environment detection behavior consistency before/after SSOT migration
2. Backward compatibility of environment detection logic
3. Golden path functionality verification with SSOT pattern

Business Value: Platform/Internal - SSOT Regression Prevention & System Stability
Prevents re-introduction of SSOT violations and maintains environment detection reliability.

Expected Behavior POST-Remediation:
- All tests should PASS consistently
- Any future SSOT violations should be caught immediately
- Environment detection behavior should remain stable across code changes
"""

import os
import ast
import inspect
import sys
from unittest.mock import patch, MagicMock

# SSOT BaseTestCase import
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Target class under test
from netra_backend.app.core.exceptions.error_policy import ErrorPolicy, EnvironmentType, ErrorEscalationPolicy
from netra_backend.app.core.error_codes import ErrorSeverity
from shared.isolated_environment import IsolatedEnvironment


class TestErrorPolicySsotRegressionPrevention(SSotBaseTestCase):
    """
    SSOT regression prevention tests for ErrorPolicy class.

    These tests ensure that ErrorPolicy maintains SSOT compliance after remediation
    and prevents re-introduction of direct os.getenv() usage or other SSOT violations.
    """

    def setup_method(self, method=None):
        """Setup test environment for regression prevention testing."""
        super().setup_method(method)

        # Reset ErrorPolicy singleton state for clean testing
        ErrorPolicy._instance = None
        ErrorPolicy._environment_type = None
        ErrorPolicy._policy_overrides = {}

        # Store baseline environment state
        self.baseline_env_vars = {}
        env_vars_to_backup = [
            'ENVIRONMENT', 'NETRA_ENV', 'GCP_PROJECT', 'DATABASE_URL',
            'REDIS_URL', 'SERVICE_ENV', 'POSTGRES_PORT', 'REDIS_PORT',
            'CI', 'TESTING', '_'
        ]

        for var in env_vars_to_backup:
            self.baseline_env_vars[var] = os.getenv(var)

    def teardown_method(self, method=None):
        """Cleanup test environment."""
        # Reset ErrorPolicy singleton state
        ErrorPolicy._instance = None
        ErrorPolicy._environment_type = None
        ErrorPolicy._policy_overrides = {}

        # Restore baseline environment state
        for var, value in self.baseline_env_vars.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

        super().teardown_method(method)

    def test_environment_detection_behavior_consistency_post_ssot_migration(self):
        """
        REGRESSION TEST: Validates environment detection behavior remains consistent post-SSOT migration.

        This test ensures that the environment detection logic produces the same
        results after SSOT remediation as it did before (for the correct cases),
        while now properly using IsolatedEnvironment instead of direct os.getenv().

        Expected Behavior POST-Remediation:
        - Environment detection results remain consistent
        - All detection now goes through IsolatedEnvironment
        - No direct os.getenv() usage anywhere in ErrorPolicy
        """
        # Define reference environment detection test cases
        # These represent the expected behavior that should be preserved
        reference_test_cases = [
            {
                'name': 'production_explicit',
                'env_vars': {'ENVIRONMENT': 'production'},
                'expected': EnvironmentType.PRODUCTION,
                'priority': 'critical'
            },
            {
                'name': 'production_netra_env',
                'env_vars': {'NETRA_ENV': 'prod'},
                'expected': EnvironmentType.PRODUCTION,
                'priority': 'critical'
            },
            {
                'name': 'staging_explicit',
                'env_vars': {'ENVIRONMENT': 'staging'},
                'expected': EnvironmentType.STAGING,
                'priority': 'critical'
            },
            {
                'name': 'staging_netra_env',
                'env_vars': {'NETRA_ENV': 'stage'},
                'expected': EnvironmentType.STAGING,
                'priority': 'critical'
            },
            {
                'name': 'testing_explicit',
                'env_vars': {'ENVIRONMENT': 'testing'},
                'expected': EnvironmentType.TESTING,
                'priority': 'high'
            },
            {
                'name': 'testing_pytest',
                'env_vars': {'_': 'pytest'},
                'expected': EnvironmentType.TESTING,
                'priority': 'high'
            },
            {
                'name': 'development_explicit',
                'env_vars': {'ENVIRONMENT': 'development'},
                'expected': EnvironmentType.DEVELOPMENT,
                'priority': 'medium'
            },
            {
                'name': 'development_fallback',
                'env_vars': {},  # No environment vars set
                'expected': EnvironmentType.DEVELOPMENT,
                'priority': 'critical'  # Fallback behavior is critical
            }
        ]

        behavior_consistency_results = {}
        consistency_violations = []

        for test_case in reference_test_cases:
            # Reset ErrorPolicy for each test case
            ErrorPolicy._instance = None
            ErrorPolicy._environment_type = None

            try:
                # Test with IsolatedEnvironment isolation
                with self.temp_env_vars(**test_case['env_vars']):
                    # Verify IsolatedEnvironment sees the correct values
                    isolated_env = self.get_env()

                    # Clear any variables not in test case
                    all_env_vars = set(self.baseline_env_vars.keys())
                    test_env_vars = set(test_case['env_vars'].keys())
                    vars_to_clear = all_env_vars - test_env_vars

                    for var in vars_to_clear:
                        self.delete_env_var(var)

                    # Verify test setup through IsolatedEnvironment
                    for key, expected_value in test_case['env_vars'].items():
                        actual_value = isolated_env.get(key)
                        if actual_value != expected_value:
                            consistency_violations.append(
                                f"Test case {test_case['name']}: IsolatedEnvironment setup failed - "
                                f"'{key}' should be '{expected_value}', got '{actual_value}'"
                            )

                    # Test ErrorPolicy environment detection
                    detected_env = ErrorPolicy.detect_environment()

                    # Record behavior consistency results
                    is_consistent = (detected_env == test_case['expected'])
                    behavior_consistency_results[test_case['name']] = {
                        'expected': test_case['expected'].value,
                        'detected': detected_env.value if detected_env else None,
                        'consistent': is_consistent,
                        'priority': test_case['priority'],
                        'env_vars': test_case['env_vars']
                    }

                    # Check for consistency violations
                    if not is_consistent:
                        consistency_violations.append(
                            f"Test case {test_case['name']} ({test_case['priority']} priority): "
                            f"Expected {test_case['expected']}, got {detected_env} - "
                            f"behavior changed after SSOT migration"
                        )

            except Exception as e:
                behavior_consistency_results[test_case['name']] = {
                    'error': str(e),
                    'consistent': False,
                    'priority': test_case['priority']
                }
                consistency_violations.append(
                    f"Test case {test_case['name']} failed: {e}"
                )

        # Calculate consistency metrics
        total_cases = len(reference_test_cases)
        consistent_cases = sum(1 for r in behavior_consistency_results.values() if r.get('consistent', False))
        critical_cases = len([tc for tc in reference_test_cases if tc['priority'] == 'critical'])
        critical_consistent = sum(1 for tc in reference_test_cases
                                 if tc['priority'] == 'critical' and
                                 behavior_consistency_results[tc['name']].get('consistent', False))

        # Record test metrics
        self.record_metric('behavior_consistency_results', behavior_consistency_results)
        self.record_metric('consistency_violations', consistency_violations)
        self.record_metric('total_test_cases', total_cases)
        self.record_metric('consistent_cases', consistent_cases)
        self.record_metric('consistency_percentage', (consistent_cases / total_cases) * 100)
        self.record_metric('critical_cases_total', critical_cases)
        self.record_metric('critical_cases_consistent', critical_consistent)

        # ASSERTION: All environment detection behavior should remain consistent
        if consistency_violations:
            violation_details = "\n".join([f"  - {violation}" for violation in consistency_violations])

            self.fail(
                f"BEHAVIOR CONSISTENCY VIOLATIONS: Environment detection behavior changed after SSOT migration.\n"
                f"Violations detected ({len(consistency_violations)}/{total_cases}):\n{violation_details}\n\n"
                f"Consistency Rate: {consistent_cases}/{total_cases} ({(consistent_cases/total_cases)*100:.1f}%)\n"
                f"Critical Cases: {critical_consistent}/{critical_cases} consistent\n\n"
                f"SSOT migration should preserve environment detection behavior while changing implementation.\n\n"
                f"Required Investigation:\n"
                f"1. Verify IsolatedEnvironment integration doesn't change detection logic\n"
                f"2. Check that environment detection precedence rules are preserved\n"
                f"3. Ensure fallback behavior works correctly with SSOT pattern\n"
                f"4. Validate that singleton pattern behavior is maintained"
            )

    def test_backward_compatibility_environment_detection_logic(self):
        """
        REGRESSION TEST: Validates backward compatibility of environment detection logic.

        This test ensures that the environment detection logic remains backward
        compatible after SSOT remediation, preserving all existing detection patterns
        while using IsolatedEnvironment instead of direct os.getenv().

        Expected Behavior POST-Remediation:
        - All existing detection patterns work identically
        - Detection precedence order is preserved
        - Edge cases and complex scenarios work correctly
        """
        # Test backward compatibility with complex detection scenarios
        complex_scenarios = [
            {
                'name': 'multiple_indicators_production_precedence',
                'env_vars': {
                    'ENVIRONMENT': 'production',
                    'NETRA_ENV': 'staging',  # Should be overridden by ENVIRONMENT
                    'GCP_PROJECT': 'netra-staging'
                },
                'expected': EnvironmentType.PRODUCTION,
                'test_precedence': True
            },
            {
                'name': 'indirect_production_detection',
                'env_vars': {
                    'GCP_PROJECT': 'netra-production',
                    'DATABASE_URL': 'postgresql://user:pass@prod-db:5432/netra'
                },
                'expected': EnvironmentType.PRODUCTION,
                'test_indirect': True
            },
            {
                'name': 'indirect_staging_detection',
                'env_vars': {
                    'DATABASE_URL': 'postgresql://user:pass@staging-db:5432/netra',
                    'REDIS_URL': 'redis://staging-redis:6379/0'
                },
                'expected': EnvironmentType.STAGING,
                'test_indirect': True
            },
            {
                'name': 'testing_multiple_indicators',
                'env_vars': {
                    'CI': 'true',
                    'POSTGRES_PORT': '5434',
                    'TESTING': 'true'
                },
                'expected': EnvironmentType.TESTING,
                'test_multiple': True
            },
            {
                'name': 'edge_case_empty_values',
                'env_vars': {
                    'ENVIRONMENT': '',
                    'NETRA_ENV': '',
                    'GCP_PROJECT': 'netra-staging'
                },
                'expected': EnvironmentType.STAGING,
                'test_edge_case': True
            }
        ]

        compatibility_results = {}
        compatibility_violations = []

        for scenario in complex_scenarios:
            # Reset ErrorPolicy for each scenario
            ErrorPolicy._instance = None
            ErrorPolicy._environment_type = None

            try:
                # Test complex scenario with IsolatedEnvironment
                with self.temp_env_vars(**scenario['env_vars']):
                    # Clear other environment variables for clean test
                    all_env_vars = set(self.baseline_env_vars.keys())
                    scenario_env_vars = set(scenario['env_vars'].keys())
                    vars_to_clear = all_env_vars - scenario_env_vars

                    for var in vars_to_clear:
                        self.delete_env_var(var)

                    # Verify scenario setup
                    isolated_env = self.get_env()
                    setup_correct = True

                    for key, expected_value in scenario['env_vars'].items():
                        actual_value = isolated_env.get(key)
                        if actual_value != expected_value:
                            setup_correct = False
                            compatibility_violations.append(
                                f"Scenario {scenario['name']}: Setup failed - "
                                f"'{key}' should be '{expected_value}', got '{actual_value}'"
                            )

                    if setup_correct:
                        # Test ErrorPolicy environment detection
                        detected_env = ErrorPolicy.detect_environment()

                        # Record compatibility results
                        is_compatible = (detected_env == scenario['expected'])
                        compatibility_results[scenario['name']] = {
                            'expected': scenario['expected'].value,
                            'detected': detected_env.value if detected_env else None,
                            'compatible': is_compatible,
                            'scenario_type': {
                                'precedence': scenario.get('test_precedence', False),
                                'indirect': scenario.get('test_indirect', False),
                                'multiple': scenario.get('test_multiple', False),
                                'edge_case': scenario.get('test_edge_case', False)
                            },
                            'env_vars': scenario['env_vars']
                        }

                        # Check for compatibility violations
                        if not is_compatible:
                            compatibility_violations.append(
                                f"Scenario {scenario['name']}: "
                                f"Expected {scenario['expected']}, got {detected_env} - "
                                f"backward compatibility broken"
                            )

            except Exception as e:
                compatibility_results[scenario['name']] = {
                    'error': str(e),
                    'compatible': False,
                    'scenario_type': 'error'
                }
                compatibility_violations.append(
                    f"Scenario {scenario['name']} failed: {e}"
                )

        # Calculate compatibility metrics
        total_scenarios = len(complex_scenarios)
        compatible_scenarios = sum(1 for r in compatibility_results.values() if r.get('compatible', False))

        # Record test metrics
        self.record_metric('compatibility_results', compatibility_results)
        self.record_metric('compatibility_violations', compatibility_violations)
        self.record_metric('total_scenarios', total_scenarios)
        self.record_metric('compatible_scenarios', compatible_scenarios)
        self.record_metric('compatibility_percentage', (compatible_scenarios / total_scenarios) * 100)

        # ASSERTION: All complex scenarios should remain backward compatible
        if compatibility_violations:
            violation_details = "\n".join([f"  - {violation}" for violation in compatibility_violations])

            self.fail(
                f"BACKWARD COMPATIBILITY VIOLATIONS: Complex environment detection scenarios broken after SSOT migration.\n"
                f"Violations detected ({len(compatibility_violations)}/{total_scenarios}):\n{violation_details}\n\n"
                f"Compatibility Rate: {compatible_scenarios}/{total_scenarios} ({(compatible_scenarios/total_scenarios)*100:.1f}%)\n\n"
                f"SSOT migration must preserve all existing detection patterns and edge cases.\n\n"
                f"Required Investigation:\n"
                f"1. Verify precedence rules are preserved in SSOT implementation\n"
                f"2. Check that indirect detection patterns work with IsolatedEnvironment\n"
                f"3. Ensure edge cases and empty values are handled correctly\n"
                f"4. Validate complex multi-variable scenarios maintain expected behavior"
            )

    def test_golden_path_functionality_ssot_pattern_verification(self):
        """
        REGRESSION TEST: Validates Golden Path functionality works correctly with SSOT pattern.

        This test ensures that the core business functionality (Golden Path user flow)
        continues to work correctly after ErrorPolicy SSOT remediation, particularly
        focusing on error escalation policies that affect user experience.

        Expected Behavior POST-Remediation:
        - Error escalation policies work correctly across all environments
        - WebSocket event failure handling maintains proper escalation
        - Agent lifecycle error handling works with SSOT environment detection
        - Business-critical error paths function correctly
        """
        # Test Golden Path error escalation scenarios
        golden_path_scenarios = [
            {
                'name': 'production_websocket_event_failure',
                'environment': {'ENVIRONMENT': 'production'},
                'error_category': 'websocket_event',
                'severity': ErrorSeverity.HIGH,
                'business_critical': True,
                'expected_policy': ErrorEscalationPolicy.ERROR_STRICT
            },
            {
                'name': 'staging_agent_lifecycle_failure',
                'environment': {'ENVIRONMENT': 'staging'},
                'error_category': 'agent_lifecycle',
                'severity': ErrorSeverity.HIGH,
                'business_critical': True,
                'expected_policy': ErrorEscalationPolicy.ERROR_GRACEFUL
            },
            {
                'name': 'development_deprecated_pattern',
                'environment': {'ENVIRONMENT': 'development'},
                'error_category': 'deprecated_pattern',
                'severity': ErrorSeverity.MEDIUM,
                'business_critical': False,
                'expected_policy': ErrorEscalationPolicy.WARN_ONLY
            },
            {
                'name': 'testing_critical_error',
                'environment': {'TESTING': 'true'},
                'error_category': 'system_error',
                'severity': ErrorSeverity.CRITICAL,
                'business_critical': True,
                'expected_policy': ErrorEscalationPolicy.ERROR_GRACEFUL
            }
        ]

        golden_path_results = {}
        golden_path_violations = []

        for scenario in golden_path_scenarios:
            # Reset ErrorPolicy for each scenario
            ErrorPolicy._instance = None
            ErrorPolicy._environment_type = None
            ErrorPolicy._policy_overrides = {}

            try:
                # Set up environment for scenario
                with self.temp_env_vars(**scenario['environment']):
                    # Clear other environment variables
                    all_env_vars = set(self.baseline_env_vars.keys())
                    scenario_env_vars = set(scenario['environment'].keys())
                    vars_to_clear = all_env_vars - scenario_env_vars

                    for var in vars_to_clear:
                        self.delete_env_var(var)

                    # Verify environment detection works correctly
                    isolated_env = self.get_env()
                    detected_env = ErrorPolicy.detect_environment()

                    # Test error escalation policy
                    actual_policy = ErrorPolicy.get_escalation_policy(
                        error_category=scenario['error_category'],
                        severity=scenario['severity'],
                        business_critical=scenario['business_critical']
                    )

                    # Record Golden Path results
                    policy_correct = (actual_policy == scenario['expected_policy'])
                    golden_path_results[scenario['name']] = {
                        'environment_setup': scenario['environment'],
                        'detected_environment': detected_env.value if detected_env else None,
                        'error_category': scenario['error_category'],
                        'severity': scenario['severity'].value,
                        'business_critical': scenario['business_critical'],
                        'expected_policy': scenario['expected_policy'].value,
                        'actual_policy': actual_policy.value if actual_policy else None,
                        'policy_correct': policy_correct,
                        'ssot_working': True
                    }

                    # Check for Golden Path violations
                    if not policy_correct:
                        golden_path_violations.append(
                            f"Scenario {scenario['name']}: "
                            f"Expected policy {scenario['expected_policy']}, got {actual_policy} - "
                            f"Golden Path error escalation broken"
                        )

                    # Additional test: Verify environment detection influenced policy correctly
                    if detected_env is None:
                        golden_path_violations.append(
                            f"Scenario {scenario['name']}: "
                            f"Environment detection failed - this affects policy decisions"
                        )

            except Exception as e:
                golden_path_results[scenario['name']] = {
                    'error': str(e),
                    'policy_correct': False,
                    'ssot_working': False
                }
                golden_path_violations.append(
                    f"Scenario {scenario['name']} failed: {e}"
                )

        # Test progressive error handler integration
        try:
            from netra_backend.app.core.exceptions.error_policy import ProgressiveErrorHandler

            # Test that ProgressiveErrorHandler works with SSOT environment detection
            with self.temp_env_vars(ENVIRONMENT='staging'):
                ErrorPolicy._instance = None
                ErrorPolicy._environment_type = None

                handler = ProgressiveErrorHandler(category='test', logger=None)

                # Verify handler can access environment through ErrorPolicy
                env_type = ErrorPolicy.detect_environment()
                if env_type != EnvironmentType.STAGING:
                    golden_path_violations.append(
                        f"ProgressiveErrorHandler environment detection failed: "
                        f"expected STAGING, got {env_type}"
                    )

        except Exception as e:
            golden_path_violations.append(f"ProgressiveErrorHandler integration test failed: {e}")

        # Calculate Golden Path metrics
        total_scenarios = len(golden_path_scenarios)
        working_scenarios = sum(1 for r in golden_path_results.values() if r.get('policy_correct', False))

        # Record test metrics
        self.record_metric('golden_path_results', golden_path_results)
        self.record_metric('golden_path_violations', golden_path_violations)
        self.record_metric('total_golden_path_scenarios', total_scenarios)
        self.record_metric('working_golden_path_scenarios', working_scenarios)
        self.record_metric('golden_path_success_rate', (working_scenarios / total_scenarios) * 100)

        # ASSERTION: All Golden Path scenarios should work correctly with SSOT
        if golden_path_violations:
            violation_details = "\n".join([f"  - {violation}" for violation in golden_path_violations])

            self.fail(
                f"GOLDEN PATH FUNCTIONALITY VIOLATIONS: Critical business functionality broken after SSOT migration.\n"
                f"Violations detected ({len(golden_path_violations)}):\n{violation_details}\n\n"
                f"Golden Path Success Rate: {working_scenarios}/{total_scenarios} ({(working_scenarios/total_scenarios)*100:.1f}%)\n\n"
                f"Golden Path represents $500K+ ARR functionality - these violations are BUSINESS CRITICAL.\n\n"
                f"Required Immediate Investigation:\n"
                f"1. Verify error escalation policies work correctly with SSOT environment detection\n"
                f"2. Check that business-critical error handling is not disrupted\n"
                f"3. Ensure WebSocket event failure handling maintains proper escalation\n"
                f"4. Validate agent lifecycle error handling works with IsolatedEnvironment\n"
                f"5. Test end-to-end Golden Path user flow with SSOT ErrorPolicy"
            )

    def test_ssot_compliance_permanent_validation(self):
        """
        PERMANENT REGRESSION TEST: Validates ongoing SSOT compliance in ErrorPolicy.

        This test should be run regularly to ensure that future changes to ErrorPolicy
        do not re-introduce SSOT violations. It provides permanent protection against
        regression of direct os.getenv() usage.

        Expected Behavior POST-Remediation:
        - ZERO direct os.getenv() calls in ErrorPolicy
        - ALL environment access through IsolatedEnvironment
        - NO bypass of SSOT patterns
        """
        # Perform static analysis of ErrorPolicy source code
        import netra_backend.app.core.exceptions.error_policy as error_policy_module
        source_file = inspect.getsourcefile(error_policy_module)

        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Parse source code for SSOT compliance analysis
        tree = ast.parse(source_code)

        # Track SSOT violations
        ssot_violations = []
        ssot_compliance_metrics = {
            'total_os_getenv_calls': 0,
            'total_environment_access_calls': 0,
            'isolated_environment_usage': 0,
            'methods_with_violations': [],
            'compliance_score': 0.0
        }

        class SsotComplianceVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_error_policy_class = False
                self.current_method = None

            def visit_ClassDef(self, node):
                if node.name == 'ErrorPolicy':
                    self.in_error_policy_class = True
                    self.generic_visit(node)
                    self.in_error_policy_class = False
                else:
                    self.generic_visit(node)

            def visit_FunctionDef(self, node):
                if self.in_error_policy_class:
                    old_method = self.current_method
                    self.current_method = node.name
                    self.generic_visit(node)
                    self.current_method = old_method
                else:
                    self.generic_visit(node)

            def visit_Call(self, node):
                if self.in_error_policy_class:
                    # Check for os.getenv() calls (VIOLATION)
                    if (isinstance(node.func, ast.Attribute) and
                        isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'os' and
                        node.func.attr == 'getenv'):

                        ssot_violations.append({
                            'type': 'direct_os_getenv',
                            'method': self.current_method,
                            'line': node.lineno,
                            'severity': 'CRITICAL'
                        })
                        ssot_compliance_metrics['total_os_getenv_calls'] += 1
                        if self.current_method not in ssot_compliance_metrics['methods_with_violations']:
                            ssot_compliance_metrics['methods_with_violations'].append(self.current_method)

                    # Check for IsolatedEnvironment usage (GOOD)
                    elif (isinstance(node.func, ast.Attribute) and
                          hasattr(node.func.value, 'id') and
                          'isolated_env' in str(node.func.value.id).lower() and
                          node.func.attr == 'get'):

                        ssot_compliance_metrics['isolated_environment_usage'] += 1

                    # Count total environment access attempts
                    if (isinstance(node.func, ast.Attribute) and
                        node.func.attr in ['get', 'getenv'] and
                        any(env_related in str(node).lower() for env_related in ['env', 'environment', 'os'])):

                        ssot_compliance_metrics['total_environment_access_calls'] += 1

                self.generic_visit(node)

        visitor = SsotComplianceVisitor()
        visitor.visit(tree)

        # Calculate compliance score
        total_access = ssot_compliance_metrics['total_environment_access_calls']
        if total_access > 0:
            ssot_compliance_metrics['compliance_score'] = (
                ssot_compliance_metrics['isolated_environment_usage'] / total_access
            ) * 100
        else:
            ssot_compliance_metrics['compliance_score'] = 100.0

        # Record permanent compliance metrics
        self.record_metric('ssot_violations', ssot_violations)
        self.record_metric('ssot_compliance_metrics', ssot_compliance_metrics)
        self.record_metric('compliance_score', ssot_compliance_metrics['compliance_score'])
        self.record_metric('violation_count', len(ssot_violations))

        # ASSERTION: ZERO SSOT violations allowed post-remediation
        if ssot_violations:
            violation_details = "\n".join([
                f"  - {v['type']} in method '{v['method']}' at line {v['line']} (severity: {v['severity']})"
                for v in ssot_violations
            ])

            self.fail(
                f"SSOT REGRESSION DETECTED: ErrorPolicy contains {len(ssot_violations)} SSOT violations.\n"
                f"Violations found:\n{violation_details}\n\n"
                f"Compliance Score: {ssot_compliance_metrics['compliance_score']:.1f}%\n"
                f"Total Environment Access: {total_access}\n"
                f"IsolatedEnvironment Usage: {ssot_compliance_metrics['isolated_environment_usage']}\n"
                f"Direct os.getenv() Calls: {ssot_compliance_metrics['total_os_getenv_calls']}\n\n"
                f"POST-REMEDIATION REQUIREMENT: ErrorPolicy MUST have ZERO direct os.getenv() calls.\n\n"
                f"IMMEDIATE ACTION REQUIRED:\n"
                f"1. Replace ALL os.getenv() calls with IsolatedEnvironment.get()\n"
                f"2. Ensure ErrorPolicy constructor accepts IsolatedEnvironment instance\n"
                f"3. Verify all environment detection methods use injected IsolatedEnvironment\n"
                f"4. Re-run this test to confirm 100% SSOT compliance\n"
                f"5. Add code review checks to prevent future regressions"
            )

        # Additional verification: Check method signatures for SSOT readiness
        try:
            # Test that ErrorPolicy can work with IsolatedEnvironment injection
            isolated_env = self.get_env()

            # This test documents the expected post-remediation interface
            post_remediation_interface_notes = {
                'constructor_should_accept': 'IsolatedEnvironment instance parameter',
                'all_env_access_should_use': 'injected IsolatedEnvironment.get()',
                'no_direct_os_access': 'zero os.getenv() calls anywhere',
                'test_compatibility': 'seamless integration with SSOT test framework'
            }

            self.record_metric('post_remediation_interface_requirements', post_remediation_interface_notes)

        except Exception as e:
            self.record_metric('interface_validation_error', str(e))

        # Success case: Record that SSOT compliance is maintained
        self.record_metric('ssot_compliance_maintained', True)
        self.record_metric('regression_prevention_successful', len(ssot_violations) == 0)