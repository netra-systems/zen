"""
Message Router - Routes Bridge Module
ISSUE: Test Infrastructure Remediation - Golden Path Phase 3

PURPOSE: Provides the missing import path that mission critical tests expect:
    from netra_backend.app.routes.message_router import MessageRouter

PROBLEM: 10 collection errors in mission critical tests due to missing import path
SOLUTION: Bridge module that routes to canonical SSOT implementation

BUSINESS VALUE:
- Unblocks mission critical test execution
- Protects $500K+ ARR Golden Path validation
- Enables complete test infrastructure SSOT compliance

CREATED: 2025-09-16 (Golden Path Phase 3 Test Infrastructure Fix)
"""

import warnings
from typing import Dict, Any, Optional

# Import canonical SSOT implementation
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
    "GOLDEN PATH PHASE 3: MessageRouter import from 'app.routes.message_router' is a "
    "test infrastructure bridge. Production code should use "
    "'from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter'. "
    "This bridge exists only to fix mission critical test collection errors.",
    DeprecationWarning,
    stacklevel=2
)

# Primary alias for tests expecting MessageRouter from routes
MessageRouter = CanonicalMessageRouter

# Additional aliases for test compatibility
WebSocketMessageRouter = CanonicalMessageRouter
UnifiedMessageRouter = CanonicalMessageRouter

# Factory function for tests
def create_router(user_context: Optional[Dict[str, Any]] = None) -> CanonicalMessageRouter:
    """
    Factory function for creating MessageRouter instances (test compatibility)
    
    Args:
        user_context: Optional user context for isolation
        
    Returns:
        CanonicalMessageRouter: Router instance
    """
    warnings.warn(
        "create_router() from routes module is deprecated. Use canonical "
        "create_message_router() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return create_message_router(user_context)

# Export canonical factory for preferred usage
get_message_router = create_message_router

# Test infrastructure validation
__all__ = [
    'MessageRouter',
    'WebSocketMessageRouter', 
    'UnifiedMessageRouter',
    'create_router',
    'get_message_router',
    'create_message_router',
    'CanonicalMessageRouter',
    'MessageRoutingStrategy',
    'RoutingContext',
    'RouteDestination',
    'SSOT_INFO'
]