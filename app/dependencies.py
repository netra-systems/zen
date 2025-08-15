from typing import Annotated, TYPE_CHECKING
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_async_db
from app.llm.llm_manager import LLMManager
from app.services.security_service import SecurityService
from app.services.agent_service import AgentService
from app.services.thread_service import ThreadService
from app.services.corpus_service import CorpusService
from app.logging_config import central_logger

if TYPE_CHECKING:
    from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor

logger = central_logger.get_logger(__name__)

DbDep = Annotated[AsyncSession, Depends(get_async_db)]

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

async def get_db_session(request: Request) -> AsyncSession:
    async with request.app.state.db_session_factory() as session:
        yield session

def get_security_service(request: Request) -> SecurityService:
    logger.debug("Getting security service from app state")
    return request.app.state.security_service

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]

def get_agent_supervisor(request: Request) -> "Supervisor":
    return request.app.state.agent_supervisor

def get_agent_service(request: Request) -> AgentService:
    """Get agent service from app state"""
    return request.app.state.agent_service

def get_thread_service(request: Request) -> ThreadService:
    """Get thread service from app state"""
    return request.app.state.thread_service

def get_corpus_service(request: Request) -> CorpusService:
    """Get corpus service from app state"""
    return request.app.state.corpus_service