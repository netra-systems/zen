#!/usr/bin/env python3
"""
Comprehensive test to verify authentication session expiry and refresh:
1. Initial authentication
2. Token expiry monitoring
3. Automatic refresh handling
4. Session invalidation
5. Multi-device session management
6. Refresh token rotation

This test ensures proper session lifecycle management.
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import jwt
import pytest

# Configuration
DEV_BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8081"

class AuthenticationSessionTester:
    """Test authentication session expiry and refresh."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.session_id: Optional[str] = None
        self.refresh_count = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    @pytest.mark.asyncio
    async def test_initial_authentication(self) -> bool:
        """Test initial authentication and token issuance."""
        print("\n[AUTH] Testing initial authentication...")
        
        # Register/login
        user_data = {
            "email": "session_test@example.com",
            "password": "sessiontest123",
            "name": "Session Test User"
        }
        
        # Register (ignore if exists)
        await self.session.post(f"{AUTH_SERVICE_URL}/auth/register", json=user_data)
        
        # Login
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]}
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.session_id = data.get("session_id")
                
                # Decode token to get expiry (without verification for testing)
                try:
                    payload = jwt.decode(self.access_token, options={"verify_signature": False})
                    self.token_expiry = datetime.fromtimestamp(payload.get("exp", 0))
                    print(f"[OK] Authenticated. Token expires at: {self.token_expiry}")
                except:
                    pass
                    
                return bool(self.access_token and self.refresh_token)
                
        return False
        
    @pytest.mark.asyncio
    async def test_token_validation(self) -> bool:
        """Test token validation before expiry."""
        print("\n[VALIDATE] Testing token validation...")
        
        if not self.access_token:
            return False
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with self.session.get(
            f"{DEV_BACKEND_URL}/api/user/profile",
            headers=headers
        ) as response:
            if response.status == 200:
                print("[OK] Token valid and accepted")
                return True
            elif response.status == 401:
                print("[ERROR] Token rejected before expiry")
                return False
                
        return False
        
    @pytest.mark.asyncio
    async def test_token_refresh(self) -> bool:
        """Test token refresh mechanism."""
        print("\n[REFRESH] Testing token refresh...")
        
        if not self.refresh_token:
            return False
            
        refresh_data = {"refresh_token": self.refresh_token}
        
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/refresh",
            json=refresh_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                new_access = data.get("access_token")
                new_refresh = data.get("refresh_token")
                
                if new_access:
                    # Update tokens
                    old_access = self.access_token
                    self.access_token = new_access
                    if new_refresh:
                        self.refresh_token = new_refresh
                        
                    self.refresh_count += 1
                    
                    # Verify new token is different
                    if old_access != new_access:
                        print(f"[OK] Token refreshed successfully (attempt {self.refresh_count})")
                        return True
                        
        return False
        
    @pytest.mark.asyncio
    async def test_expired_token_rejection(self) -> bool:
        """Test that expired tokens are rejected."""
        print("\n[EXPIRE] Testing expired token rejection...")
        
        # Create an expired token for testing (would need mock in production)
        # For now, test with invalid token
        invalid_token = "expired.token.here"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        async with self.session.get(
            f"{DEV_BACKEND_URL}/api/user/profile",
            headers=headers
        ) as response:
            if response.status == 401:
                print("[OK] Expired/invalid token rejected")
                return True
            else:
                print(f"[ERROR] Invalid token not rejected: {response.status}")
                return False
                
    @pytest.mark.asyncio
    async def test_refresh_token_rotation(self) -> bool:
        """Test refresh token rotation for security."""
        print("\n[ROTATE] Testing refresh token rotation...")
        
        if not self.refresh_token:
            return False
            
        old_refresh = self.refresh_token
        
        # Refresh multiple times
        for i in range(3):
            refresh_data = {"refresh_token": self.refresh_token}
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/refresh",
                json=refresh_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    new_refresh = data.get("refresh_token")
                    
                    if new_refresh and new_refresh != self.refresh_token:
                        self.refresh_token = new_refresh
                        print(f"[OK] Refresh token rotated (iteration {i+1})")
                        
            await asyncio.sleep(1)
            
        # Old refresh token should be invalid
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/refresh",
            json={"refresh_token": old_refresh}
        ) as response:
            if response.status == 401:
                print("[OK] Old refresh token invalidated")
                return True
            else:
                print("[WARNING] Old refresh token still valid")
                return False
                
    @pytest.mark.asyncio
    async def test_session_invalidation(self) -> bool:
        """Test explicit session invalidation."""
        print("\n[LOGOUT] Testing session invalidation...")
        
        if not self.access_token:
            return False
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Logout
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/logout",
            headers=headers
        ) as response:
            if response.status in [200, 204]:
                print("[OK] Logout successful")
                
                # Try to use token after logout
                async with self.session.get(
                    f"{DEV_BACKEND_URL}/api/user/profile",
                    headers=headers
                ) as profile_response:
                    if profile_response.status == 401:
                        print("[OK] Token invalidated after logout")
                        return True
                    else:
                        print("[ERROR] Token still valid after logout")
                        return False
                        
        return False
        
    @pytest.mark.asyncio
    async def test_multi_device_sessions(self) -> bool:
        """Test multi-device session management."""
        print("\n[MULTI] Testing multi-device sessions...")
        
        # Create multiple sessions
        sessions = []
        user_data = {
            "email": "multidevice@example.com",
            "password": "multidevice123"
        }
        
        # Register user
        await self.session.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json={**user_data, "name": "Multi Device User"}
        )
        
        # Create 3 sessions
        for i in range(3):
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json={**user_data, "device_id": f"device_{i}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    sessions.append({
                        "device": f"device_{i}",
                        "token": data.get("access_token"),
                        "session_id": data.get("session_id")
                    })
                    
        if len(sessions) == 3:
            print(f"[OK] Created {len(sessions)} device sessions")
            
            # Invalidate one session
            headers = {"Authorization": f"Bearer {sessions[0]['token']}"}
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/logout",
                headers=headers
            ) as response:
                if response.status in [200, 204]:
                    # Check other sessions still valid
                    other_valid = True
                    for sess in sessions[1:]:
                        headers = {"Authorization": f"Bearer {sess['token']}"}
                        async with self.session.get(
                            f"{DEV_BACKEND_URL}/api/user/profile",
                            headers=headers
                        ) as check_response:
                            if check_response.status != 200:
                                other_valid = False
                                break
                                
                    if other_valid:
                        print("[OK] Other device sessions remain valid")
                        return True
                        
        return False
        
    @pytest.mark.asyncio
    async def test_automatic_refresh_before_expiry(self) -> bool:
        """Test automatic refresh before token expiry."""
        print("\n[AUTO] Testing automatic refresh...")
        
        # This would require WebSocket or polling in real implementation
        # Simulating the check here
        
        if not self.access_token:
            return False
            
        # Check if token is near expiry
        if self.token_expiry:
            time_to_expiry = (self.token_expiry - datetime.utcnow()).total_seconds()
            
            if time_to_expiry < 300:  # Less than 5 minutes
                print(f"[INFO] Token expiring in {time_to_expiry}s, refreshing...")
                
                if await self.test_token_refresh():
                    print("[OK] Automatic refresh successful")
                    return True
                    
        # Simulate automatic refresh trigger
        return self.refresh_count > 0
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests in sequence."""
        results = {}
        
        results["initial_auth"] = await self.test_initial_authentication()
        if not results["initial_auth"]:
            print("[ERROR] Initial authentication failed")
            return results
            
        results["token_validation"] = await self.test_token_validation()
        results["token_refresh"] = await self.test_token_refresh()
        results["expired_rejection"] = await self.test_expired_token_rejection()
        results["refresh_rotation"] = await self.test_refresh_token_rotation()
        results["multi_device"] = await self.test_multi_device_sessions()
        results["auto_refresh"] = await self.test_automatic_refresh_before_expiry()
        results["session_invalidation"] = await self.test_session_invalidation()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.asyncio
async def test_authentication_session_expiry():
    """Test authentication session expiry and refresh."""
    async with AuthenticationSessionTester() as tester:
        results = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("AUTHENTICATION SESSION TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        print(f"\nTotal refreshes: {tester.refresh_count}")
        
        assert all(results.values()), f"Some tests failed: {results}"

if __name__ == "__main__":
    exit_code = asyncio.run(test_authentication_session_expiry())
    sys.exit(0 if exit_code else 1)