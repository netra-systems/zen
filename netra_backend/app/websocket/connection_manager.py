"""
WebSocket Connection Manager - Compatibility Shim

This module provides a compatibility layer for legacy imports that expect
netra_backend.app.websocket.connection_manager. The actual implementation
has been moved to websocket_core.

Business Value: Platform/Internal - Maintains backward compatibility
Prevents breaking changes for existing imports while system transitions to new structure.
"""

# Import the actual implementations from websocket_core
from netra_backend.app.websocket_core.manager import WebSocketManager as CoreManager
from netra_backend.app.websocket_core.connection_info import ConnectionInfo as CoreConnectionInfo
from netra_backend.app.websocket_core.types import WebSocketConnectionState, WebSocketMessage


class ConnectionManager(CoreManager):
    """
    Compatibility wrapper for WebSocket connection management.
    
    Delegates all functionality to the core WebSocket manager while
    maintaining the expected interface for legacy code.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize connection manager with compatibility layer."""
        super().__init__(*args, **kwargs)


class ConnectionInfo(CoreConnectionInfo):
    """
    Compatibility wrapper for connection information.
    
    Maintains the expected interface while delegating to core implementation.
    """
    pass


# Compatibility functions
def get_connection_manager():
    """Get the global connection manager instance."""
    from netra_backend.app.websocket_core.manager import get_manager
    return get_manager()


def get_connection_monitor():
    """Get connection monitoring instance."""
    # Delegate to core monitoring functionality
    manager = get_connection_manager()
    return manager


# Export the compatibility classes
__all__ = [
    'ConnectionManager',
    'ConnectionInfo', 
    'WebSocketConnectionState',
    'WebSocketMessage',
    'get_connection_manager',
    'get_connection_monitor'
]

# Create alias for backward compatibility
ConnectionState = WebSocketConnectionState