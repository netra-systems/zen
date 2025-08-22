"""Recovery management functionality for supervisor state."""

from typing import Dict, Optional, Tuple

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent_state import RecoveryType, StateRecoveryRequest
from netra_backend.app.services.state_persistence import state_persistence_service

logger = central_logger.get_logger(__name__)


class AgentStateRecoveryManager:
    """Manages state recovery and rollback operations."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.state_persistence = state_persistence_service
    
    async def handle_agent_crash_recovery(self, run_id: str, thread_id: str,
                                          failure_reason: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Handle agent crash recovery scenario."""
        recovery_request = self._build_crash_recovery_request(
            run_id, thread_id, failure_reason)
        success, recovery_id = await self._execute_recovery_request(recovery_request)
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
    
    async def _execute_recovery_request(self, recovery_request: StateRecoveryRequest):
        """Execute recovery request."""
        return await self.state_persistence.recover_agent_state(
            recovery_request, self.db_session)
    
    async def _process_crash_recovery_result(self, success: bool, recovery_id: str,
                                           run_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Process crash recovery result."""
        if success:
            return await self._handle_successful_recovery(recovery_id, run_id)
        return self._handle_failed_recovery(run_id)
    
    async def _handle_successful_recovery(self, recovery_id: str, 
                                        run_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Handle successful crash recovery."""
        recovered_state = await self.state_persistence.load_agent_state(
            run_id, self.db_session)
        logger.info(f"Crash recovery {recovery_id} completed for run {run_id}")
        return True, recovered_state
    
    def _handle_failed_recovery(self, run_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Handle failed crash recovery."""
        logger.error(f"Crash recovery failed for run {run_id}")
        return False, None
    
    async def rollback_to_checkpoint(self, run_id: str, thread_id: str,
                                    checkpoint_id: str) -> Tuple[bool, Optional[DeepAgentState]]:
        """Rollback to a specific checkpoint."""
        recovery_request = self._build_rollback_recovery_request(
            run_id, thread_id, checkpoint_id)
        success, recovery_id = await self._execute_recovery_request(recovery_request)
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
                run_id, self.db_session)
            return True, recovered_state
        return False, None
    
    async def attempt_state_recovery(self, run_id: str, 
                                    thread_id: str) -> Optional[DeepAgentState]:
        """Attempt to recover agent state from previous run."""
        try:
            return await self._recover_and_validate_state(run_id)
        except Exception as e:
            self._log_recovery_failure(run_id, e)
            return None
    
    async def _recover_and_validate_state(self, run_id: str) -> Optional[DeepAgentState]:
        """Recover and validate state from storage."""
        recovered_state = await self._load_previous_state(run_id)
        return self._validate_recovered_state(recovered_state, run_id)
    
    async def _load_previous_state(self, run_id: str) -> Optional[DeepAgentState]:
        """Load the most recent state."""
        session = self.db_session
        return await self.state_persistence.load_agent_state(run_id, session)
    
    def _validate_recovered_state(self, recovered_state: Optional[DeepAgentState], 
                                 run_id: str) -> Optional[DeepAgentState]:
        """Validate and log recovered state."""
        if recovered_state:
            logger.info(f"Recovered state for run {run_id}")
            return recovered_state
        return None
    
    def _log_recovery_failure(self, run_id: str, error: Exception) -> None:
        """Log state recovery failure."""
        logger.warning(f"State recovery failed for run {run_id}: {error}")
