"""User Repository Pattern Implementation

Repositories for User, Secret, and ToolUsageLog entities.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from app.logging_config import central_logger
from app.db.models_user import User, Secret, ToolUsageLog
from .base_repository import BaseRepository

logger = central_logger.get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return await self.get_by_field("email", email)
    
    async def get_active_users(self, limit: int = 100) -> List[User]:
        """Get all active users."""
        try:
            result = await self.session.execute(
                select(User).where(User.is_active == True).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    async def get_by_plan_tier(self, plan_tier: str) -> List[User]:
        """Get users by plan tier."""
        try:
            result = await self.session.execute(
                select(User).where(User.plan_tier == plan_tier)
            )
            return list(result.scalars().all())
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
    
    async def get_user_secrets(self, user_id: str) -> List[Secret]:
        """Get all secrets for a user."""
        try:
            result = await self.session.execute(
                select(Secret).where(Secret.user_id == user_id)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting user secrets: {e}")
            return []
    
    async def get_user_secret_by_key(self, user_id: str, key: str) -> Optional[Secret]:
        """Get specific secret for user by key."""
        try:
            result = await self.session.execute(
                select(Secret).where(
                    and_(Secret.user_id == user_id, Secret.key == key)
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user secret by key: {e}")
            return None


class ToolUsageRepository(BaseRepository[ToolUsageLog]):
    """Repository for ToolUsageLog entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ToolUsageLog, session)
    
    async def get_user_usage(self, user_id: str, limit: int = 100) -> List[ToolUsageLog]:
        """Get tool usage logs for a user."""
        try:
            result = await self.session.execute(
                select(ToolUsageLog)
                .where(ToolUsageLog.user_id == user_id)
                .order_by(ToolUsageLog.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting user tool usage: {e}")
            return []
    
    async def get_by_tool_name(self, tool_name: str, limit: int = 100) -> List[ToolUsageLog]:
        """Get usage logs by tool name."""
        try:
            result = await self.session.execute(
                select(ToolUsageLog)
                .where(ToolUsageLog.tool_name == tool_name)
                .order_by(ToolUsageLog.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting tool usage by name: {e}")
            return []