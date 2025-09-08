# Shim module for backward compatibility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core import create_websocket_manager
WebSocketRecoveryManager = UnifiedWebSocketManager
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

def get_reconnection_handler(user_id: str = None) -> WebSocketRecoveryManager:
    """Get the reconnection handler with proper user context.
    
    SECURITY FIX: Now requires user_id for proper isolation.
    If no user_id provided, creates a default context for backward compatibility.
    """
    if user_id:
        # SECURITY: Create proper user context for isolated WebSocket manager
        context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=f"reconnection_{user_id}",
            run_id=f"reconnection_run_{user_id}"
        )
        return create_websocket_manager(context=context)
    else:
        # BACKWARD COMPATIBILITY: Default context for legacy callers
        # TODO: All callers should provide user_id for security
        # SECURITY FIX: Log warning and return None to encourage proper usage
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "ReconnectionHandler called without user_id - this is a security risk. "
            "Please provide user_id for proper isolation."
        )
        return None

# Export for backward compatibility
__all__ = [
    'ReconnectionHandler', 
    'WebSocketRecoveryManager', 
    'ConnectionState', 
    'ReconnectionReason', 
    'ReconnectionContext',
    'get_reconnection_handler'
]