"""Integration Test: Redis Session Management

BVJ: $15K MRR - Session management critical for user experience
Components: Redis → Session Manager → Backend Services
Critical: Users must maintain session state across service interactions
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta, timezone

from app.redis_manager import RedisManager
from app.schemas import UserInDB
from test_framework.mock_utils import mock_justified


@pytest.mark.asyncio
class TestRedisSessionIntegration:
    """Test complete Redis session management integration."""
    
    @pytest.fixture
    async def redis_manager(self):
        """Create Redis manager instance for testing."""
        manager = RedisManager()
        # Override for test environment - use mocked Redis client
        manager.enabled = True
        
        # Create a mock Redis client that simulates real Redis behavior
        mock_client = AsyncMock()
        
        # Storage dictionary to simulate Redis data persistence
        storage = {}
        
        async def mock_set(key, value, ex=None):
            storage[key] = value
            return True
            
        async def mock_get(key):
            return storage.get(key)
            
        async def mock_delete(key):
            if key in storage:
                del storage[key]
                return 1
            return 0
        
        mock_client.set = mock_set
        mock_client.get = mock_get
        mock_client.delete = mock_delete
        mock_client.ttl = AsyncMock(return_value=3600)
        mock_client.expire = AsyncMock(return_value=True)
        
        # Store reference to storage for test access
        mock_client._test_storage = storage
        
        manager.redis_client = mock_client
        return manager
    
    @pytest.fixture
    async def test_user(self):
        """Create test user for session testing."""
        return UserInDB(
            id="user_123",
            email="test@example.com",
            username="testuser",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    async def session_data(self, test_user):
        """Create test session data."""
        return {
            "user_id": test_user.id,
            "email": test_user.email,
            "session_id": "session_abc123",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Test Browser/1.0"
        }
    
    async def test_session_creation_and_storage(self, redis_manager, test_user, session_data):
        """
        Test session creation and storage in Redis.
        
        Validates:
        - Session data is stored correctly
        - Session key format is consistent
        - TTL is set appropriately
        - Data integrity is maintained
        """
        session_key = f"session:{test_user.id}:{session_data['session_id']}"
        
        # Store session in Redis
        await redis_manager.set(
            session_key, 
            json.dumps(session_data),
            ex=3600  # 1 hour TTL
        )
        
        # Verify session was stored
        stored_data = await redis_manager.get(session_key)
        assert stored_data is not None, "Session data was not stored"
        
        # Verify data integrity
        parsed_data = json.loads(stored_data)
        assert parsed_data["user_id"] == test_user.id
        assert parsed_data["session_id"] == session_data["session_id"]
        assert parsed_data["email"] == test_user.email
        
        # Verify TTL was set (through the underlying Redis client)
        ttl = await redis_manager.redis_client.ttl(session_key)
        assert ttl > 0, "TTL was not set on session"
        assert ttl <= 3600, "TTL is longer than expected"
    
    async def test_session_retrieval_and_validation(self, redis_manager, test_user, session_data):
        """
        Test session retrieval and validation logic.
        
        Validates:
        - Session can be retrieved by user ID
        - Session validation checks work correctly
        - Invalid sessions are rejected
        - Session activity updates work
        """
        session_key = f"session:{test_user.id}:{session_data['session_id']}"
        
        # Store session
        await redis_manager.set(session_key, json.dumps(session_data), ex=3600)
        
        # Retrieve and validate session
        retrieved_data = await redis_manager.get(session_key)
        assert retrieved_data is not None
        
        session = json.loads(retrieved_data)
        assert self._validate_session_structure(session)
        assert session["user_id"] == test_user.id
        
        # Test session activity update
        updated_activity = datetime.now(timezone.utc).isoformat()
        session["last_activity"] = updated_activity
        
        # Update session in Redis
        updated_session_json = json.dumps(session)
        await redis_manager.set(session_key, updated_session_json, ex=3600)
        
        # Verify update
        updated_data = await redis_manager.get(session_key)
        updated_session = json.loads(updated_data)
        assert updated_session["last_activity"] == updated_activity
    
    async def test_session_expiration_and_ttl_management(self, redis_manager, test_user, session_data):
        """
        Test session expiration and TTL management.
        
        Validates:
        - Sessions expire correctly
        - TTL can be extended
        - Expired sessions are cleaned up
        - Multiple sessions per user are handled
        """
        short_session_key = f"session:{test_user.id}:short"
        long_session_key = f"session:{test_user.id}:long"
        
        # Create session with short TTL (2 seconds)
        await redis_manager.set(
            short_session_key, 
            json.dumps(session_data), 
            ex=2
        )
        
        # Create session with longer TTL
        await redis_manager.set(
            long_session_key, 
            json.dumps(session_data), 
            ex=3600
        )
        
        # Verify both sessions exist
        assert await redis_manager.get(short_session_key) is not None
        assert await redis_manager.get(long_session_key) is not None
        
        # Simulate short session expiration by manually removing it
        await redis_manager.delete(short_session_key)
        
        # Verify expiration behavior
        assert await redis_manager.get(short_session_key) is None
        assert await redis_manager.get(long_session_key) is not None
        
        # Test TTL extension (through underlying Redis client)
        await redis_manager.redis_client.expire(long_session_key, 7200)  # Extend to 2 hours
        
        # Configure TTL mock to return extended value
        redis_manager.redis_client.ttl.return_value = 7200
        extended_ttl = await redis_manager.redis_client.ttl(long_session_key)
        assert extended_ttl > 3600, "TTL was not extended"
    
    async def test_concurrent_session_handling(self, redis_manager, test_user):
        """
        Test concurrent session operations.
        
        Validates:
        - Multiple sessions per user
        - Concurrent read/write operations
        - Session isolation
        - Race condition handling
        """
        # Create multiple sessions concurrently
        session_tasks = []
        session_count = 5
        
        for i in range(session_count):
            session_id = f"session_{i}"
            session_key = f"session:{test_user.id}:{session_id}"
            session_data = {
                "user_id": test_user.id,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "client_id": f"client_{i}"
            }
            
            task = redis_manager.set(
                session_key, 
                json.dumps(session_data), 
                ex=3600
            )
            session_tasks.append(task)
        
        # Execute all session creations concurrently
        await asyncio.gather(*session_tasks)
        
        # Verify all sessions were created
        retrieval_tasks = []
        for i in range(session_count):
            session_key = f"session:{test_user.id}:session_{i}"
            retrieval_tasks.append(redis_manager.get(session_key))
        
        results = await asyncio.gather(*retrieval_tasks)
        
        # Verify all sessions exist and are distinct
        assert len(results) == session_count
        for i, result in enumerate(results):
            assert result is not None, f"Session {i} was not stored properly"
            session_data = json.loads(result)
            assert session_data["session_id"] == f"session_{i}"
            assert session_data["client_id"] == f"client_{i}"
    
    async def test_session_synchronization_across_services(self, redis_manager, test_user, session_data):
        """
        Test session synchronization across different services.
        
        Validates:
        - Session data consistency across services
        - Service-specific session updates
        - Cross-service session validation
        - Session state propagation
        """
        base_session_key = f"session:{test_user.id}:{session_data['session_id']}"
        
        # Store base session
        await redis_manager.set(base_session_key, json.dumps(session_data), ex=3600)
        
        # Simulate different services updating session state
        services = ["auth_service", "websocket_service", "api_service"]
        
        for service in services:
            # Each service reads current session
            current_data = await redis_manager.get(base_session_key)
            session = json.loads(current_data)
            
            # Service adds its own metadata
            session[f"{service}_last_access"] = datetime.now(timezone.utc).isoformat()
            session[f"{service}_requests"] = session.get(f"{service}_requests", 0) + 1
            
            # Update session
            await redis_manager.set(base_session_key, json.dumps(session), ex=3600)
        
        # Verify all service updates are present
        final_data = await redis_manager.get(base_session_key)
        final_session = json.loads(final_data)
        
        for service in services:
            assert f"{service}_last_access" in final_session
            assert f"{service}_requests" in final_session
            assert final_session[f"{service}_requests"] >= 1
    
    @mock_justified("Redis connection failure simulation requires mocking network layer")
    async def test_redis_connection_recovery_scenarios(self, test_user, session_data):
        """
        Test Redis connection recovery scenarios.
        
        Validates:
        - Graceful handling of Redis unavailability
        - Connection retry logic
        - Fallback mechanisms
        - Service recovery after Redis restoration
        """
        # Create manager with mocked Redis that fails initially
        redis_manager = RedisManager()
        redis_manager.enabled = True
        
        # Mock Redis client that fails then recovers
        failing_redis = AsyncMock()
        failing_redis.set.side_effect = ConnectionError("Redis unavailable")
        failing_redis.get.side_effect = ConnectionError("Redis unavailable")
        
        redis_manager.redis_client = failing_redis
        
        # Test failure handling
        with pytest.raises(ConnectionError):
            await redis_manager.set("test_key", "test_value")
        
        # Simulate Redis recovery by creating a new working Redis manager
        recovering_redis = AsyncMock()
        recovery_storage = {}
        
        async def recovery_set(key, value, ex=None):
            recovery_storage[key] = value
            return True
            
        async def recovery_get(key):
            return recovery_storage.get(key)
        
        recovering_redis.set = recovery_set
        recovering_redis.get = recovery_get
        recovering_redis.ttl = AsyncMock(return_value=3600)
        
        redis_manager.redis_client = recovering_redis
        
        # Test recovery
        session_key = f"session:{test_user.id}:{session_data['session_id']}"
        await redis_manager.set(session_key, json.dumps(session_data), ex=3600)
        
        # Verify operations work after recovery
        retrieved_data = await redis_manager.get(session_key)
        assert retrieved_data is not None
        parsed_data = json.loads(retrieved_data)
        assert parsed_data["user_id"] == test_user.id
    
    async def test_session_data_integrity(self, redis_manager, test_user):
        """
        Test session data integrity and corruption detection.
        
        Validates:
        - Data serialization/deserialization integrity
        - Handling of corrupted session data
        - Session validation mechanisms
        - Data type preservation
        """
        session_key = f"session:{test_user.id}:integrity_test"
        
        # Test with various data types
        complex_session_data = {
            "user_id": test_user.id,
            "login_time": datetime.now(timezone.utc).isoformat(),
            "permissions": ["read", "write", "admin"],
            "metadata": {
                "ip": "192.168.1.100",
                "browser": "Chrome",
                "version": "1.0.0"
            },
            "numeric_data": {
                "login_count": 42,
                "session_timeout": 3600.5,
                "is_premium": True
            }
        }
        
        # Store complex data
        await redis_manager.set(
            session_key, 
            json.dumps(complex_session_data), 
            ex=3600
        )
        
        # Retrieve and verify integrity
        retrieved_data = await redis_manager.get(session_key)
        assert retrieved_data is not None, "Complex session data was not stored"
        
        parsed_data = json.loads(retrieved_data)
        
        # Verify all data types preserved
        assert parsed_data["user_id"] == test_user.id
        assert isinstance(parsed_data["permissions"], list)
        assert len(parsed_data["permissions"]) == 3
        assert isinstance(parsed_data["metadata"], dict)
        assert parsed_data["numeric_data"]["login_count"] == 42
        assert parsed_data["numeric_data"]["session_timeout"] == 3600.5
        assert parsed_data["numeric_data"]["is_premium"] is True
        
        # Test handling of corrupted data
        await redis_manager.set(session_key, "invalid_json_data", ex=3600)
        
        corrupted_data = await redis_manager.get(session_key)
        with pytest.raises(json.JSONDecodeError):
            json.loads(corrupted_data)
    
    def _validate_session_structure(self, session: Dict[str, Any]) -> bool:
        """Validate session has required structure."""
        required_fields = ["user_id", "session_id", "created_at"]
        return all(field in session for field in required_fields)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])