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
        
        if trace_id is None:
            trace_id = str(uuid4())
        
        # Get request ID if available
        request_id = None
        if request and hasattr(request.state, 'request_id'):
            request_id = request.state.request_id
        
        # Handle Netra exceptions
        if isinstance(exc, NetraException):
            return self._handle_netra_exception(exc, trace_id, request_id)
        
        # Handle Pydantic validation errors
        if isinstance(exc, ValidationError):
            return self._handle_pydantic_validation_error(exc, trace_id, request_id)
        
        # Handle SQLAlchemy errors
        if isinstance(exc, SQLAlchemyError):
            return self._handle_sqlalchemy_error(exc, trace_id, request_id)
        
        # Handle HTTP exceptions
        if isinstance(exc, HTTPException):
            return self._handle_http_exception(exc, trace_id, request_id)
        
        # Handle unknown exceptions
        return self._handle_unknown_exception(exc, trace_id, request_id)
    
    def _handle_netra_exception(
        self,
        exc: NetraException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle custom Netra exceptions."""
        
        # Update trace ID in exception details
        exc.error_details.trace_id = trace_id
        
        # Log the error
        self._log_error(exc, exc.error_details.severity)
        
        error_code_value = exc.error_details.code if isinstance(exc.error_details.code, str) else exc.error_details.code.value
        return ErrorResponse(
            error_code=error_code_value,
            message=exc.error_details.message,
            user_message=exc.error_details.user_message,
            details=exc.error_details.details,
            trace_id=trace_id,
            timestamp=exc.error_details.timestamp.isoformat(),
            request_id=request_id
        )
    
    def _handle_pydantic_validation_error(
        self,
        exc: ValidationError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle Pydantic validation errors."""
        
        validation_errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(f"{field}: {error['msg']}")
        
        self._logger.warning(f"Validation error: {validation_errors}")
        
        return ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            user_message="Please check your input and try again",
            details={
                "validation_errors": validation_errors,
                "error_count": len(validation_errors)
            },
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _handle_sqlalchemy_error(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle SQLAlchemy database errors."""
        
        if isinstance(exc, IntegrityError):
            self._logger.warning(f"Database integrity error: {exc}")
            return ErrorResponse(
                error_code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION.value,
                message="Database constraint violation",
                user_message="The operation could not be completed due to data constraints",
                details={"error_type": "constraint_violation"},  # Don't expose DB structure
                trace_id=trace_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=request_id
            )
        
        # General SQLAlchemy error
        self._logger.error(f"Database error: {str(exc)}", exc_info=True)
        return ErrorResponse(
            error_code=ErrorCode.DATABASE_QUERY_FAILED.value,
            message="Database operation failed",
            user_message="A database error occurred. Please try again",
            details={"error_type": type(exc).__name__},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _handle_http_exception(
        self,
        exc: HTTPException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle FastAPI HTTP exceptions."""
        
        # Map HTTP status codes to error codes
        status_to_error_code = {
            HTTP_401_UNAUTHORIZED: ErrorCode.AUTHENTICATION_FAILED,
            HTTP_403_FORBIDDEN: ErrorCode.AUTHORIZATION_FAILED,
            HTTP_404_NOT_FOUND: ErrorCode.RECORD_NOT_FOUND,
            HTTP_409_CONFLICT: ErrorCode.RECORD_ALREADY_EXISTS,
            HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
        }
        
        error_code = status_to_error_code.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        
        self._logger.warning(f"HTTP exception {exc.status_code}: {exc.detail}")
        
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
        
        return ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR.value,
            message="An internal server error occurred",
            user_message="Something went wrong. Please try again later",
            details={
                "error_id": trace_id  # Only expose trace ID for debugging
            },
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _log_error(self, exc: Exception, severity: Union[ErrorSeverity, str]):
        """Log error based on severity level."""
        
        # Convert string to enum if needed
        if isinstance(severity, str):
            severity_value = severity.lower()
        else:
            severity_value = severity.value
        
        if severity_value == ErrorSeverity.CRITICAL.value:
            self._logger.critical(f"Critical error: {exc}", exc_info=True)
        elif severity_value == ErrorSeverity.HIGH.value:
            self._logger.error(f"High severity error: {exc}", exc_info=True)
        elif severity_value == ErrorSeverity.MEDIUM.value:
            self._logger.warning(f"Medium severity error: {exc}")
        else:  # LOW
            self._logger.info(f"Low severity error: {exc}")
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        
        status_map = {
            # Authentication/Authorization errors
            ErrorCode.AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
            ErrorCode.AUTHORIZATION_FAILED: HTTP_403_FORBIDDEN,
            ErrorCode.TOKEN_EXPIRED: HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID: HTTP_401_UNAUTHORIZED,
            
            # Database errors
            ErrorCode.RECORD_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.RECORD_ALREADY_EXISTS: HTTP_409_CONFLICT,
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION: HTTP_409_CONFLICT,
            ErrorCode.DATABASE_CONNECTION_FAILED: HTTP_503_SERVICE_UNAVAILABLE,
            
            # Validation errors
            ErrorCode.VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
            ErrorCode.DATA_VALIDATION_ERROR: HTTP_400_BAD_REQUEST,
            
            # Service errors
            ErrorCode.SERVICE_UNAVAILABLE: HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SERVICE_TIMEOUT: HTTP_503_SERVICE_UNAVAILABLE,
            
            # WebSocket errors
            ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED: HTTP_401_UNAUTHORIZED,
            
            # File errors
            ErrorCode.FILE_NOT_FOUND: HTTP_404_NOT_FOUND,
            ErrorCode.FILE_ACCESS_DENIED: HTTP_403_FORBIDDEN,
        }
        
        return status_map.get(error_code, HTTP_500_INTERNAL_SERVER_ERROR)


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
    
    # Handle code whether it's an ErrorCode enum or string
    code = exc.error_details.code
    if isinstance(code, str):
        # Convert string back to ErrorCode enum for status mapping
        try:
            code = next(ec for ec in ErrorCode if ec.value == code)
        except StopIteration:
            code = ErrorCode.INTERNAL_ERROR
    
    status_code = get_http_status_code(code)
    
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