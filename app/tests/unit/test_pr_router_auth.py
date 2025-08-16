"""Tests for PR router authentication and validation functions."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.auth.pr_router import (
    route_pr_auth,
    validate_pr_environment,
    encode_pr_state,
    decode_pr_state,
    PRAuthRouter
)
from app.core.exceptions_auth import AuthenticationError, NetraSecurityException
from fastapi.responses import RedirectResponse


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


@pytest.fixture
def mock_github_client():
    """Mock GitHub HTTP client for testing."""
    client = Mock()
    client.get = AsyncMock()
    return client


@pytest.fixture
def pr_auth_router(mock_redis_manager):
    """Create PRAuthRouter instance for testing."""
    return PRAuthRouter(mock_redis_manager)


@pytest.fixture
def valid_pr_state_data():
    """Valid PR state data for testing."""
    import time
    return {
        "pr_number": "123",
        "return_url": "https://pr-123.staging.netrasystems.ai",
        "csrf_token": "test-csrf-token-12345678",
        "timestamp": int(time.time()),
        "version": "1.0"
    }


# Tests for route_pr_auth function
class TestRoutePrAuth:
    """Test route_pr_auth function with success and error cases."""

    @patch('app.auth.pr_router._validate_pr_inputs')
    @patch('app.auth.pr_router.validate_pr_environment')
    @patch('app.auth.pr_router._generate_secure_csrf_token')
    @patch('app.auth.pr_router.encode_pr_state')
    @patch('app.auth.pr_router._build_oauth_authorization_url')
    @patch('app.auth.pr_router._log_pr_auth_initiation')
    async def test_route_pr_auth_success(self, mock_log, mock_oauth_url, mock_encode, 
                                       mock_csrf, mock_validate_env, mock_validate_inputs,
                                       pr_auth_router):
        """Test successful PR authentication routing."""
        mock_csrf.return_value = "csrf-token-123"
        mock_encode.return_value = "encoded-state-data"
        mock_oauth_url.return_value = "https://oauth.example.com/auth?state=encoded"
        
        result = await route_pr_auth("123", "https://example.com", pr_auth_router)
        
        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "https://oauth.example.com/auth?state=encoded"
        mock_validate_inputs.assert_called_once_with("123", "https://example.com")
        mock_validate_env.assert_called_once_with("123", pr_auth_router)

    @patch('app.auth.pr_router._validate_pr_inputs')
    async def test_route_pr_auth_invalid_pr(self, mock_validate_inputs, pr_auth_router):
        """Test route_pr_auth with invalid PR number."""
        mock_validate_inputs.side_effect = AuthenticationError("Invalid PR number")
        
        with pytest.raises(AuthenticationError, match="Invalid PR number"):
            await route_pr_auth("invalid", "https://example.com", pr_auth_router)


# Tests for validate_pr_environment function  
class TestValidatePrEnvironment:
    """Test validate_pr_environment function with success and error cases."""

    @patch('app.auth.pr_router._validate_pr_number_format')
    @patch('app.auth.pr_router._validate_pr_with_github')
    @patch('app.auth.pr_router._validate_pr_in_cache')
    async def test_validate_pr_environment_valid(self, mock_cache, mock_github, 
                                                mock_format, pr_auth_router, mock_github_client):
        """Test successful PR environment validation."""
        pr_auth_router.github_client = mock_github_client
        
        await validate_pr_environment("123", pr_auth_router)
        
        mock_format.assert_called_once_with("123")
        mock_github.assert_called_once_with("123", pr_auth_router.github_client)
        mock_cache.assert_called_once_with("123", pr_auth_router.redis)

    @patch('app.auth.pr_router._validate_pr_number_format')
    async def test_validate_pr_environment_invalid(self, mock_format, pr_auth_router):
        """Test validate_pr_environment with invalid PR number format."""
        mock_format.side_effect = AuthenticationError("Invalid format")
        
        with pytest.raises(AuthenticationError, match="Invalid format"):
            await validate_pr_environment("abc", pr_auth_router)


# Tests for encode_pr_state function
class TestEncodePrState:
    """Test encode_pr_state function with success and error cases."""

    @patch('app.auth.pr_router._build_pr_state_data')
    @patch('app.auth.pr_router._encode_state_to_base64')
    @patch('app.auth.pr_router._store_csrf_token_in_redis')
    async def test_encode_pr_state_success(self, mock_store, mock_encode, mock_build,
                                         pr_auth_router, valid_pr_state_data):
        """Test successful PR state encoding."""
        mock_build.return_value = valid_pr_state_data
        mock_encode.return_value = "encoded-state-123"
        
        result = await encode_pr_state("123", "https://example.com", "csrf-token", pr_auth_router)
        
        assert result == "encoded-state-123"
        mock_build.assert_called_once_with("123", "https://example.com", "csrf-token")
        mock_store.assert_called_once_with("123", "csrf-token", pr_auth_router.redis)

    @patch('app.auth.pr_router._build_pr_state_data')
    @patch('app.auth.pr_router._encode_state_to_base64')
    @patch('app.auth.pr_router._store_csrf_token_in_redis')
    async def test_encode_pr_state_expired(self, mock_store, mock_encode, mock_build,
                                         pr_auth_router):
        """Test encode_pr_state with expired timestamp data."""
        import time
        expired_data = {
            "pr_number": "123",
            "timestamp": int(time.time()) - 400
        }
        mock_build.return_value = expired_data
        mock_encode.return_value = "encoded-expired-state"
        
        result = await encode_pr_state("123", "https://example.com", "csrf-token", pr_auth_router)
        
        assert result == "encoded-expired-state"
        mock_store.assert_called_once()


# Tests for decode_pr_state function
class TestDecodePrState:
    """Test decode_pr_state function with success and error cases."""

    @patch('app.auth.pr_router._decode_state_from_base64')
    @patch('app.auth.pr_router._validate_state_timestamp')
    @patch('app.auth.pr_router._validate_and_consume_csrf_token')
    async def test_decode_pr_state_success(self, mock_csrf, mock_timestamp, mock_decode,
                                         pr_auth_router, valid_pr_state_data):
        """Test successful PR state decoding."""
        mock_decode.return_value = valid_pr_state_data
        
        result = await decode_pr_state("encoded-state", pr_auth_router)
        
        assert result == valid_pr_state_data
        mock_decode.assert_called_once_with("encoded-state")
        mock_timestamp.assert_called_once_with(valid_pr_state_data, pr_auth_router.state_ttl)

    @patch('app.auth.pr_router._decode_state_from_base64')
    async def test_decode_pr_state_invalid(self, mock_decode, pr_auth_router):
        """Test decode_pr_state with invalid state data."""
        mock_decode.side_effect = NetraSecurityException("Invalid state")
        
        with pytest.raises(NetraSecurityException, match="Invalid OAuth state"):
            await decode_pr_state("invalid-state", pr_auth_router)