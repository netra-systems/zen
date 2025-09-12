"""
E2E Configuration Audit Test: Comprehensive Load Balancer Configuration Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure all E2E test configurations align with load balancer infrastructure
- Value Impact: Prevents configuration mismatches that cause false test failures or missed issues
- Strategic Impact: Validates complete configuration consistency across test environments

CRITICAL: This test performs comprehensive auditing of all E2E test configurations
to ensure they align with load balancer domain requirements. Configuration mismatches
cause false test failures and can mask real infrastructure issues.

This addresses GitHub issue #113: E2E Configuration Audit for Load Balancer Compliance
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import pytest
import yaml
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestE2EConfigurationAudit(SSotBaseTestCase):
    """
    Comprehensive audit of E2E test configurations for load balancer compliance.
    
    E2E CONFIGURATION AUDIT: Validates that all E2E test configurations use proper
    load balancer domains and are consistent with infrastructure requirements.
    """
    
    # Load balancer domains that should be used in E2E tests
    LOAD_BALANCER_DOMAINS = {
        "api.staging.netrasystems.ai",
        "auth.staging.netrasystems.ai",
        "app.staging.netrasystems.ai"
    }
    
    # Direct Cloud Run URLs that should NOT appear in E2E configurations
    FORBIDDEN_CLOUDRUN_PATTERNS = [
        r"netra-backend-staging-[a-z0-9]+-uc\.a\.run\.app",
        r"netra-frontend-staging-[a-z0-9]+-uc\.a\.run\.app",
        r"auth-staging-[a-z0-9]+-uc\.a\.run\.app",
        r"[a-zA-Z0-9-]+-staging-[a-zA-Z0-9]+-uc\.a\.run\.app"
    ]
    
    # E2E configuration files to audit
    E2E_CONFIG_FILES = [
        "tests/e2e/e2e_test_config.py",
        "tests/e2e/staging_config.py", 
        "tests/e2e/staging_test_helpers.py",
        "tests/e2e/real_services_manager.py",
        "tests/e2e/enforce_real_services_config.py",
    ]
    
    # Test framework configuration files
    TEST_FRAMEWORK_CONFIG_FILES = [
        "test_framework/ssot/e2e_auth_helper.py",
        "test_framework/ssot/base_test_case.py",
        "tests/conftest.py",
        "tests/conftest_e2e.py",
    ]
    
    @pytest.mark.e2e
    @pytest.mark.configuration_audit
    @pytest.mark.no_skip
    def test_e2e_configuration_files_load_balancer_compliance(self):
        """
        HARD FAIL: E2E configuration files MUST comply with load balancer requirements.
        
        This test audits all E2E configuration files to ensure they use proper
        load balancer domains instead of direct Cloud Run URLs.
        """
        config_audit_results = {}
        config_audit_failures = []
        
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Audit E2E configuration files
        for config_file in self.E2E_CONFIG_FILES:
            config_path = project_root / config_file
            
            if config_path.exists():
                try:
                    audit_result = self._audit_configuration_file(config_path)
                    config_audit_results[config_file] = audit_result
                    
                    if audit_result['violations']:
                        config_audit_failures.append(
                            f"Configuration violations in {config_file}: {len(audit_result['violations'])} issues"
                        )
                
                except Exception as e:
                    config_audit_results[config_file] = {
                        'violations': [],
                        'load_balancer_compliant': False,
                        'error': str(e)
                    }
                    config_audit_failures.append(f"Failed to audit {config_file}: {e}")
        
        if config_audit_failures:
            error_report = self._build_config_audit_failure_report(config_audit_results, config_audit_failures)
            raise AssertionError(
                f"CRITICAL: E2E configuration compliance violations detected!\n\n"
                f"Configuration violations in E2E test files can cause tests to bypass\n"
                f"the load balancer, missing critical infrastructure issues.\n\n"
                f"CONFIGURATION AUDIT FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Update E2E configuration files to use *.staging.netrasystems.ai\n"
                f"2. Remove hardcoded Cloud Run URLs from test configurations\n"
                f"3. Ensure staging environment detection works correctly\n"
                f"4. Validate test authentication uses proper staging domains\n"
                f"5. Update WebSocket test configurations for load balancer URLs\n\n"
                f"Reference: E2E Configuration Load Balancer Compliance"
            )
    
    @pytest.mark.e2e
    @pytest.mark.configuration_audit
    @pytest.mark.no_skip
    def test_test_framework_configuration_compliance(self):
        """
        HARD FAIL: Test framework configurations MUST be load balancer compliant.
        
        This test audits test framework configuration files to ensure they support
        proper load balancer domain usage in E2E tests.
        """
        framework_audit_results = {}
        framework_audit_failures = []
        
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Audit test framework configuration files
        for config_file in self.TEST_FRAMEWORK_CONFIG_FILES:
            config_path = project_root / config_file
            
            if config_path.exists():
                try:
                    audit_result = self._audit_test_framework_file(config_path)
                    framework_audit_results[config_file] = audit_result
                    
                    if audit_result['violations']:
                        framework_audit_failures.append(
                            f"Test framework violations in {config_file}: {len(audit_result['violations'])} issues"
                        )
                
                except Exception as e:
                    framework_audit_results[config_file] = {
                        'violations': [],
                        'load_balancer_compliant': False,
                        'error': str(e)
                    }
                    framework_audit_failures.append(f"Failed to audit {config_file}: {e}")
        
        if framework_audit_failures:
            error_report = self._build_framework_audit_failure_report(framework_audit_results, framework_audit_failures)
            raise AssertionError(
                f"CRITICAL: Test framework configuration compliance violations!\n\n"
                f"Test framework configuration violations prevent E2E tests from\n"
                f"properly validating load balancer functionality.\n\n"
                f"FRAMEWORK AUDIT FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Update test framework to support load balancer domains\n"
                f"2. Fix authentication helpers to use proper staging URLs\n"
                f"3. Update base test case configurations\n"
                f"4. Ensure pytest configuration supports load balancer testing\n"
                f"5. Validate test fixture configurations\n\n"
                f"Reference: Test Framework Load Balancer Support"
            )
    
    @pytest.mark.e2e
    @pytest.mark.configuration_audit 
    @pytest.mark.no_skip
    def test_environment_variable_configuration_audit(self):
        """
        HARD FAIL: Environment variable configurations MUST support load balancer URLs.
        
        This test audits environment variable usage to ensure proper support
        for load balancer domain configuration in different environments.
        """
        env_audit_results = {}
        env_audit_failures = []
        
        try:
            # Audit environment variable patterns
            env_patterns_result = self._audit_environment_variable_patterns()
            env_audit_results['env_patterns'] = env_patterns_result
            
            if env_patterns_result['violations']:
                env_audit_failures.append(
                    f"Environment variable pattern violations: {len(env_patterns_result['violations'])} issues"
                )
            
            # Audit staging environment variable resolution
            staging_resolution_result = self._audit_staging_environment_resolution()
            env_audit_results['staging_resolution'] = staging_resolution_result
            
            if staging_resolution_result['violations']:
                env_audit_failures.append(
                    f"Staging environment resolution violations: {len(staging_resolution_result['violations'])} issues"
                )
            
            # Audit environment-specific URL overrides
            url_override_result = self._audit_url_override_mechanisms()
            env_audit_results['url_overrides'] = url_override_result
            
            if url_override_result['violations']:
                env_audit_failures.append(
                    f"URL override mechanism violations: {len(url_override_result['violations'])} issues"
                )
        
        except Exception as e:
            env_audit_failures.append(f"Environment variable audit failed: {e}")
        
        if env_audit_failures:
            error_report = self._build_env_audit_failure_report(env_audit_results, env_audit_failures)
            raise AssertionError(
                f"CRITICAL: Environment variable configuration audit failures!\n\n"
                f"Environment variable configuration issues prevent proper load balancer\n"
                f"URL resolution and can cause tests to use wrong endpoints.\n\n"
                f"ENVIRONMENT AUDIT FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Fix environment variable patterns for load balancer URLs\n"
                f"2. Ensure staging environment detection works correctly\n"
                f"3. Validate URL override mechanisms support staging domains\n"
                f"4. Check isolated environment configuration loading\n"
                f"5. Test environment-specific URL resolution\n\n"
                f"Reference: Environment Variable Load Balancer Configuration"
            )
    
    @pytest.mark.e2e
    @pytest.mark.configuration_audit
    @pytest.mark.no_skip
    def test_websocket_configuration_audit(self):
        """
        HARD FAIL: WebSocket configurations MUST use load balancer domains.
        
        This test specifically audits WebSocket-related configurations to ensure
        they use proper load balancer domains and WSS protocol.
        """
        websocket_audit_results = {}
        websocket_audit_failures = []
        
        try:
            # Audit WebSocket URL configurations
            websocket_url_result = self._audit_websocket_url_configurations()
            websocket_audit_results['websocket_urls'] = websocket_url_result
            
            if websocket_url_result['violations']:
                websocket_audit_failures.append(
                    f"WebSocket URL configuration violations: {len(websocket_url_result['violations'])} issues"
                )
            
            # Audit WebSocket authentication configurations
            websocket_auth_result = self._audit_websocket_authentication_config()
            websocket_audit_results['websocket_auth'] = websocket_auth_result
            
            if websocket_auth_result['violations']:
                websocket_audit_failures.append(
                    f"WebSocket authentication configuration violations: {len(websocket_auth_result['violations'])} issues"
                )
            
            # Audit WebSocket test helper configurations
            websocket_helpers_result = self._audit_websocket_test_helpers()
            websocket_audit_results['websocket_helpers'] = websocket_helpers_result
            
            if websocket_helpers_result['violations']:
                websocket_audit_failures.append(
                    f"WebSocket test helper violations: {len(websocket_helpers_result['violations'])} issues"
                )
        
        except Exception as e:
            websocket_audit_failures.append(f"WebSocket configuration audit failed: {e}")
        
        if websocket_audit_failures:
            error_report = self._build_websocket_audit_failure_report(websocket_audit_results, websocket_audit_failures)
            raise AssertionError(
                f"CRITICAL: WebSocket configuration audit failures!\n\n"
                f"WebSocket configuration violations prevent proper testing of real-time\n"
                f"features through the load balancer infrastructure.\n\n"
                f"WEBSOCKET AUDIT FAILURES:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Update WebSocket URL configurations to use WSS and staging domains\n"
                f"2. Fix WebSocket authentication to work with load balancer\n"
                f"3. Update WebSocket test helpers for load balancer compliance\n"
                f"4. Validate WebSocket connection handling through load balancer\n"
                f"5. Test WebSocket agent event delivery through load balancer\n\n"
                f"Reference: WebSocket Load Balancer Configuration"
            )
    
    def _audit_configuration_file(self, file_path: Path) -> Dict:
        """Audit a single configuration file for load balancer compliance."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for forbidden Cloud Run patterns
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.FORBIDDEN_CLOUDRUN_PATTERNS:
                    if re.search(pattern, line):
                        violations.append({
                            'type': 'forbidden_cloudrun_url',
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'pattern': pattern,
                            'severity': 'critical'
                        })
            
            # Check for localhost URLs in staging configs
            if 'staging' in file_path.name.lower():
                for line_num, line in enumerate(content.splitlines(), 1):
                    if re.search(r'localhost|127\.0\.0\.1', line) and 'http' in line:
                        violations.append({
                            'type': 'localhost_in_staging_config',
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'severity': 'high'
                        })
            
            # Check for missing load balancer domains
            missing_domains = set()
            for domain in self.LOAD_BALANCER_DOMAINS:
                if domain not in content:
                    missing_domains.add(domain)
            
            if missing_domains and 'staging' in file_path.name.lower():
                violations.append({
                    'type': 'missing_load_balancer_domains',
                    'missing_domains': list(missing_domains),
                    'severity': 'medium'
                })
        
        except Exception as e:
            violations.append({
                'type': 'file_read_error',
                'description': str(e),
                'severity': 'critical'
            })
        
        return {
            'violations': violations,
            'load_balancer_compliant': len([v for v in violations if v['severity'] == 'critical']) == 0,
            'file_path': str(file_path)
        }
    
    def _audit_test_framework_file(self, file_path: Path) -> Dict:
        """Audit a test framework file for load balancer support."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for hardcoded staging URLs
            if 'staging' in content:
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in self.FORBIDDEN_CLOUDRUN_PATTERNS:
                        if re.search(pattern, line):
                            violations.append({
                                'type': 'hardcoded_cloudrun_in_framework',
                                'line_number': line_num,
                                'line_content': line.strip(),
                                'pattern': pattern,
                                'severity': 'critical'
                            })
            
            # Check for proper staging environment support
            if 'e2e_auth_helper.py' in file_path.name:
                if '.staging.netrasystems.ai' not in content:
                    violations.append({
                        'type': 'missing_staging_domain_support',
                        'description': 'Auth helper should support staging domains',
                        'severity': 'high'
                    })
        
        except Exception as e:
            violations.append({
                'type': 'framework_file_read_error',
                'description': str(e),
                'severity': 'critical'
            })
        
        return {
            'violations': violations,
            'load_balancer_compliant': len([v for v in violations if v['severity'] == 'critical']) == 0,
            'file_path': str(file_path)
        }
    
    def _audit_environment_variable_patterns(self) -> Dict:
        """Audit environment variable usage patterns."""
        violations = []
        
        # Check for common environment variable patterns
        common_env_vars = [
            'BACKEND_SERVICE_URL',
            'AUTH_SERVICE_URL', 
            'FRONTEND_URL',
            'WEBSOCKET_URL'
        ]
        
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Scan configuration files for environment variable usage
        for config_file in self.E2E_CONFIG_FILES + self.TEST_FRAMEWORK_CONFIG_FILES:
            config_path = project_root / config_file
            
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for proper environment variable usage
                    for env_var in common_env_vars:
                        if env_var in content:
                            # Check if there are hardcoded fallbacks to Cloud Run URLs
                            for pattern in self.FORBIDDEN_CLOUDRUN_PATTERNS:
                                if re.search(f'{env_var}.*{pattern}', content, re.MULTILINE):
                                    violations.append({
                                        'type': 'env_var_fallback_to_cloudrun',
                                        'env_var': env_var,
                                        'file': str(config_path),
                                        'pattern': pattern,
                                        'severity': 'high'
                                    })
                
                except Exception:
                    continue
        
        return {
            'violations': violations,
            'patterns_compliant': len(violations) == 0
        }
    
    def _audit_staging_environment_resolution(self) -> Dict:
        """Audit staging environment URL resolution."""
        violations = []
        
        try:
            # Test environment resolution by mocking staging environment
            original_env = os.environ.get('ENVIRONMENT')
            
            try:
                os.environ['ENVIRONMENT'] = 'staging'
                
                # Import and test NetworkEnvironmentHelper
                from netra_backend.app.core.network_constants import NetworkEnvironmentHelper
                
                staging_urls = NetworkEnvironmentHelper.get_service_urls_for_environment()
                
                # Check each URL for compliance
                for url_type, url_value in staging_urls.items():
                    if not url_value:
                        violations.append({
                            'type': 'empty_staging_url',
                            'url_type': url_type,
                            'severity': 'critical'
                        })
                    elif '.staging.netrasystems.ai' not in url_value:
                        violations.append({
                            'type': 'non_compliant_staging_url',
                            'url_type': url_type,
                            'url_value': url_value,
                            'severity': 'critical'
                        })
            
            finally:
                if original_env is not None:
                    os.environ['ENVIRONMENT'] = original_env
                else:
                    os.environ.pop('ENVIRONMENT', None)
        
        except Exception as e:
            violations.append({
                'type': 'staging_resolution_error',
                'description': str(e),
                'severity': 'critical'
            })
        
        return {
            'violations': violations,
            'resolution_compliant': len(violations) == 0
        }
    
    def _audit_url_override_mechanisms(self) -> Dict:
        """Audit URL override mechanisms."""
        violations = []
        
        # Check if URL override mechanisms support load balancer domains
        try:
            from netra_backend.app.core.network_constants import URLConstants
            
            # Test URL building methods
            test_methods = [
                ('build_http_url', {'host': 'api.staging.netrasystems.ai', 'secure': True}),
                ('build_websocket_url', {'host': 'api.staging.netrasystems.ai', 'secure': True}),
            ]
            
            for method_name, kwargs in test_methods:
                if hasattr(URLConstants, method_name):
                    try:
                        method = getattr(URLConstants, method_name)
                        result_url = method(**kwargs)
                        
                        # Check if result uses staging domain
                        if 'api.staging.netrasystems.ai' not in result_url:
                            violations.append({
                                'type': 'url_builder_non_compliant',
                                'method': method_name,
                                'result_url': result_url,
                                'severity': 'medium'
                            })
                    
                    except Exception as e:
                        violations.append({
                            'type': 'url_builder_error',
                            'method': method_name,
                            'error': str(e),
                            'severity': 'high'
                        })
        
        except Exception as e:
            violations.append({
                'type': 'url_override_audit_error',
                'description': str(e),
                'severity': 'critical'
            })
        
        return {
            'violations': violations,
            'override_compliant': len(violations) == 0
        }
    
    def _audit_websocket_url_configurations(self) -> Dict:
        """Audit WebSocket URL configurations."""
        violations = []
        
        try:
            from netra_backend.app.core.network_constants import URLConstants
            
            # Check WebSocket URL constant
            websocket_url = URLConstants.STAGING_WEBSOCKET_URL
            
            if not websocket_url.startswith('wss://'):
                violations.append({
                    'type': 'websocket_insecure_protocol',
                    'url': websocket_url,
                    'severity': 'critical'
                })
            
            if 'api.staging.netrasystems.ai' not in websocket_url:
                violations.append({
                    'type': 'websocket_non_compliant_domain',
                    'url': websocket_url,
                    'severity': 'critical'
                })
        
        except Exception as e:
            violations.append({
                'type': 'websocket_url_audit_error',
                'description': str(e),
                'severity': 'critical'
            })
        
        return {
            'violations': violations,
            'websocket_urls_compliant': len(violations) == 0
        }
    
    def _audit_websocket_authentication_config(self) -> Dict:
        """Audit WebSocket authentication configurations."""
        violations = []
        
        project_root = Path(__file__).parent.parent.parent.parent
        websocket_auth_file = project_root / "test_framework/ssot/e2e_auth_helper.py"
        
        if websocket_auth_file.exists():
            try:
                with open(websocket_auth_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for WebSocket authentication support
                if 'websocket' in content.lower():
                    # Check for staging domain support
                    if '.staging.netrasystems.ai' not in content:
                        violations.append({
                            'type': 'websocket_auth_missing_staging_support',
                            'description': 'WebSocket auth helper missing staging domain support',
                            'severity': 'high'
                        })
                    
                    # Check for forbidden Cloud Run patterns
                    for pattern in self.FORBIDDEN_CLOUDRUN_PATTERNS:
                        if re.search(pattern, content):
                            violations.append({
                                'type': 'websocket_auth_cloudrun_pattern',
                                'pattern': pattern,
                                'severity': 'critical'
                            })
            
            except Exception as e:
                violations.append({
                    'type': 'websocket_auth_audit_error',
                    'description': str(e),
                    'severity': 'critical'
                })
        
        return {
            'violations': violations,
            'websocket_auth_compliant': len(violations) == 0
        }
    
    def _audit_websocket_test_helpers(self) -> Dict:
        """Audit WebSocket test helper configurations."""
        violations = []
        
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Check for WebSocket test helper files
        websocket_helper_files = [
            "test_framework/websocket_helpers.py",
            "tests/e2e/test_helpers/websocket_helpers.py",
        ]
        
        for helper_file in websocket_helper_files:
            helper_path = project_root / helper_file
            
            if helper_path.exists():
                try:
                    with open(helper_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for Cloud Run patterns in WebSocket helpers
                    for pattern in self.FORBIDDEN_CLOUDRUN_PATTERNS:
                        if re.search(pattern, content):
                            violations.append({
                                'type': 'websocket_helper_cloudrun_pattern',
                                'file': str(helper_path),
                                'pattern': pattern,
                                'severity': 'critical'
                            })
                
                except Exception as e:
                    violations.append({
                        'type': 'websocket_helper_audit_error',
                        'file': str(helper_path),
                        'description': str(e),
                        'severity': 'high'
                    })
        
        return {
            'violations': violations,
            'websocket_helpers_compliant': len(violations) == 0
        }
    
    def _build_config_audit_failure_report(self, audit_results: Dict, failures: List[str]) -> str:
        """Build configuration audit failure report."""
        report_parts = []
        
        for config_file, result in audit_results.items():
            if result.get('violations'):
                report_parts.append(f"  {config_file}:")
                for violation in result['violations']:
                    if 'line_number' in violation:
                        report_parts.append(
                            f"    Line {violation['line_number']}: {violation['type']}"
                        )
                    else:
                        report_parts.append(f"    {violation['type']}: {violation.get('description', 'Violation')}")
        
        return "\n".join(report_parts)
    
    def _build_framework_audit_failure_report(self, audit_results: Dict, failures: List[str]) -> str:
        """Build framework audit failure report."""
        return self._build_config_audit_failure_report(audit_results, failures)
    
    def _build_env_audit_failure_report(self, audit_results: Dict, failures: List[str]) -> str:
        """Build environment audit failure report."""
        report_parts = []
        
        for audit_type, result in audit_results.items():
            if result.get('violations'):
                report_parts.append(f"  {audit_type}:")
                for violation in result['violations']:
                    report_parts.append(f"    {violation['type']}: {violation.get('description', 'Violation')}")
        
        return "\n".join(report_parts)
    
    def _build_websocket_audit_failure_report(self, audit_results: Dict, failures: List[str]) -> str:
        """Build WebSocket audit failure report."""
        return self._build_env_audit_failure_report(audit_results, failures)


if __name__ == "__main__":
    # Run this test standalone to perform E2E configuration audit
    test_instance = TestE2EConfigurationAudit()
    
    tests = [
        test_instance.test_e2e_configuration_files_load_balancer_compliance,
        test_instance.test_test_framework_configuration_compliance,
        test_instance.test_environment_variable_configuration_audit,
        test_instance.test_websocket_configuration_audit,
    ]
    
    passed_tests = 0
    
    for test_func in tests:
        try:
            test_func()
            print(f" PASS:  {test_func.__name__} passed")
            passed_tests += 1
        except AssertionError as e:
            print(f" FAIL:  {test_func.__name__} failed:\n{e}\n")
        except Exception as e:
            print(f" FAIL:  {test_func.__name__} error: {e}\n")
    
    if passed_tests == len(tests):
        print(" PASS:  All E2E configuration audit tests passed!")
    else:
        print(f" FAIL:  {len(tests) - passed_tests} out of {len(tests)} tests failed")
        exit(1)