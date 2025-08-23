"""WebSocket Connection Manager
 
Main entry point for WebSocket connection management.
Provides a unified interface to the various connection management components.

Business Value: Eliminates connection management complexity by providing a
single entry point for all WebSocket connection operations.
"""

from netra_backend.app.logging_config import central_logger

# Import the primary connection management implementation
from netra_backend.app.websocket.load_balanced_connection_manager import (
    LoadBalancedConnectionManager
)

# Import connection registry for connection tracking
from netra_backend.app.websocket.connection_registry import (
    ConnectionRegistry,
    ConnectionInfoProvider,
    ConnectionCleanupManager
)

# Import basic WebSocket manager for simple operations
from netra_backend.app.websocket.ws_manager import WebSocketManager

logger = central_logger.get_logger(__name__)

# Main connection manager - uses load balanced implementation
ConnectionManager = LoadBalancedConnectionManager

def get_connection_manager() -> LoadBalancedConnectionManager:
    """Get the main connection manager instance."""
    return LoadBalancedConnectionManager()

def get_simple_websocket_manager() -> WebSocketManager:
    """Get a simple WebSocket manager for basic operations."""
    return WebSocketManager()

# Export all for backward compatibility
__all__ = [
    'ConnectionManager',
    'get_connection_manager', 
    'get_simple_websocket_manager',
    'ConnectionRegistry',
    'ConnectionInfoProvider',
    'ConnectionCleanupManager',
    'WebSocketManager'
]