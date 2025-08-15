"""Database rollback manager for coordinated rollback operations.

Provides sophisticated rollback capabilities across PostgreSQL and ClickHouse
with operation tracking, dependency management, and cascading rollbacks.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable

from app.db.postgres import get_postgres_session
from app.db.clickhouse import get_clickhouse_client
from app.core.error_recovery import OperationType
from app.logging_config import central_logger

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


class PostgresRollbackExecutor:
    """Executes PostgreSQL rollback operations."""
    
    def __init__(self):
        """Initialize PostgreSQL rollback executor."""
        self.active_connections: Dict[str, Any] = {}
    
    async def execute_rollback(
        self,
        operation: RollbackOperation,
        session_id: str
    ) -> bool:
        """Execute a single PostgreSQL rollback operation."""
        try:
            session = await self._get_session(session_id)
            
            if operation.operation_type == "INSERT":
                success = await self._rollback_insert(session, operation)
            elif operation.operation_type == "UPDATE":
                success = await self._rollback_update(session, operation)
            elif operation.operation_type == "DELETE":
                success = await self._rollback_delete(session, operation)
            else:
                logger.error(f"Unknown operation type: {operation.operation_type}")
                return False
            
            if success:
                operation.state = RollbackState.COMPLETED
                operation.executed_at = datetime.now()
                logger.debug(f"Rollback completed: {operation.operation_id}")
            else:
                operation.state = RollbackState.FAILED
            
            return success
            
        except Exception as e:
            operation.state = RollbackState.FAILED
            operation.error = str(e)
            logger.error(f"Rollback execution failed: {operation.operation_id}: {e}")
            return False
    
    async def _get_session(self, session_id: str):
        """Get or create database session for rollback."""
        if session_id not in self.active_connections:
            session = await get_postgres_session()
            self.active_connections[session_id] = session
            
            # Start transaction
            await session.begin()
        
        return self.active_connections[session_id]
    
    async def _rollback_insert(self, session, operation: RollbackOperation) -> bool:
        """Rollback an INSERT operation by deleting the record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Build DELETE query using primary key or unique identifier
            where_conditions = []
            where_values = []
            
            for key, value in rollback_data.get('primary_key', {}).items():
                where_conditions.append(f"{key} = %s")
                where_values.append(value)
            
            if not where_conditions:
                # Fallback to all columns if no primary key
                for key, value in rollback_data.get('data', {}).items():
                    where_conditions.append(f"{key} = %s")
                    where_values.append(value)
            
            query = f"DELETE FROM {table_name} WHERE {' AND '.join(where_conditions)}"
            
            result = await session.execute(query, where_values)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Insert rollback failed: {e}")
            return False
    
    async def _rollback_update(self, session, operation: RollbackOperation) -> bool:
        """Rollback an UPDATE operation by restoring original values."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Restore original values
            original_data = rollback_data.get('original_data', {})
            primary_key = rollback_data.get('primary_key', {})
            
            if not original_data or not primary_key:
                logger.error("Insufficient data for UPDATE rollback")
                return False
            
            # Build UPDATE query
            set_clauses = []
            set_values = []
            
            for key, value in original_data.items():
                set_clauses.append(f"{key} = %s")
                set_values.append(value)
            
            where_conditions = []
            where_values = []
            
            for key, value in primary_key.items():
                where_conditions.append(f"{key} = %s")
                where_values.append(value)
            
            query = f"""
                UPDATE {table_name}
                SET {', '.join(set_clauses)}
                WHERE {' AND '.join(where_conditions)}
            """
            
            result = await session.execute(query, set_values + where_values)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Update rollback failed: {e}")
            return False
    
    async def _rollback_delete(self, session, operation: RollbackOperation) -> bool:
        """Rollback a DELETE operation by restoring the record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Restore deleted record
            original_data = rollback_data.get('original_data', {})
            
            if not original_data:
                logger.error("No original data for DELETE rollback")
                return False
            
            # Build INSERT query
            columns = list(original_data.keys())
            values = list(original_data.values())
            placeholders = ', '.join(['%s'] * len(values))
            
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """
            
            await session.execute(query, values)
            return True
            
        except Exception as e:
            logger.error(f"Delete rollback failed: {e}")
            return False
    
    async def commit_session(self, session_id: str) -> None:
        """Commit rollback session."""
        if session_id in self.active_connections:
            session = self.active_connections[session_id]
            await session.commit()
            await session.close()
            del self.active_connections[session_id]
    
    async def rollback_session(self, session_id: str) -> None:
        """Rollback the rollback session (undo rollbacks)."""
        if session_id in self.active_connections:
            session = self.active_connections[session_id]
            await session.rollback()
            await session.close()
            del self.active_connections[session_id]


class ClickHouseRollbackExecutor:
    """Executes ClickHouse rollback operations using compensation."""
    
    def __init__(self):
        """Initialize ClickHouse rollback executor."""
        pass
    
    async def execute_rollback(
        self,
        operation: RollbackOperation,
        session_id: str
    ) -> bool:
        """Execute ClickHouse rollback using compensation patterns."""
        try:
            client = await get_clickhouse_client()
            
            if operation.operation_type == "INSERT":
                success = await self._compensate_insert(client, operation)
            elif operation.operation_type == "UPDATE":
                success = await self._compensate_update(client, operation)
            elif operation.operation_type == "DELETE":
                success = await self._compensate_delete(client, operation)
            else:
                logger.error(f"Unknown operation type: {operation.operation_type}")
                return False
            
            if success:
                operation.state = RollbackState.COMPLETED
                operation.executed_at = datetime.now()
            else:
                operation.state = RollbackState.FAILED
            
            return success
            
        except Exception as e:
            operation.state = RollbackState.FAILED
            operation.error = str(e)
            logger.error(f"ClickHouse rollback failed: {operation.operation_id}: {e}")
            return False
    
    async def _compensate_insert(self, client, operation: RollbackOperation) -> bool:
        """Compensate INSERT by marking as deleted."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Create compensation record in deletion table
            deletion_table = f"{table_name}_deletions"
            compensation_data = {
                **rollback_data.get('primary_key', {}),
                'deleted_at': datetime.now(),
                'deletion_reason': 'rollback_compensation',
                'operation_id': operation.operation_id
            }
            
            await client.insert(deletion_table, [compensation_data])
            logger.debug(f"ClickHouse INSERT compensated: {operation.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse INSERT compensation failed: {e}")
            return False
    
    async def _compensate_update(self, client, operation: RollbackOperation) -> bool:
        """Compensate UPDATE by inserting correction record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Create correction record
            correction_table = f"{table_name}_corrections"
            correction_data = {
                **rollback_data.get('primary_key', {}),
                **rollback_data.get('original_data', {}),
                'corrected_at': datetime.now(),
                'correction_reason': 'rollback_compensation',
                'operation_id': operation.operation_id
            }
            
            await client.insert(correction_table, [correction_data])
            logger.debug(f"ClickHouse UPDATE compensated: {operation.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse UPDATE compensation failed: {e}")
            return False
    
    async def _compensate_delete(self, client, operation: RollbackOperation) -> bool:
        """Compensate DELETE by re-inserting the record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            # Re-insert deleted data
            original_data = rollback_data.get('original_data', {})
            if not original_data:
                logger.error("No original data for DELETE compensation")
                return False
            
            # Add metadata for tracking
            restore_data = {
                **original_data,
                'restored_at': datetime.now(),
                'restore_reason': 'rollback_compensation',
                'operation_id': operation.operation_id
            }
            
            await client.insert(table_name, [restore_data])
            logger.debug(f"ClickHouse DELETE compensated: {operation.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse DELETE compensation failed: {e}")
            return False


class DependencyResolver:
    """Resolves dependencies between rollback operations."""
    
    def __init__(self):
        """Initialize dependency resolver."""
        self.dependency_rules = {
            DependencyType.FOREIGN_KEY: self._resolve_foreign_key,
            DependencyType.CASCADE: self._resolve_cascade,
            DependencyType.TRIGGER: self._resolve_trigger,
            DependencyType.LOGICAL: self._resolve_logical,
            DependencyType.TEMPORAL: self._resolve_temporal,
        }
    
    def resolve_execution_order(
        self,
        operations: List[RollbackOperation]
    ) -> List[List[RollbackOperation]]:
        """Resolve execution order considering dependencies."""
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(operations)
        
        # Topological sort to determine execution order
        execution_batches = []
        remaining_ops = set(op.operation_id for op in operations)
        operations_map = {op.operation_id: op for op in operations}
        
        while remaining_ops:
            # Find operations with no unresolved dependencies
            ready_ops = []
            for op_id in remaining_ops:
                dependencies = dependency_graph.get(op_id, set())
                if not dependencies.intersection(remaining_ops):
                    ready_ops.append(operations_map[op_id])
            
            if not ready_ops:
                # Circular dependency detected - break it
                logger.warning("Circular dependency detected in rollback operations")
                ready_ops = [operations_map[next(iter(remaining_ops))]]
            
            execution_batches.append(ready_ops)
            for op in ready_ops:
                remaining_ops.remove(op.operation_id)
        
        return execution_batches
    
    def _build_dependency_graph(
        self,
        operations: List[RollbackOperation]
    ) -> Dict[str, Set[str]]:
        """Build dependency graph from operations."""
        graph = {}
        
        for operation in operations:
            dependencies = set()
            
            # Add explicit dependencies
            dependencies.update(operation.dependencies)
            
            # Add implicit dependencies based on operation analysis
            implicit_deps = self._analyze_implicit_dependencies(operation, operations)
            dependencies.update(implicit_deps)
            
            graph[operation.operation_id] = dependencies
        
        return graph
    
    def _analyze_implicit_dependencies(
        self,
        operation: RollbackOperation,
        all_operations: List[RollbackOperation]
    ) -> Set[str]:
        """Analyze implicit dependencies between operations."""
        dependencies = set()
        
        for other_op in all_operations:
            if other_op.operation_id == operation.operation_id:
                continue
            
            # Check for table-level dependencies
            if self._has_table_dependency(operation, other_op):
                dependencies.add(other_op.operation_id)
            
            # Check for temporal dependencies
            if self._has_temporal_dependency(operation, other_op):
                dependencies.add(other_op.operation_id)
        
        return dependencies
    
    def _has_table_dependency(
        self,
        op1: RollbackOperation,
        op2: RollbackOperation
    ) -> bool:
        """Check if operations have table-level dependencies."""
        # Same table operations should be ordered
        if op1.table_name == op2.table_name:
            # DELETEs should happen before INSERTs for same table
            if op1.operation_type == "INSERT" and op2.operation_type == "DELETE":
                return True
            # UPDATEs should happen after DELETEs and before INSERTs
            if op1.operation_type == "UPDATE" and op2.operation_type == "DELETE":
                return True
        
        return False
    
    def _has_temporal_dependency(
        self,
        op1: RollbackOperation,
        op2: RollbackOperation
    ) -> bool:
        """Check if operations have temporal dependencies."""
        # Operations created earlier should be rolled back later
        return op1.created_at > op2.created_at
    
    def _resolve_foreign_key(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve foreign key dependencies."""
        # Implementation would analyze FK constraints
        return []
    
    def _resolve_cascade(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve cascade dependencies."""
        # Implementation would analyze cascade rules
        return []
    
    def _resolve_trigger(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve trigger dependencies."""
        # Implementation would analyze trigger effects
        return []
    
    def _resolve_logical(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve logical business dependencies."""
        # Implementation would analyze business logic dependencies
        return []
    
    def _resolve_temporal(self, operations: List[RollbackOperation]) -> List[str]:
        """Resolve temporal dependencies."""
        # Implementation would analyze time-based dependencies
        return []


class RollbackManager:
    """Central manager for database rollback operations."""
    
    def __init__(self):
        """Initialize rollback manager."""
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
        success_count = 0
        failed_operations = []
        for batch_idx, batch in enumerate(execution_batches):
            batch_result = await self._execute_single_batch(session_id, batch, batch_idx, len(execution_batches))
            success_count += batch_result['successes']
            failed_operations.extend(batch_result['failures'])
        return {'success_count': success_count, 'failed_operations': failed_operations}

    async def _execute_single_batch(
        self, 
        session_id: str, 
        batch: List[RollbackOperation], 
        batch_idx: int, 
        total_batches: int
    ) -> Dict[str, Any]:
        """Execute a single batch of operations concurrently."""
        batch_tasks = [self._create_execution_task(operation, session_id) for operation in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        result = self._process_batch_results(batch, batch_results)
        self._log_batch_completion(batch_idx, total_batches, len(batch), result)
        return result

    def _create_execution_task(self, operation: RollbackOperation, session_id: str):
        """Create execution task for operation based on table type."""
        if operation.table_name.startswith('clickhouse_'):
            return self.clickhouse_executor.execute_rollback(operation, session_id)
        return self.postgres_executor.execute_rollback(operation, session_id)

    def _process_batch_results(
        self, 
        batch: List[RollbackOperation], 
        batch_results: List[Any]
    ) -> Dict[str, Any]:
        """Process batch execution results and update operation states."""
        successes = 0
        failures = []
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                batch[i].state = RollbackState.FAILED
                batch[i].error = str(result)
                failures.append(batch[i])
            elif result:
                successes += 1
            else:
                failures.append(batch[i])
        return {'successes': successes, 'failures': failures}

    def _log_batch_completion(
        self, 
        batch_idx: int, 
        total_batches: int, 
        batch_size: int, 
        result: Dict[str, Any]
    ) -> None:
        """Log batch completion statistics."""
        logger.info(
            f"Completed rollback batch {batch_idx + 1}/{total_batches}",
            batch_size=batch_size,
            successes=result['successes'],
            failures=len(result['failures'])
        )

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