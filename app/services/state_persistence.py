"""Enhanced Agent State Persistence Service

This service provides atomic state persistence with versioning,
compression, and recovery capabilities following the 8-line function limit.
"""

import json
import time
import gzip
import pickle
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from sqlalchemy.exc import SQLAlchemyError
from app.db.models_postgres import Run, Reference
from app.db.models_agent_state import (
    AgentStateSnapshot, AgentStateTransaction, AgentRecoveryLog
)
from app.schemas.agent_state import (
    StatePersistenceRequest, StateRecoveryRequest, StateSnapshot,
    StateTransaction, RecoveryOperation, CheckpointType, RecoveryType,
    SerializationFormat, StateValidationResult, StateMergeResult
)
from app.redis_manager import redis_manager
from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.core.exceptions import NetraException

logger = central_logger.get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder for datetime objects."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class StateSerializer:
    """Handles state serialization with compression."""
    
    def serialize(self, state_data: Dict[str, Any], 
                 format_type: SerializationFormat) -> bytes:
        """Serialize state data in specified format."""
        if format_type == SerializationFormat.JSON:
            return json.dumps(state_data, cls=DateTimeEncoder).encode('utf-8')
        elif format_type == SerializationFormat.PICKLE:
            return pickle.dumps(state_data)
        elif format_type == SerializationFormat.COMPRESSED_JSON:
            return self._compress_json(state_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def deserialize(self, serialized_data: bytes, 
                   format_type: SerializationFormat) -> Dict[str, Any]:
        """Deserialize state data from specified format."""
        if format_type == SerializationFormat.JSON:
            return json.loads(serialized_data.decode('utf-8'))
        elif format_type == SerializationFormat.PICKLE:
            return pickle.loads(serialized_data)
        elif format_type == SerializationFormat.COMPRESSED_JSON:
            return self._decompress_json(serialized_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _compress_json(self, state_data: Dict[str, Any]) -> bytes:
        """Compress JSON data using gzip."""
        json_data = json.dumps(state_data, cls=DateTimeEncoder).encode('utf-8')
        return gzip.compress(json_data)
    
    def _decompress_json(self, compressed_data: bytes) -> Dict[str, Any]:
        """Decompress gzipped JSON data."""
        json_data = gzip.decompress(compressed_data).decode('utf-8')
        return json.loads(json_data)


class StateValidator:
    """Validates agent state integrity."""
    
    def validate_state(self, state_data: Dict[str, Any]) -> StateValidationResult:
        """Validate state data integrity."""
        errors = []
        warnings = []
        missing_fields = []
        corrupted_fields = []
        
        self._check_required_fields(state_data, missing_fields)
        self._check_data_integrity(state_data, corrupted_fields)
        self._check_field_types(state_data, errors)
        
        is_valid = len(errors) == 0 and len(corrupted_fields) == 0
        validation_score = self._calculate_validation_score(
            errors, warnings, missing_fields, corrupted_fields)
        
        return StateValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            corrupted_fields=corrupted_fields,
            validation_score=validation_score
        )
    
    def _check_required_fields(self, state_data: Dict[str, Any], 
                              missing_fields: List[str]) -> None:
        """Check for required fields in state data."""
        required_fields = ['user_request', 'step_count', 'metadata']
        for field in required_fields:
            if field not in state_data:
                missing_fields.append(field)
    
    def _check_data_integrity(self, state_data: Dict[str, Any], 
                             corrupted_fields: List[str]) -> None:
        """Check data integrity of state fields."""
        try:
            if 'step_count' in state_data and not isinstance(state_data['step_count'], int):
                corrupted_fields.append('step_count')
            if 'metadata' in state_data and not isinstance(state_data['metadata'], dict):
                corrupted_fields.append('metadata')
        except Exception:
            corrupted_fields.append('general_corruption')
    
    def _check_field_types(self, state_data: Dict[str, Any], 
                          errors: List[str]) -> None:
        """Check field type consistency."""
        if 'step_count' in state_data:
            if not isinstance(state_data['step_count'], int) or state_data['step_count'] < 0:
                errors.append('Invalid step_count: must be non-negative integer')
    
    def _calculate_validation_score(self, errors: List[str], warnings: List[str],
                                   missing_fields: List[str], 
                                   corrupted_fields: List[str]) -> float:
        """Calculate validation score (0.0 to 1.0)."""
        total_issues = len(errors) + len(warnings) + len(missing_fields) + len(corrupted_fields)
        if total_issues == 0:
            return 1.0
        # Weighted scoring: errors=0.4, corrupted=0.3, missing=0.2, warnings=0.1
        score = 1.0 - (len(errors) * 0.4 + len(corrupted_fields) * 0.3 + 
                      len(missing_fields) * 0.2 + len(warnings) * 0.1) / 10
        return max(0.0, min(1.0, score))


class StatePersistenceService:
    """Enhanced service for atomic agent state persistence and recovery."""
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.redis_ttl = 3600  # 1 hour TTL for Redis cache
        self.compression_threshold = 1024  # Compress if > 1KB
        self.max_snapshots_per_run = 50
        self.default_retention_days = 7
        self.serializer = StateSerializer()
        self.validator = StateValidator()
    
    async def save_agent_state(self, request: StatePersistenceRequest,
                              db_session: AsyncSession) -> Tuple[bool, Optional[str]]:
        """Save agent state with atomic transactions and versioning."""
        snapshot_id = None
        transaction_id = None
        
        try:
            # Start transaction
            async with db_session.begin():
                snapshot_id = await self._create_state_snapshot(request, db_session)
                transaction_id = await self._log_state_transaction(
                    snapshot_id, request, "create", db_session)
                
                # Cache in Redis
                await self._cache_state_in_redis(request)
                
                # Clean up old snapshots
                await self._cleanup_old_snapshots(request.run_id, db_session)
                
                await self._complete_transaction(transaction_id, "committed", db_session)
                
            logger.info(f"Saved state snapshot {snapshot_id} for run {request.run_id}")
            return True, snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to save state for run {request.run_id}: {e}")
            if transaction_id:
                await self._complete_transaction(transaction_id, "failed", db_session, str(e))
            return False, None
    
    async def load_agent_state(self, run_id: str, snapshot_id: Optional[str] = None,
                              db_session: Optional[AsyncSession] = None) -> Optional[DeepAgentState]:
        """Load agent state with recovery support."""
        try:
            # Try Redis cache first
            if not snapshot_id:
                state = await self._load_from_redis_cache(run_id)
                if state:
                    return state
            
            # Load from database snapshots
            if db_session:
                snapshot = await self._get_latest_snapshot(run_id, snapshot_id, db_session)
                if snapshot:
                    state_data = await self._deserialize_state_data(
                        snapshot.state_data, snapshot.serialization_format)
                    
                    # Re-cache in Redis
                    await self._cache_deserialized_state(run_id, state_data)
                    
                    logger.info(f"Loaded state from snapshot {snapshot.id}")
                    return DeepAgentState(**state_data)
            
            logger.warning(f"No state found for run {run_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load state for run {run_id}: {e}")
            return None
    
    async def recover_agent_state(self, request: StateRecoveryRequest,
                                 db_session: AsyncSession) -> Tuple[bool, Optional[str]]:
        """Recover agent state from a specific checkpoint."""
        recovery_id = str(uuid.uuid4())
        
        try:
            # Create recovery log
            recovery_log = await self._create_recovery_log(request, recovery_id, db_session)
            
            # Perform recovery based on type
            if request.recovery_type == RecoveryType.RESTART:
                success = await self._perform_restart_recovery(request, db_session)
            elif request.recovery_type == RecoveryType.RESUME:
                success = await self._perform_resume_recovery(request, db_session)
            elif request.recovery_type == RecoveryType.ROLLBACK:
                success = await self._perform_rollback_recovery(request, db_session)
            else:
                raise ValueError(f"Unsupported recovery type: {request.recovery_type}")
            
            # Update recovery log
            await self._complete_recovery_log(recovery_id, success, db_session)
            
            logger.info(f"Recovery {recovery_id} {'completed' if success else 'failed'}")
            return success, recovery_id if success else None
            
        except Exception as e:
            logger.error(f"Recovery failed for run {request.run_id}: {e}")
            await self._complete_recovery_log(recovery_id, False, db_session, str(e))
            return False, None
    
    async def _create_state_snapshot(self, request: StatePersistenceRequest,
                                    db_session: AsyncSession) -> str:
        """Create a new state snapshot in database."""
        snapshot_id = str(uuid.uuid4())
        
        # Validate state data
        validation_result = self.validator.validate_state(request.state_data)
        if not validation_result.is_valid:
            raise NetraException(f"Invalid state data: {validation_result.errors}")
        
        # Determine serialization format
        serialization_format = self._choose_serialization_format(request.state_data)
        
        # Serialize datetime objects to ISO format strings for JSON storage
        json_safe_data = json.loads(json.dumps(request.state_data, cls=DateTimeEncoder))
        
        # Create snapshot record
        snapshot = AgentStateSnapshot(
            id=snapshot_id,
            run_id=request.run_id,
            thread_id=request.thread_id,
            user_id=request.user_id,
            state_data=json_safe_data,  # Store JSON-safe data in database
            serialization_format=serialization_format.value if hasattr(serialization_format, 'value') else serialization_format,
            checkpoint_type=request.checkpoint_type.value if hasattr(request.checkpoint_type, 'value') else request.checkpoint_type,
            agent_phase=request.agent_phase.value if request.agent_phase and hasattr(request.agent_phase, 'value') else request.agent_phase,
            execution_context=request.execution_context,
            is_recovery_point=request.is_recovery_point,
            expires_at=request.expires_at or self._calculate_expiry_date()
        )
        
        db_session.add(snapshot)
        await db_session.flush()
        
        return snapshot_id
    
    async def _log_state_transaction(self, snapshot_id: str, request: StatePersistenceRequest,
                                    operation_type: str, db_session: AsyncSession) -> str:
        """Log state transaction for audit trail."""
        transaction_id = str(uuid.uuid4())
        
        transaction = AgentStateTransaction(
            id=transaction_id,
            snapshot_id=snapshot_id,
            run_id=request.run_id,
            operation_type=operation_type,
            triggered_by="system",
            execution_phase=request.agent_phase.value if request.agent_phase and hasattr(request.agent_phase, 'value') else request.agent_phase,
            status="pending"
        )
        
        db_session.add(transaction)
        await db_session.flush()
        
        return transaction_id
    
    async def _cache_state_in_redis(self, request: StatePersistenceRequest) -> None:
        """Cache state data in Redis for fast access."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return
        
        redis_key = f"agent_state:{request.run_id}"
        state_json = json.dumps(request.state_data, cls=DateTimeEncoder)
        
        await redis_client.set(redis_key, state_json, ex=self.redis_ttl)
        
        # Also cache thread context
        thread_key = f"thread_context:{request.thread_id}"
        thread_context = {
            "current_run_id": request.run_id,
            "user_id": request.user_id,
            "last_updated": time.time(),
            "checkpoint_type": request.checkpoint_type.value if hasattr(request.checkpoint_type, 'value') else request.checkpoint_type
        }
        await redis_client.set(thread_key, json.dumps(thread_context), ex=self.redis_ttl * 24)
    
    async def _cleanup_old_snapshots(self, run_id: str, db_session: AsyncSession) -> None:
        """Clean up old snapshots to maintain performance."""
        # Keep only the latest N snapshots per run
        result = await db_session.execute(
            select(AgentStateSnapshot.id)
            .where(AgentStateSnapshot.run_id == run_id)
            .order_by(desc(AgentStateSnapshot.created_at))
            .offset(self.max_snapshots_per_run)
        )
        old_snapshot_ids = [row[0] for row in result.fetchall()]
        
        if old_snapshot_ids:
            # Delete old snapshots and their transactions
            await self._delete_snapshots_batch(old_snapshot_ids, db_session)
    
    async def _delete_snapshots_batch(self, snapshot_ids: List[str], 
                                     db_session: AsyncSession) -> None:
        """Delete snapshots and related data in batch."""
        # Delete transactions first (foreign key constraint)
        await db_session.execute(
            AgentStateTransaction.__table__.delete()
            .where(AgentStateTransaction.snapshot_id.in_(snapshot_ids))
        )
        
        # Delete snapshots
        await db_session.execute(
            AgentStateSnapshot.__table__.delete()
            .where(AgentStateSnapshot.id.in_(snapshot_ids))
        )
    
    async def _complete_transaction(self, transaction_id: str, status: str,
                                   db_session: AsyncSession, error_message: Optional[str] = None) -> None:
        """Complete a state transaction with final status."""
        await db_session.execute(
            update(AgentStateTransaction)
            .where(AgentStateTransaction.id == transaction_id)
            .values(
                status=status,
                completed_at=datetime.now(timezone.utc),
                error_message=error_message
            )
        )
    
    def _choose_serialization_format(self, state_data: Dict[str, Any]) -> SerializationFormat:
        """Choose optimal serialization format based on data size."""
        estimated_size = len(json.dumps(state_data, cls=DateTimeEncoder))
        
        if estimated_size > self.compression_threshold:
            return SerializationFormat.COMPRESSED_JSON
        else:
            return SerializationFormat.JSON
    
    def _calculate_expiry_date(self) -> datetime:
        """Calculate default expiry date for snapshots."""
        return datetime.now(timezone.utc) + timedelta(days=self.default_retention_days)
    
    async def _load_from_redis_cache(self, run_id: str) -> Optional[DeepAgentState]:
        """Load state from Redis cache."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return None
        
        redis_key = f"agent_state:{run_id}"
        state_json = await redis_client.get(redis_key)
        
        if state_json:
            state_dict = json.loads(state_json)
            logger.info(f"Loaded state for run {run_id} from Redis cache")
            return DeepAgentState(**state_dict)
        
        return None
    
    async def _get_latest_snapshot(self, run_id: str, snapshot_id: Optional[str],
                                  db_session: AsyncSession) -> Optional[AgentStateSnapshot]:
        """Get the latest or specific snapshot for a run."""
        if snapshot_id:
            result = await db_session.execute(
                select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id)
            )
        else:
            result = await db_session.execute(
                select(AgentStateSnapshot)
                .where(AgentStateSnapshot.run_id == run_id)
                .order_by(desc(AgentStateSnapshot.created_at))
                .limit(1)
            )
        
        return result.scalar_one_or_none()
    
    async def _deserialize_state_data(self, state_data: Dict[str, Any], 
                                     serialization_format: str) -> Dict[str, Any]:
        """Deserialize state data from database format."""
        # For now, state_data is already stored as JSON in database
        # In future, could support other formats stored as BLOB
        return state_data
    
    async def _cache_deserialized_state(self, run_id: str, state_data: Dict[str, Any]) -> None:
        """Cache deserialized state in Redis."""
        redis_client = await self.redis_manager.get_client()
        if not redis_client:
            return
        
        redis_key = f"agent_state:{run_id}"
        state_json = json.dumps(state_data, cls=DateTimeEncoder)
        await redis_client.set(redis_key, state_json, ex=self.redis_ttl)
    
    async def _create_recovery_log(self, request: StateRecoveryRequest, recovery_id: str,
                                  db_session: AsyncSession) -> AgentRecoveryLog:
        """Create recovery log entry."""
        recovery_log = AgentRecoveryLog(
            id=recovery_id,
            run_id=request.run_id,
            thread_id=request.thread_id,
            recovery_type=request.recovery_type.value if hasattr(request.recovery_type, 'value') else request.recovery_type,
            target_snapshot_id=request.target_snapshot_id,
            failure_reason=request.failure_reason,
            trigger_event="recovery_request",
            auto_recovery=request.auto_recovery,
            recovery_status="initiated"
        )
        
        db_session.add(recovery_log)
        await db_session.flush()
        
        return recovery_log
    
    async def _perform_restart_recovery(self, request: StateRecoveryRequest,
                                       db_session: AsyncSession) -> bool:
        """Perform restart recovery - clear current state."""
        try:
            # Clear Redis cache
            redis_client = await self.redis_manager.get_client()
            if redis_client:
                await redis_client.delete(f"agent_state:{request.run_id}")
                await redis_client.delete(f"thread_context:{request.thread_id}")
            
            # Mark current snapshots as obsolete (don't delete for audit)
            await db_session.execute(
                update(AgentStateSnapshot)
                .where(AgentStateSnapshot.run_id == request.run_id)
                .values(recovery_reason="restart_recovery")
            )
            
            return True
        except Exception as e:
            logger.error(f"Restart recovery failed: {e}")
            return False
    
    async def _perform_resume_recovery(self, request: StateRecoveryRequest,
                                      db_session: AsyncSession) -> bool:
        """Perform resume recovery - restore from checkpoint."""
        try:
            if request.target_snapshot_id:
                snapshot = await self._get_latest_snapshot(
                    request.run_id, request.target_snapshot_id, db_session)
            else:
                snapshot = await self._get_latest_snapshot(
                    request.run_id, None, db_session)
            
            if not snapshot:
                return False
            
            # Cache the restored state in Redis
            redis_client = await self.redis_manager.get_client()
            if redis_client:
                state_json = json.dumps(snapshot.state_data, cls=DateTimeEncoder)
                await redis_client.set(
                    f"agent_state:{request.run_id}", state_json, ex=self.redis_ttl)
            
            return True
        except Exception as e:
            logger.error(f"Resume recovery failed: {e}")
            return False
    
    async def _perform_rollback_recovery(self, request: StateRecoveryRequest,
                                        db_session: AsyncSession) -> bool:
        """Perform rollback recovery - revert to previous state."""
        try:
            if not request.target_snapshot_id:
                return False
            
            # Get target snapshot
            target_snapshot = await self._get_latest_snapshot(
                request.run_id, request.target_snapshot_id, db_session)
            
            if not target_snapshot:
                return False
            
            # Create new snapshot based on rollback target
            rollback_request = StatePersistenceRequest(
                run_id=request.run_id,
                thread_id=request.thread_id,
                user_id=target_snapshot.user_id,
                state_data=target_snapshot.state_data,
                checkpoint_type=CheckpointType.RECOVERY,
                is_recovery_point=True
            )
            
            success, _ = await self.save_agent_state(rollback_request, db_session)
            return success
            
        except Exception as e:
            logger.error(f"Rollback recovery failed: {e}")
            return False
    
    async def _complete_recovery_log(self, recovery_id: str, success: bool,
                                    db_session: AsyncSession, error_message: Optional[str] = None) -> None:
        """Complete recovery log with final status."""
        status = "completed" if success else "failed"
        
        await db_session.execute(
            update(AgentRecoveryLog)
            .where(AgentRecoveryLog.id == recovery_id)
            .values(
                recovery_status=status,
                completed_at=datetime.now(timezone.utc),
                error_message=error_message
            )
        )


# Global instance
state_persistence_service = StatePersistenceService()