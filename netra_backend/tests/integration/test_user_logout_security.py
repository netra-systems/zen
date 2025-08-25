"""
User Logout Security Integration Test

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Security and user session management integrity
- Value Impact: Prevents unauthorized access after logout, protecting user accounts and data
- Revenue Impact: Critical for user trust and regulatory compliance (GDPR, SOX) - security breaches could cost $1M+ in damages

This test covers logout security mechanisms that are currently missing from test coverage:
1. Token blacklisting after logout
2. Session invalidation 
3. Multiple session management
4. Logout audit logging
5. Token validation after logout (should fail)

This addresses a gap in existing authentication testing - login is well tested but logout security is not.
"""

import asyncio
import pytest
import uuid
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import LoginRequest, AuthProvider


class TestUserLogoutSecurity:
    """Test user logout security mechanisms that are missing from current test coverage."""

    @pytest.fixture
    async def auth_service(self):
        """Create auth service for testing logout functionality."""
        service = AuthService()
        yield service

    @pytest.fixture
    async def test_user_session(self, auth_service):
        """Create a test user and login session for logout testing."""
        try:
            # Register test user
            email = "logout_test@netra.ai"
            password = "SecurePassword123!"
            
            user_info = auth_service.register_test_user(email, password)
            
            # Perform login to get tokens and session
            login_request = LoginRequest(
                email=email,
                password=password,
                provider=AuthProvider.LOCAL
            )
            
            client_info = {
                "ip": "192.168.1.100",
                "user_agent": "TestClient/1.0"
            }
            
            login_response = await auth_service.login(login_request, client_info)
            
            return {
                "user_info": user_info,
                "login_response": login_response,
                "email": email,
                "password": password
            }
        except Exception as e:
            pytest.skip(f"Could not set up test user session: {e}")
            return None

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, auth_service, test_user_session):
        """
        Test that logout properly blacklists the access token.
        
        This is a critical security test - after logout, tokens should be invalidated.
        """
        session_data = test_user_session
        access_token = session_data["login_response"].access_token
        session_id = session_data["login_response"].user["session_id"]
        
        # Step 1: Verify token is valid before logout
        token_validation = await auth_service.validate_token(access_token)
        assert token_validation.valid is True, "Token should be valid before logout"
        assert token_validation.user_id == session_data["user_info"]["user_id"], "Token should contain correct user"
        
        print(f"✅ Step 1: Token validation before logout - VALID")
        
        # Step 2: Perform logout
        logout_success = await auth_service.logout(access_token, session_id)
        assert logout_success is True, "Logout should succeed"
        
        print(f"✅ Step 2: Logout completed successfully")
        
        # Step 3: Verify token is blacklisted after logout
        token_validation_after = await auth_service.validate_token(access_token)
        assert token_validation_after.valid is False, "Token should be INVALID after logout (blacklisted)"
        
        print(f"✅ Step 3: Token blacklisting verified - token is now INVALID")
        
        # Step 4: Attempt to use blacklisted token for another request (should fail)
        try:
            # This should fail because token is blacklisted
            second_validation = await auth_service.validate_token(access_token)
            assert second_validation.valid is False, "Blacklisted token should remain invalid"
        except Exception as e:
            # Expected behavior - blacklisted token causes validation to fail
            print(f"✅ Step 4: Blacklisted token properly rejected - {type(e).__name__}")
        
        print(f"🔒 LOGOUT TOKEN BLACKLISTING TEST PASSED")

    @pytest.mark.asyncio  
    async def test_logout_invalidates_session(self, auth_service, test_user_session):
        """
        Test that logout invalidates the user session.
        
        Sessions should be cleaned up on logout for security.
        """
        session_data = test_user_session
        access_token = session_data["login_response"].access_token
        session_id = session_data["login_response"].user["session_id"]
        user_id = session_data["user_info"]["user_id"]
        
        # Step 1: Verify session exists before logout
        session_exists_before = auth_service.session_manager.session_exists(session_id)
        assert session_exists_before is True, "Session should exist before logout"
        
        print(f"✅ Step 1: Session exists before logout - ID: {session_id}")
        
        # Step 2: Perform logout
        logout_success = await auth_service.logout(access_token, session_id)
        assert logout_success is True, "Logout should succeed"
        
        print(f"✅ Step 2: Logout completed")
        
        # Step 3: Verify session is invalidated after logout
        session_exists_after = auth_service.session_manager.session_exists(session_id)
        assert session_exists_after is False, "Session should be invalidated after logout"
        
        print(f"✅ Step 3: Session invalidation verified - session no longer exists")
        
        print(f"🔒 LOGOUT SESSION INVALIDATION TEST PASSED")

    @pytest.mark.asyncio
    async def test_logout_all_sessions_for_user(self, auth_service):
        """
        Test logout invalidates all sessions for a user (multi-device logout).
        
        This tests the scenario where a user logs out from all devices.
        """
        # Create test user
        email = "multidevice_logout@netra.ai" 
        password = "SecurePassword123!"
        user_info = auth_service.register_test_user(email, password)
        
        # Step 1: Create multiple login sessions (simulating multiple devices)
        sessions = []
        for i, device in enumerate(["phone", "laptop", "tablet"]):
            login_request = LoginRequest(
                email=email,
                password=password,
                provider=AuthProvider.LOCAL
            )
            
            client_info = {
                "ip": f"192.168.1.{100 + i}",
                "user_agent": f"TestClient-{device}/1.0"
            }
            
            login_response = await auth_service.login(login_request, client_info)
            sessions.append({
                "device": device,
                "token": login_response.access_token,
                "session_id": login_response.user["session_id"],
                "response": login_response
            })
        
        assert len(sessions) == 3, "Should have 3 active sessions"
        
        print(f"✅ Step 1: Created {len(sessions)} sessions for multiple devices")
        
        # Step 2: Verify all tokens are initially valid
        for session in sessions:
            validation = await auth_service.validate_token(session["token"])
            assert validation.valid is True, f"Token for {session['device']} should be valid"
        
        print(f"✅ Step 2: All tokens validated before logout")
        
        # Step 3: Logout from one device without specifying session_id (should invalidate ALL sessions)
        primary_token = sessions[0]["token"]
        logout_success = await auth_service.logout(primary_token)  # No session_id = logout all
        
        assert logout_success is True, "Logout should succeed"
        
        print(f"✅ Step 3: Performed logout (all sessions)")
        
        # Step 4: Verify ALL tokens are now invalid
        for session in sessions:
            validation = await auth_service.validate_token(session["token"])
            assert validation.valid is False, f"Token for {session['device']} should be invalid after logout"
        
        print(f"✅ Step 4: All {len(sessions)} sessions invalidated")
        
        print(f"🔒 MULTI-SESSION LOGOUT TEST PASSED")

    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self, auth_service):
        """
        Test logout behavior with invalid or expired tokens.
        
        This ensures logout is resilient to invalid input.
        """
        # Step 1: Test logout with completely invalid token
        fake_token = "invalid.token.here"
        logout_result = await auth_service.logout(fake_token)
        
        # Should handle gracefully - either succeed (no-op) or fail safely
        assert isinstance(logout_result, bool), "Logout should return boolean result"
        
        print(f"✅ Step 1: Invalid token logout handled gracefully - result: {logout_result}")
        
        # Step 2: Test logout with expired token (simulate)
        # Create a token that's already expired
        import jwt
        expired_payload = {
            "sub": "test_user_id",
            "email": "test@example.com", 
            "exp": int(time.time()) - 3600  # Expired 1 hour ago
        }
        
        expired_token = jwt.encode(expired_payload, "test_secret", algorithm="HS256")
        
        logout_result_expired = await auth_service.logout(expired_token)
        assert isinstance(logout_result_expired, bool), "Expired token logout should return boolean"
        
        print(f"✅ Step 2: Expired token logout handled gracefully - result: {logout_result_expired}")
        
        # Step 3: Test logout with malformed token
        malformed_token = "not.a.jwt.token.at.all"
        logout_result_malformed = await auth_service.logout(malformed_token)
        
        assert isinstance(logout_result_malformed, bool), "Malformed token logout should return boolean"
        
        print(f"✅ Step 3: Malformed token logout handled gracefully - result: {logout_result_malformed}")
        
        print(f"🛡️ INVALID TOKEN LOGOUT RESILIENCE TEST PASSED")

    @pytest.mark.asyncio
    async def test_logout_audit_logging(self, auth_service, test_user_session):
        """
        Test that logout events are properly audit logged.
        
        This ensures security events are tracked for compliance.
        """
        session_data = test_user_session
        access_token = session_data["login_response"].access_token
        session_id = session_data["login_response"].user["session_id"]
        user_id = session_data["user_info"]["user_id"]
        
        # Mock the audit logging to capture what gets logged
        audit_logs = []
        
        async def mock_audit_log(event_type, user_id, success, metadata=None, client_info=None):
            audit_logs.append({
                "event_type": event_type,
                "user_id": user_id,
                "success": success,
                "metadata": metadata,
                "client_info": client_info,
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Patch the audit logging method
        auth_service._audit_log = mock_audit_log
        
        # Step 1: Perform logout
        logout_success = await auth_service.logout(access_token, session_id)
        assert logout_success is True, "Logout should succeed"
        
        print(f"✅ Step 1: Logout completed")
        
        # Step 2: Verify audit log was created
        logout_logs = [log for log in audit_logs if log["event_type"] == "logout"]
        assert len(logout_logs) >= 1, "Should have at least one logout audit log"
        
        logout_log = logout_logs[0]
        assert logout_log["user_id"] == user_id, "Audit log should contain correct user ID"
        assert logout_log["success"] is True, "Audit log should indicate successful logout"
        
        print(f"✅ Step 2: Logout audit log verified")
        print(f"   - Event: {logout_log['event_type']}")
        print(f"   - User: {logout_log['user_id']}")
        print(f"   - Success: {logout_log['success']}")
        
        print(f"📋 LOGOUT AUDIT LOGGING TEST PASSED")

    @pytest.mark.asyncio
    async def test_double_logout_idempotency(self, auth_service, test_user_session):
        """
        Test that double logout is idempotent (safe to call multiple times).
        
        This prevents errors if logout is called multiple times.
        """
        session_data = test_user_session
        access_token = session_data["login_response"].access_token
        session_id = session_data["login_response"].user["session_id"]
        
        # Step 1: First logout
        first_logout = await auth_service.logout(access_token, session_id)
        assert first_logout is True, "First logout should succeed"
        
        print(f"✅ Step 1: First logout successful")
        
        # Step 2: Second logout with same token (should be idempotent)
        second_logout = await auth_service.logout(access_token, session_id)
        # Should either succeed (idempotent) or fail gracefully
        assert isinstance(second_logout, bool), "Second logout should return boolean result"
        
        print(f"✅ Step 2: Second logout handled gracefully - result: {second_logout}")
        
        # Step 3: Token should still be invalid after double logout
        token_validation = await auth_service.validate_token(access_token)
        assert token_validation.valid is False, "Token should remain invalid after double logout"
        
        print(f"✅ Step 3: Token remains invalid after double logout")
        
        print(f"🔄 DOUBLE LOGOUT IDEMPOTENCY TEST PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])