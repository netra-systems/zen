"""Centralized error handling utilities and FastAPI exception handlers.

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

# Import from consolidated error handlers for backward compatibility
from netra_backend.app.core.error_handlers import (
    ApiErrorHandler,
    general_exception_handler,
    get_http_status_code,
    handle_exception,
    http_exception_handler,
    netra_exception_handler,
    validation_exception_handler,
)

# Maintain the original interface
__all__ = [
    'ApiErrorHandler',
    'handle_exception',
    'get_http_status_code',
    'netra_exception_handler',
    'validation_exception_handler',
    'http_exception_handler',
    'general_exception_handler'
]