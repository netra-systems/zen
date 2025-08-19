"""Error handling orchestration.

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

# Import from consolidated error handlers for backward compatibility
from app.core.error_handlers import ExecutionErrorHandler as ConsolidatedExecutionErrorHandler
from app.core.error_handlers import global_execution_error_handler

# Maintain the original interface
ExecutionErrorHandler = ConsolidatedExecutionErrorHandler

# Export the same interface for backward compatibility
__all__ = [
    'ExecutionErrorHandler',
    'global_execution_error_handler'
]