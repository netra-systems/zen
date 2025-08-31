"""
WebSocket connection validation utilities.
Compatibility module for test support.
"""

from typing import Any


class ConnectionValidator:
    """Validates WebSocket connections."""
    
    @staticmethod
    def is_websocket_connected(websocket: Any) -> bool:
        """Check if WebSocket is connected."""
        if not websocket:
            return False
        
        # Check if websocket has a client_state indicating it's connected
        if hasattr(websocket, 'client_state'):
            state = getattr(websocket.client_state, 'name', None)
            return state == "CONNECTED"
        
        # Default to True if we can't determine state
        return True