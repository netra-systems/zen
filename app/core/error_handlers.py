"""Centralized error handling utilities and FastAPI exception handlers."""

from typing import Dict, Any, Optional, Union
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, ConfigDict
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.logging_config import central_logger
from .exceptions import (
    NetraException,
    ErrorCode,
    ErrorSeverity,
    ErrorDetails,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    DatabaseConnectionError,
    RecordNotFoundError,
    RecordAlreadyExistsError,
    ConstraintViolationError,
    ServiceError,
    ServiceTimeoutError,
    ValidationError as NetraValidationError,
)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    error: bool = True
    error_code: str
    message: str
    user_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    trace_id: str
    timestamp: str
    request_id: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True)


class ApiErrorHandler:
    """Centralized API error handling and logging utility for FastAPI."""
    
    def __init__(self):
        self._logger = central_logger.get_logger(__name__)
    
    def handle_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        trace_id: Optional[str] = None
    ) -> ErrorResponse:
        """Handle any exception and return standardized error response."""
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
        return self._route_exception_to_handler(exc, prepared_trace_id, request_id)
    
    def _prepare_trace_id(self, trace_id: Optional[str]) -> str:
        """Prepare trace ID for exception handling."""
        return trace_id if trace_id is not None else str(uuid4())
    
    def _extract_request_id(self, request: Optional[Request]) -> Optional[str]:
        """Extract request ID from request state if available."""
        if request and hasattr(request.state, 'request_id'):
            return request.state.request_id
        return None
    
    def _route_exception_to_handler(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Route exception to appropriate handler based on type."""
        handler_map = self._get_exception_handler_map()
        handler = self._find_exception_handler(exc, handler_map)
        return handler(exc, trace_id, request_id)
    
    def _get_exception_handler_map(self) -> Dict[type, callable]:
        """Get mapping of exception types to handler methods."""
        return {
            NetraException: self._handle_netra_exception,
            ValidationError: self._handle_pydantic_validation_error,
            SQLAlchemyError: self._handle_sqlalchemy_error,
            HTTPException: self._handle_http_exception,
        }
    
    def _find_exception_handler(self, exc: Exception, handler_map: Dict) -> callable:
        """Find appropriate handler for exception type."""
        for exc_type, handler in handler_map.items():
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
        self._update_exception_trace_id(exc, trace_id)
        self._log_error(exc, exc.error_details.severity)
        return self._create_netra_error_response(exc, trace_id, request_id)
    
    def _update_exception_trace_id(self, exc: NetraException, trace_id: str) -> None:
        """Update trace ID in exception details."""
        exc.error_details.trace_id = trace_id
    
    def _create_netra_error_response(
        self,
        exc: NetraException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for Netra exception."""
        error_code_value = self._extract_error_code_value(exc.error_details.code)
        return self._build_netra_response(exc, error_code_value, trace_id, request_id)
    
    def _build_netra_response(
        self, exc: NetraException, error_code_value: str, trace_id: str, request_id: Optional[str]
    ) -> ErrorResponse:
        """Build ErrorResponse from Netra exception details."""
        return ErrorResponse(
            error_code=error_code_value,
            message=exc.error_details.message,
            user_message=exc.error_details.user_message,
            details=exc.error_details.details,
            trace_id=trace_id,
            timestamp=exc.error_details.timestamp.isoformat(),
            request_id=request_id
        )
    
    def _extract_error_code_value(self, code) -> str:
        """Extract string value from error code."""
        return code if isinstance(code, str) else code.value
    
    def _handle_pydantic_validation_error(
        self,
        exc: ValidationError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle Pydantic validation errors."""
        validation_errors = self._extract_validation_errors(exc)
        self._logger.warning(f"Validation error: {validation_errors}")
        return self._create_validation_error_response(
            validation_errors, trace_id, request_id
        )
    
    def _extract_validation_errors(self, exc: ValidationError) -> list:
        """Extract validation errors from Pydantic exception."""
        validation_errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(f"{field}: {error['msg']}")
        return validation_errors
    
    def _create_validation_error_response(
        self,
        validation_errors: list,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for validation errors."""
        return self._build_validation_response(validation_errors, trace_id, request_id)
    
    def _build_validation_response(self, validation_errors: list, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Build validation error response with details."""
        details = self._create_validation_details(validation_errors)
        return ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            user_message="Please check your input and try again",
            details=details, trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _create_validation_details(self, validation_errors: list) -> Dict[str, Any]:
        """Create validation error details."""
        return {
            "validation_errors": validation_errors,
            "error_count": len(validation_errors)
        }
    
    def _handle_sqlalchemy_error(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle SQLAlchemy database errors."""
        if isinstance(exc, IntegrityError):
            return self._handle_integrity_error(exc, trace_id, request_id)
        return self._handle_general_db_error(exc, trace_id, request_id)
    
    def _handle_integrity_error(
        self,
        exc: IntegrityError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle database integrity constraint violations."""
        self._logger.warning(f"Database integrity error: {exc}")
        return self._create_integrity_error_response(trace_id, request_id)
    
    def _create_integrity_error_response(self, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Create integrity error response."""
        return ErrorResponse(
            error_code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION.value,
            message="Database constraint violation",
            user_message="The operation could not be completed due to data constraints",
            details={"error_type": "constraint_violation"}, trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(), request_id=request_id
        )
    
    def _handle_general_db_error(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle general SQLAlchemy database errors."""
        self._logger.error(f"Database error: {str(exc)}", exc_info=True)
        return self._create_general_db_error_response(exc, trace_id, request_id)
    
    def _create_general_db_error_response(self, exc: SQLAlchemyError, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Create general database error response."""
        return ErrorResponse(
            error_code=ErrorCode.DATABASE_QUERY_FAILED.value,
            message="Database operation failed",
            user_message="A database error occurred. Please try again",
            details={"error_type": type(exc).__name__}, trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(), request_id=request_id
        )
    
    def _handle_http_exception(
        self,
        exc: HTTPException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle FastAPI HTTP exceptions."""
        error_code = self._map_http_status_to_error_code(exc.status_code)
        self._logger.warning(f"HTTP exception {exc.status_code}: {exc.detail}")
        return self._create_http_error_response(
            exc, error_code, trace_id, request_id
        )
    
    def _map_http_status_to_error_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to internal error codes."""
        status_to_error_code = {
            HTTP_401_UNAUTHORIZED: ErrorCode.AUTHENTICATION_FAILED,
            HTTP_403_FORBIDDEN: ErrorCode.AUTHORIZATION_FAILED,
            HTTP_404_NOT_FOUND: ErrorCode.RECORD_NOT_FOUND,
            HTTP_409_CONFLICT: ErrorCode.RECORD_ALREADY_EXISTS,
            HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
        }
        return status_to_error_code.get(status_code, ErrorCode.INTERNAL_ERROR)
    
    def _create_http_error_response(
        self,
        exc: HTTPException,
        error_code: ErrorCode,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for HTTP exceptions."""
        return ErrorResponse(
            error_code=error_code.value,
            message=str(exc.detail),
            user_message=str(exc.detail),
            details={"status_code": exc.status_code, "headers": dict(exc.headers) if exc.headers else None},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _handle_unknown_exception(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle unknown exceptions."""
        self._logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return self._create_unknown_error_response(trace_id, request_id)
    
    def _create_unknown_error_response(
        self,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for unknown exceptions."""
        return ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR.value,
            message="An internal server error occurred",
            user_message="Something went wrong. Please try again later",
            details={"error_id": trace_id},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _log_error(self, exc: Exception, severity: Union[ErrorSeverity, str]):
        """Log error based on severity level."""
        severity_value = self._normalize_severity(severity)
        log_method = self._get_log_method(severity_value)
        log_method(f"{severity_value.title()} severity error: {exc}")
    
    def _normalize_severity(self, severity: Union[ErrorSeverity, str]) -> str:
        """Normalize severity to string value."""
        if isinstance(severity, str):
            return severity.lower()
        return severity.value
    
    def _get_log_method(self, severity_value: str):
        """Get appropriate logging method for severity level."""
        log_methods = self._build_log_methods_map()
        return log_methods.get(severity_value, self._logger.info)
    
    def _build_log_methods_map(self) -> Dict[str, callable]:
        """Build mapping of severity values to log methods."""
        return {
            ErrorSeverity.CRITICAL.value: lambda msg: self._logger.critical(msg, exc_info=True),
            ErrorSeverity.HIGH.value: lambda msg: self._logger.error(msg, exc_info=True),
            ErrorSeverity.MEDIUM.value: self._logger.warning,
            ErrorSeverity.LOW.value: self._logger.info
        }
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        status_map = self._get_error_status_map()
        return status_map.get(error_code, HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get error code to HTTP status mapping."""
        maps = self._collect_error_status_maps()
        return {**maps['auth'], **maps['db'], **maps['validation'], 
                **maps['service'], **maps['websocket'], **maps['file']}
    
    def _collect_error_status_maps(self) -> Dict[str, Dict[ErrorCode, int]]:
        """Collect all error status maps."""
        return {
            'auth': self._get_auth_error_status_map(),
            'db': self._get_db_error_status_map(),
            'validation': self._get_validation_error_status_map(),
            'service': self._get_service_error_status_map(),
            'websocket': self._get_websocket_error_status_map(),
            'file': self._get_file_error_status_map()
        }
    
    def _get_auth_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get authentication/authorization error status mapping."""
        return {
            ErrorCode.AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
            ErrorCode.AUTHORIZATION_FAILED: HTTP_403_FORBIDDEN,
            ErrorCode.TOKEN_EXPIRED: HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID: HTTP_401_UNAUTHORIZED,
        }
    
    def _get_db_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get database error status mapping."""
        return {
            ErrorCode.RECORD_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.RECORD_ALREADY_EXISTS: HTTP_409_CONFLICT,
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION: HTTP_409_CONFLICT,
            ErrorCode.DATABASE_CONNECTION_FAILED: HTTP_503_SERVICE_UNAVAILABLE,
        }
    
    def _get_validation_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get validation error status mapping."""
        return {
            ErrorCode.VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
            ErrorCode.DATA_VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
        }
    
    def _get_service_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get service error status mapping."""
        return {
            ErrorCode.SERVICE_UNAVAILABLE: HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SERVICE_TIMEOUT: HTTP_503_SERVICE_UNAVAILABLE,
        }
    
    def _get_websocket_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get WebSocket error status mapping."""
        return {
            ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
        }
    
    def _get_file_error_status_map(self) -> Dict[ErrorCode, int]:
        """Get file error status mapping."""
        return {
            ErrorCode.FILE_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.FILE_ACCESS_DENIED: HTTP_403_FORBIDDEN,
        }


# Global error handler instance
_error_handler = ApiErrorHandler()


def handle_exception(
    exc: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> ErrorResponse:
    """Convenient function to handle exceptions using the global handler."""
    return _error_handler.handle_exception(exc, request, trace_id)


def get_http_status_code(error_code: ErrorCode) -> int:
    """Get HTTP status code for error code."""
    return _error_handler.get_http_status_code(error_code)


# FastAPI Exception Handlers

async def netra_exception_handler(request: Request, exc: NetraException) -> JSONResponse:
    """FastAPI exception handler for Netra exceptions."""
    error_response = handle_exception(exc, request)
    code = _convert_code_to_enum(exc.error_details.code)
    status_code = get_http_status_code(code)
    return _create_json_response(status_code, error_response)


def _convert_code_to_enum(code) -> ErrorCode:
    """Convert error code to ErrorCode enum."""
    if isinstance(code, str):
        return _find_error_code_by_value(code)
    return code


def _find_error_code_by_value(code_value: str) -> ErrorCode:
    """Find ErrorCode enum by string value."""
    try:
        return next(ec for ec in ErrorCode if ec.value == code_value)
    except StopIteration:
        return ErrorCode.INTERNAL_ERROR


def _create_json_response(status_code: int, error_response: ErrorResponse) -> JSONResponse:
    """Create JSON response for error."""
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """FastAPI exception handler for validation errors."""
    error_response = handle_exception(exc, request)
    
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """FastAPI exception handler for HTTP exceptions."""
    error_response = handle_exception(exc, request)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI exception handler for general exceptions."""
    error_response = handle_exception(exc, request)
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )