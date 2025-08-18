"""Transaction manager for coordinated database operations with rollback support.

Provides transactional consistency across multiple database operations
with automatic rollback capabilities for error recovery.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable

from app.db.postgres import get_postgres_session
from app.db.clickhouse import get_clickhouse_client
from app.core.error_recovery import OperationType
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionState(Enum):
    """States of a transaction."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class OperationState(Enum):
    """States of individual operations within a transaction."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass
class Operation:
    """Represents a single operation within a transaction."""
    operation_id: str
    operation_type: OperationType
    state: OperationState = OperationState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    compensation_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    """Represents a distributed transaction."""
    transaction_id: str
    state: TransactionState = TransactionState.PENDING
    operations: List[Operation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        return datetime.now() - self.created_at > self.timeout
    
    @property
    def completed_operations(self) -> List[Operation]:
        """Get all completed operations."""
        return [op for op in self.operations if op.state == OperationState.COMPLETED]
    
    @property
    def failed_operations(self) -> List[Operation]:
        """Get all failed operations."""
        return [op for op in self.operations if op.state == OperationState.FAILED]


class CompensationRegistry:
    """Registry for compensation handlers."""
    
    def __init__(self):
        """Initialize compensation registry."""
        self.handlers: Dict[OperationType, Callable] = {}
    
    def register(self, operation_type: OperationType, handler: Callable):
        """Register compensation handler for operation type."""
        self.handlers[operation_type] = handler
        logger.debug(f"Registered compensation handler for {operation_type}")
    
    def get_handler(self, operation_type: OperationType) -> Optional[Callable]:
        """Get compensation handler for operation type."""
        return self.handlers.get(operation_type)


class PostgresOperationManager:
    """Manages PostgreSQL operations within transactions."""
    
    def __init__(self):
        """Initialize PostgreSQL operation manager."""
        self.active_sessions: Dict[str, Any] = {}
    
    async def begin_operation(self, transaction_id: str, operation_id: str) -> None:
        """Begin a new PostgreSQL operation."""
        if transaction_id not in self.active_sessions:
            session = await get_postgres_session()
            await session.begin()
            self.active_sessions[transaction_id] = session
            logger.debug(f"Started PostgreSQL transaction: {transaction_id}")
    
    async def commit_operation(self, transaction_id: str) -> None:
        """Commit PostgreSQL transaction."""
        if transaction_id in self.active_sessions:
            session = self.active_sessions[transaction_id]
            await session.commit()
            await session.close()
            del self.active_sessions[transaction_id]
            logger.debug(f"Committed PostgreSQL transaction: {transaction_id}")
    
    async def rollback_operation(self, transaction_id: str) -> None:
        """Rollback PostgreSQL transaction."""
        if transaction_id in self.active_sessions:
            session = self.active_sessions[transaction_id]
            await session.rollback()
            await session.close()
            del self.active_sessions[transaction_id]
            logger.debug(f"Rolled back PostgreSQL transaction: {transaction_id}")


class ClickHouseOperationManager:
    """Manages ClickHouse operations with compensation."""
    
    def __init__(self):
        """Initialize ClickHouse operation manager."""
        self.operation_records: Dict[str, List[Dict]] = {}
    
    async def record_insert(self, operation_id: str, table: str, data: Dict) -> None:
        """Record ClickHouse insert for potential compensation."""
        if operation_id not in self.operation_records:
            self.operation_records[operation_id] = []
        
        record = self._create_insert_record(table, data)
        self.operation_records[operation_id].append(record)
        logger.debug(f"Recorded ClickHouse insert: {operation_id}")
    
    def _create_insert_record(self, table: str, data: Dict) -> Dict:
        """Create insert record for compensation."""
        return {
            'action': 'insert',
            'table': table,
            'data': data,
            'timestamp': datetime.now()
        }
    
    async def compensate_inserts(self, operation_id: str) -> bool:
        """Compensate ClickHouse inserts by marking as deleted."""
        if operation_id not in self.operation_records:
            return True
        
        try:
            success = await self._execute_compensation(operation_id)
            self._handle_successful_compensation(operation_id, success)
            return success
        except Exception as e:
            logger.error(f"ClickHouse compensation failed: {e}")
            return False
    
    def _handle_successful_compensation(self, operation_id: str, success: bool) -> None:
        """Handle successful compensation cleanup."""
        if success:
            del self.operation_records[operation_id]
            logger.debug(f"Compensated ClickHouse operations: {operation_id}")
    
    async def _execute_compensation(self, operation_id: str) -> bool:
        """Execute compensation for operation records."""
        client = await get_clickhouse_client()
        for record in self.operation_records[operation_id]:
            if record['action'] == 'insert':
                await self._mark_as_deleted(client, record)
        return True
    
    async def _mark_as_deleted(self, client, record: Dict) -> None:
        """Mark ClickHouse record as deleted."""
        compensation_data = self._create_compensation_data(record['data'])
        deleted_table = f"{record['table']}_deleted"
        await client.insert(deleted_table, [compensation_data])
    
    def _create_compensation_data(self, original_data: Dict) -> Dict:
        """Create compensation record data."""
        return {
            **original_data,
            'deleted_at': datetime.now(),
            'deleted_by_compensation': True
        }


class TransactionManager:
    """Manages distributed transactions across multiple data stores."""
    
    def __init__(self):
        """Initialize transaction manager."""
        self.active_transactions: Dict[str, Transaction] = {}
        self.compensation_registry = CompensationRegistry()
        self.postgres_manager = PostgresOperationManager()
        self.clickhouse_manager = ClickHouseOperationManager()
        
        # Register default compensation handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default compensation handlers."""
        handlers = self._get_default_handler_mappings()
        self._register_handlers(handlers)
    
    def _get_default_handler_mappings(self) -> List:
        """Get default handler mappings."""
        return [
            (OperationType.DATABASE_WRITE, self._compensate_postgres_write),
            (OperationType.DATABASE_READ, self._compensate_postgres_read)
        ]
    
    def _register_handlers(self, handlers: List) -> None:
        """Register all handlers from list."""
        for operation_type, handler in handlers:
            self.compensation_registry.register(operation_type, handler)
    
    async def begin_transaction(self, metadata: Optional[Dict] = None) -> str:
        """Begin a new distributed transaction."""
        transaction_id = str(uuid.uuid4())
        transaction = self._create_new_transaction(transaction_id, metadata)
        self.active_transactions[transaction_id] = transaction
        logger.info(f"Started transaction: {transaction_id}")
        return transaction_id
    
    def _create_new_transaction(self, transaction_id: str, metadata: Optional[Dict]) -> Transaction:
        """Create new transaction instance."""
        return Transaction(
            transaction_id=transaction_id,
            state=TransactionState.ACTIVE,
            metadata=metadata or {}
        )
    
    async def add_operation(
        self,
        transaction_id: str,
        operation_type: OperationType,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add operation to transaction."""
        self._validate_transaction_exists(transaction_id)
        operation = self._create_and_add_operation(transaction_id, operation_type, metadata)
        await self._initialize_operation(transaction_id, operation)
        logger.debug(f"Added operation {operation.operation_id} to transaction {transaction_id}")
        return operation.operation_id
    
    def _create_and_add_operation(self, transaction_id: str, operation_type: OperationType, metadata: Optional[Dict]) -> Operation:
        """Create new operation and add to transaction."""
        operation = self._create_new_operation(operation_type, metadata)
        transaction = self.active_transactions[transaction_id]
        transaction.operations.append(operation)
        return operation
    
    def _validate_transaction_exists(self, transaction_id: str) -> None:
        """Validate transaction exists in active transactions."""
        if transaction_id not in self.active_transactions:
            raise ValueError(f"Transaction not found: {transaction_id}")
    
    def _create_new_operation(self, operation_type: OperationType, metadata: Optional[Dict]) -> Operation:
        """Create new operation instance."""
        return Operation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_type,
            metadata=metadata or {}
        )
    
    async def complete_operation(self, transaction_id: str, operation_id: str) -> None:
        """Mark operation as completed."""
        transaction = self._get_transaction(transaction_id)
        operation = self._get_operation(transaction, operation_id)
        
        self._mark_operation_completed(operation)
        logger.debug(f"Completed operation {operation_id}")
    
    def _get_transaction(self, transaction_id: str) -> Transaction:
        """Get transaction or raise error."""
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        return transaction
    
    def _get_operation(self, transaction: Transaction, operation_id: str) -> Operation:
        """Get operation or raise error."""
        operation = self._find_operation(transaction, operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")
        return operation
    
    def _mark_operation_completed(self, operation: Operation) -> None:
        """Mark operation as completed with timestamp."""
        operation.state = OperationState.COMPLETED
        operation.completed_at = datetime.now()
    
    async def fail_operation(
        self,
        transaction_id: str,
        operation_id: str,
        error: str
    ) -> None:
        """Mark operation as failed."""
        transaction = self._get_transaction(transaction_id)
        operation = self._get_operation(transaction, operation_id)
        
        self._mark_operation_failed(operation, error)
        logger.warning(f"Failed operation {operation_id}: {error}")
    
    def _mark_operation_failed(self, operation: Operation, error: str) -> None:
        """Mark operation as failed with error and timestamp."""
        operation.state = OperationState.FAILED
        operation.error = error
        operation.completed_at = datetime.now()
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit transaction if all operations succeeded."""
        transaction = self._get_transaction(transaction_id)
        
        if not self._can_commit_transaction(transaction):
            return False
        
        return await self._attempt_commit(transaction_id)
    
    async def _attempt_commit(self, transaction_id: str) -> bool:
        """Attempt to commit transaction with error handling."""
        try:
            await self._execute_commit(transaction_id)
            return True
        except Exception as e:
            logger.error(f"Commit failed for transaction {transaction_id}: {e}")
            await self.rollback_transaction(transaction_id)
            return False
    
    def _can_commit_transaction(self, transaction: Transaction) -> bool:
        """Check if transaction can be committed."""
        if transaction.failed_operations:
            logger.warning("Cannot commit transaction with failed operations")
            return False
        return True
    
    async def _execute_commit(self, transaction_id: str) -> None:
        """Execute transaction commit."""
        await self.postgres_manager.commit_operation(transaction_id)
        
        transaction = self.active_transactions[transaction_id]
        transaction.state = TransactionState.COMMITTED
        logger.info(f"Committed transaction: {transaction_id}")
        
        await self._cleanup_transaction(transaction_id)
    
    async def rollback_transaction(self, transaction_id: str) -> None:
        """Rollback entire transaction with compensation."""
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            logger.warning(f"Rollback requested for unknown transaction: {transaction_id}")
            return
        
        logger.info(f"Rolling back transaction: {transaction_id}")
        await self._perform_rollback(transaction_id, transaction)
        await self._cleanup_transaction(transaction_id)
    
    async def _perform_rollback(self, transaction_id: str, transaction: Transaction) -> None:
        """Perform rollback operations with error handling."""
        try:
            await self._execute_rollback(transaction_id, transaction)
            transaction.state = TransactionState.ROLLED_BACK
            logger.info(f"Successfully rolled back transaction: {transaction_id}")
        except Exception as e:
            logger.error(f"Rollback failed for transaction {transaction_id}: {e}")
            transaction.state = TransactionState.FAILED
    
    async def _execute_rollback(self, transaction_id: str, transaction: Transaction) -> None:
        """Execute transaction rollback operations."""
        await self.postgres_manager.rollback_operation(transaction_id)
        
        # Compensate completed operations in reverse order
        for operation in reversed(transaction.completed_operations):
            await self._compensate_operation(operation)
    
    async def rollback_operation(self, operation_id: str) -> None:
        """Rollback specific operation across all transactions."""
        operation = self._find_operation_across_transactions(operation_id)
        if operation:
            await self._rollback_single_operation(operation)
            logger.info(f"Rolled back operation: {operation_id}")
        else:
            logger.warning(f"Operation not found for rollback: {operation_id}")
    
    def _find_operation_across_transactions(self, operation_id: str) -> Optional[Operation]:
        """Find operation across all active transactions."""
        for transaction in self.active_transactions.values():
            operation = self._find_operation(transaction, operation_id)
            if operation:
                return operation
        return None
    
    async def _rollback_single_operation(self, operation: Operation) -> None:
        """Rollback a single operation."""
        if operation.state == OperationState.COMPLETED:
            await self._compensate_operation(operation)
        operation.state = OperationState.COMPENSATED
    
    async def _initialize_operation(
        self,
        transaction_id: str,
        operation: Operation
    ) -> None:
        """Initialize operation-specific resources."""
        if self._is_database_operation(operation):
            await self.postgres_manager.begin_operation(
                transaction_id,
                operation.operation_id
            )
    
    def _is_database_operation(self, operation: Operation) -> bool:
        """Check if operation requires database initialization."""
        return operation.operation_type in [
            OperationType.DATABASE_WRITE,
            OperationType.DATABASE_READ
        ]
    
    def _find_operation(
        self,
        transaction: Transaction,
        operation_id: str
    ) -> Optional[Operation]:
        """Find operation within transaction."""
        for operation in transaction.operations:
            if operation.operation_id == operation_id:
                return operation
        return None
    
    async def _compensate_operation(self, operation: Operation) -> None:
        """Execute compensation for completed operation."""
        handler = self.compensation_registry.get_handler(operation.operation_type)
        if handler:
            await self._execute_compensation_handler(handler, operation)
        else:
            logger.warning(f"No compensation handler for {operation.operation_type}")
    
    async def _execute_compensation_handler(self, handler: Callable, operation: Operation) -> None:
        """Execute compensation handler with error handling."""
        try:
            await handler(operation)
            operation.state = OperationState.COMPENSATED
            logger.debug(f"Compensated operation: {operation.operation_id}")
        except Exception as e:
            logger.error(f"Compensation failed for {operation.operation_id}: {e}")
    
    async def _compensate_postgres_write(self, operation: Operation) -> None:
        """Compensate PostgreSQL write operation."""
        # PostgreSQL compensation is handled by transaction rollback
        logger.debug(f"PostgreSQL write compensation: {operation.operation_id}")
    
    async def _compensate_postgres_read(self, operation: Operation) -> None:
        """Compensate PostgreSQL read operation."""
        # Read operations typically don't need compensation
        logger.debug(f"PostgreSQL read compensation: {operation.operation_id}")
    
    async def _cleanup_transaction(self, transaction_id: str) -> None:
        """Clean up transaction resources."""
        if transaction_id in self.active_transactions:
            del self.active_transactions[transaction_id]
        
        # Clean up ClickHouse records
        await self.clickhouse_manager.compensate_inserts(transaction_id)
    
    @asynccontextmanager
    async def transaction(self, metadata: Optional[Dict] = None):
        """Context manager for automatic transaction management."""
        transaction_id = await self.begin_transaction(metadata)
        try:
            yield transaction_id
            await self._finalize_transaction(transaction_id)
        except Exception as e:
            await self._handle_transaction_error(transaction_id, e)
    
    async def _handle_transaction_error(self, transaction_id: str, error: Exception) -> None:
        """Handle transaction context manager error."""
        await self.rollback_transaction(transaction_id)
        raise error
    
    async def _finalize_transaction(self, transaction_id: str) -> None:
        """Finalize transaction with commit."""
        success = await self.commit_transaction(transaction_id)
        if not success:
            raise RuntimeError("Transaction commit failed")


# Global transaction manager instance
transaction_manager = TransactionManager()