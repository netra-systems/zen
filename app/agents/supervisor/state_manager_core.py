"""Core state management logic for supervisor agent."""

from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from app.agents.state import DeepAgentState
from app.schemas.agent_state import (
    CheckpointType, AgentPhase
)
from app.logging_config import central_logger
from .state_checkpoint_manager import StateCheckpointManager
from .state_recovery_manager import AgentStateRecoveryManager

logger = central_logger.get_logger(__name__)


class StateManagerCore:
    """Core state manager with initialization and coordination."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.checkpoint_manager = StateCheckpointManager(db_session)
        self.recovery_manager = AgentStateRecoveryManager(db_session)
    
    async def initialize_state(self, prompt: str, thread_id: str, 
                              user_id: str, run_id: str) -> DeepAgentState:
        """Initialize agent state with recovery support."""
        state = self._create_new_state(prompt, thread_id, user_id)
        state = await self._apply_recovery_if_available(state, run_id, thread_id)
        await self.checkpoint_manager.create_initial_checkpoint(state, run_id, thread_id, user_id)
        return state
    
    def _create_new_state(self, prompt: str, thread_id: str, 
                         user_id: str) -> DeepAgentState:
        """Create new agent state with initialization metadata."""
        state_params = self._build_state_params(prompt, thread_id, user_id)
        return DeepAgentState(**state_params)
    
    def _build_state_params(self, prompt: str, thread_id: str, user_id: str) -> dict:
        """Build parameters for new state creation."""
        return {
            "user_request": prompt,
            "chat_thread_id": thread_id,
            "user_id": user_id,
            "step_count": 0
        }
    
    async def _apply_recovery_if_available(self, state: DeepAgentState, 
                                          run_id: str, thread_id: str) -> DeepAgentState:
        """Apply recovery state if available."""
        recovered_state = await self.recovery_manager.attempt_state_recovery(run_id, thread_id)
        return recovered_state if recovered_state else state
    
    async def save_state_checkpoint(self, state: DeepAgentState, run_id: str,
                                   thread_id: str, user_id: str, 
                                   checkpoint_type: CheckpointType = CheckpointType.AUTO,
                                   agent_phase: Optional[AgentPhase] = None) -> bool:
        """Save state checkpoint with specified type."""
        return await self.checkpoint_manager.save_state_checkpoint(
            state, run_id, thread_id, user_id, checkpoint_type, agent_phase)
    
    async def auto_checkpoint_if_needed(self, state: DeepAgentState, run_id: str,
                                        thread_id: str, user_id: str) -> bool:
        """Create automatic checkpoint if time threshold exceeded."""
        return await self.checkpoint_manager.auto_checkpoint_if_needed(
            state, run_id, thread_id, user_id)
    
    async def handle_agent_crash_recovery(self, run_id: str, thread_id: str,
                                          failure_reason: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Handle agent crash recovery scenario."""
        return await self.recovery_manager.handle_agent_crash_recovery(
            run_id, thread_id, failure_reason)
    
    async def create_phase_transition_checkpoint(self, state: DeepAgentState, 
                                                run_id: str, thread_id: str, 
                                                user_id: str, phase: AgentPhase) -> bool:
        """Create checkpoint at phase transitions."""
        return await self.checkpoint_manager.create_phase_transition_checkpoint(
            state, run_id, thread_id, user_id, phase)
    
    async def rollback_to_checkpoint(self, run_id: str, thread_id: str,
                                    checkpoint_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Rollback to a specific checkpoint."""
        return await self.recovery_manager.rollback_to_checkpoint(
            run_id, thread_id, checkpoint_id)
