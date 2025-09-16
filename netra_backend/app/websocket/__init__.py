# Shim module for backward compatibility
# WebSocket functionality moved to websocket_core

# DEPRECATED: Use canonical import path instead
# OLD: from netra_backend.app.websocket import WebSocketManager  
# NEW: from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
import warnings
warnings.warn(
    "Importing WebSocketManager from 'netra_backend.app.websocket' is deprecated. "
    "Use 'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import specific components instead of wildcard import
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.websocket_core.event_validator import get_websocket_validator

__all__ = ["WebSocketManager", "MessageRouter", "get_message_router", "get_websocket_validator"]
from netra_backend.app.websocket_core.types import *

# Import compatibility classes from connection_manager
from netra_backend.app.websocket.connection_manager import (
    ConnectionManager,
    ConnectionInfo,
    get_connection_manager,
    get_connection_monitor
)
