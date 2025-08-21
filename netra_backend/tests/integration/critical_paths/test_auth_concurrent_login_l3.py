"""
L3 Integration Test: Concurrent Login Handling
Tests handling of concurrent login attempts and session management
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.config import settings
import time

# Add project root to path


class TestAuthConcurrentLoginL3:
    """Test concurrent authentication scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_login_same_user(self):
        """Test multiple concurrent login attempts for same user"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                # Concurrent login attempts
                tasks = [
                    auth_service.authenticate("testuser", "password")
                    for _ in range(10)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed
                successful = [r for r in results if not isinstance(r, Exception)]
                assert len(successful) == 10, "All concurrent logins should succeed"
                
                # Each should have unique session
                session_ids = [r["session_id"] for r in successful]
                assert len(set(session_ids)) == 10, "Each login should create unique session"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_login_different_users(self):
        """Test concurrent login attempts for different users"""
        auth_service = AuthService()
        
        users = [
            {"id": f"user{i}", "username": f"user{i}"}
            for i in range(5)
        ]
        
        async def login_user(user):
            with patch.object(auth_service, '_verify_password', return_value=True):
                with patch.object(auth_service, '_get_user', return_value=user):
                    return await auth_service.authenticate(user["username"], "password")
        
        tasks = [login_user(user) for user in users]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r is not None for r in results)
        
        # Each should have correct user data
        for i, result in enumerate(results):
            assert result["user_id"] == f"user{i}"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_limit_per_user(self):
        """Test maximum session limit per user"""
        auth_service = AuthService()
        max_sessions = 5
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                with patch.object(auth_service, 'MAX_SESSIONS_PER_USER', max_sessions):
                    sessions = []
                    
                    # Create max sessions
                    for _ in range(max_sessions):
                        result = await auth_service.authenticate("testuser", "password")
                        sessions.append(result["session_id"])
                    
                    # Next login should invalidate oldest session
                    new_result = await auth_service.authenticate("testuser", "password")
                    
                    # Check oldest session is invalid
                    oldest_valid = await auth_service.get_session(sessions[0])
                    assert oldest_valid is None, "Oldest session should be invalidated"
                    
                    # Newest session should be valid
                    newest_valid = await auth_service.get_session(new_result["session_id"])
                    assert newest_valid is not None, "Newest session should be valid"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_during_logout(self):
        """Test login attempt during logout process"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                # Initial login
                result1 = await auth_service.authenticate("testuser", "password")
                
                # Concurrent logout and new login
                async def logout():
                    await asyncio.sleep(0.01)  # Small delay
                    await auth_service.logout(result1["session_id"])
                
                async def login():
                    await asyncio.sleep(0.01)  # Small delay
                    return await auth_service.authenticate("testuser", "password")
                
                logout_task = asyncio.create_task(logout())
                login_task = asyncio.create_task(login())
                
                result2 = await login_task
                await logout_task
                
                # New login should succeed
                assert result2 is not None
                assert result2["session_id"] != result1["session_id"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_race_condition_handling(self):
        """Test handling of race conditions in login process"""
        auth_service = AuthService()
        
        call_count = 0
        
        async def slow_verify(*args):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow verification
            return True
        
        with patch.object(auth_service, '_verify_password', side_effect=slow_verify):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                # Multiple concurrent slow logins
                tasks = [
                    auth_service.authenticate("testuser", "password")
                    for _ in range(3)
                ]
                
                results = await asyncio.gather(*tasks)
                
                # All should complete successfully
                assert all(r is not None for r in results)
                assert call_count == 3, "Each login should verify independently"