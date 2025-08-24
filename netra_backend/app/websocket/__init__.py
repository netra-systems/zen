# Shim module for backward compatibility
# WebSocket functionality moved to websocket_core
from netra_backend.app.websocket_core import *
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.websocket_core.types import *

# Import compatibility classes from connection_manager
from netra_backend.app.websocket.connection_manager import (
    ConnectionManager,
    ConnectionInfo,
    get_connection_manager,
    get_connection_monitor
)
