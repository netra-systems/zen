"""
Backward Compatibility Module for WebSocket Routes.

This module provides backward compatibility for tests and code that import
from the old websocket routes module. The actual unified WebSocket implementation
is in websocket_unified.py.

DEPRECATED: Use websocket_unified.py directly for new code.
"""

from fastapi import APIRouter

from netra_backend.app.routes.websocket_unified import router as unified_router

# Re-export the unified router for backward compatibility
router = unified_router

# Add deprecation warning for developers
import warnings
warnings.warn(
    "netra_backend.app.routes.websocket is deprecated. "
    "Use netra_backend.app.routes.websocket_unified instead.",
    DeprecationWarning,
    stacklevel=2
)