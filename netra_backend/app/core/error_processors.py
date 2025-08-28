"""Core exception processing logic and utilities - DEPRECATED

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

import warnings
from typing import Optional

from fastapi import Request

# Use unified error handler instead of deleted processors
from netra_backend.app.core.unified_error_handler import api_error_handler
from netra_backend.app.core.error_response import ErrorResponse

# Issue deprecation warning when this module is imported
warnings.warn(
    "netra_backend.app.core.error_processors is deprecated. "
    "Use netra_backend.app.core.unified_error_handler instead.",
    DeprecationWarning,
    stacklevel=2
)

# Backward compatibility alias
ErrorProcessor = api_error_handler

def process_exception(
    exc: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> ErrorResponse:
    """Convenient function to process exceptions using the unified error handler."""
    import asyncio
    return asyncio.run(api_error_handler.handle_exception(exc, request, trace_id))