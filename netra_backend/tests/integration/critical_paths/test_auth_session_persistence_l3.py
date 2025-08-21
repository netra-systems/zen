"""
L3 Integration Test: Authentication Session Persistence
Tests session persistence across service restarts and Redis operations
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import redis.asyncio as redis
from unittest.mock import patch, AsyncMock, MagicMock

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.config import settings
import json

# Add project root to path


class TestAuthSessionPersistenceL3:
    """Test authentication session persistence scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_storage_in_redis(self):
        """Test session is properly stored in Redis"""
        auth_service = AuthService()
        redis_client = await redis.from_url(settings.REDIS_URL)
        
        try:
            with patch.object(auth_service, '_verify_password', return_value=True):
                with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                    result = await auth_service.authenticate("testuser", "password")
                    
                    # Check session in Redis
                    session_key = f"session:{result['session_id']}"
                    session_data = await redis_client.get(session_key)
                    
                    assert session_data is not None, "Session should be stored in Redis"
                    
                    session = json.loads(session_data)
                    assert session["user_id"] == "123"
                    assert session["username"] == "testuser"
        finally:
            await redis_client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_ttl_configuration(self):
        """Test session TTL is properly configured"""
        auth_service = AuthService()
        redis_client = await redis.from_url(settings.REDIS_URL)
        
        try:
            with patch.object(auth_service, '_verify_password', return_value=True):
                with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                    result = await auth_service.authenticate("testuser", "password")
                    
                    session_key = f"session:{result['session_id']}"
                    ttl = await redis_client.ttl(session_key)
                    
                    # Check TTL is set (should be positive)
                    assert ttl > 0, "Session should have TTL set"
                    assert ttl <= settings.SESSION_TIMEOUT, "TTL should not exceed configured timeout"
        finally:
            await redis_client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_recovery_after_redis_restart(self):
        """Test session recovery after Redis connection loss"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                result = await auth_service.authenticate("testuser", "password")
                session_id = result['session_id']
                
                # Simulate Redis restart
                with patch('app.services.auth_service.redis_client') as mock_redis:
                    mock_redis.get.side_effect = [ConnectionError(), json.dumps({"user_id": "123"})]
                    
                    # First attempt should retry
                    session = await auth_service.get_session(session_id)
                    assert session is not None, "Should recover after connection error"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_session_updates(self):
        """Test concurrent session updates don't cause race conditions"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                result = await auth_service.authenticate("testuser", "password")
                session_id = result['session_id']
                
                # Concurrent session updates
                async def update_session(data):
                    await auth_service.update_session(session_id, data)
                
                tasks = [
                    update_session({"last_activity": i})
                    for i in range(10)
                ]
                
                await asyncio.gather(*tasks)
                
                # Verify session integrity
                session = await auth_service.get_session(session_id)
                assert session is not None, "Session should still exist"
                assert "user_id" in session, "Core session data should be preserved"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_cleanup_on_logout(self):
        """Test session is properly cleaned up on logout"""
        auth_service = AuthService()
        redis_client = await redis.from_url(settings.REDIS_URL)
        
        try:
            with patch.object(auth_service, '_verify_password', return_value=True):
                with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                    result = await auth_service.authenticate("testuser", "password")
                    session_id = result['session_id']
                    
                    # Logout
                    await auth_service.logout(session_id)
                    
                    # Check session is removed
                    session_key = f"session:{session_id}"
                    session_data = await redis_client.get(session_key)
                    
                    assert session_data is None, "Session should be removed after logout"
        finally:
            await redis_client.close()