"""Main API error handler implementation.

Centralized error handling and logging utility for FastAPI applications.
"""

from typing import Optional

from fastapi import Request

from netra_backend.app.core.error_handlers.processors import ExceptionProcessor
from netra_backend.app.core.error_handlers.status_mapping import status_mapper
from netra_backend.app.core.exceptions import ErrorCode
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.transaction_manager.types import ErrorResponse

logger = central_logger.get_logger(__name__)


class ApiErrorHandler:
    """Centralized API error handling and logging utility for FastAPI."""
    
    def __init__(self):
        """Initialize API error handler."""
        self._processor = ExceptionProcessor()
        self._logger = logger
    
    def handle_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        trace_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle any exception and return standardized error response."""
        return self._processor.process_exception(exc, request, trace_id)
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        return status_mapper.get_status_code(error_code)


# Global error handler instance
api_error_handler = ApiErrorHandler()


def handle_exception(
    exc: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> ErrorResponse:
    """Convenient function to handle exceptions using the global handler."""
    return api_error_handler.handle_exception(exc, request, trace_id)


def get_http_status_code(error_code: ErrorCode) -> int:
    """Get HTTP status code for error code."""
    return api_error_handler.get_http_status_code(error_code)