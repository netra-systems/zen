"""Tests for PR router utility functions and class methods."""

import os
import pytest
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlparse

from app.auth.pr_router import (
    get_pr_redirect_url,
    _generate_secure_csrf_token,
    _build_oauth_authorization_url,
    _log_pr_auth_initiation,
    _validate_pr_in_cache,
    _get_oauth_client_id,
    create_pr_auth_router,
    PRAuthRouter,
    PR_STATE_TTL
)
from app.core.exceptions_auth import AuthenticationError


# Shared fixtures
@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for testing."""
    redis = Mock()
    redis.enabled = True
    redis.get = AsyncMock(return_value="active")
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


# Tests for get_pr_redirect_url function
class TestGetPrRedirectUrl:
    """Test get_pr_redirect_url function with success and error cases."""

    @patch('app.auth.pr_router._validate_pr_number_format')
    def test_get_pr_redirect_url_success(self, mock_validate):
        """Test successful PR redirect URL generation."""
        result = get_pr_redirect_url("123")
        
        expected = "https://pr-123.staging.netrasystems.ai"
        assert result == expected
        mock_validate.assert_called_once_with("123")

    @patch('app.auth.pr_router._validate_pr_number_format')
    def test_get_pr_redirect_url_invalid(self, mock_validate):
        """Test get_pr_redirect_url with invalid PR number."""
        mock_validate.side_effect = AuthenticationError("Invalid PR number")
        
        with pytest.raises(AuthenticationError, match="Invalid PR number"):
            get_pr_redirect_url("invalid")


# Tests for _generate_secure_csrf_token function
class TestGenerateSecureCsrfToken:
    """Test _generate_secure_csrf_token function with success and uniqueness."""

    def test_generate_csrf_token_success(self):
        """Test successful CSRF token generation."""
        token = _generate_secure_csrf_token()
        
        assert isinstance(token, str)
        assert len(token) > 0
        # URL-safe base64 characters only
        assert all(c.isalnum() or c in '-_' for c in token)

    def test_generate_csrf_token_uniqueness(self):
        """Test CSRF token uniqueness across multiple generations."""
        tokens = [_generate_secure_csrf_token() for _ in range(10)]
        unique_tokens = set(tokens)
        
        assert len(unique_tokens) == len(tokens)  # All tokens should be unique
        assert all(len(token) > 20 for token in tokens)  # Adequate length


# Tests for OAuth URL building
class TestOAuthUrl:
    """Test OAuth URL building functions."""

    @patch('app.auth.pr_router._get_oauth_client_id')
    def test_build_oauth_authorization_url_success(self, mock_client_id):
        """Test successful OAuth URL building."""
        mock_client_id.return_value = "test-client-id"
        
        url = _build_oauth_authorization_url("test-state")
        
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert "state=test-state" in url
        assert "client_id=test-client-id" in url

    @patch.dict(os.environ, {}, clear=True)
    def test_get_oauth_client_id_missing(self):
        """Test OAuth client ID retrieval when not configured."""
        with pytest.raises(AuthenticationError, match="OAuth client ID not configured"):
            _get_oauth_client_id()

    @patch.dict(os.environ, {"GOOGLE_OAUTH_CLIENT_ID_STAGING": "test-id"})
    def test_get_oauth_client_id_success(self):
        """Test successful OAuth client ID retrieval."""
        client_id = _get_oauth_client_id()
        assert client_id == "test-id"


# Tests for cache validation
class TestCacheValidation:
    """Test PR cache validation functions."""

    async def test_validate_pr_in_cache_redis_enabled(self, mock_redis_manager):
        """Test PR cache validation when Redis is enabled."""
        mock_redis_manager.get.return_value = "active"
        
        # Should not raise exception
        await _validate_pr_in_cache("123", mock_redis_manager)
        
        mock_redis_manager.get.assert_called_once_with("active_pr:123")

    async def test_validate_pr_in_cache_redis_disabled(self):
        """Test PR cache validation when Redis is disabled."""
        mock_redis = Mock()
        mock_redis.enabled = False
        
        # Should not raise exception and not call Redis
        await _validate_pr_in_cache("123", mock_redis)

    async def test_validate_pr_in_cache_not_found(self, mock_redis_manager):
        """Test PR cache validation when PR not in cache."""
        mock_redis_manager.get.return_value = None
        
        # Should add to cache when not found
        await _validate_pr_in_cache("123", mock_redis_manager)
        
        mock_redis_manager.setex.assert_called_once_with("active_pr:123", 3600, "active")


# Tests for logging function
class TestLogging:
    """Test logging functions."""

    @patch('app.auth.pr_router.logger')
    async def test_log_pr_auth_initiation_success(self, mock_logger):
        """Test successful PR auth logging."""
        await _log_pr_auth_initiation("123", "https://example.com")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "PR OAuth initiated" in call_args[0][0]

    @patch('app.auth.pr_router.logger')
    async def test_log_pr_auth_initiation_invalid(self, mock_logger):
        """Test PR auth logging with invalid data."""
        await _log_pr_auth_initiation("", "")
        
        # Should still log even with empty values
        mock_logger.info.assert_called_once()


# Tests for factory function
class TestFactoryFunction:
    """Test PR auth router factory function."""

    def test_create_pr_auth_router_success(self, mock_redis_manager):
        """Test successful PR auth router creation."""
        router = create_pr_auth_router(mock_redis_manager)
        
        assert isinstance(router, PRAuthRouter)
        assert router.redis == mock_redis_manager
        assert router.state_ttl == PR_STATE_TTL

    def test_create_pr_auth_router_initialization(self, mock_redis_manager):
        """Test PR auth router proper initialization."""
        router = create_pr_auth_router(mock_redis_manager)
        
        assert hasattr(router, 'github_client')
        assert hasattr(router, 'redis')
        assert hasattr(router, 'state_ttl')


# Tests for PRAuthRouter class
class TestPRAuthRouterClass:
    """Test PRAuthRouter class methods."""

    def test_pr_auth_router_init_success(self, mock_redis_manager):
        """Test successful PRAuthRouter initialization."""
        router = PRAuthRouter(mock_redis_manager)
        
        assert router.redis == mock_redis_manager
        assert router.state_ttl == PR_STATE_TTL

    @patch('app.auth.pr_router.httpx.AsyncClient')
    def test_pr_auth_router_github_client_init(self, mock_client, mock_redis_manager):
        """Test GitHub client initialization in PRAuthRouter."""
        router = PRAuthRouter(mock_redis_manager)
        
        # GitHub client should be initialized
        mock_client.assert_called_once_with(base_url="https://api.github.com")

    @patch('app.auth.pr_router.httpx.AsyncClient', side_effect=Exception("Connection failed"))
    def test_pr_auth_router_github_client_failure(self, mock_client, mock_redis_manager):
        """Test GitHub client initialization failure handling."""
        router = PRAuthRouter(mock_redis_manager)
        
        # Should handle failure gracefully
        assert router.github_client is None

    def test_oauth_url_includes_required_params(self):
        """Test OAuth URL includes all required parameters."""
        with patch('app.auth.pr_router._get_oauth_client_id', return_value="test-client"):
            url = _build_oauth_authorization_url("test-state")
            
            required_params = [
                "client_id=test-client",
                "redirect_uri=",
                "response_type=code",
                "scope=openid",
                "state=test-state",
                "access_type=online"
            ]
            
            for param in required_params:
                assert param in url

    def test_pr_redirect_url_format(self):
        """Test PR redirect URL follows expected format."""
        with patch('app.auth.pr_router._validate_pr_number_format'):
            url = get_pr_redirect_url("456")
            
            assert url == "https://pr-456.staging.netrasystems.ai"
            assert url.startswith("https://")
            assert "pr-456" in url
            assert "staging.netrasystems.ai" in url