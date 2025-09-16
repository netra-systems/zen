# Shim module for backward compatibility
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as BroadcastManager
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager as BroadcastCore
WebSocketManager = BroadcastManager  # Backward compatibility alias
