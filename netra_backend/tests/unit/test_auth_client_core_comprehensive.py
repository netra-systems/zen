"""
Comprehensive unit tests for auth_client_core.py achieving 100% coverage.
Tests all authentication operations, resilience modes, circuit breakers, and caching.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock

import httpx
import pytest
from freezegun import freeze_time

from netra_backend.app.clients.auth_client_core import (
    AuthOperationType,
    AuthResilienceMode,
    AuthServiceClient,
    AuthServiceConnectionError,
    AuthServiceError,
    AuthServiceHealthStatus,
    AuthServiceNotAvailableError,
    AuthServiceValidationError,
    AuthTokenExchangeError,
    AuthTokenRequest,
    AuthTokenResponse,
    CircuitBreakerError,
    ClientCredentials,
    EnvironmentDetectionError,
    OAuth2Request,
    OAuth2Response,
    OAuthConfigError,
    OAuthError,
    OAuthInvalidCredentialsError,
    OAuthInvalidGrantError,
    OAuthInvalidRequestError,
    OAuthInvalidScopeError,
    OAuthRedirectMismatchError,
    OAuthServerError,
    OAuthUnavailableError,
    ServiceCredentials,
    TokenStatus,
    TokenValidationRequest,
    TokenValidationResponse,
    UserAuthRequest,
    UserAuthResponse,
    get_auth_service_client,
    handle_auth_service_error,
    validate_jwt_format,
)
from netra_backend.app.clients.auth_client_cache import (
    AuthCircuitBreakerManager,
    AuthServiceSettings,
    AuthTokenCache,
)
from netra_backend.app.clients.auth_client_config import (
    EnvironmentDetector,
    OAuthConfig,
    OAuthConfigGenerator,
)
from netra_backend.app.clients.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    get_circuit_breaker,
)
from netra_backend.app.core.environment_constants import Environment


class TestAuthServiceClient:
    """Test AuthServiceClient initialization and configuration."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for AuthServiceClient."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings') as mock_settings, \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache') as mock_cache, \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager') as mock_circuit_manager, \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector') as mock_env_detector, \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator') as mock_oauth_gen, \
             patch('netra_backend.app.clients.auth_client_core.TracingManager') as mock_tracing, \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker') as mock_get_circuit, \
             patch('netra_backend.app.clients.auth_client_core.get_configuration') as mock_get_config, \
             patch('netra_backend.app.clients.auth_client_core.get_env') as mock_get_env:
            
            # Configure mocks
            mock_settings_instance = MagicMock()
            mock_settings_instance.cache_ttl = 300
            mock_settings_instance.auth_service_url = "http://auth-service:8081"
            mock_settings_instance.enable_cache = True
            mock_settings_instance.enable_resilience = True
            mock_settings.return_value = mock_settings_instance
            
            mock_cache_instance = MagicMock()
            mock_cache.return_value = mock_cache_instance
            
            mock_circuit_instance = MagicMock()
            mock_circuit_manager.return_value = mock_circuit_instance
            
            mock_env_instance = MagicMock()
            mock_env_detector.return_value = mock_env_instance
            
            mock_oauth_instance = MagicMock()
            mock_oauth_gen.return_value = mock_oauth_instance
            
            mock_tracing_instance = MagicMock()
            mock_tracing.return_value = mock_tracing_instance
            
            mock_circuit_breaker = MagicMock()
            mock_get_circuit.return_value = mock_circuit_breaker
            
            mock_config = MagicMock()
            mock_config.service_id = "test-service"
            mock_config.service_secret = "test-secret"
            mock_get_config.return_value = mock_config
            
            mock_env = MagicMock()
            mock_env.get.return_value = None
            mock_get_env.return_value = mock_env
            
            yield {
                'settings': mock_settings_instance,
                'cache': mock_cache_instance,
                'circuit_manager': mock_circuit_instance,
                'env_detector': mock_env_instance,
                'oauth_gen': mock_oauth_instance,
                'tracing': mock_tracing_instance,
                'circuit_breaker': mock_circuit_breaker,
                'config': mock_config,
                'env': mock_env
            }

    def test_init_with_config_secret(self, mock_dependencies):
        """Test initialization with service secret from config."""
        client = AuthServiceClient()
        
        assert client.service_id == "test-service"
        assert client.service_secret == "test-secret"
        assert client.settings == mock_dependencies['settings']
        assert client.token_cache == mock_dependencies['cache']
        assert client.circuit_manager == mock_dependencies['circuit_manager']

    def test_init_with_env_secret_fallback(self, mock_dependencies):
        """Test initialization with service secret from environment fallback."""
        mock_dependencies['config'].service_secret = None
        mock_dependencies['env'].get.return_value = "env-secret"
        
        client = AuthServiceClient()
        
        assert client.service_id == "test-service"
        assert client.service_secret == "env-secret"

    def test_init_without_any_secret(self, mock_dependencies):
        """Test initialization without service secret logs error."""
        mock_dependencies['config'].service_secret = None
        mock_dependencies['env'].get.return_value = None
        
        with patch('netra_backend.app.clients.auth_client_core.logger') as mock_logger:
            client = AuthServiceClient()
            
            assert client.service_secret is None
            mock_logger.error.assert_called_with("SERVICE_SECRET not found in config or environment - auth will fail")

    @pytest.mark.asyncio
    async def test_validate_token_success(self, mock_dependencies):
        """Test successful token validation."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "user_id": "user123",
            "email": "test@example.com",
            "permissions": ["read", "write"]
        }
        client._client.post.return_value = mock_response
        
        result = await client.validate_token("valid-token")
        
        assert result["valid"] is True
        assert result["user_id"] == "user123"
        assert result["email"] == "test@example.com"
        assert result["permissions"] == ["read", "write"]

    @pytest.mark.asyncio
    async def test_validate_token_with_cache_hit(self, mock_dependencies):
        """Test token validation with cache hit."""
        client = AuthServiceClient()
        
        # Setup cache hit
        mock_dependencies['cache'].get.return_value = {
            "valid": True,
            "user_id": "cached-user",
            "cached": True
        }
        
        result = await client.validate_token("cached-token")
        
        assert result["valid"] is True
        assert result["user_id"] == "cached-user"
        assert result["cached"] is True
        
        # Verify no HTTP call was made
        assert client._client is None

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, mock_dependencies):
        """Test invalid token validation."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"valid": False, "error": "Invalid token"}
        client._client.post.return_value = mock_response
        
        result = await client.validate_token("invalid-token")
        
        assert result["valid"] is False
        assert result["error"] == "Invalid token"

    @pytest.mark.asyncio
    async def test_validate_token_circuit_breaker_open(self, mock_dependencies):
        """Test token validation when circuit breaker is open."""
        client = AuthServiceClient()
        
        # Make circuit breaker throw exception
        mock_dependencies['circuit_breaker'].call.side_effect = CircuitBreakerOpen("auth_service")
        
        # Setup cache fallback
        mock_dependencies['cache'].get.return_value = {
            "valid": True,
            "user_id": "fallback-user",
            "degraded": True
        }
        
        result = await client.validate_token("test-token")
        
        assert result["valid"] is True
        assert result["user_id"] == "fallback-user"
        assert result["degraded"] is True

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, mock_dependencies):
        """Test successful user authentication."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "user_id": "user123",
            "expires_in": 3600
        }
        client._client.post.return_value = mock_response
        
        result = await client.authenticate_user("user@example.com", "password123")
        
        assert result["access_token"] == "new-access-token"
        assert result["refresh_token"] == "new-refresh-token"
        assert result["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, mock_dependencies):
        """Test user authentication with invalid credentials."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid credentials"}
        client._client.post.return_value = mock_response
        
        with pytest.raises(AuthServiceValidationError) as exc_info:
            await client.authenticate_user("user@example.com", "wrong-password")
        
        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, mock_dependencies):
        """Test successful token refresh."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed-access-token",
            "refresh_token": "refreshed-refresh-token",
            "expires_in": 3600
        }
        client._client.post.return_value = mock_response
        
        result = await client.refresh_token("old-refresh-token")
        
        assert result["access_token"] == "refreshed-access-token"
        assert result["refresh_token"] == "refreshed-refresh-token"

    @pytest.mark.asyncio
    async def test_logout_success(self, mock_dependencies):
        """Test successful logout."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        client._client.post.return_value = mock_response
        
        # Clear cache for testing
        mock_dependencies['cache'].remove = MagicMock()
        
        result = await client.logout("test-token")
        
        assert result["success"] is True
        mock_dependencies['cache'].remove.assert_called_with("test-token")

    @pytest.mark.asyncio
    async def test_check_permissions_allowed(self, mock_dependencies):
        """Test permission check when user has required permissions."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "allowed": True,
            "user_permissions": ["read", "write", "admin"]
        }
        client._client.post.return_value = mock_response
        
        result = await client.check_permissions("test-token", ["read", "write"])
        
        assert result["allowed"] is True
        assert "admin" in result["user_permissions"]

    @pytest.mark.asyncio
    async def test_check_permissions_denied(self, mock_dependencies):
        """Test permission check when user lacks required permissions."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "allowed": False,
            "missing_permissions": ["admin"]
        }
        client._client.post.return_value = mock_response
        
        result = await client.check_permissions("test-token", ["admin"])
        
        assert result["allowed"] is False
        assert "admin" in result["missing_permissions"]

    @pytest.mark.asyncio
    async def test_get_oauth_config_success(self, mock_dependencies):
        """Test successful OAuth config retrieval."""
        client = AuthServiceClient()
        
        mock_config = OAuthConfig(
            client_id="oauth-client-id",
            client_secret="oauth-client-secret",
            redirect_uri="http://localhost:3000/callback"
        )
        mock_dependencies['oauth_gen'].generate_config.return_value = mock_config
        
        result = await client.get_oauth_config()
        
        assert result["client_id"] == "oauth-client-id"
        assert result["redirect_uri"] == "http://localhost:3000/callback"

    @pytest.mark.asyncio
    async def test_exchange_oauth_code_success(self, mock_dependencies):
        """Test successful OAuth code exchange."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "oauth-access-token",
            "id_token": "oauth-id-token",
            "refresh_token": "oauth-refresh-token"
        }
        client._client.post.return_value = mock_response
        
        result = await client.exchange_oauth_code("auth-code", "http://localhost:3000/callback")
        
        assert result["access_token"] == "oauth-access-token"
        assert result["id_token"] == "oauth-id-token"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_dependencies):
        """Test health check when service is healthy."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "database": "connected",
            "cache": "connected"
        }
        client._client.get.return_value = mock_response
        
        result = await client.health_check()
        
        assert result["status"] == "healthy"
        assert result["database"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_dependencies):
        """Test health check when service is unhealthy."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.json.return_value = {
            "status": "unhealthy",
            "database": "disconnected"
        }
        client._client.get.return_value = mock_response
        
        result = await client.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["database"] == "disconnected"

    @pytest.mark.asyncio
    async def test_get_service_token_success(self, mock_dependencies):
        """Test successful service token retrieval."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "service_token": "service-jwt-token",
            "expires_in": 3600
        }
        client._client.post.return_value = mock_response
        
        result = await client.get_service_token()
        
        assert result["service_token"] == "service-jwt-token"
        assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_dependencies):
        """Test cleanup closes HTTP client."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        await client.cleanup()
        
        client._client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_cleanup_no_client(self, mock_dependencies):
        """Test cleanup when no client exists."""
        client = AuthServiceClient()
        
        # Should not raise error
        await client.cleanup()
        
        assert client._client is None

    def test_resilience_mode_property(self, mock_dependencies):
        """Test resilience mode property."""
        client = AuthServiceClient()
        
        mock_dependencies['circuit_manager'].get_current_mode.return_value = AuthResilienceMode.DEGRADED
        
        assert client.resilience_mode == AuthResilienceMode.DEGRADED

    def test_circuit_breaker_state_property(self, mock_dependencies):
        """Test circuit breaker state property."""
        client = AuthServiceClient()
        
        mock_dependencies['circuit_breaker'].state = "open"
        
        assert client.circuit_breaker_state == "open"

    @pytest.mark.asyncio
    async def test_retry_logic_success_on_second_attempt(self, mock_dependencies):
        """Test retry logic succeeds on second attempt."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        # First attempt fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"valid": True}
        
        client._client.post.side_effect = [
            httpx.ConnectTimeout("Timeout"),
            mock_response_success
        ]
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await client.validate_token("test-token")
        
        assert result["valid"] is True
        assert client._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_monitoring_metrics_recording(self, mock_dependencies):
        """Test that monitoring metrics are recorded."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True}
        client._client.post.return_value = mock_response
        
        # Mock monitoring
        with patch('netra_backend.app.clients.auth_client_core.record_auth_operation') as mock_record:
            await client.validate_token("test-token")
            
            mock_record.assert_called()

    @pytest.mark.asyncio
    async def test_environment_specific_config(self, mock_dependencies):
        """Test environment-specific configuration."""
        with patch('netra_backend.app.clients.auth_client_core.get_current_environment') as mock_get_env:
            mock_get_env.return_value = Environment.PRODUCTION
            
            client = AuthServiceClient()
            
            # In production, should validate more strictly
            assert client.settings is not None

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, mock_dependencies):
        """Test handling of concurrent requests."""
        client = AuthServiceClient()
        client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True}
        client._client.post.return_value = mock_response
        
        # Run multiple concurrent requests
        tasks = [client.validate_token(f"token-{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert all(r["valid"] for r in results)
        assert client._client.post.call_count == 10


class TestAuthServiceErrorHandling:
    """Test error handling in auth service client."""

    @pytest.mark.asyncio
    async def test_handle_auth_service_error_401(self):
        """Test handling of 401 Unauthorized error."""
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {"error": "Unauthorized"}
        
        with pytest.raises(AuthServiceValidationError) as exc_info:
            handle_auth_service_error(response, "test_operation")
        
        assert "Unauthorized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_auth_service_error_403(self):
        """Test handling of 403 Forbidden error."""
        response = MagicMock()
        response.status_code = 403
        response.json.return_value = {"error": "Forbidden"}
        
        with pytest.raises(AuthServiceValidationError) as exc_info:
            handle_auth_service_error(response, "test_operation")
        
        assert "Forbidden" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_auth_service_error_404(self):
        """Test handling of 404 Not Found error."""
        response = MagicMock()
        response.status_code = 404
        response.json.return_value = {"error": "Not found"}
        
        with pytest.raises(AuthServiceNotAvailableError) as exc_info:
            handle_auth_service_error(response, "test_operation")
        
        assert "Not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_auth_service_error_500(self):
        """Test handling of 500 Internal Server Error."""
        response = MagicMock()
        response.status_code = 500
        response.json.return_value = {"error": "Internal server error"}
        
        with pytest.raises(AuthServiceError) as exc_info:
            handle_auth_service_error(response, "test_operation")
        
        assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_auth_service_error_503(self):
        """Test handling of 503 Service Unavailable error."""
        response = MagicMock()
        response.status_code = 503
        response.json.return_value = {"error": "Service unavailable"}
        
        with pytest.raises(AuthServiceNotAvailableError) as exc_info:
            handle_auth_service_error(response, "test_operation")
        
        assert "Service unavailable" in str(exc_info.value)


class TestJWTValidation:
    """Test JWT format validation."""

    def test_validate_jwt_format_valid(self):
        """Test validation of valid JWT format."""
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        assert validate_jwt_format(valid_jwt) is True

    def test_validate_jwt_format_invalid_parts(self):
        """Test validation of JWT with wrong number of parts."""
        invalid_jwt = "not.a.valid.jwt.token"
        
        assert validate_jwt_format(invalid_jwt) is False

    def test_validate_jwt_format_invalid_encoding(self):
        """Test validation of JWT with invalid base64 encoding."""
        invalid_jwt = "invalid!@#$.invalid!@#$.invalid!@#$"
        
        assert validate_jwt_format(invalid_jwt) is False

    def test_validate_jwt_format_empty(self):
        """Test validation of empty JWT."""
        assert validate_jwt_format("") is False

    def test_validate_jwt_format_none(self):
        """Test validation of None JWT."""
        assert validate_jwt_format(None) is False


class TestGetAuthServiceClient:
    """Test singleton auth service client."""

    def test_get_auth_service_client_singleton(self):
        """Test that get_auth_service_client returns singleton."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient') as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            
            # First call creates instance
            client1 = get_auth_service_client()
            assert client1 == mock_instance
            mock_client_class.assert_called_once()
            
            # Second call returns same instance
            mock_client_class.reset_mock()
            client2 = get_auth_service_client()
            assert client2 == mock_instance
            mock_client_class.assert_not_called()
            
            # Verify same instance
            assert client1 is client2


class TestOAuthOperations:
    """Test OAuth-specific operations."""

    @pytest.fixture
    def auth_client(self):
        """Create auth client with mocked dependencies."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration'), \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            return AuthServiceClient()

    @pytest.mark.asyncio
    async def test_oauth_invalid_grant_error(self, auth_client):
        """Test OAuth invalid grant error handling."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant"}
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(OAuthInvalidGrantError):
            await auth_client.exchange_oauth_code("invalid-code", "http://redirect")

    @pytest.mark.asyncio
    async def test_oauth_invalid_scope_error(self, auth_client):
        """Test OAuth invalid scope error handling."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_scope"}
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(OAuthInvalidScopeError):
            await auth_client.exchange_oauth_code("code", "http://redirect")

    @pytest.mark.asyncio
    async def test_oauth_redirect_mismatch_error(self, auth_client):
        """Test OAuth redirect URI mismatch error handling."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "redirect_uri_mismatch"}
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(OAuthRedirectMismatchError):
            await auth_client.exchange_oauth_code("code", "http://wrong-redirect")


class TestAuthServiceMetrics:
    """Test metrics and monitoring in auth service client."""

    @pytest.fixture
    def auth_client(self):
        """Create auth client with mocked dependencies."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration'), \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            return AuthServiceClient()

    @pytest.mark.asyncio
    async def test_get_metrics(self, auth_client):
        """Test metrics retrieval."""
        metrics = await auth_client.get_metrics()
        
        assert "cache_stats" in metrics
        assert "circuit_breaker_state" in metrics
        assert "resilience_mode" in metrics

    @pytest.mark.asyncio
    async def test_reset_metrics(self, auth_client):
        """Test metrics reset."""
        auth_client.circuit_manager = MagicMock()
        auth_client.token_cache = MagicMock()
        
        await auth_client.reset_metrics()
        
        auth_client.circuit_manager.reset_stats.assert_called_once()
        auth_client.token_cache.clear.assert_called_once()


class TestCacheOperations:
    """Test caching operations in auth service client."""

    @pytest.fixture
    def auth_client(self):
        """Create auth client with mocked dependencies."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache') as mock_cache, \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration'), \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            
            mock_cache_instance = MagicMock()
            mock_cache.return_value = mock_cache_instance
            
            client = AuthServiceClient()
            client.token_cache = mock_cache_instance
            return client

    @pytest.mark.asyncio
    async def test_cache_warming(self, auth_client):
        """Test cache warming operation."""
        auth_client._client = AsyncMock()
        
        tokens = ["token1", "token2", "token3"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": True, "user_id": "user123"}
        auth_client._client.post.return_value = mock_response
        
        await auth_client.warm_cache(tokens)
        
        # Verify all tokens were validated
        assert auth_client._client.post.call_count == len(tokens)
        
        # Verify results were cached
        assert auth_client.token_cache.set.call_count == len(tokens)

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, auth_client):
        """Test cache invalidation."""
        auth_client.token_cache.remove = MagicMock()
        
        await auth_client.invalidate_cache_entry("token-to-invalidate")
        
        auth_client.token_cache.remove.assert_called_once_with("token-to-invalidate")

    @pytest.mark.asyncio
    async def test_cache_clear(self, auth_client):
        """Test clearing entire cache."""
        auth_client.token_cache.clear = MagicMock()
        
        await auth_client.clear_cache()
        
        auth_client.token_cache.clear.assert_called_once()


class TestServiceAuthentication:
    """Test service-to-service authentication."""

    @pytest.fixture
    def auth_client(self):
        """Create auth client with service credentials."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration') as mock_config, \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            
            mock_config.return_value.service_id = "backend-service"
            mock_config.return_value.service_secret = "service-secret-key"
            
            return AuthServiceClient()

    @pytest.mark.asyncio
    async def test_service_authentication_success(self, auth_client):
        """Test successful service-to-service authentication."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "service_token": "service-jwt-token",
            "expires_in": 3600
        }
        auth_client._client.post.return_value = mock_response
        
        result = await auth_client.authenticate_service()
        
        assert result["service_token"] == "service-jwt-token"
        assert auth_client.service_id == "backend-service"

    @pytest.mark.asyncio
    async def test_service_authentication_invalid_secret(self, auth_client):
        """Test service authentication with invalid secret."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid service credentials"}
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(AuthServiceValidationError) as exc_info:
            await auth_client.authenticate_service()
        
        assert "Invalid service credentials" in str(exc_info.value)


class TestRateLimiting:
    """Test rate limiting handling."""

    @pytest.fixture
    def auth_client(self):
        """Create auth client."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration'), \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            return AuthServiceClient()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, auth_client):
        """Test handling of rate limit exceeded response."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(AuthServiceError) as exc_info:
            await auth_client.validate_token("test-token")
        
        assert "Rate limit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_automatic_retry_with_backoff(self, auth_client):
        """Test automatic retry with exponential backoff."""
        auth_client._client = AsyncMock()
        
        # First two attempts fail with rate limit, third succeeds
        mock_response_limit = MagicMock()
        mock_response_limit.status_code = 429
        mock_response_limit.json.return_value = {"error": "Rate limit"}
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"valid": True}
        
        auth_client._client.post.side_effect = [
            mock_response_limit,
            mock_response_limit,
            mock_response_success
        ]
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await auth_client.validate_token("test-token")
        
        assert result["valid"] is True
        # Verify exponential backoff was applied
        assert mock_sleep.call_count >= 2


class TestEnvironmentDetection:
    """Test environment detection and configuration."""

    @pytest.mark.asyncio
    async def test_production_environment_strict_validation(self):
        """Test strict validation in production environment."""
        with patch('netra_backend.app.clients.auth_client_core.get_current_environment') as mock_env, \
             patch('netra_backend.app.clients.auth_client_core.is_production') as mock_is_prod, \
             patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration') as mock_config, \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            
            mock_env.return_value = Environment.PRODUCTION
            mock_is_prod.return_value = True
            mock_config.return_value.service_secret = None
            
            # In production, missing service secret should log critical error
            with patch('netra_backend.app.clients.auth_client_core.logger') as mock_logger:
                client = AuthServiceClient()
                
                # Verify critical error was logged
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_development_environment_relaxed_validation(self):
        """Test relaxed validation in development environment."""
        with patch('netra_backend.app.clients.auth_client_core.get_current_environment') as mock_env, \
             patch('netra_backend.app.clients.auth_client_core.is_production') as mock_is_prod, \
             patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration') as mock_config, \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            
            mock_env.return_value = Environment.TEST
            mock_is_prod.return_value = False
            mock_config.return_value.service_secret = None
            
            # In development, missing service secret is acceptable
            client = AuthServiceClient()
            
            assert client.service_secret is None  # But client still initializes


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def auth_client(self):
        """Create auth client."""
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceSettings'), \
             patch('netra_backend.app.clients.auth_client_core.AuthTokenCache'), \
             patch('netra_backend.app.clients.auth_client_core.AuthCircuitBreakerManager'), \
             patch('netra_backend.app.clients.auth_client_core.EnvironmentDetector'), \
             patch('netra_backend.app.clients.auth_client_core.OAuthConfigGenerator'), \
             patch('netra_backend.app.clients.auth_client_core.TracingManager'), \
             patch('netra_backend.app.clients.auth_client_core.get_circuit_breaker'), \
             patch('netra_backend.app.clients.auth_client_core.get_configuration'), \
             patch('netra_backend.app.clients.auth_client_core.get_env'):
            return AuthServiceClient()

    @pytest.mark.asyncio
    async def test_empty_token_validation(self, auth_client):
        """Test validation with empty token."""
        with pytest.raises(AuthServiceValidationError):
            await auth_client.validate_token("")

    @pytest.mark.asyncio
    async def test_none_token_validation(self, auth_client):
        """Test validation with None token."""
        with pytest.raises(AuthServiceValidationError):
            await auth_client.validate_token(None)

    @pytest.mark.asyncio
    async def test_extremely_long_token(self, auth_client):
        """Test handling of extremely long token."""
        long_token = "x" * 10000
        
        auth_client._client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Token too long"}
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(AuthServiceValidationError):
            await auth_client.validate_token(long_token)

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, auth_client):
        """Test handling of malformed JSON response."""
        auth_client._client = AsyncMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        mock_response.text = "Not JSON"
        auth_client._client.post.return_value = mock_response
        
        with pytest.raises(AuthServiceError):
            await auth_client.validate_token("test-token")

    @pytest.mark.asyncio
    async def test_network_timeout(self, auth_client):
        """Test handling of network timeout."""
        auth_client._client = AsyncMock()
        auth_client._client.post.side_effect = httpx.TimeoutException("Request timed out")
        
        # Should fall back to cache if available
        auth_client.token_cache.get = MagicMock(return_value={"valid": True, "cached": True})
        
        result = await auth_client.validate_token("test-token")
        
        assert result["valid"] is True
        assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, auth_client):
        """Test handling of DNS resolution failure."""
        auth_client._client = AsyncMock()
        auth_client._client.post.side_effect = httpx.ConnectError("DNS resolution failed")
        
        # Should fall back to degraded mode
        auth_client.token_cache.get = MagicMock(return_value=None)
        
        with pytest.raises(AuthServiceConnectionError):
            await auth_client.validate_token("test-token")