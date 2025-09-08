"""
JWT Token Validation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure authentication for all user tiers
- Value Impact: JWT validation protects user data and enables subscription tier access control
- Strategic Impact: Core security foundation that prevents unauthorized access and enables revenue protection

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real JWT libraries and validation logic
- Tests real JWT secret synchronization across services
- Validates token expiry, refresh, and security patterns
- Ensures multi-user isolation through proper token validation
"""

import asyncio
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from auth_service.auth_core.jwt_handler import JWTHandler
from auth_service.auth_core.models import User, UserSession


class TestJWTTokenValidationIntegration(BaseIntegrationTest):
    """Integration tests for JWT token validation with real authentication flows."""
    
    def setup_method(self):
        """Set up for JWT validation tests."""
        super().setup_method()
        self.env = get_env()
        
        # Use real JWT secrets - CRITICAL for business security
        self.jwt_secret = self.env.get("JWT_SECRET_KEY") or "test-jwt-secret-key-unified-testing-32chars"
        self.jwt_handler = JWTHandler(secret_key=self.jwt_secret)
        
        # Test user data for consistent validation
        self.test_user_data = {
            "user_id": "test-user-12345",
            "email": "jwt-test@example.com",
            "permissions": ["read", "write"],
            "subscription_tier": "early"
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_jwt_token_creation_and_validation(self):
        """
        Test JWT token creation and validation with real crypto operations.
        
        Business Value: Ensures tokens protect user sessions and subscription access.
        Security Impact: Validates cryptographic integrity prevents token forgery.
        """
        # Create real JWT token with business-critical claims
        token_payload = {
            "sub": self.test_user_data["user_id"],
            "email": self.test_user_data["email"],
            "permissions": self.test_user_data["permissions"],
            "subscription_tier": self.test_user_data["subscription_tier"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        # Use real JWT library to create token
        token = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")
        
        # Validate token with real JWT verification
        decoded = self.jwt_handler.verify_token(token)
        
        # Assert business-critical claims are preserved
        assert decoded["sub"] == self.test_user_data["user_id"]
        assert decoded["email"] == self.test_user_data["email"]
        assert decoded["permissions"] == self.test_user_data["permissions"]
        assert decoded["subscription_tier"] == self.test_user_data["subscription_tier"]
        assert decoded["type"] == "access"
        assert decoded["iss"] == "netra-auth-service"
        
        self.logger.info(f"JWT token validation successful for user {decoded['email']}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_jwt_token_expiry_validation(self):
        """
        Test JWT token expiry validation with real time-based checks.
        
        Business Value: Prevents expired tokens from accessing paid features.
        Security Impact: Ensures session timeouts protect against session hijacking.
        """
        # Create expired token - CRITICAL security test
        expired_payload = {
            "sub": self.test_user_data["user_id"],
            "email": self.test_user_data["email"],
            "permissions": self.test_user_data["permissions"],
            "iat": datetime.now(timezone.utc) - timedelta(minutes=60),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=30),  # Expired 30 mins ago
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        expired_token = jwt.encode(expired_payload, self.jwt_secret, algorithm="HS256")
        
        # Validate that expired token is properly rejected
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, self.jwt_secret, algorithms=["HS256"])
        
        # Validate JWT handler properly handles expired tokens
        validation_result = self.jwt_handler.validate_token_safely(expired_token)
        assert not validation_result.is_valid
        assert "expired" in validation_result.error_message.lower()
        
        self.logger.info("JWT token expiry validation successful - expired tokens properly rejected")
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    def test_jwt_token_malformed_validation(self):
        """
        Test JWT token validation against malformed/tampered tokens.
        
        Business Value: Protects against token manipulation attacks on subscription access.
        Security Impact: Validates cryptographic signature prevents privilege escalation.
        """
        # Create valid token
        valid_payload = {
            "sub": self.test_user_data["user_id"],
            "email": self.test_user_data["email"],
            "permissions": ["read"],  # Limited permissions
            "subscription_tier": "free",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        valid_token = jwt.encode(valid_payload, self.jwt_secret, algorithm="HS256")
        
        # Test various malformed token scenarios
        test_cases = [
            ("empty_token", ""),
            ("null_token", None),
            ("invalid_format", "not.a.jwt"),
            ("tampered_token", valid_token[:-10] + "tampered123"),
            ("wrong_secret", jwt.encode(valid_payload, "wrong-secret", algorithm="HS256")),
        ]
        
        for case_name, malformed_token in test_cases:
            validation_result = self.jwt_handler.validate_token_safely(malformed_token)
            assert not validation_result.is_valid, f"Case {case_name} should fail validation"
            assert validation_result.error_message is not None
            
            self.logger.info(f"Malformed token case '{case_name}' properly rejected")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    def test_jwt_subscription_tier_validation(self):
        """
        Test JWT token validation for different subscription tiers.
        
        Business Value: Enables revenue protection by validating subscription access levels.
        Strategic Impact: Core functionality for subscription tier enforcement.
        """
        subscription_tiers = [
            ("free", ["read"]),
            ("early", ["read", "write"]),
            ("mid", ["read", "write", "advanced_analytics"]),
            ("enterprise", ["read", "write", "advanced_analytics", "custom_models", "priority_support"])
        ]
        
        for tier, expected_permissions in subscription_tiers:
            # Create token with subscription tier
            tier_payload = {
                "sub": f"user-{tier}-12345",
                "email": f"{tier}-user@example.com",
                "permissions": expected_permissions,
                "subscription_tier": tier,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
                "type": "access",
                "iss": "netra-auth-service"
            }
            
            token = jwt.encode(tier_payload, self.jwt_secret, algorithm="HS256")
            
            # Validate token preserves subscription tier information
            decoded = self.jwt_handler.verify_token(token)
            assert decoded["subscription_tier"] == tier
            assert decoded["permissions"] == expected_permissions
            
            # Validate subscription tier-specific access
            has_advanced_access = "advanced_analytics" in decoded["permissions"]
            if tier in ["mid", "enterprise"]:
                assert has_advanced_access, f"{tier} should have advanced access"
            else:
                assert not has_advanced_access, f"{tier} should not have advanced access"
            
            self.logger.info(f"Subscription tier '{tier}' validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_jwt_multi_user_isolation_validation(self):
        """
        Test JWT token validation ensures proper user isolation.
        
        Business Value: Prevents data leakage between users - CRITICAL for multi-tenant system.
        Security Impact: Ensures user context isolation prevents unauthorized access.
        """
        # Create tokens for different users
        user1_payload = {
            "sub": "user-1-isolation-test",
            "email": "user1@isolation-test.com",
            "permissions": ["read", "write"],
            "subscription_tier": "early",
            "user_context_id": "ctx-user-1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        user2_payload = {
            "sub": "user-2-isolation-test",
            "email": "user2@isolation-test.com", 
            "permissions": ["read", "write"],
            "subscription_tier": "mid",
            "user_context_id": "ctx-user-2",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        user1_token = jwt.encode(user1_payload, self.jwt_secret, algorithm="HS256")
        user2_token = jwt.encode(user2_payload, self.jwt_secret, algorithm="HS256")
        
        # Validate each token maintains user isolation
        user1_decoded = self.jwt_handler.verify_token(user1_token)
        user2_decoded = self.jwt_handler.verify_token(user2_token)
        
        # Assert user isolation - users must have different contexts
        assert user1_decoded["sub"] != user2_decoded["sub"]
        assert user1_decoded["email"] != user2_decoded["email"]
        assert user1_decoded["user_context_id"] != user2_decoded["user_context_id"]
        
        # Validate subscription tier isolation
        assert user1_decoded["subscription_tier"] == "early"
        assert user2_decoded["subscription_tier"] == "mid"
        
        # Ensure no cross-contamination of user data
        assert "user-2" not in user1_decoded["sub"]
        assert "user-1" not in user2_decoded["sub"]
        
        self.logger.info("JWT multi-user isolation validation successful")


class TestJWTSecretSynchronizationIntegration(BaseIntegrationTest):
    """Integration tests for JWT secret synchronization across services."""
    
    def setup_method(self):
        """Set up for JWT secret synchronization tests."""
        super().setup_method()
        self.env = get_env()
        
        # Test different JWT secret scenarios
        self.primary_secret = self.env.get("JWT_SECRET_KEY") or "primary-test-secret-32chars"
        self.secondary_secret = "secondary-test-secret-32chars"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_jwt_cross_service_secret_consistency(self):
        """
        Test JWT secret consistency across different service contexts.
        
        Business Value: Ensures tokens created by auth service work across all services.
        Strategic Impact: Enables seamless multi-service authentication.
        """
        # Create token with primary secret (auth service)
        auth_payload = {
            "sub": "cross-service-user",
            "email": "cross-service@test.com",
            "permissions": ["read", "write"],
            "service_origin": "auth_service",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        auth_token = jwt.encode(auth_payload, self.primary_secret, algorithm="HS256")
        
        # Validate token can be decoded by other services using same secret
        backend_handler = JWTHandler(secret_key=self.primary_secret)
        decoded_in_backend = backend_handler.verify_token(auth_token)
        
        assert decoded_in_backend["sub"] == "cross-service-user"
        assert decoded_in_backend["service_origin"] == "auth_service"
        assert decoded_in_backend["iss"] == "netra-auth-service"
        
        self.logger.info("JWT cross-service secret consistency validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_jwt_secret_rotation_compatibility(self):
        """
        Test JWT token validation during secret rotation scenarios.
        
        Business Value: Ensures service continuity during security updates.
        Security Impact: Validates graceful handling of secret rotation.
        """
        # Create token with old secret
        old_payload = {
            "sub": "rotation-test-user",
            "email": "rotation@test.com",
            "permissions": ["read"],
            "rotation_test": True,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
        old_token = jwt.encode(old_payload, self.primary_secret, algorithm="HS256")
        new_token = jwt.encode(old_payload, self.secondary_secret, algorithm="HS256")
        
        # Validate old handler rejects new secret tokens
        old_handler = JWTHandler(secret_key=self.primary_secret)
        new_handler = JWTHandler(secret_key=self.secondary_secret)
        
        # Old handler should validate old tokens
        old_decoded = old_handler.verify_token(old_token)
        assert old_decoded["rotation_test"] is True
        
        # New handler should validate new tokens  
        new_decoded = new_handler.verify_token(new_token)
        assert new_decoded["rotation_test"] is True
        
        # Cross-validation should fail (proper security)
        with pytest.raises(jwt.InvalidSignatureError):
            old_handler.verify_token(new_token)
            
        with pytest.raises(jwt.InvalidSignatureError):
            new_handler.verify_token(old_token)
        
        self.logger.info("JWT secret rotation compatibility validation successful")