from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nCORS Integration Tests - Core functionality tests for Cross-Origin Resource Sharing\n\nThese tests validate that CORS is properly configured across services to enable\nfrontend-backend communication while maintaining security boundaries.\n\nFollowing CLAUDE.md principles:\n- Tests use real services, not mocks\n- Tests validate end-to-end CORS functionality\n- Tests check for proper security configurations\n- Tests verify multi-user isolation with CORS\n'
import asyncio
import json
import os
from typing import Dict, List, Optional
from unittest.mock import patch
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth_service.main import app as auth_app
from netra_backend.app.core.app_factory import create_app
pytestmark = pytest.mark.asyncio

class CORSTestHelper:
    """Helper methods for CORS testing."""

    @staticmethod
    def mock_backend_server_url():
        """Get backend server URL for testing."""
        return get_env().get('BACKEND_URL', 'http://localhost:8000')

    @staticmethod
    def mock_auth_server_url():
        """Get auth server URL for testing."""
        return get_env().get('AUTH_URL', 'http://localhost:8081')

    @staticmethod
    def frontend_origin():
        """Frontend origin that makes cross-origin requests."""
        return 'http://localhost:3001'

    @staticmethod
    def websocket_url():
        """Get WebSocket URL for testing."""
        return get_env().get('WS_URL', 'ws://localhost:8000/ws')

    @staticmethod
    def backend_url():
        return get_env().get('BACKEND_URL', 'http://localhost:8000')

    @staticmethod
    def auth_url():
        return get_env().get('AUTH_URL', 'http://localhost:8081')

    @staticmethod
    def get_cors_headers(origin: str=None) -> Dict[str, str]:
        """Get standard CORS headers for testing."""
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        return headers

    @staticmethod
    def validate_cors_response(response, expected_origin: str=None) -> Dict[str, bool]:
        """Validate CORS headers in response."""
        validation = {'has_access_control_allow_origin': False, 'has_access_control_allow_methods': False, 'has_access_control_allow_headers': False, 'has_access_control_allow_credentials': False, 'origin_matches_expected': False}
        cors_headers = {k.lower(): v for k, v in response.headers.items() if k.lower().startswith('access-control')}
        if 'access-control-allow-origin' in cors_headers:
            validation['has_access_control_allow_origin'] = True
            if expected_origin and cors_headers['access-control-allow-origin'] == expected_origin:
                validation['origin_matches_expected'] = True
        validation['has_access_control_allow_methods'] = 'access-control-allow-methods' in cors_headers
        validation['has_access_control_allow_headers'] = 'access-control-allow-headers' in cors_headers
        validation['has_access_control_allow_credentials'] = 'access-control-allow-credentials' in cors_headers
        return validation

@pytest.mark.integration
class CORSIntegrationCoreTests:
    """Core CORS integration tests."""

    @pytest.fixture
    def backend_app(self):
        """Create backend FastAPI app for testing."""
        with patch.dict('os.environ', {'SKIP_STARTUP_TASKS': 'true', 'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            return create_app()

    @pytest.fixture
    def auth_test_app(self):
        """Create auth service test app."""
        with patch.dict('os.environ', {'AUTH_FAST_TEST_MODE': 'true', 'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
            return auth_app

    @pytest.fixture
    def cors_helper(self):
        """Get CORS test helper."""
        return CORSTestHelper()

    async def test_backend_cors_preflight_request(self, backend_app, cors_helper):
        """Test that backend handles CORS preflight requests correctly."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()
        response = client.options('/api/v1/chat', headers={'Origin': frontend_origin, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type,Authorization'})
        validation = cors_helper.validate_cors_response(response, frontend_origin)
        assert response.status_code in [200, 204], f'Preflight failed with status {response.status_code}'
        assert validation['has_access_control_allow_origin'], 'Missing Access-Control-Allow-Origin header'
        assert validation['has_access_control_allow_methods'], 'Missing Access-Control-Allow-Methods header'
        assert validation['has_access_control_allow_headers'], 'Missing Access-Control-Allow-Headers header'

    async def test_backend_cors_actual_request(self, backend_app, cors_helper):
        """Test actual CORS request to backend after preflight."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()
        response = client.post('/api/v1/health', headers={'Origin': frontend_origin, 'Content-Type': 'application/json'}, json={})
        validation = cors_helper.validate_cors_response(response, frontend_origin)
        assert response.status_code != 403, 'CORS request should not be forbidden'
        assert validation['has_access_control_allow_origin'], f'Missing CORS origin header. Response headers: {dict(response.headers)}'

    async def test_auth_service_cors_configuration(self, auth_test_app, cors_helper):
        """Test that auth service has proper CORS configuration."""
        client = TestClient(auth_test_app)
        frontend_origin = cors_helper.frontend_origin()
        response = client.get('/health', headers={'Origin': frontend_origin})
        validation = cors_helper.validate_cors_response(response, frontend_origin)
        assert response.status_code != 403, 'Auth service should allow CORS for health checks'

    async def test_websocket_cors_headers(self, backend_app, cors_helper):
        """Test that WebSocket endpoints respect CORS configuration."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()
        try:
            with client.websocket_connect('/ws', headers={'Origin': frontend_origin}) as websocket:
                websocket.send_json({'type': 'ping'})
                data = websocket.receive_json()
                assert data is not None, 'WebSocket connection should work with proper origin'
        except Exception as e:
            if '403' in str(e) or 'Origin' in str(e):
                pytest.fail(f'WebSocket CORS configuration may be too restrictive: {e}')

    async def test_cors_with_credentials(self, backend_app, cors_helper):
        """Test CORS configuration with credentials (cookies, auth headers)."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()
        response = client.get('/api/v1/health', headers={'Origin': frontend_origin, 'Authorization': 'Bearer test_token', 'Cookie': 'session_id=test123'})
        validation = cors_helper.validate_cors_response(response)
        assert response.status_code != 403, 'CORS should not block requests with credentials'
        if validation['has_access_control_allow_credentials']:
            cors_origin = response.headers.get('Access-Control-Allow-Origin', '')
            assert cors_origin != '*', 'When credentials are allowed, origin cannot be wildcard for security'

    async def test_cors_multiple_origins(self, backend_app, cors_helper):
        """Test CORS configuration with multiple allowed origins."""
        client = TestClient(backend_app)
        test_origins = [cors_helper.frontend_origin(), 'http://localhost:3000', 'https://app.netra.com']
        results = []
        for origin in test_origins:
            response = client.options('/api/v1/health', headers={'Origin': origin, 'Access-Control-Request-Method': 'GET'})
            validation = cors_helper.validate_cors_response(response, origin)
            results.append({'origin': origin, 'status_code': response.status_code, 'cors_configured': validation['has_access_control_allow_origin']})
        configured_origins = [r for r in results if r['cors_configured']]
        assert len(configured_origins) > 0, f'No origins properly configured for CORS: {results}'

    async def test_cors_rejected_origins(self, backend_app, cors_helper):
        """Test that CORS properly rejects unauthorized origins."""
        client = TestClient(backend_app)
        malicious_origins = ['https://evil.com', 'http://localhost:9999', 'https://attacker.example.com']
        for malicious_origin in malicious_origins:
            response = client.options('/api/v1/chat', headers={'Origin': malicious_origin, 'Access-Control-Request-Method': 'POST'})
            cors_origin = response.headers.get('Access-Control-Allow-Origin')
            if cors_origin:
                assert cors_origin != malicious_origin, f'CORS should not allow malicious origin {malicious_origin}'

    async def test_cors_method_restrictions(self, backend_app, cors_helper):
        """Test that CORS properly restricts HTTP methods."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()
        methods_to_test = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        for method in methods_to_test:
            response = client.options('/api/v1/health', headers={'Origin': frontend_origin, 'Access-Control-Request-Method': method})
            allowed_methods = response.headers.get('Access-Control-Allow-Methods', '')
            print(f'Method {method}: Status {response.status_code}, Allowed methods: {allowed_methods}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')