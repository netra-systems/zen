"""Agent Repository Pattern Implementation

Repositories for Agent, Thread, Message, and AgentState entities.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.models_agent import Assistant, Thread, Message
from netra_backend.app.db.models_agent_state import AgentStateSnapshot
from netra_backend.app.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)


class AgentRepository(BaseRepository[Assistant]):
    """Repository for Assistant entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Assistant, session)
    
    def _build_model_query(self, model: str):
        """Build query for assistants by model."""
        return select(Assistant).where(Assistant.model == model)
    
    def _handle_model_error(self, e: SQLAlchemyError) -> List[Assistant]:
        """Handle model query error."""
        logger.error(f"Error getting assistants by model: {e}")
        return []
    
    async def get_by_model(self, model: str) -> List[Assistant]:
        """Get assistants by model name."""
        try:
            query = self._build_model_query(model)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            return self._handle_model_error(e)
    
    async def get_by_name(self, name: str) -> Optional[Assistant]:
        """Get assistant by name."""
        return await self.get_by_field("name", name)


class ThreadRepository(BaseRepository[Thread]):
    """Repository for Thread entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Thread, session)
    
    def _build_thread_with_messages_query(self, thread_id: str):
        """Build query for thread with messages."""
        return (select(Thread)
                .where(Thread.id == thread_id)
                .options(selectinload(Thread.messages)))
    
    def _handle_thread_messages_error(self, e: SQLAlchemyError):
        """Handle thread messages query error."""
        logger.error(f"Error getting thread with messages: {e}")
        return None
    
    async def get_thread_with_messages(self, thread_id: str) -> Optional[Thread]:
        """Get thread with all messages loaded."""
        try:
            query = self._build_thread_with_messages_query(thread_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            return self._handle_thread_messages_error(e)
    
    def _build_recent_threads_query(self, limit: int):
        """Build query for recent threads."""
        return (select(Thread)
                .order_by(desc(Thread.created_at))
                .limit(limit))
    
    def _handle_recent_threads_error(self, e: SQLAlchemyError) -> List[Thread]:
        """Handle recent threads query error."""
        logger.error(f"Error getting recent threads: {e}")
        return []
    
    async def get_recent_threads(self, limit: int = 50) -> List[Thread]:
        """Get most recent threads."""
        try:
            query = self._build_recent_threads_query(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            return self._handle_recent_threads_error(e)


class MessageRepository(BaseRepository[Message]):
    """Repository for Message entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)
    
    def _build_thread_messages_query(self, thread_id: str):
        """Build query for thread messages."""
        return (select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at))
    
    def _handle_thread_messages_error(self, e: SQLAlchemyError) -> List[Message]:
        """Handle thread messages query error."""
        logger.error(f"Error getting thread messages: {e}")
        return []
    
    async def get_thread_messages(self, thread_id: str) -> List[Message]:
        """Get all messages for a thread."""
        try:
            query = self._build_thread_messages_query(thread_id)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            return self._handle_thread_messages_error(e)
    
    def _build_latest_message_query(self, thread_id: str):
        """Build query for latest message."""
        return (select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(desc(Message.created_at))
                .limit(1))
    
    def _handle_latest_message_error(self, e: SQLAlchemyError):
        """Handle latest message query error."""
        logger.error(f"Error getting latest message: {e}")
        return None
    
    async def get_latest_message(self, thread_id: str) -> Optional[Message]:
        """Get latest message in thread."""
        try:
            query = self._build_latest_message_query(thread_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            return self._handle_latest_message_error(e)


class AgentStateRepository(BaseRepository[AgentStateSnapshot]):
    """Repository for AgentStateSnapshot entity operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(AgentStateSnapshot, session)
    
    def _build_run_states_query(self, run_id: str):
        """Build query for agent states by run ID."""
        return (select(AgentStateSnapshot)
                .where(AgentStateSnapshot.run_id == run_id)
                .order_by(desc(AgentStateSnapshot.created_at)))
    
    def _handle_run_states_error(self, e: SQLAlchemyError) -> List[AgentStateSnapshot]:
        """Handle run states query error."""
        logger.error(f"Error getting agent states by run ID: {e}")
        return []
    
    async def get_by_run_id(self, run_id: str) -> List[AgentStateSnapshot]:
        """Get agent states by run ID."""
        try:
            query = self._build_run_states_query(run_id)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            return self._handle_run_states_error(e)
    
    def _build_latest_state_query(self, run_id: str):
        """Build query for latest agent state."""
        return (select(AgentStateSnapshot)
                .where(AgentStateSnapshot.run_id == run_id)
                .order_by(desc(AgentStateSnapshot.created_at))
                .limit(1))
    
    def _handle_latest_state_error(self, e: SQLAlchemyError):
        """Handle latest state query error."""
        logger.error(f"Error getting latest agent state: {e}")
        return None
    
    async def get_latest_state(self, run_id: str) -> Optional[AgentStateSnapshot]:
        """Get latest agent state for run."""
        try:
            query = self._build_latest_state_query(run_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            return self._handle_latest_state_error(e)
    
    def _build_user_states_query(self, user_id: str, limit: int):
        """Build query for user agent states."""
        return (select(AgentStateSnapshot)
                .where(AgentStateSnapshot.user_id == user_id)
                .order_by(desc(AgentStateSnapshot.created_at))
                .limit(limit))
    
    def _handle_user_states_error(self, e: SQLAlchemyError) -> List[AgentStateSnapshot]:
        """Handle user states query error."""
        logger.error(f"Error getting user agent states: {e}")
        return []
    
    async def get_user_states(self, user_id: str, limit: int = 50) -> List[AgentStateSnapshot]:
        """Get agent states for a user."""
        try:
            query = self._build_user_states_query(user_id, limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            return self._handle_user_states_error(e)