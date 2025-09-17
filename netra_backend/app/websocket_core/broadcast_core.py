# Shim module for backward compatibility
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as BroadcastManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as BroadcastCore
WebSocketManager = BroadcastManager  # Backward compatibility alias
