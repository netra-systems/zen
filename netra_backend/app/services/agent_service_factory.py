"""Agent service factory functions.

Provides factory functions for creating AgentService instances
with proper dependency injection and configuration.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.dependencies import DbDep, get_llm_manager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.websocket.ws_manager import manager


def get_agent_service(
    db_session: DbDep, 
    llm_manager: LLMManager = Depends(get_llm_manager)
) -> AgentService:
    """Factory function for creating AgentService instances."""
    supervisor = _create_supervisor_agent(db_session, llm_manager)
    return AgentService(supervisor)


def _create_supervisor_agent(db_session: AsyncSession, llm_manager: LLMManager):
    """Create configured supervisor agent."""
    from netra_backend.app.agents.supervisor_consolidated import (
        SupervisorAgent as Supervisor,
    )
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    tool_dispatcher = ToolDispatcher(db_session)
    return Supervisor(db_session, llm_manager, manager, tool_dispatcher)