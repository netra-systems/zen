# Shim module for backward compatibility
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
StateSynchronizationManager = UnifiedWebSocketManager

# Create a stub sync_state function for backward compatibility
def sync_state(state):
    """Stub function for backward compatibility. State synchronization is now handled by UnifiedWebSocketManager."""
    pass

__all__ = ['StateSynchronizationManager', 'sync_state']
