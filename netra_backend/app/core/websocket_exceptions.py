"""
WebSocket exceptions module.

Custom exceptions for WebSocket operations.
"""


class WebSocketConnectionError(Exception):
    """Raised when WebSocket connection fails."""
    pass


class WebSocketMessageError(Exception):
    """Raised when WebSocket message handling fails."""
    pass


class WebSocketTimeoutError(Exception):
    """Raised when WebSocket operation times out."""
    pass


class WebSocketAuthenticationError(Exception):
    """Raised when WebSocket authentication fails."""
    pass


class WebSocketValidationError(Exception):
    """Raised when WebSocket data validation fails."""
    pass