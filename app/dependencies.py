from typing import Annotated, TYPE_CHECKING
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_async_db
from app.llm.llm_manager import LLMManager
from app.services.security_service import SecurityService
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