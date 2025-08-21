"""User Repository Pattern Implementation

Repositories for User, Secret, and ToolUsageLog entities.
"""

from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_user import Secret, ToolUsageLog, User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return await self.get_by_field("email", email)
    
    async def _execute_active_users_query(self, limit: int) -> List[User]:
        """Execute query for active users."""
        result = await self.session.execute(
            select(User).where(User.is_active == True).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_active_users(self, limit: int = 100) -> List[User]:
        """Get all active users."""
        try:
            return await self._execute_active_users_query(limit)
        except SQLAlchemyError as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    async def _execute_plan_tier_query(self, plan_tier: str) -> List[User]:
        """Execute query for users by plan tier."""
        result = await self.session.execute(
            select(User).where(User.plan_tier == plan_tier)
        )
        return list(result.scalars().all())
    
    async def get_by_plan_tier(self, plan_tier: str) -> List[User]:
        """Get users by plan tier."""
        try:
            return await self._execute_plan_tier_query(plan_tier)
        except SQLAlchemyError as e:
            logger.error(f"Error getting users by plan tier: {e}")
            return []
    
    async def update_plan(self, user_id: str, plan_tier: str, **kwargs) -> bool:
        """Update user plan tier and related fields."""
        update_data = {"plan_tier": plan_tier, **kwargs}
        return await self.update_by_id(user_id, **update_data)


class SecretRepository(BaseRepository[Secret]):
    """Repository for Secret entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Secret, session)
    
    async def _execute_user_secrets_query(self, user_id: str) -> List[Secret]:
        """Execute query for user secrets."""
        result = await self.session.execute(
            select(Secret).where(Secret.user_id == user_id)
        )
        return list(result.scalars().all())
    
    async def get_user_secrets(self, user_id: str) -> List[Secret]:
        """Get all secrets for a user."""
        try:
            return await self._execute_user_secrets_query(user_id)
        except SQLAlchemyError as e:
            logger.error(f"Error getting user secrets: {e}")
            return []
    
    async def _execute_user_secret_key_query(self, user_id: str, key: str) -> Optional[Secret]:
        """Execute query for user secret by key."""
        result = await self.session.execute(
            select(Secret).where(
                and_(Secret.user_id == user_id, Secret.key == key)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_secret_by_key(self, user_id: str, key: str) -> Optional[Secret]:
        """Get specific secret for user by key."""
        try:
            return await self._execute_user_secret_key_query(user_id, key)
        except SQLAlchemyError as e:
            logger.error(f"Error getting user secret by key: {e}")
            return None


class ToolUsageRepository(BaseRepository[ToolUsageLog]):
    """Repository for ToolUsageLog entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ToolUsageLog, session)
    
    def _build_user_usage_query(self, user_id: str, limit: int):
        """Build query for user tool usage."""
        return select(ToolUsageLog)\
            .where(ToolUsageLog.user_id == user_id)\
            .order_by(ToolUsageLog.created_at.desc())\
            .limit(limit)
    
    async def _execute_user_usage_query(self, user_id: str, limit: int) -> List[ToolUsageLog]:
        """Execute query for user tool usage."""
        query = self._build_user_usage_query(user_id, limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_user_usage(self, user_id: str, limit: int = 100) -> List[ToolUsageLog]:
        """Get tool usage logs for a user."""
        try:
            return await self._execute_user_usage_query(user_id, limit)
        except SQLAlchemyError as e:
            logger.error(f"Error getting user tool usage: {e}")
            return []
    
    def _build_tool_name_query(self, tool_name: str, limit: int):
        """Build query for tool usage by name."""
        return select(ToolUsageLog)\
            .where(ToolUsageLog.tool_name == tool_name)\
            .order_by(ToolUsageLog.created_at.desc())\
            .limit(limit)
    
    async def _execute_tool_name_query(self, tool_name: str, limit: int) -> List[ToolUsageLog]:
        """Execute query for tool usage by name."""
        query = self._build_tool_name_query(tool_name, limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_tool_name(self, tool_name: str, limit: int = 100) -> List[ToolUsageLog]:
        """Get usage logs by tool name."""
        try:
            return await self._execute_tool_name_query(tool_name, limit)
        except SQLAlchemyError as e:
            logger.error(f"Error getting tool usage by name: {e}")
            return []