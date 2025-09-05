"""
Comprehensive unit tests for Database Repository and Models
Tests database operations, models, and repository methods
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy import select
from auth_service.auth_core.database.models import DBUser, DBSession, DBAuditLog
from auth_service.auth_core.database.repository import AuthRepository
from auth_service.auth_core.database.connection import auth_db


class TestAuthRepository:
    """Test AuthRepository database operations"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.repository = AuthRepository()
        self.email = f"repo_test_{uuid.uuid4()}@example.com"
        self.username = f"repo_user_{uuid.uuid4()}"
        self.password_hash = "hashed_password_123"
        
        # Clean up any existing test data
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            async with auth_db.get_session() as session:
                # Clean up test users
                result = await session.execute(
                    select(DBUser).where(DBUser.email.like("repo_test_%"))
                )
                users = result.scalars().all()
                for user in users:
                    await session.delete(user)
                await session.commit()
        except Exception:
            pass  # Ignore cleanup errors
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a new user"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        assert user is not None
        assert user.email == self.email
        assert user.username == self.username
        assert user.password_hash == self.password_hash
        assert user.id is not None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        """Test getting user by ID"""
        created = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        user = await self.repository.get_user_by_id(created.id)
        assert user is not None
        assert user.id == created.id
        assert user.email == self.email
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        """Test getting user by email"""
        await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        user = await self.repository.get_user_by_email(self.email)
        assert user is not None
        assert user.email == self.email
        assert user.username == self.username
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self):
        """Test getting user by username"""
        await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        user = await self.repository.get_user_by_username(self.username)
        assert user is not None
        assert user.username == self.username
        assert user.email == self.email
    
    @pytest.mark.asyncio
    async def test_update_user(self):
        """Test updating user information"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        
        new_username = f"updated_{uuid.uuid4()}"
        updated = await self.repository.update_user(
            user_id=user.id,
            username=new_username,
            full_name="Updated User"
        )
        assert updated is not None
        assert updated.username == new_username
        assert updated.full_name == "Updated User"
    
    @pytest.mark.asyncio
    async def test_update_user_password(self):
        """Test updating user password"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        
        new_password_hash = "new_hashed_password_456"
        result = await self.repository.update_user_password(user.id, new_password_hash)
        assert result is True
        
        updated = await self.repository.get_user_by_id(user.id)
        assert updated.password_hash == new_password_hash
    
    @pytest.mark.asyncio
    async def test_delete_user(self):
        """Test deleting user"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        
        result = await self.repository.delete_user(user.id)
        assert result is True
        
        deleted = await self.repository.get_user_by_id(user.id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_verify_user_email(self):
        """Test verifying user email"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        assert user.email_verified is False
        
        result = await self.repository.verify_user_email(user.id)
        assert result is True
        
        verified = await self.repository.get_user_by_id(user.id)
        assert verified.email_verified is True
    
    @pytest.mark.asyncio
    async def test_update_last_login(self):
        """Test updating user's last login time"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        
        result = await self.repository.update_last_login(user.id)
        assert result is True
        
        updated = await self.repository.get_user_by_id(user.id)
        assert updated.last_login is not None
        assert (datetime.now(timezone.utc) - updated.last_login).total_seconds() < 5
    
    @pytest.mark.asyncio
    async def test_activate_user(self):
        """Test activating user"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        
        # First deactivate
        await self.repository.deactivate_user(user.id)
        deactivated = await self.repository.get_user_by_id(user.id)
        assert deactivated.is_active is False
        
        # Then activate
        result = await self.repository.activate_user(user.id)
        assert result is True
        
        activated = await self.repository.get_user_by_id(user.id)
        assert activated.is_active is True
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self):
        """Test deactivating user"""
        user = await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        assert user.is_active is True
        
        result = await self.repository.deactivate_user(user.id)
        assert result is True
        
        deactivated = await self.repository.get_user_by_id(user.id)
        assert deactivated.is_active is False
    
    @pytest.mark.asyncio
    async def test_list_users(self):
        """Test listing users with pagination"""
        # Create multiple users
        for i in range(5):
            await self.repository.create_user(
                email=f"repo_test_{i}_{uuid.uuid4()}@example.com",
                password_hash=f"hash_{i}",
                username=f"repo_user_{i}_{uuid.uuid4()}"
            )
        
        users = await self.repository.list_users(limit=3, offset=0)
        assert len(users) >= 3
        
        # Test pagination
        page2 = await self.repository.list_users(limit=3, offset=3)
        assert len(page2) >= 0
        assert all(u.id not in [user.id for user in users] for u in page2)
    
    @pytest.mark.asyncio
    async def test_count_users(self):
        """Test counting total users"""
        initial_count = await self.repository.count_users()
        
        # Create new user
        await self.repository.create_user(
            email=self.email,
            password_hash=self.password_hash,
            username=self.username
        )
        
        new_count = await self.repository.count_users()
        assert new_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_search_users(self):
        """Test searching users"""
        # Create test users
        await self.repository.create_user(
            email="search_test_1@example.com",
            password_hash="hash1",
            username="search_user_alpha"
        )
        await self.repository.create_user(
            email="search_test_2@example.com",
            password_hash="hash2",
            username="search_user_beta"
        )
        
        # Search by username
        results = await self.repository.search_users("alpha")
        assert len(results) >= 1
        assert any(u.username == "search_user_alpha" for u in results)
        
        # Search by email
        results = await self.repository.search_users("search_test")
        assert len(results) >= 2


class TestSessionRepository:
    """Test session-related repository operations"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.repository = AuthRepository()
        # Create a test user for sessions
        self.user = await self.repository.create_user(
            email=f"session_test_{uuid.uuid4()}@example.com",
            password_hash="hash",
            username=f"session_user_{uuid.uuid4()}"
        )
        self.token = f"token_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a session"""
        session = await self.repository.create_session(
            user_id=self.user.id,
            token=self.token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert session is not None
        assert session.user_id == self.user.id
        assert session.token == self.token
        assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_session_by_token(self):
        """Test getting session by token"""
        created = await self.repository.create_session(
            user_id=self.user.id,
            token=self.token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        session = await self.repository.get_session_by_token(self.token)
        assert session is not None
        assert session.id == created.id
        assert session.token == self.token
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self):
        """Test getting all sessions for a user"""
        # Create multiple sessions
        for i in range(3):
            await self.repository.create_session(
                user_id=self.user.id,
                token=f"token_{i}_{uuid.uuid4()}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
        
        sessions = await self.repository.get_user_sessions(self.user.id)
        assert len(sessions) >= 3
        assert all(s.user_id == self.user.id for s in sessions)
    
    @pytest.mark.asyncio
    async def test_invalidate_session(self):
        """Test invalidating a session"""
        session = await self.repository.create_session(
            user_id=self.user.id,
            token=self.token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert session.is_active is True
        
        result = await self.repository.invalidate_session(session.id)
        assert result is True
        
        invalidated = await self.repository.get_session_by_token(self.token)
        assert invalidated.is_active is False
    
    @pytest.mark.asyncio
    async def test_invalidate_user_sessions(self):
        """Test invalidating all user sessions"""
        # Create multiple sessions
        for i in range(3):
            await self.repository.create_session(
                user_id=self.user.id,
                token=f"token_{i}_{uuid.uuid4()}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
        
        result = await self.repository.invalidate_user_sessions(self.user.id)
        assert result is True
        
        sessions = await self.repository.get_user_sessions(self.user.id)
        active_sessions = [s for s in sessions if s.is_active]
        assert len(active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        # Create expired session
        await self.repository.create_session(
            user_id=self.user.id,
            token="expired_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Create valid session
        await self.repository.create_session(
            user_id=self.user.id,
            token="valid_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        deleted_count = await self.repository.cleanup_expired_sessions()
        assert deleted_count >= 1
        
        # Expired session should be gone
        expired = await self.repository.get_session_by_token("expired_token")
        assert expired is None
        
        # Valid session should remain
        valid = await self.repository.get_session_by_token("valid_token")
        assert valid is not None
    
    @pytest.mark.asyncio
    async def test_extend_session(self):
        """Test extending session expiry"""
        session = await self.repository.create_session(
            user_id=self.user.id,
            token=self.token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        original_expiry = session.expires_at
        
        result = await self.repository.extend_session(
            session.id,
            datetime.now(timezone.utc) + timedelta(hours=2)
        )
        assert result is True
        
        extended = await self.repository.get_session_by_token(self.token)
        assert extended.expires_at > original_expiry


class TestAuditLogRepository:
    """Test audit log repository operations"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.repository = AuthRepository()
        # Create a test user for audit logs
        self.user = await self.repository.create_user(
            email=f"audit_test_{uuid.uuid4()}@example.com",
            password_hash="hash",
            username=f"audit_user_{uuid.uuid4()}"
        )
    
    @pytest.mark.asyncio
    async def test_create_audit_log(self):
        """Test creating an audit log entry"""
        log = await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="login",
            event_data={"ip": "127.0.0.1", "user_agent": "TestAgent"}
        )
        assert log is not None
        assert log.user_id == self.user.id
        assert log.event_type == "login"
        assert log.event_data["ip"] == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_get_user_audit_logs(self):
        """Test getting user audit logs"""
        # Create multiple audit logs
        events = ["login", "logout", "password_change"]
        for event in events:
            await self.repository.create_audit_log(
                user_id=self.user.id,
                event_type=event,
                event_data={"test": True}
            )
        
        logs = await self.repository.get_user_audit_logs(self.user.id)
        assert len(logs) >= 3
        assert all(log.user_id == self.user.id for log in logs)
        assert set(log.event_type for log in logs) >= set(events)
    
    @pytest.mark.asyncio
    async def test_get_recent_audit_logs(self):
        """Test getting recent audit logs"""
        # Create old and new logs
        old_log = await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="old_event",
            event_data={}
        )
        # Manually update timestamp to be old
        async with auth_db.get_session() as session:
            stmt = select(DBAuditLog).where(DBAuditLog.id == old_log.id)
            result = await session.execute(stmt)
            db_log = result.scalar_one()
            db_log.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
            await session.commit()
        
        # Create recent log
        await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="recent_event",
            event_data={}
        )
        
        recent = await self.repository.get_recent_audit_logs(hours=1)
        assert len(recent) >= 1
        assert all(log.event_type != "old_event" for log in recent)
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_type(self):
        """Test getting audit logs by event type"""
        # Create logs of different types
        await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="login",
            event_data={}
        )
        await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="logout",
            event_data={}
        )
        await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="login",
            event_data={}
        )
        
        login_logs = await self.repository.get_audit_logs_by_type("login")
        assert len(login_logs) >= 2
        assert all(log.event_type == "login" for log in login_logs)
    
    @pytest.mark.asyncio
    async def test_count_user_events(self):
        """Test counting user events by type"""
        # Create multiple login events
        for _ in range(3):
            await self.repository.create_audit_log(
                user_id=self.user.id,
                event_type="login",
                event_data={}
            )
        
        count = await self.repository.count_user_events(self.user.id, "login")
        assert count >= 3
    
    @pytest.mark.asyncio
    async def test_cleanup_old_audit_logs(self):
        """Test cleaning up old audit logs"""
        # Create old log
        old_log = await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="old_event",
            event_data={}
        )
        
        # Manually update timestamp to be very old
        async with auth_db.get_session() as session:
            stmt = select(DBAuditLog).where(DBAuditLog.id == old_log.id)
            result = await session.execute(stmt)
            db_log = result.scalar_one()
            db_log.created_at = datetime.now(timezone.utc) - timedelta(days=100)
            await session.commit()
        
        # Create recent log
        recent_log = await self.repository.create_audit_log(
            user_id=self.user.id,
            event_type="recent_event",
            event_data={}
        )
        
        # Clean up logs older than 90 days
        deleted = await self.repository.cleanup_old_audit_logs(days=90)
        assert deleted >= 1
        
        # Old log should be gone
        old_logs = await self.repository.get_audit_logs_by_type("old_event")
        assert len([l for l in old_logs if l.id == old_log.id]) == 0
        
        # Recent log should remain
        recent_logs = await self.repository.get_audit_logs_by_type("recent_event")
        assert any(l.id == recent_log.id for l in recent_logs)