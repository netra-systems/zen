"""WebSocket management modules.

This package contains the unified WebSocket manager functionality.
All WebSocket operations should use the unified manager system.
"""

# Import from unified WebSocket system
try:
    from netra_backend.app.websocket.unified.manager import (
        UnifiedWebSocketManager,
        get_unified_manager
    )
except ImportError:
    UnifiedWebSocketManager = None
    get_unified_manager = None

try:
    from netra_backend.app.websocket.connection import ConnectionInfo, ConnectionManager
except ImportError:
    ConnectionInfo = None
    ConnectionManager = None

try:
    from netra_backend.app.websocket.heartbeat_manager import HeartbeatManager
except ImportError:
    HeartbeatManager = None

# For backward compatibility, provide access to the unified manager
try:
    from netra_backend.app.ws_manager import WebSocketManager
except ImportError:
    WebSocketManager = None

__all__ = [
    'ConnectionInfo',
    'ConnectionManager', 
    'HeartbeatManager',
    'UnifiedWebSocketManager',
    'get_unified_manager',
    'WebSocketManager'
]