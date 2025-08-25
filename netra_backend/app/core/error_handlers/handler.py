"""Main API error handler implementation.

Centralized error handling and logging utility for FastAPI applications.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError

from netra_backend.app.core.error_handlers.processors import ExceptionProcessor
from netra_backend.app.core.error_handlers.status_mapping import status_mapper
from netra_backend.app.core.exceptions import ErrorCode
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.logging_config import central_logger

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
    
    def _handle_pydantic_validation_error(
        self,
        exc: PydanticValidationError,
        trace_id: str,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle Pydantic validation errors."""
        validation_errors = []
        if hasattr(exc, 'errors') and callable(exc.errors):
            for error in exc.errors():
                validation_errors.append({
                    "field": ".".join(str(loc) for loc in error.get("loc", [])),
                    "message": error.get("msg", "Validation error"),
                    "type": error.get("type", "value_error")
                })
        
        return ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            user_message="The provided data is invalid",
            details={"validation_errors": validation_errors},
            trace_id=trace_id,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _handle_sqlalchemy_error(
        self,
        exc: IntegrityError,
        trace_id: str,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle SQLAlchemy integrity constraint errors."""
        return ErrorResponse(
            error_code="DB_CONSTRAINT_VIOLATION",
            message="Database constraint violation occurred",
            user_message="The operation failed due to data constraints",
            details={"original_error": str(exc)},
            trace_id=trace_id,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


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