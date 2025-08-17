"""Comprehensive tests for JWT token generation, validation, and management.

Tests AuthTokenService JWT operations, token expiration, security validation,
user info handling, and error scenarios.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Ensure secure and reliable JWT token management
3. Value Impact: Prevents unauthorized access and ensures token security
4. Revenue Impact: Critical for platform security and customer trust
"""

import os
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.auth.auth_token_service import AuthTokenService, UserInfo


@pytest.fixture
def auth_token_service():
    """Create AuthTokenService instance for testing."""
    return AuthTokenService()


@pytest.fixture
def sample_user_info():
    """Create sample user info for testing."""
    return UserInfo(
        id="123456789",
        email="test@example.com", 
        name="Test User",
        picture="https://example.com/photo.jpg"
    )


@pytest.fixture
def sample_user_info_minimal():
    """Create minimal user info for testing."""
    return UserInfo(
        id="minimal_123",
        email="minimal@test.com",
        name="Minimal User"
    )


class TestUserInfoClass:
    """Test UserInfo data structure and methods."""
    
    def test_user_info_initialization_complete(self):
        """Test UserInfo initialization with all fields."""
        user = UserInfo("123", "test@example.com", "Test User", "https://photo.url")
        assert user.id == "123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.picture == "https://photo.url"


    def test_user_info_initialization_without_picture(self):
        """Test UserInfo initialization without picture field."""
        user = UserInfo("456", "user@test.com", "User Name")
        assert user.id == "456"
        assert user.email == "user@test.com"
        assert user.name == "User Name"
        assert user.picture is None


    def test_user_info_get_method_existing_attribute(self):
        """Test UserInfo get method returns existing attributes."""
        user = UserInfo("789", "get@test.com", "Get User", "https://pic.url")
        assert user.get("id") == "789"
        assert user.get("email") == "get@test.com"
        assert user.get("name") == "Get User"
        assert user.get("picture") == "https://pic.url"


    def test_user_info_get_method_nonexistent_attribute(self):
        """Test UserInfo get method returns None for nonexistent attributes."""
        user = UserInfo("999", "none@test.com", "None User")
        assert user.get("nonexistent") is None
        assert user.get("fake_field") is None


class TestJWTSecretManagement:
    """Test JWT secret loading and validation."""
    
    def test_jwt_secret_from_environment(self, auth_token_service):
        """Test JWT secret loaded from environment variable."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret_key_with_32_characters"}):
            auth_token_service._jwt_secret = None  # Reset cached secret
            secret = auth_token_service._get_secure_jwt_secret()
            assert secret == "test_secret_key_with_32_characters"


    def test_jwt_secret_validation_minimum_length(self, auth_token_service):
        """Test JWT secret validation requires minimum length."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "short"}):
            auth_token_service._jwt_secret = None
            with pytest.raises(HTTPException) as exc_info:
                auth_token_service._get_secure_jwt_secret()
            assert exc_info.value.status_code == 500
            assert "at least 32 characters" in exc_info.value.detail


    def test_jwt_secret_test_environment_default(self, auth_token_service):
        """Test JWT secret defaults in test environment."""
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(auth_token_service, '_is_test_environment', return_value=True):
            auth_token_service._jwt_secret = None
            secret = auth_token_service._get_secure_jwt_secret()
            assert len(secret) >= 32
            assert "test" in secret.lower()


    def test_jwt_secret_missing_non_test_environment(self, auth_token_service):
        """Test JWT secret missing in non-test environment raises error."""
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(auth_token_service, '_is_test_environment', return_value=False):
            auth_token_service._jwt_secret = None
            with pytest.raises(HTTPException) as exc_info:
                auth_token_service._get_secure_jwt_secret()
            assert exc_info.value.status_code == 500


    def test_is_test_environment_detection(self, auth_token_service):
        """Test test environment detection logic."""
        test_envs = ["pytest", "test", "testing"]
        for env in test_envs:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                assert auth_token_service._is_test_environment() is True


    def test_jwt_secret_caching(self, auth_token_service):
        """Test JWT secret is cached after first load."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "cached_secret_key_with_32_characters"}):
            auth_token_service._jwt_secret = None
            secret1 = auth_token_service._get_secure_jwt_secret()
            secret2 = auth_token_service._get_secure_jwt_secret()
            assert secret1 == secret2
            assert auth_token_service._jwt_secret == secret1


class TestJWTGeneration:
    """Test JWT token generation with various user data."""
    
    def test_generate_jwt_complete_user_info(self, auth_token_service, sample_user_info):
        """Test JWT generation with complete user information."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_jwt_secret_key_with_32_characters"}):
            token = auth_token_service.generate_jwt(sample_user_info)
            assert isinstance(token, str)
            assert len(token) > 0
            # Should be valid JWT format (3 parts separated by dots)
            assert len(token.split('.')) == 3


    def test_generate_jwt_minimal_user_info(self, auth_token_service, sample_user_info_minimal):
        """Test JWT generation with minimal user information."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "minimal_jwt_secret_key_with_32_chars"}):
            token = auth_token_service.generate_jwt(sample_user_info_minimal)
            # Decode to verify structure
            decoded = jwt.decode(token, "minimal_jwt_secret_key_with_32_chars", algorithms=["HS256"])
            assert decoded["sub"] == "minimal_123"
            assert decoded["email"] == "minimal@test.com"


    def test_jwt_payload_structure(self, auth_token_service, sample_user_info):
        """Test JWT payload contains required claims."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "payload_test_secret_key_with_32_chars"}):
            token = auth_token_service.generate_jwt(sample_user_info)
            decoded = jwt.decode(token, "payload_test_secret_key_with_32_chars", algorithms=["HS256"])
            required_claims = ["sub", "email", "name", "iat", "exp", "iss", "aud"]
            for claim in required_claims:
                assert claim in decoded


    def test_jwt_issuer_and_audience(self, auth_token_service, sample_user_info):
        """Test JWT contains correct issuer and audience claims."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "issuer_test_secret_key_with_32_chars"}):
            token = auth_token_service.generate_jwt(sample_user_info)
            decoded = jwt.decode(token, "issuer_test_secret_key_with_32_chars", algorithms=["HS256"])
            assert decoded["iss"] == "netra-auth-service"
            assert decoded["aud"] == "netra-api"


    def test_jwt_expiration_timing(self, auth_token_service, sample_user_info):
        """Test JWT expiration is set correctly."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "expiry_test_secret_key_with_32_chars"}):
            before_time = datetime.now(timezone.utc)
            token = auth_token_service.generate_jwt(sample_user_info)
            after_time = datetime.now(timezone.utc)
            
            decoded = jwt.decode(token, "expiry_test_secret_key_with_32_chars", algorithms=["HS256"])
            expected_exp = int((before_time + timedelta(seconds=3600)).timestamp())
            # Allow 2 second variance for test timing
            assert abs(decoded["exp"] - expected_exp) <= 2


    def test_jwt_issued_at_claim(self, auth_token_service, sample_user_info):
        """Test JWT issued at (iat) claim is current time."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "iat_test_secret_key_with_32_characters"}):
            before_time = int(datetime.now(timezone.utc).timestamp())
            token = auth_token_service.generate_jwt(sample_user_info)
            after_time = int(datetime.now(timezone.utc).timestamp())
            
            decoded = jwt.decode(token, "iat_test_secret_key_with_32_characters", algorithms=["HS256"])
            assert before_time <= decoded["iat"] <= after_time


class TestJWTValidation:
    """Test JWT token validation and error handling."""
    
    def test_validate_jwt_valid_token(self, auth_token_service, sample_user_info):
        """Test validation of valid JWT token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "valid_test_secret_key_with_32_chars"}):
            token = auth_token_service.generate_jwt(sample_user_info)
            claims = auth_token_service.validate_jwt(token)
            assert claims is not None
            assert claims["sub"] == sample_user_info.id
            assert claims["email"] == sample_user_info.email


    def test_validate_jwt_expired_token(self, auth_token_service, sample_user_info):
        """Test validation of expired JWT token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "expired_test_secret_key_with_32_chars"}):
            auth_token_service.token_expiry = -1  # Immediate expiration
            token = auth_token_service.generate_jwt(sample_user_info)
            claims = auth_token_service.validate_jwt(token)
            assert claims is None


    def test_validate_jwt_invalid_signature(self, auth_token_service, sample_user_info):
        """Test validation of JWT with invalid signature."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "signature_test_secret_key_with_32"}):
            token = auth_token_service.generate_jwt(sample_user_info)
            # Change secret to invalidate signature
            auth_token_service._jwt_secret = "different_secret_key_with_32_chars"
            claims = auth_token_service.validate_jwt(token)
            assert claims is None


    def test_validate_jwt_malformed_token(self, auth_token_service):
        """Test validation of malformed JWT token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "malformed_test_secret_key_with_32"}):
            malformed_tokens = ["invalid.token", "not.a.jwt.token", "", "single_string"]
            for token in malformed_tokens:
                claims = auth_token_service.validate_jwt(token)
                assert claims is None


    def test_validate_jwt_none_token(self, auth_token_service):
        """Test validation of None token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "none_test_secret_key_with_32_chars"}):
            claims = auth_token_service.validate_jwt(None)
            assert claims is None


class TestJWTErrorHandling:
    """Test JWT error handling and logging."""
    
    def test_jwt_expired_error_handling(self, auth_token_service):
        """Test JWT expired error is handled gracefully."""
        with patch('app.auth.auth_token_service.logger') as mock_logger:
            auth_token_service._handle_jwt_expired()
            mock_logger.warning.assert_called_once_with("JWT token expired")


    def test_jwt_invalid_error_handling(self, auth_token_service):
        """Test JWT invalid error is handled gracefully."""
        with patch('app.auth.auth_token_service.logger') as mock_logger:
            test_error = jwt.InvalidTokenError("Test error")
            auth_token_service._handle_jwt_invalid(test_error)
            mock_logger.error.assert_called_once()


    def test_jwt_validation_error_flow(self, auth_token_service):
        """Test JWT validation error flow returns None."""
        with patch.object(auth_token_service, '_decode_jwt_token') as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError("Mock error")
            claims = auth_token_service.validate_jwt("invalid_token")
            assert claims is None


    def test_jwt_expired_validation_flow(self, auth_token_service):
        """Test JWT expired validation flow returns None."""
        with patch.object(auth_token_service, '_decode_jwt_token') as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
            claims = auth_token_service.validate_jwt("expired_token")
            assert claims is None


class TestJWTCustomConfiguration:
    """Test JWT token service custom configuration."""
    
    def test_custom_token_expiry(self, sample_user_info):
        """Test custom token expiry configuration."""
        service = AuthTokenService()
        service.token_expiry = 7200  # 2 hours
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "custom_expiry_secret_key_with_32"}):
            token = service.generate_jwt(sample_user_info)
            decoded = jwt.decode(token, "custom_expiry_secret_key_with_32", algorithms=["HS256"])
            
            # Verify expiry is approximately 2 hours from now
            expected_exp = int((datetime.now(timezone.utc) + timedelta(seconds=7200)).timestamp())
            assert abs(decoded["exp"] - expected_exp) <= 2


    def test_token_service_initialization(self):
        """Test AuthTokenService initialization sets defaults."""
        service = AuthTokenService()
        assert service._jwt_secret is None
        assert service.token_expiry == 3600  # 1 hour default


    def test_build_jwt_payload_method(self, auth_token_service, sample_user_info):
        """Test JWT payload building method."""
        now = datetime.now(timezone.utc)
        payload = auth_token_service._build_jwt_payload(sample_user_info, now)
        
        assert payload["sub"] == sample_user_info.id
        assert payload["email"] == sample_user_info.email
        assert payload["name"] == sample_user_info.name
        assert payload["iat"] == int(now.timestamp())
        assert payload["iss"] == "netra-auth-service"


class TestJWTSecurityFeatures:
    """Test JWT security features and validation."""
    
    def test_jwt_algorithm_restriction(self, auth_token_service, sample_user_info):
        """Test JWT uses only HS256 algorithm."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "algorithm_test_secret_key_with_32"}):
            token = auth_token_service.generate_jwt(sample_user_info)
            # Should fail with different algorithm
            with pytest.raises(jwt.InvalidAlgorithmError):
                jwt.decode(token, "algorithm_test_secret_key_with_32", algorithms=["HS512"])


    def test_jwt_secret_isolation_between_instances(self, sample_user_info):
        """Test JWT secret isolation between service instances."""
        service1 = AuthTokenService()
        service2 = AuthTokenService()
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "isolation_test_secret_key_with_32"}):
            # Each instance should load secret independently
            secret1 = service1._get_secure_jwt_secret()
            secret2 = service2._get_secure_jwt_secret()
            assert secret1 == secret2


    def test_jwt_token_uniqueness(self, auth_token_service, sample_user_info):
        """Test JWT tokens are unique for each generation."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "unique_test_secret_key_with_32_chars"}):
            token1 = auth_token_service.generate_jwt(sample_user_info)
            token2 = auth_token_service.generate_jwt(sample_user_info)
            # Should be different due to different iat timestamps
            assert token1 != token2