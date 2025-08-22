"""WebSocket Manager Compatibility Module

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable test execution by providing import compatibility
- Value Impact: Resolves 43 test failures due to missing websocket_manager imports
- Strategic Impact: Maintains backward compatibility for WebSocket functionality

This module provides import compatibility for code that expects:
from netra_backend.app.services.websocket_manager import WebSocketManager

The actual implementation resides in:
- netra_backend.app.ws_manager (main WebSocket manager)
- netra_backend.app.services.websocket.ws_manager (service layer compatibility)
"""

from netra_backend.app.ws_manager import (
    WebSocketManager,
    get_manager,
    get_ws_manager,
    manager,
)

# Expose all the commonly used WebSocket manager components
__all__ = [
    'WebSocketManager',
    'get_ws_manager', 
    'get_manager',
    'manager'
]