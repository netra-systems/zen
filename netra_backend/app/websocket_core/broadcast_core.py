# Shim module for backward compatibility
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as BroadcastManager
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as BroadcastCore
WebSocketManager = BroadcastManager  # Backward compatibility alias
