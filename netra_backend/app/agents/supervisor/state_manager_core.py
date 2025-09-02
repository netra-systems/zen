"""Core state management logic for supervisor agent."""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_checkpoint_manager import (
    StateCheckpointManager,
)
from netra_backend.app.agents.supervisor.state_recovery_manager import (
    AgentStateRecoveryManager,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent_state import AgentPhase, CheckpointType

logger = central_logger.get_logger(__name__)


class StateManagerCore:
    """Core state manager with initialization and coordination.
    
    CRITICAL: This class no longer stores db_session as instance variable.
    Database sessions must be passed as parameters to methods that need them.
    """
    
    def __init__(self):
        """Initialize without global session storage."""
        # REMOVED: self.db_session = db_session (global session storage removed)
        # Subcomponents also updated to remove session storage
        self.checkpoint_manager = StateCheckpointManager()
        self.recovery_manager = AgentStateRecoveryManager()
    
    async def initialize_state(self, prompt: str, thread_id: str, 
                              user_id: str, run_id: str, db_session) -> DeepAgentState:
        """Initialize agent state with recovery support.
        
        Args:
            prompt: User prompt to initialize state with
            thread_id: Thread identifier
            user_id: User identifier
            run_id: Run identifier
            db_session: Database session for state operations
        """
        state = self._create_new_state(prompt, thread_id, user_id)
        state = await self._apply_recovery_if_available(state, run_id, thread_id, db_session)
        await self.checkpoint_manager.create_initial_checkpoint(state, run_id, thread_id, user_id, db_session)
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
                                          run_id: str, thread_id: str, db_session) -> DeepAgentState:
        """Apply recovery state if available."""
        recovered_state = await self.recovery_manager.attempt_state_recovery(run_id, thread_id, db_session)
        return recovered_state if recovered_state else state
    
    async def save_state_checkpoint(self, state: DeepAgentState, run_id: str,
                                   thread_id: str, user_id: str, db_session,
                                   checkpoint_type: CheckpointType = CheckpointType.AUTO,
                                   agent_phase: Optional[AgentPhase] = None) -> bool:
        """Save state checkpoint with specified type.
        
        Args:
            state: State to checkpoint
            run_id: Run identifier
            thread_id: Thread identifier
            user_id: User identifier
            db_session: Database session for checkpoint operations
            checkpoint_type: Type of checkpoint to create
            agent_phase: Optional phase information
        """
        return await self.checkpoint_manager.save_state_checkpoint(
            state, run_id, thread_id, user_id, db_session, checkpoint_type, agent_phase)
    
    async def auto_checkpoint_if_needed(self, state: DeepAgentState, run_id: str,
                                        thread_id: str, user_id: str, db_session) -> bool:
        """Create automatic checkpoint if time threshold exceeded.
        
        Args:
            state: State to potentially checkpoint
            run_id: Run identifier
            thread_id: Thread identifier
            user_id: User identifier
            db_session: Database session for checkpoint operations
        """
        return await self.checkpoint_manager.auto_checkpoint_if_needed(
            state, run_id, thread_id, user_id, db_session)
    
    async def handle_agent_crash_recovery(self, run_id: str, thread_id: str,
                                          failure_reason: str, db_session) -> Tuple[bool, Optional[DeepAgentState]]:
        """Handle agent crash recovery scenario.
        
        Args:
            run_id: Run identifier
            thread_id: Thread identifier
            failure_reason: Reason for the crash
            db_session: Database session for recovery operations
        """
        return await self.recovery_manager.handle_agent_crash_recovery(
            run_id, thread_id, failure_reason, db_session)
    
    async def create_phase_transition_checkpoint(self, state: DeepAgentState, 
                                                run_id: str, thread_id: str, 
                                                user_id: str, phase: AgentPhase, db_session) -> bool:
        """Create checkpoint at phase transitions.
        
        Args:
            state: State to checkpoint
            run_id: Run identifier
            thread_id: Thread identifier
            user_id: User identifier
            phase: Agent phase being transitioned to
            db_session: Database session for checkpoint operations
        """
        return await self.checkpoint_manager.create_phase_transition_checkpoint(
            state, run_id, thread_id, user_id, phase, db_session)
    
    async def rollback_to_checkpoint(self, run_id: str, thread_id: str,
                                    checkpoint_id: str, db_session) -> Tuple[bool, Optional[DeepAgentState]]:
        """Rollback to a specific checkpoint.
        
        Args:
            run_id: Run identifier
            thread_id: Thread identifier
            checkpoint_id: Checkpoint to rollback to
            db_session: Database session for rollback operations
        """
        return await self.recovery_manager.rollback_to_checkpoint(
            run_id, thread_id, checkpoint_id, db_session)
