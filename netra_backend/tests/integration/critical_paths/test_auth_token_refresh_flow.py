#!/usr/bin/env python3
"""
L3 Integration Test: Token Refresh Flow
Tests JWT token refresh mechanisms including edge cases and error scenarios.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import aiohttp
import jwt
import pytest

from netra_backend.app.core.auth import TokenManager
from netra_backend.app.redis_manager import RedisManager
from test_framework.test_patterns import L3IntegrationTest

class TestAuthTokenRefreshFlow(L3IntegrationTest):
    """Test token refresh flow from multiple angles."""
    
    async def test_successful_token_refresh(self):
        """Test successful refresh token flow."""
        async with aiohttp.ClientSession() as session:
            # Login to get initial tokens
            user_data = await self.create_test_user("refresh1@test.com")
            login_resp = await self.login_user(session, user_data)
            
            access_token = login_resp["access_token"]
            refresh_token = login_resp["refresh_token"]
            
            # Wait a bit to ensure new token has different timestamp
            await asyncio.sleep(1)
            
            # Refresh the token
            refresh_data = {"refresh_token": refresh_token}
            
            async with session.post(
                f"{self.auth_service_url}/auth/refresh",
                json=refresh_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Verify new tokens are returned
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["access_token"] != access_token
                assert data["refresh_token"] != refresh_token
                
    async def test_refresh_with_expired_access_token(self):
        """Test that refresh works even when access token is expired."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh2@test.com")
            login_resp = await self.login_user(session, user_data)
            
            refresh_token = login_resp["refresh_token"]
            
            # Wait for access token to expire (simulated)
            # In real scenario, we'd wait or mock time
            await asyncio.sleep(2)
            
            # Refresh should still work
            refresh_data = {"refresh_token": refresh_token}
            
            async with session.post(
                f"{self.auth_service_url}/auth/refresh",
                json=refresh_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "access_token" in data
                
    async def test_refresh_with_invalid_token(self):
        """Test refresh with invalid or malformed refresh token."""
        async with aiohttp.ClientSession() as session:
            refresh_data = {"refresh_token": "invalid_token_here"}
            
            async with session.post(
                f"{self.auth_service_url}/auth/refresh",
                json=refresh_data
            ) as resp:
                assert resp.status == 401
                data = await resp.json()
                assert "error" in data
                assert "Invalid refresh token" in data["error"]
                
    async def test_refresh_with_revoked_token(self):
        """Test refresh with a revoked refresh token."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh3@test.com")
            login_resp = await self.login_user(session, user_data)
            
            access_token = login_resp["access_token"]
            refresh_token = login_resp["refresh_token"]
            
            # Logout to revoke tokens
            async with session.post(
                f"{self.auth_service_url}/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                assert resp.status == 200
            
            # Try to refresh with revoked token
            refresh_data = {"refresh_token": refresh_token}
            
            async with session.post(
                f"{self.auth_service_url}/auth/refresh",
                json=refresh_data
            ) as resp:
                assert resp.status == 401
                data = await resp.json()
                assert "Token has been revoked" in data.get("error", "")
                
    async def test_refresh_token_rotation(self):
        """Test that refresh tokens are rotated on use."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh4@test.com")
            login_resp = await self.login_user(session, user_data)
            
            refresh_token = login_resp["refresh_token"]
            used_tokens = {refresh_token}
            
            # Perform multiple refreshes
            for i in range(3):
                refresh_data = {"refresh_token": refresh_token}
                
                async with session.post(
                    f"{self.auth_service_url}/auth/refresh",
                    json=refresh_data
                ) as resp:
                    assert resp.status == 200
                    data = await resp.json()
                    
                    new_refresh = data["refresh_token"]
                    assert new_refresh not in used_tokens
                    used_tokens.add(new_refresh)
                    refresh_token = new_refresh
                    
                await asyncio.sleep(0.5)
                
    async def test_concurrent_refresh_attempts(self):
        """Test multiple concurrent refresh attempts with same token."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh5@test.com")
            login_resp = await self.login_user(session, user_data)
            
            refresh_token = login_resp["refresh_token"]
            
            # Attempt concurrent refreshes
            refresh_data = {"refresh_token": refresh_token}
            
            tasks = []
            for _ in range(5):
                tasks.append(session.post(
                    f"{self.auth_service_url}/auth/refresh",
                    json=refresh_data
                ))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Only one should succeed, others should fail
            success_count = sum(
                1 for r in responses 
                if not isinstance(r, Exception) and r.status == 200
            )
            assert success_count == 1, "Only one refresh should succeed"
            
    async def test_refresh_token_expiry(self):
        """Test that refresh tokens have proper expiry."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh6@test.com")
            login_resp = await self.login_user(session, user_data)
            
            refresh_token = login_resp["refresh_token"]
            
            # Decode to check expiry (without verification for test)
            decoded = jwt.decode(
                refresh_token,
                options={"verify_signature": False}
            )
            
            exp_time = datetime.fromtimestamp(decoded["exp"])
            now = datetime.utcnow()
            
            # Refresh token should have longer expiry (e.g., 7 days)
            time_diff = (exp_time - now).total_seconds()
            assert time_diff > 86400  # More than 1 day
            assert time_diff < 864000  # Less than 10 days
            
    async def test_refresh_maintains_user_context(self):
        """Test that refresh maintains user context and permissions."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh7@test.com")
            login_resp = await self.login_user(session, user_data)
            
            original_user_id = login_resp["user"]["id"]
            refresh_token = login_resp["refresh_token"]
            
            # Refresh token
            refresh_data = {"refresh_token": refresh_token}
            
            async with session.post(
                f"{self.auth_service_url}/auth/refresh",
                json=refresh_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                # Decode new access token
                decoded = jwt.decode(
                    data["access_token"],
                    options={"verify_signature": False}
                )
                
                assert decoded["sub"] == original_user_id
                assert decoded["email"] == user_data["email"]
                
    async def test_refresh_updates_last_activity(self):
        """Test that token refresh updates user's last activity timestamp."""
        redis_manager = RedisManager()
        
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh8@test.com")
            login_resp = await self.login_user(session, user_data)
            
            user_id = login_resp["user"]["id"]
            refresh_token = login_resp["refresh_token"]
            
            # Check initial activity time
            activity_key = f"user:activity:{user_id}"
            initial_activity = await redis_manager.get(activity_key)
            
            # Wait and refresh
            await asyncio.sleep(2)
            
            refresh_data = {"refresh_token": refresh_token}
            
            async with session.post(
                f"{self.auth_service_url}/auth/refresh",
                json=refresh_data
            ) as resp:
                assert resp.status == 200
            
            # Check updated activity time
            new_activity = await redis_manager.get(activity_key)
            assert new_activity != initial_activity
            
    async def test_refresh_rate_limiting(self):
        """Test that refresh endpoint has rate limiting."""
        async with aiohttp.ClientSession() as session:
            user_data = await self.create_test_user("refresh9@test.com")
            login_resp = await self.login_user(session, user_data)
            
            refresh_token = login_resp["refresh_token"]
            
            # Rapid refresh attempts
            attempts = []
            for i in range(20):
                refresh_data = {"refresh_token": f"fake_token_{i}"}
                attempts.append(session.post(
                    f"{self.auth_service_url}/auth/refresh",
                    json=refresh_data
                ))
            
            responses = await asyncio.gather(*attempts, return_exceptions=True)
            
            # Check for rate limiting
            rate_limited = sum(
                1 for r in responses 
                if not isinstance(r, Exception) and r.status == 429
            )
            assert rate_limited > 0, "Rate limiting should trigger"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])