"""
Message Router Module - SSOT Proxy Implementation (Phase 1)

⚠️ DEPRECATION WARNING: This module is deprecated as of SSOT Phase 1 consolidation.
Please use the canonical MessageRouter from: netra_backend.app.websocket_core.handlers

MIGRATION PATH:
- OLD: from netra_backend.app.core.message_router import MessageRouter
- NEW: from netra_backend.app.websocket_core.handlers import MessageRouter

This module now provides a PROXY implementation that forwards all calls to the canonical SSOT MessageRouter.
All method calls are routed to the canonical implementation in websocket_core.handlers.

SSOT COMPLIANCE STATUS: PHASE 1 COMPLETE
- Proxy routes all calls to canonical MessageRouter
- Maintains backward compatibility during transition
- Provides deprecation warnings with migration guidance
- NO BREAKING CHANGES - all existing imports continue working

Business Value Justification:
- Segment: Platform/Internal - System Stability & Golden Path Protection
- Business Goal: Eliminate MessageRouter SSOT violations while maintaining compatibility
- Value Impact: Protects $500K+ ARR chat functionality from routing conflicts
- Strategic Impact: Enables safe SSOT consolidation without breaking existing code
"""

import warnings
from typing import Any, Dict, List, Optional, Union, Callable

# Import the canonical SSOT MessageRouter
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
from netra_backend.app.websocket_core.handlers import get_message_router

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MessageRouter:
    """
    SSOT Proxy MessageRouter - forwards all calls to canonical implementation.

    ⚠️ DEPRECATION WARNING: This is a proxy for backward compatibility.
    Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead.
    
    This proxy ensures all MessageRouter functionality is provided by the canonical SSOT implementation
    while maintaining complete backward compatibility during the transition period.
    """

    def __init__(self):
        """Initialize proxy router with deprecation warning and canonical delegation."""
        # Issue deprecation warning with clear migration guidance
        warnings.warn(
            "MessageRouter from netra_backend.app.core.message_router is deprecated. "
            "Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead. "
            "This proxy will be removed in Phase 2 of SSOT consolidation.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Get canonical router instance (SSOT compliance)
        self._canonical_router = get_message_router()
        
        logger.warning("DEPRECATED PROXY: MessageRouter proxy initialized - "
                      "All calls forwarded to canonical SSOT implementation. "
                      "Use netra_backend.app.websocket_core.handlers.MessageRouter instead.")

    def add_route(self, pattern: str, handler: Callable) -> None:
        """Add a route handler - proxied to canonical implementation."""
        logger.debug(f"PROXY: add_route({pattern}) -> canonical MessageRouter")
        return self._canonical_router.add_route(pattern, handler)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to processing pipeline - proxied to canonical implementation."""
        logger.debug(f"PROXY: add_middleware({getattr(middleware, '__name__', 'unknown')}) -> canonical MessageRouter")
        return self._canonical_router.add_middleware(middleware)

    def start(self) -> None:
        """Start the message router - proxied to canonical implementation."""
        logger.debug("PROXY: start() -> canonical MessageRouter")
        return self._canonical_router.start()

    def stop(self) -> None:
        """Stop the message router - proxied to canonical implementation."""
        logger.debug("PROXY: stop() -> canonical MessageRouter")
        return self._canonical_router.stop()

    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics - proxied to canonical implementation."""
        logger.debug("PROXY: get_statistics() -> canonical MessageRouter")
        stats = self._canonical_router.get_statistics()
        # Add proxy information for debugging
        stats["proxy_info"] = {
            "is_proxy": True,
            "canonical_source": "netra_backend.app.websocket_core.handlers.MessageRouter",
            "deprecation_status": "Phase 1 proxy - will be removed in Phase 2"
        }
        return stats

    # Forward all other attributes to the canonical router
    def __getattr__(self, name: str) -> Any:
        """Forward any unknown attributes to the canonical router."""
        logger.debug(f"PROXY: {name} -> canonical MessageRouter")
        return getattr(self._canonical_router, name)

    # Properties that need special handling
    @property
    def handlers(self) -> List[Any]:
        """Get handlers from canonical router."""
        return self._canonical_router.handlers

    @property 
    def routes(self) -> Dict[str, List[Callable]]:
        """Get routes from canonical router (compatibility)."""
        # For backward compatibility with tests expecting .routes attribute
        return getattr(self._canonical_router, '_test_routes', {})

    @property
    def middleware(self) -> List[Callable]:
        """Get middleware from canonical router (compatibility)."""
        # For backward compatibility with tests expecting .middleware attribute
        return getattr(self._canonical_router, '_test_middleware', [])

    @property
    def active(self) -> bool:
        """Get active status from canonical router (compatibility)."""
        # For backward compatibility with tests expecting .active attribute
        return getattr(self._canonical_router, '_test_active', False)


# Legacy compatibility types - imported from canonical source
from netra_backend.app.websocket_core.types import WebSocketMessage as Message
from netra_backend.app.websocket_core.types import MessageType

# Global instance for compatibility
message_router = MessageRouter()

# Export definitions for backward compatibility
__all__ = [
    "MessageRouter", 
    "Message",
    "MessageType",
    "message_router"
]