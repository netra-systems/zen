"""State Recovery Operations Service

This module handles state recovery operations following the 8-line function limit.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.db.models_agent_state import (
    AgentStateSnapshot, AgentRecoveryLog
)
from app.schemas.agent_state import (
    StateRecoveryRequest, StatePersistenceRequest, 
    CheckpointType, RecoveryType
)
from app.redis_manager import redis_manager
from app.logging_config import central_logger
from app.services.state_serialization import DateTimeEncoder

logger = central_logger.get_logger(__name__)


class StateRecoveryService:
    """Handles state recovery operations."""
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.redis_ttl = 3600  # 1 hour TTL for Redis cache
    
    async def perform_recovery(self, request: StateRecoveryRequest, 
                              db_session: AsyncSession,
                              get_latest_snapshot_func,
                              save_agent_state_func) -> bool:
        """Perform recovery operation based on recovery type."""
        if request.recovery_type == RecoveryType.RESTART:
            return await self._perform_restart_recovery(request, db_session)
        elif request.recovery_type == RecoveryType.RESUME:
            return await self._perform_resume_recovery(request, db_session, get_latest_snapshot_func)
        elif request.recovery_type == RecoveryType.ROLLBACK:
            return await self._perform_rollback_recovery(
                request, db_session, get_latest_snapshot_func, save_agent_state_func)
        else:
            raise ValueError(f"Unsupported recovery type: {request.recovery_type}")
    
    async def create_recovery_log(self, request: StateRecoveryRequest, recovery_id: str,
                                 db_session: AsyncSession) -> AgentRecoveryLog:
        """Create recovery log entry."""
        recovery_type_value = self._extract_recovery_type_value(request.recovery_type)
        recovery_log = AgentRecoveryLog(
            id=recovery_id, run_id=request.run_id, thread_id=request.thread_id,
            recovery_type=recovery_type_value, target_snapshot_id=request.target_snapshot_id,
            failure_reason=request.failure_reason, trigger_event="recovery_request",
            auto_recovery=request.auto_recovery, recovery_status="initiated")
        db_session.add(recovery_log)
        await db_session.flush()
        return recovery_log
    
    async def complete_recovery_log(self, recovery_id: str, success: bool,
                                   db_session: AsyncSession, error_message: Optional[str] = None) -> None:
        """Complete recovery log with final status."""
        status = "completed" if success else "failed"
        await db_session.execute(
            update(AgentRecoveryLog)
            .where(AgentRecoveryLog.id == recovery_id)
            .values(recovery_status=status, completed_at=datetime.now(timezone.utc),
                   error_message=error_message))
    
    async def _perform_restart_recovery(self, request: StateRecoveryRequest,
                                       db_session: AsyncSession) -> bool:
        """Perform restart recovery - clear current state."""
        try:
            await self._clear_redis_cache_for_restart(request)
            await self._mark_snapshots_obsolete(request, db_session)
            return True
        except Exception as e:
            logger.error(f"Restart recovery failed: {e}")
            return False
    
    async def _perform_resume_recovery(self, request: StateRecoveryRequest,
                                      db_session: AsyncSession,
                                      get_latest_snapshot_func) -> bool:
        """Perform resume recovery - restore from checkpoint."""
        try:
            snapshot = await self._get_recovery_snapshot(request, db_session, get_latest_snapshot_func)
            if not snapshot:
                return False
            await self._cache_recovered_state(request, snapshot)
            return True
        except Exception as e:
            logger.error(f"Resume recovery failed: {e}")
            return False
    
    async def _perform_rollback_recovery(self, request: StateRecoveryRequest,
                                        db_session: AsyncSession,
                                        get_latest_snapshot_func,
                                        save_agent_state_func) -> bool:
        """Perform rollback recovery - revert to previous state."""
        try:
            if not request.target_snapshot_id:
                return False
            target_snapshot = await get_latest_snapshot_func(
                request.run_id, request.target_snapshot_id, db_session)
            if not target_snapshot:
                return False
            rollback_request = self._create_rollback_request(request, target_snapshot)
            success, _ = await save_agent_state_func(rollback_request, db_session)
            return success
        except Exception as e:
            logger.error(f"Rollback recovery failed: {e}")
            return False
    
    def _extract_recovery_type_value(self, recovery_type) -> str:
        """Extract recovery type value."""
        if hasattr(recovery_type, 'value'):
            return recovery_type.value
        return recovery_type
    
    async def _clear_redis_cache_for_restart(self, request: StateRecoveryRequest) -> None:
        """Clear Redis cache for restart recovery."""
        redis_client = await self.redis_manager.get_client()
        if redis_client:
            await redis_client.delete(f"agent_state:{request.run_id}")
            await redis_client.delete(f"thread_context:{request.thread_id}")
    
    async def _mark_snapshots_obsolete(self, request: StateRecoveryRequest, 
                                      db_session: AsyncSession) -> None:
        """Mark current snapshots as obsolete for audit trail."""
        await db_session.execute(
            update(AgentStateSnapshot)
            .where(AgentStateSnapshot.run_id == request.run_id)
            .values(recovery_reason="restart_recovery"))
    
    async def _get_recovery_snapshot(self, request: StateRecoveryRequest, 
                                   db_session: AsyncSession,
                                   get_latest_snapshot_func) -> Optional[AgentStateSnapshot]:
        """Get snapshot for recovery operation."""
        if request.target_snapshot_id:
            return await get_latest_snapshot_func(
                request.run_id, request.target_snapshot_id, db_session)
        return await get_latest_snapshot_func(request.run_id, None, db_session)
    
    async def _cache_recovered_state(self, request: StateRecoveryRequest, 
                                   snapshot: AgentStateSnapshot) -> None:
        """Cache recovered state in Redis."""
        redis_client = await self.redis_manager.get_client()
        if redis_client:
            state_json = json.dumps(snapshot.state_data, cls=DateTimeEncoder)
            await redis_client.set(
                f"agent_state:{request.run_id}", state_json, ex=self.redis_ttl)
    
    def _create_rollback_request(self, request: StateRecoveryRequest, 
                               target_snapshot: AgentStateSnapshot) -> StatePersistenceRequest:
        """Create rollback request from target snapshot."""
        return StatePersistenceRequest(
            run_id=request.run_id, thread_id=request.thread_id,
            user_id=target_snapshot.user_id, state_data=target_snapshot.state_data,
            checkpoint_type=CheckpointType.RECOVERY, is_recovery_point=True)


# Global instance
state_recovery_service = StateRecoveryService()