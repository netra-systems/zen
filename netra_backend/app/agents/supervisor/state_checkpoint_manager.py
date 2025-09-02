"""Checkpoint management functionality for supervisor state."""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.db.session import get_session_from_factory
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent_state import (
    AgentPhase,
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.state_persistence import state_persistence_service

logger = central_logger.get_logger(__name__)


class StateCheckpointManager:
    """Manages state checkpointing and persistence.
    
    CRITICAL: This class no longer stores db_session as instance variable.
    Database sessions must be passed as parameters to methods that need them.
    """
    
    def __init__(self):
        """Initialize without global session storage."""
        # REMOVED: self.db_session = db_session (global session storage removed)
        self.state_persistence = state_persistence_service
        self.current_checkpoint_id: Optional[str] = None
        self.auto_checkpoint_interval = 300  # 5 minutes
        self.last_checkpoint_time: Optional[datetime] = None
    
    async def create_initial_checkpoint(self, state: DeepAgentState, run_id: str,
                                       thread_id: str, user_id: str, db_session) -> None:
        """Create initial state checkpoint.
        
        Args:
            state: State to checkpoint
            run_id: Run identifier
            thread_id: Thread identifier
            user_id: User identifier
            db_session: Database session for checkpoint operations
        """
        request = self._build_initial_checkpoint_request(
            state, run_id, thread_id, user_id)
        success, checkpoint_id = await self._save_checkpoint_request(request, db_session)
        self._handle_checkpoint_save_result(success, checkpoint_id)
    
    def _build_initial_checkpoint_request(self, state: DeepAgentState, 
                                         run_id: str, thread_id: str, 
                                         user_id: str) -> StatePersistenceRequest:
        """Build initial checkpoint request."""
        return self._create_checkpoint_request(
            state, run_id, thread_id, user_id, 
            CheckpointType.AUTO, AgentPhase.INITIALIZATION, True)
    
    async def _save_checkpoint_request(self, request: StatePersistenceRequest, db_session):
        """Save checkpoint request to database."""
        session = await get_session_from_factory(db_session)
        state = self._convert_request_to_state(request)
        success = await self._persist_state_data(request, state, session)
        return success, request.run_id
    
    def _convert_request_to_state(self, request: StatePersistenceRequest):
        """Convert StatePersistenceRequest to DeepAgentState."""
        from netra_backend.app.agents.state import DeepAgentState
        return DeepAgentState(**request.state_data)
    
    async def _persist_state_data(self, request: StatePersistenceRequest, 
                                state, session):
        """Persist state data to database."""
        result = await self.state_persistence.save_agent_state(
            request, session)
        # Handle both tuple and single value returns (for test compatibility)
        if isinstance(result, tuple) and len(result) >= 2:
            success, snapshot_id = result[0], result[1]
        elif isinstance(result, tuple) and len(result) == 1:
            success = result[0]
        else:
            success = bool(result) if result is not None else False
        return success
    
    def _handle_checkpoint_save_result(self, success: bool, checkpoint_id: str) -> None:
        """Handle checkpoint save result."""
        if success:
            self._update_checkpoint_tracking(checkpoint_id)
    
    def _update_checkpoint_tracking(self, checkpoint_id: str) -> None:
        """Update checkpoint tracking state."""
        self.current_checkpoint_id = checkpoint_id
        self.last_checkpoint_time = datetime.now(timezone.utc)
        logger.info(f"Created initial checkpoint {checkpoint_id}")
    
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
        request = self._build_checkpoint_request(
            state, run_id, thread_id, user_id, checkpoint_type, agent_phase)
        return await self._execute_checkpoint_save(request, run_id, db_session)
    
    def _build_checkpoint_request(self, state: DeepAgentState, run_id: str,
                                 thread_id: str, user_id: str,
                                 checkpoint_type: CheckpointType,
                                 agent_phase: Optional[AgentPhase]) -> StatePersistenceRequest:
        """Build checkpoint save request."""
        return self._create_checkpoint_request(
            state, run_id, thread_id, user_id, checkpoint_type, agent_phase)
    
    def _create_checkpoint_request(self, state: DeepAgentState, run_id: str,
                                  thread_id: str, user_id: str, checkpoint_type: CheckpointType,
                                  agent_phase: Optional[AgentPhase], is_recovery_point: bool = None) -> StatePersistenceRequest:
        """Create checkpoint request with parameters."""
        params = self._combine_checkpoint_params(run_id, thread_id, user_id, state, checkpoint_type, agent_phase, is_recovery_point)
        return StatePersistenceRequest(**params)
    
    def _combine_checkpoint_params(self, run_id: str, thread_id: str, user_id: str,
                                  state: DeepAgentState, checkpoint_type: CheckpointType,
                                  agent_phase: Optional[AgentPhase], is_recovery_point: bool = None) -> dict:
        """Combine all checkpoint parameters."""
        base_params = self._build_checkpoint_base_params(run_id, thread_id, user_id)
        state_params = self._build_checkpoint_state_params(state, checkpoint_type, agent_phase, is_recovery_point)
        return {**base_params, **state_params}
    
    def _build_checkpoint_base_params(self, run_id: str, thread_id: str, user_id: str) -> dict:
        """Build base checkpoint parameters."""
        return {
            "run_id": run_id,
            "thread_id": thread_id,
            "user_id": user_id
        }
    
    def _build_checkpoint_state_params(self, state: DeepAgentState, checkpoint_type: CheckpointType,
                                      agent_phase: Optional[AgentPhase], is_recovery_point: bool = None) -> dict:
        """Build checkpoint state parameters."""
        recovery_point = self._determine_recovery_point(checkpoint_type, is_recovery_point)
        state_dict = self._create_state_dict(state)
        return self._combine_state_checkpoint_params(state_dict, checkpoint_type, agent_phase, recovery_point)
    
    def _create_state_dict(self, state: DeepAgentState) -> dict:
        """Create state dictionary."""
        return {
            "state_data": state.model_dump(),
            "execution_context": {"step_count": state.step_count}
        }
    
    def _combine_state_checkpoint_params(self, state_dict: dict, checkpoint_type: CheckpointType,
                                        agent_phase: Optional[AgentPhase], recovery_point: bool) -> dict:
        """Combine state checkpoint parameters."""
        checkpoint_params = self._get_checkpoint_params(checkpoint_type, agent_phase, recovery_point)
        return {**state_dict, **checkpoint_params}
    
    def _get_checkpoint_params(self, checkpoint_type: CheckpointType,
                              agent_phase: Optional[AgentPhase], recovery_point: bool) -> dict:
        """Get checkpoint-specific parameters."""
        return {
            "checkpoint_type": checkpoint_type,
            "agent_phase": agent_phase,
            "is_recovery_point": recovery_point
        }
    
    def _determine_recovery_point(self, checkpoint_type: CheckpointType, 
                                 explicit_value: bool = None) -> bool:
        """Determine if checkpoint is a recovery point."""
        if explicit_value is not None:
            return explicit_value
        return checkpoint_type == CheckpointType.PHASE_TRANSITION
    
    async def _execute_checkpoint_save(self, request: StatePersistenceRequest,
                                      run_id: str, db_session) -> bool:
        """Execute checkpoint save operation."""
        try:
            success, checkpoint_id = await self._save_checkpoint_request(request, db_session)
            if success:
                self._finalize_checkpoint_save(checkpoint_id, run_id)
            return success
        except Exception as e:
            logger.error(f"Failed to save checkpoint for run {run_id}: {e}")
            return False
    
    def _finalize_checkpoint_save(self, checkpoint_id: str, run_id: str) -> None:
        """Finalize checkpoint save operation."""
        self.current_checkpoint_id = checkpoint_id
        self.last_checkpoint_time = datetime.now(timezone.utc)
        logger.debug(f"Saved checkpoint {checkpoint_id} for run {run_id}")
    
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
        if not self._should_create_auto_checkpoint():
            return False
        return await self.save_state_checkpoint(
            state, run_id, thread_id, user_id, db_session, CheckpointType.AUTO)
    
    def _should_create_auto_checkpoint(self) -> bool:
        """Check if auto checkpoint is needed."""
        if not self.last_checkpoint_time:
            return False
        time_since_last = datetime.now(timezone.utc) - self.last_checkpoint_time
        return time_since_last.total_seconds() >= self.auto_checkpoint_interval
    
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
        return await self.save_state_checkpoint(
            state, run_id, thread_id, user_id, db_session,
            CheckpointType.PHASE_TRANSITION, phase)
