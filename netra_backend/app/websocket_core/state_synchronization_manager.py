# Shim module for backward compatibility
from netra_backend.app.websocket_core.manager import WebSocketManager as StateSynchronizationManager
from netra_backend.app.websocket_core.manager import sync_state

__all__ = ['StateSynchronizationManager', 'sync_state']
