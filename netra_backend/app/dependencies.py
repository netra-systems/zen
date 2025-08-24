from typing import TYPE_CHECKING, Annotated, AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Import from the single source of truth for database sessions
from netra_backend.app.database import get_db

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.security_service import SecurityService

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor_consolidated import (
        SupervisorAgent as Supervisor,
    )
    from netra_backend.app.services.agent_service import AgentService
    from netra_backend.app.services.corpus_service import CorpusService
    from netra_backend.app.services.thread_service import ThreadService

logger = central_logger.get_logger(__name__)

def _validate_session_type(session) -> None:
    """Validate session is AsyncSession type."""
    if not isinstance(session, AsyncSession):
        logger.error(f"Invalid session type: {type(session)}")
        raise RuntimeError(f"Expected AsyncSession, got {type(session)}")
    logger.debug(f"Dependency injected session type: {type(session).__name__}")

async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Wrapper for database dependency with validation.
    
    Uses the single source of truth from netra_backend.app.database.
    """
    async for session in get_db():
        _validate_session_type(session)
        yield session

DbDep = Annotated[AsyncSession, Depends(get_db_dependency)]

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

# Legacy compatibility - DEPRECATED: use get_db_dependency() instead
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DEPRECATED: Legacy compatibility function for get_db_session.
    
    This function is deprecated. Use get_db_dependency() or DbDep type annotation instead.
    Kept for backward compatibility with existing routes.
    """
    async for session in get_db_dependency():
        yield session

def get_security_service(request: Request) -> SecurityService:
    logger.debug("Getting security service from app state")
    return request.app.state.security_service

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]

def get_agent_supervisor(request: Request) -> "Supervisor":
    return request.app.state.agent_supervisor

def get_agent_service(request: Request) -> "AgentService":
    """Get agent service from app state"""
    return request.app.state.agent_service

def get_thread_service(request: Request) -> "ThreadService":
    """Get thread service from app state"""
    return request.app.state.thread_service

def get_corpus_service(request: Request) -> "CorpusService":
    """Get corpus service from app state"""
    return request.app.state.corpus_service

def get_message_handler_service(request: Request):
    """Get message handler service from app state or create one."""
    # Try to get from app state first
    if hasattr(request.app.state, 'message_handler_service'):
        return request.app.state.message_handler_service
    
    # Create one using available dependencies
    from netra_backend.app.services.message_handlers import MessageHandlerService
    supervisor = get_agent_supervisor(request)
    thread_service = get_thread_service(request)
    return MessageHandlerService(supervisor, thread_service)