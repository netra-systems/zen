
from typing import Annotated
from fastapi import Depends, Request

from app.db.postgres import get_async_db
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.services import SecurityService
from app.agents.supervisor import Supervisor
from app.agents.tool_dispatcher import ToolDispatcher

DbDep = Annotated[AsyncSession, Depends(get_async_db)]

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

async def get_db_session(request: Request) -> AsyncSession:
    async with request.app.state.db_session_factory() as session:
        yield session

def get_security_service(request: Request) -> SecurityService:
    return request.app.state.security_service

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]

def get_agent_supervisor(request: Request) -> Supervisor:
    return request.app.state.agent_supervisor
