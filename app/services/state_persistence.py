"""Enhanced Agent State Persistence Service

This service provides atomic state persistence with versioning,
compression, and recovery capabilities following the 8-line function limit.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from app.db.models_agent_state import (
    AgentStateSnapshot, AgentStateTransaction
)
from app.schemas.agent_state import (
    StatePersistenceRequest, StateRecoveryRequest,
    CheckpointType, SerializationFormat, RecoveryType
)
from app.redis_manager import redis_manager
from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.core.exceptions import NetraException
from app.services.state_serialization import (
    DateTimeEncoder, StateSerializer, StateValidator
)
from app.services.state_recovery_manager import state_recovery_manager
from app.services.state_cache_manager import state_cache_manager

logger = central_logger.get_logger(__name__)


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
    
    async def save_agent_state(self, *args, **kwargs) -> Tuple[bool, Optional[str]]:
        """Save agent state with atomic transactions and versioning."""
        # Handle both calling patterns for backward compatibility
        if len(args) == 2 and isinstance(args[0], StatePersistenceRequest):
            # New pattern: save_agent_state(request, db_session)
            request, db_session = args
        elif 'run_id' in kwargs and 'db_session' in kwargs:
            # Legacy pattern: save_agent_state(run_id=..., thread_id=..., user_id=..., state=..., db_session=...)
            request = self._build_persistence_request_from_kwargs(kwargs)
            db_session = kwargs['db_session']
        else:
            raise ValueError("Invalid arguments for save_agent_state")
        
        try:
            snapshot_id = await self._execute_state_save_transaction(request, db_session)
            logger.info(f"Saved state snapshot {snapshot_id} for run {request.run_id}")
            return True, snapshot_id
        except Exception as e:
            logger.error(f"Failed to save state for run {request.run_id}: {e}")
            return False, None

    async def _execute_state_save_transaction(self, request: StatePersistenceRequest, db_session: AsyncSession) -> str:
        """Execute the complete state save transaction."""
        snapshot_id = None
        transaction_id = None
        async with db_session.begin():
            snapshot_id, transaction_id = await self._create_snapshot_and_transaction(request, db_session)
            await self._finalize_state_save(request, transaction_id, db_session)
        return snapshot_id

    async def _create_snapshot_and_transaction(self, request: StatePersistenceRequest, db_session: AsyncSession) -> Tuple[str, str]:
        """Create snapshot and transaction records."""
        snapshot_id = await self._create_state_snapshot(request, db_session)
        transaction_id = await self._log_state_transaction(
            snapshot_id, request, "create", db_session
        )
        return snapshot_id, transaction_id

    async def _finalize_state_save(self, request: StatePersistenceRequest, transaction_id: str, db_session: AsyncSession) -> None:
        """Complete state save with caching and cleanup."""
        await state_cache_manager.cache_state_in_redis(request)
        await self._cleanup_old_snapshots(request.run_id, db_session)
        await self._complete_transaction(transaction_id, "committed", db_session)
    
    async def load_agent_state(self, run_id: str, snapshot_id: Optional[str] = None,
                              db_session: Optional[AsyncSession] = None) -> Optional[DeepAgentState]:
        """Load agent state with recovery support."""
        try:
            state = await self._attempt_cache_load(run_id, snapshot_id)
            if state:
                return state
            return await self._attempt_database_load(run_id, snapshot_id, db_session)
        except Exception as e:
            logger.error(f"Failed to load state for run {run_id}: {e}")
            return None

    async def _attempt_cache_load(self, run_id: str, snapshot_id: Optional[str]) -> Optional[DeepAgentState]:
        """Try loading state from Redis cache first."""
        if not snapshot_id:
            return await state_cache_manager.load_from_redis_cache(run_id)
        return None

    async def _attempt_database_load(self, run_id: str, snapshot_id: Optional[str], db_session: Optional[AsyncSession]) -> Optional[DeepAgentState]:
        """Load state from database snapshots."""
        if not db_session:
            logger.warning(f"No state found for run {run_id}")
            return None
        snapshot = await self._get_latest_snapshot(run_id, snapshot_id, db_session)
        if not snapshot:
            logger.warning(f"No state found for run {run_id}")
            return None
        return await self._process_database_snapshot(run_id, snapshot)

    async def _process_database_snapshot(self, run_id: str, snapshot) -> DeepAgentState:
        """Process database snapshot and return state."""
        state_data = await self._deserialize_state_data(
            snapshot.state_data, snapshot.serialization_format
        )
        await state_cache_manager.cache_deserialized_state(run_id, state_data)
        logger.info(f"Loaded state from snapshot {snapshot.id}")
        return DeepAgentState(**state_data)
    
    async def recover_agent_state(self, request: StateRecoveryRequest,
                                 db_session: AsyncSession) -> Tuple[bool, Optional[str]]:
        """Recover agent state from a specific checkpoint."""
        recovery_id = str(uuid.uuid4())
        try:
            success = await self._execute_recovery_operation(request, recovery_id, db_session)
            logger.info(f"Recovery {recovery_id} {'completed' if success else 'failed'}")
            return success, recovery_id if success else None
        except Exception as e:
            logger.error(f"Recovery failed for run {request.run_id}: {e}")
            await state_recovery_manager.complete_recovery_log(recovery_id, False, db_session, str(e))
            return False, None

    async def _execute_recovery_operation(self, request: StateRecoveryRequest, recovery_id: str, db_session: AsyncSession) -> bool:
        """Execute the recovery operation workflow."""
        return await state_recovery_manager.execute_recovery_operation(request, recovery_id, db_session)
    
    async def _create_state_snapshot(self, request: StatePersistenceRequest,
                                    db_session: AsyncSession) -> str:
        """Create a new state snapshot in database."""
        snapshot_id = str(uuid.uuid4())
        self._validate_request_state(request)
        serialization_format = self._choose_serialization_format(request.state_data)
        json_safe_data = self._prepare_json_safe_data(request.state_data)
        snapshot = self._build_snapshot_record(snapshot_id, request, serialization_format, json_safe_data)
        db_session.add(snapshot)
        await db_session.flush()
        return snapshot_id
    
    async def _log_state_transaction(self, snapshot_id: str, request: StatePersistenceRequest,
                                    operation_type: str, db_session: AsyncSession) -> str:
        """Log state transaction for audit trail."""
        transaction_id = str(uuid.uuid4())
        execution_phase = self._extract_value(request.agent_phase) if request.agent_phase else None
        transaction = AgentStateTransaction(
            id=transaction_id, snapshot_id=snapshot_id, run_id=request.run_id,
            operation_type=operation_type, triggered_by="system",
            execution_phase=execution_phase, status="pending")
        db_session.add(transaction)
        await db_session.flush()
        return transaction_id
    
    async def _cleanup_old_snapshots(self, run_id: str, db_session: AsyncSession) -> None:
        """Clean up old snapshots to maintain performance."""
        result = await db_session.execute(
            select(AgentStateSnapshot.id)
            .where(AgentStateSnapshot.run_id == run_id)
            .order_by(desc(AgentStateSnapshot.created_at))
            .offset(self.max_snapshots_per_run))
        old_snapshot_ids = [row[0] for row in result.fetchall()]
        if old_snapshot_ids:
            await self._delete_snapshots_batch(old_snapshot_ids, db_session)
    
    async def _delete_snapshots_batch(self, snapshot_ids: List[str], 
                                     db_session: AsyncSession) -> None:
        """Delete snapshots and related data in batch."""
        await db_session.execute(
            AgentStateTransaction.__table__.delete()
            .where(AgentStateTransaction.snapshot_id.in_(snapshot_ids)))
        await db_session.execute(
            AgentStateSnapshot.__table__.delete()
            .where(AgentStateSnapshot.id.in_(snapshot_ids)))
    
    async def _complete_transaction(self, transaction_id: str, status: str,
                                   db_session: AsyncSession, error_message: Optional[str] = None) -> None:
        """Complete a state transaction with final status."""
        await db_session.execute(
            update(AgentStateTransaction)
            .where(AgentStateTransaction.id == transaction_id)
            .values(status=status, completed_at=datetime.now(timezone.utc),
                   error_message=error_message))
    
    def _choose_serialization_format(self, state_data: Dict[str, Any]) -> SerializationFormat:
        """Choose optimal serialization format based on data size."""
        estimated_size = len(json.dumps(state_data, cls=DateTimeEncoder))
        return SerializationFormat.COMPRESSED_JSON if estimated_size > self.compression_threshold else SerializationFormat.JSON
    
    def _calculate_expiry_date(self) -> datetime:
        """Calculate default expiry date for snapshots."""
        return datetime.now(timezone.utc) + timedelta(days=self.default_retention_days)
    
    def _validate_request_state(self, request: StatePersistenceRequest) -> None:
        """Validate state data in request."""
        validation_result = self.validator.validate_state(request.state_data)
        if not validation_result.is_valid:
            raise NetraException(f"Invalid state data: {validation_result.errors}")
    
    def _prepare_json_safe_data(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare JSON-safe data for database storage."""
        return json.loads(json.dumps(state_data, cls=DateTimeEncoder))
    
    def _build_snapshot_record(self, snapshot_id: str, request: StatePersistenceRequest,
                              serialization_format: SerializationFormat, 
                              json_safe_data: Dict[str, Any]) -> AgentStateSnapshot:
        """Build snapshot record for database insertion."""
        return AgentStateSnapshot(
            id=snapshot_id, run_id=request.run_id, thread_id=request.thread_id,
            user_id=request.user_id, state_data=json_safe_data,
            serialization_format=self._extract_value(serialization_format),
            checkpoint_type=self._extract_value(request.checkpoint_type),
            agent_phase=self._extract_value(request.agent_phase) if request.agent_phase else None,
            execution_context=request.execution_context, is_recovery_point=request.is_recovery_point,
            expires_at=request.expires_at or self._calculate_expiry_date())
    
    def _extract_value(self, obj) -> str:
        """Extract value from enum or return as-is."""
        return obj.value if hasattr(obj, 'value') else obj
    
    async def _get_latest_snapshot(self, run_id: str, snapshot_id: Optional[str],
                                  db_session: AsyncSession) -> Optional[AgentStateSnapshot]:
        """Get the latest or specific snapshot for a run."""
        if snapshot_id:
            result = await db_session.execute(
                select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id))
        else:
            result = await db_session.execute(
                select(AgentStateSnapshot).where(AgentStateSnapshot.run_id == run_id)
                .order_by(desc(AgentStateSnapshot.created_at)).limit(1))
        return result.scalar_one_or_none()
    
    async def _deserialize_state_data(self, state_data: Dict[str, Any], 
                                     serialization_format: str) -> Dict[str, Any]:
        """Deserialize state data from database format."""
        # For now, state_data is already stored as JSON in database
        # In future, could support other formats stored as BLOB
        return state_data

    def _build_persistence_request_from_kwargs(self, kwargs: Dict[str, Any]) -> StatePersistenceRequest:
        """Build StatePersistenceRequest from legacy kwargs."""
        state_data = kwargs['state'].model_dump() if hasattr(kwargs['state'], 'model_dump') else kwargs['state']
        return StatePersistenceRequest(
            run_id=kwargs['run_id'],
            thread_id=kwargs.get('thread_id'),
            user_id=kwargs.get('user_id'),
            state_data=state_data,
            checkpoint_type=kwargs.get('checkpoint_type', CheckpointType.MANUAL),
            agent_phase=kwargs.get('agent_phase'),
            execution_context=kwargs.get('execution_context', {}),
            is_recovery_point=kwargs.get('is_recovery_point', False),
            expires_at=kwargs.get('expires_at')
        )
    
    async def get_thread_context(self, thread_id: str = None) -> Dict[str, Any]:
        """Get thread context for agent orchestration."""
        # Return empty context for now - can be enhanced to store thread-specific data
        return {}

# Global instance
state_persistence_service = StatePersistenceService()