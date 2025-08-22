"""Error response building utilities.

Builds standardized error responses for different exception types.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.core.exceptions import ErrorCode, ErrorSeverity, NetraException


class ErrorResponseBuilder:
    """Builds standardized error responses."""
    
    def __init__(self, logger):
        """Initialize response builder with logger."""
        self._logger = logger
    
    def build_netra_response(
        self, 
        exc: NetraException, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Build ErrorResponse from Netra exception details."""
        self._update_exception_trace_id(exc, trace_id)
        self._log_error(exc, exc.error_details.severity)
        
        error_code_value = self._extract_error_code_value(exc.error_details.code)
        response_params = self._prepare_netra_response_params(
            exc, error_code_value, trace_id, request_id
        )
        
        return ErrorResponse(**response_params)
    
    def build_validation_response(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Build response for validation errors."""
        self._logger.error("Validation error: {}", str(exc))
        
        return ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR.value,
            message="Validation failed",
            user_message="Please check your input and try again",
            details={"validation_errors": str(exc)},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def build_database_response(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Build response for database errors."""
        self._logger.error("Database error: {}", str(exc), exc_info=True)
        
        return ErrorResponse(
            error_code=ErrorCode.DATABASE_ERROR.value,
            message="Database operation failed",
            user_message="A database error occurred. Please try again later",
            details={"error_id": trace_id},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def build_http_response(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Build response for HTTP exceptions."""
        self._logger.warning("HTTP error: {}", str(exc))
        
        # Map specific HTTP status codes to appropriate error codes
        error_code = self._map_http_status_to_error_code(exc)
        message = self._extract_http_message(exc)
        
        return ErrorResponse(
            error_code=error_code,
            message=message,
            user_message="An HTTP error occurred",
            details={"error_id": trace_id},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _map_http_status_to_error_code(self, exc: Exception) -> str:
        """Map HTTP status codes to appropriate error codes."""
        if hasattr(exc, 'status_code'):
            status_map = {
                503: ErrorCode.SERVICE_UNAVAILABLE.value,
                500: ErrorCode.INTERNAL_ERROR.value,
                422: ErrorCode.VALIDATION_ERROR.value,
                401: ErrorCode.AUTHENTICATION_FAILED.value,
                403: ErrorCode.AUTHORIZATION_FAILED.value,
                404: ErrorCode.FILE_NOT_FOUND.value,
            }
            return status_map.get(exc.status_code, ErrorCode.HTTP_ERROR.value)
        return ErrorCode.HTTP_ERROR.value
    
    def _extract_http_message(self, exc: Exception) -> str:
        """Extract clean message from HTTP exception."""
        message = str(exc)
        # Handle FastAPI HTTPException format "503: Service Unavailable"
        if hasattr(exc, 'detail') and exc.detail:
            return exc.detail
        # Remove status code prefix if present
        if ': ' in message and message.split(': ', 1)[0].isdigit():
            return message.split(': ', 1)[1]
        return message
    
    def build_unknown_response(
        self,
        exc: Exception,
        trace_id: str,
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Build response for unknown exceptions."""
        self._logger.error("Unhandled exception: {}", str(exc), exc_info=True)
        
        return ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR.value,
            message="An internal server error occurred",
            user_message="Something went wrong. Please try again later",
            details={"error_id": trace_id},
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _update_exception_trace_id(self, exc: NetraException, trace_id: str) -> None:
        """Update trace ID in exception details."""
        exc.error_details.trace_id = trace_id
    
    def _extract_error_code_value(self, code) -> str:
        """Extract string value from error code."""
        return code if isinstance(code, str) else code.value
    
    def _prepare_netra_response_params(
        self, exc: NetraException, error_code_value: str, trace_id: str, request_id: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare parameters for Netra error response."""
        return {
            'error_code': error_code_value,
            'message': exc.error_details.message,
            'user_message': exc.error_details.user_message,
            'details': exc.error_details.details,
            'trace_id': trace_id,
            'timestamp': exc.error_details.timestamp.isoformat(),
            'request_id': request_id
        }
    
    def _log_error(self, exc: Exception, severity: Union[ErrorSeverity, str]):
        """Log error based on severity level."""
        severity_value = self._normalize_severity(severity)
        log_method = self._get_log_method(severity_value)
        log_method("{} severity error: {}", severity_value.title(), exc)
    
    def _normalize_severity(self, severity: Union[ErrorSeverity, str]) -> str:
        """Normalize severity to string value."""
        if isinstance(severity, str):
            return severity.lower()
        return severity.value
    
    def _get_log_method(self, severity_value: str):
        """Get appropriate logging method for severity level."""
        log_methods = {
            ErrorSeverity.CRITICAL.value: lambda msg: self._logger.critical(msg, exc_info=True),
            ErrorSeverity.HIGH.value: lambda msg: self._logger.error(msg, exc_info=True),
            ErrorSeverity.MEDIUM.value: self._logger.warning,
            ErrorSeverity.LOW.value: self._logger.info
        }
        return log_methods.get(severity_value, self._logger.info)