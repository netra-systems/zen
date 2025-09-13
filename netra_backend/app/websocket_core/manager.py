"""WebSocket Manager - Import Compatibility Module

This module provides backward compatibility for the legacy import path:
from netra_backend.app.websocket_core.manager import WebSocketManager

CRITICAL: This is an SSOT compatibility layer that re-exports the unified WebSocket manager
to maintain existing import paths while consolidating the actual implementation.

PHASE 1 UPDATE: Now imports directly from unified_manager.py (SSOT)
- Legacy: from netra_backend.app.websocket_core.manager import WebSocketManager  
- SSOT: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

Business Justification:
- Maintains backward compatibility for existing tests and Golden Path functionality
- Prevents breaking changes during WebSocket SSOT consolidation
- Supports mission-critical Golden Path user flow ($500K+ ARR dependency)
"""

# Import directly from unified_manager.py (SSOT) - Phase 1 consolidation
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    _serialize_message_safely,
    WebSocketManagerMode
)

# Create compatibility alias
WebSocketManager = UnifiedWebSocketManager

# Import protocol for type checking
try:
    from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
except ImportError:
    WebSocketManagerProtocol = None

# Re-export for compatibility
__all__ = [
    'WebSocketManager',
    'WebSocketConnection', 
    'WebSocketManagerProtocol',
    '_serialize_message_safely',
    'UnifiedWebSocketManager'
]