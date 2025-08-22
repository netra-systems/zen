"""NetraException specialized error handler."""

from datetime import datetime, timezone
from typing import Optional, Union

from netra_backend.app.core.error_response_models import ErrorResponse
from netra_backend.app.core.exceptions import ErrorSeverity, NetraException


class NetraExceptionHandler:
    """Specialized handler for NetraException types."""
    
    def __init__(self, logger):
        self._logger = logger
    
    def handle(
        self, 
        exc: NetraException, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Handle NetraException with specialized processing."""
        self._update_exception_trace_id(exc, trace_id)
        self._log_netra_exception(exc)
        return self._create_netra_error_response(exc, trace_id, request_id)
    
    def _update_exception_trace_id(self, exc: NetraException, trace_id: str) -> None:
        """Update trace ID in exception details."""
        exc.error_details.trace_id = trace_id
    
    def _log_netra_exception(self, exc: NetraException) -> None:
        """Log NetraException with appropriate severity."""
        severity_value = self._normalize_severity(exc.error_details.severity)
        log_method = self._get_log_method_for_severity(severity_value)
        log_method(f"Netra error: {str(exc)}", exc_info=True)
    
    def _normalize_severity(self, severity: Union[ErrorSeverity, str]) -> str:
        """Normalize severity to string value."""
        return severity.value if hasattr(severity, 'value') else str(severity)
    
    def _get_log_method_for_severity(self, severity_value: str):
        """Get log method based on severity."""
        log_methods = {
            "low": self._logger.info,
            "medium": self._logger.warning,
            "high": self._logger.error,
            "critical": self._logger.critical,
        }
        return log_methods.get(severity_value, self._logger.error)
    
    def _create_netra_error_response(
        self, 
        exc: NetraException, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Create standardized error response for NetraException."""
        return self._build_netra_response(exc, trace_id, request_id)
    
    def _build_netra_response(
        self, 
        exc: NetraException, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Build NetraException response with all details."""
        return self._construct_netra_error_response(exc, trace_id, request_id)
    
    def _construct_netra_error_response(
        self, 
        exc: NetraException, 
        trace_id: str, 
        request_id: Optional[str]
    ) -> ErrorResponse:
        """Construct complete NetraException error response."""
        error_code = self._extract_error_code_value(exc.error_details.code)
        return ErrorResponse(
            error_code=error_code,
            message=exc.error_details.message,
            user_message=exc.error_details.user_message,
            details=exc.error_details.details,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id
        )
    
    def _extract_error_code_value(self, code) -> str:
        """Extract error code string value."""
        return code.value if hasattr(code, 'value') else str(code)
