"""Unit tests for auth service helper functions.

Tests utility and helper functions used by auth service endpoints.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.auth.auth_service import (
    _validate_and_get_return_url, _get_default_return_url, _validate_return_url_security,
    _build_google_oauth_url, _get_oauth_redirect_uri, _exchange_code_for_tokens,
    _perform_token_exchange_request, _get_user_info_from_google,
    _build_oauth_callback_response, _build_pr_environment_response,
    _set_auth_cookies, _set_pr_auth_cookies, _revoke_user_sessions,
    _clear_auth_cookies, _check_redis_connection, _get_auth_service_url
)
from app.auth.environment_config import auth_env_config


class TestAuthServiceHelpers:
    """Test helper functions."""
    
    def test_validate_return_url_success(self):
        """Test successful return URL validation."""
        with patch('app.auth.auth_service._get_default_return_url', return_value="http://localhost:8000"), \
             patch('app.auth.auth_service._validate_return_url_security'):
            result = _validate_and_get_return_url("http://localhost:8000/auth")
            assert result == "http://localhost:8000/auth"
            
    def test_validate_return_url_invalid(self):
        """Test return URL validation with invalid URL."""
        with patch('app.auth.auth_service._validate_return_url_security') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid return URL")
            with pytest.raises(HTTPException):
                _validate_and_get_return_url("http://malicious.com")
                
    def test_get_default_return_url_success(self):
        """Test default return URL generation."""
        mock_config = {"javascript_origins": ["http://localhost:8000"]}
        with patch('app.auth.auth_service.auth_env_config.get_frontend_config', return_value=mock_config), \
             patch('app.auth.auth_service.auth_env_config.is_pr_environment', False):
            result = _get_default_return_url()
            assert result == "http://localhost:8000"
            
    def test_get_default_return_url_pr_environment(self):
        """Test default return URL in PR environment."""
        with patch('app.auth.auth_service.auth_env_config.is_pr_environment', True), \
             patch('app.auth.auth_service.auth_env_config.pr_number', "42"):
            result = _get_default_return_url()
            assert result == "https://pr-42.staging.netrasystems.ai"
            
    def test_validate_return_url_security_success(self):
        """Test return URL security validation success."""
        mock_config = MagicMock()
        mock_config.javascript_origins = ["http://localhost:8000", "https://app.netrasystems.ai"]
        with patch('app.auth.auth_service.auth_env_config.get_oauth_config', return_value=mock_config):
            _validate_return_url_security("http://localhost:8000/auth")  # Should not raise
            
    def test_validate_return_url_security_invalid(self):
        """Test return URL security validation failure."""
        mock_config = MagicMock()
        mock_config.javascript_origins = ["http://localhost:8000"]
        with patch('app.auth.auth_service.auth_env_config.get_oauth_config', return_value=mock_config):
            with pytest.raises(HTTPException):
                _validate_return_url_security("http://malicious.com")
                
    def test_build_google_oauth_url_success(self):
        """Test Google OAuth URL building."""
        mock_config = MagicMock()
        mock_config.client_id = "test_client_id"
        with patch('app.auth.auth_service._get_oauth_redirect_uri', return_value="http://localhost:8001/auth/callback"):
            url = _build_google_oauth_url(mock_config, "state123")
            assert "https://accounts.google.com/o/oauth2/v2/auth" in url
            assert "state=state123" in url
            
    def test_get_oauth_redirect_uri_development(self):
        """Test OAuth redirect URI for development."""
        with patch.object(auth_env_config, 'environment') as mock_env:
            mock_env.value = "development"
            uri = _get_oauth_redirect_uri()
            assert uri == "http://localhost:8001/auth/callback"
            
    def test_get_oauth_redirect_uri_production(self):
        """Test OAuth redirect URI for production."""
        with patch.object(auth_env_config, 'environment') as mock_env:
            mock_env.value = "production"
            uri = _get_oauth_redirect_uri()
            assert uri == "https://auth.netrasystems.ai/auth/callback"
            
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self):
        """Test successful code to token exchange."""
        mock_config = MagicMock()
        mock_config.client_id = "test_client_id"
        mock_config.client_secret = "test_secret"
        mock_response = {"access_token": "token123", "token_type": "Bearer"}
        
        with patch('app.auth.auth_service._get_oauth_redirect_uri', return_value="http://localhost:8001/auth/callback"), \
             patch('app.auth.auth_service._perform_token_exchange_request', return_value=mock_response):
            result = await _exchange_code_for_tokens("code123", mock_config)
            assert result["access_token"] == "token123"
            
    @pytest.mark.asyncio
    async def test_perform_token_exchange_request_success(self):
        """Test successful token exchange HTTP request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token123"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            result = await _perform_token_exchange_request("https://oauth.googleapis.com/token", {"code": "code123"})
            assert result["access_token"] == "token123"
            
    @pytest.mark.asyncio
    async def test_perform_token_exchange_request_failure(self):
        """Test failed token exchange HTTP request."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            with pytest.raises(HTTPException):
                await _perform_token_exchange_request("https://oauth.googleapis.com/token", {"code": "invalid"})
                
    @pytest.mark.asyncio
    async def test_get_user_info_from_google_success(self):
        """Test successful user info retrieval from Google."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "email": "test@example.com"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            result = await _get_user_info_from_google("token123")
            assert result["id"] == "123"
            
    @pytest.mark.asyncio
    async def test_get_user_info_from_google_failure(self):
        """Test failed user info retrieval from Google."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            with pytest.raises(HTTPException):
                await _get_user_info_from_google("invalid_token")
                
    def test_build_oauth_callback_response_success(self):
        """Test OAuth callback response building."""
        state_data = {"return_url": "http://localhost:8000"}
        user_info = {"id": "123", "email": "test@example.com"}
        
        with patch('app.auth.auth_service._set_auth_cookies'):
            response = _build_oauth_callback_response(state_data, "jwt123", user_info)
            assert isinstance(response, RedirectResponse)
            
    def test_build_oauth_callback_response_pr_env(self):
        """Test OAuth callback response for PR environment."""
        state_data = {"return_url": "http://localhost:8000", "pr_number": "42"}
        user_info = {"id": "123", "email": "test@example.com"}
        
        with patch('app.auth.auth_service._build_pr_environment_response', return_value=RedirectResponse(url="/")):
            response = _build_oauth_callback_response(state_data, "jwt123", user_info)
            assert isinstance(response, RedirectResponse)
            
    def test_build_pr_environment_response_success(self):
        """Test PR environment response building."""
        with patch('app.auth.auth_service._set_pr_auth_cookies'):
            response = _build_pr_environment_response("http://localhost:8000", "jwt123", {}, "42")
            assert isinstance(response, RedirectResponse)
            
    def test_set_auth_cookies_success(self):
        """Test setting secure authentication cookies."""
        response = MagicMock()
        _set_auth_cookies(response, "jwt123")
        response.set_cookie.assert_called_once()
        
    def test_set_pr_auth_cookies_success(self):
        """Test setting PR environment authentication cookies."""
        response = MagicMock()
        _set_pr_auth_cookies(response, "jwt123", "42")
        response.set_cookie.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_revoke_user_sessions_success(self):
        """Test successful user session revocation."""
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.keys = AsyncMock(return_value=["session1", "session2"])
            mock_redis.delete = AsyncMock()
            await _revoke_user_sessions("user123")
            mock_redis.delete.assert_called_once_with("session1", "session2")
            
    @pytest.mark.asyncio
    async def test_revoke_user_sessions_no_user(self):
        """Test session revocation with no user ID."""
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.keys = AsyncMock()
            await _revoke_user_sessions(None)
            mock_redis.keys.assert_not_called()
            
    def test_clear_auth_cookies_success(self):
        """Test clearing authentication cookies."""
        response = MagicMock()
        _clear_auth_cookies(response)
        assert response.delete_cookie.call_count == 2
        
    @pytest.mark.asyncio
    async def test_check_redis_connection_success(self):
        """Test successful Redis connection check."""
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.ping = AsyncMock()
            result = await _check_redis_connection()
            assert result is True
            
    @pytest.mark.asyncio
    async def test_check_redis_connection_failure(self):
        """Test failed Redis connection check."""
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))
            result = await _check_redis_connection()
            assert result is False
            
    def test_get_auth_service_url_development(self):
        """Test auth service URL for development."""
        with patch.object(auth_env_config, 'environment') as mock_env:
            mock_env.value = "development"
            url = _get_auth_service_url()
            assert url == "http://localhost:8001"
            
    def test_get_auth_service_url_production(self):
        """Test auth service URL for production."""
        with patch.object(auth_env_config, 'environment') as mock_env:
            mock_env.value = "production"
            url = _get_auth_service_url()
            assert url == "https://auth.netrasystems.ai"
            
    def test_get_oauth_redirect_uri_staging(self):
        """Test OAuth redirect URI for staging environment."""
        with patch.object(auth_env_config, 'environment') as mock_env:
            mock_env.value = "staging"
            uri = _get_oauth_redirect_uri()
            assert uri == "https://auth.staging.netrasystems.ai/auth/callback"
            
    def test_get_auth_service_url_staging(self):
        """Test auth service URL for staging environment."""
        with patch.object(auth_env_config, 'environment') as mock_env:
            mock_env.value = "staging"
            url = _get_auth_service_url()
            assert url == "https://auth.staging.netrasystems.ai"