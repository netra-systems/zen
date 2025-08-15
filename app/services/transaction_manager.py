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
        
        self.operation_records[operation_id].append({
            'action': 'insert',
            'table': table,
            'data': data,
            'timestamp': datetime.now()
        })
        logger.debug(f"Recorded ClickHouse insert: {operation_id}")
    
    async def compensate_inserts(self, operation_id: str) -> bool:
        """Compensate ClickHouse inserts by marking as deleted."""
        if operation_id not in self.operation_records:
            return True
        
        try:
            client = await get_clickhouse_client()
            for record in self.operation_records[operation_id]:
                if record['action'] == 'insert':
                    # Mark as deleted with metadata
                    await self._mark_as_deleted(client, record)
            
            del self.operation_records[operation_id]
            logger.debug(f"Compensated ClickHouse operations: {operation_id}")
            return True
        except Exception as e:
            logger.error(f"ClickHouse compensation failed: {e}")
            return False
    
    async def _mark_as_deleted(self, client, record: Dict) -> None:
        """Mark ClickHouse record as deleted."""
        table = record['table']
        data = record['data']
        
        # Create compensation record
        compensation_data = {
            **data,
            'deleted_at': datetime.now(),
            'deleted_by_compensation': True
        }
        
        # Insert compensation record
        await client.insert(f"{table}_deleted", [compensation_data])


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
        self.compensation_registry.register(
            OperationType.DATABASE_WRITE,
            self._compensate_postgres_write
        )
        self.compensation_registry.register(
            OperationType.DATABASE_READ,
            self._compensate_postgres_read
        )
    
    async def begin_transaction(self, metadata: Optional[Dict] = None) -> str:
        """Begin a new distributed transaction."""
        transaction_id = str(uuid.uuid4())
        transaction = Transaction(
            transaction_id=transaction_id,
            state=TransactionState.ACTIVE,
            metadata=metadata or {}
        )
        
        self.active_transactions[transaction_id] = transaction
        logger.info(f"Started transaction: {transaction_id}")
        return transaction_id
    
    async def add_operation(
        self,
        transaction_id: str,
        operation_type: OperationType,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add operation to transaction."""
        if transaction_id not in self.active_transactions:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        operation_id = str(uuid.uuid4())
        operation = Operation(
            operation_id=operation_id,
            operation_type=operation_type,
            metadata=metadata or {}
        )
        
        transaction = self.active_transactions[transaction_id]
        transaction.operations.append(operation)
        
        # Initialize operation-specific resources
        await self._initialize_operation(transaction_id, operation)
        
        logger.debug(f"Added operation {operation_id} to transaction {transaction_id}")
        return operation_id
    
    async def complete_operation(self, transaction_id: str, operation_id: str) -> None:
        """Mark operation as completed."""
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        operation = self._find_operation(transaction, operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")
        
        operation.state = OperationState.COMPLETED
        operation.completed_at = datetime.now()
        
        logger.debug(f"Completed operation {operation_id}")
    
    async def fail_operation(
        self,
        transaction_id: str,
        operation_id: str,
        error: str
    ) -> None:
        """Mark operation as failed."""
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        operation = self._find_operation(transaction, operation_id)
        if not operation:
            raise ValueError(f"Operation not found: {operation_id}")
        
        operation.state = OperationState.FAILED
        operation.error = error
        operation.completed_at = datetime.now()
        
        logger.warning(f"Failed operation {operation_id}: {error}")
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit transaction if all operations succeeded."""
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        # Check if all operations completed successfully
        if transaction.failed_operations:
            logger.warning(f"Cannot commit transaction with failed operations")
            return False
        
        try:
            # Commit PostgreSQL transactions
            await self.postgres_manager.commit_operation(transaction_id)
            
            transaction.state = TransactionState.COMMITTED
            logger.info(f"Committed transaction: {transaction_id}")
            
            # Clean up after successful commit
            await self._cleanup_transaction(transaction_id)
            return True
            
        except Exception as e:
            logger.error(f"Commit failed for transaction {transaction_id}: {e}")
            await self.rollback_transaction(transaction_id)
            return False
    
    async def rollback_transaction(self, transaction_id: str) -> None:
        """Rollback entire transaction with compensation."""
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            logger.warning(f"Rollback requested for unknown transaction: {transaction_id}")
            return
        
        logger.info(f"Rolling back transaction: {transaction_id}")
        
        try:
            # Rollback PostgreSQL operations
            await self.postgres_manager.rollback_operation(transaction_id)
            
            # Compensate completed operations in reverse order
            for operation in reversed(transaction.completed_operations):
                await self._compensate_operation(operation)
            
            transaction.state = TransactionState.ROLLED_BACK
            logger.info(f"Successfully rolled back transaction: {transaction_id}")
            
        except Exception as e:
            logger.error(f"Rollback failed for transaction {transaction_id}: {e}")
            transaction.state = TransactionState.FAILED
        
        finally:
            await self._cleanup_transaction(transaction_id)
    
    async def rollback_operation(self, operation_id: str) -> None:
        """Rollback specific operation across all transactions."""
        for transaction in self.active_transactions.values():
            operation = self._find_operation(transaction, operation_id)
            if operation:
                if operation.state == OperationState.COMPLETED:
                    await self._compensate_operation(operation)
                operation.state = OperationState.COMPENSATED
                logger.info(f"Rolled back operation: {operation_id}")
                return
        
        logger.warning(f"Operation not found for rollback: {operation_id}")
    
    async def _initialize_operation(
        self,
        transaction_id: str,
        operation: Operation
    ) -> None:
        """Initialize operation-specific resources."""
        if operation.operation_type in [
            OperationType.DATABASE_WRITE,
            OperationType.DATABASE_READ
        ]:
            await self.postgres_manager.begin_operation(
                transaction_id,
                operation.operation_id
            )
    
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
            try:
                await handler(operation)
                operation.state = OperationState.COMPENSATED
                logger.debug(f"Compensated operation: {operation.operation_id}")
            except Exception as e:
                logger.error(f"Compensation failed for {operation.operation_id}: {e}")
        else:
            logger.warning(f"No compensation handler for {operation.operation_type}")
    
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
            success = await self.commit_transaction(transaction_id)
            if not success:
                raise RuntimeError("Transaction commit failed")
        except Exception as e:
            await self.rollback_transaction(transaction_id)
            raise e


# Global transaction manager instance
transaction_manager = TransactionManager()