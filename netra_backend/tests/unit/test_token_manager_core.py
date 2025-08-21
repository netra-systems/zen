"""Core JWT token manager tests - secret key and revocation key functionality.

Split from test_token_manager.py to meet 450-line architecture limit.
Tests for basic JWT manager setup and utility functions.
"""

import pytest
from unittest.mock import Mock, patch

from netra_backend.app.auth_integration.auth import JWTTokenManager
from netra_backend.app.core.exceptions_auth import AuthenticationError


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
    from unittest.mock import AsyncMock
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


# Helper functions for 25-line compliance
def assert_revocation_key_format(key, expected_jti):
    """Assert revocation key follows expected format."""
    assert key == f"revoked_token:{expected_jti}"


# Test class for JWT Token Manager Core Functions
class TestJWTTokenManagerCore:
    """Test cases for core JWTTokenManager functionality."""

    # Test secret key retrieval
    def test_get_secret_key_from_config(self, jwt_manager):
        """Test successful secret key retrieval from config."""
        secret = jwt_manager._get_secret_key()
        assert secret == "test_secret_key_12345"

    def test_get_secret_key_no_config_raises_error(self, jwt_manager):
        """Test error when no secret key is configured."""
        jwt_manager.config.jwt_secret_key = None
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(AuthenticationError, match="JWT secret key not configured"):
                jwt_manager._get_secret_key()

    def test_get_secret_key_from_environment(self, jwt_manager):
        """Test secret key retrieval from environment variable."""
        jwt_manager.config.jwt_secret_key = None
        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'env_secret'}):
            secret = jwt_manager._get_secret_key()
            assert secret == 'env_secret'

    # Test revocation key creation
    def test_create_revocation_key_format(self, jwt_manager):
        """Test revocation key creation follows correct format."""
        test_jti = "test_token_id_123"
        key = jwt_manager._create_revocation_key(test_jti)
        assert_revocation_key_format(key, test_jti)

    def test_create_revocation_key_unique(self, jwt_manager):
        """Test revocation keys are unique for different JTIs."""
        key1 = jwt_manager._create_revocation_key("jti_1")
        key2 = jwt_manager._create_revocation_key("jti_2")
        assert key1 != key2
        assert "jti_1" in key1 and "jti_2" in key2

    def test_create_revocation_key_empty_jti(self, jwt_manager):
        """Test revocation key creation with empty JTI."""
        key = jwt_manager._create_revocation_key("")
        assert key == "revoked_token:"

    def test_create_revocation_key_special_chars(self, jwt_manager):
        """Test revocation key creation with special characters."""
        special_jti = "test-token_123.abc"
        key = jwt_manager._create_revocation_key(special_jti)
        assert_revocation_key_format(key, special_jti)

    # Test manager initialization
    def test_jwt_manager_initialization(self):
        """Test JWT manager initializes with correct defaults."""
        manager = JWTTokenManager()
        assert manager.algorithm == "HS256"
        assert manager.expiration_hours == 1
        assert hasattr(manager, 'config')
        assert hasattr(manager, 'redis_manager')

    def test_jwt_manager_algorithm_constant(self, jwt_manager):
        """Test JWT manager uses consistent algorithm."""
        assert jwt_manager.algorithm == "HS256"

    def test_jwt_manager_expiration_hours(self, jwt_manager):
        """Test JWT manager has correct expiration setting."""
        assert jwt_manager.expiration_hours == 1