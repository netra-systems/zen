"""WebSocket recovery module - imports consolidated after refactoring.

This module re-exports recovery-related classes from their new locations
to maintain backward compatibility with existing tests.
"""

# Import from actual locations and re-export
from netra_backend.app.core.exceptions_websocket import WebSocketError
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as UnifiedWebSocketManager
WebSocketRecoveryManager = UnifiedWebSocketManager
from netra_backend.app.core.unified_error_handler import RecoveryStrategy

# Create alias for backward compatibility
ErrorRecoveryHandler = WebSocketRecoveryManager

# Re-export for backward compatibility
__all__ = [
    'WebSocketError',
    'WebSocketRecoveryManager',
    'RecoveryStrategy',
    'ErrorRecoveryHandler',  # Alias for WebSocketRecoveryManager
]