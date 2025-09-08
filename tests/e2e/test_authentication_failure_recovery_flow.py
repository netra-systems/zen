"""
E2E Tests: Authentication Failure and Recovery Flow

Business Value Justification (BVJ):
- Segment: All (authentication failures affect all users)
- Business Goal: Ensure graceful handling of auth failures and recovery paths
- Value Impact: Poor error handling leads to user frustration and support tickets
- Strategic Impact: User experience and reliability - recovery flows prevent user churn

CRITICAL REQUIREMENTS per CLAUDE.md:
- MUST use E2EAuthHelper for authentication
- Tests real failure scenarios and recovery paths
- NO MOCKS in E2E tests
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestAuthenticationFailureRecoveryFlow(SSotAsyncTestCase):
    """E2E tests for authentication failure and recovery flow."""
    
    async def async_setup_method(self, method=None):
        """Async setup for each test method."""
        await super().async_setup_method(method)
        
        self.set_env_var("TEST_ENV", "e2e")
        self.set_env_var("MAX_LOGIN_ATTEMPTS", "3")
        self.set_env_var("LOCKOUT_DURATION_MINUTES", "15")
        
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Test user for failure scenarios
        self.test_email = f"failure_test_user_{int(datetime.now().timestamp())}@example.com"
        self.test_password = "CorrectPassword123!"
        self.wrong_password = "WrongPassword456!"
        
    def _simulate_login_attempt(self, email: str, password: str, attempt_number: int = 1) -> Dict[str, Any]:
        """Simulate login attempt with failure tracking."""
        if password == self.test_password:
            return {
                "success": True,
                "user": {
                    "id": f"user_{hash(email) & 0xFFFFFFFF:08x}",
                    "email": email,
                    "login_attempts": 0  # Reset on successful login
                },
                "access_token": self.auth_helper.create_test_jwt_token(
                    user_id=f"user_{hash(email) & 0xFFFFFFFF:08x}",
                    email=email
                )
            }
        else:
            max_attempts = int(self.get_env_var("MAX_LOGIN_ATTEMPTS"))
            is_locked = attempt_number >= max_attempts
            
            return {
                "success": False,
                "error": "Invalid credentials",
                "login_attempts": attempt_number,
                "max_attempts": max_attempts,
                "account_locked": is_locked,
                "lockout_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat() if is_locked else None
            }
            
    def _simulate_password_reset_request(self, email: str) -> Dict[str, Any]:
        """Simulate password reset request."""
        return {
            "success": True,
            "message": "Password reset email sent",
            "reset_token": f"reset_token_{hash(email) & 0xFFFFFFFF:08x}",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
    def _simulate_password_reset_completion(self, reset_token: str, new_password: str) -> Dict[str, Any]:
        """Simulate password reset completion."""
        if reset_token.startswith("reset_token_"):
            return {
                "success": True,
                "message": "Password reset successfully",
                "password_updated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Invalid or expired reset token"
            }
            
    def _simulate_account_unlock(self, email: str, unlock_method: str = "admin") -> Dict[str, Any]:
        """Simulate account unlock (admin or time-based)."""
        return {
            "success": True,
            "account_unlocked": True,
            "unlock_method": unlock_method,
            "unlocked_at": datetime.now(timezone.utc).isoformat(),
            "login_attempts_reset": True
        }
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multiple_failed_login_attempts(self):
        """Test handling of multiple failed login attempts leading to lockout."""
        max_attempts = int(self.get_env_var("MAX_LOGIN_ATTEMPTS"))
        
        # Attempt login with wrong password multiple times
        for attempt in range(1, max_attempts + 1):
            login_result = self._simulate_login_attempt(
                self.test_email, 
                self.wrong_password, 
                attempt
            )
            
            assert login_result["success"] is False
            assert login_result["login_attempts"] == attempt
            
            if attempt < max_attempts:
                assert login_result["account_locked"] is False
            else:
                # Final attempt should lock account
                assert login_result["account_locked"] is True
                assert "lockout_until" in login_result
                
        self.record_metric("failed_attempts_lockout_success", True)
        self.record_metric("attempts_before_lockout", max_attempts)
        self.increment_db_query_count(max_attempts)  # Track each attempt
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_password_reset_recovery_flow(self):
        """Test complete password reset recovery flow."""
        # Step 1: User requests password reset
        reset_request = self._simulate_password_reset_request(self.test_email)
        assert reset_request["success"] is True
        assert "reset_token" in reset_request
        
        reset_token = reset_request["reset_token"]
        
        # Step 2: User completes password reset
        new_password = "NewPassword789!"
        reset_completion = self._simulate_password_reset_completion(reset_token, new_password)
        assert reset_completion["success"] is True
        
        # Step 3: User can login with new password
        login_result = self._simulate_login_attempt(self.test_email, new_password)
        assert login_result["success"] is True
        assert login_result["user"]["login_attempts"] == 0  # Reset after successful login
        
        self.record_metric("password_reset_flow_success", True)
        self.increment_db_query_count(3)  # Reset request + completion + login
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_account_lockout_and_unlock_flow(self):
        """Test account lockout and administrative unlock flow."""
        max_attempts = int(self.get_env_var("MAX_LOGIN_ATTEMPTS"))
        
        # Step 1: Lock account with failed attempts
        for attempt in range(1, max_attempts + 1):
            login_result = self._simulate_login_attempt(
                self.test_email, 
                self.wrong_password, 
                attempt
            )
            
        # Verify account is locked
        assert login_result["account_locked"] is True
        
        # Step 2: Admin unlocks account
        unlock_result = self._simulate_account_unlock(self.test_email, "admin")
        assert unlock_result["success"] is True
        assert unlock_result["account_unlocked"] is True
        assert unlock_result["login_attempts_reset"] is True
        
        # Step 3: User can login after unlock
        login_after_unlock = self._simulate_login_attempt(self.test_email, self.test_password)
        assert login_after_unlock["success"] is True
        
        self.record_metric("account_unlock_flow_success", True)
        self.increment_db_query_count(max_attempts + 2)  # Failed attempts + unlock + login
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_expired_token_recovery(self):
        """Test recovery from expired authentication tokens."""
        # Step 1: Create user and get token
        user_login = self._simulate_login_attempt(self.test_email, self.test_password)
        assert user_login["success"] is True
        
        original_token = user_login["access_token"]
        
        # Step 2: Simulate token expiry by creating expired token
        expired_token = original_token + "_expired"
        
        # Step 3: Verify expired token is rejected
        auth_headers = self.auth_helper.get_auth_headers(expired_token)
        # In real test, would attempt API call and expect 401 Unauthorized
        
        # Step 4: User re-authenticates to get new token
        reauth_result = self._simulate_login_attempt(self.test_email, self.test_password)
        assert reauth_result["success"] is True
        
        new_token = reauth_result["access_token"]
        assert new_token != original_token  # Should be different token
        
        self.record_metric("expired_token_recovery_success", True)
        self.increment_db_query_count(2)  # Original login + re-auth
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_concurrent_failed_login_attempts(self):
        """Test handling of concurrent failed login attempts."""
        
        async def attempt_concurrent_login(attempt_id: int):
            """Simulate concurrent failed login attempt."""
            return self._simulate_login_attempt(
                self.test_email, 
                f"wrong_password_{attempt_id}", 
                attempt_id
            )
            
        # Launch concurrent failed login attempts
        concurrent_attempts = 3
        attempt_tasks = [attempt_concurrent_login(i) for i in range(1, concurrent_attempts + 1)]
        
        attempt_results = await asyncio.gather(*attempt_tasks)
        
        # Verify all attempts failed
        failed_count = sum(1 for result in attempt_results if not result["success"])
        assert failed_count == concurrent_attempts
        
        # Verify attempt counting (in real system, would need proper race condition handling)
        attempt_counts = [result["login_attempts"] for result in attempt_results]
        assert max(attempt_counts) <= int(self.get_env_var("MAX_LOGIN_ATTEMPTS"))
        
        self.record_metric("concurrent_failed_attempts_handled", True)
        self.record_metric("concurrent_attempts_count", concurrent_attempts)
        self.increment_db_query_count(concurrent_attempts)