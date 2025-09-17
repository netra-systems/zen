"""
WebSocket core package-level import compatibility - COMPATIBILITY SHIM

This module provides backward compatibility during WebSocket Manager import consolidation.

DEPRECATED: This import path is deprecated as part of Issue #1196 remediation.
Use canonical import: from netra_backend.app.websocket_core.websocket_manager import ...

PHASE 1 COMPATIBILITY: This shim prevents breaking changes during systematic
import consolidation while providing deprecation warnings to guide migration.

Business Value Protection:
- Maintains Golden Path functionality during transition
- Prevents import errors in existing code
- Guides developers to canonical SSOT imports
"""

import warnings
from typing import TYPE_CHECKING

# Issue #1196 Phase 1: Compatibility warning for deprecated import path
warnings.warn(
    f"DEPRECATED: This import path is deprecated as part of WebSocket Manager "
    f"import consolidation (Issue #1196). Use canonical import from "
    f"'netra_backend.app.websocket_core.websocket_manager' instead. This compatibility shim will be "
    f"removed in Phase 2.",
    DeprecationWarning,
    stacklevel=2
)

# Import from canonical SSOT source
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as _CanonicalWebSocketManager
WebSocketManager = _CanonicalWebSocketManager

from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as _CanonicalWebSocketManager
UnifiedWebSocketManager = _CanonicalWebSocketManager  # Legacy alias

from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager as _canonical_get_websocket_manager
get_websocket_manager = _canonical_get_websocket_manager

__all__ = ['WebSocketManager', 'get_websocket_manager', 'UnifiedWebSocketManager']


def _validate_compatibility_usage():
    """Track usage of deprecated import paths for migration planning."""
    from shared.logging.unified_logging_ssot import get_logger
    logger = get_logger(__name__)
    logger.warning(
        f"COMPATIBILITY: Deprecated WebSocket import path used. "
        f"Please migrate to canonical import from netra_backend.app.websocket_core.canonical_import_patterns"
    )

# Call validation on import
_validate_compatibility_usage()
