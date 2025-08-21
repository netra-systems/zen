"""
Test Helper Functions
Utility functions for auth service testing operations.
Provides common functionality for test setup, data creation, and assertions.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog
from auth_service.tests.factories import (
    UserFactory, AuthUserFactory,
    SessionFactory, AuthSessionFactory,
    TokenFactory, AuditLogFactory
)


class AuthTestUtils:
    """Authentication testing utilities"""
    
    def __init__(self, db_session: AsyncSession = None, redis_client=None):
        self.db_session = db_session
        self.redis_client = redis_client or AsyncMock()
        self.created_users = []
        self.created_sessions = []
    
    async def create_test_user(
        self,
        email: str = None,
        password: str = "TestPassword123!",
        **kwargs
    ) -> AuthUser:
        """Create test user in database"""
        if not self.db_session:
            raise RuntimeError("Database session not configured")
        
        user = AuthUserFactory.create_local_user(
            self.db_session,
            email=email,
            password=password,
            **kwargs
        )
        await self.db_session.commit()
        
        self.created_users.append(user)
        return user
    
    async def create_oauth_test_user(
        self,
        provider: str = "google",
        email: str = None,
        **kwargs
    ) -> AuthUser:
        """Create OAuth test user in database"""
        if not self.db_session:
            raise RuntimeError("Database session not configured")
        
        user = AuthUserFactory.create_oauth_user(
            self.db_session,
            provider=provider,
            email=email,
            **kwargs
        )
        await self.db_session.commit()
        
        self.created_users.append(user)
        return user
    
    async def create_test_session(
        self,
        user_id: str,
        **kwargs
    ) -> AuthSession:
        """Create test session in database"""
        if not self.db_session:
            raise RuntimeError("Database session not configured")
        
        session = AuthSessionFactory.create_session(
            self.db_session,
            user_id=user_id,
            **kwargs
        )
        await self.db_session.commit()
        
        self.created_sessions.append(session)
        return session
    
    async def authenticate_user(
        self,
        email: str,
        password: str = "TestPassword123!"
    ) -> Dict[str, str]:
        """Simulate user authentication and return tokens"""
        # Find user by email
        if self.db_session:
            result = await self.db_session.execute(
                select(AuthUser).where(AuthUser.email == email)
            )
            user = result.scalars().first()
            
            if not user:
                raise ValueError(f"User with email {email} not found")
        else:
            # Mock user for testing without database
            user = type('MockUser', (), {
                'id': str(uuid.uuid4()),
                'email': email,
                'is_active': True
            })()
        
        # Create tokens
        access_token = TokenFactory.create_access_token(
            user_id=user.id,
            email=user.email
        )
        
        refresh_token = TokenFactory.create_refresh_token(
            user_id=user.id,
            email=user.email
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "user_id": user.id
        }
    
    async def revoke_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user"""
        if not self.db_session:
            return 0
        
        from sqlalchemy import update
        
        result = await self.db_session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id)
            .values(
                is_active=False,
                revoked_at=datetime.now(timezone.utc)
            )
        )
        
        await self.db_session.commit()
        return result.rowcount
    
    async def cleanup_test_data(self):
        """Cleanup created test data"""
        if not self.db_session:
            return
        
        # Delete created sessions
        for session in self.created_sessions:
            await self.db_session.delete(session)
        
        # Delete created users
        for user in self.created_users:
            await self.db_session.delete(user)
        
        await self.db_session.commit()
        
        self.created_users.clear()
        self.created_sessions.clear()


class TokenTestUtils:
    """JWT token testing utilities"""
    
    @staticmethod
    def create_valid_access_token(
        user_id: str = None,
        email: str = None,
        permissions: List[str] = None,
        **kwargs
    ) -> str:
        """Create valid access token for testing"""
        return TokenFactory.create_access_token(
            user_id=user_id or str(uuid.uuid4()),
            email=email or "test@example.com",
            permissions=permissions or [],
            **kwargs
        )
    
    @staticmethod
    def create_expired_token(user_id: str = None, **kwargs) -> str:
        """Create expired token for testing"""
        return TokenFactory.create_expired_token(
            user_id=user_id or str(uuid.uuid4()),
            **kwargs
        )
    
    @staticmethod
    def create_malformed_token() -> str:
        """Create malformed token for testing"""
        return TokenFactory.create_malformed_token()
    
    @staticmethod
    def extract_claims(token: str, verify: bool = False) -> Dict[str, Any]:
        """Extract claims from JWT token"""
        return TokenFactory.decode_token(token, verify=verify)
    
    @staticmethod
    def assert_token_structure(token: str):
        """Assert token has correct JWT structure"""
        parts = token.split(".")
        assert len(parts) == 3, f"Invalid JWT structure: {len(parts)} parts"
        
        # Verify each part is base64 encoded
        import base64
        for part in parts:
            try:
                # Add padding if needed
                padded = part + '=' * (4 - len(part) % 4)
                base64.urlsafe_b64decode(padded)
            except Exception as e:
                assert False, f"Invalid base64 encoding in JWT part: {e}"
    
    @staticmethod
    def assert_token_claims(
        token: str,
        expected_user_id: str = None,
        expected_email: str = None,
        expected_permissions: List[str] = None
    ):
        """Assert token contains expected claims"""
        claims = TokenTestUtils.extract_claims(token, verify=False)
        
        if expected_user_id:
            assert claims.get("sub") == expected_user_id
        
        if expected_email:
            assert claims.get("email") == expected_email
        
        if expected_permissions is not None:
            token_permissions = claims.get("permissions", [])
            for perm in expected_permissions:
                assert perm in token_permissions, f"Missing permission: {perm}"


class DatabaseTestUtils:
    """Database testing utilities"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_user_by_email(self, email: str) -> Optional[AuthUser]:
        """Get user by email from database"""
        result = await self.db_session.execute(
            select(AuthUser).where(AuthUser.email == email)
        )
        return result.scalars().first()
    
    async def get_user_by_id(self, user_id: str) -> Optional[AuthUser]:
        """Get user by ID from database"""
        return await self.db_session.get(AuthUser, user_id)
    
    async def get_active_sessions(self, user_id: str) -> List[AuthSession]:
        """Get active sessions for user"""
        result = await self.db_session.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .where(AuthSession.is_active == True)
        )
        return result.scalars().all()
    
    async def count_users(self) -> int:
        """Count total users in database"""
        from sqlalchemy import func
        result = await self.db_session.execute(
            select(func.count(AuthUser.id))
        )
        return result.scalar_one()
    
    async def count_sessions(self, user_id: str = None) -> int:
        """Count sessions (optionally for specific user)"""
        from sqlalchemy import func
        
        query = select(func.count(AuthSession.id))
        if user_id:
            query = query.where(AuthSession.user_id == user_id)
        
        result = await self.db_session.execute(query)
        return result.scalar_one()
    
    async def cleanup_user_data(self, user_id: str):
        """Clean up all data for a specific user"""
        # Delete sessions
        from sqlalchemy import delete
        
        await self.db_session.execute(
            delete(AuthSession).where(AuthSession.user_id == user_id)
        )
        
        # Delete audit logs
        await self.db_session.execute(
            delete(AuthAuditLog).where(AuthAuditLog.user_id == user_id)
        )
        
        # Delete user
        await self.db_session.execute(
            delete(AuthUser).where(AuthUser.id == user_id)
        )
        
        await self.db_session.commit()
    
    async def create_audit_log(
        self,
        event_type: str,
        user_id: str = None,
        success: bool = True,
        **kwargs
    ) -> AuthAuditLog:
        """Create audit log entry"""
        audit_data = AuditLogFactory.create_audit_data(
            event_type=event_type,
            user_id=user_id,
            success=success,
            **kwargs
        )
        
        audit_log = AuthAuditLog(**audit_data)
        self.db_session.add(audit_log)
        await self.db_session.commit()
        
        return audit_log