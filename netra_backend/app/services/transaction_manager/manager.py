"""Core transaction manager implementation.

Orchestrates distributed transactions across multiple data stores
with automatic rollback and compensation mechanisms.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional

from app.core.error_recovery import OperationType
from app.logging_config import central_logger

from netra_backend.app.types import Transaction, Operation, TransactionState, OperationState
from netra_backend.app.compensation import create_compensation_system, CompensationExecutor
from netra_backend.app.postgres_ops import PostgresOperationManager
from netra_backend.app.clickhouse_ops import ClickHouseOperationManager

logger = central_logger.get_logger(__name__)


class TransactionManager:
    """Manages distributed transactions across multiple data stores."""
    
    def __init__(self):
        """Initialize transaction manager."""
        self.active_transactions: Dict[str, Transaction] = {}
        self.compensation_registry, self.compensation_executor = create_compensation_system()
        self.postgres_manager = PostgresOperationManager()
        self.clickhouse_manager = ClickHouseOperationManager()
    
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
    
    def _validate_transaction_exists(self, transaction_id: str) -> None:
        """Validate transaction exists in active transactions."""
        if transaction_id not in self.active_transactions:
            raise ValueError(f"Transaction not found: {transaction_id}")
    
    def _create_and_add_operation(
        self, transaction_id: str, operation_type: OperationType, metadata: Optional[Dict]
    ) -> Operation:
        """Create new operation and add to transaction."""
        operation = self._create_new_operation(operation_type, metadata)
        transaction = self.active_transactions[transaction_id]
        transaction.operations.append(operation)
        return operation
    
    def _create_new_operation(self, operation_type: OperationType, metadata: Optional[Dict]) -> Operation:
        """Create new operation instance."""
        return Operation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_type,
            metadata=metadata or {}
        )
    
    async def _initialize_operation(self, transaction_id: str, operation: Operation) -> None:
        """Initialize operation-specific resources."""
        if self._is_database_operation(operation):
            await self.postgres_manager.begin_operation(transaction_id, operation.operation_id)
    
    def _is_database_operation(self, operation: Operation) -> bool:
        """Check if operation requires database initialization."""
        return operation.operation_type in [
            OperationType.DATABASE_WRITE,
            OperationType.DATABASE_READ
        ]
    
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
        operation.completed_at = None  # Will be set by property
    
    async def fail_operation(
        self, transaction_id: str, operation_id: str, error: str
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
        operation.completed_at = None  # Will be set by property
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit transaction if all operations succeeded."""
        transaction = self._get_transaction(transaction_id)
        if not self._can_commit_transaction(transaction):
            return False
        return await self._attempt_commit(transaction_id)
    
    def _can_commit_transaction(self, transaction: Transaction) -> bool:
        """Check if transaction can be committed."""
        if transaction.failed_operations:
            logger.warning("Cannot commit transaction with failed operations")
            return False
        return True
    
    async def _attempt_commit(self, transaction_id: str) -> bool:
        """Attempt to commit transaction with error handling."""
        try:
            await self._execute_commit(transaction_id)
            return True
        except Exception as e:
            logger.error(f"Commit failed for transaction {transaction_id}: {e}")
            await self.rollback_transaction(transaction_id)
            return False
    
    async def _execute_commit(self, transaction_id: str) -> None:
        """Execute transaction commit."""
        await self.postgres_manager.commit_operation(transaction_id)
        self._update_transaction_state(transaction_id, TransactionState.COMMITTED)
        logger.info(f"Committed transaction: {transaction_id}")
        await self._cleanup_transaction(transaction_id)
    
    def _update_transaction_state(self, transaction_id: str, state: TransactionState) -> None:
        """Update transaction state."""
        transaction = self.active_transactions[transaction_id]
        transaction.state = state
    
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
            await self.compensation_executor.compensate_operation(operation)
    
    def _find_operation(self, transaction: Transaction, operation_id: str) -> Optional[Operation]:
        """Find operation within transaction."""
        for operation in transaction.operations:
            if operation.operation_id == operation_id:
                return operation
        return None
    
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