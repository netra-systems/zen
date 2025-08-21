"""JWT token generation and validation tests.

Split from test_token_manager.py to meet 450-line architecture limit.
Tests for JWT token creation, validation, and claims extraction.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from freezegun import freeze_time
from jose import jwt, JWTError

from netra_backend.app.auth_integration.auth import JWTTokenManager, TokenClaims
from netra_backend.app.core.exceptions_auth import AuthenticationError
from netra_backend.app.core.exceptions_base import ValidationError

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



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


@pytest.fixture
def valid_jwt_token(jwt_manager, sample_token_claims):
    """Generate a valid JWT token for testing."""
    secret = jwt_manager._get_secret_key()
    return jwt.encode(sample_token_claims, secret, algorithm="HS256")


# Helper functions for 25-line compliance
def create_malformed_token():
    """Create malformed JWT token for testing."""
    return "invalid.jwt.token.format"


def assert_token_claims_match(claims, expected_user_id, expected_email):
    """Assert token claims match expected values."""
    assert claims.user_id == expected_user_id
    assert claims.email == expected_email
    assert hasattr(claims, 'environment')
    assert hasattr(claims, 'jti')


# Test class for JWT Generation and Validation
class TestJWTTokenGeneration:
    """Test cases for JWT token generation and validation."""

    # Test JWT generation
    @freeze_time("2023-01-01 12:00:00")
    @patch('uuid.uuid4')
    async def test_generate_jwt_success(self, mock_uuid, jwt_manager, sample_user_data):
        """Test successful JWT token generation."""
        mock_uuid.return_value = Mock(return_value="mock_jti")
        mock_uuid.return_value.__str__ = Mock(return_value="mock_jti")
        
        token = await jwt_manager.generate_jwt(sample_user_data, "development")
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts

    @freeze_time("2023-01-01 12:00:00")
    @patch('uuid.uuid4')
    async def test_generate_jwt_with_pr_number(self, mock_uuid, jwt_manager, sample_user_data):
        """Test JWT generation with PR number included."""
        mock_uuid.return_value = Mock(return_value="mock_jti")
        mock_uuid.return_value.__str__ = Mock(return_value="mock_jti")
        
        token = await jwt_manager.generate_jwt(sample_user_data, "development", "PR-123")
        claims = jwt.decode(token, jwt_manager._get_secret_key(), algorithms=["HS256"])
        assert claims["pr_number"] == "PR-123"

    @freeze_time("2023-01-01 12:00:00")
    @patch('uuid.uuid4')
    async def test_generate_jwt_no_pr_number(self, mock_uuid, jwt_manager, sample_user_data):
        """Test JWT generation without PR number."""
        mock_uuid.return_value = Mock(return_value="mock_jti")
        mock_uuid.return_value.__str__ = Mock(return_value="mock_jti")
        
        token = await jwt_manager.generate_jwt(sample_user_data, "production")
        claims = jwt.decode(token, jwt_manager._get_secret_key(), algorithms=["HS256"])
        assert claims["pr_number"] is None

    # Test JWT validation
    async def test_validate_jwt_success(self, jwt_manager, valid_jwt_token):
        """Test successful JWT token validation."""
        claims = await jwt_manager.validate_jwt(valid_jwt_token)
        assert_token_claims_match(claims, "user_123", "test@example.com")

    async def test_validate_jwt_expired(self, jwt_manager):
        """Test validation fails for expired token."""
        with patch('jose.jwt.decode') as mock_decode:
            mock_decode.side_effect = JWTError("Token has expired")
            
            with pytest.raises(AuthenticationError, match="Invalid JWT token"):
                await jwt_manager.validate_jwt("expired_token")

    async def test_validate_jwt_invalid_signature(self, jwt_manager, sample_token_claims):
        """Test validation fails for invalid signature."""
        invalid_token = jwt.encode(sample_token_claims, "wrong_secret", algorithm="HS256")
        
        with pytest.raises(AuthenticationError, match="Invalid JWT token"):
            await jwt_manager.validate_jwt(invalid_token)

    async def test_validate_jwt_revoked_token(self, jwt_manager, valid_jwt_token):
        """Test validation fails for revoked token."""
        jwt_manager.redis_manager.get = AsyncMock(return_value="revoked")
        
        with pytest.raises(AuthenticationError, match="Token has been revoked"):
            await jwt_manager.validate_jwt(valid_jwt_token)

    # Test JWT claims extraction
    async def test_get_jwt_claims_success(self, jwt_manager, valid_jwt_token):
        """Test successful JWT claims extraction."""
        claims = await jwt_manager.get_jwt_claims(valid_jwt_token)
        assert_token_claims_match(claims, "user_123", "test@example.com")

    async def test_get_jwt_claims_malformed(self, jwt_manager):
        """Test claims extraction fails for malformed token."""
        malformed_token = create_malformed_token()
        
        with pytest.raises(ValidationError, match="Invalid token format"):
            await jwt_manager.get_jwt_claims(malformed_token)

    # Test token expiry time
    @freeze_time("2023-01-01 12:00:00")
    async def test_token_expiry_time(self, jwt_manager, sample_user_data):
        """Test token contains correct expiry time."""
        from datetime import timezone
        with patch('uuid.uuid4', return_value=Mock(__str__=Mock(return_value="test_jti"))):
            token = await jwt_manager.generate_jwt(sample_user_data, "test")
            claims = await jwt_manager.get_jwt_claims(token)
            now = datetime.now(timezone.utc)
            expected_exp = int((now + timedelta(hours=1)).timestamp())
            assert claims.exp == expected_exp

    # Test token claims structure
    async def test_token_claims_structure(self, jwt_manager, valid_jwt_token):
        """Test token claims have all required fields."""
        claims = await jwt_manager.get_jwt_claims(valid_jwt_token)
        required_fields = ["user_id", "email", "environment", "iat", "exp", "jti"]
        for field in required_fields:
            assert hasattr(claims, field)
            assert getattr(claims, field) is not None

    # Additional security tests
    async def test_validate_jwt_empty_token(self, jwt_manager):
        """Test validation fails for empty token."""
        with pytest.raises(AuthenticationError, match="Invalid JWT token"):
            await jwt_manager.validate_jwt("")

    async def test_validate_jwt_none_token(self, jwt_manager):
        """Test validation fails for None token."""
        with pytest.raises(Exception):
            await jwt_manager.validate_jwt(None)

    async def test_token_signature_verification(self, jwt_manager, sample_token_claims):
        """Test that tokens with wrong signature are rejected."""
        # Create token with wrong secret
        wrong_secret_token = jwt.encode(sample_token_claims, "wrong_secret", algorithm="HS256")
        
        with pytest.raises(AuthenticationError, match="Invalid JWT token"):
            await jwt_manager.validate_jwt(wrong_secret_token)