"""Error handling modules for example message processing

Provides comprehensive error handling with recovery strategies,
user-friendly error messages, and business continuity measures.
"""

from netra_backend.app.error_handling.example_message_errors import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    RecoveryStrategy,
    get_error_handler,
    handle_example_message_error,
)

__all__ = [
    'handle_example_message_error',
    'get_error_handler',
    'ErrorContext',
    'ErrorCategory', 
    'ErrorSeverity',
    'RecoveryStrategy'
]