"""Core exception processing logic and utilities - DEPRECATED

DEPRECATED: This module has been replaced by the consolidated error handlers
in app.core.error_handlers. This file now provides backward compatibility.
"""

import warnings
from typing import Optional

from fastapi import Request

from netra_backend.app.core.error_handlers.processors import (
    ExceptionProcessor as CanonicalExceptionProcessor,
)
from netra_backend.app.core.error_response import ErrorResponse

# Issue deprecation warning when this module is imported
warnings.warn(
    "netra_backend.app.core.error_processors is deprecated. "
    "Use netra_backend.app.core.error_handlers.processors.ExceptionProcessor instead.",
    DeprecationWarning,
    stacklevel=2
)

# Backward compatibility alias
ErrorProcessor = CanonicalExceptionProcessor

# Global processor instance for backward compatibility
_error_processor = CanonicalExceptionProcessor()

def process_exception(
    exc: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> ErrorResponse:
    """Convenient function to process exceptions using the canonical processor."""
    return _error_processor.process_exception(exc, request, trace_id)