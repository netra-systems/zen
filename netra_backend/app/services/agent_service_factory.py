"""Agent service factory functions.

Provides factory functions for creating AgentService instances
with proper dependency injection and configuration.

ARCHITECTURE: Factory pattern implementation using lazy WebSocket manager initialization
to comply with User Context Architecture and eliminate import-time dependencies.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from netra_backend.app.dependencies import DbDep, get_llm_manager
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core import create_websocket_manager


def get_agent_service(
    db_session: DbDep, 
    llm_manager: LLMManager = Depends(get_llm_manager)
) -> AgentService:
    """
    Factory function for creating AgentService instances.
    
    ARCHITECTURE: Uses lazy initialization pattern - WebSocket managers are created
    per-request when UserExecutionContext is available, not at import time.
    """
    supervisor = _create_supervisor_agent(db_session, llm_manager)
    return AgentService(supervisor)


def _create_supervisor_agent(db_session: AsyncSession, llm_manager: LLMManager):
    """
    Create configured supervisor agent with lazy WebSocket initialization.
    
    CRITICAL: No import-time WebSocket manager creation. WebSocket bridge will be
    created per-request when UserExecutionContext is available.
    """
    from netra_backend.app.agents.supervisor_consolidated import (
        SupervisorAgent as Supervisor,
    )
    
    # Create supervisor without WebSocket bridge (will be set per-request)
    db_session_factory = lambda: db_session  # Create a factory that returns the session
    return Supervisor(
        llm_manager=llm_manager,
        websocket_bridge=None,  # ARCHITECTURE: Lazy initialization per-request
        db_session_factory=db_session_factory,
        user_context=None  # Will be set per-request
    )