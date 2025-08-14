"""State management logic for supervisor agent."""

from typing import Dict
from app.agents.state import DeepAgentState
from app.services.state_persistence_service import state_persistence_service
from app.logging_config import central_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = central_logger.get_logger(__name__)


class StateManager:
    """Handles state initialization and restoration for supervisor."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.state_persistence = state_persistence_service
    
    async def initialize_state(self, prompt: str, 
                              thread_id: str, user_id: str) -> DeepAgentState:
        """Initialize agent state."""
        state = self._create_new_state(prompt, thread_id, user_id)
        await self._restore_previous_state(state, thread_id)
        return state
    
    def _create_new_state(self, prompt: str, 
                         thread_id: str, user_id: str) -> DeepAgentState:
        """Create new agent state."""
        return DeepAgentState(
            user_request=prompt,
            chat_thread_id=thread_id,
            user_id=user_id
        )
    
    async def _restore_previous_state(self, state: DeepAgentState, 
                                     thread_id: str) -> None:
        """Restore previous state if available."""
        thread_context = await self.state_persistence.get_thread_context(thread_id)
        if not thread_context or not thread_context.get('current_run_id'):
            return
        await self._merge_restored_state(state, thread_context, thread_id)
    
    async def _merge_restored_state(self, state: DeepAgentState,
                                   thread_context: Dict, thread_id: str) -> None:
        """Merge restored state into current state."""
        restored = await self.state_persistence.load_agent_state(
            thread_context['current_run_id'], self.db_session)
        if not restored:
            return
        self._apply_restored_fields(state, restored)
        logger.info(f"Restored state for thread {thread_id}")
    
    def _apply_restored_fields(self, state: DeepAgentState, 
                              restored: DeepAgentState) -> None:
        """Apply restored fields to state."""
        self._restore_core_fields(state, restored)
        self._restore_report_field(state, restored)
    
    def _restore_core_fields(self, state: DeepAgentState, restored: DeepAgentState) -> None:
        """Restore core workflow fields."""
        if restored.triage_result:
            state.triage_result = restored.triage_result
        if restored.data_result:
            state.data_result = restored.data_result
        if restored.optimizations_result:
            state.optimizations_result = restored.optimizations_result
        if restored.action_plan_result:
            state.action_plan_result = restored.action_plan_result
    
    def _restore_report_field(self, state: DeepAgentState, restored: DeepAgentState) -> None:
        """Restore report field."""
        if restored.report_result:
            state.report_result = restored.report_result