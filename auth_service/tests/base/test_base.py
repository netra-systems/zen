"""
Base Test Classes
Common functionality for auth service tests with proper setup and teardown.
Follows 450-line limit with focused test infrastructure.
"""

import asyncio
import pytest
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.test_settings import TestSettings
from ..config.test_env import TestEnvironment
from ..factories import (
    UserFactory, AuthUserFactory,
    SessionFactory, AuthSessionFactory,
    TokenFactory, PermissionFactory
)


class AsyncTestBase:
    """Base class for async tests with common setup"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.test_settings = TestSettings.for_unit_tests()
        self.test_env = TestEnvironment()
        self.mock_objects = {}
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up mock objects
        self.mock_objects.clear()
        
        # Clean up test environment
        if hasattr(self, 'test_env'):
            self.test_env.teardown()
    
    def create_mock(self, name: str, spec=None, **kwargs) -> MagicMock:
        """Create and store mock object"""
        mock_obj = AsyncMock(spec=spec, **kwargs) if asyncio.iscoroutinefunction(spec) else MagicMock(spec=spec, **kwargs)
        self.mock_objects[name] = mock_obj
        return mock_obj
    
    def get_mock(self, name: str) -> Optional[MagicMock]:
        """Get stored mock object"""
        return self.mock_objects.get(name)
    
    async def async_setup(self):
        """Async setup - override in subclasses"""
        pass
    
    async def async_teardown(self):
        """Async teardown - override in subclasses"""
        pass


class AuthTestBase(AsyncTestBase):
    """Base class for auth service tests with auth-specific functionality"""
    
    def setup_method(self):
        """Setup auth test environment"""
        super().setup_method()
        
        # Initialize factories
        self.user_factory = UserFactory()
        self.session_factory = SessionFactory()
        self.token_factory = TokenFactory()
        self.permission_factory = PermissionFactory()
        
        # Test data containers
        self.test_users = {}
        self.test_sessions = {}
        self.test_tokens = {}
    
    def create_test_user(self, **kwargs) -> Dict[str, Any]:
        """Create test user data"""
        user_data = self.user_factory.create_user_data(**kwargs)
        self.test_users[user_data["id"]] = user_data
        return user_data
    
    def create_test_local_user(self, password: str = "TestPassword123!", **kwargs) -> Dict[str, Any]:
        """Create test local user with password"""
        user_data = self.user_factory.create_local_user_data(password=password, **kwargs)
        self.test_users[user_data["id"]] = user_data
        return user_data
    
    def create_test_oauth_user(self, provider: str = "google", **kwargs) -> Dict[str, Any]:
        """Create test OAuth user"""
        user_data = self.user_factory.create_oauth_user_data(provider=provider, **kwargs)
        self.test_users[user_data["id"]] = user_data
        return user_data
    
    def create_test_session(self, user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create test session data"""
        session_data = self.session_factory.create_session_data(user_id=user_id, **kwargs)
        self.test_sessions[session_data["id"]] = session_data
        return session_data
    
    def create_test_access_token(self, user_id: str = None, **kwargs) -> str:
        """Create test access token"""
        token = self.token_factory.create_access_token(user_id=user_id, **kwargs)
        self.test_tokens[user_id or "default"] = {"access_token": token}
        return token
    
    def create_test_refresh_token(self, user_id: str = None, **kwargs) -> str:
        """Create test refresh token"""
        token = self.token_factory.create_refresh_token(user_id=user_id, **kwargs)
        if user_id not in self.test_tokens:
            self.test_tokens[user_id or "default"] = {}
        self.test_tokens[user_id or "default"]["refresh_token"] = token
        return token
    
    def create_test_user_with_permissions(
        self,
        permissions: list = None,
        role: str = "user",
        **kwargs
    ) -> Dict[str, Any]:
        """Create test user with specific permissions"""
        user_data = self.create_test_user(**kwargs)
        
        if permissions:
            user_permissions = self.permission_factory.create_custom_permissions(
                user_data["id"],
                permissions
            )
        else:
            from ..factories.permission_factory import RoleFactory
            user_permissions = RoleFactory.create_role_permissions(
                user_data["id"],
                role
            )
        
        user_data["permissions"] = user_permissions
        return user_data
    
    def assert_user_data_valid(self, user_data: Dict[str, Any]):
        """Assert user data is valid"""
        assert "id" in user_data
        assert "email" in user_data
        assert "auth_provider" in user_data
        assert user_data["email"].count("@") == 1  # Valid email format
    
    def assert_session_data_valid(self, session_data: Dict[str, Any]):
        """Assert session data is valid"""
        assert "id" in session_data
        assert "user_id" in session_data
        assert "created_at" in session_data
        assert "expires_at" in session_data
        assert session_data["expires_at"] > session_data["created_at"]
    
    def assert_token_valid(self, token: str):
        """Assert JWT token is valid"""
        assert token is not None
        assert len(token) > 0
        assert token.count(".") == 2  # Valid JWT format
        
        # Decode and verify structure
        claims = self.token_factory.decode_token(token, verify=False)
        assert "sub" in claims  # Subject (user ID)
        assert "exp" in claims  # Expiration
        assert "iat" in claims  # Issued at


class DatabaseTestBase(AuthTestBase):
    """Base class for database-dependent tests"""
    
    def __init__(self):
        super().__init__()
        self.db_session: Optional[AsyncSession] = None
        self.db_users = {}
        self.db_sessions = {}
    
    async def setup_database(self, db_session: AsyncSession):
        """Setup database session for test"""
        self.db_session = db_session
    
    async def create_db_user(self, **kwargs):
        """Create user in database"""
        if not self.db_session:
            raise RuntimeError("Database session not setup")
        
        user = AuthUserFactory.create_user(self.db_session, **kwargs)
        await self.db_session.commit()
        
        self.db_users[user.id] = user
        return user
    
    async def create_db_session(self, user_id: str = None, **kwargs):
        """Create session in database"""
        if not self.db_session:
            raise RuntimeError("Database session not setup")
        
        session = AuthSessionFactory.create_session(
            self.db_session,
            user_id=user_id,
            **kwargs
        )
        await self.db_session.commit()
        
        self.db_sessions[session.id] = session
        return session
    
    async def cleanup_database(self):
        """Cleanup database objects"""
        if self.db_session:
            await self.db_session.rollback()
        
        self.db_users.clear()
        self.db_sessions.clear()