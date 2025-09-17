"""
WebSocket services package.

Provides subscription-based broadcasting and message management services.
"""

# BroadcastManager removed - use UnifiedWebSocketManager from websocket_core instead
# from netra_backend.app.services.websocket.broadcast_manager import BroadcastManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as BroadcastManager

__all__ = ['BroadcastManager']