# Shim module for backward compatibility
from netra_backend.app.core.websocket_recovery_manager import WebSocketRecoveryManager
from netra_backend.app.core.websocket_recovery_types import ConnectionState, ReconnectionReason

# Alias for backward compatibility
ReconnectionHandler = WebSocketRecoveryManager

# Mock context class for backward compatibility
class ReconnectionContext:
    """Mock reconnection context for backward compatibility."""
    def __init__(self, user_id: str, connection_id: str = None):
        self.user_id = user_id
        self.connection_id = connection_id or f"conn_{user_id}"
        self.timestamp = None
        self.reason = None
        self.state = ConnectionState.CONNECTING

# Global reconnection handler instance
_reconnection_handler = None

def get_reconnection_handler() -> WebSocketRecoveryManager:
    """Get the global reconnection handler."""
    global _reconnection_handler
    if _reconnection_handler is None:
        _reconnection_handler = WebSocketRecoveryManager()
    return _reconnection_handler

# Export for backward compatibility
__all__ = [
    'ReconnectionHandler', 
    'WebSocketRecoveryManager', 
    'ConnectionState', 
    'ReconnectionReason', 
    'ReconnectionContext',
    'get_reconnection_handler'
]