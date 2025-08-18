"""State Recovery Manager Module

Handles state recovery operations with specialized recovery strategies.
Follows 300-line limit with 8-line function limit.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.schemas.agent_state import StateRecoveryRequest, RecoveryType
from app.db.models_agent_state import AgentStateTransaction
from app.logging_config import central_logger
from app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class ServiceStateRecoveryManager:
    """Manages state recovery operations and logging."""
    
    def __init__(self):
        self.redis_manager = redis_manager
    
    async def execute_recovery_operation(self, request: StateRecoveryRequest, 
                                       recovery_id: str, db_session: AsyncSession) -> bool:
        """Execute the recovery operation workflow."""
        await self.create_recovery_log(request, recovery_id, db_session)
        success = await self.perform_recovery_by_type(request, db_session)
        await self.complete_recovery_log(recovery_id, success, db_session)
        return success
    
    async def perform_recovery_by_type(self, request: StateRecoveryRequest, 
                                     db_session: AsyncSession) -> bool:
        """Perform recovery operation based on recovery type."""
        if request.recovery_type == RecoveryType.RESTART:
            return await self.perform_restart_recovery(request, db_session)
        elif request.recovery_type == RecoveryType.RESUME:
            return await self.perform_resume_recovery(request, db_session)
        elif request.recovery_type == RecoveryType.ROLLBACK:
            return await self.perform_rollback_recovery(request, db_session)
        else:
            raise ValueError(f"Unsupported recovery type: {request.recovery_type}")
    
    async def create_recovery_log(self, request: StateRecoveryRequest, 
                                recovery_id: str, db_session: AsyncSession) -> None:
        """Create recovery log entry."""
        transaction_id = str(uuid.uuid4())
        transaction = AgentStateTransaction(
            id=transaction_id, snapshot_id=None, run_id=request.run_id,
            operation_type="recovery", triggered_by="system",
            execution_phase=f"recovery_{request.recovery_type.value}",
            status="pending", metadata_={"recovery_id": recovery_id})
        db_session.add(transaction)
        await db_session.flush()
    
    async def complete_recovery_log(self, recovery_id: str, success: bool, 
                                  db_session: AsyncSession, error_message: str = None) -> None:
        """Complete recovery log with result."""
        status = "completed" if success else "failed"
        await db_session.execute(
            update(AgentStateTransaction)
            .where(AgentStateTransaction.metadata_['recovery_id'].astext == recovery_id)
            .values(status=status, completed_at=datetime.now(timezone.utc),
                   error_message=error_message))
    
    async def perform_restart_recovery(self, request: StateRecoveryRequest, 
                                     db_session: AsyncSession) -> bool:
        """Perform restart recovery by clearing state."""
        await self.clear_cached_state(request.run_id)
        return True
    
    async def perform_resume_recovery(self, request: StateRecoveryRequest, 
                                    db_session: AsyncSession) -> bool:
        """Perform resume recovery by loading last valid state."""
        from app.services.state_persistence import state_persistence_service
        state = await state_persistence_service.load_agent_state(request.run_id, None, db_session)
        return state is not None
    
    async def perform_rollback_recovery(self, request: StateRecoveryRequest, 
                                      db_session: AsyncSession) -> bool:
        """Perform rollback recovery to specific snapshot."""
        if request.target_snapshot_id:
            from app.services.state_persistence import state_persistence_service
            state = await state_persistence_service.load_agent_state(
                request.run_id, request.target_snapshot_id, db_session)
            return state is not None
        return False
    
    async def clear_cached_state(self, run_id: str) -> None:
        """Clear cached state from Redis."""
        redis_client = await self.redis_manager.get_client()
        if redis_client:
            redis_key = f"agent_state:{run_id}"
            await redis_client.delete(redis_key)

# Global instance
state_recovery_manager = ServiceStateRecoveryManager()