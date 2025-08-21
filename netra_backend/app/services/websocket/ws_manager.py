"""WebSocket Manager - Service Import Compatibility

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable test execution and prevent websocket import errors
- Value Impact: Ensures test suite can import websocket manager dependencies
- Strategic Impact: Maintains compatibility for websocket functionality

This module provides a compatibility layer for code that expects websocket manager
imports from app.services.websocket.ws_manager. The actual implementation is in app.ws_manager.
"""

# Import the actual WebSocket manager from its real location
from netra_backend.app.ws_manager import (
    WebSocketManager,
    get_ws_manager,
    manager as ws_manager_instance
)

# Export all the common symbols that tests might expect
__all__ = [
    "WebSocketManager", 
    "get_ws_manager", 
    "ws_manager_instance",
    "manager"
]

# Provide common aliases for compatibility
manager = ws_manager_instance