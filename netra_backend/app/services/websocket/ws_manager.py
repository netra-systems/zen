"""WebSocket Manager - Service Import Compatibility

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable test execution and prevent websocket import errors
- Value Impact: Ensures test suite can import websocket manager dependencies
- Strategic Impact: Maintains compatibility for websocket functionality

This module provides a compatibility layer for code that expects websocket manager
imports from netra_backend.app.services.websocket.ws_manager. The actual implementation is in app.ws_manager.
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.ws_manager import WebSocketManager

# Use lazy imports to avoid circular dependencies
_manager = None
_WebSocketManager = None
_get_ws_manager = None
_get_manager = None

def _lazy_import():
    """Lazily import the WebSocket manager to avoid circular imports."""
    global _manager, _WebSocketManager, _get_ws_manager, _get_manager
    if _manager is None:
        from netra_backend.app.ws_manager import WebSocketManager as _WSM
        from netra_backend.app.ws_manager import get_manager as _get_mgr
        from netra_backend.app.ws_manager import get_ws_manager as _get_ws
        from netra_backend.app.ws_manager import manager as _mgr
        _WebSocketManager = _WSM
        _get_ws_manager = _get_ws
        _get_manager = _get_mgr
        _manager = _mgr
    return _manager, _WebSocketManager, _get_ws_manager, _get_manager


class _LazyModule:
    """Lazy module wrapper to defer imports until access."""
    
    def __getattr__(self, name):
        if name in ("manager", "ws_manager", "ws_manager_instance"):
            mgr, _, _, _ = _lazy_import()
            # Cache for future access
            setattr(self, name, mgr)
            return mgr
        elif name == "WebSocketManager":
            _, WSM, _, _ = _lazy_import()
            setattr(self, name, WSM)
            return WSM
        elif name == "get_ws_manager":
            _, _, get_ws, _ = _lazy_import()
            setattr(self, name, get_ws)
            return get_ws
        elif name == "get_manager":
            _, _, _, get_mgr = _lazy_import()
            setattr(self, name, get_mgr)
            return get_mgr
        raise AttributeError(f"module has no attribute '{name}'")

# Replace the module with our lazy wrapper
sys.modules[__name__] = _LazyModule()