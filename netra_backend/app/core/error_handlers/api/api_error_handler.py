"""Centralized API error handling for FastAPI applications.

Provides consistent error response formatting and routing to specialized handlers.
"""

from typing import Dict, Any, Optional, Union
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.exceptions import NetraException, ErrorCode, ErrorSeverity
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app..base_error_handler import BaseErrorHandler
from netra_backend.app.response_builder import ErrorResponseBuilder
from netra_backend.app.exception_router import ExceptionRouter

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