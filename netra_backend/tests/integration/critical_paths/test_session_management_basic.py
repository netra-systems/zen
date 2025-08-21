#!/usr/bin/env python3
"""
L3 Integration Test: Session Management Basic Operations
Tests session creation, validation, expiration, and multi-device scenarios.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

import aiohttp
import pytest

# Add project root to path
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.session_service import SessionService
from test_framework.test_patterns import L3IntegrationTest

# Add project root to path


class TestSessionManagementBasic(L3IntegrationTest):
    """Test session management from multiple angles."""
    
    async def test_session_creation_on_login(self):
        """Test that session is properly created on login."""
        user_data = await self.create_test_user("session1@test.com")
        
        async with aiohttp.ClientSession() as session:
            # Login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                
                access_token = data["access_token"]
                user_id = data["user"]["id"]
            
            # Verify session exists
            redis_manager = RedisManager()
            session_key = f"session:{user_id}:*"
            sessions = await redis_manager.scan_keys(session_key)
            assert len(sessions) > 0
            
            # Check session data
            session_data = await redis_manager.get(sessions[0])
            session_info = json.loads(session_data)
            
            assert session_info["user_id"] == user_id
            assert "created_at" in session_info
            assert "last_activity" in session_info
            
    async def test_session_validation(self):
        """Test session validation with valid and invalid tokens."""
        user_data = await self.create_test_user("session2@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Valid session
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["email"] == user_data["email"]
            
            # Invalid session
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": "Bearer invalid_token"}
            ) as resp:
                assert resp.status == 401
                
    async def test_session_expiration(self):
        """Test session expiration and cleanup."""
        user_data = await self.create_test_user("session3@test.com")
        token = await self.get_auth_token(user_data)
        
        redis_manager = RedisManager()
        
        # Get session key
        user_id = user_data["id"]
        session_pattern = f"session:{user_id}:*"
        sessions = await redis_manager.scan_keys(session_pattern)
        assert len(sessions) > 0
        
        session_key = sessions[0]
        
        # Check TTL
        ttl = await redis_manager.ttl(session_key)
        assert ttl > 0  # Should have expiration set
        assert ttl <= 3600  # Default 1 hour
        
        # Manually expire session
        await redis_manager.expire(session_key, 1)
        await asyncio.sleep(2)
        
        # Try to use expired session
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 401
                
    async def test_session_logout_cleanup(self):
        """Test that logout properly cleans up session."""
        user_data = await self.create_test_user("session4@test.com")
        token = await self.get_auth_token(user_data)
        
        redis_manager = RedisManager()
        user_id = user_data["id"]
        
        async with aiohttp.ClientSession() as session:
            # Verify session exists
            session_pattern = f"session:{user_id}:*"
            sessions_before = await redis_manager.scan_keys(session_pattern)
            assert len(sessions_before) > 0
            
            # Logout
            async with session.post(
                f"{self.auth_service_url}/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
            
            # Verify session is removed
            sessions_after = await redis_manager.scan_keys(session_pattern)
            assert len(sessions_after) == 0
            
            # Verify token no longer works
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 401
                
    async def test_multiple_sessions_same_user(self):
        """Test multiple active sessions for same user."""
        user_data = await self.create_test_user("session5@test.com")
        
        tokens = []
        async with aiohttp.ClientSession() as session:
            # Create multiple sessions
            for i in range(3):
                login_data = {
                    "email": user_data["email"],
                    "password": user_data["password"]
                }
                
                async with session.post(
                    f"{self.auth_service_url}/auth/login",
                    json=login_data
                ) as resp:
                    assert resp.status == 200
                    data = await resp.json()
                    tokens.append(data["access_token"])
            
            # Verify all sessions work
            for token in tokens:
                async with session.get(
                    f"{self.backend_url}/api/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
            
            # Verify sessions in Redis
            redis_manager = RedisManager()
            user_id = user_data["id"]
            session_pattern = f"session:{user_id}:*"
            sessions = await redis_manager.scan_keys(session_pattern)
            assert len(sessions) >= 3
            
    async def test_session_activity_tracking(self):
        """Test that session tracks last activity."""
        user_data = await self.create_test_user("session6@test.com")
        token = await self.get_auth_token(user_data)
        
        redis_manager = RedisManager()
        user_id = user_data["id"]
        
        # Get session
        session_pattern = f"session:{user_id}:*"
        sessions = await redis_manager.scan_keys(session_pattern)
        session_key = sessions[0]
        
        # Get initial activity time
        session_data = await redis_manager.get(session_key)
        initial_activity = json.loads(session_data)["last_activity"]
        
        # Wait and make request
        await asyncio.sleep(2)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
        
        # Check updated activity time
        session_data = await redis_manager.get(session_key)
        new_activity = json.loads(session_data)["last_activity"]
        
        assert new_activity > initial_activity
        
    async def test_session_device_tracking(self):
        """Test session tracks device information."""
        user_data = await self.create_test_user("session7@test.com")
        
        async with aiohttp.ClientSession() as session:
            # Login with device info
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"],
                "device_info": {
                    "device_id": str(uuid.uuid4()),
                    "device_name": "Test Device",
                    "device_type": "desktop",
                    "os": "Windows",
                    "browser": "Chrome"
                }
            }
            
            async with session.post(
                f"{self.auth_service_url}/auth/login",
                json=login_data
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                token = data["access_token"]
            
            # Get session info
            async with session.get(
                f"{self.backend_url}/api/v1/users/sessions",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
                sessions_data = await resp.json()
                
                # Find current session
                current_session = next(
                    s for s in sessions_data["sessions"]
                    if s.get("is_current")
                )
                
                assert current_session["device_info"]["device_name"] == "Test Device"
                assert current_session["device_info"]["device_type"] == "desktop"
                
    async def test_session_invalidation_cascade(self):
        """Test that invalidating a session cascades properly."""
        user_data = await self.create_test_user("session8@test.com")
        token = await self.get_auth_token(user_data)
        
        # Establish WebSocket connection with session
        ws_url = f"{self.ws_url}?token={token}"
        
        import websockets
        ws_connection = await websockets.connect(ws_url)
        
        try:
            # Invalidate session
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.auth_service_url}/auth/logout",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    assert resp.status == 200
            
            # WebSocket should be closed
            await asyncio.sleep(1)
            assert ws_connection.closed
            
        finally:
            if not ws_connection.closed:
                await ws_connection.close()
                
    async def test_session_refresh_extends_expiry(self):
        """Test that using a session extends its expiry."""
        user_data = await self.create_test_user("session9@test.com")
        token = await self.get_auth_token(user_data)
        
        redis_manager = RedisManager()
        user_id = user_data["id"]
        
        # Get session
        session_pattern = f"session:{user_id}:*"
        sessions = await redis_manager.scan_keys(session_pattern)
        session_key = sessions[0]
        
        # Get initial TTL
        initial_ttl = await redis_manager.ttl(session_key)
        
        # Wait and make request
        await asyncio.sleep(5)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200
        
        # Check new TTL
        new_ttl = await redis_manager.ttl(session_key)
        
        # TTL should be refreshed (close to original)
        assert new_ttl > initial_ttl - 10
        
    async def test_concurrent_session_operations(self):
        """Test concurrent operations on same session."""
        user_data = await self.create_test_user("session10@test.com")
        token = await self.get_auth_token(user_data)
        
        async with aiohttp.ClientSession() as session:
            # Make concurrent requests with same session
            tasks = []
            for i in range(10):
                tasks.append(session.get(
                    f"{self.backend_url}/api/v1/threads",
                    headers={"Authorization": f"Bearer {token}"}
                ))
            
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            for resp in responses:
                assert resp.status == 200
            
            # Session should still be valid
            async with session.get(
                f"{self.backend_url}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            ) as resp:
                assert resp.status == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])