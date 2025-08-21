"""
Test Mixins for Auth Service
Reusable test functionality as mixins for specific concerns.
Each mixin provides focused functionality following single responsibility.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.auth_core.database.models import AuthSession, AuthUser
from auth_service.tests.factories import (
    AuditLogFactory,
    AuthSessionFactory,
    AuthUserFactory,
)


class DatabaseTestMixin:
    """Mixin for database testing functionality"""
    
    async def assert_user_in_database(
        self,
        db_session: AsyncSession,
        user_id: str,
        expected_data: Dict[str, Any] = None
    ):
        """Assert user exists in database with expected data"""
        result = await db_session.get(AuthUser, user_id)
        assert result is not None, f"User {user_id} not found in database"
        
        if expected_data:
            for key, expected_value in expected_data.items():
                actual_value = getattr(result, key, None)
                assert actual_value == expected_value, f"User {user_id}.{key}: expected {expected_value}, got {actual_value}"
    
    async def assert_user_not_in_database(self, db_session: AsyncSession, user_id: str):
        """Assert user does not exist in database"""
        result = await db_session.get(AuthUser, user_id)
        assert result is None, f"User {user_id} unexpectedly found in database"
    
    async def assert_session_in_database(
        self,
        db_session: AsyncSession,
        session_id: str,
        expected_data: Dict[str, Any] = None
    ):
        """Assert session exists in database"""
        result = await db_session.get(AuthSession, session_id)
        assert result is not None, f"Session {session_id} not found in database"
        
        if expected_data:
            for key, expected_value in expected_data.items():
                actual_value = getattr(result, key, None)
                assert actual_value == expected_value, f"Session {session_id}.{key}: expected {expected_value}, got {actual_value}"
    
    async def assert_session_not_in_database(self, db_session: AsyncSession, session_id: str):
        """Assert session does not exist in database"""
        result = await db_session.get(AuthSession, session_id)
        assert result is None, f"Session {session_id} unexpectedly found in database"
    
    async def count_users_in_database(self, db_session: AsyncSession) -> int:
        """Count total users in database"""
        from sqlalchemy import func, select
        result = await db_session.execute(
            select(func.count(AuthUser.id))
        )
        return result.scalar_one()
    
    async def count_sessions_in_database(self, db_session: AsyncSession) -> int:
        """Count total sessions in database"""
        from sqlalchemy import func, select
        result = await db_session.execute(
            select(func.count(AuthSession.id))
        )
        return result.scalar_one()
    
    async def get_user_sessions(
        self,
        db_session: AsyncSession,
        user_id: str
    ) -> List[AuthSession]:
        """Get all sessions for a user"""
        from sqlalchemy import select
        result = await db_session.execute(
            select(AuthSession).where(AuthSession.user_id == user_id)
        )
        return result.scalars().all()


class RedisTestMixin:
    """Mixin for Redis testing functionality"""
    
    def create_mock_redis(self) -> AsyncMock:
        """Create mock Redis client"""
        mock_redis = AsyncMock()
        
        # Setup common Redis methods
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=0)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.hget = AsyncMock(return_value=None)
        mock_redis.hset = AsyncMock(return_value=1)
        mock_redis.hdel = AsyncMock(return_value=1)
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.decr = AsyncMock(return_value=0)
        mock_redis.ttl = AsyncMock(return_value=-1)
        
        return mock_redis
    
    async def assert_redis_key_exists(self, mock_redis: AsyncMock, key: str):
        """Assert Redis key was set"""
        mock_redis.exists.assert_called_with(key)
    
    async def assert_redis_key_deleted(self, mock_redis: AsyncMock, key: str):
        """Assert Redis key was deleted"""
        mock_redis.delete.assert_called_with(key)
    
    def setup_redis_session_storage(self, mock_redis: AsyncMock, session_data: Dict[str, Any]):
        """Setup mock Redis for session storage"""
        session_key = f"session:{session_data['id']}"
        mock_redis.hgetall.return_value = session_data
        mock_redis.exists.return_value = 1
        mock_redis.hget.side_effect = lambda key, field: session_data.get(field)
    
    def setup_redis_rate_limiting(
        self,
        mock_redis: AsyncMock,
        current_count: int = 0,
        limit: int = 10
    ):
        """Setup mock Redis for rate limiting"""
        mock_redis.incr.return_value = current_count + 1
        mock_redis.ttl.return_value = 60  # 60 seconds remaining
        
        # Return True if under limit, False if over
        mock_redis.exists.return_value = 1 if current_count < limit else 0


class AuthTestMixin:
    """Mixin for authentication testing functionality"""
    
    def setup_auth_mocks(self) -> Dict[str, MagicMock]:
        """Setup common auth-related mocks"""
        mocks = {
            "password_hasher": MagicMock(),
            "jwt_handler": MagicMock(),
            "oauth_client": AsyncMock(),
            "session_manager": AsyncMock(),
        }
        
        # Setup password hasher
        mocks["password_hasher"].hash.return_value = "hashed_password"
        mocks["password_hasher"].verify.return_value = True
        
        # Setup JWT handler
        mocks["jwt_handler"].create_access_token.return_value = "test_access_token"
        mocks["jwt_handler"].create_refresh_token.return_value = "test_refresh_token"
        mocks["jwt_handler"].decode_token.return_value = {"sub": "user_id", "exp": 9999999999}
        
        return mocks
    
    async def simulate_login_flow(
        self,
        user_data: Dict[str, Any],
        password: str = "TestPassword123!"
    ) -> Dict[str, str]:
        """Simulate complete login flow and return tokens"""
        # This would typically call the actual auth service
        from ..factories import TokenFactory
        
        access_token = TokenFactory.create_access_token(
            user_id=user_data["id"],
            email=user_data["email"]
        )
        
        refresh_token = TokenFactory.create_refresh_token(
            user_id=user_data["id"],
            email=user_data["email"]
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        }
    
    async def simulate_oauth_flow(
        self,
        provider: str = "google",
        user_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Simulate OAuth authentication flow"""
        from ..factories import OAuthTokenFactory, TokenFactory
        
        # Simulate OAuth provider response
        if provider == "google":
            oauth_response = OAuthTokenFactory.create_google_token_response(
                user_id=user_data.get("id") if user_data else None,
                email=user_data.get("email") if user_data else None
            )
        elif provider == "github":
            oauth_response = OAuthTokenFactory.create_github_token_response(
                user_id=user_data.get("id") if user_data else None
            )
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        # Create our service tokens
        if user_data:
            access_token = TokenFactory.create_access_token(
                user_id=user_data["id"],
                email=user_data["email"]
            )
            refresh_token = TokenFactory.create_refresh_token(
                user_id=user_data["id"],
                email=user_data["email"]
            )
        else:
            access_token = TokenFactory.create_access_token()
            refresh_token = TokenFactory.create_refresh_token()
        
        return {
            "oauth_response": oauth_response,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        }
    
    def assert_login_response_valid(self, response: Dict[str, Any]):
        """Assert login response has required fields"""
        required_fields = ["access_token", "refresh_token", "token_type"]
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"
        
        assert response["token_type"] == "Bearer"
        assert len(response["access_token"]) > 0
        assert len(response["refresh_token"]) > 0
    
    def assert_token_claims_valid(
        self,
        token: str,
        expected_user_id: str = None,
        expected_email: str = None
    ):
        """Assert JWT token claims are valid"""
        from ..factories import TokenFactory
        
        claims = TokenFactory.decode_token(token, verify=False)
        
        assert "sub" in claims
        assert "exp" in claims
        assert "iat" in claims
        
        if expected_user_id:
            assert claims["sub"] == expected_user_id
        
        if expected_email:
            assert claims.get("email") == expected_email