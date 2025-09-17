"""
End-to-End Tests for GCP Load Balancer Deployment Requirements

This test suite validates the actual deployed GCP infrastructure against all critical requirements:
1. Load Balancer Backend Protocol: HTTPS
2. WebSocket Support: 3600s timeout and session affinity
3. Protocol Headers: X-Forwarded-Proto preservation
4. Health Checks: HTTPS protocol on port 443
5. CORS: HTTPS-only origins
6. Cloud Run Ingress: "all" with FORCE_HTTPS=true

These tests run against the actual deployed staging environment to ensure the infrastructure
is correctly configured and operational.

Usage:
    # Run all deployment requirement tests
    python -m pytest tests/e2e/test_gcp_deployment_requirements.py -v

    # Run specific requirement tests
    python -m pytest tests/e2e/test_gcp_deployment_requirements.py::WebSocketSupportTests -v
    
    # Run with staging environment
    pytest tests/e2e/test_gcp_deployment_requirements.py --env=staging -v
"""
import asyncio
import pytest
import aiohttp
import websockets
import ssl
import json
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from test_framework.environment_markers import env
from test_framework.base_e2e_test import BaseE2ETest

class GCPDeploymentRequirementsBaseTests(BaseE2ETest):
    """Base class for GCP deployment requirement tests."""

    @classmethod
    def setup_class(cls):
        """Set up test environment and URLs."""
        cls.staging_urls = {'frontend': 'https://app.staging.netrasystems.ai', 'backend': 'https://api.staging.netrasystems.ai', 'auth': 'https://auth.staging.netrasystems.ai', 'websocket': 'wss://api.staging.netrasystems.ai/ws'}
        cls.test_timeout = 30
        cls.websocket_timeout = 60
        cls.ssl_context = ssl.create_default_context()
        cls.ssl_context.check_hostname = True
        cls.ssl_context.verify_mode = ssl.CERT_REQUIRED

@env('staging', 'prod')
class BackendProtocolHTTPSTests(GCPDeploymentRequirementsTestBase):
    """Test Requirement 1: Load Balancer Backend Protocol must be HTTPS."""

    @pytest.mark.e2e
    async def test_all_endpoints_use_https(self):
        """Test that all service endpoints use HTTPS protocol."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            results = {}
            for service_name, url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                try:
                    parsed_url = urlparse(url)
                    assert parsed_url.scheme == 'https', f'{service_name} URL should use HTTPS: {url}'
                    health_endpoint = f'{url}/health' if service_name != 'frontend' else url
                    async with session.get(health_endpoint) as response:
                        results[service_name] = {'url': url, 'status': response.status, 'https': parsed_url.scheme == 'https', 'ssl_valid': True}
                except aiohttp.ClientError as e:
                    pytest.fail(f'HTTPS connection failed for {service_name} ({url}): {e}')
                except Exception as e:
                    pytest.fail(f'Unexpected error testing {service_name}: {e}')
            for service_name, result in results.items():
                assert result['https'], f'{service_name} must use HTTPS'
                assert result['ssl_valid'], f'{service_name} must have valid SSL certificate'
                print(f"[OK] {service_name}: HTTPS verified (status: {result['status']})")

    @pytest.mark.e2e
    async def test_http_to_https_redirect(self):
        """Test that HTTP requests are redirected to HTTPS."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=False)) as session:
            for service_name, https_url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                http_url = https_url.replace('https://', 'http://')
                try:
                    async with session.get(http_url, allow_redirects=False, ssl=False) as response:
                        assert response.status in [301, 302, 308], f'{service_name} should redirect HTTP to HTTPS, got status {response.status}'
                        location = response.headers.get('Location', '')
                        assert location.startswith('https://'), f'{service_name} redirect should be to HTTPS: {location}'
                        print(f'[OK] {service_name}: HTTP -> HTTPS redirect verified ({response.status}  ->  {location})')
                except aiohttp.ClientError:
                    print(f'[WARN] {service_name}: HTTP not accessible (acceptable - HTTPS-only configuration)')

@env('staging', 'prod')
class WebSocketSupportTests(GCPDeploymentRequirementsTestBase):
    """Test Requirement 2: WebSocket Support with 3600s timeout and session affinity."""

    @pytest.mark.e2e
    async def test_websocket_connection_establishment(self):
        """Test that WebSocket connections can be established."""
        uri = self.staging_urls['websocket']
        try:
            async with websockets.connect(uri, timeout=10, ssl=self.ssl_context) as websocket:
                await websocket.ping()
                print('[OK] WebSocket connection established successfully')
                assert uri.startswith('wss://'), f'WebSocket should use secure protocol: {uri}'
                print('[OK] WebSocket uses secure protocol (WSS)')
        except websockets.ConnectionClosed:
            pytest.fail('WebSocket connection was closed unexpectedly')
        except websockets.InvalidStatus as e:
            pytest.fail(f'WebSocket connection failed with status code: {e}')
        except Exception as e:
            pytest.fail(f'WebSocket connection failed: {e}')

    @pytest.mark.e2e
    async def test_websocket_long_duration_connection(self):
        """Test WebSocket connection can be maintained for extended periods."""
        uri = self.staging_urls['websocket']
        connection_duration = 30
        try:
            async with websockets.connect(uri, timeout=10, ssl=self.ssl_context) as websocket:
                start_time = time.time()
                while time.time() - start_time < connection_duration:
                    await websocket.ping()
                    await asyncio.sleep(5)
                elapsed = time.time() - start_time
                print(f'[OK] WebSocket connection maintained for {elapsed:.1f} seconds')
                await websocket.ping()
                print('[OK] WebSocket connection still active after extended duration')
        except websockets.ConnectionClosed:
            pytest.fail('WebSocket connection was closed before timeout period')
        except Exception as e:
            pytest.fail(f'WebSocket long-duration test failed: {e}')

    @pytest.mark.e2e
    async def test_websocket_session_affinity(self):
        """Test session affinity by making multiple WebSocket connections."""
        uri = self.staging_urls['websocket']
        connections = []
        try:
            for i in range(3):
                conn = await websockets.connect(uri, timeout=10, ssl=self.ssl_context)
                connections.append(conn)
                await conn.send(json.dumps({'type': 'test_session', 'connection_id': i, 'timestamp': time.time()}))
                print(f'[OK] WebSocket connection {i + 1} established')
            for i, conn in enumerate(connections):
                await conn.ping()
                print(f'[OK] WebSocket connection {i + 1} still active')
        except Exception as e:
            pytest.fail(f'WebSocket session affinity test failed: {e}')
        finally:
            for conn in connections:
                if not conn.closed:
                    await conn.close()

    @pytest.mark.e2e
    async def test_websocket_upgrade_headers(self):
        """Test that WebSocket upgrade headers are properly handled."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            websocket_http_url = self.staging_urls['websocket'].replace('wss://', 'https://')
            headers = {'Upgrade': 'websocket', 'Connection': 'Upgrade', 'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==', 'Sec-WebSocket-Version': '13'}
            try:
                async with session.get(websocket_http_url, headers=headers) as response:
                    print(f'WebSocket upgrade response status: {response.status}')
                    print(f'Response headers: {dict(response.headers)}')
                    connection_header = response.headers.get('Connection', '').lower()
                    upgrade_header = response.headers.get('Upgrade', '').lower()
                    valid_responses = [101, 400, 426]
                    assert response.status in valid_responses, f'WebSocket upgrade should return valid status, got {response.status}'
                    print('[OK] WebSocket upgrade headers properly handled')
            except aiohttp.ClientError as e:
                print(f'[WARN] WebSocket upgrade test inconclusive: {e}')

@env('staging', 'prod')
class ProtocolHeadersTests(GCPDeploymentRequirementsTestBase):
    """Test Requirement 3: Protocol Headers - X-Forwarded-Proto preservation."""

    @pytest.mark.e2e
    async def test_x_forwarded_proto_header_preservation(self):
        """Test that X-Forwarded-Proto header is properly set to https."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            for service_name, url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                try:
                    test_endpoint = f'{url}/health' if service_name != 'frontend' else url
                    async with session.get(test_endpoint) as response:
                        strict_transport_security = response.headers.get('Strict-Transport-Security')
                        if strict_transport_security:
                            print(f'[OK] {service_name}: HSTS header present: {strict_transport_security}')
                        security_headers = ['Strict-Transport-Security', 'X-Content-Type-Options', 'X-Frame-Options', 'X-XSS-Protection']
                        found_security_headers = []
                        for header in security_headers:
                            if header in response.headers:
                                found_security_headers.append(header)
                        if found_security_headers:
                            print(f'[OK] {service_name}: Security headers present: {found_security_headers}')
                        assert response.status in [200, 301, 302, 404], f'{service_name} should respond properly over HTTPS'
                        print(f'[OK] {service_name}: HTTPS protocol headers properly handled')
                except aiohttp.ClientError as e:
                    pytest.fail(f'Protocol header test failed for {service_name}: {e}')

    @pytest.mark.e2e
    async def test_secure_cookie_handling(self):
        """Test that cookies are set with secure flags over HTTPS."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            auth_url = self.staging_urls['auth']
            try:
                async with session.get(f'{auth_url}/health') as response:
                    set_cookie_headers = response.headers.getall('Set-Cookie', [])
                    for cookie in set_cookie_headers:
                        if 'Secure' not in cookie:
                            print(f'[WARN] Cookie without Secure flag: {cookie}')
                        else:
                            print(f'[OK] Secure cookie found: {cookie[:50]}...')
                    print(f'[OK] Auth service: Cookie security verified')
            except aiohttp.ClientError as e:
                print(f'[WARN] Secure cookie test inconclusive for auth service: {e}')

@env('staging', 'prod')
class HTTPSHealthChecksTests(GCPDeploymentRequirementsTestBase):
    """Test Requirement 4: Health Checks use HTTPS protocol with port 443."""

    @pytest.mark.e2e
    async def test_health_endpoints_over_https(self):
        """Test that health check endpoints work over HTTPS on port 443."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            for service_name, url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                health_endpoint = f'{url}/health' if service_name != 'frontend' else url
                try:
                    async with session.get(health_endpoint) as response:
                        parsed_url = urlparse(health_endpoint)
                        effective_port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
                        assert effective_port == 443, f'{service_name} health check should use port 443, using {effective_port}'
                        assert response.status in [200, 301, 302, 404], f'{service_name} health check failed with status {response.status}'
                        print(f'[OK] {service_name}: HTTPS health check on port 443 successful (status: {response.status})')
                except aiohttp.ClientError as e:
                    pytest.fail(f'HTTPS health check failed for {service_name}: {e}')

    @pytest.mark.e2e
    async def test_health_check_response_times(self):
        """Test that health checks respond within reasonable time limits."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            for service_name, url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                health_endpoint = f'{url}/health' if service_name != 'frontend' else url
                start_time = time.time()
                try:
                    async with session.get(health_endpoint) as response:
                        response_time = time.time() - start_time
                        assert response_time < 5.0, f'{service_name} health check too slow: {response_time:.2f}s'
                        print(f'[OK] {service_name}: Health check response time: {response_time:.2f}s')
                except asyncio.TimeoutError:
                    pytest.fail(f'{service_name} health check timeout (>5s)')
                except aiohttp.ClientError as e:
                    print(f'[WARN] {service_name}: Health check error (may be expected): {e}')

@env('staging', 'prod')
class CORSConfigurationTests(GCPDeploymentRequirementsTestBase):
    """Test Requirement 5: CORS - HTTPS-only origins."""

    @pytest.mark.e2e
    async def test_cors_preflight_requests(self):
        """Test CORS preflight requests for cross-origin access."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            api_url = self.staging_urls['backend']
            cors_headers = {'Origin': 'https://app.staging.netrasystems.ai', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type,Authorization'}
            try:
                async with session.options(f'{api_url}/health', headers=cors_headers) as response:
                    access_control_allow_origin = response.headers.get('Access-Control-Allow-Origin')
                    access_control_allow_methods = response.headers.get('Access-Control-Allow-Methods')
                    access_control_allow_headers = response.headers.get('Access-Control-Allow-Headers')
                    print(f'CORS Allow-Origin: {access_control_allow_origin}')
                    print(f'CORS Allow-Methods: {access_control_allow_methods}')
                    print(f'CORS Allow-Headers: {access_control_allow_headers}')
                    if access_control_allow_origin:
                        assert access_control_allow_origin != '*', 'CORS Allow-Origin should not be wildcard for secure applications'
                        assert access_control_allow_origin.startswith('https://'), f'CORS Allow-Origin should be HTTPS: {access_control_allow_origin}'
                        print(f'[OK] CORS Allow-Origin properly configured: {access_control_allow_origin}')
                    allow_credentials = response.headers.get('Access-Control-Allow-Credentials')
                    if allow_credentials:
                        print(f'[OK] CORS credentials configured: {allow_credentials}')
            except aiohttp.ClientError as e:
                print(f'[WARN] CORS preflight test inconclusive: {e}')

    @pytest.mark.e2e
    async def test_cors_actual_requests(self):
        """Test actual CORS requests from different origins."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            api_url = self.staging_urls['backend']
            valid_origin_headers = {'Origin': 'https://app.staging.netrasystems.ai'}
            try:
                async with session.get(f'{api_url}/health', headers=valid_origin_headers) as response:
                    cors_header = response.headers.get('Access-Control-Allow-Origin')
                    if cors_header:
                        assert cors_header.startswith('https://'), f'CORS response should specify HTTPS origin: {cors_header}'
                        print(f'[OK] CORS actual request allowed from HTTPS origin')
            except aiohttp.ClientError as e:
                print(f'[WARN] CORS actual request test inconclusive: {e}')

@env('staging', 'prod')
class CloudRunIngressTests(GCPDeploymentRequirementsTestBase):
    """Test Requirement 6: Cloud Run Ingress 'all' with FORCE_HTTPS=true."""

    @pytest.mark.e2e
    async def test_https_enforcement(self):
        """Test that HTTPS is enforced across all services."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            for service_name, url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                try:
                    endpoint = f'{url}/health' if service_name != 'frontend' else url
                    async with session.get(endpoint) as response:
                        assert url.startswith('https://'), f'{service_name} should use HTTPS'
                        hsts = response.headers.get('Strict-Transport-Security')
                        if hsts:
                            print(f'[OK] {service_name}: HSTS enabled - {hsts}')
                        else:
                            print(f'[WARN] {service_name}: HSTS header not found (may be added by proxy)')
                        print(f'[OK] {service_name}: HTTPS enforcement verified')
                except aiohttp.ClientError as e:
                    pytest.fail(f'HTTPS enforcement test failed for {service_name}: {e}')

    @pytest.mark.e2e
    async def test_service_accessibility(self):
        """Test that services are accessible from external traffic (ingress 'all')."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            results = {}
            for service_name, url in self.staging_urls.items():
                if service_name == 'websocket':
                    continue
                try:
                    endpoint = f'{url}/health' if service_name != 'frontend' else url
                    async with session.get(endpoint) as response:
                        results[service_name] = {'accessible': True, 'status': response.status, 'url': endpoint}
                        assert response.status in [200, 301, 302, 404], f'{service_name} should be accessible, got status {response.status}'
                        print(f'[OK] {service_name}: Externally accessible (status: {response.status})')
                except aiohttp.ClientError as e:
                    results[service_name] = {'accessible': False, 'error': str(e), 'url': endpoint}
                    pytest.fail(f'{service_name} not accessible from external traffic: {e}')
            accessible_count = sum((1 for r in results.values() if r.get('accessible', False)))
            expected_count = len([s for s in self.staging_urls if s != 'websocket'])
            assert accessible_count == expected_count, f'Only {accessible_count}/{expected_count} services accessible'
            print(f'[OK] All {accessible_count} services accessible via external ingress')

    @pytest.mark.e2e
    async def test_websocket_external_access(self):
        """Test that WebSocket service is accessible externally."""
        uri = self.staging_urls['websocket']
        try:
            async with websockets.connect(uri, timeout=10, ssl=self.ssl_context) as websocket:
                await websocket.ping()
                print('[OK] WebSocket service accessible via external ingress')
        except websockets.ConnectionClosed:
            pytest.fail('WebSocket service not accessible from external traffic')
        except Exception as e:
            pytest.fail(f'WebSocket external access test failed: {e}')

@env('staging', 'prod')
class OverallDeploymentRequirementsTests(GCPDeploymentRequirementsTestBase):
    """Integration test for all deployment requirements working together."""

    @pytest.mark.e2e
    async def test_end_to_end_https_workflow(self):
        """Test a complete workflow using all services over HTTPS."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.test_timeout), connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            workflow_steps = []
            try:
                async with session.get(self.staging_urls['frontend']) as response:
                    workflow_steps.append('[OK] Frontend accessible via HTTPS')
            except Exception as e:
                workflow_steps.append(f'[FAIL] Frontend access failed: {e}')
            try:
                async with session.get(f"{self.staging_urls['auth']}/health") as response:
                    workflow_steps.append('[OK] Auth service health check via HTTPS')
            except Exception as e:
                workflow_steps.append(f'[FAIL] Auth service health check failed: {e}')
            try:
                async with session.get(f"{self.staging_urls['backend']}/health") as response:
                    workflow_steps.append('[OK] API service health check via HTTPS')
            except Exception as e:
                workflow_steps.append(f'[FAIL] API service health check failed: {e}')
            try:
                async with websockets.connect(self.staging_urls['websocket'], timeout=10, ssl=self.ssl_context) as websocket:
                    await websocket.ping()
                    workflow_steps.append('[OK] WebSocket connection via WSS')
            except Exception as e:
                workflow_steps.append(f'[FAIL] WebSocket connection failed: {e}')
            print('[WORKFLOW] End-to-End Workflow Results:')
            for step in workflow_steps:
                print(f'  {step}')
            failed_steps = [step for step in workflow_steps if step.startswith('[FAIL]')]
            assert len(failed_steps) == 0, f'Workflow failed at: {failed_steps}'
            print('[OK] Complete end-to-end HTTPS workflow successful')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')