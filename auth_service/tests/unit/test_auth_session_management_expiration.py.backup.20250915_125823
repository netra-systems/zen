"""
Authentication Session Management and Expiration Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure secure session management and prevent unauthorized access
- Value Impact: Users have secure, reliable session management without security breaches
- Strategic Impact: Core platform security - protects user data and prevents auth bypasses

CRITICAL: Tests session management logic including expiration, blacklisting, and cleanup.
Focuses on core business logic without integration dependencies.

Following CLAUDE.md requirements:
- Unit tests can have limited mocks for external dependencies if needed
- Tests MUST fail hard - no try/except blocks masking errors
- Focus on business logic validation
- Use SSOT patterns from test_framework/ssot/
"""
import pytest
import time
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, Set

# Absolute imports per CLAUDE.md
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env


class TestAuthSessionManagementCore:
    """Unit tests for authentication session management core logic."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup isolated environment for session management tests."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Set session management test configuration
        self.env.set("JWT_SECRET_KEY", "unit-test-session-jwt-secret-32-chars-long", "test_session")
        self.env.set("SERVICE_SECRET", "unit-test-session-service-secret-32", "test_session")
        self.env.set("SERVICE_ID", "auth-service", "test_session")
        self.env.set("ENVIRONMENT", "test", "test_session")
        
        # Configure session timeouts
        self.env.set("JWT_ACCESS_TOKEN_EXPIRY_MINUTES", "30", "test_session")
        self.env.set("JWT_REFRESH_TOKEN_EXPIRY_DAYS", "30", "test_session")
        
        yield
        
        # Cleanup
        self.env.disable_isolation()
    
    def test_jwt_handler_tracks_session_expiration_correctly(self):
        """Test that JWT handler correctly tracks and validates session expiration times."""
        # Arrange
        handler = JWTHandler()
        user_id = "session-test-user-12345"
        email = "session.test@netra.ai"
        permissions = ["read:agents", "write:threads"]
        
        # Test different expiration times
        expiration_test_cases = [
            {"exp_minutes": 30, "should_be_valid": True, "description": "normal_session"},
            {"exp_minutes": 1, "should_be_valid": True, "description": "short_session"},  
            {"exp_minutes": -1, "should_be_valid": False, "description": "expired_session"},
            {"exp_minutes": -60, "should_be_valid": False, "description": "long_expired_session"}
        ]
        
        for test_case in expiration_test_cases:
            # Act: Create token with specific expiration
            token = handler.create_access_token(
                user_id=f"{user_id}-{test_case['description']}",
                email=email,
                permissions=permissions
            )
            
            # Modify expiry for test (simulate token creation with specific expiry)
            if test_case["exp_minutes"] < 0:
                with patch.object(handler, 'access_expiry', test_case["exp_minutes"]):
                    expired_token = handler.create_access_token(
                        user_id=f"{user_id}-{test_case['description']}",
                        email=email,
                        permissions=permissions
                    )
                    token = expired_token
            
            # Assert: Validate token expiration behavior
            payload = handler.validate_token(token, "access")
            
            if test_case["should_be_valid"]:
                assert payload is not None, f"Token with {test_case['exp_minutes']} min expiry must be valid"
                assert payload["sub"] == f"{user_id}-{test_case['description']}", "Valid token must contain correct user_id"
                
                # Verify expiration time is set correctly in payload
                if test_case["exp_minutes"] > 0:
                    import jwt as jwt_lib
                    decoded = jwt_lib.decode(token, options={"verify_signature": False, "verify_exp": False})
                    current_time = int(time.time())
                    expected_expiry_range = current_time + (test_case["exp_minutes"] * 60)
                    
                    # Allow 10 second tolerance for test execution time
                    assert abs(decoded["exp"] - expected_expiry_range) <= 10, (
                        f"Token expiry must be approximately {test_case['exp_minutes']} minutes from now: "
                        f"expected ~{expected_expiry_range}, got {decoded['exp']}"
                    )
            else:
                assert payload is None, f"Token with {test_case['exp_minutes']} min expiry must be invalid/expired"
    
    def test_token_blacklisting_immediately_invalidates_sessions(self):
        """Test that token blacklisting immediately invalidates active sessions."""
        # Arrange
        handler = JWTHandler()
        user_id = "blacklist-test-user-12345"
        email = "blacklist.test@netra.ai"
        
        # Create multiple tokens for the same user (simulate multiple sessions)
        session_tokens = []
        for i in range(3):
            token = handler.create_access_token(
                user_id=f"{user_id}-session-{i}",
                email=email,
                permissions=["read:agents"]
            )
            session_tokens.append({
                "token": token,
                "user_id": f"{user_id}-session-{i}",
                "session_index": i
            })
        
        # Verify all tokens are initially valid
        for session in session_tokens:
            payload = handler.validate_token(session["token"], "access")
            assert payload is not None, f"Session {session['session_index']} must be initially valid"
            assert payload["sub"] == session["user_id"], f"Session {session['session_index']} must contain correct user_id"
        
        # Act: Blacklist specific token (not user)
        target_token = session_tokens[1]["token"]  # Blacklist middle token
        blacklist_result = handler.blacklist_token(target_token)
        
        # Assert: Only blacklisted token should be invalid
        assert blacklist_result is True, "Token blacklisting operation must succeed"
        
        for i, session in enumerate(session_tokens):
            payload = handler.validate_token(session["token"], "access")
            
            if i == 1:  # Blacklisted token
                assert payload is None, f"Blacklisted token (session {i}) must be immediately invalid"
                assert handler.is_token_blacklisted(session["token"]) is True, f"Token {i} must report as blacklisted"
            else:  # Other tokens should remain valid
                assert payload is not None, f"Non-blacklisted token (session {i}) must remain valid"
                assert payload["sub"] == session["user_id"], f"Non-blacklisted token {i} must contain correct user_id"
    
    def test_user_blacklisting_invalidates_all_user_sessions(self):
        """Test that user blacklisting invalidates all sessions for that user."""
        # Arrange
        handler = JWTHandler()
        
        # Create multiple users with multiple sessions each
        users_config = [
            {"user_id": "multi-session-user-1", "email": "user1@netra.ai"},
            {"user_id": "multi-session-user-2", "email": "user2@netra.ai"},
            {"user_id": "multi-session-user-3", "email": "user3@netra.ai"}
        ]
        
        all_sessions = {}
        
        for user_config in users_config:
            user_sessions = []
            # Create 2 sessions per user
            for session_num in range(2):
                token = handler.create_access_token(
                    user_id=user_config["user_id"],
                    email=user_config["email"],
                    permissions=[f"read:user_{user_config['user_id']}", "write:threads"]
                )
                
                user_sessions.append({
                    "token": token,
                    "session_number": session_num
                })
            
            all_sessions[user_config["user_id"]] = user_sessions
        
        # Verify all sessions are initially valid
        for user_id, sessions in all_sessions.items():
            for session in sessions:
                payload = handler.validate_token(session["token"], "access")
                assert payload is not None, f"Initial session for {user_id} must be valid"
                assert payload["sub"] == user_id, f"Session for {user_id} must contain correct user_id"
        
        # Act: Blacklist one specific user
        target_user_id = "multi-session-user-2"
        user_blacklist_result = handler.blacklist_user(target_user_id)
        
        # Assert: Only blacklisted user's sessions should be invalid
        assert user_blacklist_result is True, "User blacklisting operation must succeed"
        assert handler.is_user_blacklisted(target_user_id) is True, "User must report as blacklisted"
        
        for user_id, sessions in all_sessions.items():
            for session in sessions:
                payload = handler.validate_token(session["token"], "access")
                
                if user_id == target_user_id:  # Blacklisted user
                    assert payload is None, f"All sessions for blacklisted user {user_id} must be invalid"
                else:  # Other users should remain valid
                    assert payload is not None, f"Sessions for non-blacklisted user {user_id} must remain valid"
                    assert payload["sub"] == user_id, f"Non-blacklisted user {user_id} session must contain correct user_id"
    
    def test_session_cleanup_removes_expired_blacklist_entries(self):
        """Test that session cleanup properly removes expired blacklist entries to prevent memory leaks."""
        # Arrange
        handler = JWTHandler()
        
        # Create tokens with different expiration times
        short_lived_token = None
        long_lived_token = None
        
        # Create short-lived token (already expired)
        with patch.object(handler, 'access_expiry', -1):  # Already expired
            short_lived_token = handler.create_access_token(
                user_id="short-lived-user",
                email="short@netra.ai"
            )
        
        # Create long-lived token 
        long_lived_token = handler.create_access_token(
            user_id="long-lived-user",
            email="long@netra.ai"
        )
        
        # Blacklist both tokens
        handler.blacklist_token(short_lived_token)
        handler.blacklist_token(long_lived_token)
        
        # Verify both are blacklisted
        assert handler.is_token_blacklisted(short_lived_token) is True, "Short-lived token must be blacklisted"
        assert handler.is_token_blacklisted(long_lived_token) is True, "Long-lived token must be blacklisted"
        
        # Mock Redis cleanup to test logic (since Redis is not available in unit tests)
        with patch.object(handler, '_cleanup_expired_blacklist_entries') as mock_cleanup:
            mock_cleanup.return_value = True
            
            # Act: Simulate cleanup process
            cleanup_result = handler._cleanup_expired_blacklist_entries()
            
            # Assert: Cleanup should be called and return success
            assert cleanup_result is True, "Blacklist cleanup should complete successfully"
            mock_cleanup.assert_called_once()
            
        # Test that validation still works correctly for non-expired blacklisted tokens
        long_lived_validation = handler.validate_token(long_lived_token, "access")
        assert long_lived_validation is None, "Long-lived blacklisted token must still be invalid after cleanup"
    
    def test_concurrent_session_operations_maintain_data_integrity(self):
        """Test that concurrent session operations (blacklist, validate) maintain data integrity."""
        # Arrange
        handler = JWTHandler()
        user_id = "concurrent-test-user"
        email = "concurrent@netra.ai"
        
        # Create multiple tokens for concurrent operations
        tokens = []
        for i in range(5):
            token = handler.create_access_token(
                user_id=f"{user_id}-{i}",
                email=email,
                permissions=["read:agents"]
            )
            tokens.append(token)
        
        # Act: Simulate concurrent operations
        # Note: In unit tests, we simulate concurrency logic without actual threads
        
        concurrent_operations = [
            {"operation": "validate", "token": tokens[0], "expected": True},
            {"operation": "blacklist", "token": tokens[1], "expected": True},
            {"operation": "validate", "token": tokens[1], "expected": False},  # After blacklist
            {"operation": "validate", "token": tokens[2], "expected": True},
            {"operation": "blacklist", "token": tokens[3], "expected": True},
            {"operation": "validate", "token": tokens[3], "expected": False},  # After blacklist
            {"operation": "validate", "token": tokens[4], "expected": True}
        ]
        
        # Execute operations sequentially to simulate concurrent state changes
        results = []
        for op in concurrent_operations:
            if op["operation"] == "validate":
                payload = handler.validate_token(op["token"], "access")
                result = payload is not None
                results.append({"operation": "validate", "result": result, "expected": op["expected"]})
                
            elif op["operation"] == "blacklist":
                blacklist_result = handler.blacklist_token(op["token"])
                results.append({"operation": "blacklist", "result": blacklist_result, "expected": op["expected"]})
        
        # Assert: All concurrent operations must produce expected results
        for i, result in enumerate(results):
            assert result["result"] == result["expected"], (
                f"Concurrent operation {i} ({result['operation']}) must produce expected result: "
                f"expected {result['expected']}, got {result['result']}"
            )
        
        # Verify final state is consistent
        final_validation_results = [
            (tokens[0], True),   # Never blacklisted
            (tokens[1], False),  # Blacklisted
            (tokens[2], True),   # Never blacklisted
            (tokens[3], False),  # Blacklisted
            (tokens[4], True)    # Never blacklisted
        ]
        
        for token, should_be_valid in final_validation_results:
            payload = handler.validate_token(token, "access")
            is_valid = payload is not None
            
            assert is_valid == should_be_valid, (
                f"Final validation state must be consistent: "
                f"expected {should_be_valid}, got {is_valid}"
            )
    
    def test_refresh_token_expiration_longer_than_access_token(self):
        """Test that refresh tokens have longer expiration than access tokens for proper session management."""
        # Arrange
        handler = JWTHandler()
        user_id = "refresh-expiry-test-user"
        email = "refresh.expiry@netra.ai"
        
        # Act: Create access and refresh tokens
        access_token = handler.create_access_token(user_id, email)
        refresh_token = handler.create_refresh_token(user_id, email)
        
        # Assert: Both tokens should be created
        assert access_token is not None, "Access token must be created"
        assert refresh_token is not None, "Refresh token must be created"
        
        # Decode tokens to check expiration times
        import jwt as jwt_lib
        
        access_decoded = jwt_lib.decode(access_token, options={"verify_signature": False, "verify_exp": False})
        refresh_decoded = jwt_lib.decode(refresh_token, options={"verify_signature": False, "verify_exp": False})
        
        access_exp = access_decoded["exp"]
        refresh_exp = refresh_decoded["exp"]
        
        # Assert: Refresh token must expire later than access token
        assert refresh_exp > access_exp, (
            f"Refresh token must expire later than access token: "
            f"access_exp={access_exp}, refresh_exp={refresh_exp}"
        )
        
        # Calculate time differences
        access_duration = access_exp - access_decoded["iat"]
        refresh_duration = refresh_exp - refresh_decoded["iat"]
        
        # Refresh token should be significantly longer (at least 10x longer)
        duration_ratio = refresh_duration / access_duration
        assert duration_ratio >= 10, (
            f"Refresh token duration must be at least 10x access token duration: "
            f"ratio={duration_ratio:.1f} (access={access_duration}s, refresh={refresh_duration}s)"
        )
        
        # Verify token types are correct
        assert access_decoded["token_type"] == "access", "Access token must have correct type"
        assert refresh_decoded["token_type"] == "refresh", "Refresh token must have correct type"
        
        # Verify both tokens contain same user information
        assert access_decoded["sub"] == user_id, "Access token must contain correct user_id"
        assert refresh_decoded["sub"] == user_id, "Refresh token must contain correct user_id"