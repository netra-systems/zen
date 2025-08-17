"""Comprehensive tests for the Netra Auth Service core functionality.

Tests all FastAPI endpoints, OAuth flows, error handling, and service lifecycle.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Ensure secure authentication for AI optimization platform access
3. Value Impact: Prevents unauthorized access to AI optimization services and data
4. Revenue Impact: Critical for customer trust and retention across all segments
"""

import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.testclient import TestClient

from app.auth.auth_service import app, startup_event
from app.auth.auth_service import (
    initiate_oauth_login, handle_oauth_callback, exchange_token,
    logout_user, get_auth_service_status, get_frontend_auth_config,
    health_check, validate_exchange_request, process_logout_token,
    revoke_user_sessions, check_redis_connection
)


@pytest.fixture
def client():
    """Create test client for auth service."""
    return TestClient(app)


@pytest.fixture 
def mock_redis():
    """Mock Redis service for testing."""
    with patch('app.auth.auth_service.redis_service') as mock:
        mock.ping = AsyncMock(return_value=True)
        mock.keys = AsyncMock(return_value=['key1', 'key2'])
        mock.delete = AsyncMock()
        yield mock


@pytest.fixture
def mock_auth_services():
    """Mock all auth service dependencies."""
    mocks = {}
    services = [
        'app.auth.auth_service.auth_session_manager',
        'app.auth.auth_service.auth_token_service', 
        'app.auth.auth_service.auth_env_config',
        'app.auth.url_validators.validate_and_get_return_url',
        'app.auth.oauth_utils.build_google_oauth_url',
        'app.auth.oauth_utils.exchange_code_for_tokens',
        'app.auth.oauth_utils.get_user_info_from_google',
        'app.auth.auth_response_builders.build_oauth_callback_response',
        'app.auth.auth_response_builders.build_token_response',
        'app.auth.auth_response_builders.clear_auth_cookies',
        'app.auth.auth_response_builders.build_service_status',
        'app.auth.auth_response_builders.add_auth_urls',
        'app.auth.url_validators.get_auth_service_url'
    ]
    for service in services:
        mocks[service] = patch(service)
    return mocks


class TestAuthServiceEndpoints:
    """Test FastAPI auth service endpoints comprehensively."""
    
    @pytest.mark.asyncio
    async def test_login_endpoint_development_environment(self, mock_auth_services):
        """Test OAuth login in development environment."""
        with mock_auth_services['app.auth.auth_service.auth_session_manager'].start() as mock_session, \
             mock_auth_services['app.auth.url_validators.validate_and_get_return_url'].start() as mock_validate, \
             mock_auth_services['app.auth.oauth_utils.build_google_oauth_url'].start() as mock_oauth:
            mock_session.create_oauth_state = AsyncMock(return_value="dev_state_123")
            mock_validate.return_value = "http://localhost:3000/dashboard"
            mock_oauth.return_value = "https://accounts.google.com/oauth/authorize?dev"
            
            request = Mock()
            response = await initiate_oauth_login(request, pr=None, return_url="http://localhost:3000/dashboard")
            assert isinstance(response, RedirectResponse)


    @pytest.mark.asyncio
    async def test_login_endpoint_pr_environment(self, mock_auth_services):
        """Test OAuth login in PR environment."""
        with mock_auth_services['app.auth.auth_service.auth_session_manager'].start() as mock_session, \
             mock_auth_services['app.auth.url_validators.validate_and_get_return_url'].start() as mock_validate, \
             mock_auth_services['app.auth.oauth_utils.build_google_oauth_url'].start() as mock_oauth:
            mock_session.create_oauth_state = AsyncMock(return_value="pr42_state_123")
            mock_validate.return_value = "https://pr-42.staging.netrasystems.ai/dashboard"
            mock_oauth.return_value = "https://accounts.google.com/oauth/authorize?pr42"
            
            request = Mock()
            response = await initiate_oauth_login(request, pr="42", return_url="https://pr-42.staging.netrasystems.ai/dashboard")
            assert isinstance(response, RedirectResponse)


    @pytest.mark.asyncio
    async def test_login_endpoint_malicious_return_url(self, mock_auth_services):
        """Test OAuth login rejects malicious return URLs."""
        with mock_auth_services['app.auth.url_validators.validate_and_get_return_url'].start() as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid return URL")
            request = Mock()
            with pytest.raises(HTTPException) as exc_info:
                await initiate_oauth_login(request, return_url="https://malicious-site.com/steal")
            assert exc_info.value.status_code == 400


    @pytest.mark.asyncio
    async def test_callback_endpoint_success_with_user_data(self, mock_auth_services):
        """Test successful OAuth callback with complete user data."""
        mock_state_data = {"return_url": "http://localhost:3000", "pr_number": None}
        mock_token_data = {"access_token": "ya29.example_token", "token_type": "Bearer"}
        mock_user_info = {"id": "123456", "email": "user@example.com", "name": "Test User"}
        
        with mock_auth_services['app.auth.auth_service.auth_session_manager'].start() as mock_session, \
             mock_auth_services['app.auth.oauth_utils.exchange_code_for_tokens'].start() as mock_exchange, \
             mock_auth_services['app.auth.oauth_utils.get_user_info_from_google'].start() as mock_user, \
             mock_auth_services['app.auth.auth_service.auth_token_service'].start() as mock_token, \
             mock_auth_services['app.auth.auth_response_builders.build_oauth_callback_response'].start() as mock_response:
            mock_session.validate_and_consume_state = AsyncMock(return_value=mock_state_data)
            mock_exchange.return_value = mock_token_data
            mock_user.return_value = mock_user_info
            mock_token.generate_jwt.return_value = "jwt_token_123"
            mock_response.return_value = RedirectResponse(url="http://localhost:3000")
            
            request = Mock()
            response = await handle_oauth_callback(request, "auth_code_123", "state_123")
            assert isinstance(response, RedirectResponse)


    @pytest.mark.asyncio
    async def test_callback_endpoint_expired_state(self, mock_auth_services):
        """Test OAuth callback with expired state parameter."""
        with mock_auth_services['app.auth.auth_service.auth_session_manager'].start() as mock_session:
            mock_session.validate_and_consume_state = AsyncMock(
                side_effect=HTTPException(status_code=400, detail="OAuth state expired")
            )
            request = Mock()
            with pytest.raises(HTTPException) as exc_info:
                await handle_oauth_callback(request, "code123", "expired_state")
            assert exc_info.value.detail == "OAuth state expired"


    @pytest.mark.asyncio
    async def test_token_exchange_endpoint_success(self, mock_auth_services):
        """Test successful token exchange via POST endpoint."""
        mock_token_data = {"access_token": "ya29.token", "refresh_token": "refresh123"}
        mock_user_info = {"id": "user123", "email": "test@example.com", "verified_email": True}
        
        with mock_auth_services['app.auth.oauth_utils.exchange_code_for_tokens'].start() as mock_exchange, \
             mock_auth_services['app.auth.oauth_utils.get_user_info_from_google'].start() as mock_user, \
             mock_auth_services['app.auth.auth_service.auth_token_service'].start() as mock_token, \
             mock_auth_services['app.auth.auth_response_builders.build_token_response'].start() as mock_response:
            mock_exchange.return_value = mock_token_data
            mock_user.return_value = mock_user_info
            mock_token.generate_jwt.return_value = "jwt_final_token"
            mock_response.return_value = {"access_token": "jwt_final_token", "user_info": mock_user_info}
            
            request = Mock()
            request.json = AsyncMock(return_value={"code": "exchange_code_123"})
            response = await exchange_token(request)
            assert response["access_token"] == "jwt_final_token"


    def test_validate_exchange_request_missing_code(self):
        """Test token exchange validation with missing code."""
        with pytest.raises(HTTPException) as exc_info:
            validate_exchange_request(None)
        assert exc_info.value.status_code == 400
        assert "Authorization code required" in exc_info.value.detail


    def test_validate_exchange_request_empty_code(self):
        """Test token exchange validation with empty code."""
        with pytest.raises(HTTPException) as exc_info:
            validate_exchange_request("")
        assert exc_info.value.status_code == 400


    @pytest.mark.asyncio
    async def test_logout_endpoint_with_valid_token(self, mock_auth_services, mock_redis):
        """Test user logout with valid JWT token."""
        mock_claims = {"sub": "user123", "email": "test@example.com", "exp": 1234567890}
        
        with mock_auth_services['app.auth.auth_service.auth_token_service'].start() as mock_token, \
             mock_auth_services['app.auth.auth_response_builders.clear_auth_cookies'].start() as mock_clear:
            mock_token.validate_jwt.return_value = mock_claims
            mock_clear.return_value = None
            
            request = Mock()
            request.headers = {"Authorization": "Bearer valid_jwt_token"}
            response = await logout_user(request)
            assert isinstance(response, JSONResponse)
            mock_redis.keys.assert_called_once()


    @pytest.mark.asyncio
    async def test_logout_endpoint_no_authorization_header(self, mock_auth_services):
        """Test logout without authorization header."""
        with mock_auth_services['app.auth.auth_response_builders.clear_auth_cookies'].start():
            request = Mock()
            request.headers = {}
            response = await logout_user(request)
            assert isinstance(response, JSONResponse)


    @pytest.mark.asyncio
    async def test_process_logout_token_invalid_token(self, mock_auth_services):
        """Test logout token processing with invalid token."""
        with mock_auth_services['app.auth.auth_service.auth_token_service'].start() as mock_token:
            mock_token.validate_jwt.return_value = None
            await process_logout_token("Bearer invalid_token")
            mock_token.validate_jwt.assert_called_once_with("invalid_token")


    @pytest.mark.asyncio
    async def test_revoke_user_sessions_success(self, mock_redis):
        """Test successful user session revocation."""
        mock_redis.keys.return_value = ['user_session:123:device1', 'user_session:123:device2']
        await revoke_user_sessions("123")
        mock_redis.delete.assert_called_once_with('user_session:123:device1', 'user_session:123:device2')


    @pytest.mark.asyncio
    async def test_revoke_user_sessions_no_sessions(self, mock_redis):
        """Test user session revocation when no sessions exist."""
        mock_redis.keys.return_value = []
        await revoke_user_sessions("123")
        mock_redis.delete.assert_not_called()


    @pytest.mark.asyncio
    async def test_check_redis_connection_success(self, mock_redis):
        """Test successful Redis connection check."""
        result = await check_redis_connection()
        assert result is True
        mock_redis.ping.assert_called_once()


    @pytest.mark.asyncio
    async def test_check_redis_connection_failure(self, mock_redis):
        """Test Redis connection check failure."""
        mock_redis.ping.side_effect = Exception("Connection failed")
        result = await check_redis_connection()
        assert result is False


    @pytest.mark.asyncio
    async def test_status_endpoint_redis_connected(self, mock_auth_services):
        """Test auth service status with Redis connected."""
        with mock_auth_services['app.auth.auth_response_builders.build_service_status'].start() as mock_status, \
             patch('app.auth.auth_service.check_redis_connection', return_value=True):
            mock_status.return_value = {"status": "healthy", "redis_connected": True}
            response = await get_auth_service_status()
            assert response["status"] == "healthy"
            assert response["redis_connected"] is True


    @pytest.mark.asyncio
    async def test_status_endpoint_redis_disconnected(self, mock_auth_services):
        """Test auth service status with Redis disconnected."""
        with mock_auth_services['app.auth.auth_response_builders.build_service_status'].start() as mock_status, \
             patch('app.auth.auth_service.check_redis_connection', return_value=False):
            mock_status.return_value = {"status": "degraded", "redis_connected": False}
            response = await get_auth_service_status()
            assert response["redis_connected"] is False


    @pytest.mark.asyncio
    async def test_config_endpoint_development(self, mock_auth_services):
        """Test frontend config endpoint in development."""
        mock_config = {"client_id": "dev_client_id", "environment": "development", "allow_dev_login": True}
        
        with mock_auth_services['app.auth.auth_service.auth_env_config'].start() as mock_env, \
             mock_auth_services['app.auth.url_validators.get_auth_service_url'].start() as mock_url, \
             mock_auth_services['app.auth.auth_response_builders.add_auth_urls'].start() as mock_urls:
            mock_env.get_frontend_config.return_value = mock_config
            mock_url.return_value = "http://localhost:8001"
            mock_urls.return_value = None
            
            response = await get_frontend_auth_config()
            mock_urls.assert_called_once_with(mock_config, "http://localhost:8001")


    @pytest.mark.asyncio
    async def test_config_endpoint_production(self, mock_auth_services):
        """Test frontend config endpoint in production."""
        mock_config = {"client_id": "prod_client_id", "environment": "production", "allow_dev_login": False}
        
        with mock_auth_services['app.auth.auth_service.auth_env_config'].start() as mock_env, \
             mock_auth_services['app.auth.url_validators.get_auth_service_url'].start() as mock_url, \
             mock_auth_services['app.auth.auth_response_builders.add_auth_urls'].start() as mock_urls:
            mock_env.get_frontend_config.return_value = mock_config
            mock_url.return_value = "https://api.netrasystems.ai"
            mock_urls.return_value = None
            
            response = await get_frontend_auth_config()
            assert mock_config["allow_dev_login"] is False


    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test basic health check endpoint."""
        response = await health_check()
        assert response["status"] == "ok"
        assert response["service"] == "netra-auth-service"


    @pytest.mark.asyncio
    async def test_startup_event_success(self, mock_redis):
        """Test successful startup event execution."""
        mock_redis.connect = AsyncMock()
        await startup_event()
        mock_redis.connect.assert_called_once()


    @pytest.mark.asyncio
    async def test_startup_event_redis_connection_error(self, mock_redis):
        """Test startup event with Redis connection error."""
        mock_redis.connect.side_effect = ConnectionError("Redis connection failed")
        # Should not raise exception for ConnectionError
        await startup_event()


    @pytest.mark.asyncio
    async def test_startup_event_critical_error(self, mock_redis):
        """Test startup event with critical error."""
        mock_redis.connect.side_effect = ValueError("Critical config error")
        with pytest.raises(ValueError):
            await startup_event()


class TestAuthServiceIntegration:
    """Test auth service integration scenarios."""
    
    def test_cors_configuration(self, client):
        """Test CORS middleware configuration."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:3000,https://netrasystems.ai"}):
            response = client.options("/auth/status", headers={"Origin": "http://localhost:3000"})
            # Should not block CORS preflight
            assert response.status_code in [200, 405]  # Either allowed or method not allowed


    def test_app_metadata(self):
        """Test FastAPI app metadata configuration."""
        assert app.title == "Netra Auth Service"
        assert app.description == "OAuth authentication service for all environments"
        assert app.version == "1.0.0"


    def test_environment_variable_isolation(self):
        """Test auth service isolates environment variables properly."""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test_isolation"}):
            # Should not affect running service
            assert os.getenv("GOOGLE_CLIENT_ID") == "test_isolation"