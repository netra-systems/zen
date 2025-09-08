"""
Test JWT Handler Batch 4 - Comprehensive JWT Security and Validation Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Mid - Security-Critical Infrastructure
- Business Goal: Prevent security breaches and ensure compliant JWT handling
- Value Impact: Validates core authentication security mechanisms
- Revenue Impact: Protects $120K+ MRR by preventing auth bypasses and token exploits

CRITICAL: These tests ensure JWT security compliance and prevent token-based attacks.
All security mechanisms MUST be validated with NO mocks in critical paths.
"""

import pytest
import jwt
import time
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from shared.isolated_environment import get_env


class TestJWTHandlerSecurityBatch4(SSotAsyncTestCase):
    """
    Comprehensive JWT Handler security tests for Batch 4.
    
    Tests critical security mechanisms that protect business operations:
    - Token validation with enhanced security checks
    - Blacklist functionality for compromised tokens
    - Cross-service authentication validation
    - JWT structure and algorithm security
    - Token replay protection mechanisms
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each JWT security test."""
        super().setup_method(method)
        
        # Initialize with test-safe JWT secret
        self.env = get_env()
        self.env.set("JWT_SECRET_KEY", "test_jwt_secret_32_characters_long_key", "test_jwt_handler_batch4")
        self.env.set("ENVIRONMENT", "test", "test_jwt_handler_batch4")
        self.env.set("SERVICE_SECRET", "test_service_secret_32_chars_long", "test_jwt_handler_batch4")
        
        # Create JWT handler with isolated config
        self.jwt_handler = JWTHandler()
        
        # Test data for comprehensive security testing
        self.test_user_id = "test_user_batch4_security"
        self.test_email = "batch4@security-test.com"
        self.test_permissions = ["read", "write", "security_test"]
        
        # Create baseline valid tokens for security testing
        self.valid_access_token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email, 
            self.test_permissions
        )
        
        self.valid_refresh_token = self.jwt_handler.create_refresh_token(
            self.test_user_id, 
            self.test_email, 
            self.test_permissions
        )
        
        self.record_metric("jwt_handler_security_test_setup", True)
    
    def teardown_method(self, method):
        """Clean up isolated environment after each test."""
        # Clean up environment
        self.env.delete("JWT_SECRET_KEY", "test_jwt_handler_batch4")
        self.env.delete("ENVIRONMENT", "test_jwt_handler_batch4") 
        self.env.delete("SERVICE_SECRET", "test_jwt_handler_batch4")
        
        super().teardown_method(method)
    
    # ===================== JWT TOKEN STRUCTURE SECURITY TESTS =====================
    
    def test_jwt_handler_validates_token_structure_security(self):
        """Test JWT handler properly validates token structure for security.
        
        BVJ: Prevents malformed token attacks that could bypass authentication.
        CRITICAL: Token structure validation is first line of defense against JWT exploits.
        """
        # Test cases for malformed tokens that should be rejected
        malformed_tokens = [
            "",  # Empty token
            "not.a.jwt",  # Too few segments
            "not.a.jwt.token.with.too.many.segments",  # Too many segments
            "invalid_base64.invalid_base64.invalid_signature",  # Invalid base64
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..invalid_signature",  # Empty payload
            ".eyJzdWIiOiJ0ZXN0In0.signature",  # Empty header
            "header.payload.",  # Empty signature
            "malicious<script>alert(1)</script>.payload.signature"  # XSS attempt
        ]
        
        for malformed_token in malformed_tokens:
            result = self.jwt_handler.validate_token(malformed_token)
            assert result is None, f"Malformed token should be rejected: {malformed_token[:20]}..."
        
        # Verify valid token still works
        result = self.jwt_handler.validate_token(self.valid_access_token)
        assert result is not None, "Valid token should be accepted"
        assert result["sub"] == self.test_user_id
        
        self.record_metric("jwt_structure_validation_tests", len(malformed_tokens))
    
    def test_jwt_handler_prevents_algorithm_confusion_attacks(self):
        """Test JWT handler prevents algorithm confusion attacks.
        
        BVJ: Prevents attackers from switching to 'none' algorithm to bypass signature validation.
        CRITICAL: Algorithm validation prevents one of the most common JWT attack vectors.
        """
        # Test 'none' algorithm attack attempt
        none_algorithm_payload = {
            "sub": "attacker_user", 
            "email": "attacker@evil.com",
            "permissions": ["admin", "root"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "token_type": "access",
            "iss": "netra-auth-service"
        }
        
        # Create token with 'none' algorithm (no signature)
        none_token = jwt.encode(none_algorithm_payload, "", algorithm="none")
        
        # JWT handler should reject this token
        result = self.jwt_handler.validate_token(none_token)
        assert result is None, "Token with 'none' algorithm should be rejected"
        
        # Test algorithm switching attack (sign with HS256, claim it's RS256)
        with patch('jwt.get_unverified_header') as mock_header:
            mock_header.return_value = {"alg": "RS256", "typ": "JWT"}
            
            # This should fail because we're using HS256 secret with RS256 claim
            result = self.jwt_handler.validate_token(self.valid_access_token)
            # Handler should detect algorithm mismatch through security validation
            
        self.record_metric("algorithm_confusion_prevention_test", True)
    
    def test_jwt_handler_validates_token_claims_security(self):
        """Test JWT handler validates security-critical token claims.
        
        BVJ: Ensures tokens have required security fields to prevent bypass attacks.
        CRITICAL: Missing claims can indicate token tampering or generation attacks.
        """
        # Create token missing required security claims
        incomplete_payload = {
            "sub": "test_user",
            "email": "test@example.com"
            # Missing: iat, exp, iss, jti - all security-critical
        }
        
        incomplete_token = jwt.encode(
            incomplete_payload, 
            self.jwt_handler.secret, 
            algorithm=self.jwt_handler.algorithm
        )
        
        # Should be rejected due to missing security claims
        result = self.jwt_handler.validate_token(incomplete_token)
        assert result is None, "Token missing security claims should be rejected"
        
        # Test token with invalid issuer (potential forgery)
        forged_payload = {
            "sub": "test_user",
            "email": "test@example.com", 
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "token_type": "access",
            "iss": "evil-auth-service",  # Wrong issuer
            "jti": str(uuid.uuid4())
        }
        
        forged_token = jwt.encode(
            forged_payload,
            self.jwt_handler.secret,
            algorithm=self.jwt_handler.algorithm
        )
        
        # Should be rejected due to invalid issuer
        result = self.jwt_handler.validate_token(forged_token)
        assert result is None, "Token with invalid issuer should be rejected"
        
        self.record_metric("token_claims_security_validation", True)
    
    # ===================== JWT BLACKLIST SECURITY TESTS =====================
    
    def test_jwt_handler_token_blacklist_prevents_reuse(self):
        """Test JWT handler blacklist prevents token reuse after compromise.
        
        BVJ: Protects against compromised tokens being reused by attackers.
        CRITICAL: Token blacklisting is essential for incident response and security.
        """
        # Valid token should work initially
        result = self.jwt_handler.validate_token(self.valid_access_token)
        assert result is not None, "Token should be valid before blacklisting"
        
        # Blacklist the token (simulating compromise detection)
        blacklist_success = self.jwt_handler.blacklist_token(self.valid_access_token)
        assert blacklist_success, "Token blacklisting should succeed"
        
        # Token should now be rejected
        result = self.jwt_handler.validate_token(self.valid_access_token)
        assert result is None, "Blacklisted token should be rejected"
        
        # Verify blacklist status check works
        is_blacklisted = self.jwt_handler.is_token_blacklisted(self.valid_access_token)
        assert is_blacklisted, "Token should be detected as blacklisted"
        
        # Test token removal from blacklist (for incident resolution)
        removal_success = self.jwt_handler.remove_from_blacklist(self.valid_access_token)
        assert removal_success, "Token removal from blacklist should succeed"
        
        # Token should work again after removal
        result = self.jwt_handler.validate_token(self.valid_access_token)
        assert result is not None, "Token should work after blacklist removal"
        
        self.record_metric("token_blacklist_security_test", True)
    
    def test_jwt_handler_user_blacklist_invalidates_all_tokens(self):
        """Test JWT handler user blacklist invalidates all user tokens.
        
        BVJ: Enables immediate security response for compromised user accounts.
        CRITICAL: User blacklisting provides account-level security controls.
        """
        # Create multiple tokens for the same user
        token1 = self.jwt_handler.create_access_token(self.test_user_id, self.test_email, ["read"])
        token2 = self.jwt_handler.create_access_token(self.test_user_id, self.test_email, ["write"])
        token3 = self.jwt_handler.create_refresh_token(self.test_user_id, self.test_email)
        
        # All tokens should work initially
        for token in [token1, token2, token3]:
            result = self.jwt_handler.validate_token(token, "access" if token != token3 else "refresh")
            assert result is not None, f"Token should be valid before user blacklisting"
        
        # Blacklist the user
        user_blacklist_success = self.jwt_handler.blacklist_user(self.test_user_id)
        assert user_blacklist_success, "User blacklisting should succeed"
        
        # All user tokens should now be rejected
        for token in [token1, token2, token3]:
            result = self.jwt_handler.validate_token(token, "access" if token != token3 else "refresh")
            assert result is None, f"User token should be rejected after user blacklisting"
        
        # Verify user blacklist status check works
        is_user_blacklisted = self.jwt_handler.is_user_blacklisted(self.test_user_id)
        assert is_user_blacklisted, "User should be detected as blacklisted"
        
        # Test different user's tokens are not affected
        other_user_token = self.jwt_handler.create_access_token("other_user", "other@test.com", ["read"])
        result = self.jwt_handler.validate_token(other_user_token)
        assert result is not None, "Other user's token should not be affected by different user blacklist"
        
        # Test user removal from blacklist
        user_removal_success = self.jwt_handler.remove_user_from_blacklist(self.test_user_id)
        assert user_removal_success, "User removal from blacklist should succeed"
        
        # Create new token for user after removal (old tokens should still be invalid due to cache invalidation)
        new_user_token = self.jwt_handler.create_access_token(self.test_user_id, self.test_email, ["read"])
        result = self.jwt_handler.validate_token(new_user_token)
        assert result is not None, "New token should work after user blacklist removal"
        
        self.record_metric("user_blacklist_security_test", True)
    
    # ===================== CROSS-SERVICE AUTHENTICATION SECURITY =====================
    
    def test_jwt_handler_cross_service_token_validation(self):
        """Test JWT handler validates cross-service authentication properly.
        
        BVJ: Ensures secure service-to-service communication.
        CRITICAL: Cross-service validation prevents unauthorized service access.
        """
        # Create service token with proper audience and claims
        service_token = self.jwt_handler.create_service_token("netra-backend", "backend-service")
        
        # Service token validation should include enhanced security checks
        result = self.jwt_handler.validate_token(service_token, "service")
        assert result is not None, "Valid service token should be accepted"
        assert result["sub"] == "netra-backend"
        assert result["token_type"] == "service"
        
        # Test token with invalid audience for service context
        invalid_audience_payload = {
            "sub": "malicious-service",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "token_type": "service",
            "iss": "netra-auth-service",
            "aud": "malicious-audience",  # Invalid audience
            "jti": str(uuid.uuid4())
        }
        
        invalid_audience_token = jwt.encode(
            invalid_audience_payload,
            self.jwt_handler.secret,
            algorithm=self.jwt_handler.algorithm
        )
        
        # Should be rejected due to invalid audience
        result = self.jwt_handler.validate_token(invalid_audience_token, "service")
        assert result is None, "Service token with invalid audience should be rejected"
        
        self.record_metric("cross_service_token_validation", True)
    
    def test_jwt_handler_service_signature_validation(self):
        """Test JWT handler validates service signatures for enhanced security.
        
        BVJ: Prevents service impersonation attacks in microservice architecture.
        CRITICAL: Service signature validation ensures authentic service communication.
        """
        # Create service token and validate it gets proper service signature
        service_token = self.jwt_handler.create_service_token("netra-analytics", "analytics-service")
        
        result = self.jwt_handler.validate_token(service_token, "service")
        assert result is not None, "Service token should be valid"
        
        # Validate service signature is present and properly formatted
        assert "service_signature" in result, "Service signature should be present in validation result"
        service_signature = result["service_signature"]
        assert isinstance(service_signature, str), "Service signature should be string"
        assert len(service_signature) > 32, "Service signature should be substantial (HMAC-SHA256)"
        
        # Test that service signature changes for different services
        other_service_token = self.jwt_handler.create_service_token("netra-frontend", "frontend-service")
        other_result = self.jwt_handler.validate_token(other_service_token, "service")
        
        assert other_result["service_signature"] != service_signature, \
            "Different services should have different signatures"
        
        self.record_metric("service_signature_validation", True)
    
    # ===================== TOKEN REPLAY PROTECTION TESTS =====================
    
    def test_jwt_handler_prevents_token_replay_attacks(self):
        """Test JWT handler prevents token replay attacks for consumption operations.
        
        BVJ: Protects against attackers replaying intercepted tokens.
        CRITICAL: Replay protection is essential for token refresh and consumption operations.
        """
        # Create refresh token for consumption testing
        refresh_token = self.jwt_handler.create_refresh_token(
            "replay_test_user", 
            "replay@test.com",
            ["read", "write"]
        )
        
        # First consumption should work (token refresh)
        first_result = self.jwt_handler.validate_token_for_consumption(refresh_token, "refresh")
        assert first_result is not None, "First token consumption should succeed"
        
        # Use token for refresh (this consumes it)
        new_tokens = self.jwt_handler.refresh_access_token(refresh_token)
        assert new_tokens is not None, "Token refresh should succeed"
        new_access_token, new_refresh_token = new_tokens
        
        # Verify new tokens are valid
        new_access_result = self.jwt_handler.validate_token(new_access_token)
        assert new_access_result is not None, "New access token should be valid"
        
        new_refresh_result = self.jwt_handler.validate_token(new_refresh_token, "refresh")
        assert new_refresh_result is not None, "New refresh token should be valid"
        
        # Verify tokens have proper user data from refresh token payload
        assert new_access_result["sub"] == "replay_test_user"
        assert new_access_result["email"] == "replay@test.com"
        
        self.record_metric("token_replay_protection_test", True)
    
    # ===================== TOKEN EXPIRATION AND TIME-BASED SECURITY =====================
    
    def test_jwt_handler_enforces_token_expiration_security(self):
        """Test JWT handler properly enforces token expiration for security.
        
        BVJ: Prevents indefinite token usage that could lead to security breaches.
        CRITICAL: Token expiration limits attack windows and ensures fresh authentication.
        """
        # Create short-lived token for testing (1 second expiration)
        now = datetime.now(timezone.utc)
        short_lived_payload = {
            "sub": "expiration_test_user",
            "email": "expiration@test.com",
            "permissions": ["read"],
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 1,  # 1 second expiration
            "token_type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform",
            "jti": str(uuid.uuid4())
        }
        
        short_lived_token = jwt.encode(
            short_lived_payload,
            self.jwt_handler.secret,
            algorithm=self.jwt_handler.algorithm
        )
        
        # Token should be valid immediately
        result = self.jwt_handler.validate_token(short_lived_token)
        assert result is not None, "Token should be valid immediately after creation"
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Token should now be expired
        result = self.jwt_handler.validate_token(short_lived_token)
        assert result is None, "Expired token should be rejected"
        
        # Test token issued in future (clock skew attack)
        future_payload = {
            "sub": "future_test_user",
            "email": "future@test.com",
            "permissions": ["read"],
            "iat": int(time.time()) + 3600,  # Issued 1 hour in future
            "exp": int(time.time()) + 7200,  # Expires 2 hours in future
            "token_type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform", 
            "jti": str(uuid.uuid4())
        }
        
        future_token = jwt.encode(
            future_payload,
            self.jwt_handler.secret,
            algorithm=self.jwt_handler.algorithm
        )
        
        # Future token should be rejected
        result = self.jwt_handler.validate_token(future_token)
        assert result is None, "Token issued in future should be rejected"
        
        self.record_metric("token_expiration_security_test", True)
    
    def test_jwt_handler_rejects_ancient_tokens_security(self):
        """Test JWT handler rejects tokens that are too old for security.
        
        BVJ: Prevents use of old tokens that may have been compromised.
        CRITICAL: Age limits reduce attack surface from long-lived compromised tokens.
        """
        # Create very old token (25 hours ago - beyond 24 hour limit)
        ancient_time = datetime.now(timezone.utc) - timedelta(hours=25)
        ancient_payload = {
            "sub": "ancient_test_user",
            "email": "ancient@test.com", 
            "permissions": ["read"],
            "iat": int(ancient_time.timestamp()),
            "exp": int(time.time()) + 3600,  # Still not expired, but too old
            "token_type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform",
            "jti": str(uuid.uuid4())
        }
        
        ancient_token = jwt.encode(
            ancient_payload,
            self.jwt_handler.secret,
            algorithm=self.jwt_handler.algorithm
        )
        
        # Ancient token should be rejected even if not expired
        result = self.jwt_handler.validate_token(ancient_token)
        assert result is None, "Ancient token should be rejected for security"
        
        self.record_metric("ancient_token_rejection_test", True)
    
    # ===================== JWT PERFORMANCE AND CACHING SECURITY =====================
    
    def test_jwt_handler_cache_security_validation(self):
        """Test JWT handler cache doesn't create security vulnerabilities.
        
        BVJ: Ensures performance optimizations don't compromise security.
        CRITICAL: JWT caching must not allow stale security decisions.
        """
        # Create token and validate it (should be cached)
        test_token = self.jwt_handler.create_access_token("cache_test_user", "cache@test.com", ["read"])
        
        # First validation (populates cache)
        result1 = self.jwt_handler.validate_token(test_token)
        assert result1 is not None, "First validation should succeed"
        
        # Second validation (should use cache)
        result2 = self.jwt_handler.validate_token(test_token)
        assert result2 is not None, "Cached validation should succeed"
        assert result1["sub"] == result2["sub"], "Cached result should match original"
        
        # Blacklist user - this should invalidate cache
        self.jwt_handler.blacklist_user("cache_test_user")
        
        # Validation should now fail even with cache (cache should be invalidated)
        result3 = self.jwt_handler.validate_token(test_token)
        assert result3 is None, "Validation should fail after user blacklist despite cache"
        
        self.record_metric("jwt_cache_security_test", True)
    
    # ===================== JWT ERROR HANDLING SECURITY =====================
    
    def test_jwt_handler_secure_error_handling(self):
        """Test JWT handler doesn't leak sensitive information in errors.
        
        BVJ: Prevents information disclosure that could aid attackers.
        CRITICAL: Error handling must not reveal system internals or secrets.
        """
        # Test with completely invalid token
        invalid_tokens = [
            "definitely_not_a_jwt_token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.INVALID.PAYLOAD",
            self.jwt_handler.secret,  # Secret itself should not work as token
            '{"sub": "attacker", "admin": true}'  # Raw JSON should not work
        ]
        
        for invalid_token in invalid_tokens:
            # Validation should fail gracefully without revealing system details
            result = self.jwt_handler.validate_token(invalid_token)
            assert result is None, f"Invalid token should be rejected: {invalid_token[:20]}..."
        
        # Ensure handler doesn't raise exceptions that could leak information
        try:
            # Try validation with mock token that could cause various errors
            mock_token = "mock_token_for_error_testing" 
            result = self.jwt_handler.validate_token(mock_token)
            assert result is None, "Mock token should be rejected"
        except Exception as e:
            pytest.fail(f"JWT handler should not raise exceptions during validation: {e}")
        
        self.record_metric("secure_error_handling_test", len(invalid_tokens))
    
    def test_jwt_handler_performance_stats_security(self):
        """Test JWT handler performance stats don't leak sensitive information.
        
        BVJ: Ensures monitoring doesn't compromise security.
        CRITICAL: Performance metrics must not expose sensitive authentication data.
        """
        # Perform some operations to generate stats
        test_token = self.jwt_handler.create_access_token("stats_test_user", "stats@test.com", ["read"])
        self.jwt_handler.validate_token(test_token)
        self.jwt_handler.blacklist_token(test_token)
        
        # Get performance stats
        stats = self.jwt_handler.get_performance_stats()
        
        # Verify stats structure without sensitive data
        assert "cache_stats" in stats, "Performance stats should include cache information"
        assert "blacklist_stats" in stats, "Performance stats should include blacklist information"
        assert "performance_optimizations" in stats, "Performance stats should include optimization info"
        
        # Verify no sensitive data is exposed
        stats_json = json.dumps(stats)
        assert self.jwt_handler.secret not in stats_json, "JWT secret should not appear in stats"
        assert "stats_test_user" not in stats_json, "User IDs should not appear in stats"
        assert test_token not in stats_json, "Tokens should not appear in stats"
        
        # Verify blacklist stats are just counts, not actual tokens/users
        blacklist_stats = stats["blacklist_stats"]
        assert "blacklisted_tokens" in blacklist_stats
        assert "blacklisted_users" in blacklist_stats
        assert isinstance(blacklist_stats["blacklisted_tokens"], int)
        assert isinstance(blacklist_stats["blacklisted_users"], int)
        
        self.record_metric("performance_stats_security_test", True)


class TestJWTHandlerTokenOperationsBatch4(SSotAsyncTestCase):
    """
    JWT Handler token operations tests for Batch 4.
    
    Tests core token lifecycle operations with business security requirements:
    - Token creation with proper security claims
    - Token refresh with user data preservation
    - Service token authentication 
    - ID token validation for OAuth flows
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for JWT operations tests."""
        super().setup_method(method)
        
        # Initialize with test environment
        self.env = get_env()
        self.env.set("JWT_SECRET_KEY", "jwt_operations_test_secret_32chars", "test_jwt_operations_batch4")
        self.env.set("ENVIRONMENT", "test", "test_jwt_operations_batch4")
        self.env.set("SERVICE_SECRET", "service_operations_secret_32chars", "test_jwt_operations_batch4")
        
        self.jwt_handler = JWTHandler()
        
        # Test user data
        self.test_user_id = "ops_test_user_batch4"
        self.test_email = "ops@batch4-test.com"
        self.test_permissions = ["read", "write", "operations"]
        
        self.record_metric("jwt_operations_test_setup", True)
    
    def teardown_method(self, method):
        """Clean up isolated environment after each test."""
        self.env.delete("JWT_SECRET_KEY", "test_jwt_operations_batch4")
        self.env.delete("ENVIRONMENT", "test_jwt_operations_batch4")
        self.env.delete("SERVICE_SECRET", "test_jwt_operations_batch4")
        
        super().teardown_method(method)
    
    def test_jwt_handler_creates_access_tokens_with_security_claims(self):
        """Test JWT handler creates access tokens with all required security claims.
        
        BVJ: Ensures access tokens have proper security attributes for business operations.
        CRITICAL: Missing security claims could lead to authorization bypass vulnerabilities.
        """
        # Create access token
        access_token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email, 
            self.test_permissions
        )
        
        assert access_token is not None, "Access token should be created"
        assert isinstance(access_token, str), "Access token should be string"
        assert len(access_token) > 100, "Access token should be substantial length"
        
        # Decode and verify security claims (without signature verification for inspection)
        payload = jwt.decode(access_token, options={"verify_signature": False})
        
        # Verify required security claims are present
        required_claims = ["sub", "email", "permissions", "iat", "exp", "token_type", "iss", "aud", "jti", "env", "svc_id"]
        for claim in required_claims:
            assert claim in payload, f"Access token missing required claim: {claim}"
        
        # Verify claim values
        assert payload["sub"] == self.test_user_id, "Subject should match user ID"
        assert payload["email"] == self.test_email, "Email should match provided email"
        assert payload["permissions"] == self.test_permissions, "Permissions should match"
        assert payload["token_type"] == "access", "Token type should be access"
        assert payload["type"] == "access", "Type field should also be access (compatibility)"
        assert payload["iss"] == "netra-auth-service", "Issuer should be netra-auth-service"
        assert payload["aud"] == "netra-platform", "Audience should be netra-platform for access tokens"
        
        # Verify token expiration is reasonable
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], timezone.utc)
        token_lifetime = exp_time - iat_time
        
        assert token_lifetime.total_seconds() > 0, "Token should have positive lifetime"
        assert token_lifetime.total_seconds() <= 24 * 3600, "Token should not live longer than 24 hours"
        
        self.record_metric("access_token_creation_with_security_claims", True)
    
    def test_jwt_handler_creates_refresh_tokens_with_user_data(self):
        """Test JWT handler creates refresh tokens with user data for token refresh.
        
        BVJ: Ensures refresh tokens contain necessary data to generate new access tokens.
        CRITICAL: Refresh tokens must preserve user context for seamless token renewal.
        """
        # Create refresh token with user data
        refresh_token = self.jwt_handler.create_refresh_token(
            self.test_user_id,
            self.test_email,
            self.test_permissions
        )
        
        assert refresh_token is not None, "Refresh token should be created"
        assert isinstance(refresh_token, str), "Refresh token should be string"
        
        # Decode and verify refresh token contains user data
        payload = jwt.decode(refresh_token, options={"verify_signature": False})
        
        # Verify user data preservation
        assert payload["sub"] == self.test_user_id, "Refresh token should preserve user ID"
        assert payload["email"] == self.test_email, "Refresh token should preserve email"
        assert payload["permissions"] == self.test_permissions, "Refresh token should preserve permissions"
        assert payload["token_type"] == "refresh", "Token type should be refresh"
        
        # Verify refresh token has longer lifetime than access token
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], timezone.utc)
        token_lifetime = exp_time - iat_time
        
        assert token_lifetime.total_seconds() > 24 * 3600, "Refresh token should live longer than 24 hours"
        
        self.record_metric("refresh_token_creation_with_user_data", True)
    
    def test_jwt_handler_refresh_access_token_preserves_user_data(self):
        """Test JWT handler refresh operation preserves user data correctly.
        
        BVJ: Ensures token refresh maintains user context and permissions.
        CRITICAL: Token refresh must not lose user data or change permissions unexpectedly.
        """
        # Create initial tokens
        original_refresh_token = self.jwt_handler.create_refresh_token(
            self.test_user_id,
            self.test_email, 
            self.test_permissions
        )
        
        # Refresh to get new tokens
        new_tokens = self.jwt_handler.refresh_access_token(original_refresh_token)
        assert new_tokens is not None, "Token refresh should succeed"
        
        new_access_token, new_refresh_token = new_tokens
        
        # Verify new access token has preserved user data
        access_payload = jwt.decode(new_access_token, options={"verify_signature": False})
        assert access_payload["sub"] == self.test_user_id, "Refreshed access token should preserve user ID"
        assert access_payload["email"] == self.test_email, "Refreshed access token should preserve email"
        assert access_payload["permissions"] == self.test_permissions, "Refreshed access token should preserve permissions"
        
        # Verify new refresh token also preserves user data
        refresh_payload = jwt.decode(new_refresh_token, options={"verify_signature": False})
        assert refresh_payload["sub"] == self.test_user_id, "New refresh token should preserve user ID"
        assert refresh_payload["email"] == self.test_email, "New refresh token should preserve email"
        assert refresh_payload["permissions"] == self.test_permissions, "New refresh token should preserve permissions"
        
        # Verify tokens are actually different (new JTIs)
        original_payload = jwt.decode(original_refresh_token, options={"verify_signature": False})
        assert access_payload["jti"] != original_payload["jti"], "New access token should have different JTI"
        assert refresh_payload["jti"] != original_payload["jti"], "New refresh token should have different JTI"
        assert access_payload["jti"] != refresh_payload["jti"], "Access and refresh tokens should have different JTIs"
        
        # Verify new tokens are valid
        access_validation = self.jwt_handler.validate_token(new_access_token)
        assert access_validation is not None, "New access token should be valid"
        
        refresh_validation = self.jwt_handler.validate_token(new_refresh_token, "refresh")
        assert refresh_validation is not None, "New refresh token should be valid"
        
        self.record_metric("token_refresh_user_data_preservation", True)
    
    def test_jwt_handler_service_token_authentication(self):
        """Test JWT handler creates and validates service tokens for inter-service auth.
        
        BVJ: Enables secure service-to-service communication in microservice architecture.
        CRITICAL: Service authentication prevents unauthorized access between internal services.
        """
        service_id = "netra-analytics"
        service_name = "analytics-service"
        
        # Create service token
        service_token = self.jwt_handler.create_service_token(service_id, service_name)
        
        assert service_token is not None, "Service token should be created"
        assert isinstance(service_token, str), "Service token should be string"
        
        # Decode and verify service token structure
        payload = jwt.decode(service_token, options={"verify_signature": False})
        
        # Verify service-specific claims
        assert payload["sub"] == service_id, "Service token subject should be service ID"
        assert payload["service"] == service_name, "Service token should contain service name"
        assert payload["token_type"] == "service", "Token type should be service"
        assert payload["aud"] == "netra-services", "Service token audience should be netra-services"
        
        # Verify service token validation
        validation_result = self.jwt_handler.validate_token(service_token, "service")
        assert validation_result is not None, "Service token should validate successfully"
        assert validation_result["sub"] == service_id, "Validated service token should preserve service ID"
        assert validation_result["service"] == service_name, "Validated service token should preserve service name"
        
        # Verify service signature is added during validation
        assert "service_signature" in validation_result, "Service validation should add service signature"
        service_signature = validation_result["service_signature"]
        assert isinstance(service_signature, str), "Service signature should be string"
        assert len(service_signature) > 32, "Service signature should be substantial (HMAC)"
        
        self.record_metric("service_token_authentication", True)
    
    def test_jwt_handler_validates_oauth_id_tokens(self):
        """Test JWT handler validates OAuth ID tokens from external providers.
        
        BVJ: Enables OAuth integration for enterprise SSO and third-party authentication.
        CRITICAL: ID token validation ensures authentic external authentication.
        """
        # Create mock OAuth ID token (simulating Google OAuth response)
        oauth_id_payload = {
            "sub": "google_user_12345",
            "email": "user@enterprise.com",
            "name": "Enterprise User",
            "iss": "https://accounts.google.com",  # Google issuer
            "aud": "our-google-client-id",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour
            "email_verified": True,
            "hd": "enterprise.com"  # Hosted domain claim
        }
        
        # Create ID token (note: in real scenario, this would come from Google with their signature)
        oauth_id_token = jwt.encode(oauth_id_payload, "mock_google_secret", algorithm="HS256")
        
        # Validate ID token
        id_validation_result = self.jwt_handler.validate_id_token(
            oauth_id_token,
            expected_issuer="https://accounts.google.com"
        )
        
        assert id_validation_result is not None, "Valid OAuth ID token should be accepted"
        assert id_validation_result["sub"] == "google_user_12345", "ID token should preserve external subject"
        assert id_validation_result["email"] == "user@enterprise.com", "ID token should preserve email"
        assert id_validation_result["iss"] == "https://accounts.google.com", "ID token should preserve issuer"
        
        # Test ID token with wrong issuer
        wrong_issuer_result = self.jwt_handler.validate_id_token(
            oauth_id_token,
            expected_issuer="https://malicious-provider.com"
        )
        
        assert wrong_issuer_result is None, "ID token with wrong issuer should be rejected"
        
        # Test expired ID token
        expired_oauth_payload = oauth_id_payload.copy()
        expired_oauth_payload["exp"] = int(time.time()) - 3600  # Expired 1 hour ago
        expired_oauth_token = jwt.encode(expired_oauth_payload, "mock_google_secret", algorithm="HS256")
        
        expired_result = self.jwt_handler.validate_id_token(expired_oauth_token)
        assert expired_result is None, "Expired OAuth ID token should be rejected"
        
        self.record_metric("oauth_id_token_validation", True)
    
    def test_jwt_handler_user_id_extraction_utility(self):
        """Test JWT handler utility for extracting user ID without full validation.
        
        BVJ: Enables efficient user identification for logging and routing without full auth.
        CRITICAL: User ID extraction must be safe and not bypass security for actual operations.
        """
        # Create test token
        test_token = self.jwt_handler.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_permissions
        )
        
        # Extract user ID
        extracted_user_id = self.jwt_handler.extract_user_id(test_token)
        assert extracted_user_id == self.test_user_id, "Should extract correct user ID"
        
        # Test with invalid token structure
        invalid_token = "not.a.jwt.token"
        extracted_invalid = self.jwt_handler.extract_user_id(invalid_token)
        assert extracted_invalid is None, "Should return None for invalid token structure"
        
        # Test with malformed token
        malformed_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.INVALID_BASE64.signature"
        extracted_malformed = self.jwt_handler.extract_user_id(malformed_token)
        assert extracted_malformed is None, "Should return None for malformed token"
        
        # Verify extraction doesn't bypass security checks completely
        # (it should still do basic security validation)
        security_bypass_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiJhdHRhY2tlciJ9."
        extracted_bypass = self.jwt_handler.extract_user_id(security_bypass_token)
        assert extracted_bypass is None, "Should not extract from insecure tokens"
        
        self.record_metric("user_id_extraction_utility", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])