"""Transaction Manager with Retry Logic and Best Practices

Main module that imports and exposes functionality from focused sub-modules.
Maintains backward compatibility while adhering to modular architecture.
"""

# Import core transaction functionality
from netra_backend.app.db.transaction_core import (
    TransactionConfig,
    TransactionIsolationLevel,
    TransactionManager,
    transaction_manager,
    transactional,
    with_deadlock_retry,
    with_serializable_retry,
)

# Import error handling
from netra_backend.app.db.transaction_errors import (
    ConnectionError,
    DeadlockError,
    TransactionError,
)

# Import statistics
from netra_backend.app.db.transaction_stats import TransactionMetrics

# Re-export all functionality for backward compatibility
__all__ = [
    'TransactionManager',
    'TransactionConfig',
    'TransactionIsolationLevel',
    'TransactionError',
    'DeadlockError',
    'ConnectionError',
    'TransactionMetrics',
    'transaction_manager',
    'transactional',
    'with_deadlock_retry',
    'with_serializable_retry'
]