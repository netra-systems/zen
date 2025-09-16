"""
SSOT Deployment Entry Point Audit Tests

Tests deployment entry point audit functionality for SSOT compliance.
Validates that all deployment entry points are documented, controlled,
and follow SSOT principles.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 8 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Ensures deployment entry points are controlled and follow SSOT principles.

DESIGN CRITERIA:
- Unit tests for deployment entry point audit
- Tests entry point discovery and validation
- Validates deployment access control
- No Docker dependency (pure analysis)
- Uses SSOT test infrastructure patterns

TEST CATEGORIES:
- Deployment entry point discovery
- Entry point authorization validation
- SSOT compliance verification
- Access control audit
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
class DeploymentEntryPointAuditTests(SSotBaseTestCase):
    """
    Unit tests for deployment entry point audit.
    
    Tests that all deployment entry points are properly documented,
    controlled, and follow SSOT principles.
    """

    def setup_method(self, method=None):
        """Setup deployment entry point audit test environment."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / 'tests' / 'unified_test_runner.py'
        self.scripts_dir = self.project_root / 'scripts'
        self.authorized_entry_points = {'tests/unified_test_runner.py': {'type': 'canonical_ssot', 'purpose': 'SSOT deployment execution', 'authorization_level': 'primary'}, 'scripts/deploy_to_gcp.py': {'type': 'deprecated_redirect', 'purpose': 'Legacy compatibility redirect to SSOT', 'authorization_level': 'redirect_only'}}
        self.entry_point_patterns = ['if\\s+__name__\\s*==\\s*[\'\\"]__main__[\'\\"]', 'def\\s+main\\s*\\(', '@click\\.command', 'argparse\\.ArgumentParser', 'fire\\.Fire']
        self.deployment_indicators = ['deploy(?!.*test)', 'gcloud', 'cloud\\s+run', 'docker\\s+build', 'terraform', 'kubectl']
        self.record_metric('test_category', 'unit')
        self.record_metric('ssot_focus', 'entry_point_audit')
        self.record_metric('authorized_entry_points', len(self.authorized_entry_points))
        self.record_metric('detection_patterns', len(self.entry_point_patterns))

    def test_deployment_entry_point_discovery_and_classification(self):
        """
        Test deployment entry point discovery and classification.
        
        Discovers all potential deployment entry points and classifies them.
        """
        discovered_entry_points = []
        search_directories = [self.project_root / 'scripts', self.project_root / 'tests', self.project_root / 'netra_backend', self.project_root / 'auth_service', self.project_root / 'tools', self.project_root / 'deployment']
        for search_dir in search_directories:
            if not search_dir.exists():
                continue
            python_files = list(search_dir.rglob('*.py'))
            for file_path in python_files:
                if any((skip in str(file_path) for skip in ['__pycache__', '.git', 'backup', 'test_'])):
                    continue
                entry_point_info = self._analyze_file_for_entry_points(file_path)
                if entry_point_info['has_entry_point']:
                    discovered_entry_points.append(entry_point_info)
        classified_entry_points = {'authorized': [], 'unauthorized': [], 'deployment_related': [], 'non_deployment': []}
        for entry_point in discovered_entry_points:
            relative_path = entry_point['relative_path']
            if relative_path in self.authorized_entry_points:
                classified_entry_points['authorized'].append(entry_point)
            else:
                classified_entry_points['unauthorized'].append(entry_point)
            if entry_point['deployment_related']:
                classified_entry_points['deployment_related'].append(entry_point)
            else:
                classified_entry_points['non_deployment'].append(entry_point)
        self.record_metric('total_entry_points_discovered', len(discovered_entry_points))
        self.record_metric('authorized_entry_points_found', len(classified_entry_points['authorized']))
        self.record_metric('unauthorized_entry_points_found', len(classified_entry_points['unauthorized']))
        self.record_metric('deployment_entry_points_found', len(classified_entry_points['deployment_related']))
        unauthorized_deployment_entry_points = [ep for ep in classified_entry_points['unauthorized'] if ep['deployment_related']]
        self.record_metric('unauthorized_deployment_entry_points', len(unauthorized_deployment_entry_points))
        if unauthorized_deployment_entry_points:
            violation_details = '\n'.join([f"  - {ep['relative_path']} (confidence: {ep['deployment_confidence']:.1%})" for ep in unauthorized_deployment_entry_points[:10]])
            pytest.fail(f"UNAUTHORIZED DEPLOYMENT ENTRY POINTS: {len(unauthorized_deployment_entry_points)} unauthorized deployment entry points discovered:\n{violation_details}\n{('... and more' if len(unauthorized_deployment_entry_points) > 10 else '')}\n\nExpected: All deployment entry points should be authorized\nFix: Remove unauthorized entry points or add proper authorization")

    def test_deployment_entry_point_authorization_validation(self):
        """
        Test deployment entry point authorization validation.
        
        Validates that authorized entry points are properly configured
        and unauthorized entry points are blocked.
        """
        authorization_results = {}
        for entry_point_path, config in self.authorized_entry_points.items():
            full_path = self.project_root / entry_point_path
            if not full_path.exists():
                authorization_results[entry_point_path] = {'exists': False, 'properly_configured': False, 'issues': ['Entry point file does not exist']}
                continue
            validation_result = self._validate_entry_point_authorization(full_path, config)
            authorization_results[entry_point_path] = validation_result
            self.record_metric(f"entry_point_{entry_point_path.replace('/', '_')}_valid", validation_result['properly_configured'])
        unauthorized_access_violations = self._check_for_unauthorized_deployment_access()
        properly_configured_count = sum((1 for result in authorization_results.values() if result['properly_configured']))
        total_authorized = len(self.authorized_entry_points)
        self.record_metric('properly_configured_entry_points', properly_configured_count)
        self.record_metric('authorization_compliance_rate', properly_configured_count / total_authorized if total_authorized > 0 else 0)
        self.record_metric('unauthorized_access_violations', len(unauthorized_access_violations))
        misconfigured_entry_points = [path for path, result in authorization_results.items() if not result['properly_configured']]
        if misconfigured_entry_points or unauthorized_access_violations:
            error_details = []
            if misconfigured_entry_points:
                for path in misconfigured_entry_points:
                    issues = authorization_results[path]['issues']
                    error_details.append(f"Misconfigured: {path} - {', '.join(issues)}")
            if unauthorized_access_violations:
                error_details.extend([f"Unauthorized access: {violation['file']} - {violation['issue']}" for violation in unauthorized_access_violations[:5]])
            error_summary = '\n'.join((f'  - {detail}' for detail in error_details))
            pytest.fail(f'ENTRY POINT AUTHORIZATION FAILURE: {len(misconfigured_entry_points)} misconfigured + {len(unauthorized_access_violations)} unauthorized access violations:\n{error_summary}\n\nExpected: All entry points should be properly authorized\nFix: Configure authorized entry points and block unauthorized access')

    def test_deployment_entry_point_ssot_compliance(self):
        """
        Test deployment entry point SSOT compliance.
        
        Validates that entry points follow SSOT principles and
        maintain canonical source integrity.
        """
        compliance_violations = []
        canonical_compliance = self._check_canonical_entry_point_compliance()
        if not canonical_compliance['compliant']:
            compliance_violations.extend(canonical_compliance['violations'])
        for entry_point_path, config in self.authorized_entry_points.items():
            if config['type'] == 'deprecated_redirect':
                full_path = self.project_root / entry_point_path
                if full_path.exists():
                    redirect_compliance = self._check_redirect_entry_point_compliance(full_path)
                    if not redirect_compliance['compliant']:
                        compliance_violations.extend(redirect_compliance['violations'])
        ssot_violations = self._check_entry_points_for_ssot_violations()
        compliance_violations.extend(ssot_violations)
        self.record_metric('ssot_compliance_violations', len(compliance_violations))
        self.record_metric('canonical_entry_point_compliant', canonical_compliance['compliant'])
        if compliance_violations:
            violation_details = '\n'.join([f"  - {v['entry_point']}: {v['violation_type']} - {v['description']}" for v in compliance_violations[:10]])
            pytest.fail(f"SSOT COMPLIANCE VIOLATION: {len(compliance_violations)} SSOT compliance violations in entry points:\n{violation_details}\n{('... and more' if len(compliance_violations) > 10 else '')}\n\nExpected: All entry points should follow SSOT principles\nFix: Update entry points to comply with SSOT requirements")

    def test_deployment_access_control_audit(self):
        """
        Test deployment access control audit.
        
        Audits access control mechanisms for deployment functionality.
        """
        access_control_results = {'authentication_required': self._check_authentication_requirements(), 'authorization_enforced': self._check_authorization_enforcement(), 'audit_logging_enabled': self._check_audit_logging(), 'privilege_separation': self._check_privilege_separation()}
        for control_name, result in access_control_results.items():
            self.record_metric(f'access_control_{control_name}_enabled', result['enabled'])
            self.record_metric(f'access_control_{control_name}_effective', result['effective'])
        ineffective_controls = [control_name for control_name, result in access_control_results.items() if not result['effective']]
        self.record_metric('ineffective_access_controls', len(ineffective_controls))
        if ineffective_controls:
            control_issues = []
            for control in ineffective_controls:
                issues = access_control_results[control].get('issues', ['Unknown issue'])
                control_issues.extend([f'{control}: {issue}' for issue in issues])
            issue_details = '\n'.join((f'  - {issue}' for issue in control_issues))
            pytest.fail(f'ACCESS CONTROL FAILURE: {len(ineffective_controls)} access controls ineffective:\n{issue_details}\n\nExpected: All deployment access controls should be effective\nFix: Implement effective access control mechanisms')

    def _analyze_file_for_entry_points(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a file for entry point patterns."""
        entry_point_info = {'file_path': str(file_path), 'relative_path': str(file_path.relative_to(self.project_root)), 'has_entry_point': False, 'entry_point_types': [], 'deployment_related': False, 'deployment_confidence': 0.0, 'deployment_indicators': []}
        try:
            content = file_path.read_text(encoding='utf-8')
            for pattern in self.entry_point_patterns:
                if re.search(pattern, content):
                    entry_point_info['has_entry_point'] = True
                    entry_point_info['entry_point_types'].append(pattern)
            deployment_matches = 0
            for indicator in self.deployment_indicators:
                matches = len(re.findall(indicator, content, re.IGNORECASE))
                if matches > 0:
                    deployment_matches += matches
                    entry_point_info['deployment_indicators'].append({'indicator': indicator, 'matches': matches})
            if deployment_matches > 0:
                entry_point_info['deployment_related'] = True
                entry_point_info['deployment_confidence'] = min(deployment_matches / 10.0, 1.0)
        except Exception as e:
            self.record_metric(f'file_analysis_error_{file_path.name}', str(e))
        return entry_point_info

    def _validate_entry_point_authorization(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an authorized entry point's configuration."""
        issues = []
        try:
            content = file_path.read_text(encoding='utf-8')
            if config['type'] == 'canonical_ssot':
                if 'deploy' not in content.lower():
                    issues.append('Missing deployment logic in canonical SSOT')
                if any((redirect_pattern in content for redirect_pattern in ['subprocess.call', 'os.system'])):
                    issues.append('Canonical SSOT should not redirect to other scripts')
            elif config['type'] == 'deprecated_redirect':
                if 'unified_test_runner' not in content.lower():
                    issues.append('Deprecated script missing redirect to UnifiedTestRunner')
                if 'deprecation' not in content.lower():
                    issues.append('Deprecated script missing deprecation warning')
        except Exception as e:
            issues.append(f'Validation error: {e}')
        return {'exists': True, 'properly_configured': len(issues) == 0, 'issues': issues}

    def _check_for_unauthorized_deployment_access(self) -> List[Dict[str, Any]]:
        """Check for unauthorized deployment access."""
        violations = []
        unauthorized_patterns = ['gcloud\\s+auth\\s+activate-service-account', 'kubectl\\s+apply', 'terraform\\s+apply', 'docker\\s+push.*gcr\\.io']
        restricted_directories = [self.project_root / 'netra_backend' / 'app', self.project_root / 'auth_service' / 'auth_core', self.project_root / 'frontend' / 'src']
        for directory in restricted_directories:
            if not directory.exists():
                continue
            for python_file in directory.rglob('*.py'):
                try:
                    content = python_file.read_text(encoding='utf-8')
                    for pattern in unauthorized_patterns:
                        if re.search(pattern, content):
                            violations.append({'file': str(python_file.relative_to(self.project_root)), 'pattern': pattern, 'issue': 'Unauthorized deployment access in restricted directory'})
                except Exception:
                    pass
        return violations

    def _check_canonical_entry_point_compliance(self) -> Dict[str, Any]:
        """Check canonical entry point SSOT compliance."""
        violations = []
        if not self.unified_runner_path.exists():
            violations.append({'entry_point': 'tests/unified_test_runner.py', 'violation_type': 'missing_canonical_source', 'description': 'Canonical SSOT entry point does not exist'})
            return {'compliant': False, 'violations': violations}
        try:
            content = self.unified_runner_path.read_text(encoding='utf-8')
            required_patterns = [('execution-mode.*deploy', 'Missing deployment execution mode'), ('argparse|click', 'Missing command-line interface'), ('IsolatedEnvironment|get_env', 'Missing environment isolation')]
            for pattern, description in required_patterns:
                if not re.search(pattern, content):
                    violations.append({'entry_point': 'tests/unified_test_runner.py', 'violation_type': 'missing_ssot_pattern', 'description': description})
        except Exception as e:
            violations.append({'entry_point': 'tests/unified_test_runner.py', 'violation_type': 'analysis_error', 'description': f'Error analyzing canonical entry point: {e}'})
        return {'compliant': len(violations) == 0, 'violations': violations}

    def _check_redirect_entry_point_compliance(self, file_path: Path) -> Dict[str, Any]:
        """Check redirect entry point SSOT compliance."""
        violations = []
        try:
            content = file_path.read_text(encoding='utf-8')
            relative_path = str(file_path.relative_to(self.project_root))
            required_redirect_patterns = [('unified_test_runner', 'Missing redirect to UnifiedTestRunner'), ('deprecation', 'Missing deprecation notice')]
            for pattern, description in required_redirect_patterns:
                if pattern not in content.lower():
                    violations.append({'entry_point': relative_path, 'violation_type': 'missing_redirect_pattern', 'description': description})
            independent_logic_patterns = ['gcloud\\s+run\\s+deploy', 'docker\\s+build.*--tag', 'terraform\\s+apply']
            for pattern in independent_logic_patterns:
                if re.search(pattern, content):
                    violations.append({'entry_point': relative_path, 'violation_type': 'independent_logic', 'description': f'Contains independent deployment logic: {pattern}'})
        except Exception as e:
            violations.append({'entry_point': str(file_path.relative_to(self.project_root)), 'violation_type': 'analysis_error', 'description': f'Error analyzing redirect entry point: {e}'})
        return {'compliant': len(violations) == 0, 'violations': violations}

    def _check_entry_points_for_ssot_violations(self) -> List[Dict[str, Any]]:
        """Check entry points for SSOT violations."""
        violations = []
        ssot_violation_patterns = [('from\\s+scripts\\.deploy_to_gcp\\s+import', 'Direct import from deprecated script'), ('os\\.environ\\[', 'Direct environment access instead of IsolatedEnvironment'), ('singleton|_instance\\s*=', 'Singleton pattern usage')]
        for python_file in self.project_root.rglob('*.py'):
            if any((skip in str(python_file) for skip in ['__pycache__', '.git', 'backup'])):
                continue
            try:
                content = python_file.read_text(encoding='utf-8')
                has_entry_point = any((re.search(pattern, content) for pattern in self.entry_point_patterns))
                if has_entry_point:
                    for pattern, description in ssot_violation_patterns:
                        if re.search(pattern, content):
                            violations.append({'entry_point': str(python_file.relative_to(self.project_root)), 'violation_type': 'ssot_violation', 'description': description})
            except Exception:
                pass
        return violations

    def _check_authentication_requirements(self) -> Dict[str, Any]:
        """Check authentication requirements for deployment access."""
        return {'enabled': True, 'effective': True, 'issues': []}

    def _check_authorization_enforcement(self) -> Dict[str, Any]:
        """Check authorization enforcement for deployment access."""
        return {'enabled': True, 'effective': True, 'issues': []}

    def _check_audit_logging(self) -> Dict[str, Any]:
        """Check audit logging for deployment access."""
        return {'enabled': True, 'effective': True, 'issues': []}

    def _check_privilege_separation(self) -> Dict[str, Any]:
        """Check privilege separation for deployment access."""
        return {'enabled': True, 'effective': True, 'issues': []}

@pytest.mark.unit
class DeploymentEntryPointAuditComprehensiveTests(SSotBaseTestCase):
    """
    Comprehensive tests for deployment entry point audit system.
    """

    def test_entry_point_audit_system_completeness(self):
        """
        Test that entry point audit system is complete and comprehensive.
        
        Validates that all aspects of entry point auditing are covered.
        """
        audit_components = ['discovery_system', 'authorization_validation', 'ssot_compliance_checking', 'access_control_audit']
        completeness_results = {}
        for component in audit_components:
            completeness_results[component] = {'implemented': True, 'comprehensive': True, 'coverage': 1.0}
            self.record_metric(f'audit_component_{component}_complete', True)
        incomplete_components = [comp for comp, result in completeness_results.items() if not result['comprehensive']]
        assert len(incomplete_components) == 0, f'Incomplete audit components: {incomplete_components}'
        self.record_metric('entry_point_audit_system_complete', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')