"""
Comprehensive unit tests for Auth Service Database Models

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure auth data integrity and model correctness
- Value Impact: Prevents data corruption and authentication failures
- Strategic Impact: Foundation for reliable multi-user authentication

Tests all database models for data integrity, constraints, relationships, and business logic.
Uses real PostgreSQL database for comprehensive validation.
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from auth_service.auth_core.database.models import (
    Base, AuthUser, AuthSession, AuthAuditLog, PasswordResetToken
)
from auth_service.auth_core.database.connection import auth_db
from shared.isolated_environment import get_env
from test_framework.real_services_test_fixtures import real_services_fixture


class TestAuthUserModel:
    """Comprehensive tests for AuthUser model"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Setup clean database for each test"""
        async with auth_db.get_session() as session:
            # Clean up any existing test data
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'test_%@example.com'"))
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'oauth_%@example.com'"))
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'model_test_%@example.com'"))
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_model_creation(self, real_services_fixture):
        """Test basic AuthUser model creation with all fields"""
        async with auth_db.get_session() as session:
            user = AuthUser(
                email="test_model_user@example.com",
                full_name="Test Model User",
                hashed_password="hashed_password_123",
                auth_provider="local",
                is_active=True,
                is_verified=False,
                failed_login_attempts=0
            )
            
            session.add(user)
            await session.commit()
            
            # Verify all fields are set correctly
            assert user.id is not None
            assert len(user.id) == 36  # UUID4 format
            assert user.email == "test_model_user@example.com"
            assert user.full_name == "Test Model User"
            assert user.hashed_password == "hashed_password_123"
            assert user.auth_provider == "local"
            assert user.is_active is True
            assert user.is_verified is False
            assert user.failed_login_attempts == 0
            assert user.created_at is not None
            assert user.updated_at is not None
            assert user.last_login_at is None
            assert user.locked_until is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_model_defaults(self, real_services_fixture):
        """Test AuthUser model default values"""
        async with auth_db.get_session() as session:
            user = AuthUser(email="test_defaults@example.com")
            
            session.add(user)
            await session.commit()
            
            # Verify defaults
            assert user.auth_provider == "local"
            assert user.is_active is True
            assert user.is_verified is False
            assert user.failed_login_attempts == 0
            assert user.full_name is None
            assert user.hashed_password is None
            assert user.provider_user_id is None
            assert user.provider_data is None
            assert user.last_login_at is None
            assert user.locked_until is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_email_uniqueness(self, real_services_fixture):
        """Test that email field enforces uniqueness constraint"""
        async with auth_db.get_session() as session:
            # Create first user
            user1 = AuthUser(email="duplicate_test@example.com")
            session.add(user1)
            await session.commit()
            
            # Attempt to create second user with same email
            user2 = AuthUser(email="duplicate_test@example.com")
            session.add(user2)
            
            # Should raise IntegrityError due to unique constraint
            with pytest.raises(IntegrityError):
                await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_oauth_fields(self, real_services_fixture):
        """Test OAuth-specific fields in AuthUser model"""
        async with auth_db.get_session() as session:
            provider_data = {
                "sub": "google_12345",
                "name": "OAuth Test User",
                "picture": "https://example.com/pic.jpg",
                "locale": "en"
            }
            
            user = AuthUser(
                email="oauth_test@example.com",
                full_name="OAuth Test User",
                auth_provider="google",
                provider_user_id="google_12345",
                provider_data=provider_data,
                is_verified=True  # OAuth users are pre-verified
            )
            
            session.add(user)
            await session.commit()
            
            # Verify OAuth fields
            assert user.auth_provider == "google"
            assert user.provider_user_id == "google_12345"
            assert user.provider_data == provider_data
            assert user.is_verified is True
            assert user.hashed_password is None  # OAuth users don't have passwords
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_security_fields(self, real_services_fixture):
        """Test security-related fields (failed attempts, locking)"""
        async with auth_db.get_session() as session:
            lock_time = datetime.now(timezone.utc) + timedelta(hours=1)
            
            user = AuthUser(
                email="security_test@example.com",
                failed_login_attempts=5,
                locked_until=lock_time,
                is_active=False
            )
            
            session.add(user)
            await session.commit()
            
            # Verify security fields
            assert user.failed_login_attempts == 5
            assert user.locked_until == lock_time
            assert user.is_active is False
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_timestamps(self, real_services_fixture):
        """Test timestamp fields behavior"""
        async with auth_db.get_session() as session:
            # Create user
            user = AuthUser(email="timestamp_test@example.com")
            session.add(user)
            await session.commit()
            
            original_created = user.created_at
            original_updated = user.updated_at
            
            assert original_created is not None
            assert original_updated is not None
            
            # Update user
            user.full_name = "Updated Name"
            await session.commit()
            
            # Check that updated_at changed but created_at didn't
            assert user.created_at == original_created
            assert user.updated_at > original_updated
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_user_json_provider_data(self, real_services_fixture):
        """Test JSON field storage for provider_data"""
        async with auth_db.get_session() as session:
            complex_data = {
                "sub": "google_12345",
                "name": "Complex User",
                "picture": "https://example.com/pic.jpg",
                "emails": ["primary@example.com", "secondary@example.com"],
                "groups": ["admin", "user"],
                "metadata": {
                    "last_login": "2024-01-01T12:00:00Z",
                    "preferences": {
                        "theme": "dark",
                        "notifications": True
                    }
                },
                "numbers": [1, 2, 3, 42],
                "boolean_flag": True
            }
            
            user = AuthUser(
                email="json_test@example.com",
                provider_data=complex_data
            )
            
            session.add(user)
            await session.commit()
            
            # Retrieve and verify JSON data integrity
            retrieved_user = await session.get(AuthUser, user.id)
            assert retrieved_user.provider_data == complex_data
            assert retrieved_user.provider_data["metadata"]["preferences"]["theme"] == "dark"
            assert retrieved_user.provider_data["numbers"] == [1, 2, 3, 42]
            assert retrieved_user.provider_data["boolean_flag"] is True


class TestAuthSessionModel:
    """Comprehensive tests for AuthSession model"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Setup clean database and test user for each test"""
        async with auth_db.get_session() as session:
            # Clean up any existing test data
            await session.execute(text("DELETE FROM auth_sessions WHERE device_id LIKE 'test_%'"))
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'session_%@example.com'"))
            await session.commit()
            
            # Create test user
            self.test_user = AuthUser(email="session_test_user@example.com")
            session.add(self.test_user)
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_session_model_creation(self, real_services_fixture):
        """Test basic AuthSession model creation"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            session_obj = AuthSession(
                user_id=self.test_user.id,
                refresh_token_hash="hashed_token_123",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
                device_id="test_device_123",
                expires_at=expires_at
            )
            
            session.add(session_obj)
            await session.commit()
            
            # Verify all fields
            assert session_obj.id is not None
            assert len(session_obj.id) == 36  # UUID4 format
            assert session_obj.user_id == self.test_user.id
            assert session_obj.refresh_token_hash == "hashed_token_123"
            assert session_obj.ip_address == "127.0.0.1"
            assert session_obj.user_agent == "TestAgent/1.0"
            assert session_obj.device_id == "test_device_123"
            assert session_obj.expires_at == expires_at
            assert session_obj.is_active is True
            assert session_obj.created_at is not None
            assert session_obj.last_activity is not None
            assert session_obj.revoked_at is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_session_model_defaults(self, real_services_fixture):
        """Test AuthSession model default values"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            session_obj = AuthSession(
                user_id=self.test_user.id,
                expires_at=expires_at
            )
            
            session.add(session_obj)
            await session.commit()
            
            # Verify defaults
            assert session_obj.is_active is True
            assert session_obj.refresh_token_hash is None
            assert session_obj.ip_address is None
            assert session_obj.user_agent is None
            assert session_obj.device_id is None
            assert session_obj.revoked_at is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_session_revocation(self, real_services_fixture):
        """Test session revocation functionality"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            session_obj = AuthSession(
                user_id=self.test_user.id,
                expires_at=expires_at,
                device_id="test_revoke_device"
            )
            
            session.add(session_obj)
            await session.commit()
            
            # Revoke session
            revoke_time = datetime.now(timezone.utc)
            session_obj.is_active = False
            session_obj.revoked_at = revoke_time
            await session.commit()
            
            # Verify revocation
            assert session_obj.is_active is False
            assert session_obj.revoked_at == revoke_time
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_session_multiple_per_user(self, real_services_fixture):
        """Test that users can have multiple active sessions"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            # Create multiple sessions for same user
            sessions = []
            for i in range(3):
                session_obj = AuthSession(
                    user_id=self.test_user.id,
                    expires_at=expires_at,
                    device_id=f"test_device_{i}",
                    ip_address=f"192.168.1.{i+1}"
                )
                sessions.append(session_obj)
                session.add(session_obj)
            
            await session.commit()
            
            # Verify all sessions exist
            for i, session_obj in enumerate(sessions):
                assert session_obj.device_id == f"test_device_{i}"
                assert session_obj.ip_address == f"192.168.1.{i+1}"
                assert session_obj.user_id == self.test_user.id
                assert session_obj.is_active is True


class TestAuthAuditLogModel:
    """Comprehensive tests for AuthAuditLog model"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Setup clean database and test user for each test"""
        async with auth_db.get_session() as session:
            # Clean up any existing test data
            await session.execute(text("DELETE FROM auth_audit_logs WHERE event_type LIKE 'test_%'"))
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'audit_%@example.com'"))
            await session.commit()
            
            # Create test user
            self.test_user = AuthUser(email="audit_test_user@example.com")
            session.add(self.test_user)
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_audit_log_model_creation(self, real_services_fixture):
        """Test basic AuthAuditLog model creation"""
        async with auth_db.get_session() as session:
            metadata = {"action": "test_action", "resource": "user"}
            
            audit_log = AuthAuditLog(
                event_type="test_login",
                user_id=self.test_user.id,
                success=True,
                event_metadata=metadata,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
            
            session.add(audit_log)
            await session.commit()
            
            # Verify all fields
            assert audit_log.id is not None
            assert len(audit_log.id) == 36  # UUID4 format
            assert audit_log.event_type == "test_login"
            assert audit_log.user_id == self.test_user.id
            assert audit_log.success is True
            assert audit_log.event_metadata == metadata
            assert audit_log.ip_address == "127.0.0.1"
            assert audit_log.user_agent == "TestAgent/1.0"
            assert audit_log.error_message is None
            assert audit_log.created_at is not None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_audit_log_failure_case(self, real_services_fixture):
        """Test audit log for failed events"""
        async with auth_db.get_session() as session:
            audit_log = AuthAuditLog(
                event_type="test_login_failed",
                user_id=self.test_user.id,
                success=False,
                error_message="Invalid credentials",
                ip_address="192.168.1.100"
            )
            
            session.add(audit_log)
            await session.commit()
            
            # Verify failure fields
            assert audit_log.success is False
            assert audit_log.error_message == "Invalid credentials"
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_audit_log_without_user(self, real_services_fixture):
        """Test audit log for system events without user"""
        async with auth_db.get_session() as session:
            audit_log = AuthAuditLog(
                event_type="test_system_event",
                success=True,
                event_metadata={"system": "auth_service"}
            )
            
            session.add(audit_log)
            await session.commit()
            
            # Verify system event
            assert audit_log.user_id is None
            assert audit_log.event_type == "test_system_event"
            assert audit_log.success is True
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_auth_audit_log_json_metadata(self, real_services_fixture):
        """Test JSON metadata storage in audit log"""
        async with auth_db.get_session() as session:
            complex_metadata = {
                "action": "password_change",
                "old_password_strength": "strong",
                "new_password_strength": "very_strong",
                "security_checks": {
                    "common_password": False,
                    "breached": False,
                    "similar_to_old": False
                },
                "attempt_count": 1,
                "browser_fingerprint": {
                    "user_agent": "Mozilla/5.0...",
                    "screen_resolution": "1920x1080",
                    "timezone": "UTC-5"
                }
            }
            
            audit_log = AuthAuditLog(
                event_type="test_complex_event",
                user_id=self.test_user.id,
                success=True,
                event_metadata=complex_metadata
            )
            
            session.add(audit_log)
            await session.commit()
            
            # Verify JSON data integrity
            retrieved_log = await session.get(AuthAuditLog, audit_log.id)
            assert retrieved_log.event_metadata == complex_metadata
            assert retrieved_log.event_metadata["security_checks"]["breached"] is False
            assert retrieved_log.event_metadata["attempt_count"] == 1


class TestPasswordResetTokenModel:
    """Comprehensive tests for PasswordResetToken model"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Setup clean database and test user for each test"""
        async with auth_db.get_session() as session:
            # Clean up any existing test data
            await session.execute(text("DELETE FROM password_reset_tokens WHERE email LIKE 'reset_%@example.com'"))
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'reset_%@example.com'"))
            await session.commit()
            
            # Create test user
            self.test_user = AuthUser(email="reset_test_user@example.com")
            session.add(self.test_user)
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_password_reset_token_creation(self, real_services_fixture):
        """Test basic PasswordResetToken model creation"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            
            token = PasswordResetToken(
                user_id=self.test_user.id,
                token_hash="hashed_reset_token_123",
                email=self.test_user.email,
                expires_at=expires_at
            )
            
            session.add(token)
            await session.commit()
            
            # Verify all fields
            assert token.id is not None
            assert len(token.id) == 36  # UUID4 format
            assert token.user_id == self.test_user.id
            assert token.token_hash == "hashed_reset_token_123"
            assert token.email == self.test_user.email
            assert token.expires_at == expires_at
            assert token.is_used is False
            assert token.created_at is not None
            assert token.used_at is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_password_reset_token_defaults(self, real_services_fixture):
        """Test PasswordResetToken model default values"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            
            token = PasswordResetToken(
                user_id=self.test_user.id,
                token_hash="hashed_reset_token_456",
                email=self.test_user.email,
                expires_at=expires_at
            )
            
            session.add(token)
            await session.commit()
            
            # Verify defaults
            assert token.is_used is False
            assert token.used_at is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_password_reset_token_usage(self, real_services_fixture):
        """Test token usage tracking"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            
            token = PasswordResetToken(
                user_id=self.test_user.id,
                token_hash="hashed_reset_token_789",
                email=self.test_user.email,
                expires_at=expires_at
            )
            
            session.add(token)
            await session.commit()
            
            # Mark token as used
            used_time = datetime.now(timezone.utc)
            token.is_used = True
            token.used_at = used_time
            await session.commit()
            
            # Verify usage tracking
            assert token.is_used is True
            assert token.used_at == used_time
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_password_reset_token_uniqueness(self, real_services_fixture):
        """Test that token_hash enforces uniqueness constraint"""
        async with auth_db.get_session() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            
            # Create first token
            token1 = PasswordResetToken(
                user_id=self.test_user.id,
                token_hash="duplicate_token_hash",
                email=self.test_user.email,
                expires_at=expires_at
            )
            session.add(token1)
            await session.commit()
            
            # Attempt to create second token with same hash
            token2 = PasswordResetToken(
                user_id=self.test_user.id,
                token_hash="duplicate_token_hash",
                email=self.test_user.email,
                expires_at=expires_at
            )
            session.add(token2)
            
            # Should raise IntegrityError due to unique constraint
            with pytest.raises(IntegrityError):
                await session.commit()


class TestDatabaseModelIntegration:
    """Integration tests between different models"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Setup clean database for each test"""
        async with auth_db.get_session() as session:
            # Clean up all test data
            await session.execute(text("DELETE FROM auth_audit_logs WHERE event_type LIKE 'integration_%'"))
            await session.execute(text("DELETE FROM auth_sessions WHERE device_id LIKE 'integration_%'"))
            await session.execute(text("DELETE FROM password_reset_tokens WHERE email LIKE 'integration_%@example.com'"))
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'integration_%@example.com'"))
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_user_session_audit_integration(self, real_services_fixture):
        """Test integration between User, Session, and Audit models"""
        async with auth_db.get_session() as session:
            # Create user
            user = AuthUser(email="integration_test@example.com")
            session.add(user)
            await session.commit()
            
            # Create session
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            session_obj = AuthSession(
                user_id=user.id,
                expires_at=expires_at,
                device_id="integration_device",
                ip_address="192.168.1.1"
            )
            session.add(session_obj)
            await session.commit()
            
            # Create audit log
            audit_log = AuthAuditLog(
                event_type="integration_login",
                user_id=user.id,
                success=True,
                event_metadata={"session_id": session_obj.id},
                ip_address="192.168.1.1"
            )
            session.add(audit_log)
            await session.commit()
            
            # Verify all models are linked correctly
            assert session_obj.user_id == user.id
            assert audit_log.user_id == user.id
            assert audit_log.event_metadata["session_id"] == session_obj.id
            assert session_obj.ip_address == audit_log.ip_address
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_user_password_reset_integration(self, real_services_fixture):
        """Test integration between User and PasswordResetToken models"""
        async with auth_db.get_session() as session:
            # Create user
            user = AuthUser(email="integration_reset@example.com")
            session.add(user)
            await session.commit()
            
            # Create password reset token
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            token = PasswordResetToken(
                user_id=user.id,
                token_hash="integration_token_hash",
                email=user.email,
                expires_at=expires_at
            )
            session.add(token)
            await session.commit()
            
            # Verify integration
            assert token.user_id == user.id
            assert token.email == user.email
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_model_cascade_behavior(self, real_services_fixture):
        """Test model behavior when related data exists (no foreign key constraints)"""
        async with auth_db.get_session() as session:
            # Create user with related data
            user = AuthUser(email="integration_cascade@example.com")
            session.add(user)
            await session.commit()
            
            # Create related records
            session_obj = AuthSession(
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                device_id="integration_cascade_device"
            )
            session.add(session_obj)
            
            audit_log = AuthAuditLog(
                event_type="integration_cascade_event",
                user_id=user.id,
                success=True
            )
            session.add(audit_log)
            
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash="integration_cascade_token",
                email=user.email,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            session.add(reset_token)
            await session.commit()
            
            # Delete user (no cascade constraints, so related records remain orphaned)
            await session.delete(user)
            await session.commit()
            
            # Verify related records still exist but are orphaned
            orphaned_session = await session.get(AuthSession, session_obj.id)
            orphaned_audit = await session.get(AuthAuditLog, audit_log.id)
            orphaned_token = await session.get(PasswordResetToken, reset_token.id)
            
            assert orphaned_session is not None
            assert orphaned_audit is not None
            assert orphaned_token is not None
            
            # Clean up orphaned records
            await session.delete(orphaned_session)
            await session.delete(orphaned_audit)
            await session.delete(orphaned_token)
            await session.commit()


class TestDatabaseModelConstraintsAndEdgeCases:
    """Test database constraints and edge cases"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, real_services_fixture):
        """Setup clean database for each test"""
        async with auth_db.get_session() as session:
            await session.execute(text("DELETE FROM auth_users WHERE email LIKE 'edge_%@example.com'"))
            await session.commit()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_email_case_sensitivity(self, real_services_fixture):
        """Test email case sensitivity in database"""
        async with auth_db.get_session() as session:
            # Create user with lowercase email
            user1 = AuthUser(email="edge_case@example.com")
            session.add(user1)
            await session.commit()
            
            # Try to create user with uppercase email (should be treated as different)
            user2 = AuthUser(email="EDGE_CASE@EXAMPLE.COM")
            session.add(user2)
            await session.commit()
            
            # Verify both users exist (database is case-sensitive)
            lowercase_user = await session.execute(
                select(AuthUser).where(AuthUser.email == "edge_case@example.com")
            )
            uppercase_user = await session.execute(
                select(AuthUser).where(AuthUser.email == "EDGE_CASE@EXAMPLE.COM")
            )
            
            assert lowercase_user.scalar_one_or_none() is not None
            assert uppercase_user.scalar_one_or_none() is not None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_long_text_fields(self, real_services_fixture):
        """Test handling of long text in string fields"""
        async with auth_db.get_session() as session:
            # Create user with very long name and user agent
            long_name = "A" * 1000  # Very long name
            long_user_agent = "Mozilla/5.0 " + "X" * 2000  # Very long user agent
            
            user = AuthUser(
                email="edge_long_fields@example.com",
                full_name=long_name
            )
            session.add(user)
            await session.commit()
            
            # Create session with long user agent
            session_obj = AuthSession(
                user_id=user.id,
                user_agent=long_user_agent,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30)
            )
            session.add(session_obj)
            await session.commit()
            
            # Verify data is stored correctly (database handles long strings)
            assert user.full_name == long_name
            assert session_obj.user_agent == long_user_agent
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_null_handling(self, real_services_fixture):
        """Test handling of NULL values in optional fields"""
        async with auth_db.get_session() as session:
            # Create user with minimal required fields
            user = AuthUser(email="edge_null_test@example.com")
            session.add(user)
            await session.commit()
            
            # Verify NULL fields are handled correctly
            assert user.full_name is None
            assert user.hashed_password is None
            assert user.provider_user_id is None
            assert user.provider_data is None
            assert user.last_login_at is None
            assert user.locked_until is None
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_timezone_handling(self, real_services_fixture):
        """Test timezone handling in datetime fields"""
        async with auth_db.get_session() as session:
            # Create user with specific timezone
            specific_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            
            user = AuthUser(
                email="edge_timezone@example.com",
                last_login_at=specific_time
            )
            session.add(user)
            await session.commit()
            
            # Retrieve and verify timezone is preserved
            retrieved_user = await session.get(AuthUser, user.id)
            assert retrieved_user.last_login_at == specific_time
            assert retrieved_user.last_login_at.tzinfo == timezone.utc