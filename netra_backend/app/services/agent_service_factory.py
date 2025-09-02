"""Agent service factory functions.

Provides factory functions for creating AgentService instances
with proper dependency injection and configuration.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.dependencies import DbDep, get_llm_manager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()


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
    # Pass llm_manager first, then websocket_bridge, tool_dispatcher, and db_session_factory
    # This avoids storing the session in the llm_manager field
    db_session_factory = lambda: db_session  # Create a factory that returns the session
    return Supervisor(llm_manager, manager, tool_dispatcher, db_session_factory)