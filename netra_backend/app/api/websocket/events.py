"""WebSocket Events API - SSOT Bridge Module.

This module provides a bridge to the SSOT WebSocket event types implementation.
All WebSocket event definitions are consolidated in shared.types.core_types.

Business Value:
- Maintains backward compatibility for existing imports expecting API-style WebSocket events
- Redirects to SSOT implementation to eliminate code duplication
- Ensures all WebSocket event handling uses the same strongly-typed system

Architecture:
- Bridge pattern to maintain import compatibility
- All functionality delegated to shared.types.core_types
- Strongly typed event system preserved from SSOT implementation
"""

# SSOT Import - redirect to the unified implementation
from shared.types.core_types import (
    WebSocketEventType,
    WebSocketMessage,
    WebSocketConnectionInfo,
    WebSocketID,
    UserID,
    ThreadID,
    RequestID
)

# Backward compatibility aliases
WebSocketConnection = WebSocketConnectionInfo

# Export for backward compatibility
__all__ = [
    'WebSocketEventType',
    'WebSocketMessage',
    'WebSocketConnection',
    'WebSocketConnectionInfo',
    'WebSocketID',
    'UserID',
    'ThreadID', 
    'RequestID'
]