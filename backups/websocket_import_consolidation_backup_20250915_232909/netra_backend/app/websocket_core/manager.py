"""WebSocket Manager - Import Compatibility Module

This module provides backward compatibility for the legacy import path:
from netra_backend.app.websocket_core.manager import WebSocketManager

CRITICAL: This is an SSOT compatibility layer that re-exports the unified WebSocket manager
to maintain existing import paths while consolidating the actual implementation.

PHASE 1 SSOT CONSOLIDATION: Now imports from canonical websocket_manager.py (SSOT)
- Legacy: from netra_backend.app.websocket_core.manager import WebSocketManager  
- SSOT: from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

Business Justification:
- Maintains backward compatibility for existing tests and Golden Path functionality
- Prevents breaking changes during WebSocket SSOT consolidation
- Supports mission-critical Golden Path user flow ($500K+ ARR dependency)
"""

import warnings

# ISSUE #1182 REMEDIATION: Add deprecation warning for non-canonical imports
warnings.warn(
    "ISSUE #1182: Importing from 'netra_backend.app.websocket_core.manager' is deprecated. "
    "Use 'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager' instead. "
    "This import path will be removed in Phase 2 of SSOT consolidation.",
    DeprecationWarning,
    stacklevel=2
)

# ISSUE #824 REMEDIATION: Import from canonical SSOT path
# SSOT CONSOLIDATION: websocket_manager.py is the canonical import point
from netra_backend.app.websocket_core.canonical_import_patterns import (
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

# Import heartbeat functionality for compatibility
try:
    from netra_backend.app.websocket_core.utils import WebSocketHeartbeat
    # Create compatibility alias for tests expecting WebSocketHeartbeatManager
    WebSocketHeartbeatManager = WebSocketHeartbeat
except ImportError:
    WebSocketHeartbeat = None
    WebSocketHeartbeatManager = None

# Re-export for compatibility
__all__ = [
    'WebSocketManager',
    'WebSocketConnection',
    'WebSocketManagerProtocol',
    '_serialize_message_safely',
    'UnifiedWebSocketManager',
    'WebSocketHeartbeat',
    'WebSocketHeartbeatManager'  # Compatibility alias
]