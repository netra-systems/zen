"""Transaction manager package for distributed transaction management.

Provides all transaction management functionality through a modular architecture
with support for PostgreSQL and ClickHouse operations.
"""

from netra_backend.app.services.transaction_manager.types import (
    TransactionState,
    OperationState,
    Operation,
    Transaction
)
from netra_backend.app.services.transaction_manager.compensation import (
    CompensationRegistry,
    CompensationExecutor,
    DefaultHandlers,
    create_compensation_system
)
from netra_backend.app.services.transaction_manager.postgres_ops import PostgresOperationManager
from netra_backend.app.services.transaction_manager.clickhouse_ops import ClickHouseOperationManager
from netra_backend.app.services.transaction_manager.manager import TransactionManager

# Global transaction manager instance for backward compatibility
transaction_manager = TransactionManager()

__all__ = [
    'TransactionState',
    'OperationState', 
    'Operation',
    'Transaction',
    'CompensationRegistry',
    'CompensationExecutor',
    'DefaultHandlers',
    'create_compensation_system',
    'PostgresOperationManager',
    'ClickHouseOperationManager',
    'TransactionManager',
    'transaction_manager'
]