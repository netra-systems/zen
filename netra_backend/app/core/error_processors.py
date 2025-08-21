"""Core exception processing logic and utilities."""

from typing import Dict, Optional, Union
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import Request

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.error_response_models import ErrorResponse
from netra_backend.app.exceptions import NetraException, ErrorSeverity
from netra_backend.app.error_handlers_netra import NetraExceptionHandler
from netra_backend.app.error_handlers_validation import ValidationErrorHandler
from netra_backend.app.error_handlers_database import DatabaseErrorHandler
from netra_backend.app.error_handlers_http import HttpExceptionHandler


class ErrorProcessor:
    """Core exception processor that routes to specialized handlers."""
    
    def __init__(self):
        self._logger = central_logger.get_logger(__name__)
        self._init_handlers()
    
    def _init_handlers(self) -> None:
        """Initialize specialized error handlers."""
        self._netra_handler = NetraExceptionHandler(self._logger)
        self._validation_handler = ValidationErrorHandler(self._logger)
        self._database_handler = DatabaseErrorHandler(self._logger)
        self._http_handler = HttpExceptionHandler(self._logger)
    
    def process_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        trace_id: Optional[str] = None
    ) -> ErrorResponse:
        """Process any exception and return standardized error response."""
        return self._process_exception_with_context(exc, request, trace_id)
    
    def _process_exception_with_context(
        self, 
        exc: Exception, 
        request: Optional[Request], 
        trace_id: Optional[str]
    ) -> ErrorResponse:
        """Process exception with trace ID and request context."""
        prepared_trace_id = self._prepare_trace_id(trace_id)
        request_id = self._extract_request_id(request)
        return self._route_to_handler(exc, prepared_trace_id, request_id)
    
    def _prepare_trace_id(self, trace_id: Optional[str]) -> str:
        """Prepare trace ID for exception handling."""
        return trace_id if trace_id is not None else str(uuid4())
    
    def _extract_request_id(self, request: Optional[Request]) -> Optional[str]:
        """Extract request ID from request state if available."""
        if request and hasattr(request.state, 'request_id'):
            return request.state.request_id
        return None
    
    def _route_to_handler(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Route exception to appropriate specialized handler."""
        handler = self._find_handler_for_exception(exc)
        return handler.handle(exc, trace_id, request_id)
    
    def _find_handler_for_exception(self, exc: Exception):
        """Find appropriate handler for exception type."""
        handler_map = self._get_handler_map()
        for exc_type, handler in handler_map.items():
            if isinstance(exc, exc_type):
                return handler
        return self._create_unknown_handler()
    
    def _get_handler_map(self) -> Dict[type, object]:
        """Get mapping of exception types to handlers."""
        from pydantic import ValidationError
        from sqlalchemy.exc import SQLAlchemyError
        from fastapi import HTTPException
        
        return {
            NetraException: self._netra_handler,
            ValidationError: self._validation_handler,
            SQLAlchemyError: self._database_handler,
            HTTPException: self._http_handler,
        }
    
    def _create_unknown_handler(self):
        """Create handler for unknown exception types."""
        return UnknownExceptionHandler(self._logger)
    
    def log_error(self, exc: Exception, severity: Union[ErrorSeverity, str]):
        """Log error with appropriate severity level."""
        severity_value = self._normalize_severity(severity)
        log_method = self._get_log_method(severity_value)
        log_method(f"Error occurred: {str(exc)}", exc_info=True)
    
    def _normalize_severity(self, severity: Union[ErrorSeverity, str]) -> str:
        """Normalize severity to string value."""
        return severity.value if hasattr(severity, 'value') else str(severity)
    
    def _get_log_method(self, severity_value: str):
        """Get appropriate log method for severity."""
        log_methods = self._build_log_methods_map()
        return log_methods.get(severity_value, self._logger.error)
    
    def _build_log_methods_map(self) -> Dict[str, callable]:
        """Build mapping of severity values to log methods."""
        return {
            "low": self._logger.info,
            "medium": self._logger.warning,
            "high": self._logger.error,
            "critical": self._logger.critical,
        }


class UnknownExceptionHandler:
    """Handler for unknown exception types."""
    
    def __init__(self, logger):
        self._logger = logger
    
    def handle(self, exc: Exception, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Handle unknown exception types."""
        self._logger.error(f"Unknown exception: {type(exc).__name__}: {str(exc)}", exc_info=True)
        return self._create_unknown_error_response(exc, trace_id, request_id)
    
    def _create_unknown_error_response(
        self, 
        exc: Exception, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for unknown exceptions."""
        return ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An internal server error occurred",
            user_message="Something went wrong. Please try again later.",
            details={"exception_type": type(exc).__name__},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )


# Global processor instance
_error_processor = ErrorProcessor()


def process_exception(
    exc: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> ErrorResponse:
    """Convenient function to process exceptions using the global processor."""
    return _error_processor.process_exception(exc, request, trace_id)
