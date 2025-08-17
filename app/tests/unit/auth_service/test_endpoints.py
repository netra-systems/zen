"""Unit tests for auth service endpoint functions.

Tests FastAPI endpoint handlers for OAuth flow.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

from app.auth.auth_service import (
    initiate_oauth_login, handle_oauth_callback, exchange_token, logout_user,
    get_auth_service_status, get_frontend_auth_config, health_check, startup_event
)


class TestAuthServiceEndpoints:
    """Test FastAPI endpoint functions."""
    
    @pytest.mark.asyncio
    async def test_login_endpoint_success(self):
        """Test successful OAuth login initiation."""
        with patch('app.auth.auth_service.auth_session_manager.create_oauth_state', return_value="state123"), \
             patch('app.auth.auth_service.auth_env_config.get_oauth_config'), \
             patch('app.auth.url_validators.validate_and_get_return_url', return_value="http://example.com"), \
             patch('app.auth.oauth_utils.build_google_oauth_url', return_value="https://oauth.url"):
            request = MagicMock()
            response = await initiate_oauth_login(request, pr="42", return_url="http://example.com")
            assert isinstance(response, RedirectResponse)
            
    @pytest.mark.asyncio
    async def test_login_endpoint_invalid_params(self):
        """Test OAuth login with invalid return URL."""
        with patch('app.auth.url_validators.validate_and_get_return_url') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid return URL")
            request = MagicMock()
            with pytest.raises(HTTPException):
                await initiate_oauth_login(request, return_url="http://malicious.com")
                
    @pytest.mark.asyncio
    async def test_callback_endpoint_success(self):
        """Test successful OAuth callback handling."""
        mock_state_data = {"return_url": "http://example.com"}
        mock_token_data = {"access_token": "token123"}
        mock_user_info = {"id": "123", "email": "test@example.com"}
        
        with patch('app.auth.auth_service.auth_session_manager.validate_and_consume_state', return_value=mock_state_data), \
             patch('app.auth.oauth_utils.exchange_code_for_tokens', return_value=mock_token_data), \
             patch('app.auth.oauth_utils.get_user_info_from_google', return_value=mock_user_info), \
             patch('app.auth.auth_service.auth_token_service.generate_jwt', return_value="jwt123"), \
             patch('app.auth.auth_response_builders.build_oauth_callback_response', return_value=RedirectResponse(url="/")):
            request = MagicMock()
            response = await handle_oauth_callback(request, "code123", "state123")
            assert isinstance(response, RedirectResponse)
            
    @pytest.mark.asyncio
    async def test_callback_endpoint_invalid_state(self):
        """Test OAuth callback with invalid state."""
        with patch('app.auth.auth_service.auth_session_manager.validate_and_consume_state') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid state")
            request = MagicMock()
            with pytest.raises(HTTPException):
                await handle_oauth_callback(request, "code123", "invalid_state")
                
    @pytest.mark.asyncio
    async def test_token_endpoint_success(self):
        """Test successful token exchange."""
        mock_token_data = {"access_token": "token123"}
        mock_user_info = {"id": "123", "email": "test@example.com"}
        
        with patch('app.auth.oauth_utils.exchange_code_for_tokens', return_value=mock_token_data), \
             patch('app.auth.oauth_utils.get_user_info_from_google', return_value=mock_user_info), \
             patch('app.auth.auth_service.auth_token_service.generate_jwt', return_value="jwt123"):
            request = MagicMock()
            request.json = AsyncMock(return_value={"code": "code123"})
            response = await exchange_token(request)
            assert response["access_token"] == "jwt123"
            assert response["user_info"] == mock_user_info
            
    @pytest.mark.asyncio
    async def test_token_endpoint_invalid_code(self):
        """Test token exchange with missing code."""
        request = MagicMock()
        request.json = AsyncMock(return_value={})
        with pytest.raises(HTTPException) as exc_info:
            await exchange_token(request)
        assert exc_info.value.status_code == 400
        
    @pytest.mark.asyncio
    async def test_logout_endpoint_success(self):
        """Test successful user logout."""
        mock_claims = {"sub": "123", "email": "test@example.com"}
        with patch('app.auth.auth_service.auth_token_service.validate_jwt', return_value=mock_claims), \
             patch('app.auth.auth_service.revoke_user_sessions'), \
             patch('app.auth.auth_response_builders.clear_auth_cookies'):
            request = MagicMock()
            request.headers = {"Authorization": "Bearer valid_token"}
            response = await logout_user(request)
            assert isinstance(response, JSONResponse)
            
    @pytest.mark.asyncio
    async def test_logout_endpoint_invalid_token(self):
        """Test logout with invalid token."""
        with patch('app.auth.auth_service.auth_token_service.validate_jwt', return_value=None), \
             patch('app.auth.auth_response_builders.clear_auth_cookies'):
            request = MagicMock()
            request.headers = {"Authorization": "Bearer invalid_token"}
            response = await logout_user(request)
            assert isinstance(response, JSONResponse)
            
    @pytest.mark.asyncio
    async def test_status_endpoint_success(self):
        """Test successful auth service status check."""
        with patch('app.auth.auth_service.check_redis_connection', return_value=True):
            response = await get_auth_service_status()
            assert response["status"] == "healthy"
            assert "redis_connected" in response
            
    @pytest.mark.asyncio
    async def test_status_endpoint_redis_down(self):
        """Test auth service status with Redis down."""
        with patch('app.auth.auth_service.check_redis_connection', return_value=False):
            response = await get_auth_service_status()
            assert response["status"] == "healthy"
            assert response["redis_connected"] is False
            
    @pytest.mark.asyncio
    async def test_config_endpoint_success(self):
        """Test successful frontend config retrieval."""
        mock_config = {"client_id": "test_client_id"}
        with patch('app.auth.auth_service.auth_env_config.get_frontend_config', return_value=mock_config), \
             patch('app.auth.url_validators.get_auth_service_url', return_value="http://localhost:8001"):
            response = await get_frontend_auth_config()
            assert "auth_service_url" in response
            assert "login_url" in response
            
    @pytest.mark.asyncio 
    async def test_config_endpoint_pr_environment(self):
        """Test frontend config in PR environment."""
        mock_config = {"client_id": "test_client_id", "use_proxy": True}
        with patch('app.auth.auth_service.auth_env_config.get_frontend_config', return_value=mock_config), \
             patch('app.auth.url_validators.get_auth_service_url', return_value="https://auth.staging.netrasystems.ai"):
            response = await get_frontend_auth_config()
            assert response["auth_service_url"] == "https://auth.staging.netrasystems.ai"
            
    @pytest.mark.asyncio
    async def test_health_check_endpoint_success(self):
        """Test successful health check endpoint."""
        response = await health_check()
        assert response["status"] == "ok"
        assert response["service"] == "netra-auth-service"
        
    @pytest.mark.asyncio
    async def test_health_check_endpoint_response_format(self):
        """Test health check endpoint response format."""
        response = await health_check()
        assert isinstance(response, dict)
        assert "status" in response
        assert "service" in response
        
    @pytest.mark.asyncio
    async def test_startup_event_success(self):
        """Test successful startup event initialization."""
        with patch('app.auth.auth_service.redis_service.connect') as mock_connect:
            mock_connect.return_value = None
            await startup_event()
            mock_connect.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_startup_event_redis_failure(self):
        """Test startup event with Redis connection failure."""
        with patch('app.auth.auth_service.redis_service.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            with pytest.raises(Exception):
                await startup_event()