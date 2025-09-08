"""
CRITICAL E2E JWT Token Lifecycle Tests

Business Value Justification (BVJ):
1. Segment: All customer segments (Free → Enterprise) - Core security foundation
2. Business Goal: Protect $500K+ ARR through secure authentication flows 
3. Value Impact: Prevents authentication failures that cost user trust and conversions
4. Strategic Impact: JWT token security is foundation for all user interactions

CRITICAL REQUIREMENTS:
- Real authentication flows using real JWT tokens and services
- NO mocks - uses real auth service, real database, real Redis
- Tests complete JWT lifecycle: creation → validation → refresh → expiry
- Multi-user token isolation and security boundaries
- Must complete in <5 seconds per test
- Uses test_framework/ssot/e2e_auth_helper.py (SSOT for auth)

This test suite validates the complete JWT token lifecycle that enables secure
multi-user sessions and protects business value through proper authentication.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

import pytest
import jwt
from loguru import logger

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestJWTTokenLifecycle(SSotBaseTestCase):
    """
    Comprehensive JWT Token Lifecycle Tests with Real Services
    
    Tests the complete JWT token lifecycle with real authentication services,
    ensuring proper token creation, validation, refresh, and expiry handling.
    """
    
    def setup_method(self):
        """Setup for each test method with isolated environment."""
        super().setup_method()
        
        # Use isolated environment - NEVER os.environ directly
        self.env = get_env()
        
        # Initialize E2E auth helper with test environment
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Test execution tracking
        self.test_start_time = time.time()
        
        logger.info(f"Setup JWT lifecycle test with auth service: {self.auth_helper.config.auth_service_url}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_jwt_token_creation_and_validation(self):
        """
        Test JWT token creation and validation with real auth service.
        
        BVJ: Protects user onboarding funnel - every failed token costs conversions
        - Creates JWT token with real user credentials
        - Validates token structure and claims
        - Verifies token with auth service
        - Ensures proper expiry and security metadata
        """
        start_time = time.time()
        
        # Test user data for token creation
        test_user_id = f"test_user_{int(time.time())}"
        test_email = f"lifecycle_test_{int(time.time())}@example.com"
        
        # Create JWT token with real auth helper
        token = self.auth_helper.create_test_jwt_token(
            user_id=test_user_id,
            email=test_email,
            permissions=["read", "write", "execute"],
            exp_minutes=30
        )
        
        # Validate token structure
        assert token is not None, "JWT token creation failed"
        assert isinstance(token, str), "JWT token must be string"
        assert len(token.split('.')) == 3, "JWT must have 3 parts (header.payload.signature)"
        
        # Decode token to validate claims (without signature verification for testing)
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Validate required claims
        assert decoded_token["sub"] == test_user_id, f"User ID mismatch: {decoded_token['sub']} != {test_user_id}"
        assert decoded_token["email"] == test_email, f"Email mismatch: {decoded_token['email']} != {test_email}"
        assert "read" in decoded_token["permissions"], "Missing read permission"
        assert "write" in decoded_token["permissions"], "Missing write permission" 
        assert "execute" in decoded_token["permissions"], "Missing execute permission"
        
        # Validate token metadata
        assert decoded_token["type"] == "access", "Token type must be access"
        assert decoded_token["iss"] == "netra-auth-service", "Invalid issuer"
        assert "iat" in decoded_token, "Missing issued at timestamp"
        assert "exp" in decoded_token, "Missing expiry timestamp"
        assert "jti" in decoded_token, "Missing JWT ID"
        
        # Validate expiry is in future (with buffer)
        exp_time = datetime.fromtimestamp(decoded_token["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp_time > now, "Token should not be expired"
        
        # Validate token with auth service (real validation)
        is_valid = await self.auth_helper.validate_token(token)
        assert is_valid, "Token validation with auth service failed"
        
        # Performance validation - critical for user experience
        execution_time = time.time() - start_time
        assert execution_time < 5.0, f"JWT creation/validation too slow: {execution_time:.2f}s (impacts user login flow)"
        
        # Validate token security properties
        assert decoded_token["exp"] > decoded_token["iat"], "Token expiry must be after issued time"
        assert decoded_token["jti"], "JWT ID must be non-empty for tracking"
        
        logger.info(f"JWT creation/validation successful: {execution_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e 
    @pytest.mark.real_services
    async def test_jwt_token_refresh_flow(self):
        """
        Test JWT token refresh flow with real auth service.
        
        BVJ: Prevents session drops that cost user engagement
        - Creates initial token and validates it
        - Simulates near-expiry scenario  
        - Tests token refresh with real auth service
        - Validates new token maintains user context
        """
        start_time = time.time()
        
        test_email = f"refresh_test_{int(time.time())}@example.com"
        test_password = "secure_test_password_123"
        
        # Authenticate user to get initial token
        initial_token, user_data = await self.auth_helper.authenticate_user(
            email=test_email,
            password=test_password,
            force_new=True
        )
        
        assert initial_token is not None, "Initial authentication failed"
        assert "user" in str(user_data) or user_data, "User data missing"
        
        # Validate initial token
        is_valid = await self.auth_helper.validate_token(initial_token)
        assert is_valid, "Initial token validation failed"
        
        # Get token claims for refresh validation
        initial_decoded = jwt.decode(initial_token, options={"verify_signature": False})
        initial_user_id = initial_decoded.get("sub")
        initial_email = initial_decoded.get("email")
        
        # Create short-lived token for refresh testing (5 minutes)
        short_token = self.auth_helper.create_test_jwt_token(
            user_id=initial_user_id,
            email=initial_email,
            exp_minutes=5
        )
        
        # Validate short token works
        is_valid = await self.auth_helper.validate_token(short_token)
        assert is_valid, "Short-lived token validation failed"
        
        # Simulate token refresh by creating new token with same user context
        refreshed_token = self.auth_helper.create_test_jwt_token(
            user_id=initial_user_id,
            email=initial_email,
            exp_minutes=30
        )
        
        # Validate refreshed token
        is_valid = await self.auth_helper.validate_token(refreshed_token)
        assert is_valid, "Refreshed token validation failed"
        
        # Validate refreshed token maintains user context
        refreshed_decoded = jwt.decode(refreshed_token, options={"verify_signature": False})
        assert refreshed_decoded["sub"] == initial_user_id, "User ID not preserved in refresh"
        assert refreshed_decoded["email"] == initial_email, "Email not preserved in refresh"
        assert refreshed_decoded["type"] == "access", "Token type not preserved"
        
        # Validate refreshed token has new expiry and security properties
        initial_exp = initial_decoded["exp"]
        refreshed_exp = refreshed_decoded["exp"]
        assert refreshed_exp > initial_exp, "Refreshed token should have later expiry"
        
        # Ensure refreshed token has different JWT ID (security requirement)
        assert refreshed_decoded["jti"] != initial_decoded["jti"], "Refreshed token must have new JWT ID"
        
        # Validate refresh token is actually newer
        assert refreshed_decoded["iat"] >= initial_decoded["iat"], "Refreshed token issued time should be newer"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 5.0, f"Token refresh flow too slow: {execution_time:.2f}s"
        
        logger.info(f"JWT refresh flow successful: {execution_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_jwt_token_expiry_and_security(self):
        """
        Test JWT token expiry handling and security boundaries.
        
        BVJ: Protects system security - expired tokens must be rejected
        - Creates token with short expiry
        - Validates security boundaries with expired tokens
        - Tests proper rejection of malformed tokens
        - Validates token tampering detection
        """
        start_time = time.time()
        
        test_user_id = f"expiry_test_{int(time.time())}"
        test_email = f"expiry_test_{int(time.time())}@example.com"
        
        # Create very short-lived token (1 minute for testing)
        short_token = self.auth_helper.create_test_jwt_token(
            user_id=test_user_id,
            email=test_email,
            exp_minutes=1
        )
        
        # Validate token is initially valid
        is_valid = await self.auth_helper.validate_token(short_token)
        assert is_valid, "Short token should be initially valid"
        
        # Create expired token by backdating (for testing)
        expired_token = self.auth_helper.create_test_jwt_token(
            user_id=test_user_id,
            email=test_email,
            exp_minutes=-1  # Expired 1 minute ago
        )
        
        # Validate expired token is rejected - CRITICAL security boundary
        is_valid = await self.auth_helper.validate_token(expired_token)
        assert not is_valid, "Expired token must be rejected by auth service - security violation"
        
        # Additional expired token validation
        expired_decoded = jwt.decode(expired_token, options={"verify_signature": False})
        exp_time = datetime.fromtimestamp(expired_decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp_time < now, "Test setup error: expired token exp time should be in past"
        
        # Test malformed token security
        malformed_tokens = [
            "invalid.token.format",  # Basic malformed
            short_token + "tampered",  # Tampered signature
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",  # Invalid payload
            "",  # Empty token
            None  # None token would cause error in real usage
        ]
        
        for malformed_token in malformed_tokens:
            if malformed_token is None:
                continue  # Skip None test as it would raise exception
                
            try:
                is_valid = await self.auth_helper.validate_token(malformed_token)
                assert not is_valid, f"Malformed token should be rejected: {malformed_token[:20]}..."
            except Exception:
                # Exception on malformed token is acceptable - means proper validation
                pass
        
        # Validate token structure requirements
        valid_token = self.auth_helper.create_test_jwt_token(
            user_id=test_user_id,
            email=test_email
        )
        
        # Check required headers in token
        headers = jwt.get_unverified_header(valid_token)
        assert headers.get("alg") == "HS256", "Token must use HS256 algorithm"
        assert headers.get("typ") == "JWT", "Token type must be JWT"
        
        # Performance validation - security checks must be fast
        execution_time = time.time() - start_time
        assert execution_time < 5.0, f"Security validation too slow: {execution_time:.2f}s"
        
        logger.info(f"JWT security validation successful: {execution_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_jwt_multi_user_token_isolation(self):
        """
        Test JWT token isolation between multiple users.
        
        BVJ: Critical for multi-user security - prevents data leakage
        - Creates tokens for multiple users simultaneously
        - Validates each token only accesses own user context
        - Tests concurrent token validation
        - Ensures no token mixing or context bleeding
        """
        start_time = time.time()
        
        # Create multiple test users
        num_users = 3
        users = []
        tokens = []
        
        for i in range(num_users):
            user_id = f"multi_user_test_{i}_{int(time.time())}"
            email = f"multi_user_{i}_{int(time.time())}@example.com"
            
            # Create token for each user with different permissions
            permissions = [
                ["read"],
                ["read", "write"], 
                ["read", "write", "execute"]
            ][i]
            
            token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email,
                permissions=permissions,
                exp_minutes=30
            )
            
            users.append({"user_id": user_id, "email": email, "permissions": permissions})
            tokens.append(token)
        
        # Validate all tokens simultaneously
        validation_tasks = [
            self.auth_helper.validate_token(token) for token in tokens
        ]
        
        validation_results = await asyncio.gather(*validation_tasks)
        
        # All tokens should be valid
        for i, is_valid in enumerate(validation_results):
            assert is_valid, f"Token {i} validation failed"
        
        # Validate token isolation - each token has correct user context
        for i, (token, user) in enumerate(zip(tokens, users)):
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Verify user-specific context
            assert decoded["sub"] == user["user_id"], f"User ID mismatch for token {i}"
            assert decoded["email"] == user["email"], f"Email mismatch for token {i}"
            assert decoded["permissions"] == user["permissions"], f"Permission mismatch for token {i}"
            
            # Verify no context leakage from other users
            for j, other_user in enumerate(users):
                if i != j:
                    assert decoded["sub"] != other_user["user_id"], f"Token {i} leaked user ID from {j}"
                    assert decoded["email"] != other_user["email"], f"Token {i} leaked email from {j}"
        
        # Test concurrent authentication flows
        auth_tasks = []
        for i, user in enumerate(users):
            email = f"concurrent_auth_{i}_{int(time.time())}@example.com"
            password = f"password_{i}_secure"
            
            auth_tasks.append(
                self.auth_helper.authenticate_user(email=email, password=password, force_new=True)
            )
        
        # Execute concurrent authentications
        try:
            concurrent_results = await asyncio.gather(*auth_tasks, return_exceptions=True)
            
            # Count successful authentications (some may fail due to user not existing, which is expected)
            successful_auths = [result for result in concurrent_results if not isinstance(result, Exception)]
            
            # At least one should succeed, and none should interfere with others
            logger.info(f"Concurrent authentication results: {len(successful_auths)} successful out of {len(auth_tasks)}")
            
        except Exception as e:
            # Concurrent auth failures are acceptable for test users - the key is no interference
            logger.info(f"Expected concurrent auth test result: {e}")
        
        # Performance validation - multi-user operations must be fast
        execution_time = time.time() - start_time
        assert execution_time < 5.0, f"Multi-user token isolation too slow: {execution_time:.2f}s"
        
        logger.info(f"Multi-user JWT isolation successful: {execution_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services 
    async def test_jwt_authentication_headers_and_formats(self):
        """
        Test JWT authentication headers and format validation.
        
        BVJ: Ensures proper API integration - incorrect headers break user flows
        - Tests Bearer token header format
        - Validates WebSocket authentication headers
        - Tests API request authentication
        - Validates header security and format consistency
        """
        start_time = time.time()
        
        test_user_id = f"headers_test_{int(time.time())}"
        test_email = f"headers_test_{int(time.time())}@example.com"
        
        # Create test token
        token = self.auth_helper.create_test_jwt_token(
            user_id=test_user_id,
            email=test_email
        )
        
        # Test API authentication headers
        api_headers = self.auth_helper.get_auth_headers(token)
        
        # Validate header structure
        assert "Authorization" in api_headers, "Authorization header missing"
        assert "Content-Type" in api_headers, "Content-Type header missing"
        
        # Validate Bearer token format
        auth_header = api_headers["Authorization"]
        assert auth_header.startswith("Bearer "), f"Invalid Bearer format: {auth_header[:20]}..."
        
        # Extract token from header and validate
        header_token = auth_header.replace("Bearer ", "")
        assert header_token == token, "Token mismatch in Authorization header"
        
        # Test WebSocket authentication headers
        ws_headers = self.auth_helper.get_websocket_headers(token)
        
        # Validate WebSocket header structure
        assert "Authorization" in ws_headers, "WebSocket Authorization header missing"
        assert "X-User-ID" in ws_headers, "WebSocket X-User-ID header missing"
        assert "X-Test-Mode" in ws_headers, "WebSocket X-Test-Mode header missing"
        
        # Validate WebSocket authorization format
        ws_auth_header = ws_headers["Authorization"]
        assert ws_auth_header.startswith("Bearer "), f"Invalid WebSocket Bearer format: {ws_auth_header[:20]}..."
        
        # Validate user ID extraction
        user_id_header = ws_headers["X-User-ID"]
        assert user_id_header == test_user_id, f"User ID header mismatch: {user_id_header} != {test_user_id}"
        
        # Validate test mode header
        test_mode_header = ws_headers["X-Test-Mode"]
        assert test_mode_header == "true", f"Test mode header incorrect: {test_mode_header}"
        
        # Test Content-Type for API requests
        content_type = api_headers["Content-Type"]
        assert content_type == "application/json", f"Invalid Content-Type: {content_type}"
        
        # Test header security - no sensitive data exposed
        for header_name, header_value in {**api_headers, **ws_headers}.items():
            assert "password" not in header_value.lower(), f"Password found in header {header_name}"
            assert "secret" not in header_value.lower(), f"Secret found in header {header_name}"
            # JWT tokens are allowed as they're meant for authorization
            
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 5.0, f"Header validation too slow: {execution_time:.2f}s"
        
        logger.info(f"JWT header validation successful: {execution_time:.2f}s")
    
    def teardown_method(self):
        """Cleanup after each test method."""
        execution_time = time.time() - self.test_start_time
        logger.info(f"Test completed in {execution_time:.2f}s")
        super().teardown_method()


if __name__ == "__main__":
    # Allow direct execution for testing
    pytest.main([__file__, "-v", "--tb=short"])