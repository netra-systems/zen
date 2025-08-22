"""JWT token operations tests - refresh, revocation, and convenience functions.

Split from test_token_manager.py to meet 450-line architecture limit.
Tests for token lifecycle operations and module-level convenience functions.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
from netra_backend.app.auth_integration.auth import JWTTokenManager, TokenClaims
from netra_backend.app.core.exceptions_auth import AuthenticationError

# Add project root to path


# Test fixtures
@pytest.fixture
def mock_config():
    """Mock configuration with JWT secret."""
    config = Mock()
    config.jwt_secret_key = "test_secret_key_12345"
    return config


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager with enabled state."""
    redis = AsyncMock()
    redis.enabled = True
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def jwt_manager(mock_config, mock_redis_manager):
    """JWT token manager instance with mocked dependencies."""
    manager = JWTTokenManager()
    manager.config = mock_config
    manager.redis_manager = mock_redis_manager
    return manager


@pytest.fixture
def sample_user_data():
    """Sample user data for token generation."""
    return {
        "user_id": "user_123",
        "email": "test@example.com"
    }


@pytest.fixture
def sample_token_claims():
    """Sample token claims structure with future expiration."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    future_time = now + timedelta(hours=1)
    return {
        "user_id": "user_123",
        "email": "test@example.com",
        "environment": "development",
        "pr_number": "PR-456",
        "iat": int(now.timestamp()),
        "exp": int(future_time.timestamp()),
        "jti": "token_id_789"
    }


# Test class for JWT Token Operations
class TestJWTTokenOperations:
    """Test cases for JWT token refresh and revocation operations."""

    # Test JWT refresh
    async def test_refresh_jwt_success(self, jwt_manager):
        """Test successful JWT token refresh."""
        with patch.object(jwt_manager, 'generate_jwt', return_value="new_token") as mock_gen, \
             patch.object(jwt_manager, 'validate_jwt') as mock_validate, \
             patch.object(jwt_manager, 'get_jwt_claims') as mock_get_claims:
            
            expected_claims = TokenClaims(
                user_id="user_123", email="test@example.com", environment="dev",
                iat=123, exp=456, jti="test_jti"
            )
            mock_validate.return_value = expected_claims
            mock_get_claims.return_value = expected_claims
            
            new_token = await jwt_manager.refresh_jwt("old_token")
            assert new_token == "new_token"

    async def test_refresh_jwt_expired(self, jwt_manager):
        """Test refresh fails for expired token."""
        with patch.object(jwt_manager, 'validate_jwt') as mock_validate:
            mock_validate.side_effect = AuthenticationError("Token expired")
            
            with pytest.raises(AuthenticationError):
                await jwt_manager.refresh_jwt("expired_token")

    async def test_refresh_jwt_calls_revoke(self, jwt_manager):
        """Test refresh properly revokes old token."""
        with patch.object(jwt_manager, 'validate_jwt') as mock_validate, \
             patch.object(jwt_manager, 'revoke_jwt') as mock_revoke, \
             patch.object(jwt_manager, 'generate_jwt', return_value="new_token"):
            
            mock_validate.return_value = TokenClaims(
                user_id="test", email="test@test.com", environment="test",
                iat=123, exp=456, jti="test_jti"
            )
            await jwt_manager.refresh_jwt("old_token")
            mock_revoke.assert_called_once_with("old_token")

    # Test JWT revocation
    async def test_revoke_jwt_success(self, jwt_manager, sample_token_claims):
        """Test successful JWT token revocation."""
        with patch.object(jwt_manager, 'get_jwt_claims') as mock_claims:
            mock_claims.return_value = TokenClaims(**sample_token_claims)
            
            await jwt_manager.revoke_jwt("test_token")
            jwt_manager.redis_manager.set.assert_called_once()
            call_args = jwt_manager.redis_manager.set.call_args
            assert "revoked_token:" in call_args[0][0]

    async def test_revoke_jwt_redis_disabled(self, jwt_manager):
        """Test revocation when Redis is disabled."""
        jwt_manager.redis_manager.enabled = False
        
        with patch.object(jwt_manager, 'get_jwt_claims') as mock_claims:
            mock_claims.return_value = Mock(jti="test_jti")
            await jwt_manager.revoke_jwt("test_token")
            jwt_manager.redis_manager.set.assert_not_called()

    async def test_revoke_jwt_exception_handling(self, jwt_manager):
        """Test revocation handles exceptions gracefully."""
        with patch.object(jwt_manager, 'get_jwt_claims') as mock_claims:
            mock_claims.side_effect = Exception("Token error")
            
            # Should not raise exception
            await jwt_manager.revoke_jwt("invalid_token")

    # Test token revocation checking
    async def test_is_token_revoked_true(self, jwt_manager, sample_token_claims):
        """Test token revocation check returns True for revoked token."""
        jwt_manager.redis_manager.get = AsyncMock(return_value="revoked")
        
        with patch.object(jwt_manager, 'get_jwt_claims') as mock_claims:
            mock_claims.return_value = TokenClaims(**sample_token_claims)
            result = await jwt_manager.is_token_revoked("test_token")
            assert result is True

    async def test_is_token_revoked_false(self, jwt_manager, sample_token_claims):
        """Test token revocation check returns False for valid token."""
        jwt_manager.redis_manager.get = AsyncMock(return_value=None)
        
        with patch.object(jwt_manager, 'get_jwt_claims') as mock_claims:
            mock_claims.return_value = TokenClaims(**sample_token_claims)
            result = await jwt_manager.is_token_revoked("test_token")
            assert result is False

    async def test_is_token_revoked_redis_disabled(self, jwt_manager):
        """Test revocation check when Redis is disabled."""
        jwt_manager.redis_manager.enabled = False
        
        result = await jwt_manager.is_token_revoked("test_token")
        assert result is False

    async def test_is_token_revoked_exception_handling(self, jwt_manager):
        """Test revocation check handles exceptions gracefully."""
        with patch.object(jwt_manager, 'get_jwt_claims') as mock_claims:
            mock_claims.side_effect = Exception("Token error")
            
            result = await jwt_manager.is_token_revoked("invalid_token")
            assert result is False


# Test convenience functions
class TestConvenienceFunctions:
    """Test cases for module-level convenience functions."""

    @patch('app.auth.token_manager.token_manager')
    async def test_generate_jwt_convenience(self, mock_manager, sample_user_data):
        """Test convenience function for JWT generation."""
        mock_manager.generate_jwt = AsyncMock(return_value="test_token")
        
        # Deprecated test - auth logic moved to auth service
        pytest.skip("generate_jwt moved to auth service")
        return
        result = await generate_jwt(sample_user_data, "test")
        assert result == "test_token"

    @patch('app.auth.token_manager.token_manager')
    async def test_validate_jwt_convenience(self, mock_manager):
        """Test convenience function for JWT validation."""
        expected_claims = TokenClaims(
            user_id="test", email="test@test.com", environment="test",
            iat=123, exp=456, jti="test_jti"
        )
        mock_manager.validate_jwt = AsyncMock(return_value=expected_claims)
        
        # Deprecated test - auth logic moved to auth service
        pytest.skip("validate_jwt moved to auth service")
        return
        result = await validate_jwt("test_token")
        assert result == expected_claims

    @patch('app.auth.token_manager.token_manager')
    async def test_refresh_jwt_convenience(self, mock_manager):
        """Test convenience function for JWT refresh."""
        mock_manager.refresh_jwt = AsyncMock(return_value="new_token")
        
        # Deprecated test - auth logic moved to auth service
        pytest.skip("refresh_jwt moved to auth service")
        return
        result = await refresh_jwt("old_token")
        assert result == "new_token"

    @patch('app.auth.token_manager.token_manager')  
    async def test_revoke_jwt_convenience(self, mock_manager):
        """Test convenience function for JWT revocation."""
        mock_manager.revoke_jwt = AsyncMock()
        
        # Deprecated test - auth logic moved to auth service
        pytest.skip("revoke_jwt moved to auth service")
        return
        await revoke_jwt("test_token")
        mock_manager.revoke_jwt.assert_called_once_with("test_token")

    @patch('app.auth.token_manager.token_manager')
    async def test_get_jwt_claims_convenience(self, mock_manager):
        """Test convenience function for JWT claims extraction."""
        expected_claims = TokenClaims(
            user_id="test", email="test@test.com", environment="test", 
            iat=123, exp=456, jti="test_jti"
        )
        mock_manager.get_jwt_claims = AsyncMock(return_value=expected_claims)
        
        # Deprecated test - auth logic moved to auth service
        pytest.skip("get_jwt_claims moved to auth service")
        return
        result = await get_jwt_claims("test_token")
        assert result == expected_claims

    @patch('app.auth.token_manager.token_manager')
    async def test_is_token_revoked_convenience(self, mock_manager):
        """Test convenience function for token revocation check."""
        mock_manager.is_token_revoked = AsyncMock(return_value=True)
        
        # Deprecated test - auth logic moved to auth service
        pytest.skip("is_token_revoked moved to auth service")
        return
        result = await is_token_revoked("test_token")
        assert result is True


# Test private helper methods
class TestPrivateHelperMethods:
    """Test cases for private helper methods."""

    def test_decode_token_payload_success(self, jwt_manager, sample_token_claims):
        """Test successful token payload decoding without validation."""
        from jose import jwt
        secret = jwt_manager._get_secret_key()
        token = jwt.encode(sample_token_claims, secret, algorithm="HS256")
        
        payload = jwt_manager._decode_token_payload(token)
        assert payload["user_id"] == "user_123"
        assert payload["email"] == "test@example.com"

    def test_decode_token_payload_malformed(self, jwt_manager):
        """Test token payload decoding with malformed token."""
        with pytest.raises(Exception):
            jwt_manager._decode_token_payload("invalid.token.format")

    async def test_check_revocation_in_redis_true(self, jwt_manager):
        """Test Redis revocation check returns True for revoked token."""
        jwt_manager.redis_manager.get = AsyncMock(return_value="revoked")
        
        result = await jwt_manager._check_revocation_in_redis("test_jti")
        assert result is True

    async def test_check_revocation_in_redis_false(self, jwt_manager):
        """Test Redis revocation check returns False for valid token."""
        jwt_manager.redis_manager.get = AsyncMock(return_value=None)
        
        result = await jwt_manager._check_revocation_in_redis("test_jti")
        assert result is False