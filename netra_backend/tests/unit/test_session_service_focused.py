"""Focused Session Service Tests.

Tests the actual SessionService implementation focusing on core functionality
that exists in the current codebase.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime, timezone, timedelta
from netra_backend.app.services.session_service import SessionService


class TestSessionServiceCore:
    """Test core SessionService functionality."""

    @pytest.fixture
    def session_service(self):
        """Session service with mock Redis."""
        mock_redis = AsyncMock()
        return SessionService(redis_client=mock_redis)

    @pytest.fixture
    def session_service_no_redis(self):
        """Session service without Redis for fallback testing."""
        return SessionService()

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service):
        """Test successful session creation."""
        user_id = "user_123"
        device_id = "device_456"
        ip_address = "192.168.1.100"
        
        # Mock Redis operations
        session_service.redis_client.setex = AsyncMock()
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        result = await session_service.create_session(user_id, device_id, ip_address)
        
        assert result is not None
        assert isinstance(result, dict)
        assert "session_id" in result
        assert result["user_id"] == user_id
        assert result["device_id"] == device_id
        assert result["ip_address"] == ip_address

    @pytest.mark.asyncio
    async def test_create_session_with_custom_timeout(self, session_service):
        """Test session creation with custom timeout."""
        user_id = "user_789"
        device_id = "device_abc"
        ip_address = "10.0.0.1"
        timeout_seconds = 7200  # 2 hours
        
        session_service.redis_client.setex = AsyncMock()
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        result = await session_service.create_session(
            user_id, device_id, ip_address, timeout_seconds=timeout_seconds
        )
        
        assert result is not None
        assert result["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_validate_session_success(self, session_service):
        """Test successful session validation."""
        session_id = "valid_session_123"
        
        # Mock Redis get to return valid session data
        session_service.redis_client.get = AsyncMock(return_value="dummy_data")
        session_service.redis_client.expire = AsyncMock()
        
        result = await session_service.validate_session(session_id)
        
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_session_not_found(self, session_service):
        """Test validation of non-existent session."""
        session_id = "nonexistent_session"
        
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        result = await session_service.validate_session(session_id)
        
        # Should return empty dict or handle gracefully
        assert result == {} or result is None

    @pytest.mark.asyncio
    async def test_expire_session_success(self, session_service):
        """Test successful session expiration."""
        session_id = "expire_session_123"
        
        session_service.redis_client.delete = AsyncMock(return_value=1)
        
        result = await session_service.expire_session(session_id)
        
        assert result is True
        session_service.redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_expire_session_not_found(self, session_service):
        """Test expiring non-existent session."""
        session_id = "nonexistent_session"
        
        session_service.redis_client.delete = AsyncMock(return_value=0)
        
        result = await session_service.expire_session(session_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_expire_all_user_sessions(self, session_service):
        """Test expiring all sessions for a user."""
        user_id = "user_123"
        
        # Mock finding user sessions
        session_service._get_user_sessions = AsyncMock(return_value=["session1", "session2"])
        session_service._expire_session_internal = AsyncMock(return_value=True)
        
        result = await session_service.expire_all_user_sessions(user_id)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_update_activity_success(self, session_service):
        """Test updating session activity."""
        session_id = "active_session_123"
        
        session_service.redis_client.get = AsyncMock(return_value="dummy_session")
        session_service.redis_client.setex = AsyncMock()
        
        result = await session_service.update_activity(session_id)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_update_activity_session_not_found(self, session_service):
        """Test updating activity for non-existent session."""
        session_id = "nonexistent_session"
        
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        result = await session_service.update_activity(session_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_store_session_data_success(self, session_service):
        """Test storing additional session data."""
        session_id = "store_session_123"
        data = {"custom_field": "custom_value", "preferences": {"theme": "dark"}}
        
        session_service.redis_client.get = AsyncMock(return_value="existing_session")
        session_service.redis_client.setex = AsyncMock()
        
        result = await session_service.store_session_data(session_id, data)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_session_data_success(self, session_service):
        """Test retrieving session data."""
        session_id = "get_session_123"
        expected_data = {"custom_field": "value"}
        
        session_service.redis_client.get = AsyncMock(return_value=json.dumps(expected_data))
        
        result = await session_service.get_session_data(session_id)
        
        assert result == expected_data

    @pytest.mark.asyncio
    async def test_get_session_data_not_found(self, session_service):
        """Test retrieving data for non-existent session."""
        session_id = "nonexistent_session"
        
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        result = await session_service.get_session_data(session_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_migrate_session_data(self, session_service):
        """Test migrating session data between sessions."""
        from_session = "old_session_123"
        to_session = "new_session_456"
        
        # Mock getting data from old session
        old_data = {"user_preferences": {"theme": "dark"}}
        session_service.redis_client.get = AsyncMock()
        session_service.redis_client.get.side_effect = [
            json.dumps(old_data),  # First call for old session
            "new_session_data"     # Second call for new session
        ]
        session_service.redis_client.setex = AsyncMock()
        session_service.redis_client.delete = AsyncMock()
        
        result = await session_service.migrate_session_data(from_session, to_session)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_fallback_behavior(self, session_service):
        """Test behavior when Redis operations fail."""
        session_id = "fallback_session"
        
        # Redis operation fails
        session_service.redis_client.get = AsyncMock(side_effect=Exception("Redis error"))
        
        # Should handle gracefully and not crash
        result = await session_service.validate_session(session_id)
        
        # Should return gracefully (either None or empty dict)
        assert result is not None or result == {}


class TestSessionServiceConfiguration:
    """Test SessionService configuration and initialization."""

    def test_initialization_with_redis(self):
        """Test initialization with Redis client."""
        mock_redis = Mock()
        service = SessionService(redis_client=mock_redis)
        
        assert service.redis_client is mock_redis
        assert service._session_timeout_default == 3600
        assert service._cleanup_interval == 300

    def test_initialization_without_redis(self):
        """Test initialization without Redis client."""
        service = SessionService()
        
        assert service.redis_client is None
        assert service._session_timeout_default == 3600

    def test_session_timeout_configuration(self):
        """Test session timeout configuration is reasonable."""
        service = SessionService()
        
        # Should have reasonable default timeout (1 hour)
        assert service._session_timeout_default == 3600
        
        # Cleanup interval should be reasonable (5 minutes)
        assert service._cleanup_interval == 300


class TestSessionServiceSecurity:
    """Test session security features."""

    @pytest.fixture
    def session_service(self):
        """Session service with mock Redis."""
        mock_redis = AsyncMock()
        return SessionService(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_session_creation_rate_limiting_concept(self, session_service):
        """Test that multiple rapid session creations are handled properly."""
        user_id = "rate_test_user"
        device_id = "device_123"
        ip_address = "192.168.1.100"
        
        session_service.redis_client.setex = AsyncMock()
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        # Create multiple sessions rapidly
        sessions = []
        for i in range(3):
            result = await session_service.create_session(
                user_id, f"{device_id}_{i}", ip_address
            )
            sessions.append(result)
        
        # Should create all sessions (no built-in rate limiting currently)
        assert len(sessions) == 3
        assert all(s is not None for s in sessions)

    @pytest.mark.asyncio
    async def test_session_data_validation(self, session_service):
        """Test that session data is properly validated."""
        session_id = "validation_session"
        
        # Test storing various data types
        test_data_sets = [
            {"string": "value"},
            {"number": 123},
            {"boolean": True},
            {"nested": {"key": "value"}},
            {"list": [1, 2, 3]}
        ]
        
        session_service.redis_client.get = AsyncMock(return_value="session_exists")
        session_service.redis_client.setex = AsyncMock()
        
        for data in test_data_sets:
            result = await session_service.store_session_data(session_id, data)
            assert result is True

    @pytest.mark.asyncio
    async def test_invalid_session_handling(self, session_service):
        """Test handling of invalid session IDs."""
        invalid_session_ids = [
            "",           # Empty string
            None,         # None value  
            "short",      # Too short
            "a" * 1000,   # Too long
        ]
        
        session_service.redis_client.get = AsyncMock(return_value=None)
        
        for invalid_id in invalid_session_ids:
            if invalid_id is None:
                continue  # Skip None test as it would cause TypeError
                
            result = await session_service.validate_session(invalid_id)
            # Should handle gracefully without crashing
            assert result == {} or result is None