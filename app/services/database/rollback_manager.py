"""Database rollback manager - Backward compatibility module.

This module provides backward compatibility by re-exporting all classes
and functions from the split rollback manager modules.
"""

# Import core components
from .rollback_manager_core import (
    RollbackState,
    DependencyType,
    RollbackOperation,
    RollbackSession,
    RollbackManager,
    rollback_manager
)

# Import transaction executors
from .rollback_manager_transactions import (
    PostgresRollbackExecutor,
    ClickHouseRollbackExecutor
)

# Import recovery components
from .rollback_manager_recovery import (
    DependencyResolver
)

# Import execution components
from .rollback_manager_execution import (
    BatchExecutor
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