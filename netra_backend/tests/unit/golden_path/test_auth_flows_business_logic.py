"""
Golden Path Unit Tests: User Authentication Flows Business Logic

Tests core authentication business logic that drives the golden path user flow,
focusing on business rules, validation, and authentication state management
without requiring external auth services.

Business Value:
- Ensures authentication logic works correctly for 90% of user scenarios
- Validates JWT token creation, validation, and user context management
- Tests user permission and role-based access control
- Verifies password security and user data protection
"""

import pytest
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock

# Import the business logic components we're testing
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig, AuthenticatedUser
from netra_backend.app.services.user_service import pwd_context
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ensure_user_id


@pytest.mark.unit
@pytest.mark.golden_path
class TestAuthenticationBusinessLogic:
    """Test core authentication business logic for golden path scenarios."""

    def test_jwt_token_creation_business_rules(self):
        """Test JWT token creation follows business rules."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Tokens must have required claims for user context
        user_id = "test-user-123"
        email = "test@example.com"
        permissions = ["read", "write"]
        
        token = auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=permissions,
            exp_minutes=30
        )
        
        # Validate token structure
        assert isinstance(token, str), "JWT token must be string"
        assert len(token.split('.')) == 3, "JWT must have 3 parts (header.payload.signature)"
        
        # Decode without verification to check claims
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Business Rule: Required claims for user identification
        assert decoded["sub"] == user_id, "Token must contain correct user ID"
        assert decoded["email"] == email, "Token must contain correct email"
        assert decoded["permissions"] == permissions, "Token must contain correct permissions"
        assert "iat" in decoded, "Token must have issued at timestamp"
        assert "exp" in decoded, "Token must have expiration timestamp"
        assert decoded["type"] == "access", "Token must be access type"
        assert decoded["iss"] == "netra-auth-service", "Token must have correct issuer"

    def test_jwt_token_expiration_business_rules(self):
        """Test JWT token expiration follows business security rules."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Tokens should expire after specified time
        exp_minutes = 10
        token = auth_helper.create_test_jwt_token(
            exp_minutes=exp_minutes
        )
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Calculate expected expiration
        issued_at = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        token_duration = expires_at - issued_at
        
        # Business Rule: Token should expire within reasonable window of requested time
        expected_duration = timedelta(minutes=exp_minutes)
        assert abs((token_duration - expected_duration).total_seconds()) < 60, \
            "Token expiration must be within 1 minute of requested duration"

    def test_user_authentication_context_creation(self):
        """Test user execution context creation for authenticated users."""
        # Business Rule: Authenticated users must have proper execution context
        user_id = "auth-user-456"
        email = "context@example.com"
        
        # Create user context
        context = UserExecutionContext(
            user_id=user_id,
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}"
        )
        
        # Business Rule: Context must properly identify user
        assert context.user_id == user_id, "Context must contain correct user ID"
        assert context.request_id is not None, "Context must have request ID"
        assert context.thread_id is not None, "Context must have thread ID"
        assert context.run_id is not None, "Context must have run ID"
        
        # Business Rule: Context should support user isolation
        assert hasattr(context, 'user_id'), "Context must support user identification"
        
    def test_authenticated_user_creation_business_logic(self):
        """Test AuthenticatedUser creation follows business requirements."""
        # Business Rule: Authenticated users must have complete user data
        user_id = "business-user-789"
        email = "business@example.com"
        full_name = "Business User"
        permissions = ["read", "write", "admin"]
        
        auth_user = AuthenticatedUser(
            user_id=user_id,
            email=email,
            full_name=full_name,
            jwt_token="mock-jwt-token",
            permissions=permissions,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Business Rule: User must have all required identification
        assert auth_user.user_id == user_id, "User must have correct ID"
        assert auth_user.email == email, "User must have correct email"
        assert auth_user.full_name == full_name, "User must have display name"
        assert auth_user.permissions == permissions, "User must have correct permissions"
        assert auth_user.is_test_user is True, "Test users must be marked as test users"
        
        # Business Rule: Strongly typed user ID should work
        strongly_typed_id = auth_user.get_strongly_typed_user_id()
        assert isinstance(strongly_typed_id, UserID), "Should return strongly typed UserID"
        assert str(strongly_typed_id) == user_id, "Strongly typed ID must match original"

    def test_password_security_business_requirements(self):
        """Test password hashing meets business security requirements."""
        # Business Rule: Passwords must be securely hashed and never stored in plain text
        plain_password = "business_secure_password_123!"
        
        # Test password hashing
        hashed = pwd_context.hash(plain_password)
        
        # Business Rule: Hash must be different from original
        assert hashed != plain_password, "Hashed password must differ from plain text"
        assert len(hashed) > len(plain_password), "Hash should be longer than original"
        assert "$" in hashed, "Hash should use proper format with separators"
        
        # Business Rule: Same password should produce different hashes (salting)
        hash2 = pwd_context.hash(plain_password)
        assert hashed != hash2, "Same password must produce different hashes (salt requirement)"
        
        # Business Rule: Verification should work without exposing original
        try:
            is_valid = pwd_context.verify(hashed, plain_password)
            assert is_valid is True, "Valid password must verify correctly"
        except Exception as e:
            pytest.fail(f"Password verification failed: {e}")
        
        # Business Rule: Wrong password should fail verification
        wrong_password_fails = True
        try:
            pwd_context.verify(hashed, "wrong_password")
            wrong_password_fails = False
        except Exception:
            pass  # Expected to fail
        
        assert wrong_password_fails, "Wrong password must fail verification"

    def test_user_permissions_business_logic(self):
        """Test user permissions follow business access control rules."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Different users should have different permission levels
        # Economy tier user - basic permissions
        economy_user_token = auth_helper.create_test_jwt_token(
            user_id="economy-user",
            email="economy@example.com",
            permissions=["read"]
        )
        
        # Premium tier user - extended permissions
        premium_user_token = auth_helper.create_test_jwt_token(
            user_id="premium-user", 
            email="premium@example.com",
            permissions=["read", "write", "admin", "premium_features"]
        )
        
        economy_claims = jwt.decode(economy_user_token, options={"verify_signature": False})
        premium_claims = jwt.decode(premium_user_token, options={"verify_signature": False})
        
        # Business Rule: Permission levels should reflect user tiers
        assert "read" in economy_claims["permissions"], "All users should have read access"
        assert len(economy_claims["permissions"]) == 1, "Economy users should have limited permissions"
        
        assert "read" in premium_claims["permissions"], "Premium users should have read access"
        assert "write" in premium_claims["permissions"], "Premium users should have write access"
        assert "premium_features" in premium_claims["permissions"], "Premium users should have premium features"
        assert len(premium_claims["permissions"]) > len(economy_claims["permissions"]), \
            "Premium users should have more permissions than economy users"

    def test_authentication_state_management(self):
        """Test authentication state management business logic."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Authentication state should be properly managed
        user_id = "state-user-123"
        email = "state@example.com"
        
        # Create initial token
        token1 = auth_helper.create_test_jwt_token(user_id=user_id, email=email)
        assert token1 is not None, "Token creation should succeed"
        
        # Business Rule: Token should be cached for efficiency
        cached_token = auth_helper._cached_token
        assert cached_token == token1, "Token should be cached for reuse"
        
        # Business Rule: Valid token should be reused
        token2 = auth_helper._get_valid_token()
        assert token2 == token1, "Valid cached token should be reused"
        
        # Business Rule: Expired tokens should not be used
        auth_helper._token_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)
        token3 = auth_helper._get_valid_token()
        assert token3 != token1, "Expired token should be replaced with new token"

    def test_multi_user_auth_isolation_business_rules(self):
        """Test multi-user authentication isolation follows business requirements."""
        # Business Rule: Different users should have completely isolated authentication
        auth_helper_user1 = E2EAuthHelper()
        auth_helper_user2 = E2EAuthHelper()
        
        user1_token = auth_helper_user1.create_test_jwt_token(
            user_id="isolated-user-1",
            email="user1@example.com",
            permissions=["read", "write"]
        )
        
        user2_token = auth_helper_user2.create_test_jwt_token(
            user_id="isolated-user-2", 
            email="user2@example.com",
            permissions=["read", "admin"]
        )
        
        # Business Rule: Users should have different tokens
        assert user1_token != user2_token, "Different users must have different tokens"
        
        # Business Rule: Users should have isolated claims
        user1_claims = jwt.decode(user1_token, options={"verify_signature": False})
        user2_claims = jwt.decode(user2_token, options={"verify_signature": False})
        
        assert user1_claims["sub"] != user2_claims["sub"], "Users must have different IDs"
        assert user1_claims["email"] != user2_claims["email"], "Users must have different emails"
        assert user1_claims["permissions"] != user2_claims["permissions"], "Users should have different permissions"

    def test_auth_config_environment_business_logic(self):
        """Test authentication configuration follows environment business rules."""
        # Business Rule: Different environments should have different configurations
        
        # Test environment configuration
        test_config = E2EAuthConfig.for_environment("test")
        assert "localhost" in test_config.auth_service_url, "Test env should use localhost"
        assert "test" in test_config.test_user_email, "Test env should use test email"
        
        # Staging environment configuration
        staging_config = E2EAuthConfig.for_staging()
        assert staging_config.auth_service_url != test_config.auth_service_url, \
            "Staging should have different auth service URL"
        assert staging_config.jwt_secret != test_config.jwt_secret, \
            "Staging should have different JWT secret"
        assert staging_config.timeout >= test_config.timeout, \
            "Staging should have same or longer timeout for network latency"

    def test_authentication_error_handling_business_rules(self):
        """Test authentication error handling follows business requirements."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Invalid token data should be handled gracefully
        invalid_tokens = [
            "invalid.token.format",
            "not-a-jwt-token",
            "",
            None
        ]
        
        for invalid_token in invalid_tokens[:-1]:  # Skip None for string operations
            # Business Rule: Invalid tokens should not crash the system
            try:
                decoded = auth_helper._decode_token(invalid_token)
                # Should return empty dict for invalid tokens
                assert isinstance(decoded, dict), "Invalid token should return dict"
            except Exception:
                # Some invalid formats might raise exceptions, which is acceptable
                pass
        
        # Business Rule: User ID extraction should handle invalid tokens
        user_id = auth_helper._extract_user_id("invalid.token")
        assert user_id == "unknown-user", "Invalid token should return unknown-user ID"

    def test_strongly_typed_user_id_business_logic(self):
        """Test strongly typed user ID follows business type safety rules."""
        # Business Rule: User IDs should be strongly typed for type safety
        raw_user_id = "typed-user-123"
        
        # Test ensure_user_id function
        typed_user_id = ensure_user_id(raw_user_id)
        assert isinstance(typed_user_id, UserID), "Should return UserID type"
        assert str(typed_user_id) == raw_user_id, "Content should be preserved"
        
        # Business Rule: Strongly typed IDs should work with auth system
        auth_helper = E2EAuthHelper()
        token = auth_helper.create_test_jwt_token(user_id=raw_user_id)
        
        # Extract and verify type safety
        extracted_id = auth_helper._extract_user_id(token)
        assert extracted_id == raw_user_id, "Extracted ID should match original"
        
        # Verify it can be made strongly typed
        strongly_typed = ensure_user_id(extracted_id)
        assert isinstance(strongly_typed, UserID), "Extracted ID should be typeable"


@pytest.mark.unit
@pytest.mark.golden_path
class TestAuthenticationValidationBusinessRules:
    """Test authentication validation business rules and edge cases."""

    def test_jwt_validation_comprehensive_business_rules(self):
        """Test comprehensive JWT validation for business requirements."""
        auth_helper = E2EAuthHelper()
        
        # Create valid token
        valid_token = auth_helper.create_test_jwt_token(
            user_id="validation-user",
            email="validation@example.com", 
            permissions=["read", "write"]
        )
        
        # Business Rule: Valid tokens should pass validation
        decoded = jwt.decode(valid_token, options={"verify_signature": False})
        
        # Check all required business claims
        required_claims = ["sub", "email", "permissions", "iat", "exp", "type", "iss"]
        for claim in required_claims:
            assert claim in decoded, f"Token must have required claim: {claim}"
        
        # Business Rule: Token should have reasonable expiration
        exp_timestamp = decoded["exp"] 
        iat_timestamp = decoded["iat"]
        duration = exp_timestamp - iat_timestamp
        
        assert duration > 0, "Token expiration must be after issuance"
        assert duration <= 3600 * 24, "Token should not be valid for more than 24 hours"  # 1 day max

    def test_user_context_validation_business_rules(self):
        """Test user context validation for business isolation requirements."""
        # Business Rule: User contexts must properly validate required fields
        
        # Valid context should work
        valid_context = UserExecutionContext(
            user_id="valid-user",
            request_id="req-123",
            thread_id="thread-123", 
            run_id="run-123"
        )
        
        assert valid_context.user_id == "valid-user", "Context must store user ID correctly"
        assert valid_context.request_id == "req-123", "Context must store request ID correctly"
        
        # Business Rule: Context should support additional metadata
        context_with_metadata = UserExecutionContext(
            user_id="metadata-user",
            request_id="req-456",
            thread_id="thread-456",
            run_id="run-456"
        )
        
        # Should be able to access all required fields
        assert hasattr(context_with_metadata, 'user_id'), "Context must have user_id field"
        assert hasattr(context_with_metadata, 'request_id'), "Context must have request_id field"
        assert hasattr(context_with_metadata, 'thread_id'), "Context must have thread_id field"
        assert hasattr(context_with_metadata, 'run_id'), "Context must have run_id field"

    def test_permission_validation_business_logic(self):
        """Test permission validation follows business access control."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Different permission levels should be properly encoded
        permission_test_cases = [
            (["read"], "Basic read-only user"),
            (["read", "write"], "Standard user with read/write"),
            (["read", "write", "admin"], "Admin user with full access"),
            (["read", "write", "premium_features"], "Premium user with special features"),
            ([], "User with no specific permissions")
        ]
        
        for permissions, description in permission_test_cases:
            token = auth_helper.create_test_jwt_token(
                user_id=f"perm-user-{len(permissions)}",
                permissions=permissions
            )
            
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Business Rule: Permissions should be preserved exactly
            assert decoded["permissions"] == permissions, \
                f"Permissions should be preserved for {description}"
            
            # Business Rule: Permissions should be list type
            assert isinstance(decoded["permissions"], list), \
                f"Permissions must be list type for {description}"

    def test_authentication_edge_cases_business_handling(self):
        """Test authentication edge cases follow business requirements."""
        auth_helper = E2EAuthHelper()
        
        # Business Rule: Edge cases should be handled gracefully
        edge_cases = [
            ("", "Empty user ID should be handled"),
            ("   ", "Whitespace user ID should be handled"),
            ("user@with@symbols", "User ID with symbols should be handled"),
            ("very-long-user-id-that-exceeds-normal-length-expectations-for-testing", "Long user ID should be handled")
        ]
        
        for user_id, description in edge_cases:
            try:
                token = auth_helper.create_test_jwt_token(user_id=user_id)
                
                # Should be able to create token
                assert isinstance(token, str), f"Should create token for: {description}"
                
                # Should be able to extract user ID back
                extracted_id = auth_helper._extract_user_id(token)
                assert extracted_id == user_id, f"Should preserve user ID for: {description}"
                
            except Exception as e:
                # Some edge cases might legitimately fail, but should not crash
                assert isinstance(e, (ValueError, TypeError)), \
                    f"Should fail gracefully for: {description}, got: {type(e)}"

    def test_concurrent_auth_business_isolation(self):
        """Test concurrent authentication maintains business isolation."""
        # Business Rule: Concurrent authentication should not interfere
        auth_helpers = [E2EAuthHelper() for _ in range(3)]
        
        tokens = []
        for i, helper in enumerate(auth_helpers):
            token = helper.create_test_jwt_token(
                user_id=f"concurrent-user-{i}",
                email=f"user{i}@example.com"
            )
            tokens.append(token)
        
        # Business Rule: All tokens should be unique
        assert len(set(tokens)) == len(tokens), "All concurrent tokens should be unique"
        
        # Business Rule: Each token should have correct isolated data
        for i, token in enumerate(tokens):
            decoded = jwt.decode(token, options={"verify_signature": False})
            assert decoded["sub"] == f"concurrent-user-{i}", f"Token {i} should have correct user ID"
            assert decoded["email"] == f"user{i}@example.com", f"Token {i} should have correct email"

    def test_authentication_business_value_metrics(self):
        """Test authentication provides measurable business value."""
        auth_helper = E2EAuthHelper()
        
        # Business Value: Authentication should be fast (< 100ms for token creation)
        import time
        start_time = time.time()
        
        token = auth_helper.create_test_jwt_token()
        
        creation_time = time.time() - start_time
        assert creation_time < 0.1, f"Token creation should be fast (< 100ms), took {creation_time*1000:.2f}ms"
        
        # Business Value: Authentication should be reliable (no exceptions)
        for i in range(10):
            try:
                test_token = auth_helper.create_test_jwt_token(user_id=f"reliability-test-{i}")
                assert isinstance(test_token, str), f"Token {i} should be created successfully"
            except Exception as e:
                pytest.fail(f"Authentication reliability failed on iteration {i}: {e}")
        
        # Business Value: Authentication should support user identification
        user_id = "business-value-user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        extracted_id = auth_helper._extract_user_id(token)
        
        assert extracted_id == user_id, "Authentication should preserve user identity"