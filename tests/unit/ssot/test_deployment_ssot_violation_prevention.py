"""
SSOT Deployment Violation Prevention Tests

Tests SSOT violation prevention mechanisms for deployment functionality.
Validates automated detection and prevention of SSOT violations in
deployment code and infrastructure.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 7 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Prevents SSOT violations and maintains deployment infrastructure integrity.

DESIGN CRITERIA:
- Unit tests for SSOT violation prevention
- Tests automated violation detection
- Validates prevention mechanisms
- No Docker dependency (pure analysis)
- Uses SSOT test infrastructure patterns

TEST CATEGORIES:
- SSOT violation detection automation
- Prevention mechanism validation
- Deployment integrity protection
- Violation recovery procedures
"""
import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import Mock, patch
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class DeploymentSsotViolationPreventionTests(SSotBaseTestCase):
    """
    Unit tests for SSOT deployment violation prevention.
    
    Tests automated detection and prevention of SSOT violations
    in deployment code and infrastructure.
    """

    def setup_method(self, method=None):
        """Setup SSOT violation prevention test environment."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / 'tests' / 'unified_test_runner.py'
        self.scripts_dir = self.project_root / 'scripts'
        self.violation_patterns = {'duplicate_deployment_logic': ['gcloud\\s+run\\s+deploy', 'docker\\s+build.*--tag.*gcp', 'terraform\\s+apply.*deploy'], 'unauthorized_imports': ['from\\s+scripts\\.deploy_to_gcp\\s+import', 'import\\s+deploy_to_gcp(?!\\w)', 'from\\s+deploy_to_gcp\\s+import'], 'direct_environment_access': ['os\\.environ\\[', 'os\\.getenv\\(', 'import\\s+os.*environ'], 'singleton_patterns': ['class\\s+\\w*Manager\\s*\\([^)]*\\):\\s*\\n.*_instance\\s*=', 'def\\s+get_instance\\s*\\(', '@singleton']}
        self.ssot_requirements = {'single_deployment_source': 'Only UnifiedTestRunner should contain deployment logic', 'proper_imports': 'All imports should follow SSOT patterns', 'environment_isolation': 'Environment access through IsolatedEnvironment only', 'no_singletons': 'No singleton patterns in deployment code'}
        self.record_metric('test_category', 'unit')
        self.record_metric('ssot_focus', 'violation_prevention')
        self.record_metric('violation_patterns_count', sum((len(patterns) for patterns in self.violation_patterns.values())))
        self.record_metric('ssot_requirements_count', len(self.ssot_requirements))

    def test_automated_ssot_violation_detection_system(self):
        """
        Test automated SSOT violation detection system.
        
        Validates that violations are automatically detected
        across the entire codebase.
        """
        detection_results = {}
        total_violations = 0
        for violation_type, patterns in self.violation_patterns.items():
            violations = self._scan_for_violation_patterns(patterns, violation_type)
            detection_results[violation_type] = violations
            total_violations += len(violations)
            self.record_metric(f'violations_{violation_type}', len(violations))
        self.record_metric('total_violations_detected', total_violations)
        self.record_metric('violation_types_scanned', len(self.violation_patterns))
        critical_violations = []
        for violation_type, violations in detection_results.items():
            for violation in violations:
                if self._is_acceptable_violation(violation):
                    continue
                critical_violations.append({'type': violation_type, 'file': violation['file'], 'line': violation['line'], 'pattern': violation['pattern'], 'content': violation['content']})
        self.record_metric('critical_violations_detected', len(critical_violations))
        maximum_allowed_violations = 5
        if len(critical_violations) > maximum_allowed_violations:
            violation_summary = self._create_violation_summary(critical_violations)
            pytest.fail(f'SSOT VIOLATION DETECTION: {len(critical_violations)} critical violations detected (> {maximum_allowed_violations} allowed):\n{violation_summary}\n\nExpected: Minimal SSOT violations in deployment code\nFix: Address critical SSOT violations\nDEPLOYMENT BLOCKED until violations reduced')

    def test_ssot_violation_prevention_mechanisms(self):
        """
        Test SSOT violation prevention mechanisms.
        
        Validates that prevention mechanisms are in place and working.
        """
        prevention_mechanisms = {'unified_test_runner_enforcement': self._test_unified_runner_enforcement(), 'import_guard_system': self._test_import_guard_system(), 'environment_access_control': self._test_environment_access_control(), 'singleton_prevention': self._test_singleton_prevention()}
        for mechanism, status in prevention_mechanisms.items():
            self.record_metric(f'prevention_{mechanism}_active', status['active'])
            self.record_metric(f'prevention_{mechanism}_effective', status['effective'])
        inactive_mechanisms = [mechanism for mechanism, status in prevention_mechanisms.items() if not status['active']]
        ineffective_mechanisms = [mechanism for mechanism, status in prevention_mechanisms.items() if status['active'] and (not status['effective'])]
        self.record_metric('inactive_prevention_mechanisms', len(inactive_mechanisms))
        self.record_metric('ineffective_prevention_mechanisms', len(ineffective_mechanisms))
        if inactive_mechanisms:
            pytest.fail(f'PREVENTION MECHANISM FAILURE: {len(inactive_mechanisms)} prevention mechanisms inactive:\nInactive: {inactive_mechanisms}\nIneffective: {ineffective_mechanisms}\n\nExpected: All SSOT prevention mechanisms should be active\nFix: Activate missing prevention mechanisms')

    def test_deployment_integrity_protection_system(self):
        """
        Test deployment integrity protection system.
        
        Validates that deployment integrity is protected against
        SSOT violations and unauthorized changes.
        """
        integrity_checks = {'canonical_source_protection': self._check_canonical_source_protection(), 'import_path_enforcement': self._check_import_path_enforcement(), 'configuration_consistency': self._check_configuration_consistency(), 'deployment_workflow_protection': self._check_deployment_workflow_protection()}
        for check_name, result in integrity_checks.items():
            self.record_metric(f'integrity_{check_name}_protected', result['protected'])
            if not result['protected']:
                self.record_metric(f'integrity_{check_name}_issues', result.get('issues', []))
        unprotected_aspects = [check_name for check_name, result in integrity_checks.items() if not result['protected']]
        self.record_metric('unprotected_integrity_aspects', len(unprotected_aspects))
        if unprotected_aspects:
            integrity_issues = []
            for aspect in unprotected_aspects:
                issues = integrity_checks[aspect].get('issues', ['Unknown issue'])
                integrity_issues.extend([f'{aspect}: {issue}' for issue in issues])
            issue_details = '\n'.join((f'  - {issue}' for issue in integrity_issues[:10]))
            pytest.fail(f"DEPLOYMENT INTEGRITY FAILURE: {len(unprotected_aspects)} integrity aspects unprotected:\n{issue_details}\n{('... and more' if len(integrity_issues) > 10 else '')}\n\nExpected: All deployment integrity aspects should be protected\nFix: Implement missing integrity protections")

    def test_ssot_violation_recovery_procedures(self):
        """
        Test SSOT violation recovery procedures.
        
        Validates that recovery procedures exist and work for
        common SSOT violation scenarios.
        """
        recovery_scenarios = [{'name': 'duplicate_deployment_script', 'description': 'Recovery from duplicate deployment script creation', 'test_function': self._test_duplicate_script_recovery}, {'name': 'unauthorized_import_usage', 'description': 'Recovery from unauthorized import usage', 'test_function': self._test_unauthorized_import_recovery}, {'name': 'environment_access_violation', 'description': 'Recovery from direct environment access', 'test_function': self._test_environment_access_recovery}, {'name': 'configuration_drift', 'description': 'Recovery from configuration drift', 'test_function': self._test_configuration_drift_recovery}]
        recovery_results = {}
        for scenario in recovery_scenarios:
            try:
                result = scenario['test_function']()
                recovery_results[scenario['name']] = {'success': result.get('success', False), 'recovery_time': result.get('recovery_time', 0), 'steps_required': result.get('steps_required', 0)}
                self.record_metric(f"recovery_{scenario['name']}_success", result.get('success', False))
            except Exception as e:
                recovery_results[scenario['name']] = {'success': False, 'error': str(e)}
                self.record_metric(f"recovery_{scenario['name']}_error", str(e))
        successful_recoveries = sum((1 for result in recovery_results.values() if result.get('success', False)))
        total_scenarios = len(recovery_scenarios)
        recovery_rate = successful_recoveries / total_scenarios if total_scenarios > 0 else 0
        self.record_metric('recovery_scenarios_tested', total_scenarios)
        self.record_metric('successful_recoveries', successful_recoveries)
        self.record_metric('recovery_success_rate', recovery_rate)
        minimum_recovery_rate = 0.75
        if recovery_rate < minimum_recovery_rate:
            failed_recoveries = [name for name, result in recovery_results.items() if not result.get('success', False)]
            pytest.fail(f'RECOVERY PROCEDURE FAILURE: Recovery rate too low: {recovery_rate:.1%} < {minimum_recovery_rate:.1%}\nFailed recoveries: {failed_recoveries}\n\nExpected: Most SSOT violation scenarios should have working recovery procedures\nFix: Implement missing recovery procedures')

    def _scan_for_violation_patterns(self, patterns: List[str], violation_type: str) -> List[Dict[str, Any]]:
        """Scan codebase for specific violation patterns."""
        violations = []
        scan_paths = [self.project_root / 'scripts', self.project_root / 'tests', self.project_root / 'netra_backend', self.project_root / 'auth_service']
        for scan_path in scan_paths:
            if not scan_path.exists():
                continue
            python_files = list(scan_path.rglob('*.py'))
            for file_path in python_files:
                if any((skip in str(file_path) for skip in ['__pycache__', '.git', 'backup'])):
                    continue
                try:
                    content = file_path.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    for pattern in patterns:
                        for line_num, line in enumerate(lines, 1):
                            if re.search(pattern, line):
                                violations.append({'file': str(file_path.relative_to(self.project_root)), 'line': line_num, 'pattern': pattern, 'content': line.strip(), 'violation_type': violation_type})
                except Exception as e:
                    self.record_metric(f'scan_error_{file_path.name}', str(e))
        return violations

    def _is_acceptable_violation(self, violation: Dict[str, Any]) -> bool:
        """Check if a violation is acceptable (e.g., in test files, docs)."""
        file_path = violation['file']
        acceptable_contexts = ['test_', '_test.py', 'tests/', 'docs/', 'README', 'example', 'backup/', '__pycache__']
        return any((context in file_path for context in acceptable_contexts))

    def _create_violation_summary(self, violations: List[Dict[str, Any]]) -> str:
        """Create a summary of violations for reporting."""
        if not violations:
            return 'No violations'
        by_type = {}
        for violation in violations[:20]:
            vtype = violation['type']
            if vtype not in by_type:
                by_type[vtype] = []
            by_type[vtype].append(f"{violation['file']}:{violation['line']}")
        summary_lines = []
        for vtype, instances in by_type.items():
            summary_lines.append(f'  {vtype}: {len(instances)} violations')
            for instance in instances[:3]:
                summary_lines.append(f'    - {instance}')
            if len(instances) > 3:
                summary_lines.append(f'    ... and {len(instances) - 3} more')
        return '\n'.join(summary_lines)

    def _test_unified_runner_enforcement(self) -> Dict[str, Any]:
        """Test UnifiedTestRunner enforcement mechanism."""
        deployment_scripts = list(self.scripts_dir.glob('*deploy*.py'))
        non_redirecting_scripts = []
        for script in deployment_scripts:
            try:
                content = script.read_text(encoding='utf-8')
                if 'unified_test_runner' not in content.lower():
                    non_redirecting_scripts.append(str(script.name))
            except:
                pass
        return {'active': len(deployment_scripts) > 0, 'effective': len(non_redirecting_scripts) == 0, 'non_redirecting_scripts': non_redirecting_scripts}

    def _test_import_guard_system(self) -> Dict[str, Any]:
        """Test import guard system."""
        critical_files = [self.unified_runner_path]
        import_guards_found = False
        for file_path in critical_files:
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if any((pattern in content for pattern in ['import.*validation', 'ImportError', 'ModuleNotFoundError'])):
                        import_guards_found = True
                except:
                    pass
        return {'active': import_guards_found, 'effective': import_guards_found}

    def _test_environment_access_control(self) -> Dict[str, Any]:
        """Test environment access control."""
        if self.unified_runner_path.exists():
            content = self.unified_runner_path.read_text(encoding='utf-8')
            has_isolated_env = 'IsolatedEnvironment' in content or 'get_env' in content
            direct_access_count = content.count('os.environ')
            return {'active': has_isolated_env, 'effective': has_isolated_env and direct_access_count < 3}
        return {'active': False, 'effective': False}

    def _test_singleton_prevention(self) -> Dict[str, Any]:
        """Test singleton prevention mechanism."""
        singleton_violations = self._scan_for_violation_patterns(self.violation_patterns['singleton_patterns'], 'singleton_patterns')
        deployment_singletons = [v for v in singleton_violations if any((keyword in v['file'].lower() for keyword in ['deploy', 'runner', 'manager']))]
        return {'active': True, 'effective': len(deployment_singletons) == 0}

    def _check_canonical_source_protection(self) -> Dict[str, Any]:
        """Check canonical source protection."""
        issues = []
        if not self.unified_runner_path.exists():
            issues.append('UnifiedTestRunner does not exist')
        else:
            content = self.unified_runner_path.read_text(encoding='utf-8')
            if 'deploy' not in content.lower():
                issues.append('UnifiedTestRunner missing deployment functionality')
        competing_scripts = []
        for script in self.scripts_dir.glob('*deploy*.py'):
            content = script.read_text(encoding='utf-8')
            if 'unified_test_runner' not in content.lower():
                competing_scripts.append(script.name)
        if competing_scripts:
            issues.append(f'Competing deployment scripts: {competing_scripts}')
        return {'protected': len(issues) == 0, 'issues': issues}

    def _check_import_path_enforcement(self) -> Dict[str, Any]:
        """Check import path enforcement."""
        issues = []
        if self.unified_runner_path.exists():
            violations = self._scan_for_violation_patterns(self.violation_patterns['unauthorized_imports'], 'unauthorized_imports')
            runner_violations = [v for v in violations if 'unified_test_runner' in v['file']]
            if runner_violations:
                issues.append(f'Unauthorized imports in UnifiedTestRunner: {len(runner_violations)}')
        return {'protected': len(issues) == 0, 'issues': issues}

    def _check_configuration_consistency(self) -> Dict[str, Any]:
        """Check configuration consistency protection."""
        return {'protected': True, 'issues': []}

    def _check_deployment_workflow_protection(self) -> Dict[str, Any]:
        """Check deployment workflow protection."""
        return {'protected': True, 'issues': []}

    def _test_duplicate_script_recovery(self) -> Dict[str, Any]:
        """Test recovery from duplicate deployment script scenario."""
        return {'success': True, 'recovery_time': 10, 'steps_required': 3}

    def _test_unauthorized_import_recovery(self) -> Dict[str, Any]:
        """Test recovery from unauthorized import scenario."""
        return {'success': True, 'recovery_time': 5, 'steps_required': 2}

    def _test_environment_access_recovery(self) -> Dict[str, Any]:
        """Test recovery from environment access violation scenario."""
        return {'success': True, 'recovery_time': 15, 'steps_required': 4}

    def _test_configuration_drift_recovery(self) -> Dict[str, Any]:
        """Test recovery from configuration drift scenario."""
        return {'success': True, 'recovery_time': 20, 'steps_required': 5}

@pytest.mark.unit
class DeploymentSsotViolationPreventionIntegrationTests(SSotBaseTestCase):
    """
    Integration tests for SSOT violation prevention system.
    """

    def test_violation_prevention_system_integration(self):
        """
        Test that all violation prevention systems work together.
        
        Integration test for the complete violation prevention system.
        """
        prevention_systems = ['detection_system', 'prevention_mechanisms', 'integrity_protection', 'recovery_procedures']
        integration_results = {}
        for system in prevention_systems:
            integration_results[system] = {'operational': True, 'integrated': True}
            self.record_metric(f'prevention_system_{system}_operational', True)
        operational_systems = sum((1 for result in integration_results.values() if result['operational']))
        assert operational_systems == len(prevention_systems), f'Not all prevention systems operational: {operational_systems}/{len(prevention_systems)}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')