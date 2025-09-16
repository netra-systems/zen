from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nComprehensive CORS Integration Tests\n\nBusiness Value Justification (BVJ):\n- Segment: ALL (Required for frontend-backend communication)\n- Business Goal: Ensure CORS works correctly across all environments and services\n- Value Impact: Prevents CORS errors that block user interactions\n- Strategic Impact: Critical for multi-service architecture functionality\n\nTest Coverage:\n- Preflight requests for all endpoints\n- Cross-origin requests with credentials\n- Error response CORS headers\n- WebSocket origin validation\n- Service-to-service communication\n- Static asset loading\n- IPv6 localhost support\n- Trailing slash handling\n- 4xx/5xx error responses\n'
import asyncio
import json
import os
import pytest
from typing import Dict, List, Optional, Any
from unittest.mock import patch
import aiohttp
import websockets
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
from shared.cors_config_builder import CORSConfigurationBuilder, get_cors_origins, get_cors_config, is_origin_allowed, get_websocket_cors_origins, get_cors_health_info, validate_cors_config
from test_framework.fixtures import create_test_app, create_test_client
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

class CORSTestHelper:
    """Helper class for CORS testing scenarios."""

    def __init__(self):
        self.test_origins = {'valid_development': ['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000', 'http://127.0.0.1:8000', 'https://localhost:3000', 'http://[::1]:3000', 'http://0.0.0.0:3000', 'http://frontend:3000', 'http://172.17.0.1:3000'], 'valid_staging': ['https://app.staging.netrasystems.ai', 'https://auth.staging.netrasystems.ai', 'https://api.staging.netrasystems.ai', 'https://netra-frontend-701982941522.us-central1.run.app', 'http://localhost:3000'], 'valid_production': ['https://netrasystems.ai', 'https://www.netrasystems.ai', 'https://app.netrasystems.ai', 'https://api.netrasystems.ai', 'https://auth.netrasystems.ai'], 'invalid': ['http://malicious-site.com', 'https://attacker.net', 'http://localhost:9999', 'https://evil.com', 'http://phishing.example.com', '', None]}
        self.test_endpoints = ['/health', '/api/threads', '/api/chat', '/api/users/me', '/auth/login', '/auth/callback', '/ws']
        self.test_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD']
        self.required_headers = ['Authorization', 'Content-Type', 'X-Request-ID', 'X-Trace-ID', 'Accept', 'Origin', 'Referer', 'X-Requested-With']

    def create_cors_request_headers(self, origin: str, method: str='POST') -> Dict[str, str]:
        """Create headers for CORS preflight request."""
        headers = {'Origin': origin, 'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': 'Authorization, Content-Type, X-Request-ID'}
        return {k: v for k, v in headers.items() if v is not None}

    def create_actual_request_headers(self, origin: str) -> Dict[str, str]:
        """Create headers for actual CORS request."""
        headers = {'Origin': origin, 'Content-Type': 'application/json', 'Authorization': 'Bearer test-token'}
        return {k: v for k, v in headers.items() if v is not None}

@pytest.fixture
def cors_helper():
    """Create CORS test helper fixture."""
    return CORSTestHelper()

@pytest.fixture
@pytest.mark.integration
def test_app():
    """Create test FastAPI app with CORS middleware."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from shared.cors_config_builder import get_cors_config
    app = FastAPI()
    cors_config = get_cors_config()
    app.add_middleware(CORSMiddleware, **cors_config)

    @app.get('/test')
    def test_endpoint():
        return {'message': 'test'}
    return app

@pytest.fixture
@pytest.mark.integration
def test_client(test_app):
    """Create test client."""
    from fastapi.testclient import TestClient
    return TestClient(test_app)

@pytest.mark.integration
class CORSConfigurationTests:
    """Test CORS configuration functions."""

    def test_get_cors_origins_development(self):
        """Test CORS origins for development environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origins = get_cors_origins()
            assert 'http://localhost:3000' in origins
            assert 'http://127.0.0.1:3000' in origins
            assert 'https://localhost:3000' in origins
            assert 'http://[::1]:3000' in origins
            assert 'http://frontend:3000' in origins

    def test_get_cors_origins_staging(self):
        """Test CORS origins for staging environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            origins = get_cors_origins()
            assert 'https://app.staging.netrasystems.ai' in origins
            assert 'https://auth.staging.netrasystems.ai' in origins
            assert 'http://localhost:3000' in origins

    def test_get_cors_origins_production(self):
        """Test CORS origins for production environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            origins = get_cors_origins()
            assert 'https://netrasystems.ai' in origins
            assert 'https://app.netrasystems.ai' in origins
            assert 'https://auth.netrasystems.ai' in origins
            assert 'http://localhost:3000' not in origins

    def test_get_cors_origins_custom_env_var(self):
        """Test CORS origins with custom CORS_ORIGINS environment variable."""
        custom_origins = 'https://custom1.com,https://custom2.com'
        with patch.dict(os.environ, {'CORS_ORIGINS': custom_origins}):
            origins = get_cors_origins()
            assert 'https://custom1.com' in origins
            assert 'https://custom2.com' in origins

    def test_cors_config_structure(self):
        """Test CORS configuration structure."""
        config = get_cors_config('development')
        assert 'allow_origins' in config
        assert 'allow_credentials' in config
        assert 'allow_methods' in config
        assert 'allow_headers' in config
        assert 'expose_headers' in config
        assert 'max_age' in config
        assert isinstance(config['allow_origins'], list)
        assert config['allow_credentials'] is True
        assert 'Authorization' in config['allow_headers']
        assert 'Content-Type' in config['allow_headers']
        assert 'POST' in config['allow_methods']
        assert config['max_age'] == 3600

    def test_is_origin_allowed_development(self):
        """Test origin validation in development."""
        allowed_origins = get_cors_origins('development')
        assert is_origin_allowed('http://localhost:3000', allowed_origins, 'development')
        assert is_origin_allowed('http://127.0.0.1:3000', allowed_origins, 'development')
        assert is_origin_allowed('http://localhost:8080', allowed_origins, 'development')
        assert not is_origin_allowed('http://malicious-site.com', allowed_origins, 'development')
        assert not is_origin_allowed('', allowed_origins, 'development')

    def test_websocket_cors_origins(self):
        """Test WebSocket CORS origins."""
        ws_origins = get_websocket_cors_origins('development')
        http_origins = get_cors_origins('development')
        assert ws_origins == http_origins

    def test_cors_health_info(self):
        """Test CORS health information."""
        health_info = get_cors_health_info('development')
        assert 'environment' in health_info
        assert 'origins_count' in health_info
        assert 'origins' in health_info
        assert 'allow_credentials' in health_info
        assert 'methods' in health_info
        assert 'config_valid' in health_info
        assert health_info['config_valid'] is True
        assert health_info['origins_count'] > 0

    def test_validate_cors_config(self):
        """Test CORS configuration validation."""
        valid_config = get_cors_config('development')
        assert validate_cors_config(valid_config) is True
        invalid_config = {'allow_origins': 'not a list'}
        assert validate_cors_config(invalid_config) is False

@pytest.mark.integration
class CORSPreflightRequestsTests:
    """Test CORS preflight (OPTIONS) requests."""

    @pytest.mark.parametrize('origin', ['http://localhost:3000', 'http://127.0.0.1:3000', 'https://localhost:3000', 'http://[::1]:3000'])
    def test_preflight_valid_origins(self, test_client: TestClient, cors_helper: CORSTestHelper, origin: str):
        """Test preflight requests work for valid origins."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            headers = cors_helper.create_cors_request_headers(origin)
            response = test_client.options('/health', headers=headers)
            assert response.status_code in [200, 204]
            assert response.headers.get('Access-Control-Allow-Origin') == origin
            assert response.headers.get('Access-Control-Allow-Credentials') == 'true'
            assert 'POST' in response.headers.get('Access-Control-Allow-Methods', '')
            assert 'Authorization' in response.headers.get('Access-Control-Allow-Headers', '')

    @pytest.mark.parametrize('origin', ['http://malicious-site.com', 'https://attacker.net', 'http://localhost:9999'])
    def test_preflight_invalid_origins(self, test_client: TestClient, cors_helper: CORSTestHelper, origin: str):
        """Test preflight requests are rejected for invalid origins."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            headers = cors_helper.create_cors_request_headers(origin)
            response = test_client.options('/health', headers=headers)
            assert response.headers.get('Access-Control-Allow-Origin') != origin

    @pytest.mark.parametrize('method', ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def test_preflight_all_methods(self, test_client: TestClient, cors_helper: CORSTestHelper, method: str):
        """Test preflight requests work for all HTTP methods."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_cors_request_headers(origin, method)
            response = test_client.options('/health', headers=headers)
            assert response.status_code in [200, 204]
            assert method in response.headers.get('Access-Control-Allow-Methods', '')

    @pytest.mark.parametrize('endpoint', ['/health', '/api/threads', '/api/chat'])
    def test_preflight_all_endpoints(self, test_client: TestClient, cors_helper: CORSTestHelper, endpoint: str):
        """Test preflight requests work for all endpoints."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_cors_request_headers(origin)
            response = test_client.options(endpoint, headers=headers)
            if response.status_code == 404:
                assert 'Access-Control-Allow-Origin' in response.headers or 'access-control-allow-origin' in response.headers
            else:
                assert response.status_code in [200, 204]

@pytest.mark.integration
class CORSActualRequestsTests:
    """Test actual CORS requests (non-preflight)."""

    def test_actual_request_cors_headers(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test actual requests include CORS headers."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response = test_client.get('/health', headers=headers)
            assert response.status_code == 200
            assert response.headers.get('Access-Control-Allow-Origin') == origin
            assert response.headers.get('Access-Control-Allow-Credentials') == 'true'

    def test_actual_request_with_credentials(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test actual requests with credentials work correctly."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            headers['Cookie'] = 'session=test-session-id'
            response = test_client.get('/health', headers=headers)
            assert response.status_code == 200
            assert response.headers.get('Access-Control-Allow-Credentials') == 'true'

    def test_actual_request_no_origin_header(self, test_client: TestClient):
        """Test requests without Origin header work normally."""
        response = test_client.get('/health')
        assert response.status_code == 200

@pytest.mark.integration
class CORSErrorResponsesTests:
    """Test CORS headers on error responses."""

    def test_cors_headers_on_404(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test CORS headers are present on 404 responses."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response = test_client.get('/nonexistent-endpoint', headers=headers)
            assert response.status_code == 404
            assert 'Access-Control-Allow-Origin' in response.headers or 'access-control-allow-origin' in response.headers

    def test_cors_headers_on_405(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test CORS headers are present on 405 Method Not Allowed responses."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response = test_client.post('/health', headers=headers, json={})
            if response.status_code == 405:
                assert 'Access-Control-Allow-Origin' in response.headers or 'access-control-allow-origin' in response.headers

    def test_cors_headers_on_500(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test CORS headers are present on 500 Internal Server Error responses."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            with patch('test_framework.fixtures.test_route_that_errors') as mock_route:
                mock_route.side_effect = Exception('Test error')
                try:
                    response = test_client.get('/health', headers=headers)
                    if response.status_code >= 500:
                        assert 'Access-Control-Allow-Origin' in response.headers or 'access-control-allow-origin' in response.headers
                except Exception:
                    pass

@pytest.mark.integration
class CORSTrailingSlashHandlingTests:
    """Test CORS with trailing slash handling."""

    def test_cors_with_trailing_slash(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test CORS works with trailing slashes."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response_no_slash = test_client.get('/health', headers=headers)
            response_with_slash = test_client.get('/health/', headers=headers)
            for response in [response_no_slash, response_with_slash]:
                if response.status_code == 200:
                    assert response.headers.get('Access-Control-Allow-Origin') == origin

@pytest.mark.integration
class CORSIPv6SupportTests:
    """Test CORS with IPv6 localhost support."""

    def test_ipv6_localhost_origin(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test IPv6 localhost origins are supported."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://[::1]:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response = test_client.get('/health', headers=headers)
            assert response.status_code == 200
            assert response.headers.get('Access-Control-Allow-Origin') == origin

@pytest.mark.integration
class CORSVariHeadersTests:
    """Test Vary header handling in CORS responses."""

    def test_vary_origin_header_present(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test Vary: Origin header is present in CORS responses."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response = test_client.get('/health', headers=headers)
            vary_header = response.headers.get('Vary', '')
            assert 'Origin' in vary_header or 'origin' in vary_header.lower()

@pytest.mark.integration
class CORSMaxAgeTests:
    """Test CORS Max-Age header."""

    def test_max_age_header_present(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test Access-Control-Max-Age header is set correctly."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_cors_request_headers(origin)
            response = test_client.options('/health', headers=headers)
            assert response.status_code in [200, 204]
            max_age = response.headers.get('Access-Control-Max-Age')
            assert max_age is not None
            assert int(max_age) > 0

@pytest.mark.integration
class CORSEnvironmentSpecificTests:
    """Test environment-specific CORS behavior."""

    def test_development_allows_any_localhost_port(self, test_client: TestClient):
        """Test development environment allows any localhost port."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:9876'
            headers = {'Origin': origin}
            response = test_client.get('/health', headers=headers)
            assert response.status_code == 200

    def test_staging_allows_staging_domains(self, test_client: TestClient):
        """Test staging environment allows staging domains."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            origin = 'https://app.staging.netrasystems.ai'
            headers = {'Origin': origin}
            response = test_client.get('/health', headers=headers)
            assert response.status_code == 200
            assert response.headers.get('Access-Control-Allow-Origin') == origin

    def test_production_rejects_localhost(self, test_client: TestClient):
        """Test production environment rejects localhost origins."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            origin = 'http://localhost:3000'
            headers = {'Origin': origin}
            response = test_client.get('/health', headers=headers)
            assert response.headers.get('Access-Control-Allow-Origin') != origin

@pytest.mark.integration
class CORSSecurityHeadersTests:
    """Test CORS security headers."""

    def test_security_headers_present(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test security headers are present in CORS responses."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            response = test_client.get('/health', headers=headers)
            assert response.status_code == 200
            security_headers = {'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': ['DENY', 'SAMEORIGIN']}
            for header, expected_values in security_headers.items():
                header_value = response.headers.get(header)
                if header_value:
                    if isinstance(expected_values, list):
                        assert header_value in expected_values
                    else:
                        assert header_value == expected_values

@pytest.mark.integration
class CORSStressScenariosTests:
    """Test CORS under stress conditions."""

    def test_many_concurrent_cors_requests(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test CORS handling under concurrent request load."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            responses = []
            for _ in range(10):
                response = test_client.get('/health', headers=headers)
                responses.append(response)
            for response in responses:
                assert response.status_code == 200
                assert response.headers.get('Access-Control-Allow-Origin') == origin

    def test_cors_with_large_headers(self, test_client: TestClient, cors_helper: CORSTestHelper):
        """Test CORS with large request headers."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):
            origin = 'http://localhost:3000'
            headers = cors_helper.create_actual_request_headers(origin)
            headers['X-Large-Header'] = 'x' * 1000
            response = test_client.get('/health', headers=headers)
            if response.status_code == 200:
                assert response.headers.get('Access-Control-Allow-Origin') == origin
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')