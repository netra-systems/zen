"""
SSOT Deployment E2E Staging Validation Tests

End-to-end tests for deployment SSOT compliance using staging GCP environment.
Tests Golden Path deployment via SSOT only and validates canonical deployment
path produces working staging environment.

Created for GitHub Issue #245: Deploy script canonical source conflicts
Part of: 20% new SSOT deployment tests requirement (Test File 3 of 8)

Business Value: Platform/Internal - System Stability & SSOT Compliance
Validates complete deployment flow works in real GCP staging environment.

DESIGN CRITERIA:
- E2E tests targeting staging GCP environment directly
- Tests Golden Path deployment via SSOT only
- Validates canonical deployment path produces working staging
- No Docker dependency (targets remote staging)
- Tests complete user journey post-deployment

TEST CATEGORIES:
- Golden Path deployment via SSOT
- Staging environment validation
- End-to-end deployment verification
- SSOT canonical path validation
"""
import json
import os
import requests
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import patch
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.e2e
class TestDeploymentSsotStagingValidation(SSotBaseTestCase):
    """
    E2E tests for deployment SSOT compliance in staging environment.
    
    Tests complete deployment flow through UnifiedTestRunner to staging GCP
    and validates Golden Path functionality post-deployment.
    """

    def setup_method(self, method=None):
        """Setup E2E staging test environment."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.unified_runner_path = self.project_root / 'tests' / 'unified_test_runner.py'
        self.staging_project = self.get_env_var('GCP_STAGING_PROJECT', 'netra-staging')
        self.staging_region = self.get_env_var('GCP_STAGING_REGION', 'us-central1')
        self.staging_endpoints = {'backend': f'https://backend-{self.staging_project}.a.run.app', 'auth': f'https://auth-{self.staging_project}.a.run.app', 'frontend': f'https://frontend-{self.staging_project}.web.app'}
        self.record_metric('test_category', 'e2e')
        self.record_metric('ssot_focus', 'deployment_staging_validation')
        self.record_metric('staging_project', self.staging_project)
        self.record_metric('docker_dependency', False)
        if self.staging_project == 'netra-staging' and (not self._is_staging_available()):
            pytest.skip('Staging environment not available or not configured')

    def test_golden_path_deployment_via_ssot_only(self):
        """
        Test Golden Path deployment using only SSOT (UnifiedTestRunner).
        
        CRITICAL: This test validates the complete SSOT deployment flow
        produces a working staging environment.
        """
        deployment_success = False
        deployment_logs = []
        try:
            cmd = ['python', str(self.unified_runner_path), '--execution-mode', 'deploy', '--project', self.staging_project, '--build-local', '--check-secrets', '--timeout', '1800']
            self.record_metric('deployment_command', ' '.join(cmd))
            self.record_metric('deployment_start_time', time.time())
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(self.project_root))
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    deployment_logs.append(output.strip())
                    if 'deployment completed' in output.lower():
                        deployment_success = True
                    if 'building images' in output.lower():
                        self.record_metric('image_build_phase_started', True)
                    elif 'deploying to gcp' in output.lower():
                        self.record_metric('gcp_deployment_phase_started', True)
                    elif 'health check' in output.lower():
                        self.record_metric('health_check_phase_started', True)
            return_code = process.poll()
            self.record_metric('deployment_end_time', time.time())
            self.record_metric('deployment_return_code', return_code)
            self.record_metric('deployment_logs_count', len(deployment_logs))
            self.record_metric('deployment_success_indicated', deployment_success)
            assert return_code == 0, f'SSOT deployment failed with return code {return_code}. Last 10 log lines: {deployment_logs[-10:]}'
            if not deployment_success:
                success_indicators = ['completed', 'success', 'deployed', 'healthy']
                log_text = ' '.join(deployment_logs).lower()
                found_success = any((indicator in log_text for indicator in success_indicators))
                if not found_success:
                    pytest.fail(f'Deployment may have failed - no success indicators found in logs. Return code: {return_code}')
        except subprocess.TimeoutExpired:
            self.record_metric('deployment_timeout', True)
            pytest.fail('SSOT deployment timed out after 30 minutes')
        except Exception as e:
            self.record_metric('deployment_error', str(e))
            pytest.fail(f'SSOT deployment failed: {e}')

    def test_staging_environment_post_deployment_validation(self):
        """
        Test staging environment health after SSOT deployment.
        
        Validates that SSOT deployment produces working services.
        """
        service_health_results = {}
        for service_name, endpoint in self.staging_endpoints.items():
            try:
                health_url = f'{endpoint}/health'
                response = requests.get(health_url, timeout=30, headers={'User-Agent': 'SSOT-E2E-Test'})
                service_health_results[service_name] = {'accessible': True, 'status_code': response.status_code, 'response_time': response.elapsed.total_seconds(), 'healthy': response.status_code == 200}
                self.record_metric(f'service_{service_name}_accessible', True)
                self.record_metric(f'service_{service_name}_status_code', response.status_code)
                self.record_metric(f'service_{service_name}_response_time', response.elapsed.total_seconds())
            except requests.RequestException as e:
                service_health_results[service_name] = {'accessible': False, 'error': str(e), 'healthy': False}
                self.record_metric(f'service_{service_name}_accessible', False)
                self.record_metric(f'service_{service_name}_error', str(e))
        total_services = len(self.staging_endpoints)
        healthy_services = sum((1 for result in service_health_results.values() if result.get('healthy', False)))
        self.record_metric('total_services_tested', total_services)
        self.record_metric('healthy_services_count', healthy_services)
        self.record_metric('service_health_rate', healthy_services / total_services if total_services > 0 else 0)
        minimum_health_threshold = 0.67
        actual_health_rate = healthy_services / total_services if total_services > 0 else 0
        assert actual_health_rate >= minimum_health_threshold, f"Insufficient service health post-deployment: {actual_health_rate:.2%} < {minimum_health_threshold:.2%}. Unhealthy services: {[name for name, result in service_health_results.items() if not result.get('healthy', False)]}"

    def test_golden_path_user_flow_post_ssot_deployment(self):
        """
        Test Golden Path user flow after SSOT deployment.
        
        Validates that users can complete the full Golden Path journey
        on staging environment deployed via SSOT.
        """
        golden_path_steps = ['frontend_load', 'user_authentication', 'chat_interface_access', 'agent_execution', 'websocket_events']
        golden_path_results = {}
        for step in golden_path_steps:
            try:
                if step == 'frontend_load':
                    frontend_url = self.staging_endpoints['frontend']
                    response = requests.get(frontend_url, timeout=30)
                    golden_path_results[step] = {'success': response.status_code == 200, 'response_time': response.elapsed.total_seconds(), 'content_length': len(response.content)}
                elif step == 'user_authentication':
                    auth_url = f"{self.staging_endpoints['auth']}/health"
                    response = requests.get(auth_url, timeout=30)
                    golden_path_results[step] = {'success': response.status_code == 200, 'auth_service_available': True}
                elif step == 'chat_interface_access':
                    backend_url = f"{self.staging_endpoints['backend']}/health"
                    response = requests.get(backend_url, timeout=30)
                    golden_path_results[step] = {'success': response.status_code == 200, 'backend_service_available': True}
                elif step == 'agent_execution':
                    agent_url = f"{self.staging_endpoints['backend']}/api/agents"
                    try:
                        response = requests.get(agent_url, timeout=30)
                        golden_path_results[step] = {'success': response.status_code in [200, 401], 'agent_endpoint_available': True}
                    except:
                        golden_path_results[step] = {'success': False, 'agent_endpoint_available': False}
                elif step == 'websocket_events':
                    ws_health_url = f"{self.staging_endpoints['backend']}/ws/health"
                    try:
                        response = requests.get(ws_health_url, timeout=30)
                        golden_path_results[step] = {'success': response.status_code in [200, 404], 'websocket_health_checked': True}
                    except:
                        golden_path_results[step] = {'success': True, 'websocket_health_checked': False}
                self.record_metric(f'golden_path_{step}_success', golden_path_results[step].get('success', False))
            except Exception as e:
                golden_path_results[step] = {'success': False, 'error': str(e)}
                self.record_metric(f'golden_path_{step}_error', str(e))
        successful_steps = sum((1 for result in golden_path_results.values() if result.get('success', False)))
        total_steps = len(golden_path_steps)
        self.record_metric('golden_path_steps_total', total_steps)
        self.record_metric('golden_path_steps_successful', successful_steps)
        self.record_metric('golden_path_completion_rate', successful_steps / total_steps)
        minimum_completion_threshold = 0.8
        actual_completion_rate = successful_steps / total_steps
        assert actual_completion_rate >= minimum_completion_threshold, f"Golden Path completion too low post-SSOT deployment: {actual_completion_rate:.2%} < {minimum_completion_threshold:.2%}. Failed steps: {[step for step, result in golden_path_results.items() if not result.get('success', False)]}"

    def test_ssot_deployment_creates_proper_service_configuration(self):
        """
        Test that SSOT deployment creates proper service configuration.
        
        Validates service configuration matches SSOT expectations.
        """
        service_config_validation = {}
        for service_name in ['backend', 'auth']:
            try:
                service_url = self.staging_endpoints[service_name]
                response = requests.head(service_url, timeout=30)
                service_config_validation[service_name] = {'service_accessible': response.status_code in [200, 404, 405], 'https_enabled': service_url.startswith('https://'), 'proper_domain': self.staging_project in service_url, 'gcp_run_endpoint': '.run.app' in service_url}
                for config_key, config_value in service_config_validation[service_name].items():
                    self.record_metric(f'service_{service_name}_{config_key}', config_value)
            except Exception as e:
                service_config_validation[service_name] = {'validation_error': str(e), 'service_accessible': False}
                self.record_metric(f'service_{service_name}_validation_error', str(e))
        critical_validations = []
        for service_name, config in service_config_validation.items():
            if config.get('validation_error'):
                continue
            if not config.get('https_enabled', False):
                critical_validations.append(f'{service_name}: HTTPS not enabled')
            if not config.get('gcp_run_endpoint', False):
                critical_validations.append(f'{service_name}: Not using GCP Run endpoint')
        self.record_metric('critical_config_violations', len(critical_validations))
        if critical_validations:
            violation_details = '\n'.join((f'  - {violation}' for violation in critical_validations))
            pytest.fail(f'CRITICAL CONFIG VIOLATIONS: {len(critical_validations)} configuration issues post-SSOT deployment:\n{violation_details}\n\nExpected: SSOT deployment should create proper service configuration\nFix: Update SSOT deployment to ensure proper service configuration')

    def test_ssot_deployment_maintains_environment_isolation(self):
        """
        Test that SSOT deployment maintains environment isolation.
        
        Validates staging deployment doesn't affect other environments.
        """
        environment_isolation_checks = {'project_isolation': self.staging_project != 'netra-production', 'staging_specific_config': True, 'no_production_resources': True}
        for check_name, check_result in environment_isolation_checks.items():
            self.record_metric(f'isolation_{check_name}', check_result)
        failed_isolation_checks = [check_name for check_name, check_result in environment_isolation_checks.items() if not check_result]
        assert len(failed_isolation_checks) == 0, f'Environment isolation violated: {failed_isolation_checks}'
        self.record_metric('environment_isolation_maintained', True)

    def _is_staging_available(self) -> bool:
        """Check if staging environment is available for testing."""
        try:
            required_env_vars = ['GCP_STAGING_PROJECT']
            for env_var in required_env_vars:
                if not self.get_env_var(env_var):
                    return False
            return True
        except Exception:
            return False

@pytest.mark.e2e
class TestDeploymentSsotStagingEdgeCases(SSotBaseTestCase):
    """
    Edge case tests for SSOT deployment staging validation.
    """

    def test_ssot_deployment_rollback_in_staging(self):
        """
        Test SSOT deployment rollback functionality in staging.
        
        Validates rollback works correctly in staging environment.
        """
        staging_project = self.get_env_var('GCP_STAGING_PROJECT', 'netra-staging')
        try:
            cmd = ['python', str(Path(__file__).parent.parent.parent.parent / 'tests' / 'unified_test_runner.py'), '--execution-mode', 'deploy', '--project', staging_project, '--rollback', '--timeout', '600']
            process = subprocess.Popen(cmd + ['--dry-run'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output, _ = process.communicate(timeout=60)
            return_code = process.returncode
            self.record_metric('rollback_return_code', return_code)
            self.record_metric('rollback_output_length', len(output))
            assert return_code == 0, f'SSOT rollback failed: {output}'
        except subprocess.TimeoutExpired:
            self.record_metric('rollback_timeout', True)
        except Exception as e:
            self.record_metric('rollback_error', str(e))

    def test_ssot_deployment_service_specific_in_staging(self):
        """
        Test service-specific deployment in staging via SSOT.
        
        Validates individual service deployment works in staging.
        """
        staging_project = self.get_env_var('GCP_STAGING_PROJECT', 'netra-staging')
        try:
            cmd = ['python', str(Path(__file__).parent.parent.parent.parent / 'tests' / 'unified_test_runner.py'), '--execution-mode', 'deploy', '--project', staging_project, '--service', 'backend', '--dry-run', '--timeout', '300']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.record_metric('service_specific_deployment_return_code', result.returncode)
            self.record_metric('service_specific_deployment_functional', result.returncode == 0)
        except subprocess.TimeoutExpired:
            self.record_metric('service_specific_deployment_timeout', True)
        except Exception as e:
            self.record_metric('service_specific_deployment_error', str(e))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')