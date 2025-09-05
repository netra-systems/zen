# Shim module for backward compatibility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as BroadcastManager
WebSocketManager = BroadcastManager  # Backward compatibility alias
