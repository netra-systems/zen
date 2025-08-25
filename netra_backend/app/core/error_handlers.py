"""DEPRECATED: Centralized error handling utilities and FastAPI exception handlers.

DEPRECATED: This module has been replaced by the unified error handler.
All error handling is now consolidated into app.core.unified_error_handler.

This file provides backward compatibility only.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "netra_backend.app.core.error_handlers is deprecated. "
    "Use netra_backend.app.core.unified_error_handler instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from unified error handler for backward compatibility
from netra_backend.app.core.unified_error_handler import (
    api_error_handler as ApiErrorHandler,
    api_error_handler,
    handle_exception,
    get_http_status_code,
    general_exception_handler,
    http_exception_handler,
    netra_exception_handler,
    validation_exception_handler,
    global_agent_error_handler,
    agent_error_handler as AgentErrorHandler,
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