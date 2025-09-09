# Legacy compatibility shim - redirects to the proper websocket_manager module
# NEW CODE: Use the dedicated websocket_manager.py for all WebSocket manager imports
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Keep backward compatibility for any legacy imports from manager.py
WebSocketManager = WebSocketManager