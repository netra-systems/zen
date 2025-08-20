"""Authentication and authorization exceptions - compliant with 25-line function limit."""

from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity


class AuthenticationError(NetraException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Authentication failed",
            code=ErrorCode.AUTHENTICATION_FAILED,
            severity=ErrorSeverity.HIGH,
            user_message="Please check your credentials and try again",
            **kwargs
        )


class AuthorizationError(NetraException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Access denied",
            code=ErrorCode.AUTHORIZATION_FAILED,
            severity=ErrorSeverity.HIGH,
            user_message="You don't have permission to perform this action",
            **kwargs
        )


class TokenExpiredError(NetraException):
    """Raised when authentication token has expired."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Authentication token has expired",
            code=ErrorCode.TOKEN_EXPIRED,
            severity=ErrorSeverity.HIGH,
            user_message="Your session has expired. Please log in again",
            **kwargs
        )


class TokenInvalidError(NetraException):
    """Raised when authentication token is invalid."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Authentication token is invalid",
            code=ErrorCode.TOKEN_INVALID,
            severity=ErrorSeverity.HIGH,
            user_message="Invalid authentication token. Please log in again",
            **kwargs
        )


class NetraSecurityException(NetraException):
    """Raised when security violations occur."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Security violation detected",
            code=ErrorCode.SECURITY_VIOLATION,
            severity=ErrorSeverity.CRITICAL,
            user_message="Security violation detected. Access denied",
            **kwargs
        )