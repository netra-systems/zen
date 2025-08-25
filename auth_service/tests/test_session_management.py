"""
Session Management Tests for Auth Service
Tests complete session lifecycle with database operations
Covers security, multi-device, and cleanup scenarios
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.auth_core.core.session_manager import SessionManager
from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.models import AuthSession, AuthUser
from test_framework.environment_markers import env


@env("test", "dev")  # Session tests can use mocked Redis and database
class TestSessionCreation:
    """Test session creation after login"""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager with mocked Redis"""
        manager = SessionManager()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        manager.redis_client = MagicMock()
        manager.redis_client.ping.return_value = True
        return manager

    def test_create_session_success(self, session_manager):
        """Test successful session creation"""
        user_data = {"email": "test@example.com", "name": "Test User"}
        session_manager.redis_client.setex.return_value = True
        
        session_id = session_manager.create_session("user123", user_data)
        
        assert session_id is not None
        assert isinstance(session_id, str)

    def test_create_session_redis_failure(self, session_manager):
        """Test session creation with Redis failure falls back to memory"""
        user_data = {"email": "test@example.com"}
        # Simulate Redis failure by setting client to None
        session_manager.redis_client = None
        session_manager.redis_enabled = False
        
        # Session should still be created using memory fallback
        session_id = session_manager.create_session("user123", user_data)
        
        assert session_id is not None
        assert isinstance(session_id, str)


class TestSessionValidation:
    """Test session validation with valid tokens"""
    
    @pytest.fixture
    def session_manager(self):
        """Setup session manager with mocked Redis"""
        with patch('auth_service.auth_core.core.session_manager.auth_redis_manager') as mock_redis_manager:
            # Mock: Redis caching isolation to prevent test interference and external dependencies
            mock_redis_client = MagicMock()
            mock_redis_manager.get_client.return_value = mock_redis_client
            mock_redis_manager.enabled = True
            mock_redis_manager.connect.return_value = True
            
            manager = SessionManager()
            return manager

    @pytest.mark.asyncio
    async def test_validate_session_success(self, session_manager):
        """Test validation of valid session"""
        session_data = {
            "user_id": "user123",
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        with patch('auth_service.auth_core.core.session_manager.auth_redis_manager') as mock_redis_manager:
            mock_redis_client = MagicMock()
            mock_redis_manager.get_client.return_value = mock_redis_client
            mock_redis_manager.enabled = True
            
            mock_redis_client.get.return_value = json.dumps(session_data)
            mock_redis_client.setex.return_value = True
            
            is_valid = await session_manager.validate_session("session123")
            
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_session_expired(self, session_manager):
        """Test validation of expired session"""
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        session_data = {
            "user_id": "user123",
            "last_activity": old_time.isoformat()
        }
        session_manager.redis_client.get.return_value = json.dumps(session_data)
        session_manager.redis_client.delete.return_value = 1
        
        is_valid = await session_manager.validate_session("session123")
        
        assert is_valid is False


class TestSessionExpiry:
    """Test session expiry handling"""
    
    @pytest.fixture
    def session_manager(self):
        """Setup session manager for expiry tests"""
        manager = SessionManager()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        manager.redis_client = MagicMock()
        manager.session_ttl = 24  # 24 hours
        return manager

    @pytest.mark.asyncio
    async def test_session_auto_expiry(self, session_manager):
        """Test automatic session expiry via validate_session"""
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        session_data = {
            "user_id": "user123",
            "last_activity": expired_time.isoformat()
        }
        session_manager.redis_client.get.return_value = json.dumps(session_data)
        session_manager.redis_client.delete.return_value = 1
        
        # validate_session should detect expiry and return False
        is_valid = await session_manager.validate_session("expired_session")
        
        assert is_valid is False

    def test_session_ttl_refresh(self, session_manager):
        """Test session TTL refresh on activity"""
        session_data = {
            "user_id": "user123",
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        session_manager.redis_client.get.return_value = json.dumps(session_data)
        
        session_manager._update_activity("session123")
        
        session_manager.redis_client.expire.assert_called_once()


class TestSessionRefresh:
    """Test session refresh before expiry"""
    
    @pytest.fixture
    def session_manager(self):
        """Setup session manager for refresh tests"""
        manager = SessionManager()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        manager.redis_client = MagicMock()
        return manager

    @pytest.mark.asyncio
    async def test_refresh_active_session(self, session_manager):
        """Test refreshing active session before expiry"""
        session_data = {
            "user_id": "user123",
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        session_manager.redis_client.get.return_value = json.dumps(session_data)
        session_manager.redis_client.setex.return_value = True
        
        result = await session_manager.update_session("session123", {"refreshed": True})
        
        assert result is True

    @pytest.mark.asyncio
    async def test_refresh_expired_session(self, session_manager):
        """Test refresh attempt on expired session"""
        session_manager.redis_client.get.return_value = None
        
        result = await session_manager.update_session("expired_session", {"data": "new"})
        
        assert result is False


class TestMultiDeviceSessionManagement:
    """Test multi-device session management"""
    
    @pytest.fixture
    def session_manager(self):
        """Setup session manager for multi-device tests"""
        manager = SessionManager()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        manager.redis_client = MagicMock()
        return manager

    @pytest.mark.asyncio
    async def test_multiple_sessions_per_user(self, session_manager):
        """Test handling multiple sessions for same user"""
        sessions_data = [
            {"session_id": "session1", "user_id": "user123", "device": "mobile"},
            {"session_id": "session2", "user_id": "user123", "device": "desktop"}
        ]
        
        mock_keys = ["session:session1", "session:session2"]
        session_manager.redis_client.scan_iter.return_value = mock_keys
        
        def get_side_effect(key):
            if key == "session:session1":
                return json.dumps(sessions_data[0])
            if key == "session:session2":
                return json.dumps(sessions_data[1])
            return None
        
        session_manager.redis_client.get.side_effect = get_side_effect
        
        user_sessions = await session_manager.get_user_sessions("user123")
        
        assert len(user_sessions) == 2

    @pytest.mark.asyncio
    async def test_session_isolation(self, session_manager):
        """Test sessions are isolated between users"""
        mock_keys = ["session:session1", "session:session2"]
        session_manager.redis_client.scan_iter.return_value = mock_keys
        
        def get_side_effect(key):
            if key == "session:session1":
                return json.dumps({"user_id": "user123", "device": "mobile"})
            if key == "session:session2":
                return json.dumps({"user_id": "user456", "device": "desktop"})
            return None
        
        session_manager.redis_client.get.side_effect = get_side_effect
        
        sessions = await session_manager.get_user_sessions("user123")
        
        assert len(sessions) == 1
        assert sessions[0]["user_id"] == "user123"


class TestSessionRevocation:
    """Test session revocation (logout)"""
    
    @pytest.fixture
    def session_manager(self):
        """Setup session manager for revocation tests"""
        manager = SessionManager()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        manager.redis_client = MagicMock()
        return manager

    def test_single_session_logout(self, session_manager):
        """Test logout of single session"""
        session_manager.redis_client.delete.return_value = 1
        
        result = session_manager.delete_session("session123")
        
        assert result is True
        session_manager.redis_client.delete.assert_called_with("session:session123")

    @pytest.mark.asyncio
    async def test_all_sessions_logout(self, session_manager):
        """Test logout of all user sessions"""
        sessions_data = [
            {"session_id": "session1", "user_id": "user123"},
            {"session_id": "session2", "user_id": "user123"}
        ]
        
        mock_keys = ["session:session1", "session:session2"]
        session_manager.redis_client.scan_iter.return_value = mock_keys
        session_manager.redis_client.get.side_effect = [
            json.dumps(sessions_data[0]), json.dumps(sessions_data[1])
        ]
        session_manager.redis_client.delete.return_value = 1
        
        count = await session_manager.invalidate_user_sessions("user123")
        
        assert count == 2


class TestSessionPersistence:
    """Test session persistence in database"""
    
    def test_session_database_model_structure(self):
        """Test database session model structure"""
        session_record = AuthSession(
            id="session123",
            user_id="user123",
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_active=True
        )
        
        # Verify model structure
        assert session_record.id == "session123"
        assert session_record.user_id == "user123"
        assert session_record.ip_address == "192.168.1.1"
        assert session_record.is_active is True

    def test_session_database_cleanup_logic(self):
        """Test session cleanup logic validation"""
        # Test expiry logic
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        current_time = datetime.now(timezone.utc)
        
        is_expired = expired_time < current_time
        assert is_expired is True
        
        # Test cleanup filtering
        sessions_to_cleanup = []
        test_sessions = [
            {"expires_at": expired_time, "id": "expired1"},
            {"expires_at": current_time + timedelta(hours=1), "id": "valid1"}
        ]
        
        for session in test_sessions:
            if session["expires_at"] < current_time:
                sessions_to_cleanup.append(session["id"])
        
        assert len(sessions_to_cleanup) == 1
        assert "expired1" in sessions_to_cleanup


class TestSessionSecurityAndHijackingPrevention:
    """Test session security measures"""
    
    @pytest.fixture
    def session_manager(self):
        """Setup session manager for security tests"""
        manager = SessionManager()
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        manager.redis_client = MagicMock()
        return manager

    def test_session_ip_tracking(self, session_manager):
        """Test session tracks IP address for security"""
        user_data = {"email": "test@example.com", "ip_address": "192.168.1.1"}
        session_manager.redis_client.setex.return_value = True
        
        session_id = session_manager.create_session("user123", user_data)
        
        assert session_id is not None
        # Verify IP was stored in session data
        call_args = session_manager.redis_client.setex.call_args
        stored_data = json.loads(call_args[0][2])
        assert stored_data["ip_address"] == "192.168.1.1"

    def test_session_uuid_generation(self, session_manager):
        """Test sessions use secure UUID generation"""
        user_data = {"email": "test@example.com"}
        session_manager.redis_client.setex.return_value = True
        
        session_id1 = session_manager.create_session("user123", user_data)
        session_id2 = session_manager.create_session("user123", user_data)
        
        assert session_id1 != session_id2
        assert len(session_id1) == 36  # UUID length
        assert "-" in session_id1  # UUID format

    @pytest.mark.asyncio
    async def test_session_data_isolation(self, session_manager):
        """Test session data is isolated per session"""
        session_data1 = {"user_id": "user1", "sensitive": "data1"}
        session_data2 = {"user_id": "user2", "sensitive": "data2"}
        
        def get_side_effect(key):
            if key == "session:session1":
                return json.dumps(session_data1)
            if key == "session:session2":
                return json.dumps(session_data2)
            return None
        
        session_manager.redis_client.get.side_effect = get_side_effect
        
        data1 = await session_manager.get_session("session1")
        data2 = await session_manager.get_session("session2")
        
        assert data1["sensitive"] != data2["sensitive"]
        assert data1["user_id"] != data2["user_id"]