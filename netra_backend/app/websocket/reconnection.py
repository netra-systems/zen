"""WebSocket Reconnection System - Backward Compatibility Layer.

Provides backward compatibility imports while delegating to focused modules.
Keeps file under 300 lines as required by architecture standards.
"""

# Import all types and classes from focused modules for backward compatibility
from netra_backend.app.reconnection_global import GlobalReconnectionManager
from netra_backend.app.reconnection_manager import WebSocketReconnectionManager
from netra_backend.app.reconnection_types import (
    DisconnectReason,
    ReconnectionAttempt,
    ReconnectionConfig,
    ReconnectionMetrics,
    ReconnectionState,
)

# Re-export all classes and types for backward compatibility
__all__ = [
    'ReconnectionState',
    'DisconnectReason',
    'ReconnectionConfig', 
    'ReconnectionAttempt',
    'ReconnectionMetrics',
    'WebSocketReconnectionManager',
    'GlobalReconnectionManager'
]