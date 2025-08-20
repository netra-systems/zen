"""WebSocket exceptions - compliant with 25-line function limit."""

from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity


class WebSocketError(NetraException):
    """Base class for WebSocket-related exceptions."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "WebSocket error occurred",
            code=ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class WebSocketConnectionError(WebSocketError):
    """Raised when WebSocket connection fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "WebSocket connection failed",
            code=ErrorCode.WEBSOCKET_CONNECTION_FAILED,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class WebSocketMessageError(WebSocketError):
    """Raised when WebSocket message is invalid."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "Invalid WebSocket message",
            code=ErrorCode.WEBSOCKET_MESSAGE_INVALID,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class WebSocketAuthenticationError(WebSocketError):
    """Raised when WebSocket authentication fails."""
    
    def __init__(self, message: str = None, **kwargs):
        super().__init__(
            message=message or "WebSocket authentication failed",
            code=ErrorCode.WEBSOCKET_AUTHENTICATION_FAILED,
            severity=ErrorSeverity.HIGH,
            user_message="Authentication failed for WebSocket connection",
            **kwargs
        )