"""Core WebSocket broadcasting functionality - Backward Compatibility Layer.

Provides backward compatibility imports while delegating to focused modules.
Keeps file under 300 lines as required by architecture standards.
"""

# Import all classes and functions from focused modules for backward compatibility
from netra_backend.app.broadcast_core import BroadcastManager

from netra_backend.app.websocket import broadcast_utils

# Re-export all classes and functions for backward compatibility
__all__ = [
    'BroadcastManager',
    'broadcast_utils'
]