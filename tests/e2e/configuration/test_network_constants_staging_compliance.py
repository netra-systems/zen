"""
Configuration Drift Prevention Test: Network Constants Staging Compliance

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent configuration drift that breaks staging environment access
- Value Impact: Prevents deployment failures and service outages from URL misconfiguration
- Strategic Impact: Ensures configuration consistency across development and staging

CRITICAL: This test prevents configuration drift by validating that all network
constants use proper staging domains instead of hardcoded Cloud Run URLs or
localhost addresses. Configuration drift causes deployment failures and blocks users.

This addresses GitHub issue #113: Configuration Drift Prevention for Load Balancer URLs
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.network_constants import URLConstants, ServiceEndpoints, NetworkEnvironmentHelper


class TestNetworkConstantsStagingCompliance(SSotBaseTestCase):
    """
    Test network constants compliance with staging domain requirements.
    
    CONFIGURATION DRIFT PREVENTION: Validates that network constants are properly
    configured for staging environment and prevents regression to Cloud Run URLs.
    """
    
    # Expected staging domain patterns
    EXPECTED_STAGING_DOMAINS = {
        "api.staging.netrasystems.ai",
        "auth.staging.netrasystems.ai",
        "app.staging.netrasystems.ai"
    }
    
    # Forbidden patterns that indicate configuration drift
    FORBIDDEN_PATTERNS = [
        r".*-staging-[a-z0-9]+-uc\.a\.run\.app",  # Cloud Run staging URLs
        r"localhost(?::\d+)?",  # Localhost URLs in staging configs
        r"127\.0\.0\.1(?::\d+)?",  # IP localhost in staging configs
        r"http://(?!localhost|127\.0\.0\.1)",  # Non-HTTPS URLs in staging (except local dev)
    ]
    
    # Required URL configurations for staging compliance
    REQUIRED_STAGING_URL_CONFIGS = {
        "STAGING_BACKEND_URL": "https://api.staging.netrasystems.ai",
        "STAGING_AUTH_URL": "https://auth.staging.netrasystems.ai", 
        "STAGING_FRONTEND_URL": "https://app.staging.netrasystems.ai",
        "STAGING_WEBSOCKET_URL": "wss://api.staging.netrasystems.ai/ws",
    }
    
    @pytest.mark.e2e
    @pytest.mark.configuration_drift
    @pytest.mark.no_skip
    def test_url_constants_staging_compliance(self):
        """
        HARD FAIL: URLConstants MUST comply with staging domain requirements.
        
        This test validates that URLConstants class uses proper staging domains
        and prevents configuration drift to Cloud Run or localhost URLs.
        """
        compliance_violations = []
        
        # Check URLConstants class for staging compliance
        staging_url_violations = self._check_url_constants_staging_urls()
        if staging_url_violations:
            compliance_violations.extend(staging_url_violations)
        
        # Check for forbidden patterns in staging URLs
        forbidden_pattern_violations = self._check_forbidden_patterns_in_urls()
        if forbidden_pattern_violations:
            compliance_violations.extend(forbidden_pattern_violations)
        
        # Check staging URL format compliance
        format_violations = self._check_staging_url_format_compliance()
        if format_violations:
            compliance_violations.extend(format_violations)
        
        if compliance_violations:
            error_report = self._build_compliance_violation_report(compliance_violations)
            raise AssertionError(
                f"CRITICAL: Network constants staging compliance violations!\n\n"
                f"Configuration drift in network constants can cause deployment failures,\n"
                f"service outages, and break staging environment accessibility.\n\n"
                f"COMPLIANCE VIOLATIONS:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Update URLConstants to use proper *.staging.netrasystems.ai domains\n"
                f"2. Remove hardcoded Cloud Run URLs from staging configurations\n"
                f"3. Ensure all staging URLs use HTTPS protocol\n"
                f"4. Validate WebSocket URLs use WSS protocol\n"
                f"5. Update environment-specific URL resolution logic\n\n"
                f"Reference: Network Constants Staging Domain Requirements"
            )
    
    @pytest.mark.e2e
    @pytest.mark.configuration_drift  
    @pytest.mark.no_skip
    def test_environment_specific_url_resolution_compliance(self):
        """
        HARD FAIL: Environment URL resolution MUST work correctly for staging.
        
        This test validates that environment-specific URL resolution returns
        proper staging domains when environment is set to "staging".
        """
        resolution_violations = []
        
        # Test staging environment URL resolution
        try:
            staging_urls = self._get_staging_environment_urls()
            
            # Validate each staging URL
            for url_type, url_value in staging_urls.items():
                violations = self._validate_staging_url(url_type, url_value)
                if violations:
                    resolution_violations.extend(violations)
        
        except Exception as e:
            resolution_violations.append({
                'type': 'environment_resolution_error',
                'description': f"Failed to resolve staging environment URLs: {e}",
                'severity': 'critical'
            })
        
        if resolution_violations:
            error_report = self._build_resolution_violation_report(resolution_violations)
            raise AssertionError(
                f"CRITICAL: Environment URL resolution compliance violations!\n\n"
                f"Environment URL resolution failures prevent proper staging configuration\n"
                f"and can cause services to connect to wrong environments.\n\n"
                f"RESOLUTION VIOLATIONS:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Fix NetworkEnvironmentHelper.get_service_urls_for_environment()\n"
                f"2. Ensure staging environment detection works correctly\n"
                f"3. Validate environment-specific URL overrides\n"
                f"4. Check isolated environment configuration loading\n"
                f"5. Test URL resolution for all supported environments\n\n"
                f"Reference: Environment-Specific URL Resolution Architecture"
            )
    
    @pytest.mark.e2e  
    @pytest.mark.configuration_drift
    @pytest.mark.no_skip
    def test_cors_origins_staging_compliance(self):
        """
        HARD FAIL: CORS origins MUST be properly configured for staging.
        
        This test validates that CORS origins configuration includes proper
        staging domains and prevents CORS-related access failures.
        """
        cors_violations = []
        
        try:
            # Get CORS origins for staging environment
            staging_cors_origins = URLConstants.get_cors_origins("staging")
            
            # Validate CORS origins include required staging domains
            required_origins = {
                "https://api.staging.netrasystems.ai",
                "https://auth.staging.netrasystems.ai",
                "https://app.staging.netrasystems.ai"
            }
            
            missing_origins = required_origins - set(staging_cors_origins)
            if missing_origins:
                cors_violations.append({
                    'type': 'missing_cors_origins',
                    'missing_origins': list(missing_origins),
                    'current_origins': staging_cors_origins,
                    'severity': 'critical'
                })
            
            # Check for forbidden origins in staging CORS
            forbidden_origins = []
            for origin in staging_cors_origins:
                if any(re.search(pattern, origin) for pattern in self.FORBIDDEN_PATTERNS):
                    forbidden_origins.append(origin)
            
            if forbidden_origins:
                cors_violations.append({
                    'type': 'forbidden_cors_origins',
                    'forbidden_origins': forbidden_origins,
                    'severity': 'high'
                })
        
        except Exception as e:
            cors_violations.append({
                'type': 'cors_configuration_error',
                'description': f"Failed to get CORS origins for staging: {e}",
                'severity': 'critical'
            })
        
        if cors_violations:
            error_report = self._build_cors_violation_report(cors_violations)
            raise AssertionError(
                f"CRITICAL: CORS origins staging compliance violations!\n\n"
                f"CORS configuration violations prevent frontend applications from\n"
                f"making authenticated requests to backend services in staging.\n\n"
                f"CORS VIOLATIONS:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Add all required staging domains to CORS origins\n"
                f"2. Remove forbidden origins (Cloud Run URLs, localhost in staging)\n"
                f"3. Validate CORS origins for all environments\n"
                f"4. Test cross-origin requests in staging environment\n"
                f"5. Update CORS middleware configuration\n\n"
                f"Reference: CORS Configuration for Staging Environment"
            )
    
    @pytest.mark.e2e
    @pytest.mark.configuration_drift
    @pytest.mark.no_skip  
    def test_websocket_url_staging_compliance(self):
        """
        HARD FAIL: WebSocket URLs MUST comply with staging requirements.
        
        This test validates that WebSocket URLs use proper staging domains
        and WSS protocol for secure connections.
        """
        websocket_violations = []
        
        # Check WebSocket URL constants
        websocket_url = URLConstants.STAGING_WEBSOCKET_URL
        
        # Validate WebSocket URL format
        if not websocket_url.startswith("wss://"):
            websocket_violations.append({
                'type': 'websocket_protocol_violation',
                'url': websocket_url,
                'issue': 'WebSocket URL must use WSS protocol for staging',
                'severity': 'critical'
            })
        
        # Validate WebSocket domain
        expected_websocket_domain = "api.staging.netrasystems.ai"
        if expected_websocket_domain not in websocket_url:
            websocket_violations.append({
                'type': 'websocket_domain_violation',
                'url': websocket_url,
                'expected_domain': expected_websocket_domain,
                'issue': 'WebSocket URL must use staging load balancer domain',
                'severity': 'critical'
            })
        
        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, websocket_url):
                websocket_violations.append({
                    'type': 'websocket_forbidden_pattern',
                    'url': websocket_url,
                    'pattern': pattern,
                    'issue': 'WebSocket URL contains forbidden pattern',
                    'severity': 'high'
                })
        
        # Test WebSocket URL builder compliance
        try:
            built_websocket_url = URLConstants.build_websocket_url(
                host="api.staging.netrasystems.ai",
                path="/ws",
                secure=True
            )
            
            if not built_websocket_url.startswith("wss://api.staging.netrasystems.ai"):
                websocket_violations.append({
                    'type': 'websocket_builder_violation',
                    'built_url': built_websocket_url,
                    'issue': 'WebSocket URL builder does not produce compliant staging URLs',
                    'severity': 'medium'
                })
        
        except Exception as e:
            websocket_violations.append({
                'type': 'websocket_builder_error',
                'description': f"WebSocket URL builder failed: {e}",
                'severity': 'high'
            })
        
        if websocket_violations:
            error_report = self._build_websocket_violation_report(websocket_violations)
            raise AssertionError(
                f"CRITICAL: WebSocket URL staging compliance violations!\n\n"
                f"WebSocket URL violations prevent real-time features from working\n"
                f"in staging environment and may cause security issues.\n\n"
                f"WEBSOCKET VIOLATIONS:\n{error_report}\n\n"
                f"REQUIRED ACTIONS:\n"
                f"1. Update STAGING_WEBSOCKET_URL to use WSS and proper domain\n"
                f"2. Fix WebSocket URL builder for staging compliance\n"
                f"3. Validate WebSocket connection security (WSS only)\n"
                f"4. Test WebSocket connections through staging load balancer\n"
                f"5. Update WebSocket routing configuration\n\n"
                f"Reference: WebSocket Staging Configuration Requirements"
            )
    
    def _check_url_constants_staging_urls(self) -> List[Dict]:
        """Check URLConstants staging URLs for compliance violations."""
        violations = []
        
        # Check each required staging URL configuration
        for constant_name, expected_url in self.REQUIRED_STAGING_URL_CONFIGS.items():
            try:
                actual_url = getattr(URLConstants, constant_name, None)
                
                if actual_url != expected_url:
                    violations.append({
                        'type': 'staging_url_mismatch',
                        'constant_name': constant_name,
                        'expected_url': expected_url,
                        'actual_url': actual_url,
                        'severity': 'critical'
                    })
            
            except Exception as e:
                violations.append({
                    'type': 'staging_url_access_error',
                    'constant_name': constant_name,
                    'description': f"Failed to access {constant_name}: {e}",
                    'severity': 'critical'
                })
        
        return violations
    
    def _check_forbidden_patterns_in_urls(self) -> List[Dict]:
        """Check for forbidden patterns in staging URLs."""
        violations = []
        
        staging_urls = {
            'STAGING_BACKEND_URL': URLConstants.STAGING_BACKEND_URL,
            'STAGING_AUTH_URL': URLConstants.STAGING_AUTH_URL,
            'STAGING_FRONTEND_URL': URLConstants.STAGING_FRONTEND_URL,
            'STAGING_WEBSOCKET_URL': URLConstants.STAGING_WEBSOCKET_URL,
        }
        
        for url_name, url_value in staging_urls.items():
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, url_value):
                    violations.append({
                        'type': 'forbidden_pattern_violation',
                        'url_name': url_name,
                        'url_value': url_value,
                        'forbidden_pattern': pattern,
                        'severity': 'high'
                    })
        
        return violations
    
    def _check_staging_url_format_compliance(self) -> List[Dict]:
        """Check staging URL format compliance."""
        violations = []
        
        staging_urls = {
            'STAGING_BACKEND_URL': URLConstants.STAGING_BACKEND_URL,
            'STAGING_AUTH_URL': URLConstants.STAGING_AUTH_URL,
            'STAGING_FRONTEND_URL': URLConstants.STAGING_FRONTEND_URL,
        }
        
        for url_name, url_value in staging_urls.items():
            # Check HTTPS protocol
            if not url_value.startswith("https://"):
                violations.append({
                    'type': 'protocol_violation',
                    'url_name': url_name,
                    'url_value': url_value,
                    'issue': 'Staging URLs must use HTTPS protocol',
                    'severity': 'critical'
                })
            
            # Check staging domain pattern
            if not re.search(r'\.staging\.netrasystems\.ai', url_value):
                violations.append({
                    'type': 'domain_pattern_violation',
                    'url_name': url_name,
                    'url_value': url_value,
                    'issue': 'Staging URLs must use *.staging.netrasystems.ai domain',
                    'severity': 'critical'
                })
        
        return violations
    
    def _get_staging_environment_urls(self) -> Dict[str, str]:
        """Get URLs for staging environment from environment helper."""
        # Mock staging environment for testing
        original_env = os.environ.get('ENVIRONMENT')
        
        try:
            os.environ['ENVIRONMENT'] = 'staging'
            staging_urls = NetworkEnvironmentHelper.get_service_urls_for_environment()
            return staging_urls
        finally:
            if original_env is not None:
                os.environ['ENVIRONMENT'] = original_env
            else:
                os.environ.pop('ENVIRONMENT', None)
    
    def _validate_staging_url(self, url_type: str, url_value: str) -> List[Dict]:
        """Validate a single staging URL for compliance."""
        violations = []
        
        if not url_value:
            violations.append({
                'type': 'empty_url',
                'url_type': url_type,
                'severity': 'critical'
            })
            return violations
        
        # Check for required staging domain
        if '.staging.netrasystems.ai' not in url_value:
            violations.append({
                'type': 'missing_staging_domain',
                'url_type': url_type,
                'url_value': url_value,
                'severity': 'critical'
            })
        
        # Check protocol
        if url_value.startswith('http://') and 'localhost' not in url_value:
            violations.append({
                'type': 'insecure_protocol',
                'url_type': url_type,
                'url_value': url_value,
                'severity': 'high'
            })
        
        return violations
    
    def _build_compliance_violation_report(self, violations: List[Dict]) -> str:
        """Build compliance violation report."""
        report_parts = []
        
        for violation in violations:
            if violation['type'] == 'staging_url_mismatch':
                report_parts.append(
                    f"  {violation['constant_name']}:\n"
                    f"    Expected: {violation['expected_url']}\n"
                    f"    Actual: {violation['actual_url']}"
                )
            elif violation['type'] == 'forbidden_pattern_violation':
                report_parts.append(
                    f"  {violation['url_name']}: {violation['url_value']}\n"
                    f"    Forbidden pattern: {violation['forbidden_pattern']}"
                )
            else:
                report_parts.append(
                    f"  {violation['type']}: {violation.get('description', 'Compliance violation')}"
                )
        
        return "\n".join(report_parts)
    
    def _build_resolution_violation_report(self, violations: List[Dict]) -> str:
        """Build resolution violation report."""
        report_parts = []
        
        for violation in violations:
            report_parts.append(
                f"  {violation['type']}: {violation.get('description', 'Resolution violation')}"
            )
        
        return "\n".join(report_parts)
    
    def _build_cors_violation_report(self, violations: List[Dict]) -> str:
        """Build CORS violation report."""
        report_parts = []
        
        for violation in violations:
            if violation['type'] == 'missing_cors_origins':
                report_parts.append(
                    f"  Missing CORS Origins: {violation['missing_origins']}\n"
                    f"  Current Origins: {violation['current_origins']}"
                )
            elif violation['type'] == 'forbidden_cors_origins':
                report_parts.append(
                    f"  Forbidden CORS Origins: {violation['forbidden_origins']}"
                )
            else:
                report_parts.append(
                    f"  {violation['type']}: {violation.get('description', 'CORS violation')}"
                )
        
        return "\n".join(report_parts)
    
    def _build_websocket_violation_report(self, violations: List[Dict]) -> str:
        """Build WebSocket violation report."""
        report_parts = []
        
        for violation in violations:
            if 'url' in violation:
                report_parts.append(
                    f"  {violation['type']}: {violation['url']}\n"
                    f"    Issue: {violation.get('issue', 'Violation detected')}"
                )
            else:
                report_parts.append(
                    f"  {violation['type']}: {violation.get('description', 'WebSocket violation')}"
                )
        
        return "\n".join(report_parts)


if __name__ == "__main__":
    # Run this test standalone to check network constants staging compliance
    test_instance = TestNetworkConstantsStagingCompliance()
    
    tests = [
        test_instance.test_url_constants_staging_compliance,
        test_instance.test_environment_specific_url_resolution_compliance,
        test_instance.test_cors_origins_staging_compliance,
        test_instance.test_websocket_url_staging_compliance,
    ]
    
    passed_tests = 0
    
    for test_func in tests:
        try:
            test_func()
            print(f"✅ {test_func.__name__} passed")
            passed_tests += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__} failed:\n{e}\n")
        except Exception as e:
            print(f"❌ {test_func.__name__} error: {e}\n")
    
    if passed_tests == len(tests):
        print("✅ All network constants staging compliance tests passed!")
    else:
        print(f"❌ {len(tests) - passed_tests} out of {len(tests)} tests failed")
        exit(1)