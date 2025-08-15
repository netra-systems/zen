"""Enhanced state management logic for supervisor agent."""

from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from app.agents.state import DeepAgentState
from app.services.state_persistence import state_persistence_service
from app.schemas.agent_state import (
    StatePersistenceRequest, StateRecoveryRequest, CheckpointType, 
    RecoveryType, AgentPhase
)
from app.logging_config import central_logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NetraException

logger = central_logger.get_logger(__name__)


class StateManager:
    """Enhanced state manager with atomic persistence and recovery."""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.state_persistence = state_persistence_service
        self.current_checkpoint_id: Optional[str] = None
        self.auto_checkpoint_interval = 300  # 5 minutes
        self.last_checkpoint_time: Optional[datetime] = None
    
    async def initialize_state(self, prompt: str, thread_id: str, 
                              user_id: str, run_id: str) -> DeepAgentState:
        """Initialize agent state with recovery support."""
        state = self._create_new_state(prompt, thread_id, user_id)
        recovered_state = await self._attempt_state_recovery(run_id, thread_id)
        if recovered_state:
            state = recovered_state
        await self._create_initial_checkpoint(state, run_id, thread_id, user_id)
        return state
    
    def _create_new_state(self, prompt: str, thread_id: str, 
                         user_id: str) -> DeepAgentState:
        """Create new agent state with initialization metadata."""
        return DeepAgentState(
            user_request=prompt,
            chat_thread_id=thread_id,
            user_id=user_id,
            step_count=0
        )
    
    async def _attempt_state_recovery(self, run_id: str, 
                                      thread_id: str) -> Optional[DeepAgentState]:
        """Attempt to recover agent state from previous run."""
        try:
            recovered_state = await self._load_previous_state(run_id)
            return self._validate_recovered_state(recovered_state, run_id)
        except Exception as e:
            logger.warning(f"State recovery failed for run {run_id}: {e}")
            return None
    
    async def _load_previous_state(self, run_id: str) -> Optional[DeepAgentState]:
        """Load the most recent state."""
        async with self.db_session_factory() as session:
            return await self.state_persistence.load_agent_state(
                run_id, None, session)
    
    def _validate_recovered_state(self, recovered_state: Optional[DeepAgentState], 
                                 run_id: str) -> Optional[DeepAgentState]:
        """Validate and log recovered state."""
        if recovered_state:
            logger.info(f"Recovered state for run {run_id}")
            return recovered_state
        return None
    
    async def _create_initial_checkpoint(self, state: DeepAgentState, run_id: str,
                                        thread_id: str, user_id: str) -> None:
        """Create initial state checkpoint."""
        request = self._build_initial_checkpoint_request(
            state, run_id, thread_id, user_id)
        async with self.db_session_factory() as session:
            success, checkpoint_id = await self.state_persistence.save_agent_state(
                request, session)
        if success:
            self._update_checkpoint_tracking(checkpoint_id)
    
    def _build_initial_checkpoint_request(self, state: DeepAgentState, 
                                         run_id: str, thread_id: str, 
                                         user_id: str) -> StatePersistenceRequest:
        """Build initial checkpoint request."""
        return StatePersistenceRequest(
            run_id=run_id, thread_id=thread_id, user_id=user_id,
            state_data=state.model_dump(), checkpoint_type=CheckpointType.AUTO,
            agent_phase=AgentPhase.INITIALIZATION, is_recovery_point=True
        )
    
    def _update_checkpoint_tracking(self, checkpoint_id: str) -> None:
        """Update checkpoint tracking state."""
        self.current_checkpoint_id = checkpoint_id
        self.last_checkpoint_time = datetime.now(timezone.utc)
        logger.info(f"Created initial checkpoint {checkpoint_id}")
    
    async def save_state_checkpoint(self, state: DeepAgentState, run_id: str,
                                   thread_id: str, user_id: str, 
                                   checkpoint_type: CheckpointType = CheckpointType.AUTO,
                                   agent_phase: Optional[AgentPhase] = None) -> bool:
        """Save state checkpoint with specified type."""
        request = self._build_checkpoint_request(
            state, run_id, thread_id, user_id, checkpoint_type, agent_phase)
        return await self._execute_checkpoint_save(request, run_id)
    
    def _build_checkpoint_request(self, state: DeepAgentState, run_id: str,
                                 thread_id: str, user_id: str,
                                 checkpoint_type: CheckpointType,
                                 agent_phase: Optional[AgentPhase]) -> StatePersistenceRequest:
        """Build checkpoint save request."""
        return StatePersistenceRequest(
            run_id=run_id, thread_id=thread_id, user_id=user_id,
            state_data=state.model_dump(), checkpoint_type=checkpoint_type,
            agent_phase=agent_phase, execution_context={"step_count": state.step_count},
            is_recovery_point=(checkpoint_type == CheckpointType.PHASE_TRANSITION)
        )
    
    async def _execute_checkpoint_save(self, request: StatePersistenceRequest,
                                      run_id: str) -> bool:
        """Execute checkpoint save operation."""
        async with self.db_session_factory() as session:
            success, checkpoint_id = await self.state_persistence.save_agent_state(
                request, session)
        if success:
            self._finalize_checkpoint_save(checkpoint_id, run_id)
        return success
    
    def _finalize_checkpoint_save(self, checkpoint_id: str, run_id: str) -> None:
        """Finalize checkpoint save operation."""
        self.current_checkpoint_id = checkpoint_id
        self.last_checkpoint_time = datetime.now(timezone.utc)
        logger.debug(f"Saved checkpoint {checkpoint_id} for run {run_id}")
    
    async def auto_checkpoint_if_needed(self, state: DeepAgentState, run_id: str,
                                        thread_id: str, user_id: str) -> bool:
        """Create automatic checkpoint if time threshold exceeded."""
        if not self._should_create_auto_checkpoint():
            return False
        return await self.save_state_checkpoint(
            state, run_id, thread_id, user_id, CheckpointType.AUTO)
    
    def _should_create_auto_checkpoint(self) -> bool:
        """Check if auto checkpoint is needed."""
        if not self.last_checkpoint_time:
            return False
        time_since_last = datetime.now(timezone.utc) - self.last_checkpoint_time
        return time_since_last.total_seconds() >= self.auto_checkpoint_interval
    
    async def handle_agent_crash_recovery(self, run_id: str, thread_id: str,
                                          failure_reason: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Handle agent crash recovery scenario."""
        recovery_request = self._build_crash_recovery_request(
            run_id, thread_id, failure_reason)
        success, recovery_id = await self.state_persistence.recover_agent_state(
            recovery_request, self.db_session)
        return await self._process_crash_recovery_result(
            success, recovery_id, run_id)
    
    def _build_crash_recovery_request(self, run_id: str, thread_id: str,
                                     failure_reason: str) -> StateRecoveryRequest:
        """Build crash recovery request."""
        return StateRecoveryRequest(
            run_id=run_id, thread_id=thread_id,
            recovery_type=RecoveryType.RESUME, failure_reason=failure_reason,
            auto_recovery=True
        )
    
    async def _process_crash_recovery_result(self, success: bool, recovery_id: str,
                                           run_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Process crash recovery result."""
        if success:
            recovered_state = await self.state_persistence.load_agent_state(
                run_id, None, self.db_session)
            logger.info(f"Crash recovery {recovery_id} completed for run {run_id}")
            return True, recovered_state
        logger.error(f"Crash recovery failed for run {run_id}")
        return False, None
    
    async def create_phase_transition_checkpoint(self, state: DeepAgentState, 
                                                run_id: str, thread_id: str, 
                                                user_id: str, phase: AgentPhase) -> bool:
        """Create checkpoint at phase transitions."""
        return await self.save_state_checkpoint(
            state, run_id, thread_id, user_id, 
            CheckpointType.PHASE_TRANSITION, phase)
    
    async def rollback_to_checkpoint(self, run_id: str, thread_id: str,
                                    checkpoint_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Rollback to a specific checkpoint."""
        recovery_request = self._build_rollback_recovery_request(
            run_id, thread_id, checkpoint_id)
        success, recovery_id = await self.state_persistence.recover_agent_state(
            recovery_request, self.db_session)
        return await self._process_rollback_result(
            success, run_id, checkpoint_id)
    
    def _build_rollback_recovery_request(self, run_id: str, thread_id: str,
                                        checkpoint_id: str) -> StateRecoveryRequest:
        """Build rollback recovery request."""
        return StateRecoveryRequest(
            run_id=run_id, thread_id=thread_id,
            recovery_type=RecoveryType.ROLLBACK, target_snapshot_id=checkpoint_id,
            auto_recovery=False
        )
    
    async def _process_rollback_result(self, success: bool, run_id: str,
                                      checkpoint_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Process rollback recovery result."""
        if success:
            recovered_state = await self.state_persistence.load_agent_state(
                run_id, checkpoint_id, self.db_session)
            return True, recovered_state
        return False, None