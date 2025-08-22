"""Database rollback manager - Backward compatibility module.

This module provides backward compatibility by re-exporting all classes
and functions from the split rollback manager modules.
"""

# Import core components
from netra_backend.app.services.database.rollback_manager_core import (
    DependencyType,
    RollbackManager,
    RollbackOperation,
    RollbackSession,
    RollbackState,
    rollback_manager,
)

# Import execution components
from netra_backend.app.services.database.rollback_manager_execution import BatchExecutor

# Import recovery components
from netra_backend.app.services.database.rollback_manager_recovery import (
    DependencyResolver,
)

# Import transaction executors
from netra_backend.app.services.database.rollback_manager_transactions import (
    ClickHouseRollbackExecutor,
    PostgresRollbackExecutor,
)

# Re-export everything for backward compatibility
__all__ = [
    'RollbackState',
    'DependencyType', 
    'RollbackOperation',
    'RollbackSession',
    'RollbackManager',
    'rollback_manager',
    'PostgresRollbackExecutor',
    'ClickHouseRollbackExecutor',
    'DependencyResolver',
    'BatchExecutor'
]