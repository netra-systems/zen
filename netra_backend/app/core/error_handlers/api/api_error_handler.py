"""Centralized API error handling for FastAPI applications.

Provides consistent error response formatting and routing to specialized handlers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.core.error_handlers.api.exception_router import ExceptionRouter
from netra_backend.app.core.error_handlers.api.response_builder import (
    ErrorResponseBuilder,
)
from netra_backend.app.core.error_handlers.base_error_handler import BaseErrorHandler
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.core.exceptions import ErrorCode, ErrorSeverity, NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ApiErrorHandler(BaseErrorHandler):
    """Centralized API error handling and logging utility for FastAPI."""
    
    def __init__(self):
        """Initialize API error handler with specialized components."""
        super().__init__()
        self._logger = central_logger.get_logger(__name__)
        self._response_builder = ErrorResponseBuilder(self._logger)
        self._exception_router = ExceptionRouter(self._logger, self._response_builder)
    
    async def handle_error(
        self,
        exc: Exception,
        context: Optional[Request] = None,
        **kwargs
    ) -> ErrorResponse:
        """Handle API exception and return standardized error response."""
        trace_id = kwargs.get('trace_id') or str(uuid4())
        return self._process_exception_with_context(exc, context, trace_id)
    
    def handle_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        trace_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle any exception and return standardized error response."""
        prepared_trace_id = trace_id or str(uuid4())
        return self._process_exception_with_context(exc, request, prepared_trace_id)
    
    def _process_exception_with_context(
        self, 
        exc: Exception, 
        request: Optional[Request], 
        trace_id: str
    ) -> ErrorResponse:
        """Process exception with trace ID and request context."""
        request_id = self._extract_request_id(request)
        return self._exception_router.route_exception(exc, trace_id, request_id)
    
    def _extract_request_id(self, request: Optional[Request]) -> Optional[str]:
        """Extract request ID from request state if available."""
        if request and hasattr(request.state, 'request_id'):
            return request.state.request_id
        return None
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        return self._exception_router.get_http_status_code(error_code)
    
    def _handle_pydantic_validation_error(
        self,
        exc: ValidationError,
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
        exc: SQLAlchemyError,
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
    
    def _handle_http_exception(
        self,
        exc: HTTPException,
        trace_id: str,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle HTTP exceptions."""
        # Map 404 status to DB_RECORD_NOT_FOUND for compatibility
        error_code = "DB_RECORD_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return ErrorResponse(
            error_code=error_code,
            message=exc.detail or "HTTP error occurred",
            user_message="A server error occurred",
            details={"status_code": exc.status_code},
            trace_id=trace_id,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _handle_unknown_exception(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle unknown/generic exceptions."""
        return ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An internal server error occurred",
            user_message="A server error occurred",
            details={"exception_type": type(exc).__name__, "error": str(exc)},
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