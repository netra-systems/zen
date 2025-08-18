"""Centralized error handling utilities and FastAPI exception handlers."""

from typing import Dict, Any, Optional, Union
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.logging_config import central_logger
from .exceptions import (
    NetraException,
    ErrorCode,
    ErrorSeverity,
)
from .error_response import ErrorResponse
from .error_handlers_validation import ValidationErrorHandler
from .error_handlers_database import DatabaseErrorHandler
from .error_handlers_http import HttpErrorHandler
from .error_handlers_status_mapping import StatusCodeMapper


class ApiErrorHandler:
    """Centralized API error handling and logging utility for FastAPI."""
    
    def __init__(self):
        self._logger = central_logger.get_logger(__name__)
        self._init_handlers()
    
    def _init_handlers(self):
        """Initialize specialized error handlers."""
        self._validation_handler = ValidationErrorHandler(self._logger)
        self._database_handler = DatabaseErrorHandler(self._logger)
        self._http_handler = HttpErrorHandler(self._logger)
        self._status_mapper = StatusCodeMapper()
    
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
        context_data = self._prepare_exception_context(trace_id, request)
        return self._route_exception_to_handler(exc, context_data['trace_id'], context_data['request_id'])
    
    def _prepare_exception_context(self, trace_id: Optional[str], request: Optional[Request]) -> Dict[str, Optional[str]]:
        """Prepare exception context data."""
        prepared_trace_id = self._prepare_trace_id(trace_id)
        request_id = self._extract_request_id(request)
        return {'trace_id': prepared_trace_id, 'request_id': request_id}
    
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
        handler = self._select_exception_handler(exc)
        return handler(exc, trace_id, request_id)
    
    def _select_exception_handler(self, exc: Exception) -> callable:
        """Select appropriate handler for exception type."""
        handler_map = self._get_exception_handler_map()
        return self._find_exception_handler(exc, handler_map)
    
    def _get_exception_handler_map(self) -> Dict[type, callable]:
        """Get mapping of exception types to handler methods."""
        return self._build_handler_map()
    
    def _build_handler_map(self) -> Dict[type, callable]:
        """Build exception handler mapping."""
        return {
            NetraException: self._handle_netra_exception,
            ValidationError: self._handle_validation_delegation,
            SQLAlchemyError: self._handle_database_delegation,
            HTTPException: self._handle_http_delegation,
        }
    
    def _find_exception_handler(self, exc: Exception, handler_map: Dict) -> callable:
        """Find appropriate handler for exception type."""
        return self._search_handlers(exc, handler_map)
    
    def _search_handlers(self, exc: Exception, handler_map: Dict) -> callable:
        """Search for matching handler in handler map."""
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
        return self._process_netra_exception(exc, trace_id, request_id)
    
    def _process_netra_exception(
        self, 
        exc: NetraException, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Process Netra exception with logging and response creation."""
        self._handle_netra_exception_data(exc, trace_id)
        return self._create_netra_error_response(exc, trace_id, request_id)
    
    def _handle_netra_exception_data(self, exc: NetraException, trace_id: str) -> None:
        """Handle Netra exception data updates and logging."""
        self._update_exception_trace_id(exc, trace_id)
        self._log_error(exc, exc.error_details.severity)
    
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
        return self._construct_netra_error_response(
            exc, error_code_value, trace_id, request_id
        )
    
    def _construct_netra_error_response(
        self, 
        exc: NetraException, 
        error_code_value: str, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Construct ErrorResponse with Netra exception data."""
        response_params = self._prepare_netra_response_params(exc, error_code_value, trace_id, request_id)
        return ErrorResponse(**response_params)
    
    def _prepare_netra_response_params(
        self, exc: NetraException, error_code_value: str, trace_id: str, request_id: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare parameters for Netra error response."""
        return {
            'error_code': error_code_value, 'message': exc.error_details.message,
            'user_message': exc.error_details.user_message, 'details': exc.error_details.details,
            'trace_id': trace_id, 'timestamp': exc.error_details.timestamp.isoformat(), 'request_id': request_id
        }
    
    def _extract_error_code_value(self, code) -> str:
        """Extract string value from error code."""
        return code if isinstance(code, str) else code.value
    
    def _handle_validation_delegation(
        self,
        exc: ValidationError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Delegate validation error handling."""
        return self._validation_handler.handle_validation_error(exc, trace_id, request_id)
    
    def _handle_database_delegation(
        self,
        exc: SQLAlchemyError,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Delegate database error handling."""
        return self._database_handler.handle_database_error(exc, trace_id, request_id)
    
    def _handle_http_delegation(
        self,
        exc: HTTPException,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Delegate HTTP error handling."""
        return self._http_handler.handle_http_error(exc, trace_id, request_id)
    
    def _handle_unknown_exception(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle unknown exceptions."""
        return self._process_unknown_exception(exc, trace_id, request_id)
    
    def _process_unknown_exception(
        self, 
        exc: Exception, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Process unknown exception with logging."""
        self._log_unknown_exception(exc)
        return self._create_unknown_error_response(trace_id, request_id)
    
    def _log_unknown_exception(self, exc: Exception) -> None:
        """Log unknown exception with full details."""
        self._logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    def _create_unknown_error_response(
        self,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create error response for unknown exceptions."""
        return self._build_unknown_error_response(trace_id, request_id)
    
    def _build_unknown_error_response(self, trace_id: str, request_id: Optional[str]) -> ErrorResponse:
        """Build unknown exception error response."""
        response_params = self._prepare_unknown_response_params(trace_id, request_id)
        return ErrorResponse(**response_params)
    
    def _prepare_unknown_response_params(self, trace_id: str, request_id: Optional[str]) -> Dict[str, Any]:
        """Prepare parameters for unknown error response."""
        return {
            'error_code': ErrorCode.INTERNAL_ERROR.value, 'message': "An internal server error occurred",
            'user_message': "Something went wrong. Please try again later", 'details': {"error_id": trace_id},
            'trace_id': trace_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'request_id': request_id
        }
    
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
            ErrorSeverity.CRITICAL.value: self._critical_log,
            ErrorSeverity.HIGH.value: self._error_log,
            ErrorSeverity.MEDIUM.value: self._logger.warning,
            ErrorSeverity.LOW.value: self._logger.info
        }
    
    def _critical_log(self, msg: str):
        """Log critical error with stack trace."""
        self._logger.critical(msg, exc_info=True)
    
    def _error_log(self, msg: str):
        """Log error with stack trace."""
        self._logger.error(msg, exc_info=True)
    
    def get_http_status_code(self, error_code: ErrorCode) -> int:
        """Map error codes to HTTP status codes."""
        return self._status_mapper.get_http_status_code(error_code)


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