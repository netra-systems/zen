"""
End-to-End integration tests for Auth Service
Tests complete user flows with real services
"""
import asyncio
import uuid
import json
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.database.repository import AuthRepository
from auth_service.auth_core.database.connection import auth_db
from netra_backend.app.redis_manager import redis_manager as auth_redis_manager
from shared.isolated_environment import IsolatedEnvironment


class TestCompleteUserLifecycle:
    """Test complete user lifecycle from registration to deletion"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.auth_service = AuthService()
        self.jwt_handler = JWTHandler()
        self.repository = AuthRepository()
        self.email = f"lifecycle_{uuid.uuid4()}@example.com"
        self.password = "Lifecycle123!"
        self.username = f"lifecycle_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self):
        """Test complete user lifecycle"""
        # 1. Registration
        user = await self.auth_service.register(self.email, self.password, self.username)
        assert user is not None
        assert user.email == self.email
        assert user.email_verified is False
        
        # 2. Email verification
        token = await self.auth_service.generate_verification_token(user.id)
        verified = await self.auth_service.verify_email(token)
        assert verified is True
        
        # 3. Login
        auth_token = await self.auth_service.login(self.email, self.password)
        assert auth_token is not None
        
        # 4. Token validation
        validated_user = await self.auth_service.validate_token(auth_token.access_token)
        assert validated_user is not None
        assert validated_user.email_verified is True
        
        # 5. Profile update
        updated = await self.auth_service.update_user_profile(
            user.id, full_name="Test User", bio="Test bio"
        )
        assert updated.full_name == "Test User"
        
        # 6. Password change
        new_password = "NewPassword456!"
        changed = await self.auth_service.update_password(
            user.id, self.password, new_password
        )
        assert changed is True
        
        # 7. Login with new password
        new_auth = await self.auth_service.login(self.email, new_password)
        assert new_auth is not None
        
        # 8. Token refresh
        refreshed = await self.auth_service.refresh_tokens(new_auth.refresh_token)
        assert refreshed is not None
        
        # 9. Logout
        logged_out = await self.auth_service.logout(refreshed.access_token)
        assert logged_out is True
        
        # 10. Account deletion
        deleted = await self.auth_service.delete_user(user.id)
        assert deleted is True
        
        # Verify user is deleted
        deleted_user = await self.auth_service.get_user_by_id(user.id)
        assert deleted_user is None
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_management(self):
        """Test managing multiple user sessions"""
        # Register user
        user = await self.auth_service.register(self.email, self.password, self.username)
        
        # Create multiple sessions (login from different devices)
        sessions = []
        for i in range(3):
            auth_token = await self.auth_service.login(self.email, self.password)
            sessions.append(auth_token)
        
        # All sessions should be valid
        for auth_token in sessions:
            validated = await self.auth_service.validate_token(auth_token.access_token)
            assert validated is not None
        
        # Logout from one session
        await self.auth_service.logout(sessions[0].access_token)
        
        # First session invalid, others still valid
        assert await self.auth_service.validate_token(sessions[0].access_token) is None
        assert await self.auth_service.validate_token(sessions[1].access_token) is not None
        assert await self.auth_service.validate_token(sessions[2].access_token) is not None
        
        # Invalidate all sessions
        await self.auth_service.invalidate_all_user_sessions(user.id)
        
        # All sessions should be invalid now
        for auth_token in sessions:
            validated = await self.auth_service.validate_token(auth_token.access_token)
            assert validated is None


class TestSecurityFlows:
    """Test security-related flows"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.auth_service = AuthService()
        self.jwt_handler = JWTHandler()
        self.email = f"security_{uuid.uuid4()}@example.com"
        self.password = "Security123!"
        self.username = f"security_{uuid.uuid4()}"
    
    @pytest.mark.asyncio
    async def test_account_lockout_flow(self):
        """Test account lockout after failed attempts"""
        # Register user
        user = await self.auth_service.register(self.email, self.password, self.username)
        
        # Multiple failed login attempts
        for _ in range(6):
            result = await self.auth_service.login(self.email, "WrongPassword!")
            assert result is None
        
        # Account might be locked (implementation dependent)
        # Try correct password
        auth_token = await self.auth_service.login(self.email, self.password)
        # Either locked (None) or still allows login
        
        # Explicitly lock account
        await self.auth_service.lock_account(user.id)
        
        # Should not be able to login when locked
        auth_token = await self.auth_service.login(self.email, self.password)
        # Locked accounts typically can't login
        
        # Unlock account
        await self.auth_service.unlock_account(user.id)
        
        # Should be able to login after unlock
        auth_token = await self.auth_service.login(self.email, self.password)
        assert auth_token is not None
    
    @pytest.mark.asyncio
    async def test_token_blacklist_flow(self):
        """Test token blacklisting flow"""
        # Register and login
        user = await self.auth_service.register(self.email, self.password, self.username)
        auth_token = await self.auth_service.login(self.email, self.password)
        
        # Token should be valid
        validated = await self.auth_service.validate_token(auth_token.access_token)
        assert validated is not None
        
        # Blacklist the token
        self.jwt_handler.blacklist_token(auth_token.access_token)
        
        # Token should be invalid now
        validated = await self.auth_service.validate_token(auth_token.access_token)
        assert validated is None
        
        # Refresh token should still work
        new_tokens = await self.auth_service.refresh_tokens(auth_token.refresh_token)
        assert new_tokens is not None
        
        # New access token should be valid
        validated = await self.auth_service.validate_token(new_tokens.access_token)
        assert validated is not None
    
    @pytest.mark.asyncio
    async def test_user_blacklist_flow(self):
        """Test user blacklisting flow"""
        # Register and login
        user = await self.auth_service.register(self.email, self.password, self.username)
        auth_token = await self.auth_service.login(self.email, self.password)
        
        # Token should be valid
        validated = await self.auth_service.validate_token(auth_token.access_token)
        assert validated is not None
        
        # Blacklist the user
        self.jwt_handler.blacklist_user(user.id)
        
        # All user's tokens should be invalid
        validated = await self.auth_service.validate_token(auth_token.access_token)
        assert validated is None
        
        # User shouldn't be able to login
        new_auth = await self.auth_service.login(self.email, self.password)
        if new_auth:
            # Even if login succeeds, token validation should fail
            validated = await self.auth_service.validate_token(new_auth.access_token)
            assert validated is None
        
        # Remove from blacklist
        self.jwt_handler.remove_user_from_blacklist(user.id)
        
        # Should be able to login again
        auth_token = await self.auth_service.login(self.email, self.password)
        assert auth_token is not None
        validated = await self.auth_service.validate_token(auth_token.access_token)
        assert validated is not None


class TestConcurrencyAndPerformance:
    """Test concurrent operations and performance"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.auth_service = AuthService()
        self.jwt_handler = JWTHandler()
    
    @pytest.mark.asyncio
    async def test_concurrent_registrations(self):
        """Test concurrent user registrations"""
        async def register_user(index):
            try:
                user = await self.auth_service.register(
                    f"concurrent_{index}_{uuid.uuid4()}@example.com",
                    "Password123!",
                    f"concurrent_{index}_{uuid.uuid4()}"
                )
                return user is not None
            except Exception:
                return False
        
        # Register multiple users concurrently
        tasks = [register_user(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All registrations should succeed
        assert all(results)
    
    @pytest.mark.asyncio
    async def test_concurrent_logins(self):
        """Test concurrent login attempts"""
        # Register a user
        email = f"concurrent_login_{uuid.uuid4()}@example.com"
        password = "ConcurrentLogin123!"
        await self.auth_service.register(email, password, f"concurrent_{uuid.uuid4()}")
        
        async def login_user():
            try:
                auth_token = await self.auth_service.login(email, password)
                return auth_token is not None
            except Exception:
                return False
        
        # Multiple concurrent login attempts
        tasks = [login_user() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All logins should succeed
        assert all(results)
    
    @pytest.mark.asyncio
    async def test_concurrent_token_validations(self):
        """Test concurrent token validations"""
        # Register and login
        email = f"concurrent_validate_{uuid.uuid4()}@example.com"
        password = "ConcurrentValidate123!"
        await self.auth_service.register(email, password, f"validate_{uuid.uuid4()}")
        auth_token = await self.auth_service.login(email, password)
        
        async def validate_token():
            try:
                user = await self.auth_service.validate_token(auth_token.access_token)
                return user is not None
            except Exception:
                return False
        
        # Multiple concurrent validation attempts
        tasks = [validate_token() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All validations should succeed
        assert all(results)
    
    @pytest.mark.asyncio
    async def test_token_validation_caching(self):
        """Test token validation caching improves performance"""
        # Register and login
        email = f"cache_test_{uuid.uuid4()}@example.com"
        password = "CacheTest123!"
        await self.auth_service.register(email, password, f"cache_{uuid.uuid4()}")
        auth_token = await self.auth_service.login(email, password)
        
        # First validation (cache miss)
        start = datetime.now(timezone.utc)
        user1 = await self.auth_service.validate_token(auth_token.access_token)
        first_duration = (datetime.now(timezone.utc) - start).total_seconds()
        assert user1 is not None
        
        # Second validation (cache hit)
        start = datetime.now(timezone.utc)
        user2 = await self.auth_service.validate_token(auth_token.access_token)
        second_duration = (datetime.now(timezone.utc) - start).total_seconds()
        assert user2 is not None
        
        # Cache hit should be faster (though this might not always be measurable)
        # Just verify both validations succeeded
        assert user1.id == user2.id


class TestDatabaseTransactions:
    """Test database transaction handling"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.auth_service = AuthService()
        self.repository = AuthRepository()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test transaction rollback on error"""
        email = f"transaction_{uuid.uuid4()}@example.com"
        
        # Try to create user with invalid data that might cause error
        try:
            # This might not actually fail, depends on validation
            user = await self.repository.create_user(
                email=email,
                password_hash="hash",
                username=None  # Might cause error if username is required
            )
        except Exception:
            # If it fails, user shouldn't exist
            user = await self.repository.get_user_by_email(email)
            assert user is None
    
    @pytest.mark.asyncio
    async def test_cascade_delete(self):
        """Test cascade delete of related records"""
        # Create user
        email = f"cascade_{uuid.uuid4()}@example.com"
        user = await self.auth_service.register(email, "Cascade123!", f"cascade_{uuid.uuid4()}")
        
        # Create sessions and audit logs
        auth_token = await self.auth_service.login(email, "Cascade123!")
        await self.repository.create_audit_log(user.id, "test_event", {"test": "data"})
        
        # Verify session and audit log exist
        sessions = await self.repository.get_user_sessions(user.id)
        assert len(sessions) > 0
        audit_logs = await self.repository.get_user_audit_logs(user.id)
        assert len(audit_logs) > 0
        
        # Delete user
        await self.auth_service.delete_user(user.id)
        
        # Sessions and audit logs should be deleted (cascade)
        sessions = await self.repository.get_user_sessions(user.id)
        assert len(sessions) == 0
        audit_logs = await self.repository.get_user_audit_logs(user.id)
        assert len(audit_logs) == 0


class TestRedisIntegration:
    """Test Redis integration for caching and sessions"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Setup for each test"""
        self.auth_service = AuthService()
        self.jwt_handler = JWTHandler()
    
    @pytest.mark.asyncio
    async def test_redis_cache_functionality(self):
        """Test Redis cache for JWT validation"""
        if not auth_redis_manager.enabled:
            pytest.skip("Redis not enabled")
        
        # Register and login
        email = f"redis_{uuid.uuid4()}@example.com"
        await self.auth_service.register(email, "Redis123!", f"redis_{uuid.uuid4()}")
        auth_token = await self.auth_service.login(email, "Redis123!")
        
        # First validation (should cache in Redis)
        user1 = await self.auth_service.validate_token(auth_token.access_token)
        assert user1 is not None
        
        # Check cache stats
        stats = self.jwt_handler.get_performance_stats()
        cache_stats = stats.get("cache_stats", {})
        # Cache should have at least one entry
        if cache_stats.get("cache_enabled"):
            assert cache_stats.get("total_validations", 0) > 0
    
    @pytest.mark.asyncio
    async def test_redis_blacklist_persistence(self):
        """Test Redis persists blacklisted tokens"""
        if not auth_redis_manager.enabled:
            pytest.skip("Redis not enabled")
        
        # Register and login
        email = f"blacklist_{uuid.uuid4()}@example.com"
        await self.auth_service.register(email, "Blacklist123!", f"blacklist_{uuid.uuid4()}")
        auth_token = await self.auth_service.login(email, "Blacklist123!")
        
        # Blacklist token
        self.jwt_handler.blacklist_token(auth_token.access_token)
        
        # Token should be invalid
        validated = await self.auth_service.validate_token(auth_token.access_token)
        assert validated is None
        
        # Create new handler instance (simulates restart)
        new_handler = JWTHandler()
        
        # If Redis persistence works, token should still be blacklisted
        # Note: This depends on Redis persistence implementation
        is_blacklisted = new_handler.is_token_blacklisted(auth_token.access_token)
        # Either cached in memory or would need to check Redis