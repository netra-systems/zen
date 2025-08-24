"""WebSocket recovery module - imports consolidated after refactoring.

This module re-exports recovery-related classes from their new locations
to maintain backward compatibility with existing tests.
"""

# Import from actual locations and re-export
from netra_backend.app.core.exceptions_websocket import WebSocketError
from netra_backend.app.core.websocket_recovery_manager import WebSocketRecoveryManager
from netra_backend.app.error_handling.example_message_errors import RecoveryStrategy

# Re-export for backward compatibility
__all__ = [
    'WebSocketError',
    'WebSocketRecoveryManager',
    'RecoveryStrategy',
]