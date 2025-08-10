"""Supervisor Agent Module

This module provides the main Supervisor implementation that orchestrates sub-agents.
It delegates to the consolidated supervisor for improved architecture.
"""

from app.logging_config import central_logger
from typing import Any, Dict
from app.agents.base import BaseSubAgent
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.supervisor_consolidated import SupervisorAgent as ConsolidatedSupervisor

logger = central_logger.get_logger(__name__)

class Supervisor(BaseSubAgent):
    """Main Supervisor class that delegates to the consolidated implementation."""
    
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager, websocket_manager: any, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="Supervisor", description="The supervisor agent that orchestrates the sub-agents.")
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self.thread_id = None  # Will be set by AgentService
        self.user_id = None  # Will be set by AgentService
        
        # Use the improved consolidated supervisor
        self._impl = ConsolidatedSupervisor(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        logger.info("Using consolidated supervisor implementation")

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the supervisor's orchestration logic."""
        if hasattr(self._impl, 'execute'):
            await self._impl.execute(state, run_id, stream_updates)
    
    async def run(self, user_request: str, run_id: str, stream_updates: bool) -> DeepAgentState:
        """Run the supervisor workflow"""
        # Delegate to consolidated implementation
        self._impl.thread_id = self.thread_id
        self._impl.user_id = self.user_id
        return await self._impl.run(user_request, run_id, stream_updates)

    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        """Get agent state from the consolidated implementation"""
        if hasattr(self._impl, 'get_agent_state'):
            return await self._impl.get_agent_state(run_id)
        return {"status": "not_found"}

    async def shutdown(self):
        """Shutdown the supervisor"""
        if hasattr(self._impl, 'shutdown'):
            await self._impl.shutdown()
        else:
            logger.info("Supervisor shutdown complete.")