"""Service and agent exceptions - compliant with 25-line function limit."""

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException


class ServiceError(NetraException):
    """Base class for service-related exceptions."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Service error occurred",
            code=ErrorCode.SERVICE_UNAVAILABLE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ServiceUnavailableError(ServiceError):
    """Raised when a service is unavailable."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Service is currently unavailable",
            code=ErrorCode.SERVICE_UNAVAILABLE,
            severity=ErrorSeverity.HIGH,
            user_message="The service is temporarily unavailable. Please try again later",
            **kwargs
        )


class ServiceTimeoutError(ServiceError):
    """Raised when a service request times out."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Service request timed out",
            code=ErrorCode.SERVICE_TIMEOUT,
            severity=ErrorSeverity.HIGH,
            user_message="The request took too long to complete. Please try again",
            **kwargs
        )


class ExternalServiceError(ServiceError):
    """Raised when an external service fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "External service error",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


# AgentTimeoutError is now consolidated in exceptions_agent.py (SSOT compliance)
# This eliminates the circular import while maintaining backward compatibility


class LLMRequestError(NetraException):
    """Raised when LLM request fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "LLM request failed",
            code=ErrorCode.LLM_REQUEST_FAILED,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class LLMRateLimitError(LLMRequestError):
    """Raised when LLM rate limit is exceeded."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "LLM rate limit exceeded",
            code=ErrorCode.LLM_RATE_LIMIT_EXCEEDED,
            severity=ErrorSeverity.MEDIUM,
            user_message="Too many requests. Please wait a moment and try again",
            **kwargs
        )


class ProcessingError(ServiceError):
    """Raised when data processing operations fail."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Data processing failed",
            code=ErrorCode.DATA_VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )