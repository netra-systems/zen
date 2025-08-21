"""WebSocket heartbeat and connection health monitoring - Backward Compatibility Layer.

Provides backward compatibility imports while delegating to focused modules.
Keeps file under 300 lines as required by architecture standards.
"""

# Import all classes and functions from focused modules for backward compatibility
from netra_backend.app.heartbeat_config import HeartbeatConfig
from netra_backend.app.heartbeat_manager import HeartbeatManager

from . import heartbeat_utils

# Re-export all classes and functions for backward compatibility
__all__ = [
    'HeartbeatConfig',
    'HeartbeatManager',
    'heartbeat_utils'
]