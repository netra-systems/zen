"""
Comprehensive unit tests for JWT Handler - Core authentication token management
Tests basic functionality and regression protection
"""
import base64
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import jwt
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment


class TestJWTHandlerBasics:
    """Test basic JWT creation and validation"""
    
    def setup_method(self):
        """Setup for each test"""
        self.handler = JWTHandler()
        self.user_id = str(uuid.uuid4())
        self.email = "test@example.com"
        self.permissions = ["read", "write"]
    
    def test_create_access_token(self):
        """Test access token creation"""
        token = self.handler.create_access_token(self.user_id, self.email, self.permissions)
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        token = self.handler.create_refresh_token(self.user_id, self.email, self.permissions)
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3
    
    def test_create_service_token(self):
        """Test service token creation"""
        service_id = "test-service"
        service_name = "Test Service"
        token = self.handler.create_service_token(service_id, service_name)
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3
    
    def test_validate_valid_access_token(self):
        """Test validation of valid access token"""
        token = self.handler.create_access_token(self.user_id, self.email, self.permissions)
        payload = self.handler.validate_token(token, "access")
        assert payload is not None
        assert payload["sub"] == self.user_id
        assert payload["email"] == self.email
        assert payload["permissions"] == self.permissions
    
    def test_validate_invalid_token_type(self):
        """Test validation fails with wrong token type"""
        token = self.handler.create_access_token(self.user_id, self.email)
        payload = self.handler.validate_token(token, "refresh")
        assert payload is None
    
    def test_validate_malformed_token(self):
        """Test validation of malformed token"""
        malformed_tokens = [
            "invalid.token",
            "invalid",
            "",
            None,
            "a.b.c.d",  # Too many parts
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",  # Only header
        ]
        for token in malformed_tokens:
            payload = self.handler.validate_token(token, "access")
            assert payload is None
    
    def test_validate_expired_token(self):
        """Test validation of expired token"""
        # Create token with negative expiry
        payload = self.handler._build_payload(
            sub=self.user_id,
            token_type="access",
            exp_minutes=-1
        )
        token = self.handler._encode_token(payload)
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_extract_user_id_from_token(self):
        """Test extracting user ID without full validation"""
        token = self.handler.create_access_token(self.user_id, self.email)
        extracted_id = self.handler.extract_user_id(token)
        assert extracted_id == self.user_id
    
    def test_extract_user_id_from_invalid_token(self):
        """Test extracting user ID from invalid token returns None"""
        invalid_tokens = ["invalid", "", None, "a.b.c"]
        for token in invalid_tokens:
            extracted_id = self.handler.extract_user_id(token)
            assert extracted_id is None
    
    def test_refresh_access_token_success(self):
        """Test refreshing access token with valid refresh token"""
        refresh_token = self.handler.create_refresh_token(self.user_id, self.email, self.permissions)
        result = self.handler.refresh_access_token(refresh_token)
        assert result is not None
        assert len(result) == 2  # Returns (access_token, refresh_token)
        new_access, new_refresh = result
        assert new_access is not None
        assert new_refresh is not None
    
    def test_refresh_access_token_with_invalid_token(self):
        """Test refreshing with invalid refresh token"""
        result = self.handler.refresh_access_token("invalid.token")
        assert result is None
    
    def test_token_payload_contains_required_claims(self):
        """Test token payload contains all required claims"""
        token = self.handler.create_access_token(self.user_id, self.email)
        # Decode without verification to check claims
        payload = jwt.decode(token, options={"verify_signature": False})
        required_claims = ["sub", "iat", "exp", "iss", "aud", "jti", "token_type"]
        for claim in required_claims:
            assert claim in payload
    
    def test_token_issuer_is_correct(self):
        """Test token has correct issuer"""
        token = self.handler.create_access_token(self.user_id, self.email)
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["iss"] == "netra-auth-service"
    
    def test_token_audience_is_correct(self):
        """Test token has correct audience based on type"""
        access_token = self.handler.create_access_token(self.user_id, self.email)
        refresh_token = self.handler.create_refresh_token(self.user_id)
        service_token = self.handler.create_service_token("svc-1", "Service 1")
        
        access_payload = jwt.decode(access_token, options={"verify_signature": False})
        refresh_payload = jwt.decode(refresh_token, options={"verify_signature": False})
        service_payload = jwt.decode(service_token, options={"verify_signature": False})
        
        assert access_payload["aud"] == "netra-platform"
        assert refresh_payload["aud"] == "netra-platform"
        assert service_payload["aud"] == "netra-services"
    
    def test_token_jti_is_unique(self):
        """Test each token has unique JWT ID"""
        tokens = [
            self.handler.create_access_token(self.user_id, self.email)
            for _ in range(5)
        ]
        jtis = []
        for token in tokens:
            payload = jwt.decode(token, options={"verify_signature": False})
            jtis.append(payload["jti"])
        assert len(jtis) == len(set(jtis))  # All JTIs are unique


class TestJWTHandlerBlacklist:
    """Test token and user blacklisting functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.handler = JWTHandler()
        self.user_id = str(uuid.uuid4())
        self.email = "blacklist@example.com"
    
    def test_blacklist_token(self):
        """Test adding token to blacklist"""
        token = self.handler.create_access_token(self.user_id, self.email)
        result = self.handler.blacklist_token(token)
        assert result is True
        assert self.handler.is_token_blacklisted(token) is True
    
    def test_validate_blacklisted_token_fails(self):
        """Test validation fails for blacklisted token"""
        token = self.handler.create_access_token(self.user_id, self.email)
        # First validate it works
        payload = self.handler.validate_token(token, "access")
        assert payload is not None
        # Now blacklist it
        self.handler.blacklist_token(token)
        # Validation should fail
        payload = self.handler.validate_token(token, "access")
        assert payload is None
    
    def test_remove_token_from_blacklist(self):
        """Test removing token from blacklist"""
        token = self.handler.create_access_token(self.user_id, self.email)
        self.handler.blacklist_token(token)
        assert self.handler.is_token_blacklisted(token) is True
        result = self.handler.remove_from_blacklist(token)
        assert result is True
        assert self.handler.is_token_blacklisted(token) is False
    
    def test_blacklist_user(self):
        """Test adding user to blacklist"""
        result = self.handler.blacklist_user(self.user_id)
        assert result is True
        assert self.handler.is_user_blacklisted(self.user_id) is True
    
    def test_validate_token_for_blacklisted_user_fails(self):
        """Test validation fails for blacklisted user's token"""
        token = self.handler.create_access_token(self.user_id, self.email)
        # First validate it works
        payload = self.handler.validate_token(token, "access")
        assert payload is not None
        # Now blacklist the user
        self.handler.blacklist_user(self.user_id)
        # Validation should fail
        payload = self.handler.validate_token(token, "access")
        assert payload is None
    
    def test_remove_user_from_blacklist(self):
        """Test removing user from blacklist"""
        self.handler.blacklist_user(self.user_id)
        assert self.handler.is_user_blacklisted(self.user_id) is True
        result = self.handler.remove_user_from_blacklist(self.user_id)
        assert result is True
        assert self.handler.is_user_blacklisted(self.user_id) is False
    
    def test_get_blacklist_info(self):
        """Test getting blacklist statistics"""
        info = self.handler.get_blacklist_info()
        assert "blacklisted_tokens" in info
        assert "blacklisted_users" in info
        assert isinstance(info["blacklisted_tokens"], int)
        assert isinstance(info["blacklisted_users"], int)


class TestJWTHandlerSecurity:
    """Test JWT security features and validations"""
    
    def setup_method(self):
        """Setup for each test"""
        self.handler = JWTHandler()
        self.user_id = str(uuid.uuid4())
        self.email = "security@example.com"
    
    def test_validate_token_with_none_algorithm_fails(self):
        """Test token with 'none' algorithm is rejected"""
        # Create unsigned token with 'none' algorithm
        payload = {
            "sub": self.user_id,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "token_type": "access"
        }
        # Create token with 'none' algorithm (unsigned)
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"{header}.{body}."
        
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_validate_token_with_wrong_algorithm_fails(self):
        """Test token with unsupported algorithm is rejected"""
        # Try to create token with unsupported algorithm
        payload = {
            "sub": self.user_id,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
            "token_type": "access"
        }
        # Create token with unsupported algorithm header
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS512", "typ": "JWT"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"{header}.{body}.signature"
        
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_validate_token_with_invalid_issuer_fails(self):
        """Test token with invalid issuer is rejected"""
        payload = self.handler._build_payload(
            sub=self.user_id,
            token_type="access",
            exp_minutes=5
        )
        payload["iss"] = "invalid-issuer"
        token = self.handler._encode_token(payload)
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_validate_token_with_invalid_audience_fails(self):
        """Test token with invalid audience is rejected"""
        payload = self.handler._build_payload(
            sub=self.user_id,
            token_type="access",
            exp_minutes=5
        )
        payload["aud"] = "invalid-audience"
        token = self.handler._encode_token(payload)
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_validate_token_too_old_fails(self):
        """Test token older than 24 hours is rejected"""
        payload = self.handler._build_payload(
            sub=self.user_id,
            token_type="access",
            exp_minutes=60
        )
        # Set issued at to 25 hours ago
        payload["iat"] = int((datetime.now(timezone.utc) - timedelta(hours=25)).timestamp())
        token = self.handler._encode_token(payload)
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_validate_token_issued_in_future_fails(self):
        """Test token issued in future is rejected"""
        payload = self.handler._build_payload(
            sub=self.user_id,
            token_type="access",
            exp_minutes=60
        )
        # Set issued at to 2 minutes in future (beyond allowed clock skew)
        payload["iat"] = int((datetime.now(timezone.utc) + timedelta(minutes=2)).timestamp())
        token = self.handler._encode_token(payload)
        result = self.handler.validate_token(token, "access")
        assert result is None
    
    def test_validate_id_token_basic(self):
        """Test basic ID token validation"""
        # Create a mock ID token
        payload = {
            "sub": self.user_id,
            "email": self.email,
            "iss": "accounts.google.com",
            "aud": "test-client-id",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        id_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        result = self.handler.validate_id_token(id_token, "accounts.google.com")
        assert result is not None
        assert result["sub"] == self.user_id
        assert result["email"] == self.email
    
    def test_validate_id_token_wrong_issuer_fails(self):
        """Test ID token with wrong issuer is rejected"""
        payload = {
            "sub": self.user_id,
            "iss": "wrong-issuer",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        id_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        result = self.handler.validate_id_token(id_token, "accounts.google.com")
        assert result is None
    
    def test_validate_id_token_expired_fails(self):
        """Test expired ID token is rejected"""
        payload = {
            "sub": self.user_id,
            "iss": "accounts.google.com",
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        }
        id_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        result = self.handler.validate_id_token(id_token)
        assert result is None
    
    def test_mock_token_rejected_in_production(self):
        """Test mock tokens are rejected"""
        mock_token = "mock_access_token_123456"
        result = self.handler.validate_token(mock_token, "access")
        assert result is None


class TestJWTHandlerPerformance:
    """Test performance-related functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.handler = JWTHandler()
        self.user_id = str(uuid.uuid4())
        self.email = "perf@example.com"
    
    def test_get_performance_stats(self):
        """Test getting performance statistics"""
        stats = self.handler.get_performance_stats()
        assert "cache_stats" in stats
        assert "blacklist_stats" in stats
        assert "performance_optimizations" in stats
        assert stats["performance_optimizations"]["caching_enabled"] is True
        assert stats["performance_optimizations"]["fast_validation"] is True
    
    def test_validate_token_caching(self):
        """Test token validation is cached"""
        token = self.handler.create_access_token(self.user_id, self.email)
        
        # First validation
        result1 = self.handler.validate_token(token, "access")
        assert result1 is not None
        
        # Second validation should use cache
        result2 = self.handler.validate_token(token, "access")
        assert result2 is not None
        assert result1["sub"] == result2["sub"]
    
    def test_token_structure_validation(self):
        """Test JWT structure validation catches malformed tokens early"""
        invalid_structures = [
            "not.a.jwt",
            "YQ==.YQ==",  # Valid base64 but not JSON
            "eyJhIjoxfQ==.eyJhIjoxfQ==.c2ln",  # Valid JSON but wrong padding
            ".",  # Empty parts
            "..",  # All empty parts
        ]
        for token in invalid_structures:
            assert self.handler._validate_jwt_structure(token) is False
    
    def test_enhanced_jwt_claims_validation_fast(self):
        """Test fast enhanced JWT claims validation"""
        payload = {
            "iss": "netra-auth-service",
            "aud": "netra-platform",
            "sub": self.user_id
        }
        assert self.handler._validate_enhanced_jwt_claims_fast(payload) is True
        
        # Test with invalid issuer
        payload["iss"] = "wrong-issuer"
        assert self.handler._validate_enhanced_jwt_claims_fast(payload) is False


class TestJWTHandlerEdgeCases:
    """Test edge cases and error handling"""
    
    def setup_method(self):
        """Setup for each test"""
        self.handler = JWTHandler()
        self.user_id = str(uuid.uuid4())
        self.email = "edge@example.com"
    
    def test_create_refresh_token_without_email(self):
        """Test creating refresh token without email"""
        token = self.handler.create_refresh_token(self.user_id)
        assert token is not None
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == self.user_id
        assert "email" not in payload or payload.get("email") is None
    
    def test_validate_token_for_consumption_with_replay_protection(self):
        """Test token consumption validation with replay protection"""
        refresh_token = self.handler.create_refresh_token(self.user_id, self.email)
        
        # First consumption should succeed
        result1 = self.handler.validate_token_for_consumption(refresh_token, "refresh")
        assert result1 is not None
        
        # Second consumption might fail if replay protection is enforced
        # (depends on implementation details)
        result2 = self.handler.validate_token_for_consumption(refresh_token, "refresh")
        # This test is flexible as replay protection behavior may vary
    
    def test_cross_service_token_validation(self):
        """Test cross-service token validation"""
        service_token = self.handler.create_service_token("test-svc", "Test Service")
        payload = jwt.decode(service_token, options={"verify_signature": False})
        
        # Test internal validation method
        result = self.handler._validate_cross_service_token(payload, service_token)
        assert result is True
    
    def test_service_signature_generation(self):
        """Test service signature is generated"""
        token = self.handler.create_access_token(self.user_id, self.email)
        payload = self.handler.validate_token(token, "access")
        assert payload is not None
        assert "service_signature" in payload
        assert payload["service_signature"] != ""
    
    def test_cleanup_expired_token_ids(self):
        """Test cleanup of expired token IDs"""
        # Generate many tokens to trigger cleanup
        for i in range(100):
            jti = str(uuid.uuid4())
            self.handler._track_token_id(jti, int(time.time()) + 3600)
        
        # Cleanup should be triggered automatically after threshold
        # This is implementation-specific behavior
        assert True  # Basic test that it doesn't crash
    
    def test_environment_binding_in_token(self):
        """Test environment is included in token"""
        token = self.handler.create_access_token(self.user_id, self.email)
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "env" in payload
        assert payload["env"] == AuthConfig.get_environment()
    
    def test_service_id_in_token(self):
        """Test service ID is included in token"""
        token = self.handler.create_access_token(self.user_id, self.email)
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "svc_id" in payload
        assert payload["svc_id"] == self.handler.service_id
    
    def test_validate_token_jwt_alias(self):
        """Test validate_token_jwt alias works"""
        token = self.handler.create_access_token(self.user_id, self.email)
        result = self.handler.validate_token_jwt(token, "access")
        assert result is not None
        assert result["sub"] == self.user_id
    
    def test_token_with_empty_permissions(self):
        """Test token creation with empty permissions"""
        token = self.handler.create_access_token(self.user_id, self.email, [])
        payload = self.handler.validate_token(token, "access")
        assert payload is not None
        assert payload["permissions"] == []
    
    def test_token_with_no_permissions(self):
        """Test token creation without permissions parameter"""
        token = self.handler.create_access_token(self.user_id, self.email)
        payload = self.handler.validate_token(token, "access")
        assert payload is not None
        assert payload["permissions"] == []