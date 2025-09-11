"""WebSocket Manager - Import Compatibility Module

This module provides backward compatibility for the legacy import path:
from netra_backend.app.websocket_core.manager import WebSocketManager

CRITICAL: This is an SSOT compatibility layer that re-exports the unified WebSocket manager
to maintain existing import paths while consolidating the actual implementation.

Import Pattern:
- Legacy: from netra_backend.app.websocket_core.manager import WebSocketManager
- SSOT: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

Business Justification:
- Maintains backward compatibility for existing tests and Golden Path functionality
- Prevents breaking changes during WebSocket SSOT consolidation
- Supports mission-critical Golden Path user flow ($500K+ ARR dependency)
"""

from netra_backend.app.websocket_core.websocket_manager import (
    WebSocketManager,
    WebSocketConnection,
    WebSocketManagerProtocol,
    _serialize_message_safely
)

# Import UnifiedWebSocketManager from unified_manager for compatibility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Re-export for compatibility
__all__ = [
    'WebSocketManager',
    'WebSocketConnection', 
    'WebSocketManagerProtocol',
    '_serialize_message_safely',
    'UnifiedWebSocketManager'
]