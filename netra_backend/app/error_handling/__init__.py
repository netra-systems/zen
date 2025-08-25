"""Error handling modules for example message processing

Provides comprehensive error handling with recovery strategies,
user-friendly error messages, and business continuity measures.
"""

from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.unified_error_handler import RecoveryStrategy, handle_error

# Compatibility functions
def get_error_handler():
    """Get unified error handler instance."""
    from netra_backend.app.core.unified_error_handler import _unified_error_handler
    return _unified_error_handler

async def handle_example_message_error(error, context=None, **kwargs):
    """Handle example message error via unified handler."""
    return await handle_error(error, context, **kwargs)

__all__ = [
    'handle_example_message_error',
    'get_error_handler',
    'ErrorContext',
    'ErrorCategory', 
    'ErrorSeverity',
    'RecoveryStrategy'
]