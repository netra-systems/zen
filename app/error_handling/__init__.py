"""Error handling modules for example message processing

Provides comprehensive error handling with recovery strategies,
user-friendly error messages, and business continuity measures.
"""

from .example_message_errors import (
    handle_example_message_error,
    get_error_handler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy
)

__all__ = [
    'handle_example_message_error',
    'get_error_handler',
    'ErrorContext',
    'ErrorCategory', 
    'ErrorSeverity',
    'RecoveryStrategy'
]