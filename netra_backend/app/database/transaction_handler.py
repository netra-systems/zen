"""Transaction Handler Module - Compatibility Layer

This module provides backward compatibility for transaction handling.
Aliases the existing TransactionManager from the db module.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

from netra_backend.app.db.transaction_manager import (
    TransactionManager,
    TransactionConfig,
    TransactionIsolationLevel,
    TransactionError,
    DeadlockError,
    ConnectionError,
    TransactionMetrics,
    transaction_manager,
    transactional,
    with_deadlock_retry,
    with_serializable_retry
)

# Create alias for backward compatibility
TransactionHandler = TransactionManager

# Re-export all functionality
__all__ = [
    'TransactionHandler',
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