"""Exception processors for different types of errors.

Handles processing of various exception types into standardized error responses.
"""

from typing import Dict, Any, List, Union
from uuid import uuid4

from fastapi import Request, HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from netra_backend.app.core.exceptions import (
    NetraException,
    ErrorCode,
    ErrorSeverity
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.transaction_manager.types import ErrorResponse, ErrorContext

logger = central_logger.get_logger(__name__)


class ExceptionProcessor:
    """Base processor for handling exceptions."""
    
    def process_exception(
        self,
        exc: Exception,
        request: Request = None,
        trace_id: str = None
    ) -> ErrorResponse:
        """Process any exception and return standardized error response."""
        context = self._create_error_context(request, trace_id)
        return self._route_to_handler(exc, context)
    
    def _create_error_context(self, request: Request, trace_id: str) -> ErrorContext:
        """Create error context from request and trace ID."""
        prepared_trace_id = trace_id or str(uuid4())
        request_id = self._extract_request_id(request)
        return ErrorContext(prepared_trace_id, request_id)
    
    def _extract_request_id(self, request: Request) -> str:
        """Extract request ID from request state if available."""
        if request and hasattr(request.state, 'request_id'):
            return request.state.request_id
        return None
    
    def _route_to_handler(self, exc: Exception, context: ErrorContext) -> ErrorResponse:
        """Route exception to appropriate handler based on type."""
        handlers = self._get_handler_map()
        handler = self._find_handler(exc, handlers)
        return handler(exc, context)
    
    def _get_handler_map(self) -> Dict[type, callable]:
        """Get mapping of exception types to handler methods."""
        return {
            NetraException: self._handle_netra_exception,
            ValidationError: self._handle_validation_error,
            SQLAlchemyError: self._handle_sqlalchemy_error,
            HTTPException: self._handle_http_exception,
        }
    
    def _find_handler(self, exc: Exception, handlers: Dict) -> callable:
        """Find appropriate handler for exception type."""
        for exc_type, handler in handlers.items():
            if isinstance(exc, exc_type):
                return handler
        return self._handle_unknown_exception


class NetraExceptionProcessor(ExceptionProcessor):
    """Processor for Netra-specific exceptions."""
    
    def _handle_netra_exception(self, exc: NetraException, context: ErrorContext) -> ErrorResponse:
        """Handle custom Netra exceptions."""
        self._update_exception_context(exc, context)
        self._log_netra_error(exc)
        return self._build_netra_response(exc, context)
    
    def _update_exception_context(self, exc: NetraException, context: ErrorContext) -> None:
        """Update trace ID in exception details."""
        exc.error_details.trace_id = context.trace_id
    
    def _log_netra_error(self, exc: NetraException) -> None:
        """Log error based on severity level."""
        severity = exc.error_details.severity
        log_method = self._get_log_method_for_severity(severity)
        log_method(f"{severity.title()} severity error: {exc}")
    
    def _get_log_method_for_severity(self, severity: Union[ErrorSeverity, str]):
        """Get appropriate logging method for severity level."""
        severity_str = self._normalize_severity(severity)
        log_methods = {
            ErrorSeverity.CRITICAL.value: lambda msg: logger.critical(msg, exc_info=True),
            ErrorSeverity.HIGH.value: lambda msg: logger.error(msg, exc_info=True),
            ErrorSeverity.MEDIUM.value: logger.warning,
            ErrorSeverity.LOW.value: logger.info
        }
        return log_methods.get(severity_str, logger.info)
    
    def _normalize_severity(self, severity: Union[ErrorSeverity, str]) -> str:
        """Normalize severity to string value."""
        if isinstance(severity, str):
            return severity.lower()
        return severity.value
    
    def _build_netra_response(self, exc: NetraException, context: ErrorContext) -> ErrorResponse:
        """Build ErrorResponse from Netra exception details."""
        error_code = self._extract_error_code_value(exc.error_details.code)
        base_response = context.create_base_response(error_code, exc.error_details.message)
        return ErrorResponse(
            **base_response,
            user_message=exc.error_details.user_message,
            details=exc.error_details.details
        )
    
    def _extract_error_code_value(self, code) -> str:
        """Extract string value from error code."""
        return code if isinstance(code, str) else code.value


class ValidationProcessor(ExceptionProcessor):
    """Processor for validation errors."""
    
    def _handle_validation_error(self, exc: ValidationError, context: ErrorContext) -> ErrorResponse:
        """Handle Pydantic validation errors."""
        validation_errors = self._extract_validation_errors(exc)
        logger.warning("Validation error: {}", validation_errors)
        return self._create_validation_response(validation_errors, context)
    
    def _extract_validation_errors(self, exc: ValidationError) -> List[str]:
        """Extract validation errors from Pydantic exception."""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        return errors
    
    def _create_validation_response(self, errors: List[str], context: ErrorContext) -> ErrorResponse:
        """Create error response for validation errors."""
        base_response = context.create_base_response(
            ErrorCode.VALIDATION_ERROR.value,
            "Request validation failed"
        )
        details = {'validation_errors': errors, 'error_count': len(errors)}
        return ErrorResponse(
            **base_response,
            user_message="Please check your input and try again",
            details=details
        )


class DatabaseProcessor(ExceptionProcessor):
    """Processor for database-related errors."""
    
    def _handle_sqlalchemy_error(self, exc: SQLAlchemyError, context: ErrorContext) -> ErrorResponse:
        """Handle SQLAlchemy database errors."""
        if isinstance(exc, IntegrityError):
            return self._handle_integrity_error(exc, context)
        return self._handle_general_db_error(exc, context)
    
    def _handle_integrity_error(self, exc: IntegrityError, context: ErrorContext) -> ErrorResponse:
        """Handle database integrity constraint violations."""
        logger.warning("Database integrity error: {}", exc)
        base_response = context.create_base_response(
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION.value,
            "Database constraint violation"
        )
        return ErrorResponse(
            **base_response,
            user_message="The operation could not be completed due to data constraints",
            details={"error_type": "constraint_violation"}
        )
    
    def _handle_general_db_error(self, exc: SQLAlchemyError, context: ErrorContext) -> ErrorResponse:
        """Handle general SQLAlchemy database errors."""
        logger.error("Database error: {}", str(exc), exc_info=True)
        base_response = context.create_base_response(
            ErrorCode.DATABASE_QUERY_FAILED.value,
            "Database operation failed"
        )
        return ErrorResponse(
            **base_response,
            user_message="A database error occurred. Please try again",
            details={"error_type": type(exc).__name__}
        )


class HTTPProcessor(ExceptionProcessor):
    """Processor for HTTP exceptions."""
    
    def _handle_http_exception(self, exc: HTTPException, context: ErrorContext) -> ErrorResponse:
        """Handle FastAPI HTTP exceptions."""
        error_code = self._map_status_to_error_code(exc.status_code)
        logger.warning("HTTP exception {}: {}", exc.status_code, exc.detail)
        return self._create_http_response(exc, error_code, context)
    
    def _map_status_to_error_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to internal error codes."""
        status_mapping = {
            HTTP_401_UNAUTHORIZED: ErrorCode.AUTHENTICATION_FAILED,
            HTTP_403_FORBIDDEN: ErrorCode.AUTHORIZATION_FAILED,
            HTTP_404_NOT_FOUND: ErrorCode.RECORD_NOT_FOUND,
            HTTP_409_CONFLICT: ErrorCode.RECORD_ALREADY_EXISTS,
            HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
        }
        return status_mapping.get(status_code, ErrorCode.INTERNAL_ERROR)
    
    def _create_http_response(self, exc: HTTPException, error_code: ErrorCode, context: ErrorContext) -> ErrorResponse:
        """Create error response for HTTP exceptions."""
        base_response = context.create_base_response(error_code.value, str(exc.detail))
        headers = dict(exc.headers) if exc.headers else None
        return ErrorResponse(
            **base_response,
            user_message=str(exc.detail),
            details={"status_code": exc.status_code, "headers": headers}
        )
    
    def _handle_unknown_exception(self, exc: Exception, context: ErrorContext) -> ErrorResponse:
        """Handle unknown exceptions."""
        logger.error("Unhandled exception: {}", exc, exc_info=True)
        base_response = context.create_base_response(
            ErrorCode.INTERNAL_ERROR.value,
            "An internal server error occurred"
        )
        return ErrorResponse(
            **base_response,
            user_message="Something went wrong. Please try again later",
            details={"error_id": context.trace_id}
        )