"""Core rollback manager components.

Contains core data structures, enums, and the main rollback manager orchestrator.
Focuses on session management and high-level rollback coordination.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RollbackState(Enum):
    """States of rollback operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class DependencyType(Enum):
    """Types of dependencies between operations."""
    FOREIGN_KEY = "foreign_key"
    CASCADE = "cascade"
    TRIGGER = "trigger"
    LOGICAL = "logical"
    TEMPORAL = "temporal"


@dataclass
class RollbackOperation:
    """Represents a single rollback operation."""
    operation_id: str
    table_name: str
    operation_type: str  # INSERT, UPDATE, DELETE
    rollback_data: Dict[str, Any]
    state: RollbackState = RollbackState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)


@dataclass
class RollbackSession:
    """Represents a rollback session with multiple operations."""
    session_id: str
    operations: List[RollbackOperation] = field(default_factory=list)
    state: RollbackState = RollbackState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if rollback session has expired."""
        return datetime.now() - self.created_at > self.timeout


class RollbackManager:
    """Central manager for database rollback operations."""
    
    def __init__(self):
        """Initialize rollback manager with executors and resolver."""
        from .rollback_manager_transactions import (
            PostgresRollbackExecutor, 
            ClickHouseRollbackExecutor
        )
        from .rollback_manager_recovery import DependencyResolver
        
        self.active_sessions: Dict[str, RollbackSession] = {}
        self.postgres_executor = PostgresRollbackExecutor()
        self.clickhouse_executor = ClickHouseRollbackExecutor()
        self.dependency_resolver = DependencyResolver()
    
    async def create_rollback_session(
        self,
        metadata: Optional[Dict] = None
    ) -> str:
        """Create a new rollback session."""
        session_id = str(uuid.uuid4())
        session = RollbackSession(
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Created rollback session: {session_id}")
        return session_id
    
    async def add_rollback_operation(
        self,
        session_id: str,
        table_name: str,
        operation_type: str,
        rollback_data: Dict[str, Any],
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Add rollback operation to session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Rollback session not found: {session_id}")
        
        operation_id = str(uuid.uuid4())
        operation = RollbackOperation(
            operation_id=operation_id,
            table_name=table_name,
            operation_type=operation_type,
            rollback_data=rollback_data,
            dependencies=dependencies or []
        )
        
        session = self.active_sessions[session_id]
        session.operations.append(operation)
        
        logger.debug(f"Added rollback operation {operation_id} to session {session_id}")
        return operation_id
    
    async def execute_rollback_session(self, session_id: str) -> bool:
        """Execute all rollback operations in session."""
        try:
            session = await self._validate_and_prepare_session(session_id)
            execution_batches = await self._resolve_execution_plan(session)
            execution_result = await self._execute_operation_batches(session_id, execution_batches)
            return await self._finalize_session_execution(session_id, session, execution_result)
        except Exception as e:
            return await self._handle_execution_failure_with_cleanup(session_id, e)

    async def _validate_and_prepare_session(self, session_id: str) -> RollbackSession:
        """Validate session exists and prepare for execution."""
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Rollback session not found: {session_id}")
        session.state = RollbackState.IN_PROGRESS
        return session

    async def _resolve_execution_plan(self, session: RollbackSession) -> List[List[RollbackOperation]]:
        """Resolve execution order and log execution plan."""
        execution_batches = self.dependency_resolver.resolve_execution_order(session.operations)
        logger.info(
            f"Executing rollback session {session.session_id}",
            total_operations=len(session.operations),
            batches=len(execution_batches)
        )
        return execution_batches

    async def _execute_operation_batches(
        self, 
        session_id: str, 
        execution_batches: List[List[RollbackOperation]]
    ) -> Dict[str, Any]:
        """Execute all operation batches and track results."""
        from .rollback_manager_execution import BatchExecutor
        executor = BatchExecutor(self.postgres_executor, self.clickhouse_executor)
        return await executor.execute_all_batches(session_id, execution_batches)

    async def _determine_final_state(
        self, 
        session_id: str, 
        session: RollbackSession, 
        execution_result: Dict[str, Any]
    ) -> bool:
        """Determine final session state based on execution results."""
        success_count = execution_result['success_count']
        failed_operations = execution_result['failed_operations']
        
        if not failed_operations:
            return await self._handle_complete_success(session_id, session)
        elif success_count > 0:
            return await self._handle_partial_success(session_id, session, success_count, failed_operations)
        else:
            return await self._handle_complete_failure(session_id, session)

    async def _handle_complete_success(self, session_id: str, session: RollbackSession) -> bool:
        """Handle complete success scenario."""
        session.state = RollbackState.COMPLETED
        await self.postgres_executor.commit_session(session_id)
        logger.info(f"Rollback session completed successfully: {session_id}")
        return True

    async def _handle_partial_success(
        self, 
        session_id: str, 
        session: RollbackSession, 
        success_count: int, 
        failed_operations: List[RollbackOperation]
    ) -> bool:
        """Handle partial success scenario."""
        session.state = RollbackState.PARTIAL
        await self.postgres_executor.commit_session(session_id)
        logger.warning(
            f"Rollback session completed with partial success: {session_id}",
            successes=success_count,
            failures=len(failed_operations)
        )
        return False

    async def _handle_complete_failure(self, session_id: str, session: RollbackSession) -> bool:
        """Handle complete failure scenario."""
        session.state = RollbackState.FAILED
        await self.postgres_executor.rollback_session(session_id)
        logger.error(f"Rollback session failed completely: {session_id}")
        return False

    async def _finalize_session_execution(
        self, 
        session_id: str, 
        session: RollbackSession, 
        execution_result: Dict[str, Any]
    ) -> bool:
        """Finalize session execution with state determination and cleanup."""
        try:
            return await self._determine_final_state(session_id, session, execution_result)
        finally:
            await self._cleanup_session(session_id)

    async def _handle_execution_failure_with_cleanup(self, session_id: str, error: Exception) -> bool:
        """Handle execution failure with proper state management and cleanup."""
        try:
            return await self._handle_execution_failure(session_id, error)
        finally:
            await self._cleanup_session(session_id)

    async def _handle_execution_failure(self, session_id: str, error: Exception) -> bool:
        """Handle execution failure with proper state management."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].state = RollbackState.FAILED
        await self.postgres_executor.rollback_session(session_id)
        logger.error(f"Rollback session execution failed: {session_id}: {error}")
        return False
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up rollback session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Clean up any remaining connections
        await self.postgres_executor.rollback_session(session_id)
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of rollback session."""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            'session_id': session_id,
            'state': session.state.value,
            'total_operations': len(session.operations),
            'completed_operations': len([
                op for op in session.operations
                if op.state == RollbackState.COMPLETED
            ]),
            'failed_operations': len([
                op for op in session.operations
                if op.state == RollbackState.FAILED
            ]),
            'created_at': session.created_at.isoformat(),
            'is_expired': session.is_expired
        }


# Global rollback manager instance
rollback_manager = RollbackManager()