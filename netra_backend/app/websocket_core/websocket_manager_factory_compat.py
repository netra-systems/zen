"""
WebSocket manager factory compatibility - COMPATIBILITY SHIM

This module provides backward compatibility during WebSocket Manager import consolidation.

DEPRECATED: This import path is deprecated as part of Issue #1196 remediation.
Use canonical import: from netra_backend.app.websocket_core.canonical_imports import ...

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
    f"'netra_backend.app.websocket_core.canonical_imports' instead. This compatibility shim will be "
    f"removed in Phase 2.",
    DeprecationWarning,
    stacklevel=2
)

# Import from canonical SSOT source
from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager as _canonical_create_websocket_manager
create_websocket_manager = _canonical_create_websocket_manager

# REMOVED: WebSocketManagerFactory no longer available - use get_websocket_manager() instead
# from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory as _CanonicalWebSocketManagerFactory
# WebSocketManagerFactory = _CanonicalWebSocketManagerFactory

from netra_backend.app.websocket_core.canonical_imports import get_websocket_manager_factory as _canonical_get_websocket_manager_factory
get_websocket_manager_factory = _canonical_get_websocket_manager_factory

__all__ = ['create_websocket_manager', 'get_websocket_manager_factory']  # Removed: 'WebSocketManagerFactory'


def _validate_compatibility_usage():
    """Track usage of deprecated import paths for migration planning."""
    from shared.logging.unified_logging_ssot import get_logger
    logger = get_logger(__name__)
    logger.warning(
        f"COMPATIBILITY: Deprecated WebSocket import path used. "
        f"Please migrate to canonical import from netra_backend.app.websocket_core.canonical_imports"
    )

# Call validation on import
_validate_compatibility_usage()
