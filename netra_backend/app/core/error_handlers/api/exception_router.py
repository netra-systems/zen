"""Exception routing to appropriate handlers.

Routes exceptions to specialized handlers based on exception type.
"""

from typing import Dict, Optional, Callable

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.core.exceptions import NetraException, ErrorCode
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.core.error_handlers_status_mapping import StatusCodeMapper
from netra_backend.app.response_builder import ErrorResponseBuilder


class ExceptionRouter:
    """Routes exceptions to appropriate handlers."""
    
    def __init__(self, logger, response_builder: ErrorResponseBuilder):
        """Initialize exception router."""
        self._logger = logger
        self._response_builder = response_builder
        self._status_mapper = StatusCodeMapper()
        self._handler_map = self._build_handler_map()
    
    def _build_handler_map(self) -> Dict[type, Callable]:
        """Build exception handler mapping."""
        return {
            NetraException: self._handle_netra_exception,
            ValidationError: self._handle_validation_exception,
            SQLAlchemyError: self._handle_database_exception,
            HTTPException: self._handle_http_exception,
        }
    
    def route_exception(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Route exception to appropriate handler."""
        handler = self._find_handler(exc)
        return handler(exc, trace_id, request_id)
    
    def _find_handler(self, exc: Exception) -> Callable:
        """Find appropriate handler for exception type."""
        for exc_type, handler in self._handler_map.items():
            if isinstance(exc, exc_type):
                return handler
        return self._handle_unknown_exception
    
    def _handle_netra_exception(
        self,
        exc: NetraException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle custom Netra exceptions."""
        return self._response_builder.build_netra_response(exc, trace_id, request_id)
    
    def _handle_validation_exception(
        self,
        exc: ValidationError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle validation errors."""
        return self._response_builder.build_validation_response(exc, trace_id, request_id)
    
    def _handle_database_exception(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle database errors."""
        return self._response_builder.build_database_response(exc, trace_id, request_id)
    
    def _handle_http_exception(
        self,
        exc: HTTPException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle HTTP exceptions."""
        return self._response_builder.build_http_response(exc, trace_id, request_id)
    
    def _handle_unknown_exception(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle unknown exceptions."""
        return self._response_builder.build_unknown_response(exc, trace_id, request_id)
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        return self._status_mapper.get_http_status_code(error_code)