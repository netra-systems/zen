"""Transaction manager package for distributed transaction management.

Provides all transaction management functionality through a modular architecture
with support for PostgreSQL and ClickHouse operations.
"""

from .types import (
    TransactionState,
    OperationState,
    Operation,
    Transaction
)
from .compensation import (
    CompensationRegistry,
    CompensationExecutor,
    DefaultHandlers,
    create_compensation_system
)
from .postgres_ops import PostgresOperationManager
from .clickhouse_ops import ClickHouseOperationManager
from .manager import TransactionManager

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