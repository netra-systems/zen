"""Base exception classes - compliant with 25-line function limit."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity


class ErrorDetails(BaseModel):
    """Detailed error information for structured error responses."""
    code: ErrorCode
    message: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    details: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True)


class WebSocketValidationError(Exception):
    """WebSocket validation error exception."""
    pass


class NetraException(Exception):
    """Base exception class for all Netra application exceptions."""
    
    def __init__(self, message: str = None, code: ErrorCode = ErrorCode.INTERNAL_ERROR,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None, report_to_gcp: bool = None):
        self.error_details = self._build_error_details(
            message, code, severity, details, user_message, trace_id, context)
        self.report_to_gcp = self._should_report_to_gcp(report_to_gcp, severity)
        super().__init__(self.error_details.message)
        
        # Auto-report to GCP if configured
        if self.report_to_gcp:
            self._report_to_gcp()
    
    def _build_error_details(self, message: str, code: ErrorCode, severity: ErrorSeverity,
                           details: Optional[Dict[str, Any]], user_message: Optional[str],
                           trace_id: Optional[str], context: Optional[Dict[str, Any]]) -> ErrorDetails:
        """Build ErrorDetails object with default values."""
        return ErrorDetails(
            code=code, message=message or "An internal error occurred", severity=severity,
            details=details or {}, user_message=user_message, trace_id=trace_id, context=context or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return self.error_details.model_dump()
    
    def _should_report_to_gcp(self, report_to_gcp: Optional[bool], severity: ErrorSeverity) -> bool:
        """Determine if this exception should be reported to GCP."""
        if report_to_gcp is not None:
            return report_to_gcp
        # Auto-report HIGH and CRITICAL severity errors
        return severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
    
    def _report_to_gcp(self) -> None:
        """Report this exception to GCP Error Reporting."""
        try:
            from netra_backend.app.services.monitoring.gcp_error_reporter import report_exception
            
            extra_context = {
                'error_code': str(self.error_details.code),
                'error_severity': str(self.error_details.severity),
                'error_details': self.error_details.details,
                'trace_id': self.error_details.trace_id
            }
            
            if self.error_details.context:
                extra_context['context'] = self.error_details.context
            
            report_exception(self, extra_context=extra_context)
        except Exception:
            # Silently fail if GCP reporting is not available
            pass
    
    def __str__(self) -> str:
        """String representation of the exception."""
        code_val = self.error_details.code if isinstance(self.error_details.code, str) else self.error_details.code.value
        return f"{code_val}: {self.error_details.message}"


class ValidationError(NetraException):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code=ErrorCode.VALIDATION_ERROR, severity=ErrorSeverity.MEDIUM,
            details=details, user_message=user_message, trace_id=trace_id, context=context
        )


class QualityGateException(NetraException):
    """Exception raised when quality gate validation fails."""
    
    def __init__(self, message: str = "Quality gate validation failed", details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code=ErrorCode.VALIDATION_ERROR, severity=ErrorSeverity.HIGH,
            details=details, user_message=user_message, trace_id=trace_id, context=context
        )


class StateRecoveryException(NetraException):
    """Exception raised when state recovery operations fail."""
    
    def __init__(self, message: str = "State recovery failed", details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code=ErrorCode.INTERNAL_ERROR, severity=ErrorSeverity.HIGH,
            details=details, user_message=user_message, trace_id=trace_id, context=context
        )


class AuthorizationException(NetraException):
    """Exception raised when authorization or permission checks fail."""
    
    def __init__(self, message: str = "Authorization failed", details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code=ErrorCode.AUTHORIZATION_FAILED, severity=ErrorSeverity.HIGH,
            details=details, user_message=user_message, trace_id=trace_id, context=context
        )


class ServiceUnavailableException(NetraException):
    """Exception raised when a service is unavailable."""
    
    def __init__(self, message: str = "Service unavailable", details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code=ErrorCode.SERVICE_UNAVAILABLE, severity=ErrorSeverity.HIGH,
            details=details, user_message=user_message, trace_id=trace_id, context=context
        )


class PaymentException(NetraException):
    """Exception raised when payment processing fails."""
    
    def __init__(self, message: str = "Payment processing failed", details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None, trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code=ErrorCode.EXTERNAL_SERVICE_ERROR, severity=ErrorSeverity.HIGH,
            details=details, user_message=user_message, trace_id=trace_id, context=context
        )