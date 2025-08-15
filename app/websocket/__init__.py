"""WebSocket management modules.

This package contains the refactored WebSocket manager functionality,
split into focused modules for better maintainability.
"""

from .connection import ConnectionInfo, ConnectionManager
from .rate_limiter import RateLimiter
from .validation import MessageValidator
from .broadcast import BroadcastManager
from .room_manager import RoomManager
from .heartbeat import HeartbeatManager
from .error_handler import WebSocketErrorHandler

__all__ = [
    'ConnectionInfo',
    'ConnectionManager', 
    'RateLimiter',
    'MessageValidator',
    'BroadcastManager',
    'RoomManager',
    'HeartbeatManager',
    'WebSocketErrorHandler'
]