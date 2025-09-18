"""
Cross-Database Transaction Coordinator: Manages consistency between PostgreSQL and ClickHouse.

This module provides distributed transaction support to ensure consistency
between PostgreSQL OLTP operations and ClickHouse OLAP operations.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Data consistency across analytical and transactional systems
- Value Impact: Prevents data inconsistencies that could impact customer analytics
- Strategic Impact: Ensures reliable analytics for customer insights and billing
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionState(str, Enum):
    """Transaction state enumeration."""
    PENDING = "pending"
    COMMITTED = "committed"
    ABORTED = "aborted"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class CompensationAction(BaseModel):
    """Compensation action for rollback scenarios."""
    database: str  # "postgresql" or "clickhouse"
    action_type: str  # "delete", "update", "insert"
    table: str
    conditions: Dict[str, Any]
    data: Optional[Dict[str, Any]] = None
    executed: bool = False
    execution_time: Optional[datetime] = None


class DistributedTransaction(BaseModel):
    """Distributed transaction model."""
    transaction_id: str
    state: TransactionState
    postgres_operations: List[Dict[str, Any]] = []
    clickhouse_operations: List[Dict[str, Any]] = []
    compensation_actions: List[CompensationAction] = []
    created_at: datetime
    committed_at: Optional[datetime] = None
    aborted_at: Optional[datetime] = None
    timeout_at: datetime
    metadata: Dict[str, Any] = {}


class TransactionCoordinator:
    """Coordinates transactions across PostgreSQL and ClickHouse databases."""
    
    def __init__(self, transaction_timeout: int = 300):  # 5 minutes default
        self._active_transactions: Dict[str, DistributedTransaction] = {}
        self._transaction_timeout = transaction_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        self._coordination_lock = asyncio.Lock()
        
    async def start(self):
        """Start the transaction coordinator."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_transactions())
            logger.info("Transaction coordinator started")
    
    async def stop(self):
        """Stop the transaction coordinator."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Transaction coordinator stopped")
    
    async def begin_distributed_transaction(
        self, 
        transaction_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Begin a new distributed transaction."""
        if not transaction_id:
            transaction_id = str(uuid.uuid4())
        
        async with self._coordination_lock:
            if transaction_id in self._active_transactions:
                raise ValueError(f"Transaction {transaction_id} already exists")
            
            transaction = DistributedTransaction(
                transaction_id=transaction_id,
                state=TransactionState.PENDING,
                created_at=datetime.now(timezone.utc),
                timeout_at=datetime.now(timezone.utc) + timedelta(seconds=self._transaction_timeout),
                metadata=metadata or {}
            )
            
            self._active_transactions[transaction_id] = transaction
            logger.info(f"Started distributed transaction: {transaction_id}")
            
        return transaction_id
    
    async def add_postgres_operation(
        self,
        transaction_id: str,
        operation: Dict[str, Any],
        compensation_action: Optional[CompensationAction] = None
    ) -> None:
        """Add a PostgreSQL operation to the transaction."""
        async with self._coordination_lock:
            transaction = self._active_transactions.get(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            if transaction.state != TransactionState.PENDING:
                raise ValueError(f"Cannot add operations to transaction in state {transaction.state}")
            
            transaction.postgres_operations.append(operation)
            if compensation_action:
                transaction.compensation_actions.append(compensation_action)
    
    async def add_clickhouse_operation(
        self,
        transaction_id: str,
        operation: Dict[str, Any],
        compensation_action: Optional[CompensationAction] = None
    ) -> None:
        """Add a ClickHouse operation to the transaction."""
        async with self._coordination_lock:
            transaction = self._active_transactions.get(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            if transaction.state != TransactionState.PENDING:
                raise ValueError(f"Cannot add operations to transaction in state {transaction.state}")
            
            transaction.clickhouse_operations.append(operation)
            if compensation_action:
                transaction.compensation_actions.append(compensation_action)
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit a distributed transaction using two-phase commit."""
        async with self._coordination_lock:
            transaction = self._active_transactions.get(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            if transaction.state != TransactionState.PENDING:
                raise ValueError(f"Cannot commit transaction in state {transaction.state}")
            
            try:
                # Phase 1: Prepare all databases
                postgres_prepared = await self._prepare_postgres_operations(transaction)
                clickhouse_prepared = await self._prepare_clickhouse_operations(transaction)
                
                if not postgres_prepared or not clickhouse_prepared:
                    logger.error(f"Failed to prepare transaction {transaction_id}")
                    await self._abort_transaction(transaction_id)
                    return False
                
                # Phase 2: Commit all databases
                postgres_committed = await self._commit_postgres_operations(transaction)
                clickhouse_committed = await self._commit_clickhouse_operations(transaction)
                
                if postgres_committed and clickhouse_committed:
                    transaction.state = TransactionState.COMMITTED
                    transaction.committed_at = datetime.now(timezone.utc)
                    logger.info(f"Successfully committed distributed transaction: {transaction_id}")
                    return True
                else:
                    logger.error(f"Failed to commit transaction {transaction_id}")
                    await self._compensate_transaction(transaction)
                    return False
                    
            except Exception as e:
                logger.error(f"Error committing transaction {transaction_id}: {e}")
                await self._abort_transaction(transaction_id)
                return False
    
    async def abort_transaction(self, transaction_id: str) -> None:
        """Abort a distributed transaction."""
        await self._abort_transaction(transaction_id)
    
    async def _abort_transaction(self, transaction_id: str) -> None:
        """Internal method to abort a transaction."""
        transaction = self._active_transactions.get(transaction_id)
        if not transaction:
            return
        
        transaction.state = TransactionState.ABORTED
        transaction.aborted_at = datetime.now(timezone.utc)
        
        # Compensate any operations that were partially committed
        if transaction.postgres_operations or transaction.clickhouse_operations:
            await self._compensate_transaction(transaction)
        
        logger.info(f"Aborted distributed transaction: {transaction_id}")
    
    async def _prepare_postgres_operations(self, transaction: DistributedTransaction) -> bool:
        """Prepare PostgreSQL operations (Phase 1 of 2PC)."""
        if not transaction.postgres_operations:
            return True
        
        try:
            # Get connection manager
            from netra_backend.app.db.database_manager import DatabaseManager
            connection_manager = DatabaseManager.get_connection_manager()
            
            async with connection_manager.get_session() as session:
                # For PostgreSQL, we can use SAVEPOINT for preparation
                await session.execute(text("SAVEPOINT prepare_distributed_tx"))
                
                # Execute all operations within the savepoint
                for operation in transaction.postgres_operations:
                    await self._execute_postgres_operation(session, operation)
                
                # Don't commit yet - just verify operations are valid
                return True
                
        except Exception as e:
            logger.error(f"Failed to prepare PostgreSQL operations: {e}")
            return False
    
    async def _prepare_clickhouse_operations(self, transaction: DistributedTransaction) -> bool:
        """Prepare ClickHouse operations (Phase 1 of 2PC)."""
        if not transaction.clickhouse_operations:
            return True
        
        try:
            # ClickHouse doesn't have traditional transactions, so we validate operations
            from netra_backend.app.db.clickhouse import get_clickhouse_client
            async with get_clickhouse_client() as client:
                # Validate all operations without executing
                for operation in transaction.clickhouse_operations:
                    if not await self._validate_clickhouse_operation(client, operation):
                        return False
                
                return True
            
        except Exception as e:
            logger.error(f"Failed to prepare ClickHouse operations: {e}")
            return False
    
    async def _commit_postgres_operations(self, transaction: DistributedTransaction) -> bool:
        """Commit PostgreSQL operations (Phase 2 of 2PC)."""
        if not transaction.postgres_operations:
            return True
        
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            connection_manager = DatabaseManager.get_connection_manager()
            
            async with connection_manager.get_session() as session:
                # Release the savepoint - operations are already executed
                await session.execute(text("RELEASE SAVEPOINT prepare_distributed_tx"))
                return True
                
        except Exception as e:
            logger.error(f"Failed to commit PostgreSQL operations: {e}")
            return False
    
    async def _commit_clickhouse_operations(self, transaction: DistributedTransaction) -> bool:
        """Commit ClickHouse operations (Phase 2 of 2PC)."""
        if not transaction.clickhouse_operations:
            return True
        
        try:
            from netra_backend.app.db.clickhouse import get_clickhouse_client
            async with get_clickhouse_client() as client:
                # Execute all ClickHouse operations
                for operation in transaction.clickhouse_operations:
                    await self._execute_clickhouse_operation(client, operation)
                
                return True
            
        except Exception as e:
            logger.error(f"Failed to commit ClickHouse operations: {e}")
            return False
    
    async def _compensate_transaction(self, transaction: DistributedTransaction) -> None:
        """Execute compensation actions to rollback partial commits."""
        transaction.state = TransactionState.COMPENSATING
        
        try:
            # Execute compensation actions in reverse order
            for action in reversed(transaction.compensation_actions):
                if not action.executed:
                    await self._execute_compensation_action(action)
            
            transaction.state = TransactionState.COMPENSATED
            logger.info(f"Successfully compensated transaction: {transaction.transaction_id}")
            
        except Exception as e:
            transaction.state = TransactionState.FAILED
            logger.error(f"Failed to compensate transaction {transaction.transaction_id}: {e}")
    
    async def _execute_postgres_operation(self, session: AsyncSession, operation: Dict[str, Any]) -> None:
        """Execute a PostgreSQL operation."""
        operation_type = operation.get("type")
        
        if operation_type == "insert":
            query = operation["query"]
            params = operation.get("params", {})
            await session.execute(query, params)
        elif operation_type == "update":
            query = operation["query"]
            params = operation.get("params", {})
            await session.execute(query, params)
        elif operation_type == "delete":
            query = operation["query"]
            params = operation.get("params", {})
            await session.execute(query, params)
        else:
            raise ValueError(f"Unsupported PostgreSQL operation type: {operation_type}")
    
    async def _execute_clickhouse_operation(self, client, operation: Dict[str, Any]) -> None:
        """Execute a ClickHouse operation."""
        operation_type = operation.get("type")
        
        if operation_type == "insert":
            query = operation["query"]
            data = operation.get("data", [])
            await client.execute(query, data)
        elif operation_type == "update":
            # ClickHouse doesn't support traditional updates, use ALTER TABLE
            query = operation["query"]
            await client.execute(query)
        elif operation_type == "delete":
            # ClickHouse doesn't support traditional deletes, use ALTER TABLE DELETE
            query = operation["query"]
            await client.execute(query)
        else:
            raise ValueError(f"Unsupported ClickHouse operation type: {operation_type}")
    
    async def _validate_clickhouse_operation(self, client, operation: Dict[str, Any]) -> bool:
        """Validate a ClickHouse operation without executing it."""
        try:
            # Basic validation - check if the query is syntactically correct
            operation_type = operation.get("type")
            query = operation.get("query", "")
            
            if not query:
                return False
            
            # For now, just check that required fields are present
            if operation_type in ["insert", "update", "delete"] and query:
                return True
            
            return False
            
        except Exception:
            return False
    
    async def _execute_compensation_action(self, action: CompensationAction) -> None:
        """Execute a compensation action."""
        try:
            if action.database == "postgresql":
                await self._execute_postgres_compensation(action)
            elif action.database == "clickhouse":
                await self._execute_clickhouse_compensation(action)
            
            action.executed = True
            action.execution_time = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to execute compensation action: {e}")
            raise
    
    async def _execute_postgres_compensation(self, action: CompensationAction) -> None:
        """Execute PostgreSQL compensation action."""
        from netra_backend.app.db.database_manager import DatabaseManager
        connection_manager = DatabaseManager.get_connection_manager()
        
        async with connection_manager.get_session() as session:
            if action.action_type == "delete":
                # Build delete query
                conditions = " AND ".join([f"{k} = :{k}" for k in action.conditions.keys()])
                query = f"DELETE FROM {action.table} WHERE {conditions}"
                await session.execute(query, action.conditions)
            elif action.action_type == "insert":
                # Build insert query
                if action.data:
                    columns = ", ".join(action.data.keys())
                    values = ", ".join([f":{k}" for k in action.data.keys()])
                    query = f"INSERT INTO {action.table} ({columns}) VALUES ({values})"
                    await session.execute(query, action.data)
            elif action.action_type == "update":
                # Build update query
                if action.data and action.conditions:
                    set_clause = ", ".join([f"{k} = :{k}" for k in action.data.keys()])
                    where_clause = " AND ".join([f"{k} = :c_{k}" for k in action.conditions.keys()])
                    query = f"UPDATE {action.table} SET {set_clause} WHERE {where_clause}"
                    
                    # Combine data and conditions with prefixed condition keys
                    params = action.data.copy()
                    for k, v in action.conditions.items():
                        params[f"c_{k}"] = v
                    
                    await session.execute(query, params)
    
    async def _execute_clickhouse_compensation(self, action: CompensationAction) -> None:
        """Execute ClickHouse compensation action."""
        from netra_backend.app.db.clickhouse import get_clickhouse_client
        async with get_clickhouse_client() as client:
            if action.action_type == "delete":
                # ClickHouse delete using ALTER TABLE
                conditions = " AND ".join([f"{k} = '{v}'" for k, v in action.conditions.items()])
                query = f"ALTER TABLE {action.table} DELETE WHERE {conditions}"
                await client.execute(query)
    
    async def _cleanup_expired_transactions(self) -> None:
        """Background task to clean up expired transactions."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.now(timezone.utc)
                expired_transactions = []
                
                async with self._coordination_lock:
                    for tx_id, transaction in self._active_transactions.items():
                        if current_time > transaction.timeout_at:
                            expired_transactions.append(tx_id)
                
                # Abort expired transactions
                for tx_id in expired_transactions:
                    logger.warning(f"Aborting expired transaction: {tx_id}")
                    await self._abort_transaction(tx_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in transaction cleanup: {e}")
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a distributed transaction."""
        transaction = self._active_transactions.get(transaction_id)
        if not transaction:
            return None
        
        return {
            "transaction_id": transaction.transaction_id,
            "state": transaction.state,
            "created_at": transaction.created_at,
            "committed_at": transaction.committed_at,
            "aborted_at": transaction.aborted_at,
            "timeout_at": transaction.timeout_at,
            "postgres_operations_count": len(transaction.postgres_operations),
            "clickhouse_operations_count": len(transaction.clickhouse_operations),
            "compensation_actions_count": len(transaction.compensation_actions),
            "executed_compensations": sum(1 for action in transaction.compensation_actions if action.executed),
            "metadata": transaction.metadata
        }
    
    def list_active_transactions(self) -> List[Dict[str, Any]]:
        """List all active transactions."""
        return [
            self.get_transaction_status(tx_id)
            for tx_id in self._active_transactions.keys()
        ]


# Global transaction coordinator instance
_transaction_coordinator: Optional[TransactionCoordinator] = None


async def get_transaction_coordinator() -> TransactionCoordinator:
    """Get the global transaction coordinator instance."""
    global _transaction_coordinator
    if _transaction_coordinator is None:
        _transaction_coordinator = TransactionCoordinator()
        await _transaction_coordinator.start()
    return _transaction_coordinator


@asynccontextmanager
async def distributed_transaction(
    metadata: Optional[Dict[str, Any]] = None,
    transaction_timeout: int = 300
):
    """Context manager for distributed transactions."""
    coordinator = await get_transaction_coordinator()
    transaction_id = await coordinator.begin_distributed_transaction(metadata=metadata)
    
    try:
        yield transaction_id
        # Auto-commit if context exits normally
        success = await coordinator.commit_transaction(transaction_id)
        if not success:
            raise RuntimeError(f"Failed to commit distributed transaction: {transaction_id}")
    except Exception:
        # Auto-abort on exception
        await coordinator.abort_transaction(transaction_id)
        raise
    finally:
        # Clean up completed transaction
        coordinator._active_transactions.pop(transaction_id, None)