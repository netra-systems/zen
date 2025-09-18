"""
WebSocketEventRouter - Infrastructure for routing events to specific user connections.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: User Isolation & Event Security  
- Value Impact: Prevents cross-user event leakage, ensures proper event routing
- Strategic Impact: Enables secure multi-user chat functionality with guaranteed event isolation

This router manages WebSocket connection pools and routes events to specific user connections,
providing the infrastructure layer for per-user event emission without being a singleton itself.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager

logger = central_logger.get_logger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    connection_id: str
    user_id: str
    thread_id: Optional[str]
    connected_at: datetime
    last_activity: datetime
    
    def is_active(self) -> bool:
        """Check if connection is still active based on recent activity."""
        # Consider connection active if last activity was within 5 minutes
        return (datetime.now(timezone.utc) - self.last_activity).seconds < 300


# === SSOT CONSOLIDATION NOTICE ===
# WebSocketEventRouter functionality has been consolidated into CanonicalMessageRouter
# This file provides compatibility during migration phase

from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter


class WebSocketEventRouter(CanonicalMessageRouter):
    """
    COMPATIBILITY ADAPTER: WebSocketEventRouter consolidated into CanonicalMessageRouter.

    This class provides backward compatibility for existing WebSocketEventRouter usage
    while routing all functionality through the consolidated CanonicalMessageRouter.

    Migration Status: Phase 1 - Compatibility adapter in place
    Business Impact: Maintains $500K+ ARR event routing functionality
    """

    def __init__(self, websocket_manager: Optional['WebSocketManager']):
        """Initialize WebSocketEventRouter compatibility adapter."""
        super().__init__(websocket_manager=websocket_manager)
        logger.info("WebSocketEventRouter compatibility adapter initialized - functionality consolidated")

    # All event routing methods are now inherited from CanonicalMessageRouter
    # Legacy methods maintained for backward compatibility


# === PHASE 1 SSOT CONSOLIDATION COMPLETE ===
# Legacy implementation removed - all functionality now delegated to CanonicalMessageRouter
# Phase 1: Legacy code removed while maintaining adapter interface  
# Phase 2: Import updates to use CanonicalMessageRouter directly
# Phase 3: Remove adapter classes after all imports updated

class LegacyWebSocketEventRouter:
    """REMOVED: Legacy implementation consolidated into CanonicalMessageRouter.
    
    This class has been removed as part of Phase 1 SSOT consolidation.
    All functionality is now available through CanonicalMessageRouter.
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManager]):
        """Legacy class removed - use CanonicalMessageRouter instead."""
        raise NotImplementedError(
            "LegacyWebSocketEventRouter removed in Phase 1 SSOT consolidation. "
            "Use CanonicalMessageRouter or WebSocketEventRouter adapter instead."
        )
    
    # All methods removed - use CanonicalMessageRouter or WebSocketEventRouter adapter instead


# Module-level router instance factory
_router_instance: Optional[WebSocketEventRouter] = None


def get_websocket_router(websocket_manager=None) -> WebSocketEventRouter:
    """Get the WebSocket event router instance.
    
    Args:
        websocket_manager: Optional WebSocket manager instance for dependency injection
        
    Returns:
        WebSocketEventRouter: Router instance
    """
    global _router_instance
    
    if _router_instance is None:
        if websocket_manager is None:
            # SECURITY FIX: This should only be called with proper context
            # Log warning when fallback is used
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("WebSocketEventRouter: No WebSocket manager provided, using factory pattern")
            
            # Create router without manager - it will need to be initialized later
            _router_instance = WebSocketEventRouter(None)
        else:
            _router_instance = WebSocketEventRouter(websocket_manager)
    
    return _router_instance


def reset_websocket_router() -> None:
    """Reset the router instance (for testing)."""
    global _router_instance
    _router_instance = None


# ISSUE #982 SSOT CONSOLIDATION: Module-level adapter functions for backward compatibility
async def broadcast_to_user(user_id: str, event: Dict[str, Any]) -> int:
    """ISSUE #982 ADAPTER: Module-level broadcast function that delegates to SSOT service.

    This is a compatibility adapter that maintains the existing module-level interface
    while delegating to the SSOT WebSocketBroadcastService implementation.

    Args:
        user_id: User to broadcast to
        event: Event payload

    Returns:
        int: Number of successful sends (legacy compatibility)
    """
    # ISSUE #982 SSOT CONSOLIDATION: Direct delegation to WebSocketBroadcastService
    try:
        # Import here to avoid circular dependency
        from netra_backend.app.services.websocket_broadcast_service import create_broadcast_service
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager

        # Get WebSocket manager instance via SSOT factory
        # NOTE: Module-level function lacks user context - consider upgrading callers
        websocket_manager = get_websocket_manager(user_context=None)

        # Create SSOT broadcast service
        broadcast_service = create_broadcast_service(websocket_manager)

        # Delegate to SSOT implementation
        result = await broadcast_service.broadcast_to_user(user_id, event)

        # Log adapter usage for migration tracking
        logger.debug(
            f"MODULE ADAPTER: websocket_event_router.broadcast_to_user delegated to SSOT service. "
            f"User: {user_id[:8]}..., Event: {event.get('type', 'unknown')}, "
            f"Result: {result.successful_sends}/{result.connections_attempted}"
        )

        # Return legacy-compatible integer result
        return result.successful_sends

    except Exception as e:
        # Adapter failure handling
        logger.error(
            f"MODULE ADAPTER FAILURE: SSOT delegation failed for user {user_id[:8]}..., "
            f"event {event.get('type', 'unknown')}: {e}"
        )

        # Return 0 to indicate failure in legacy-compatible way
        return 0