"""
Legacy WebSocket Message Router - Compatibility Alias

ISSUE #994: WebSocket Message Routing SSOT Consolidation Phase 1
This module provides backwards compatibility for existing imports while
directing all usage to the canonical implementation.

DEPRECATION NOTICE:
This module is deprecated as part of SSOT consolidation. Use the canonical
implementation directly:

    from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter

BACKWARDS COMPATIBILITY:
All existing imports continue to work but will show deprecation warnings.
This file will be removed in Phase 2 of SSOT consolidation.

Created: 2025-09-15 (Issue #994 Phase 1 - Compatibility Layer)
"""

import warnings
from typing import Dict, Any, Optional

# Import canonical implementation
from netra_backend.app.websocket_core.canonical_message_router import (
    CanonicalMessageRouter,
    MessageRoutingStrategy,
    RoutingContext,
    RouteDestination,
    create_message_router,
    SSOT_INFO
)

# Show deprecation warning for this import path
warnings.warn(
    "ISSUE #994: MessageRouter import from 'websocket_core.message_router' is deprecated. "
    "Use 'from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter' instead. "
    "This import path will be removed in Phase 2 of SSOT consolidation.",
    DeprecationWarning,
    stacklevel=2
)

# Legacy aliases for backwards compatibility
MessageRouter = CanonicalMessageRouter
WebSocketMessageRouter = CanonicalMessageRouter
MessageRouterSST = CanonicalMessageRouter
UnifiedMessageRouter = CanonicalMessageRouter

# Legacy factory functions
def create_router(user_context: Optional[Dict[str, Any]] = None) -> CanonicalMessageRouter:
    """DEPRECATED: Use create_message_router() instead"""
    warnings.warn(
        "create_router() is deprecated. Use create_message_router() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return create_message_router(user_context)

def get_message_router(user_context: Optional[Dict[str, Any]] = None) -> CanonicalMessageRouter:
    """DEPRECATED: Use create_message_router() instead"""
    warnings.warn(
        "get_message_router() is deprecated. Use create_message_router() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return create_message_router(user_context)

# Export all canonical symbols for compatibility
__all__ = [
    # Primary class (legacy alias)
    'MessageRouter',
    'WebSocketMessageRouter',
    'MessageRouterSST',
    'UnifiedMessageRouter',

    # Canonical class (preferred)
    'CanonicalMessageRouter',

    # Supporting types
    'MessageRoutingStrategy',
    'RoutingContext',
    'RouteDestination',

    # Factory functions
    'create_message_router',
    'create_router',  # deprecated
    'get_message_router',  # deprecated

    # Metadata
    'SSOT_INFO'
]

# SSOT compatibility information
COMPATIBILITY_INFO = {
    'status': 'deprecated',
    'phase': 'Phase 1 - Backwards compatibility',
    'removal_planned': 'Phase 2 - SSOT consolidation complete',
    'canonical_module': 'canonical_message_router',
    'migration_guide': 'Use CanonicalMessageRouter directly from canonical_message_router module'
}