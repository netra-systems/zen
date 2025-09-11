"""UserExecutionContext SSOT Re-export Module

DEPRECATION NOTICE: This module is deprecated in favor of the SSOT implementation.

This module now re-exports the authoritative UserExecutionContext from 
netra_backend.app.services.user_execution_context to maintain backward compatibility
while consolidating to a Single Source of Truth.

All new code should import directly from:
from netra_backend.app.services.user_execution_context import UserExecutionContext

This re-export will be removed in a future version after migration is complete.
"""

import warnings
from netra_backend.app.logging_config import central_logger

# Import SSOT implementation and re-export for backward compatibility
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    UserContextManager,
    validate_user_context,
    managed_user_context,
    create_isolated_execution_context,
    register_shared_object,
    clear_shared_object_registry
)

# Backward compatibility alias
clear_shared_objects = clear_shared_object_registry

logger = central_logger.get_logger(__name__)

# Issue deprecation warning for imports from this module
warnings.warn(
    "netra_backend.app.agents.supervisor.user_execution_context is deprecated. "
    "Use netra_backend.app.services.user_execution_context instead. "
    "This module will be removed after migration is complete.",
    DeprecationWarning,
    stacklevel=2
)

logger.debug(
    "SSOT CONSOLIDATION: UserExecutionContext re-exported from services.user_execution_context. "
    "Consider migrating imports to the SSOT path."
)

# Export all symbols for backward compatibility
__all__ = [
    'UserExecutionContext',
    'InvalidContextError', 
    'ContextIsolationError',
    'UserContextManager',
    'validate_user_context',
    'managed_user_context',
    'create_isolated_execution_context'
]