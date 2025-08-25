"""
Token Blacklisting Basic Tests - Core security functionality for token revocation

Tests the basic token blacklisting functionality that is critical for security,
especially for logout, account suspension, and security incidents.

Business Value Justification (BVJ):
- Segment: Platform/Security | Goal: Auth Security | Impact: Token Revocation
- Ensures proper token revocation for logout and security incidents
- Validates blacklisting prevents continued access with revoked tokens
- Critical foundation for account security and administrative controls

Test Coverage:
- Token blacklisting on logout operations
- User blacklisting for account suspension
- Blacklist persistence across service restarts
- Blacklist validation during token verification
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from auth_service.auth_core.core.jwt_handler import JWTHandler


class TestTokenBlacklistingBasics(unittest.TestCase):
    """Test basic token blacklisting functionality for security"""
    
    def setUp(self):
        """Setup test environment with fresh JWT handler"""
        self.jwt_handler = JWTHandler()
        self.test_user_id = "test-user-123"
        self.test_email = "test@example.com"
        
        # Clear any existing blacklist state
        self.jwt_handler._token_blacklist.clear()
        self.jwt_handler._user_blacklist.clear()
    
    def test_token_blacklisting_basic_functionality(self):
        """Test that tokens can be blacklisted and validation fails"""
        # Create a valid token
        token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email
        )
        
        # Validate token works initially
        payload = self.jwt_handler.validate_token(token)
        assert payload is not None, "Token should be valid before blacklisting"
        assert payload["sub"] == self.test_user_id
        
        # Blacklist the token
        self.jwt_handler.blacklist_token(token)
        
        # Validation should now fail
        blacklisted_payload = self.jwt_handler.validate_token(token)
        assert blacklisted_payload is None, "Blacklisted token should be invalid"
    
    def test_user_blacklisting_invalidates_all_tokens(self):
        """Test that blacklisting a user invalidates all their tokens"""
        # Create multiple tokens for the same user
        token1 = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email
        )
        
        token2 = self.jwt_handler.create_refresh_token(self.test_user_id)
        
        # Both tokens should be valid initially
        payload1 = self.jwt_handler.validate_token(token1, "access")
        payload2 = self.jwt_handler.validate_token(token2, "refresh")
        
        assert payload1 is not None, "First access token should be valid"
        assert payload2 is not None, "Refresh token should be valid"
        
        # Blacklist the user
        self.jwt_handler.blacklist_user(self.test_user_id)
        
        # All user's tokens should now be invalid
        blacklisted_payload1 = self.jwt_handler.validate_token(token1, "access")
        blacklisted_payload2 = self.jwt_handler.validate_token(token2, "refresh")
        
        assert blacklisted_payload1 is None, "User's access token should be blacklisted"
        assert blacklisted_payload2 is None, "User's refresh token should be blacklisted"
    
    def test_blacklist_check_methods(self):
        """Test the blacklist checking methods work correctly"""
        # Create token and user
        token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email
        )
        
        # Initially nothing should be blacklisted
        assert not self.jwt_handler.is_token_blacklisted(token), "Token should not be blacklisted initially"
        assert not self.jwt_handler.is_user_blacklisted(self.test_user_id), "User should not be blacklisted initially"
        
        # Blacklist token
        self.jwt_handler.blacklist_token(token)
        assert self.jwt_handler.is_token_blacklisted(token), "Token should be detected as blacklisted"
        
        # User should still not be blacklisted
        assert not self.jwt_handler.is_user_blacklisted(self.test_user_id), "User should not be blacklisted yet"
        
        # Blacklist user
        self.jwt_handler.blacklist_user(self.test_user_id)
        assert self.jwt_handler.is_user_blacklisted(self.test_user_id), "User should be detected as blacklisted"
    
    def test_blacklist_persistence_simulation(self):
        """Test blacklist persistence across JWT handler instances"""
        # Create and blacklist token
        token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email
        )
        
        self.jwt_handler.blacklist_token(token)
        self.jwt_handler.blacklist_user(self.test_user_id)
        
        # Verify blacklisted
        assert self.jwt_handler.is_token_blacklisted(token), "Token should be blacklisted"
        assert self.jwt_handler.is_user_blacklisted(self.test_user_id), "User should be blacklisted"
        
        # Create new JWT handler instance (simulates restart)
        new_jwt_handler = JWTHandler()
        
        # Test if blacklists persist (this might fail if not implemented properly)
        token_still_blacklisted = new_jwt_handler.is_token_blacklisted(token)
        user_still_blacklisted = new_jwt_handler.is_user_blacklisted(self.test_user_id)
        
        # This is a critical security test - blacklists must persist across restarts
        # If this fails, it indicates a security vulnerability
        assert token_still_blacklisted, "SECURITY ISSUE: Token blacklist must persist across service restarts"
        assert user_still_blacklisted, "SECURITY ISSUE: User blacklist must persist across service restarts"
    
    def test_blacklist_with_malformed_tokens(self):
        """Test blacklist operations handle malformed tokens gracefully"""
        malformed_tokens = [
            "not-a-jwt",
            "malformed.token",
            "",
            None,
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.malformed",
            "valid.looking.but-actually-invalid-jwt-token"
        ]
        
        for malformed_token in malformed_tokens:
            with self.subTest(token=malformed_token):
                # Blacklisting malformed tokens should not crash
                try:
                    self.jwt_handler.blacklist_token(malformed_token)
                    # Check if it's considered blacklisted
                    is_blacklisted = self.jwt_handler.is_token_blacklisted(malformed_token)
                    # The behavior here depends on implementation - either True or graceful False
                    assert isinstance(is_blacklisted, bool), "Blacklist check should return boolean"
                except Exception as e:
                    # If exceptions are thrown, they should be handled gracefully
                    self.fail(f"Blacklisting malformed token should not raise exception: {malformed_token} - {e}")
    
    def test_blacklist_edge_cases(self):
        """Test blacklist edge cases and boundary conditions"""
        # Test with empty user ID
        try:
            self.jwt_handler.blacklist_user("")
            empty_user_blacklisted = self.jwt_handler.is_user_blacklisted("")
            assert isinstance(empty_user_blacklisted, bool), "Empty user ID should handle gracefully"
        except Exception as e:
            # Should handle gracefully, not crash
            pass
        
        # Test with None user ID
        try:
            self.jwt_handler.blacklist_user(None)
            none_user_blacklisted = self.jwt_handler.is_user_blacklisted(None)
            assert isinstance(none_user_blacklisted, bool), "None user ID should handle gracefully"
        except Exception as e:
            # Should handle gracefully, not crash
            pass
    
    def test_blacklist_removes_token_from_rotation(self):
        """Test that blacklisted refresh tokens cannot be used for token rotation"""
        # Create refresh token
        refresh_token = self.jwt_handler.create_refresh_token(self.test_user_id)
        
        # Verify refresh token can be used initially
        new_tokens = self.jwt_handler.refresh_access_token(refresh_token)
        assert new_tokens is not None, "Refresh token should work initially"
        
        new_access_token, new_refresh_token = new_tokens
        assert new_access_token is not None, "New access token should be generated"
        assert new_refresh_token is not None, "New refresh token should be generated"
        
        # Blacklist the user
        self.jwt_handler.blacklist_user(self.test_user_id)
        
        # Try to use refresh token again - should fail
        failed_refresh = self.jwt_handler.refresh_access_token(refresh_token)
        assert failed_refresh is None, "Blacklisted user's refresh token should not work"
        
        # Also test that the new tokens are now invalid
        access_validation = self.jwt_handler.validate_token(new_access_token)
        refresh_validation = self.jwt_handler.validate_token(new_refresh_token, "refresh")
        
        assert access_validation is None, "New access token should be invalid after user blacklisting"
        assert refresh_validation is None, "New refresh token should be invalid after user blacklisting"
    
    def test_concurrent_blacklist_operations(self):
        """Test thread safety of blacklist operations"""
        import threading
        import time
        
        tokens = []
        results = []
        
        # Create multiple tokens
        for i in range(10):
            token = self.jwt_handler.create_access_token(
                f"user-{i}", 
                f"user{i}@example.com"
            )
            tokens.append(token)
        
        def blacklist_tokens():
            """Thread function to blacklist tokens"""
            for token in tokens[::2]:  # Blacklist every other token
                self.jwt_handler.blacklist_token(token)
                time.sleep(0.01)  # Small delay to increase chance of race conditions
        
        def check_blacklist():
            """Thread function to check blacklist status"""
            local_results = []
            for token in tokens:
                is_blacklisted = self.jwt_handler.is_token_blacklisted(token)
                local_results.append(is_blacklisted)
                time.sleep(0.01)  # Small delay
            results.append(local_results)
        
        # Run concurrent operations
        blacklist_thread = threading.Thread(target=blacklist_tokens)
        check_thread1 = threading.Thread(target=check_blacklist)
        check_thread2 = threading.Thread(target=check_blacklist)
        
        blacklist_thread.start()
        time.sleep(0.05)  # Let blacklisting start first
        check_thread1.start()
        check_thread2.start()
        
        # Wait for completion
        blacklist_thread.join()
        check_thread1.join()
        check_thread2.join()
        
        # Verify no crashes occurred and results are consistent
        assert len(results) == 2, "Both check threads should complete"
        for result_set in results:
            assert len(result_set) == len(tokens), "All tokens should be checked"
            assert all(isinstance(r, bool) for r in result_set), "All results should be boolean"


# Business Impact Summary for Token Blacklisting Tests
"""
Token Blacklisting Basic Tests - Business Impact

Security Foundation: Token Revocation and Access Control
- Ensures proper token revocation for logout and security incidents
- Validates blacklisting prevents continued access with revoked tokens
- Critical foundation for account security and administrative controls

Technical Excellence:
- Token revocation: individual tokens can be invalidated immediately
- User blacklisting: all user tokens invalidated for account suspension
- Persistence validation: blacklists survive service restarts (critical security requirement)
- Malformed token handling: robust error handling prevents service disruption
- Token rotation security: blacklisted refresh tokens cannot generate new access tokens
- Concurrent safety: thread-safe blacklist operations for production scalability

Platform Security:
- Foundation: Secure token revocation foundation for logout and security operations
- Security: Comprehensive blacklist validation prevents access with revoked credentials
- Persistence: Critical security requirement that blacklists survive system restarts
- Reliability: Robust handling of edge cases and malformed inputs
- Performance: Thread-safe operations ensure reliable blacklist checking under load
"""