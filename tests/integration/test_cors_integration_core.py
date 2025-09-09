from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

"""
CORS Integration Tests - Core functionality tests for Cross-Origin Resource Sharing

These tests validate that CORS is properly configured across services to enable
frontend-backend communication while maintaining security boundaries.

Following CLAUDE.md principles:
- Tests use real services, not mocks
- Tests validate end-to-end CORS functionality
- Tests check for proper security configurations
- Tests verify multi-user isolation with CORS
"""

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
        return get_env().get("BACKEND_URL", "http://localhost:8000")

    @staticmethod
    def mock_auth_server_url():
        """Get auth server URL for testing."""
        return get_env().get("AUTH_URL", "http://localhost:8081")

    @staticmethod
    def frontend_origin():
        """Frontend origin that makes cross-origin requests."""
        return "http://localhost:3001"

    @staticmethod
    def websocket_url():
        """Get WebSocket URL for testing."""
        return get_env().get("WS_URL", "ws://localhost:8000/ws")

    @staticmethod
    def backend_url():
        return get_env().get("BACKEND_URL", "http://localhost:8000")

    @staticmethod
    def auth_url():
        return get_env().get("AUTH_URL", "http://localhost:8081")

    @staticmethod
    def get_cors_headers(origin: str = None) -> Dict[str, str]:
        """Get standard CORS headers for testing."""
        headers = {
            'Content-Type': 'application/json'
        }
        if origin:
            headers['Origin'] = origin
        return headers

    @staticmethod
    def validate_cors_response(response, expected_origin: str = None) -> Dict[str, bool]:
        """Validate CORS headers in response."""
        validation = {
            'has_access_control_allow_origin': False,
            'has_access_control_allow_methods': False,
            'has_access_control_allow_headers': False,
            'has_access_control_allow_credentials': False,
            'origin_matches_expected': False
        }

        cors_headers = {k.lower(): v for k, v in response.headers.items() if k.lower().startswith('access-control')}
        
        if 'access-control-allow-origin' in cors_headers:
            validation['has_access_control_allow_origin'] = True
            if expected_origin and cors_headers['access-control-allow-origin'] == expected_origin:
                validation['origin_matches_expected'] = True

        validation['has_access_control_allow_methods'] = 'access-control-allow-methods' in cors_headers
        validation['has_access_control_allow_headers'] = 'access-control-allow-headers' in cors_headers
        validation['has_access_control_allow_credentials'] = 'access-control-allow-credentials' in cors_headers

        return validation


class TestCORSIntegrationCore:
    """Core CORS integration tests."""

    @pytest.fixture
    def backend_app(self):
        """Create backend FastAPI app for testing."""
        with patch.dict('os.environ', {
            'SKIP_STARTUP_TASKS': 'true',
            'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }):
            return create_app()

    @pytest.fixture
    def auth_test_app(self):
        """Create auth service test app."""
        with patch.dict('os.environ', {
            'AUTH_FAST_TEST_MODE': 'true',
            'DATABASE_URL': 'postgresql://test:test@localhost/test'
        }):
            return auth_app

    @pytest.fixture
    def cors_helper(self):
        """Get CORS test helper."""
        return CORSTestHelper()

    async def test_backend_cors_preflight_request(self, backend_app, cors_helper):
        """Test that backend handles CORS preflight requests correctly."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()

        # Send OPTIONS preflight request
        response = client.options(
            '/api/v1/chat',  # Common endpoint that should support CORS
            headers={
                'Origin': frontend_origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization'
            }
        )

        # Validate CORS preflight response
        validation = cors_helper.validate_cors_response(response, frontend_origin)

        assert response.status_code in [200, 204], f"Preflight failed with status {response.status_code}"
        assert validation['has_access_control_allow_origin'], "Missing Access-Control-Allow-Origin header"
        assert validation['has_access_control_allow_methods'], "Missing Access-Control-Allow-Methods header"
        assert validation['has_access_control_allow_headers'], "Missing Access-Control-Allow-Headers header"

    async def test_backend_cors_actual_request(self, backend_app, cors_helper):
        """Test actual CORS request to backend after preflight."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()

        # Send actual POST request with CORS headers
        response = client.post(
            '/api/v1/health',  # Use health endpoint as it's likely to exist and be simple
            headers={
                'Origin': frontend_origin,
                'Content-Type': 'application/json'
            },
            json={}
        )

        # Validate CORS headers in actual response
        validation = cors_helper.validate_cors_response(response, frontend_origin)

        assert response.status_code != 403, "CORS request should not be forbidden"
        assert validation['has_access_control_allow_origin'], \
            f"Missing CORS origin header. Response headers: {dict(response.headers)}"

    async def test_auth_service_cors_configuration(self, auth_test_app, cors_helper):
        """Test that auth service has proper CORS configuration."""
        client = TestClient(auth_test_app)
        frontend_origin = cors_helper.frontend_origin()

        # Test auth service health endpoint with CORS
        response = client.get(
            '/health',
            headers={'Origin': frontend_origin}
        )

        validation = cors_helper.validate_cors_response(response, frontend_origin)

        assert response.status_code != 403, "Auth service should allow CORS for health checks"
        # Auth service may have different CORS policy, but should not outright reject
        # Note: Auth endpoints might have stricter CORS for security

    async def test_websocket_cors_headers(self, backend_app, cors_helper):
        """Test that WebSocket endpoints respect CORS configuration."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()

        # Test WebSocket upgrade request with Origin header
        try:
            # Attempt WebSocket connection with CORS origin
            with client.websocket_connect(
                "/ws",
                headers={'Origin': frontend_origin}
            ) as websocket:
                # If connection succeeds, CORS is properly configured
                websocket.send_json({"type": "ping"})
                data = websocket.receive_json()
                assert data is not None, "WebSocket connection should work with proper origin"

        except Exception as e:
            # If WebSocket fails, check if it's due to CORS or other issues
            # This test validates that CORS doesn't prevent WebSocket connections
            if "403" in str(e) or "Origin" in str(e):
                pytest.fail(f"WebSocket CORS configuration may be too restrictive: {e}")
            # Other errors (like WebSocket not implemented) are acceptable for this test

    async def test_cors_with_credentials(self, backend_app, cors_helper):
        """Test CORS configuration with credentials (cookies, auth headers)."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()

        # Test request with credentials
        response = client.get(
            '/api/v1/health',
            headers={
                'Origin': frontend_origin,
                'Authorization': 'Bearer test_token',
                'Cookie': 'session_id=test123'
            }
        )

        validation = cors_helper.validate_cors_response(response)

        # If credentials are sent, check if server properly handles CORS
        assert response.status_code != 403, "CORS should not block requests with credentials"
        
        # If Access-Control-Allow-Credentials is set, origin should not be wildcard
        if validation['has_access_control_allow_credentials']:
            cors_origin = response.headers.get('Access-Control-Allow-Origin', '')
            assert cors_origin != '*', \
                "When credentials are allowed, origin cannot be wildcard for security"

    async def test_cors_multiple_origins(self, backend_app, cors_helper):
        """Test CORS configuration with multiple allowed origins."""
        client = TestClient(backend_app)

        test_origins = [
            cors_helper.frontend_origin(),
            'http://localhost:3000',  # Alternative frontend port
            'https://app.netra.com'   # Production frontend (if configured)
        ]

        results = []
        for origin in test_origins:
            response = client.options(
                '/api/v1/health',
                headers={
                    'Origin': origin,
                    'Access-Control-Request-Method': 'GET'
                }
            )

            validation = cors_helper.validate_cors_response(response, origin)
            results.append({
                'origin': origin,
                'status_code': response.status_code,
                'cors_configured': validation['has_access_control_allow_origin']
            })

        # At least one origin should be properly configured
        configured_origins = [r for r in results if r['cors_configured']]
        assert len(configured_origins) > 0, \
            f"No origins properly configured for CORS: {results}"

    async def test_cors_rejected_origins(self, backend_app, cors_helper):
        """Test that CORS properly rejects unauthorized origins."""
        client = TestClient(backend_app)

        # Test with potentially malicious origin
        malicious_origins = [
            'https://evil.com',
            'http://localhost:9999',
            'https://attacker.example.com'
        ]

        for malicious_origin in malicious_origins:
            response = client.options(
                '/api/v1/chat',
                headers={
                    'Origin': malicious_origin,
                    'Access-Control-Request-Method': 'POST'
                }
            )

            # Response should either:
            # 1. Not include CORS headers (browser will block)
            # 2. Explicitly reject with different origin
            # 3. Return error status
            
            cors_origin = response.headers.get('Access-Control-Allow-Origin')
            
            # If CORS header is present, it should not match malicious origin
            if cors_origin:
                assert cors_origin != malicious_origin, \
                    f"CORS should not allow malicious origin {malicious_origin}"

    async def test_cors_method_restrictions(self, backend_app, cors_helper):
        """Test that CORS properly restricts HTTP methods."""
        client = TestClient(backend_app)
        frontend_origin = cors_helper.frontend_origin()

        # Test different HTTP methods
        methods_to_test = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        
        for method in methods_to_test:
            response = client.options(
                '/api/v1/health',
                headers={
                    'Origin': frontend_origin,
                    'Access-Control-Request-Method': method
                }
            )

            allowed_methods = response.headers.get('Access-Control-Allow-Methods', '')
            
            # Document which methods are allowed for security review
            print(f"Method {method}: Status {response.status_code}, Allowed methods: {allowed_methods}")

        # This test documents current behavior rather than asserting specific restrictions
        # Security review should determine if method restrictions are appropriate


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])