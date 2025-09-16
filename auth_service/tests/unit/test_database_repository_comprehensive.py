"""
Comprehensive unit tests for Database Repository and Models
Tests database operations, models, and repository methods
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy import select, delete
from auth_service.auth_core.database.models import AuthUser as DBUser, AuthSession as DBSession, AuthAuditLog as DBAuditLog
from auth_service.auth_core.database.repository import AuthUserRepository, AuthSessionRepository, AuthAuditRepository
from auth_service.auth_core.database.connection import auth_db
from shared.isolated_environment import IsolatedEnvironment


class AuthUserRepositoryTests:
    """Test AuthUserRepository database operations"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        async with auth_db.get_session() as session:
            self.repository = AuthUserRepository(session)
            self.email = f"repo_test_{uuid.uuid4()}@example.com"
            self.password_hash = "hashed_password_123"
            
            # Clean up any existing test data
            await self.cleanup_test_data(session)
    
    async def cleanup_test_data(self, session):
        """Clean up test data from database"""
        try:
            # Clean up test users
            await session.execute(
                delete(DBUser).where(DBUser.email.like("repo_test_%"))
            )
            await session.execute(
                delete(DBUser).where(DBUser.email.like("oauth_test_%"))
            )
            await session.commit()
        except Exception:
            pass  # Ignore cleanup errors
    
    @pytest.mark.asyncio
    async def test_get_by_email_nonexistent(self):
        """Test getting user by email that doesn't exist"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            user = await repository.get_by_email("nonexistent@example.com")
            assert user is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self):
        """Test getting user by ID that doesn't exist"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            user = await repository.get_by_id("nonexistent-id")
            assert user is None
    
    @pytest.mark.asyncio
    async def test_create_oauth_user(self):
        """Test creating OAuth user"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            user_info = {
                "email": f"oauth_test_{uuid.uuid4()}@example.com",
                "name": "Test User",
                "provider": "google",
                "id": f"google_{uuid.uuid4()}",
                "picture": "https://example.com/pic.jpg"
            }
            
            user = await repository.create_oauth_user(user_info)
            await session.commit()
            
            assert user is not None
            assert user.email == user_info["email"]
            assert user.full_name == user_info["name"]
            assert user.auth_provider == "google"
            assert user.is_active is True
            assert user.is_verified is True
    
    @pytest.mark.asyncio
    async def test_create_oauth_user_existing_updates(self):
        """Test that creating OAuth user for existing email updates the user"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            email = f"oauth_test_{uuid.uuid4()}@example.com"
            
            # Create first OAuth user
            user_info1 = {
                "email": email,
                "name": "Test User 1",
                "provider": "google",
                "id": f"google_{uuid.uuid4()}",
            }
            user1 = await repository.create_oauth_user(user_info1)
            await session.commit()
            
            # Create second OAuth user with same email but different info
            user_info2 = {
                "email": email,
                "name": "Test User Updated",
                "provider": "google",
                "id": f"google_{uuid.uuid4()}",
            }
            user2 = await repository.create_oauth_user(user_info2)
            await session.commit()
            
            # Should be the same user record, just updated
            assert user1.id == user2.id
            assert user2.full_name == "Test User Updated"
    
    @pytest.mark.asyncio
    async def test_create_local_user(self):
        """Test creating local user with password"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            email = f"local_test_{uuid.uuid4()}@example.com"
            password_hash = "hashed_password_123"
            full_name = "Local Test User"
            
            user = await repository.create_local_user(email, password_hash, full_name)
            await session.commit()
            
            assert user is not None
            assert user.email == email
            assert user.hashed_password == password_hash
            assert user.full_name == full_name
            assert user.auth_provider == "local"
            assert user.is_active is True
            assert user.is_verified is False  # Local users need verification
    
    @pytest.mark.asyncio
    async def test_create_local_user_duplicate_email(self):
        """Test that creating local user with duplicate email raises error"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            email = f"local_test_{uuid.uuid4()}@example.com"
            
            # Create first user
            user1 = await repository.create_local_user(email, "hash1")
            await session.commit()
            
            # Attempt to create second user with same email should fail
            with pytest.raises(ValueError, match="already exists"):
                await repository.create_local_user(email, "hash2")
    
    @pytest.mark.asyncio
    async def test_update_login_time(self):
        """Test updating user's last login time"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            # Create a test user
            user = await repository.create_local_user(
                f"login_test_{uuid.uuid4()}@example.com",
                "password_hash"
            )
            await session.flush()
            original_login = user.last_login_at
            
            # Update login time
            await repository.update_login_time(user.id)
            await session.commit()
            
            # Verify login time was updated
            updated_user = await repository.get_by_id(user.id)
            assert updated_user.last_login_at != original_login
            assert updated_user.last_login_at is not None
    
    @pytest.mark.asyncio
    async def test_failed_login_attempts(self):
        """Test incrementing and resetting failed login attempts"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            email = f"failed_test_{uuid.uuid4()}@example.com"
            user = await repository.create_local_user(email, "password_hash")
            await session.flush()
            
            # Increment failed attempts
            count1 = await repository.increment_failed_attempts(email)
            await session.commit()
            assert count1 == 1
            
            count2 = await repository.increment_failed_attempts(email)
            await session.commit()
            assert count2 == 2
            
            # Reset failed attempts
            await repository.reset_failed_attempts(user.id)
            await session.commit()
            
            # Verify reset
            updated_user = await repository.get_by_id(user.id)
            assert updated_user.failed_login_attempts == 0
    
    @pytest.mark.asyncio
    async def test_account_locking_after_failed_attempts(self):
        """Test that account gets locked after 5 failed attempts"""
        async with auth_db.get_session() as session:
            repository = AuthUserRepository(session)
            
            email = f"lock_test_{uuid.uuid4()}@example.com"
            user = await repository.create_local_user(email, "password_hash")
            await session.flush()
            
            # Make 5 failed attempts
            for i in range(5):
                await repository.increment_failed_attempts(email)
            await session.commit()
            
            # Check if account is locked
            is_locked = await repository.check_account_locked(email)
            assert is_locked is True
            
            # Verify user is deactivated
            locked_user = await repository.get_by_id(user.id)
            assert locked_user.is_active is False
            assert locked_user.locked_until is not None


class AuthSessionRepositoryTests:
    """Test AuthSessionRepository database operations"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        # Create test user first
        async with auth_db.get_session() as session:
            user_repo = AuthUserRepository(session)
            self.user = await user_repo.create_local_user(
                f"session_test_{uuid.uuid4()}@example.com",
                "password_hash"
            )
            await session.commit()
            self.user_id = self.user.id
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a session"""
        async with auth_db.get_session() as session:
            repository = AuthSessionRepository(session)
            
            refresh_token = f"refresh_token_{uuid.uuid4()}"
            client_info = {
                "ip": "127.0.0.1",
                "user_agent": "TestAgent/1.0",
                "device_id": f"device_{uuid.uuid4()}"
            }
            
            session_obj = await repository.create_session(
                self.user_id,
                refresh_token,
                client_info
            )
            await session.commit()
            
            assert session_obj is not None
            assert session_obj.user_id == self.user_id
            assert session_obj.ip_address == "127.0.0.1"
            assert session_obj.user_agent == "TestAgent/1.0"
            assert session_obj.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_active_session(self):
        """Test getting active session by ID"""
        async with auth_db.get_session() as session:
            repository = AuthSessionRepository(session)
            
            # Create session
            refresh_token = f"refresh_token_{uuid.uuid4()}"
            session_obj = await repository.create_session(
                self.user_id,
                refresh_token,
                {"ip": "127.0.0.1"}
            )
            await session.flush()
            
            # Get active session
            retrieved = await repository.get_active_session(session_obj.id)
            assert retrieved is not None
            assert retrieved.id == session_obj.id
            assert retrieved.is_active is True
    
    @pytest.mark.asyncio
    async def test_revoke_session(self):
        """Test revoking a session"""
        async with auth_db.get_session() as session:
            repository = AuthSessionRepository(session)
            
            # Create session
            refresh_token = f"refresh_token_{uuid.uuid4()}"
            session_obj = await repository.create_session(
                self.user_id,
                refresh_token,
                {"ip": "127.0.0.1"}
            )
            await session.flush()
            
            # Revoke session
            await repository.revoke_session(session_obj.id)
            await session.commit()
            
            # Verify session is revoked
            revoked = await repository.get_active_session(session_obj.id)
            assert revoked is None  # Should not return inactive sessions
    
    @pytest.mark.asyncio
    async def test_revoke_user_sessions(self):
        """Test revoking all sessions for a user"""
        async with auth_db.get_session() as session:
            repository = AuthSessionRepository(session)
            
            # Create multiple sessions
            sessions = []
            for i in range(3):
                refresh_token = f"refresh_token_{i}_{uuid.uuid4()}"
                session_obj = await repository.create_session(
                    self.user_id,
                    refresh_token,
                    {"ip": "127.0.0.1"}
                )
                sessions.append(session_obj)
            await session.flush()
            
            # Revoke all user sessions
            await repository.revoke_user_sessions(self.user_id)
            await session.commit()
            
            # Verify all sessions are revoked
            for session_obj in sessions:
                revoked = await repository.get_active_session(session_obj.id)
                assert revoked is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        async with auth_db.get_session() as session:
            repository = AuthSessionRepository(session)
            
            # Create expired session by manually setting expiry
            refresh_token = f"refresh_token_{uuid.uuid4()}"
            session_obj = await repository.create_session(
                self.user_id,
                refresh_token,
                {"ip": "127.0.0.1"}
            )
            # Manually expire it
            session_obj.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.flush()
            
            # Run cleanup
            await repository.cleanup_expired_sessions()
            await session.commit()
            
            # Verify expired session is deactivated
            expired = await repository.get_active_session(session_obj.id)
            assert expired is None


class AuthAuditRepositoryTests:
    """Test AuthAuditRepository database operations"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        # Create test user first
        async with auth_db.get_session() as session:
            user_repo = AuthUserRepository(session)
            self.user = await user_repo.create_local_user(
                f"audit_test_{uuid.uuid4()}@example.com",
                "password_hash"
            )
            await session.commit()
            self.user_id = self.user.id
    
    @pytest.mark.asyncio
    async def test_log_event(self):
        """Test logging an audit event"""
        async with auth_db.get_session() as session:
            repository = AuthAuditRepository(session)
            
            event_log = await repository.log_event(
                event_type="login",
                user_id=self.user_id,
                success=True,
                metadata={"action": "test"},
                client_info={"ip": "127.0.0.1", "user_agent": "TestAgent"}
            )
            await session.commit()
            
            assert event_log is not None
            assert event_log.event_type == "login"
            assert event_log.user_id == self.user_id
            assert event_log.success is True
            assert event_log.event_metadata["action"] == "test"
            assert event_log.ip_address == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_log_failed_event(self):
        """Test logging a failed event"""
        async with auth_db.get_session() as session:
            repository = AuthAuditRepository(session)
            
            event_log = await repository.log_event(
                event_type="login",
                user_id=self.user_id,
                success=False,
                error_message="Invalid password",
                client_info={"ip": "127.0.0.1"}
            )
            await session.commit()
            
            assert event_log is not None
            assert event_log.success is False
            assert event_log.error_message == "Invalid password"
    
    @pytest.mark.asyncio
    async def test_get_user_events(self):
        """Test getting user events"""
        async with auth_db.get_session() as session:
            repository = AuthAuditRepository(session)
            
            # Create multiple events
            events = ["login", "logout", "password_change"]
            for event_type in events:
                await repository.log_event(
                    event_type=event_type,
                    user_id=self.user_id,
                    success=True
                )
            await session.commit()
            
            # Get user events
            user_events = await repository.get_user_events(self.user_id, limit=10)
            assert len(user_events) >= 3
            assert all(event.user_id == self.user_id for event in user_events)
            
            # Check events are in correct order (most recent first)
            event_types = [event.event_type for event in user_events]
            assert "password_change" in event_types
            assert "logout" in event_types
            assert "login" in event_types
    
    @pytest.mark.asyncio
    async def test_log_event_without_user(self):
        """Test logging system event without user"""
        async with auth_db.get_session() as session:
            repository = AuthAuditRepository(session)
            
            event_log = await repository.log_event(
                event_type="system_start",
                success=True,
                metadata={"system": "auth_service"}
            )
            await session.commit()
            
            assert event_log is not None
            assert event_log.event_type == "system_start"
            assert event_log.user_id is None
            assert event_log.success is True