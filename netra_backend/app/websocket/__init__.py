# Shim module for backward compatibility
# WebSocket functionality moved to websocket_core

# DEPRECATED: Use canonical import path instead
# OLD: from netra_backend.app.websocket import WebSocketManager  
# NEW: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
import warnings
warnings.warn(
    "Importing WebSocketManager from 'netra_backend.app.websocket' is deprecated. "
    "Use 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' instead.",
    DeprecationWarning,
    stacklevel=2
)

from netra_backend.app.websocket_core import *
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.types import *

# Import compatibility classes from connection_manager
from netra_backend.app.websocket.connection_manager import (
    ConnectionManager,
    ConnectionInfo,
    get_connection_manager,
    get_connection_monitor
)
