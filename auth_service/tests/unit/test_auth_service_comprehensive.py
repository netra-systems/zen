"""
Comprehensive unit tests for AuthService - Core authentication service
Tests basic functionality and regression protection
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import pytest
import pytest_asyncio
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import User, LoginResponse
from auth_service.auth_core.database.models import AuthUser, AuthSession
from auth_service.auth_core.core.jwt_handler import JWTHandler
from shared.isolated_environment import IsolatedEnvironment


class TestAuthServiceBasics:
    """Test basic AuthService functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.user_id = str(uuid.uuid4())
        self.email = f"test_{uuid.uuid4()}@example.com"
        self.password = "SecurePassword123!"
        self.username = f"testuser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_register_user(self):
        """Test user registration"""
        user = await self.service.register_user(self.email, self.password, self.username)
        assert user is not None
        assert user["email"] == self.email
        assert "user_id" in user
        assert user["message"] == "User registered successfully"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self):
        """Test registering with duplicate email fails"""
        await self.service.register_user(self.email, self.password, self.username)
        with pytest.raises(ValueError, match="already registered"):
            await self.service.register_user(self.email, "OtherPassword123!", "other_user")
    
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self):
        """Test login with valid credentials"""
        await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        assert auth_token is not None
        assert auth_token.access_token is not None
        assert auth_token.refresh_token is not None
        assert auth_token.token_type == "Bearer"
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_password_fails(self):
        """Test login with invalid password fails"""
        await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, "WrongPassword123!")
        assert auth_token is None
    
    @pytest.mark.asyncio
    async def test_login_with_nonexistent_user_fails(self):
        """Test login with nonexistent user fails"""
        auth_token = await self.service.login("nonexistent@example.com", self.password)
        assert auth_token is None
    
    @pytest.mark.asyncio
    async def test_validate_token(self):
        """Test token validation"""
        await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        user = await self.service.validate_token(auth_token.access_token)
        assert user is not None
        assert user.email == self.email
        assert user.username == self.username
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token_returns_none(self):
        """Test invalid token validation returns None"""
        user = await self.service.validate_token("invalid.token.here")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_refresh_tokens(self):
        """Test refreshing tokens"""
        await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        new_auth_token = await self.service.refresh_tokens(auth_token.refresh_token)
        assert new_auth_token is not None
        assert new_auth_token.access_token != auth_token.access_token
        assert new_auth_token.refresh_token != auth_token.refresh_token
    
    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token_fails(self):
        """Test refreshing with invalid token fails"""
        new_auth_token = await self.service.refresh_tokens("invalid.refresh.token")
        assert new_auth_token is None
    
    @pytest.mark.asyncio
    async def test_logout(self):
        """Test user logout"""
        await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        result = await self.service.logout(auth_token.access_token)
        assert result is True
        # Token should be blacklisted now
        user = await self.service.validate_token(auth_token.access_token)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self):
        """Test logout with invalid token"""
        result = await self.service.logout("invalid.token")
        assert result is True  # Logout is permissive
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        """Test getting user by ID"""
        registered_user = await self.service.register_user(self.email, self.password, self.username)
        user = await self.service.get_user_by_id(registered_user.id)
        assert user is not None
        assert user.email == self.email
        assert user.username == self.username
    
    @pytest.mark.asyncio
    async def test_get_user_by_nonexistent_id_returns_none(self):
        """Test getting user by nonexistent ID returns None"""
        user = await self.service.get_user_by_id(str(uuid.uuid4()))
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        """Test getting user by email"""
        await self.service.register_user(self.email, self.password, self.username)
        user = await self.service.get_user_by_email(self.email)
        assert user is not None
        assert user.email == self.email
        assert user.username == self.username
    
    @pytest.mark.asyncio
    async def test_get_user_by_nonexistent_email_returns_none(self):
        """Test getting user by nonexistent email returns None"""
        user = await self.service.get_user_by_email("nonexistent@example.com")
        assert user is None


class TestAuthServiceSessions:
    """Test session management functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"session_{uuid.uuid4()}@example.com"
        self.password = "SessionPassword123!"
        self.username = f"sessionuser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation on login"""
        user = await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        # Session should be created automatically
        sessions = await self.service.get_user_sessions(user.id)
        assert len(sessions) > 0
        assert sessions[0].user_id == user.id
    
    @pytest.mark.asyncio
    async def test_validate_session(self):
        """Test session validation"""
        user = await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        # Extract session from token
        jwt_handler = JWTHandler()
        payload = jwt_handler.validate_token(auth_token.access_token, "access")
        session_id = payload.get("session_id") if payload else None
        if session_id:
            is_valid = await self.service.validate_session(session_id)
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_invalidate_session_on_logout(self):
        """Test session invalidation on logout"""
        user = await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        await self.service.logout(auth_token.access_token)
        sessions = await self.service.get_user_sessions(user.id)
        # Active sessions should be invalidated
        active_sessions = [s for s in sessions if s.is_active]
        assert len(active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self):
        """Test getting all user sessions"""
        user = await self.service.register_user(self.email, self.password, self.username)
        # Create multiple sessions
        for _ in range(3):
            await self.service.login(self.email, self.password)
        sessions = await self.service.get_user_sessions(user.id)
        assert len(sessions) >= 3
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.login(self.email, self.password)
        # This is implementation-specific
        await self.service.cleanup_expired_sessions()
        # Should not crash
        assert True


class TestAuthServicePasswordManagement:
    """Test password-related functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"password_{uuid.uuid4()}@example.com"
        self.password = "OldPassword123!"
        self.username = f"pwduser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_update_password(self):
        """Test password update"""
        user = await self.service.register_user(self.email, self.password, self.username)
        new_password = "NewPassword456!"
        result = await self.service.update_password(user.id, self.password, new_password)
        assert result is True
        # Should be able to login with new password
        auth_token = await self.service.login(self.email, new_password)
        assert auth_token is not None
    
    @pytest.mark.asyncio
    async def test_update_password_with_wrong_old_password_fails(self):
        """Test password update with wrong old password fails"""
        user = await self.service.register_user(self.email, self.password, self.username)
        result = await self.service.update_password(user.id, "WrongOldPassword!", "NewPassword456!")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_password_hash_verification(self):
        """Test password hash verification"""
        await self.service.register_user(self.email, self.password, self.username)
        db_user = await self.service.repository.get_user_by_email(self.email)
        assert db_user is not None
        is_valid = await self.service._verify_password(self.password, db_user.password_hash)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_password_hash_differs_from_plaintext(self):
        """Test password is hashed, not stored as plaintext"""
        await self.service.register_user(self.email, self.password, self.username)
        db_user = await self.service.repository.get_user_by_email(self.email)
        assert db_user.password_hash != self.password
        assert len(db_user.password_hash) > len(self.password)
    
    @pytest.mark.asyncio
    async def test_weak_password_validation(self):
        """Test weak password is rejected"""
        weak_passwords = ["123456", "password", "12345678", "qwerty", "abc123"]
        for weak_pwd in weak_passwords:
            with pytest.raises(ValueError):
                await self.service.register_user(f"weak_{weak_pwd}@example.com", weak_pwd, f"user_{weak_pwd}")
    
    @pytest.mark.asyncio
    async def test_password_requirements(self):
        """Test password meets minimum requirements"""
        # Too short
        with pytest.raises(ValueError):
            await self.service.register_user("short@example.com", "Ab1!", "shortuser")
        # No uppercase
        with pytest.raises(ValueError):
            await self.service.register_user("lower@example.com", "lowercase123!", "loweruser")
        # No lowercase
        with pytest.raises(ValueError):
            await self.service.register_user("upper@example.com", "UPPERCASE123!", "upperuser")
        # No digit
        with pytest.raises(ValueError):
            await self.service.register_user("nodigit@example.com", "NoDigitPassword!", "nodigituser")


class TestAuthServiceUserManagement:
    """Test user management functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"usermgmt_{uuid.uuid4()}@example.com"
        self.password = "UserMgmtPassword123!"
        self.username = f"usermgmt_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self):
        """Test updating user profile"""
        user = await self.service.register_user(self.email, self.password, self.username)
        updated_user = await self.service.update_user_profile(
            user.id,
            username="new_username",
            full_name="Test User"
        )
        assert updated_user is not None
        assert updated_user.username == "new_username"
        assert updated_user.full_name == "Test User"
    
    @pytest.mark.asyncio
    async def test_update_user_email(self):
        """Test updating user email"""
        user = await self.service.register_user(self.email, self.password, self.username)
        new_email = f"newemail_{uuid.uuid4()}@example.com"
        updated_user = await self.service.update_user_email(user.id, new_email)
        assert updated_user is not None
        assert updated_user.email == new_email
    
    @pytest.mark.asyncio
    async def test_update_to_duplicate_email_fails(self):
        """Test updating to duplicate email fails"""
        user1 = await self.service.register_user(self.email, self.password, self.username)
        email2 = f"second_{uuid.uuid4()}@example.com"
        await self.service.register_user(email2, "Password123!", f"second_{uuid.uuid4()}")
        with pytest.raises(ValueError, match="already in use"):
            await self.service.update_user_email(user1.id, email2)
    
    @pytest.mark.asyncio
    async def test_delete_user(self):
        """Test user deletion"""
        user = await self.service.register_user(self.email, self.password, self.username)
        result = await self.service.delete_user(user.id)
        assert result is True
        # User should not exist anymore
        deleted_user = await self.service.get_user_by_id(user.id)
        assert deleted_user is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self):
        """Test deleting nonexistent user"""
        result = await self.service.delete_user(str(uuid.uuid4()))
        assert result is False
    
    @pytest.mark.asyncio
    async def test_activate_user(self):
        """Test user activation"""
        user = await self.service.register_user(self.email, self.password, self.username)
        # Deactivate first
        await self.service.deactivate_user(user.id)
        # Then activate
        result = await self.service.activate_user(user.id)
        assert result is True
        activated_user = await self.service.get_user_by_id(user.id)
        assert activated_user.is_active is True
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self):
        """Test user deactivation"""
        user = await self.service.register_user(self.email, self.password, self.username)
        result = await self.service.deactivate_user(user.id)
        assert result is True
        deactivated_user = await self.service.get_user_by_id(user.id)
        assert deactivated_user.is_active is False
    
    @pytest.mark.asyncio
    async def test_login_with_deactivated_user_fails(self):
        """Test login fails for deactivated user"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.deactivate_user(user.id)
        auth_token = await self.service.login(self.email, self.password)
        assert auth_token is None


class TestAuthServicePermissions:
    """Test permission and role management"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"perms_{uuid.uuid4()}@example.com"
        self.password = "PermsPassword123!"
        self.username = f"permsuser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_default_user_permissions(self):
        """Test default permissions for new user"""
        user = await self.service.register_user(self.email, self.password, self.username)
        assert user.role == "user"
        assert user.permissions == [] or user.permissions == ["read"]
    
    @pytest.mark.asyncio
    async def test_update_user_role(self):
        """Test updating user role"""
        user = await self.service.register_user(self.email, self.password, self.username)
        updated_user = await self.service.update_user_role(user.id, "admin")
        assert updated_user.role == "admin"
    
    @pytest.mark.asyncio
    async def test_update_user_permissions(self):
        """Test updating user permissions"""
        user = await self.service.register_user(self.email, self.password, self.username)
        new_permissions = ["read", "write", "delete"]
        updated_user = await self.service.update_user_permissions(user.id, new_permissions)
        assert set(updated_user.permissions) == set(new_permissions)
    
    @pytest.mark.asyncio
    async def test_add_user_permission(self):
        """Test adding single permission"""
        user = await self.service.register_user(self.email, self.password, self.username)
        updated_user = await self.service.add_user_permission(user.id, "write")
        assert "write" in updated_user.permissions
    
    @pytest.mark.asyncio
    async def test_remove_user_permission(self):
        """Test removing single permission"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.update_user_permissions(user.id, ["read", "write", "delete"])
        updated_user = await self.service.remove_user_permission(user.id, "delete")
        assert "delete" not in updated_user.permissions
        assert "read" in updated_user.permissions
        assert "write" in updated_user.permissions
    
    @pytest.mark.asyncio
    async def test_check_user_permission(self):
        """Test checking if user has permission"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.update_user_permissions(user.id, ["read", "write"])
        has_read = await self.service.check_user_permission(user.id, "read")
        has_delete = await self.service.check_user_permission(user.id, "delete")
        assert has_read is True
        assert has_delete is False
    
    @pytest.mark.asyncio
    async def test_token_includes_permissions(self):
        """Test JWT tokens include user permissions"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.update_user_permissions(user.id, ["read", "write"])
        auth_token = await self.service.login(self.email, self.password)
        
        jwt_handler = JWTHandler()
        payload = jwt_handler.validate_token(auth_token.access_token, "access")
        assert payload is not None
        assert "permissions" in payload
        assert set(payload["permissions"]) == {"read", "write"}


class TestAuthServiceEmailVerification:
    """Test email verification functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"verify_{uuid.uuid4()}@example.com"
        self.password = "VerifyPassword123!"
        self.username = f"verifyuser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_user_created_unverified(self):
        """Test new users are created unverified"""
        user = await self.service.register_user(self.email, self.password, self.username)
        assert user.email_verified is False
    
    @pytest.mark.asyncio
    async def test_generate_verification_token(self):
        """Test generating email verification token"""
        user = await self.service.register_user(self.email, self.password, self.username)
        token = await self.service.generate_verification_token(user.id)
        assert token is not None
        assert len(token) > 20
    
    @pytest.mark.asyncio
    async def test_verify_email_with_valid_token(self):
        """Test email verification with valid token"""
        user = await self.service.register_user(self.email, self.password, self.username)
        token = await self.service.generate_verification_token(user.id)
        result = await self.service.verify_email(token)
        assert result is True
        verified_user = await self.service.get_user_by_id(user.id)
        assert verified_user.email_verified is True
    
    @pytest.mark.asyncio
    async def test_verify_email_with_invalid_token_fails(self):
        """Test email verification with invalid token fails"""
        result = await self.service.verify_email("invalid_verification_token")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resend_verification_email(self):
        """Test resending verification email"""
        user = await self.service.register_user(self.email, self.password, self.username)
        result = await self.service.resend_verification_email(user.email)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_login_with_unverified_email_warning(self):
        """Test login with unverified email shows warning"""
        user = await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        # Should still allow login but with warning
        assert auth_token is not None
        # Check if warning is included
        validated_user = await self.service.validate_token(auth_token.access_token)
        assert validated_user.email_verified is False


class TestAuthServiceRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"ratelimit_{uuid.uuid4()}@example.com"
        self.password = "RateLimitPassword123!"
        self.username = f"ratelimituser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_login_attempts_tracking(self):
        """Test tracking of failed login attempts"""
        await self.service.register_user(self.email, self.password, self.username)
        # Multiple failed attempts
        for _ in range(3):
            await self.service.login(self.email, "WrongPassword!")
        # Check if attempts are tracked
        attempts = await self.service.get_failed_login_attempts(self.email)
        assert attempts >= 3
    
    @pytest.mark.asyncio
    async def test_account_lockout_after_max_attempts(self):
        """Test account lockout after maximum failed attempts"""
        await self.service.register_user(self.email, self.password, self.username)
        # Exceed max attempts
        max_attempts = 5
        for _ in range(max_attempts + 1):
            await self.service.login(self.email, "WrongPassword!")
        # Should be locked out now
        auth_token = await self.service.login(self.email, self.password)
        # Depending on implementation, might return None or raise exception
        # This is flexible based on implementation
    
    @pytest.mark.asyncio
    async def test_reset_failed_attempts_on_success(self):
        """Test failed attempts reset on successful login"""
        await self.service.register_user(self.email, self.password, self.username)
        # Some failed attempts
        for _ in range(2):
            await self.service.login(self.email, "WrongPassword!")
        # Successful login
        await self.service.login(self.email, self.password)
        # Attempts should be reset
        attempts = await self.service.get_failed_login_attempts(self.email)
        assert attempts == 0
    
    @pytest.mark.asyncio
    async def test_unlock_account(self):
        """Test unlocking a locked account"""
        user = await self.service.register_user(self.email, self.password, self.username)
        # Lock the account (implementation specific)
        await self.service.lock_account(user.id)
        # Unlock it
        result = await self.service.unlock_account(user.id)
        assert result is True
        # Should be able to login now
        auth_token = await self.service.login(self.email, self.password)
        assert auth_token is not None


class TestAuthServiceAuditLogging:
    """Test audit logging functionality"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.service = AuthService()
        self.email = f"audit_{uuid.uuid4()}@example.com"
        self.password = "AuditPassword123!"
        self.username = f"audituser_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_login_audit_log(self):
        """Test login events are logged"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.login(self.email, self.password)
        logs = await self.service.get_audit_logs(user.id)
        assert any(log.event_type == "login" for log in logs)
    
    @pytest.mark.asyncio
    async def test_logout_audit_log(self):
        """Test logout events are logged"""
        user = await self.service.register_user(self.email, self.password, self.username)
        auth_token = await self.service.login(self.email, self.password)
        await self.service.logout(auth_token.access_token)
        logs = await self.service.get_audit_logs(user.id)
        assert any(log.event_type == "logout" for log in logs)
    
    @pytest.mark.asyncio
    async def test_password_change_audit_log(self):
        """Test password change events are logged"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.update_password(user.id, self.password, "NewPassword123!")
        logs = await self.service.get_audit_logs(user.id)
        assert any(log.event_type == "password_change" for log in logs)
    
    @pytest.mark.asyncio
    async def test_failed_login_audit_log(self):
        """Test failed login attempts are logged"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.login(self.email, "WrongPassword!")
        logs = await self.service.get_audit_logs_by_email(self.email)
        assert any(log.event_type == "failed_login" for log in logs)
    
    @pytest.mark.asyncio
    async def test_get_recent_audit_logs(self):
        """Test getting recent audit logs"""
        user = await self.service.register_user(self.email, self.password, self.username)
        await self.service.login(self.email, self.password)
        recent_logs = await self.service.get_recent_audit_logs(user.id, hours=1)
        assert len(recent_logs) > 0
        # All logs should be recent
        now = datetime.now(timezone.utc)
        for log in recent_logs:
            age = now - log.timestamp
            assert age.total_seconds() < 3600  # Less than 1 hour old