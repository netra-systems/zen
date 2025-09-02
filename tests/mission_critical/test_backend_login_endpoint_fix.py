from shared.isolated_environment import get_env
"""
Mission critical test for backend login endpoint 500 error fix.
Validates the comprehensive error handling and recovery system for auth service communication.
"""

import pytest
import httpx
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from netra_backend.app.main import app
from netra_backend.app.routes.auth_routes.debug_helpers import (
    AuthServiceDebugger,
    enhanced_auth_service_call,
    create_enhanced_auth_error_response
)


class TestBackendLoginEndpointFix:
    """Test suite for backend login endpoint 500 error fixes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture  
    def mock_auth_client(self):
        """Mock auth client for testing."""
        with patch("netra_backend.app.routes.auth_proxy.auth_client") as mock:
            yield mock

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables for testing."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "SERVICE_ID": "netra-backend",
            "SERVICE_SECRET": "test-service-secret",
            "AUTH_SERVICE_ENABLED": "true"
        }
        
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = MagicMock()
            mock_get_env.return_value.get = lambda key, default=None: env_vars.get(key, default)
            yield mock_get_env

    def test_auth_service_debugger_initialization(self, mock_environment):
        """Test AuthServiceDebugger initialization and configuration detection."""
        debugger = AuthServiceDebugger()
        
        # Test URL detection
        auth_url = debugger.get_auth_service_url()
        assert auth_url == "https://auth.staging.netrasystems.ai"
        
        # Test credential detection
        service_id, service_secret = debugger.get_service_credentials()
        assert service_id == "netra-backend"
        assert service_secret == "test-service-secret"

    def test_auth_service_debugger_fallback_url(self):
        """Test AuthServiceDebugger URL fallback logic."""
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = MagicMock()
            mock_get_env.return_value.get = lambda key, default=None: {
                "ENVIRONMENT": "staging"
            }.get(key, default)
            
            debugger = AuthServiceDebugger()
            auth_url = debugger.get_auth_service_url()
            assert auth_url == "https://auth.staging.netrasystems.ai"

    def test_log_environment_debug_info(self, mock_environment):
        """Test comprehensive environment debug logging."""
        debugger = AuthServiceDebugger()
        debug_info = debugger.log_environment_debug_info()
        
        expected_keys = [
            "environment", "auth_service_url", "service_id_configured",
            "service_id_value", "service_secret_configured", "auth_service_enabled",
            "testing_flag", "netra_env"
        ]
        
        for key in expected_keys:
            assert key in debug_info
        
        assert debug_info["environment"] == "staging"
        assert debug_info["auth_service_url"] == "https://auth.staging.netrasystems.ai"
        assert debug_info["service_id_configured"] is True
        assert debug_info["service_secret_configured"] is True

    @pytest.mark.asyncio
    async def test_auth_service_connectivity_success(self, mock_environment):
        """Test successful auth service connectivity test."""
        debugger = AuthServiceDebugger()
        
        # Mock successful HTTP response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await debugger.test_auth_service_connectivity()
            
            assert result["connectivity_test"] == "success"
            assert result["status_code"] == 200
            assert result["response_time_ms"] is not None
            assert result["service_auth_supported"] is True

    @pytest.mark.asyncio
    async def test_auth_service_connectivity_failure(self, mock_environment):
        """Test auth service connectivity failure handling."""
        debugger = AuthServiceDebugger()
        
        # Mock connection error
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await debugger.test_auth_service_connectivity()
            
            assert result["connectivity_test"] == "failed"
            assert result["error"] is not None
            assert "Connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_login_endpoint_auth_service_unavailable(self, client, mock_environment, mock_auth_client):
        """Test login endpoint behavior when auth service is unavailable."""
        # Mock auth client to return None (service unavailable)
        mock_auth_client.login.return_value = None
        
        # Mock connectivity test to fail
        with patch("netra_backend.app.routes.auth_routes.debug_helpers.AuthServiceDebugger.test_auth_service_connectivity") as mock_connectivity:
            mock_connectivity.return_value = {
                "connectivity_test": "failed",
                "auth_service_url": "https://auth.staging.netrasystems.ai",
                "error": "Connection refused"
            }
            
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "testpass"}
            )
            
            # Should return 503 Service Unavailable with specific error message
            assert response.status_code == 503
            assert "Auth service unreachable" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_endpoint_auth_client_failure(self, client, mock_environment, mock_auth_client):
        """Test login endpoint behavior when auth client returns None but service is reachable."""
        # Mock auth client to return None (login failed)
        mock_auth_client.login.return_value = None
        
        # Mock connectivity test to succeed
        with patch("netra_backend.app.routes.auth_routes.debug_helpers.AuthServiceDebugger.test_auth_service_connectivity") as mock_connectivity:
            mock_connectivity.return_value = {
                "connectivity_test": "success",
                "status_code": 200,
                "service_auth_supported": True
            }
            
            with patch("netra_backend.app.routes.auth_routes.debug_helpers.AuthServiceDebugger.debug_login_attempt") as mock_debug:
                mock_debug.return_value = {
                    "recommended_actions": ["Check credentials", "Verify user exists"]
                }
                
                response = client.post(
                    "/api/v1/auth/login",
                    json={"email": "test@example.com", "password": "wrongpass"}
                )
                
                # Should return 401 Unauthorized with helpful message
                assert response.status_code == 401
                assert "Login failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_endpoint_successful_login(self, client, mock_environment, mock_auth_client):
        """Test successful login through the endpoint."""
        # Mock successful auth client response
        mock_auth_client.login.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "Bearer",
            "expires_in": 900,
            "user_id": "user-123"
        }
        
        # Mock connectivity test to succeed
        with patch("netra_backend.app.routes.auth_routes.debug_helpers.AuthServiceDebugger.test_auth_service_connectivity") as mock_connectivity:
            mock_connectivity.return_value = {
                "connectivity_test": "success",
                "status_code": 200,
                "service_auth_supported": True
            }
            
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "testpass"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test-access-token"
            assert data["token_type"] == "Bearer"
            assert data["user"]["email"] == "test@example.com"

    def test_create_enhanced_auth_error_response_staging(self, mock_environment):
        """Test enhanced error response creation in staging environment."""
        original_error = Exception("Test error")
        debug_info = {"connectivity": "failed", "error": "Connection refused"}
        
        error_response = create_enhanced_auth_error_response(original_error, debug_info)
        
        assert error_response.status_code == 500
        detail = error_response.detail
        assert detail["error"] == "Authentication service communication failed"
        assert detail["original_error"] == "Test error"
        assert detail["debug_info"] == debug_info
        assert "suggestions" in detail

    def test_create_enhanced_auth_error_response_production(self):
        """Test enhanced error response creation in production environment."""
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = MagicMock()
            mock_get_env.return_value.get = lambda key, default=None: {
                "ENVIRONMENT": "production"
            }.get(key, default)
            
            original_error = Exception("Test error")
            error_response = create_enhanced_auth_error_response(original_error)
            
            assert error_response.status_code == 500
            # In production, should return generic error
            assert error_response.detail == "Authentication service temporarily unavailable"

    @pytest.mark.asyncio
    async def test_enhanced_auth_service_call_success(self):
        """Test enhanced auth service call wrapper with successful operation."""
        async def mock_operation():
            return {"result": "success"}
        
        result = await enhanced_auth_service_call(
            mock_operation,
            operation_name="test_operation"
        )
        
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_enhanced_auth_service_call_failure(self):
        """Test enhanced auth service call wrapper with operation failure."""
        async def mock_operation():
            raise Exception("Operation failed")
        
        with patch("netra_backend.app.routes.auth_routes.debug_helpers.AuthServiceDebugger.test_auth_service_connectivity") as mock_connectivity:
            mock_connectivity.return_value = {
                "connectivity_test": "failed",
                "error": "Connection refused"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await enhanced_auth_service_call(
                    mock_operation,
                    operation_name="test_operation"
                )
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_http_proxy_with_service_credentials(self, mock_environment):
        """Test HTTP proxy adds service credentials when available."""
        from netra_backend.app.routes.auth_proxy import _http_proxy_to_auth_service
        
        with patch("httpx.AsyncClient") as mock_client:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await _http_proxy_to_auth_service(
                "/test", "POST", {"test": "data"}
            )
            
            # Verify service credentials were added to headers
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            headers = call_args[1]["headers"]
            assert "X-Service-ID" in headers
            assert "X-Service-Secret" in headers
            assert headers["X-Service-ID"] == "netra-backend"
            assert headers["X-Service-Secret"] == "test-service-secret"

    @pytest.mark.asyncio
    async def test_http_proxy_timeout_handling(self, mock_environment):
        """Test HTTP proxy timeout error handling."""
        from netra_backend.app.routes.auth_proxy import _http_proxy_to_auth_service
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectTimeout("Timeout")
            
            with pytest.raises(HTTPException) as exc_info:
                await _http_proxy_to_auth_service("/test", "POST", {"test": "data"})
            
            assert exc_info.value.status_code == 503
            assert "connection timeout" in exc_info.value.detail.lower()

    def test_debug_login_attempt_missing_credentials(self, mock_environment):
        """Test debug login attempt with missing service credentials."""
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = MagicMock()
            mock_get_env.return_value.get = lambda key, default=None: {
                "ENVIRONMENT": "staging",
                "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai"
                # Missing SERVICE_ID and SERVICE_SECRET
            }.get(key, default)
            
            debugger = AuthServiceDebugger()
            debug_info = debugger.log_environment_debug_info()
            
            assert debug_info["service_id_configured"] is False
            assert debug_info["service_secret_configured"] is False

    @pytest.mark.asyncio
    async def test_registration_endpoint_with_enhanced_error_handling(self, client, mock_environment):
        """Test registration endpoint uses enhanced error handling."""
        with patch("netra_backend.app.routes.auth_proxy._http_proxy_to_auth_service") as mock_proxy:
            mock_proxy.side_effect = httpx.ConnectError("Connection failed")
            
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": "testpass"}
            )
            
            # Should return 503 with specific error message
            assert response.status_code == 503
            assert "connection" in response.json()["detail"].lower()

    def test_environment_variable_trimming(self):
        """Test that service secrets are properly trimmed of whitespace."""
        with patch("shared.isolated_environment.get_env") as mock_get_env:
            mock_get_env.return_value = MagicMock()
            mock_get_env.return_value.get = lambda key, default=None: {
                "SERVICE_ID": "  netra-backend  ",
                "SERVICE_SECRET": "  test-secret  "
            }.get(key, default)
            
            debugger = AuthServiceDebugger()
            service_id, service_secret = debugger.get_service_credentials()
            
            assert service_id == "netra-backend"  # Trimmed
            assert service_secret == "test-secret"  # Trimmed


@pytest.mark.integration
class TestBackendLoginEndpointIntegration:
    """Integration tests for backend login endpoint with real service dependencies."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_login_endpoint_real_environment(self, client):
        """Test login endpoint with real environment configuration."""
        # This test will use actual environment variables and should be run in staging
        # Skip if not in appropriate test environment
        import os
        if get_env().get("ENVIRONMENT") not in ["staging", "testing"]:
            pytest.skip("Integration test requires staging/testing environment")
        
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"}
        )
        
        # Should not return 500 - should be 401 or 503 with proper error handling
        assert response.status_code in [401, 503]
        
        # Should have meaningful error message, not generic 500 error
        error_detail = response.json()["detail"]
        assert error_detail != "Internal Server Error"
        assert len(error_detail) > 10  # Should have meaningful message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
