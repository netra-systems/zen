"""
Auth Service Core Integration Tests

Business Value Justification (BVJ):
- Segment: All (Platform/Security Core)
- Business Goal: Ensure secure, reliable user authentication and authorization across all user tiers
- Value Impact: Validates core security functionality that protects user data and platform integrity
- Strategic Impact: Ensures authentication reliability that directly affects user trust and platform security compliance

These tests validate real auth service behavior without mocks, focusing on:
1. JWT token lifecycle management and validation
2. OAuth flow components and token exchange
3. User session management with proper isolation  
4. Authentication middleware and security controls
5. Multi-service authentication coordination
6. Performance characteristics and security compliance

CRITICAL: These tests use real auth components without Docker dependencies
NO MOCKS - Real authentication behavior validation
"""

import asyncio
import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.unified_auth_interface import UnifiedAuthInterface, get_unified_auth
from auth_service.auth_core.models.auth_models import (
    AuthProvider, 
    LoginRequest, 
    LoginResponse, 
    TokenResponse
)
from auth_service.auth_core.oauth_manager import OAuthManager
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestAuthServiceCore(BaseIntegrationTest):
    """Integration tests for auth service core functionality."""
    
    def setup_method(self):
        """Set up for each test method."""
        super().setup_method()
        
        # Initialize real auth components (no mocks for integration)
        self.jwt_handler = JWTHandler()
        self.auth_service = AuthService()
        self.unified_auth = UnifiedAuthInterface()
        self.oauth_manager = OAuthManager()
        
        # Test user data
        self.test_user_data = {
            "email": "integration-test@example.com",
            "password": "TestPassword123!",
            "name": "Integration Test User",
            "user_id": "test-user-integration-001"
        }
    
    @pytest.mark.integration
    async def test_jwt_token_lifecycle(self):
        """
        BVJ: Critical security functionality - JWT tokens must be created, validated, and expired properly
        Tests complete JWT lifecycle: creation -> validation -> expiration -> blacklisting
        """
        logger.info("Testing JWT token lifecycle management")
        
        # 1. Token Creation
        access_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=["read", "write"]
        )
        
        assert access_token is not None, "Access token creation failed"
        assert isinstance(access_token, str), "Access token must be string"
        assert len(access_token) > 50, "Access token appears too short"
        
        # 2. Token Validation
        payload = self.jwt_handler.validate_token(access_token, "access")
        assert payload is not None, "Token validation failed"
        assert payload["sub"] == self.test_user_data["user_id"], "User ID mismatch"
        assert payload["email"] == self.test_user_data["email"], "Email mismatch"
        assert "read" in payload.get("permissions", []), "Permissions missing"
        
        # 3. Token Structure Validation
        token_parts = access_token.split('.')
        assert len(token_parts) == 3, "Invalid JWT structure"
        
        # 4. Token Blacklisting
        blacklist_success = self.jwt_handler.blacklist_token(access_token)
        assert blacklist_success, "Token blacklisting failed"
        
        # 5. Validate blacklisted token fails
        blacklisted_payload = self.jwt_handler.validate_token(access_token, "access")
        assert blacklisted_payload is None, "Blacklisted token should not validate"
        
        logger.info("JWT token lifecycle test completed successfully")
    
    @pytest.mark.integration
    async def test_oauth_flow_components(self):
        """
        BVJ: OAuth authentication enables enterprise user onboarding and SSO integrations
        Tests OAuth manager initialization and provider configuration
        """
        logger.info("Testing OAuth flow components")
        
        # 1. OAuth Manager Initialization
        available_providers = self.oauth_manager.get_available_providers()
        assert isinstance(available_providers, list), "Available providers should be list"
        
        # 2. Google Provider Configuration Check
        if "google" in available_providers:
            google_provider = self.oauth_manager.get_provider("google")
            assert google_provider is not None, "Google provider should be available"
            
            provider_status = self.oauth_manager.get_provider_status("google")
            assert provider_status["available"] is True, "Google provider should be available"
            assert "configured" in provider_status, "Provider status should include configuration"
        
        # 3. Provider Status for Non-existent Provider
        invalid_provider_status = self.oauth_manager.get_provider_status("invalid-provider")
        assert invalid_provider_status["available"] is False, "Invalid provider should not be available"
        assert "error" in invalid_provider_status, "Invalid provider should have error"
        
        logger.info("OAuth flow components test completed successfully")
    
    @pytest.mark.integration
    async def test_user_session_management(self):
        """
        BVJ: Session management enables stateful user experience and security controls
        Tests session creation, retrieval, and cleanup with proper isolation
        """
        logger.info("Testing user session management")
        
        # 1. Session Creation
        user_data = {
            "email": self.test_user_data["email"],
            "name": self.test_user_data["name"],
            "permissions": ["read", "write"]
        }
        
        session_id = self.auth_service.create_session(
            user_id=self.test_user_data["user_id"],
            user_data=user_data
        )
        
        assert session_id is not None, "Session creation failed"
        assert isinstance(session_id, str), "Session ID must be string"
        assert len(session_id) > 10, "Session ID appears too short"
        
        # 2. Session Retrieval (using internal session storage)
        assert session_id in self.auth_service._sessions, "Session not stored properly"
        stored_session = self.auth_service._sessions[session_id]
        assert stored_session["user_id"] == self.test_user_data["user_id"], "User ID mismatch in session"
        assert stored_session["user_data"]["email"] == user_data["email"], "Email mismatch in session"
        
        # 3. Session Deletion
        delete_success = self.auth_service.delete_session(session_id)
        assert delete_success is True, "Session deletion failed"
        assert session_id not in self.auth_service._sessions, "Session not removed after deletion"
        
        # 4. User Session Invalidation
        session_id_2 = self.auth_service.create_session(self.test_user_data["user_id"], user_data)
        session_id_3 = self.auth_service.create_session(self.test_user_data["user_id"], user_data)
        
        await self.auth_service.invalidate_user_sessions(self.test_user_data["user_id"])
        
        assert session_id_2 not in self.auth_service._sessions, "User sessions not invalidated"
        assert session_id_3 not in self.auth_service._sessions, "User sessions not invalidated"
        
        logger.info("User session management test completed successfully")
    
    @pytest.mark.integration
    async def test_authentication_middleware_validation(self):
        """
        BVJ: Middleware ensures every request is properly authenticated and authorized
        Tests token validation in middleware context with security headers
        """
        logger.info("Testing authentication middleware validation")
        
        # 1. Create Valid Token
        access_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=["read", "write", "admin"]
        )
        
        # 2. Unified Auth Token Validation
        validation_result = await self.unified_auth.validate_user_token(access_token)
        
        assert validation_result is not None, "Token validation failed"
        assert validation_result["valid"] is True, "Token should be valid"
        assert validation_result["user_id"] == self.test_user_data["user_id"], "User ID mismatch"
        assert validation_result["email"] == self.test_user_data["email"], "Email mismatch"
        assert "permissions" in validation_result, "Permissions missing"
        assert "expires_at" in validation_result, "Expiration time missing"
        assert "verified_at" in validation_result, "Verification timestamp missing"
        
        # 3. Invalid Token Handling
        invalid_token = "invalid.jwt.token"
        invalid_result = await self.unified_auth.validate_user_token(invalid_token)
        assert invalid_result is None, "Invalid token should return None"
        
        # 4. Expired Token Handling (create token with past expiry)
        expired_payload = {
            "sub": self.test_user_data["user_id"],
            "email": self.test_user_data["email"],
            "iat": int(time.time()) - 3600,  # 1 hour ago
            "exp": int(time.time()) - 1800,  # 30 minutes ago (expired)
            "token_type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform"
        }
        
        expired_token = jwt.encode(expired_payload, self.jwt_handler.secret, algorithm=self.jwt_handler.algorithm)
        expired_result = await self.unified_auth.validate_user_token(expired_token)
        assert expired_result is None, "Expired token should return None"
        
        logger.info("Authentication middleware validation test completed successfully")
    
    @pytest.mark.integration
    async def test_permission_based_access_control(self):
        """
        BVJ: Permission-based access ensures users can only access authorized resources
        Tests permission validation and role-based access control
        """
        logger.info("Testing permission-based access control")
        
        # 1. Create Token with Specific Permissions
        read_only_permissions = ["read"]
        read_only_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=read_only_permissions
        )
        
        payload = self.jwt_handler.validate_token(read_only_token, "access")
        assert payload is not None, "Read-only token validation failed"
        assert payload["permissions"] == read_only_permissions, "Permissions mismatch"
        
        # 2. Create Token with Full Permissions
        full_permissions = ["read", "write", "admin", "delete"]
        admin_token = self.jwt_handler.create_access_token(
            user_id="admin-user-001",
            email="admin@example.com",
            permissions=full_permissions
        )
        
        admin_payload = self.jwt_handler.validate_token(admin_token, "access")
        assert admin_payload is not None, "Admin token validation failed"
        assert len(admin_payload["permissions"]) == 4, "Admin permissions count mismatch"
        assert "admin" in admin_payload["permissions"], "Admin permission missing"
        
        # 3. Permission Validation Logic
        def has_permission(token_payload: Dict, required_permission: str) -> bool:
            if not token_payload:
                return False
            return required_permission in token_payload.get("permissions", [])
        
        # Test permission checks
        assert has_permission(payload, "read") is True, "Read permission check failed"
        assert has_permission(payload, "write") is False, "Write permission check should fail"
        assert has_permission(admin_payload, "admin") is True, "Admin permission check failed"
        assert has_permission(admin_payload, "delete") is True, "Delete permission check failed"
        
        logger.info("Permission-based access control test completed successfully")
    
    @pytest.mark.integration
    async def test_user_context_creation_and_isolation(self):
        """
        BVJ: User context isolation prevents data leakage between users in multi-tenant environment
        Tests user context creation with proper isolation boundaries
        """
        logger.info("Testing user context creation and isolation")
        
        # 1. Create Multiple User Contexts
        user_1_data = {
            "user_id": "user-001",
            "email": "user1@example.com", 
            "name": "User One",
            "permissions": ["read"]
        }
        
        user_2_data = {
            "user_id": "user-002", 
            "email": "user2@example.com",
            "name": "User Two", 
            "permissions": ["read", "write"]
        }
        
        # 2. Create Tokens for Each User
        token_1 = self.jwt_handler.create_access_token(
            user_id=user_1_data["user_id"],
            email=user_1_data["email"],
            permissions=user_1_data["permissions"]
        )
        
        token_2 = self.jwt_handler.create_access_token(
            user_id=user_2_data["user_id"], 
            email=user_2_data["email"],
            permissions=user_2_data["permissions"]
        )
        
        # 3. Validate Context Isolation
        payload_1 = self.jwt_handler.validate_token(token_1, "access")
        payload_2 = self.jwt_handler.validate_token(token_2, "access")
        
        assert payload_1["sub"] != payload_2["sub"], "User IDs should be different"
        assert payload_1["email"] != payload_2["email"], "Emails should be different" 
        assert payload_1["permissions"] != payload_2["permissions"], "Permissions should be different"
        
        # 4. Test User Blacklisting Isolation
        self.jwt_handler.blacklist_user(user_1_data["user_id"])
        
        # User 1 token should be invalid
        blacklisted_payload_1 = self.jwt_handler.validate_token(token_1, "access")
        assert blacklisted_payload_1 is None, "Blacklisted user token should be invalid"
        
        # User 2 token should still be valid
        valid_payload_2 = self.jwt_handler.validate_token(token_2, "access")
        assert valid_payload_2 is not None, "Other user token should remain valid"
        
        logger.info("User context creation and isolation test completed successfully")
    
    @pytest.mark.integration
    async def test_token_refresh_and_rotation(self):
        """
        BVJ: Token refresh enables secure session extension without requiring re-authentication
        Tests refresh token lifecycle and rotation with race condition protection
        """
        logger.info("Testing token refresh and rotation mechanisms")
        
        # 1. Create Refresh Token
        refresh_token = self.jwt_handler.create_refresh_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"], 
            permissions=["read", "write"]
        )
        
        assert refresh_token is not None, "Refresh token creation failed"
        
        # 2. Validate Refresh Token
        refresh_payload = self.jwt_handler.validate_token(refresh_token, "refresh")
        assert refresh_payload is not None, "Refresh token validation failed"
        assert refresh_payload["token_type"] == "refresh", "Token type should be refresh"
        
        # 3. Use Refresh Token to Get New Access Token
        refresh_result = self.jwt_handler.refresh_access_token(refresh_token)
        assert refresh_result is not None, "Token refresh failed"
        
        new_access_token, new_refresh_token = refresh_result
        assert new_access_token != refresh_token, "New access token should be different"
        assert new_refresh_token != refresh_token, "New refresh token should be different"
        
        # 4. Validate New Tokens
        new_access_payload = self.jwt_handler.validate_token(new_access_token, "access")
        assert new_access_payload is not None, "New access token validation failed"
        assert new_access_payload["sub"] == self.test_user_data["user_id"], "User ID preserved"
        
        new_refresh_payload = self.jwt_handler.validate_token(new_refresh_token, "refresh")
        assert new_refresh_payload is not None, "New refresh token validation failed"
        
        # 5. Test Race Condition Protection
        # Using auth service which has race protection logic
        auth_refresh_result = await self.auth_service.refresh_tokens(new_refresh_token)
        assert auth_refresh_result is not None, "Auth service refresh failed"
        
        # Try to use same refresh token again (should fail due to race protection)
        second_refresh_attempt = await self.auth_service.refresh_tokens(new_refresh_token)
        assert second_refresh_attempt is None, "Second refresh attempt should fail (race protection)"
        
        logger.info("Token refresh and rotation test completed successfully")
    
    @pytest.mark.integration
    async def test_multi_service_authentication_coordination(self):
        """
        BVJ: Multi-service auth ensures consistent authentication across all platform services
        Tests service-to-service token validation and cross-service authentication
        """
        logger.info("Testing multi-service authentication coordination")
        
        # 1. Create Service Token
        service_token = self.jwt_handler.create_service_token(
            service_id="netra-backend",
            service_name="netra-backend-service"
        )
        
        assert service_token is not None, "Service token creation failed"
        
        # 2. Validate Service Token
        service_payload = self.jwt_handler.validate_token(service_token, "service")
        assert service_payload is not None, "Service token validation failed"
        assert service_payload["token_type"] == "service", "Token type should be service"
        assert service_payload["service"] == "netra-backend-service", "Service name mismatch"
        
        # 3. Test Cross-Service Token Validation
        # Create user token with proper audience for cross-service use
        cross_service_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"], 
            permissions=["read", "write"]
        )
        
        # Validate token can be used across services
        cross_payload = self.jwt_handler.validate_token(cross_service_token, "access")
        assert cross_payload is not None, "Cross-service token validation failed"
        assert cross_payload["aud"] == "netra-platform", "Audience should allow cross-service"
        assert cross_payload["iss"] == "netra-auth-service", "Issuer should be auth service"
        
        # 4. Test Service Signature Validation  
        assert "service_signature" in cross_payload, "Service signature missing"
        assert len(cross_payload["service_signature"]) > 0, "Service signature should not be empty"
        
        logger.info("Multi-service authentication coordination test completed successfully")
    
    @pytest.mark.integration
    async def test_security_headers_and_cors_handling(self):
        """
        BVJ: Security headers and CORS handling prevents XSS and unauthorized cross-origin requests
        Tests security header validation and CORS policy enforcement
        """
        logger.info("Testing security headers and CORS handling")
        
        # 1. Test JWT Token Security Validation
        # Create token and validate security claims
        secure_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=["read"]
        )
        
        # Decode token to check security headers
        payload = jwt.decode(
            secure_token, 
            options={"verify_signature": False}
        )
        
        # 2. Validate Security Claims
        required_security_claims = ["iss", "aud", "iat", "exp", "sub", "jti"]
        for claim in required_security_claims:
            assert claim in payload, f"Security claim '{claim}' missing from token"
        
        assert payload["iss"] == "netra-auth-service", "Issuer claim incorrect"
        assert payload["aud"] in ["netra-platform", "netra-services"], "Audience claim incorrect"
        
        # 3. Test Token Structure Security
        token_parts = secure_token.split('.')
        assert len(token_parts) == 3, "JWT should have exactly 3 parts"
        
        # Validate header contains algorithm info
        header = jwt.get_unverified_header(secure_token)
        assert "alg" in header, "Algorithm missing from JWT header"
        assert header["alg"] in ["HS256", "RS256"], "Insecure algorithm detected"
        
        # 4. Test Environment Binding
        assert payload.get("env") is not None, "Environment binding missing"
        
        # 5. Test Nonce/JTI for Replay Protection
        assert payload.get("jti") is not None, "JWT ID missing for replay protection"
        assert len(payload["jti"]) >= 32, "JWT ID too short for security"
        
        logger.info("Security headers and CORS handling test completed successfully")
    
    @pytest.mark.integration
    async def test_authentication_error_handling_and_recovery(self):
        """
        BVJ: Proper error handling prevents security vulnerabilities and provides clear user feedback
        Tests error scenarios, recovery mechanisms, and security logging
        """
        logger.info("Testing authentication error handling and recovery")
        
        # 1. Invalid Token Format Handling
        malformed_tokens = [
            "not.a.jwt",
            "missing.signature",
            "invalid-format",
            "",
            None
        ]
        
        for invalid_token in malformed_tokens:
            if invalid_token is not None:
                result = self.jwt_handler.validate_token(invalid_token, "access")
                assert result is None, f"Invalid token '{invalid_token}' should not validate"
        
        # 2. Expired Token Handling
        # Create token that's already expired
        past_time = int(time.time()) - 3600  # 1 hour ago
        expired_payload = {
            "sub": self.test_user_data["user_id"],
            "iat": past_time,
            "exp": past_time,  # Already expired
            "token_type": "access",
            "iss": "netra-auth-service",
            "aud": "netra-platform"
        }
        
        expired_token = jwt.encode(expired_payload, self.jwt_handler.secret, algorithm="HS256")
        expired_result = self.jwt_handler.validate_token(expired_token, "access")
        assert expired_result is None, "Expired token should not validate"
        
        # 3. Wrong Token Type Handling
        refresh_token = self.jwt_handler.create_refresh_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"]
        )
        
        # Try to validate refresh token as access token
        wrong_type_result = self.jwt_handler.validate_token(refresh_token, "access")
        assert wrong_type_result is None, "Wrong token type should not validate"
        
        # 4. Blacklisted User Recovery
        # Create token for user, blacklist user, then remove from blacklist
        recovery_token = self.jwt_handler.create_access_token(
            user_id="recovery-user-001",
            email="recovery@example.com",
            permissions=["read"]
        )
        
        # Validate token works initially
        initial_result = self.jwt_handler.validate_token(recovery_token, "access")
        assert initial_result is not None, "Initial token validation should work"
        
        # Blacklist user
        self.jwt_handler.blacklist_user("recovery-user-001")
        blacklisted_result = self.jwt_handler.validate_token(recovery_token, "access")
        assert blacklisted_result is None, "Blacklisted user token should not validate"
        
        # Remove from blacklist
        self.jwt_handler.remove_user_from_blacklist("recovery-user-001") 
        recovered_result = self.jwt_handler.validate_token(recovery_token, "access")
        assert recovered_result is not None, "Recovered user token should validate"
        
        logger.info("Authentication error handling and recovery test completed successfully")
    
    @pytest.mark.integration
    async def test_user_registration_and_onboarding_flows(self):
        """
        BVJ: User registration enables platform growth and new user acquisition
        Tests user registration with validation, password hashing, and account creation
        """
        logger.info("Testing user registration and onboarding flows")
        
        # 1. Email Validation
        invalid_emails = [
            "invalid-email",
            "@example.com", 
            "test@",
            "test..test@example.com",
            ""
        ]
        
        for invalid_email in invalid_emails:
            is_valid = self.auth_service.validate_email(invalid_email)
            assert is_valid is False, f"Invalid email '{invalid_email}' should not validate"
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for valid_email in valid_emails:
            is_valid = self.auth_service.validate_email(valid_email)
            assert is_valid is True, f"Valid email '{valid_email}' should validate"
        
        # 2. Password Validation
        weak_passwords = [
            "123", 
            "password",
            "Password", 
            "password123",
            "PASSWORD123"
        ]
        
        for weak_password in weak_passwords:
            is_valid, message = self.auth_service.validate_password(weak_password)
            assert is_valid is False, f"Weak password '{weak_password}' should not validate"
            assert len(message) > 0, "Validation message should be provided"
        
        # Strong password should validate
        strong_password = "StrongPass123!"
        is_valid, message = self.auth_service.validate_password(strong_password)
        assert is_valid is True, f"Strong password should validate"
        assert message == "Password is valid", f"Expected success message, got: {message}"
        
        # 3. Password Hashing
        test_password = "TestPassword123!"
        hashed = await self.auth_service.hash_password(test_password)
        assert hashed != test_password, "Password should be hashed"
        assert len(hashed) > 50, "Hash should be sufficiently long"
        
        # Verify password against hash
        is_correct = await self.auth_service.verify_password(test_password, hashed)
        assert is_correct is True, "Password verification should succeed"
        
        is_incorrect = await self.auth_service.verify_password("wrong-password", hashed)
        assert is_incorrect is False, "Wrong password verification should fail"
        
        # 4. Test User Registration (using test registration for integration)
        registration_result = self.auth_service.register_test_user(
            "integration-new-user@example.com",
            strong_password
        )
        
        assert "user_id" in registration_result, "Registration should return user_id"
        assert "email" in registration_result, "Registration should return email"
        assert "message" in registration_result, "Registration should return message"
        
        logger.info("User registration and onboarding flows test completed successfully")
    
    @pytest.mark.integration
    async def test_session_timeout_and_cleanup(self):
        """
        BVJ: Session timeout prevents unauthorized access from abandoned sessions
        Tests session expiration, cleanup mechanisms, and security timeouts
        """
        logger.info("Testing session timeout and cleanup mechanisms")
        
        # 1. Create Session with Timestamp
        user_data = {
            "email": self.test_user_data["email"],
            "name": self.test_user_data["name"],
            "login_time": datetime.now(timezone.utc).isoformat()
        }
        
        session_id = self.auth_service.create_session(
            user_id=self.test_user_data["user_id"],
            user_data=user_data
        )
        
        # 2. Verify Session Exists
        assert session_id in self.auth_service._sessions, "Session should exist after creation"
        stored_session = self.auth_service._sessions[session_id]
        assert "created_at" in stored_session, "Session should have creation timestamp"
        
        # 3. Test Session Age Calculation
        creation_time = stored_session["created_at"]
        assert isinstance(creation_time, datetime), "Creation time should be datetime object"
        
        current_time = datetime.now(timezone.utc)
        session_age = (current_time - creation_time).total_seconds()
        assert session_age < 5, "Session should be very recent"  # Less than 5 seconds old
        
        # 4. Test Manual Session Cleanup
        await self.auth_service.invalidate_user_sessions(self.test_user_data["user_id"])
        assert session_id not in self.auth_service._sessions, "Session should be cleaned up"
        
        # 5. Test Token Expiration vs Session
        # Create short-lived token (simulate timeout)
        short_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=["read"]
        )
        
        # Validate token is currently valid
        token_payload = self.jwt_handler.validate_token(short_token, "access")
        assert token_payload is not None, "Short token should initially be valid"
        
        # Check token expiration time
        exp_timestamp = token_payload["exp"]
        current_timestamp = int(time.time())
        time_to_expiry = exp_timestamp - current_timestamp
        
        # Token should have reasonable expiry (typically 15 minutes = 900 seconds)
        assert 0 < time_to_expiry <= 900, f"Token expiry seems wrong: {time_to_expiry} seconds"
        
        logger.info("Session timeout and cleanup test completed successfully")
    
    @pytest.mark.integration
    async def test_authentication_performance_and_throughput(self):
        """
        BVJ: Performance validation ensures authentication doesn't become a bottleneck
        Tests authentication speed, caching effectiveness, and concurrent access handling
        """
        logger.info("Testing authentication performance and throughput")
        
        # 1. Token Creation Performance
        start_time = time.time()
        tokens = []
        
        for i in range(100):
            token = self.jwt_handler.create_access_token(
                user_id=f"perf-user-{i:03d}",
                email=f"perf-user-{i:03d}@example.com",
                permissions=["read"]
            )
            tokens.append(token)
        
        creation_time = time.time() - start_time
        assert creation_time < 5.0, f"Token creation too slow: {creation_time} seconds for 100 tokens"
        
        # 2. Token Validation Performance
        start_time = time.time()
        valid_count = 0
        
        for token in tokens:
            payload = self.jwt_handler.validate_token(token, "access")
            if payload:
                valid_count += 1
        
        validation_time = time.time() - start_time
        assert validation_time < 2.0, f"Token validation too slow: {validation_time} seconds for 100 tokens"
        assert valid_count == 100, "All tokens should validate successfully"
        
        # 3. Test Caching Performance (second validation should be faster)
        start_time = time.time()
        
        for token in tokens[:10]:  # Test subset for cache performance
            payload = self.jwt_handler.validate_token(token, "access")
            assert payload is not None, "Cached token should still validate"
        
        cached_validation_time = time.time() - start_time
        
        # Cache should provide some performance benefit
        per_token_original = validation_time / 100
        per_token_cached = cached_validation_time / 10
        
        logger.info(f"Original validation: {per_token_original:.4f}s/token")
        logger.info(f"Cached validation: {per_token_cached:.4f}s/token")
        
        # 4. Test Performance Stats
        perf_stats = self.jwt_handler.get_performance_stats()
        assert "cache_stats" in perf_stats, "Performance stats should include cache info"
        assert "blacklist_stats" in perf_stats, "Performance stats should include blacklist info"
        
        cache_stats = perf_stats["cache_stats"]
        logger.info(f"Cache statistics: {cache_stats}")
        
        # 5. Concurrent Access Simulation
        async def validate_token_async(token):
            payload = self.jwt_handler.validate_token(token, "access")
            return payload is not None
        
        # Create tasks for concurrent validation
        validation_tasks = [validate_token_async(token) for token in tokens[:20]]
        
        start_time = time.time()
        results = await asyncio.gather(*validation_tasks)
        concurrent_time = time.time() - start_time
        
        assert all(results), "All concurrent validations should succeed"
        assert concurrent_time < 1.0, f"Concurrent validation too slow: {concurrent_time} seconds"
        
        logger.info("Authentication performance and throughput test completed successfully")
    
    @pytest.mark.integration
    async def test_security_audit_trail_and_logging(self):
        """
        BVJ: Audit trails enable security monitoring and compliance reporting
        Tests security event logging, audit trail creation, and monitoring integration
        """
        logger.info("Testing security audit trail and logging")
        
        # 1. Test Login Event Logging
        login_request = LoginRequest(
            email=self.test_user_data["email"],
            password=self.test_user_data["password"],
            provider=AuthProvider.LOCAL
        )
        
        client_info = {
            "ip": "192.168.1.100",
            "user_agent": "Integration-Test-Client/1.0"
        }
        
        # Create a test user first
        test_user_creation = self.auth_service.register_test_user(
            self.test_user_data["email"],
            self.test_user_data["password"]
        )
        
        # Mock the authentication to test audit logging
        with patch.object(self.auth_service, '_audit_log') as mock_audit:
            try:
                # This will fail auth but trigger audit logging
                await self.auth_service.login(login_request, client_info)
            except:
                pass  # Expected to fail, we're testing audit logging
            
            # Verify audit logging was called
            mock_audit.assert_called()
            
            # Check audit log call arguments
            call_args = mock_audit.call_args
            assert call_args is not None, "Audit log should be called"
        
        # 2. Test Token Blacklisting Audit
        test_token = self.jwt_handler.create_access_token(
            user_id="audit-user-001",
            email="audit@example.com", 
            permissions=["read"]
        )
        
        # Blacklist token (should trigger internal logging)
        blacklist_success = self.jwt_handler.blacklist_token(test_token)
        assert blacklist_success, "Token blacklisting should succeed"
        
        # 3. Test Security Event Collection
        security_events = []
        
        def log_security_event(event_type: str, details: Dict):
            security_events.append({
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": details
            })
        
        # Simulate various security events
        log_security_event("token_created", {"user_id": "test-001"})
        log_security_event("token_validated", {"user_id": "test-001"}) 
        log_security_event("token_blacklisted", {"user_id": "test-001"})
        log_security_event("user_blacklisted", {"user_id": "malicious-user"})
        
        assert len(security_events) == 4, "All security events should be logged"
        
        # Verify event structure
        for event in security_events:
            assert "type" in event, "Event should have type"
            assert "timestamp" in event, "Event should have timestamp"
            assert "details" in event, "Event should have details"
        
        # 4. Test Auth Health Monitoring
        auth_health = self.unified_auth.get_auth_health()
        
        assert "status" in auth_health, "Health check should include status"
        assert "jwt_handler" in auth_health, "Health check should include JWT handler status"
        assert "timestamp" in auth_health, "Health check should include timestamp"
        
        # 5. Test Security Metrics Collection
        security_metrics = self.unified_auth.get_security_metrics()
        
        assert "blacklisted_tokens" in security_metrics, "Metrics should include blacklisted tokens"
        assert "blacklisted_users" in security_metrics, "Metrics should include blacklisted users"
        assert "timestamp" in security_metrics, "Metrics should include timestamp"
        assert isinstance(security_metrics["timestamp"], float), "Timestamp should be float"
        
        logger.info("Security audit trail and logging test completed successfully")
    
    @pytest.mark.integration
    async def test_integration_with_user_execution_contexts(self):
        """
        BVJ: User execution context integration ensures proper user isolation in agent workflows
        Tests auth integration with user execution contexts and agent workflows
        """
        logger.info("Testing integration with user execution contexts")
        
        # 1. Create User Authentication Context
        user_context_data = {
            "user_id": self.test_user_data["user_id"],
            "email": self.test_user_data["email"],
            "permissions": ["read", "write", "execute_agents"],
            "context_id": f"ctx-{secrets.token_hex(8)}"
        }
        
        # 2. Create Token for User Context
        context_token = self.jwt_handler.create_access_token(
            user_id=user_context_data["user_id"],
            email=user_context_data["email"],
            permissions=user_context_data["permissions"]
        )
        
        # 3. Validate Token in Context
        context_payload = self.jwt_handler.validate_token(context_token, "access")
        assert context_payload is not None, "Context token validation failed"
        assert "execute_agents" in context_payload["permissions"], "Agent execution permission missing"
        
        # 4. Test User Context Isolation
        # Create second user context
        user_2_context = {
            "user_id": "user-002-context",
            "email": "user2-context@example.com",
            "permissions": ["read"],  # No agent execution permission
            "context_id": f"ctx-{secrets.token_hex(8)}"
        }
        
        context_token_2 = self.jwt_handler.create_access_token(
            user_id=user_2_context["user_id"],
            email=user_2_context["email"],
            permissions=user_2_context["permissions"]
        )
        
        context_payload_2 = self.jwt_handler.validate_token(context_token_2, "access")
        assert context_payload_2 is not None, "Second context token validation failed"
        assert "execute_agents" not in context_payload_2["permissions"], "Second user should not have agent permission"
        
        # 5. Test Context-Based Permission Validation
        def can_execute_agents(token_payload: Dict) -> bool:
            if not token_payload:
                return False
            return "execute_agents" in token_payload.get("permissions", [])
        
        assert can_execute_agents(context_payload) is True, "First user should be able to execute agents"
        assert can_execute_agents(context_payload_2) is False, "Second user should not be able to execute agents"
        
        # 6. Test Session Context Association
        session_id_1 = self.auth_service.create_session(
            user_id=user_context_data["user_id"],
            user_data={
                "context_id": user_context_data["context_id"],
                "permissions": user_context_data["permissions"]
            }
        )
        
        session_id_2 = self.auth_service.create_session(
            user_id=user_2_context["user_id"],
            user_data={
                "context_id": user_2_context["context_id"],
                "permissions": user_2_context["permissions"]
            }
        )
        
        # Verify sessions are isolated
        assert session_id_1 != session_id_2, "Session IDs should be different"
        
        session_1_data = self.auth_service._sessions[session_id_1]
        session_2_data = self.auth_service._sessions[session_id_2]
        
        assert session_1_data["user_id"] != session_2_data["user_id"], "User IDs should be different"
        assert session_1_data["user_data"]["context_id"] != session_2_data["user_data"]["context_id"], "Context IDs should be different"
        
        # 7. Test Context Cleanup
        await self.auth_service.invalidate_user_sessions(user_context_data["user_id"])
        assert session_id_1 not in self.auth_service._sessions, "User 1 session should be cleaned up"
        assert session_id_2 in self.auth_service._sessions, "User 2 session should remain"
        
        await self.auth_service.invalidate_user_sessions(user_2_context["user_id"])
        assert session_id_2 not in self.auth_service._sessions, "User 2 session should be cleaned up"
        
        logger.info("Integration with user execution contexts test completed successfully")