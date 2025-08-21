"""WebSocket unified types module - Re-exports common types for unified websocket system.

This module provides a unified interface for websocket-related types and errors.
"""

# Re-export validation error from the schemas module
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError

# Re-export other commonly used types if needed
# This provides a consistent import path for tests and other modules

__all__ = [
    "WebSocketValidationError",
]