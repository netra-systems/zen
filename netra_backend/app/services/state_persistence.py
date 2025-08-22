"""Enhanced Agent State Persistence Service

This service provides atomic state persistence with versioning,
compression, and recovery capabilities following the 25-line function limit.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.db.models_agent_state import (
    AgentStateSnapshot,
    AgentStateTransaction,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    RecoveryType,
    SerializationFormat,
    StatePersistenceRequest,
    StateRecoveryRequest,
)
from netra_backend.app.services.state_cache_manager import state_cache_manager
from netra_backend.app.services.state_recovery_manager import state_recovery_manager
from netra_backend.app.services.state_serialization import (
    DateTimeEncoder,
    StateSerializer,
    StateValidator,
)

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
        request, db_session = self._parse_save_arguments(*args, **kwargs)
        return await self._execute_save_with_error_handling(request, db_session)

    def _parse_save_arguments(self, *args, **kwargs) -> Tuple[StatePersistenceRequest, AsyncSession]:
        """Parse and validate save arguments for backward compatibility."""
        if len(args) == 2 and isinstance(args[0], StatePersistenceRequest):
            return args[0], args[1]
        return self._parse_kwargs_arguments(kwargs)

    def _parse_kwargs_arguments(self, kwargs: Dict[str, Any]) -> Tuple[StatePersistenceRequest, AsyncSession]:
        """Parse kwargs-style arguments for save operation."""
        if 'run_id' in kwargs and 'db_session' in kwargs:
            request = self._build_persistence_request_from_kwargs(kwargs)
            return request, kwargs['db_session']
        raise ValueError("Invalid arguments for save_agent_state")

    async def _execute_save_with_error_handling(self, request: StatePersistenceRequest, 
                                               db_session: AsyncSession) -> Tuple[bool, Optional[str]]:
        """Execute save operation with comprehensive error handling."""
        try:
            snapshot_id = await self._execute_state_save_transaction(request, db_session)
            self._log_save_success(snapshot_id, request.run_id)
            return True, snapshot_id
        except Exception as e:
            return self._handle_save_error(request, e)

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
        return await self._execute_load_with_error_handling(run_id, snapshot_id, db_session)

    async def _execute_load_with_error_handling(self, run_id: str, snapshot_id: Optional[str],
                                               db_session: Optional[AsyncSession]) -> Optional[DeepAgentState]:
        """Execute load operation with comprehensive error handling."""
        try:
            state = await self._attempt_cache_load(run_id, snapshot_id)
            if state:
                return state
            return await self._attempt_database_load(run_id, snapshot_id, db_session)
        except Exception as e:
            return self._handle_load_error(run_id, e)

    async def _attempt_cache_load(self, run_id: str, snapshot_id: Optional[str]) -> Optional[DeepAgentState]:
        """Try loading state from Redis cache first."""
        if not snapshot_id:
            return await state_cache_manager.load_from_redis_cache(run_id)
        return None

    async def _attempt_database_load(self, run_id: str, snapshot_id: Optional[str], 
                                    db_session: Optional[AsyncSession]) -> Optional[DeepAgentState]:
        """Load state from database snapshots."""
        if not db_session:
            return self._handle_no_session_warning(run_id)
        snapshot = await self._get_latest_snapshot(run_id, snapshot_id, db_session)
        return await self._process_snapshot_result(run_id, snapshot)

    def _handle_no_session_warning(self, run_id: str) -> None:
        """Handle case when no database session is provided."""
        logger.warning(f"No state found for run {run_id}")
        return None

    async def _process_snapshot_result(self, run_id: str, snapshot) -> Optional[DeepAgentState]:
        """Process snapshot result or handle missing snapshot."""
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
        return await self._execute_recovery_with_error_handling(request, recovery_id, db_session)

    async def _execute_recovery_with_error_handling(self, request: StateRecoveryRequest, 
                                                   recovery_id: str, db_session: AsyncSession) -> Tuple[bool, Optional[str]]:
        """Execute recovery operation with comprehensive error handling."""
        try:
            success = await self._execute_recovery_operation(request, recovery_id, db_session)
            self._log_recovery_result(recovery_id, success)
            return self._format_recovery_result(success, recovery_id)
        except Exception as e:
            return await self._handle_recovery_error(request, recovery_id, db_session, e)

    async def _handle_recovery_error(self, request: StateRecoveryRequest, recovery_id: str,
                                   db_session: AsyncSession, error: Exception) -> Tuple[bool, None]:
        """Handle recovery operation errors."""
        logger.error(f"Recovery failed for run {request.run_id}: {error}")
        await state_recovery_manager.complete_recovery_log(recovery_id, False, db_session, str(error))
        return False, None

    async def _execute_recovery_operation(self, request: StateRecoveryRequest, recovery_id: str, db_session: AsyncSession) -> bool:
        """Execute the recovery operation workflow."""
        return await state_recovery_manager.execute_recovery_operation(request, recovery_id, db_session)
    
    async def _create_state_snapshot(self, request: StatePersistenceRequest,
                                    db_session: AsyncSession) -> str:
        """Create a new state snapshot in database."""
        snapshot_id = str(uuid.uuid4())
        snapshot = await self._prepare_snapshot_for_database(snapshot_id, request)
        return await self._insert_snapshot_to_database(snapshot, db_session, snapshot_id)

    async def _prepare_snapshot_for_database(self, snapshot_id: str, request: StatePersistenceRequest) -> AgentStateSnapshot:
        """Prepare and validate snapshot data for database insertion."""
        self._validate_request_state(request)
        serialization_format = self._choose_serialization_format(request.state_data)
        json_safe_data = self._prepare_json_safe_data(request.state_data)
        return self._build_snapshot_record(snapshot_id, request, serialization_format, json_safe_data)

    async def _insert_snapshot_to_database(self, snapshot: AgentStateSnapshot, 
                                         db_session: AsyncSession, snapshot_id: str) -> str:
        """Insert prepared snapshot into database."""
        db_session.add(snapshot)
        await db_session.flush()
        return snapshot_id
    
    async def _log_state_transaction(self, snapshot_id: str, request: StatePersistenceRequest,
                                    operation_type: str, db_session: AsyncSession) -> str:
        """Log state transaction for audit trail."""
        transaction_id = str(uuid.uuid4())
        transaction = self._build_transaction_record(transaction_id, snapshot_id, request, operation_type)
        return await self._insert_transaction_to_database(transaction, db_session, transaction_id)

    def _build_transaction_record(self, transaction_id: str, snapshot_id: str, 
                                 request: StatePersistenceRequest, operation_type: str) -> AgentStateTransaction:
        """Build transaction record for database insertion."""
        execution_phase = self._extract_value(request.agent_phase) if request.agent_phase else None
        return AgentStateTransaction(
            id=transaction_id, snapshot_id=snapshot_id, run_id=request.run_id,
            operation_type=operation_type, triggered_by="system",
            execution_phase=execution_phase, status="pending")

    async def _insert_transaction_to_database(self, transaction: AgentStateTransaction, 
                                            db_session: AsyncSession, transaction_id: str) -> str:
        """Insert transaction record into database."""
        db_session.add(transaction)
        await db_session.flush()
        return transaction_id
    
    async def _cleanup_old_snapshots(self, run_id: str, db_session: AsyncSession) -> None:
        """Clean up old snapshots to maintain performance."""
        old_snapshot_ids = await self._get_old_snapshot_ids(run_id, db_session)
        if old_snapshot_ids:
            await self._delete_snapshots_batch(old_snapshot_ids, db_session)

    async def _get_old_snapshot_ids(self, run_id: str, db_session: AsyncSession) -> List[str]:
        """Get IDs of old snapshots that should be cleaned up."""
        result = await db_session.execute(
            select(AgentStateSnapshot.id)
            .where(AgentStateSnapshot.run_id == run_id)
            .order_by(desc(AgentStateSnapshot.created_at))
            .offset(self.max_snapshots_per_run))
        return [row[0] for row in result.fetchall()]
    
    async def _delete_snapshots_batch(self, snapshot_ids: List[str], 
                                     db_session: AsyncSession) -> None:
        """Delete snapshots and related data in batch."""
        await self._delete_related_transactions(snapshot_ids, db_session)
        await self._delete_snapshots_records(snapshot_ids, db_session)

    async def _delete_related_transactions(self, snapshot_ids: List[str], db_session: AsyncSession) -> None:
        """Delete transactions related to snapshots."""
        await db_session.execute(
            AgentStateTransaction.__table__.delete()
            .where(AgentStateTransaction.snapshot_id.in_(snapshot_ids)))

    async def _delete_snapshots_records(self, snapshot_ids: List[str], db_session: AsyncSession) -> None:
        """Delete snapshot records from database."""
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
        core_fields = self._build_snapshot_core_fields(snapshot_id, request, json_safe_data)
        metadata_fields = self._build_snapshot_metadata_fields(request, serialization_format)
        return AgentStateSnapshot(**core_fields, **metadata_fields)

    def _build_snapshot_core_fields(self, snapshot_id: str, request: StatePersistenceRequest,
                                   json_safe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build core fields for snapshot record."""
        return {
            'id': snapshot_id, 'run_id': request.run_id, 'thread_id': request.thread_id,
            'user_id': request.user_id, 'state_data': json_safe_data,
            'execution_context': request.execution_context, 'is_recovery_point': request.is_recovery_point
        }

    def _build_snapshot_metadata_fields(self, request: StatePersistenceRequest,
                                       serialization_format: SerializationFormat) -> Dict[str, Any]:
        """Build metadata fields for snapshot record."""
        return {
            'serialization_format': self._extract_value(serialization_format),
            'checkpoint_type': self._extract_value(request.checkpoint_type),
            'agent_phase': self._extract_value(request.agent_phase) if request.agent_phase else None,
            'expires_at': request.expires_at or self._calculate_expiry_date()
        }
    
    def _extract_value(self, obj) -> str:
        """Extract value from enum or return as-is."""
        return obj.value if hasattr(obj, 'value') else obj
    
    async def _get_latest_snapshot(self, run_id: str, snapshot_id: Optional[str],
                                  db_session: AsyncSession) -> Optional[AgentStateSnapshot]:
        """Get the latest or specific snapshot for a run."""
        if snapshot_id:
            return await self._get_specific_snapshot(snapshot_id, db_session)
        return await self._get_latest_run_snapshot(run_id, db_session)

    async def _get_specific_snapshot(self, snapshot_id: str, db_session: AsyncSession) -> Optional[AgentStateSnapshot]:
        """Get a specific snapshot by ID."""
        result = await db_session.execute(
            select(AgentStateSnapshot).where(AgentStateSnapshot.id == snapshot_id))
        return result.scalar_one_or_none()

    async def _get_latest_run_snapshot(self, run_id: str, db_session: AsyncSession) -> Optional[AgentStateSnapshot]:
        """Get the latest snapshot for a run."""
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
        state_data = self._extract_state_data_from_kwargs(kwargs)
        core_fields = self._build_request_core_fields_from_kwargs(kwargs, state_data)
        optional_fields = self._build_request_optional_fields_from_kwargs(kwargs)
        return StatePersistenceRequest(**core_fields, **optional_fields)

    def _extract_state_data_from_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process state data from kwargs."""
        return kwargs['state'].model_dump() if hasattr(kwargs['state'], 'model_dump') else kwargs['state']

    def _build_request_core_fields_from_kwargs(self, kwargs: Dict[str, Any], state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build core required fields for StatePersistenceRequest."""
        return {
            'run_id': kwargs['run_id'], 'thread_id': kwargs.get('thread_id'),
            'user_id': kwargs.get('user_id'), 'state_data': state_data
        }

    def _build_request_optional_fields_from_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build optional fields for StatePersistenceRequest."""
        return {
            'checkpoint_type': kwargs.get('checkpoint_type', CheckpointType.MANUAL),
            'agent_phase': kwargs.get('agent_phase'), 'execution_context': kwargs.get('execution_context', {}),
            'is_recovery_point': kwargs.get('is_recovery_point', False), 'expires_at': kwargs.get('expires_at')
        }
    
    def _log_save_success(self, snapshot_id: str, run_id: str) -> None:
        """Log successful save operation."""
        logger.info(f"Saved state snapshot {snapshot_id} for run {run_id}")
    
    def _handle_save_error(self, request: StatePersistenceRequest, error: Exception) -> Tuple[bool, None]:
        """Handle save operation error."""
        logger.error(f"Failed to save state for run {request.run_id}: {error}")
        return False, None
    
    def _format_recovery_result(self, success: bool, recovery_id: str) -> Tuple[bool, Optional[str]]:
        """Format recovery operation result."""
        return success, recovery_id if success else None
    
    def _handle_load_error(self, run_id: str, error: Exception) -> None:
        """Handle load operation error."""
        logger.error(f"Failed to load state for run {run_id}: {error}")
        return None
    
    def _log_recovery_result(self, recovery_id: str, success: bool) -> None:
        """Log recovery operation result."""
        status = 'completed' if success else 'failed'
        logger.info(f"Recovery {recovery_id} {status}")
    
    async def get_thread_context(self, thread_id: str = None) -> Dict[str, Any]:
        """Get thread context for agent orchestration."""
        # Return empty context for now - can be enhanced to store thread-specific data
        return {}

# Global instance
state_persistence_service = StatePersistenceService()