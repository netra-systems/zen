"""WebSocket management modules.

This package contains the refactored WebSocket manager functionality,
split into focused modules for better maintainability.
"""

from netra_backend.app.connection import ConnectionInfo, ConnectionManager
from netra_backend.app.services.api_gateway.rate_limiter import RateLimiter
from netra_backend.app.services.corpus.validation import MessageValidator
from netra_backend.app.broadcast import BroadcastManager
from netra_backend.app.room_manager import RoomManager
from netra_backend.app.heartbeat import HeartbeatManager
from netra_backend.app.services.synthetic_data.error_handler import WebSocketErrorHandler

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