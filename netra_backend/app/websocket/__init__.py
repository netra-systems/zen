"""WebSocket management modules.

This package contains the refactored WebSocket manager functionality,
split into focused modules for better maintainability.
"""

# Conditional imports to avoid circular dependencies
try:
    from netra_backend.app.core.websocket_connection_manager import (
        WebSocketConnectionManager as ConnectionManager,
    )
except ImportError:
    ConnectionManager = None

try:
    from netra_backend.app.websocket.connection_info import ConnectionInfo
except ImportError:
    ConnectionInfo = None

try:
    from netra_backend.app.websocket.heartbeat_manager import HeartbeatManager
except ImportError:
    HeartbeatManager = None

# WebSocket error handler import removed - module not found

__all__ = [
    'ConnectionInfo',
    'ConnectionManager',
    'HeartbeatManager'
]