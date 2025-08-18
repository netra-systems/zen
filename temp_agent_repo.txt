"""Agent Repository Pattern Implementation

Repositories for Agent, Thread, Message, and AgentState entities.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.logging_config import central_logger
from app.db.models_agent import Assistant, Thread, Message
from app.db.models_agent_state import AgentStateSnapshot
from .base_repository import BaseRepository

logger = central_logger.get_logger(__name__)


class AgentRepository(BaseRepository[Assistant]):
    """Repository for Assistant entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Assistant, session)
    
    async def get_by_model(self, model: str) -> List[Assistant]:
        """Get assistants by model name."""
        try:
            result = await self.session.execute(
                select(Assistant).where(Assistant.model == model)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting assistants by model: {e}")
            return []
    
    async def get_by_name(self, name: str) -> Optional[Assistant]:
        """Get assistant by name."""
        return await self.get_by_field("name", name)


class ThreadRepository(BaseRepository[Thread]):
    """Repository for Thread entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Thread, session)
    
    async def get_thread_with_messages(self, thread_id: str) -> Optional[Thread]:
        """Get thread with all messages loaded."""
        try:
            result = await self.session.execute(
                select(Thread)
                .where(Thread.id == thread_id)
                .options(selectinload(Thread.messages))
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting thread with messages: {e}")
            return None
    
    async def get_recent_threads(self, limit: int = 50) -> List[Thread]:
        """Get most recent threads."""
        try:
            result = await self.session.execute(
                select(Thread)
                .order_by(desc(Thread.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent threads: {e}")
            return []


class MessageRepository(BaseRepository[Message]):
    """Repository for Message entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)
    
    async def get_thread_messages(self, thread_id: str) -> List[Message]:
        """Get all messages for a thread."""
        try:
            result = await self.session.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting thread messages: {e}")
            return []
    
    async def get_latest_message(self, thread_id: str) -> Optional[Message]:
        """Get latest message in thread."""
        try:
            result = await self.session.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(desc(Message.created_at))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting latest message: {e}")
            return None


class AgentStateRepository(BaseRepository[AgentStateSnapshot]):
    """Repository for AgentStateSnapshot entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(AgentStateSnapshot, session)
    
    async def get_by_run_id(self, run_id: str) -> List[AgentStateSnapshot]:
        """Get agent states by run ID."""
        try:
            result = await self.session.execute(
                select(AgentStateSnapshot)
                .where(AgentStateSnapshot.run_id == run_id)
                .order_by(desc(AgentStateSnapshot.created_at))
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting agent states by run ID: {e}")
            return []
    
    async def get_latest_state(self, run_id: str) -> Optional[AgentStateSnapshot]:
        """Get latest agent state for run."""
        try:
            result = await self.session.execute(
                select(AgentStateSnapshot)
                .where(AgentStateSnapshot.run_id == run_id)
                .order_by(desc(AgentStateSnapshot.created_at))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting latest agent state: {e}")
            return None
    
    async def get_user_states(self, user_id: str, limit: int = 50) -> List[AgentStateSnapshot]:
        """Get agent states for a user."""
        try:
            result = await self.session.execute(
                select(AgentStateSnapshot)
                .where(AgentStateSnapshot.user_id == user_id)
                .order_by(desc(AgentStateSnapshot.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting user agent states: {e}")
            return []