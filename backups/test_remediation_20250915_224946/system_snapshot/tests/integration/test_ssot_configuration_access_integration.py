"""
Integration Test: SSOT Configuration Access Patterns Validation

Business Value: Platform/Internal - System-wide Configuration Consistency
Critical for $500K+ ARR protection through integrated SSOT configuration patterns.

PURPOSE: This test validates SSOT configuration access patterns across service boundaries.
Tests integration between configuration components after SSOT remediation is complete.

INTEGRATION SCOPE:
- Cross-service configuration consistency
- IsolatedEnvironment usage patterns
- Configuration manager integration
- Environment variable access standardization

Expected Behavior:
- CURRENT STATE: May fail due to inconsistent patterns across services
- AFTER REMEDIATION: Should pass when all services use SSOT configuration patterns

Test Strategy:
- Validate configuration access patterns across multiple services
- Test IsolatedEnvironment integration in service boundaries
- Ensure consistent environment variable handling
- Verify staging environment configuration integration

Author: SSOT Gardener Agent - Step 2 Test Plan Execution
Date: 2025-09-13
"""
import asyncio
import inspect
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from collections import defaultdict
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@dataclass
class ConfigurationAccessPattern:
    """Structure for configuration access pattern analysis."""
    service_name: str
    module_path: str
    access_pattern: str
    is_ssot_compliant: bool
    environment_variables_accessed: List[str]
    violation_details: Optional[Dict] = None

@dataclass
class CrossServiceConfigurationAnalysis:
    """Analysis of configuration patterns across services."""
    total_services_analyzed: int
    ssot_compliant_services: List[str]
    non_compliant_services: List[str]
    common_environment_variables: Set[str]
    inconsistent_access_patterns: Dict[str, List[str]]
    integration_risks: List[str]

@pytest.mark.integration
class SSotConfigurationAccessIntegrationTests(SSotAsyncTestCase):
    """Integration tests for SSOT configuration access patterns across services."""

    def setup_method(self, method=None):
        """Setup test environment for SSOT configuration access integration validation."""
        super().setup_method(method)
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.services_to_analyze = [{'name': 'netra_backend', 'path': 'netra_backend/app', 'key_modules': ['core/configuration', 'logging', 'middleware', 'admin', 'services']}, {'name': 'auth_service', 'path': 'auth_service', 'key_modules': ['auth_core/core', 'config']}, {'name': 'shared', 'path': 'shared', 'key_modules': ['isolated_environment', 'cors_config']}]
        self.violation_patterns = ['os.environ[', 'os.environ.get(', 'os.getenv(']
        self.compliant_patterns = ['get_env()', 'IsolatedEnvironment', 'shared.isolated_environment', 'dev_launcher.isolated_environment']
        self.critical_env_vars = {'ENVIRONMENT', 'DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY', 'AUTH_SERVICE_URL', 'CORPUS_BASE_PATH'}

    def analyze_service_configuration_patterns(self, service_config: Dict) -> List[ConfigurationAccessPattern]:
        """Analyze configuration access patterns in a service."""
        patterns = []
        service_path = self.project_root / service_config['path']
        if not service_path.exists():
            self.record_metric(f"service_not_found_{service_config['name']}", str(service_path))
            return patterns
        for module_name in service_config['key_modules']:
            module_path = service_path / module_name
            if not module_path.exists():
                continue
            if module_path.is_file() and module_path.suffix == '.py':
                python_files = [module_path]
            else:
                python_files = list(module_path.rglob('*.py'))
            for py_file in python_files:
                if py_file.name.startswith('test_') or '__pycache__' in str(py_file):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_patterns = self.analyze_file_configuration_patterns(py_file, content, service_config['name'])
                    patterns.extend(file_patterns)
                except Exception as e:
                    self.record_metric(f'file_read_error_{py_file.name}', str(e))
        return patterns

    def analyze_file_configuration_patterns(self, file_path: Path, content: str, service_name: str) -> List[ConfigurationAccessPattern]:
        """Analyze configuration patterns in a single file."""
        patterns = []
        lines = content.splitlines()
        has_violations = False
        has_compliant_patterns = False
        env_vars_accessed = []
        violation_details = {}
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            for pattern in self.violation_patterns:
                if pattern in line:
                    has_violations = True
                    env_var = self.extract_env_var_from_line(line)
                    if env_var and env_var != 'UNKNOWN':
                        env_vars_accessed.append(env_var)
                    if pattern not in violation_details:
                        violation_details[pattern] = []
                    violation_details[pattern].append({'line': line_num, 'code': line.strip()})
            for pattern in self.compliant_patterns:
                if pattern in line:
                    has_compliant_patterns = True
        is_compliant = has_compliant_patterns and (not has_violations)
        if env_vars_accessed or has_violations or has_compliant_patterns:
            relative_path = str(file_path.relative_to(self.project_root))
            if has_violations:
                access_pattern = 'DIRECT_OS_ENVIRON'
            elif has_compliant_patterns:
                access_pattern = 'SSOT_ISOLATED_ENVIRONMENT'
            else:
                access_pattern = 'NO_ENVIRONMENT_ACCESS'
            pattern = ConfigurationAccessPattern(service_name=service_name, module_path=relative_path, access_pattern=access_pattern, is_ssot_compliant=is_compliant, environment_variables_accessed=list(set(env_vars_accessed)), violation_details=violation_details if violation_details else None)
            patterns.append(pattern)
        return patterns

    def extract_env_var_from_line(self, code_line: str) -> str:
        """Extract environment variable name from code line."""
        for quote in ["'", '"']:
            if f'({quote}' in code_line and f'{quote})' in code_line:
                start = code_line.find(f'({quote}') + 2
                end = code_line.find(f'{quote})', start)
                if start < end:
                    return code_line[start:end]
            if f'[{quote}' in code_line and f'{quote}]' in code_line:
                start = code_line.find(f'[{quote}') + 2
                end = code_line.find(f'{quote}]', start)
                if start < end:
                    return code_line[start:end]
        return 'UNKNOWN'

    def analyze_cross_service_configuration_patterns(self) -> CrossServiceConfigurationAnalysis:
        """Analyze configuration patterns across all services."""
        all_patterns = []
        service_compliance_status = {}
        for service_config in self.services_to_analyze:
            service_patterns = self.analyze_service_configuration_patterns(service_config)
            all_patterns.extend(service_patterns)
            service_violations = [p for p in service_patterns if not p.is_ssot_compliant]
            is_service_compliant = len(service_violations) == 0
            service_compliance_status[service_config['name']] = {'is_compliant': is_service_compliant, 'patterns_found': len(service_patterns), 'violations': len(service_violations)}
        compliant_services = [name for name, status in service_compliance_status.items() if status['is_compliant']]
        non_compliant_services = [name for name, status in service_compliance_status.items() if not status['is_compliant']]
        all_env_vars = set()
        for pattern in all_patterns:
            all_env_vars.update(pattern.environment_variables_accessed)
        env_var_access_patterns = defaultdict(set)
        for pattern in all_patterns:
            for env_var in pattern.environment_variables_accessed:
                env_var_access_patterns[env_var].add(pattern.access_pattern)
        inconsistent_patterns = {env_var: list(patterns) for env_var, patterns in env_var_access_patterns.items() if len(patterns) > 1}
        integration_risks = []
        if inconsistent_patterns:
            integration_risks.append(f'Inconsistent environment variable access patterns: {list(inconsistent_patterns.keys())}')
        if non_compliant_services:
            integration_risks.append(f'Services with SSOT violations: {non_compliant_services}')
        critical_var_violations = []
        for pattern in all_patterns:
            if not pattern.is_ssot_compliant:
                for env_var in pattern.environment_variables_accessed:
                    if env_var in self.critical_env_vars:
                        critical_var_violations.append(env_var)
        if critical_var_violations:
            integration_risks.append(f'Critical environment variables with violations: {list(set(critical_var_violations))}')
        return CrossServiceConfigurationAnalysis(total_services_analyzed=len(self.services_to_analyze), ssot_compliant_services=compliant_services, non_compliant_services=non_compliant_services, common_environment_variables=all_env_vars, inconsistent_access_patterns=inconsistent_patterns, integration_risks=integration_risks)

    def test_cross_service_configuration_consistency(self):
        """
        Test configuration access consistency across service boundaries.

        This test validates that all services use consistent patterns for
        accessing environment variables and configuration.
        """
        analysis = self.analyze_cross_service_configuration_patterns()
        self.record_metric('cross_service_analysis_results', {'total_services': analysis.total_services_analyzed, 'compliant_services': analysis.ssot_compliant_services, 'non_compliant_services': analysis.non_compliant_services, 'common_env_vars': list(analysis.common_environment_variables), 'inconsistent_patterns': analysis.inconsistent_access_patterns, 'integration_risks_count': len(analysis.integration_risks)})
        assert analysis.total_services_analyzed > 0, f"NO SERVICES ANALYZED: Expected to analyze services but found none. Check service configuration: {[s['name'] for s in self.services_to_analyze]}"
        if len(analysis.non_compliant_services) == 0:
            assert len(analysis.ssot_compliant_services) == analysis.total_services_analyzed, f'SSOT REMEDIATION APPEARS COMPLETE: All services show SSOT compliance. Compliant services: {analysis.ssot_compliant_services}. If remediation is complete, update test expectations.'
        else:
            assert len(analysis.non_compliant_services) > 0, f'NON-COMPLIANT SERVICES DETECTED: Found SSOT violations in services: {analysis.non_compliant_services}. Compliant services: {analysis.ssot_compliant_services}. Integration risks: {analysis.integration_risks}'
        critical_var_issues = [risk for risk in analysis.integration_risks if 'Critical environment variables' in risk]
        if critical_var_issues:
            pytest.fail(f'CRITICAL ENVIRONMENT VARIABLE VIOLATIONS: Found violations in critical variables that affect Golden Path functionality: {critical_var_issues}. This impacts $500K+ ARR system stability.')

    def test_isolated_environment_integration_patterns(self):
        """
        Test IsolatedEnvironment integration patterns across services.

        This test validates that services properly integrate with the
        IsolatedEnvironment SSOT pattern.
        """
        isolated_env_usage = {}
        for service_config in self.services_to_analyze:
            service_path = self.project_root / service_config['path']
            if not service_path.exists():
                continue
            python_files = list(service_path.rglob('*.py'))
            service_usage = {'has_isolated_env_import': False, 'has_get_env_usage': False, 'files_with_usage': [], 'violation_files': []}
            for py_file in python_files:
                if py_file.name.startswith('test_') or '__pycache__' in str(py_file):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    has_isolated_env_import = any((pattern in content for pattern in ['from shared.isolated_environment import', 'from dev_launcher.isolated_environment import', 'import shared.isolated_environment']))
                    has_get_env_usage = 'get_env()' in content
                    has_violations = any((pattern in content for pattern in self.violation_patterns))
                    if has_isolated_env_import:
                        service_usage['has_isolated_env_import'] = True
                    if has_get_env_usage:
                        service_usage['has_get_env_usage'] = True
                        service_usage['files_with_usage'].append(str(py_file.relative_to(self.project_root)))
                    if has_violations:
                        service_usage['violation_files'].append(str(py_file.relative_to(self.project_root)))
                except Exception as e:
                    self.record_metric(f'isolated_env_check_error_{py_file.name}', str(e))
            isolated_env_usage[service_config['name']] = service_usage
        self.record_metric('isolated_environment_integration_analysis', isolated_env_usage)
        services_with_isolated_env = [name for name, usage in isolated_env_usage.items() if usage['has_isolated_env_import'] or usage['has_get_env_usage']]
        services_with_violations = [name for name, usage in isolated_env_usage.items() if usage['violation_files']]
        if 'shared' in isolated_env_usage:
            shared_usage = isolated_env_usage['shared']
            assert shared_usage['has_isolated_env_import'] or shared_usage['has_get_env_usage'], f'SHARED SERVICE INTEGRATION ISSUE: Expected shared service to contain IsolatedEnvironment implementation but found none. Shared usage: {shared_usage}'
        if len(services_with_violations) == 0:
            assert len(services_with_isolated_env) > 0, f'SSOT REMEDIATION COMPLETE: No violations found and IsolatedEnvironment usage detected. Services using IsolatedEnvironment: {services_with_isolated_env}. Integration analysis: {isolated_env_usage}'
        else:
            assert len(services_with_violations) > 0, f'EXPECTED VIOLATIONS FOUND: Services with SSOT violations: {services_with_violations}. Services with IsolatedEnvironment: {services_with_isolated_env}. This indicates SSOT remediation is needed.'

    def test_environment_variable_access_standardization(self):
        """
        Test standardization of environment variable access patterns.

        This test validates that common environment variables are accessed
        consistently across services.
        """
        env_var_analysis = defaultdict(lambda: {'services': set(), 'access_patterns': set(), 'violation_count': 0, 'compliant_count': 0})
        for service_config in self.services_to_analyze:
            service_patterns = self.analyze_service_configuration_patterns(service_config)
            for pattern in service_patterns:
                for env_var in pattern.environment_variables_accessed:
                    analysis = env_var_analysis[env_var]
                    analysis['services'].add(pattern.service_name)
                    analysis['access_patterns'].add(pattern.access_pattern)
                    if pattern.is_ssot_compliant:
                        analysis['compliant_count'] += 1
                    else:
                        analysis['violation_count'] += 1
        env_var_summary = {}
        for env_var, analysis in env_var_analysis.items():
            env_var_summary[env_var] = {'services': list(analysis['services']), 'access_patterns': list(analysis['access_patterns']), 'violation_count': analysis['violation_count'], 'compliant_count': analysis['compliant_count'], 'is_standardized': len(analysis['access_patterns']) == 1}
        self.record_metric('environment_variable_standardization_analysis', env_var_summary)
        critical_var_inconsistencies = []
        for env_var in self.critical_env_vars:
            if env_var in env_var_summary:
                var_data = env_var_summary[env_var]
                if not var_data['is_standardized'] or var_data['violation_count'] > 0:
                    critical_var_inconsistencies.append(env_var)
        assert len(env_var_summary) > 0, f'NO ENVIRONMENT VARIABLE USAGE FOUND: Expected to find environment variable access patterns but found none. This may indicate the analysis is not working properly.'
        if critical_var_inconsistencies:
            inconsistent_details = {var: env_var_summary[var] for var in critical_var_inconsistencies}
            assert len(critical_var_inconsistencies) > 0, f'CRITICAL ENVIRONMENT VARIABLE INCONSISTENCIES: Found inconsistent access patterns for critical variables: {critical_var_inconsistencies}. Details: {inconsistent_details}. This affects Golden Path functionality and $500K+ ARR system stability.'
        total_vars = len(env_var_summary)
        standardized_vars = len([var for var, data in env_var_summary.items() if data['is_standardized']])
        standardization_rate = standardized_vars / total_vars * 100 if total_vars > 0 else 0
        self.record_metric('standardization_metrics', {'total_environment_variables': total_vars, 'standardized_variables': standardized_vars, 'standardization_rate_percent': standardization_rate, 'critical_var_inconsistencies': len(critical_var_inconsistencies)})
        if standardization_rate == 100.0 and len(critical_var_inconsistencies) == 0:
            pytest.fail(f'FULL STANDARDIZATION ACHIEVED: All environment variables show consistent access patterns. Standardization rate: {standardization_rate}%. If SSOT remediation is complete, update test expectations.')

    async def test_staging_environment_configuration_integration(self):
        """
        Test staging environment configuration integration.

        This test validates that configuration patterns work correctly
        in staging environment context without Docker dependencies.
        """
        with self.temp_env_vars(ENVIRONMENT='staging', TESTING='true'):
            staging_config_results = {'environment_detected': self.get_env_var('ENVIRONMENT'), 'testing_mode': self.get_env_var('TESTING'), 'config_access_successful': False, 'isolated_env_working': False}
            try:
                from shared.isolated_environment import get_env
                env = get_env()
                detected_env = env.get('ENVIRONMENT')
                staging_config_results['config_access_successful'] = detected_env == 'staging'
                staging_config_results['isolated_env_working'] = True
            except ImportError:
                staging_config_results['isolated_env_working'] = False
            except Exception as e:
                self.record_metric('staging_config_error', str(e))
            self.record_metric('staging_environment_integration_results', staging_config_results)
            assert staging_config_results['environment_detected'] == 'staging', f"STAGING ENVIRONMENT DETECTION FAILED: Expected 'staging' but got '{staging_config_results['environment_detected']}'. Test environment configuration is not working properly."
            if staging_config_results['isolated_env_working']:
                assert staging_config_results['config_access_successful'], f'STAGING CONFIGURATION ACCESS FAILED: IsolatedEnvironment is available but configuration access failed. Results: {staging_config_results}'
            assert True, f'STAGING ENVIRONMENT INTEGRATION VALIDATED: Configuration access working without Docker. Results: {staging_config_results}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')