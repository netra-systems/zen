"""Agent Startup User Manager - Supporting Module

User management utilities for agent startup E2E tests.
Handles test user creation, authentication, and cleanup.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Enable comprehensive user flow testing in agent startup scenarios
- Value Impact: Ensures reliable user authentication and session management
- Revenue Impact: Protects user conversion by validating authentication flows

Architecture:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Focused on user management operations
- Integration with JWT helpers for token management
"""

import asyncio
import uuid
import logging
from typing import List, Optional
from dataclasses import dataclass, field

from .jwt_token_helpers import JWTTestHelper

logger = logging.getLogger(__name__)


@dataclass
class TestUser:
    """Test user data container."""
    user_id: str = field(default_factory=lambda: f"test_user_{uuid.uuid4().hex[:8]}")
    email: str = field(default_factory=lambda: f"test_{uuid.uuid4().hex[:8]}@netra.ai")
    access_token: Optional[str] = None
    websocket_url: Optional[str] = None


class UserManager:
    """Manages test user creation and authentication."""
    
    def __init__(self, auth_url: str):
        self.auth_url = auth_url
        self.jwt_helper = JWTTestHelper()
        self.created_users: List[TestUser] = []
        
    async def create_test_user(self, custom_email: Optional[str] = None) -> TestUser:
        """Create a new test user with authentication token."""
        user = TestUser()
        if custom_email:
            user.email = custom_email
        await self._authenticate_user(user)
        self.created_users.append(user)
        return user
        
    async def create_multiple_users(self, count: int) -> List[TestUser]:
        """Create multiple test users concurrently."""
        tasks = [self.create_test_user() for _ in range(count)]
        return await asyncio.gather(*tasks)
        
    async def cleanup_users(self) -> None:
        """Clean up all created test users."""
        cleanup_tasks = [self._cleanup_user(user) for user in self.created_users]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.created_users.clear()
        
    async def get_user_count(self) -> int:
        """Get count of created users."""
        return len(self.created_users)
        
    async def get_authenticated_users(self) -> List[TestUser]:
        """Get list of users with valid tokens."""
        return [user for user in self.created_users if user.access_token]
        
    async def revoke_user_token(self, user: TestUser) -> None:
        """Revoke user's access token."""
        user.access_token = None
        logger.debug(f"Revoked token for user {user.user_id}")
        
    async def refresh_user_token(self, user: TestUser) -> None:
        """Refresh user's access token."""
        await self._authenticate_user(user)
        logger.debug(f"Refreshed token for user {user.user_id}")
        
    async def _authenticate_user(self, user: TestUser) -> None:
        """Authenticate user and get access token."""
        payload = self.jwt_helper.create_valid_payload()
        payload["sub"] = user.user_id
        payload["email"] = user.email
        user.access_token = await self.jwt_helper.create_jwt_token(payload)
        
    async def _cleanup_user(self, user: TestUser) -> None:
        """Clean up individual user resources."""
        logger.debug(f"Cleaning up user {user.user_id}")
        # Additional cleanup operations can be added here