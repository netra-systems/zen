"""SSOT WebSocket Manager Factory - Issue #1226 Resolution

This module provides the canonical factory pattern for WebSocket manager creation,
ensuring proper user isolation and SSOT compliance.

CRITICAL: This factory enables the Golden Path user flow by providing:
- User-isolated WebSocket manager instances
- Proper factory pattern for multi-user environments
- SSOT compliance for WebSocket management
- Support for all 5 critical WebSocket events

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Enable $500K+ ARR Golden Path WebSocket functionality
- Value Impact: Foundation for reliable AI chat interactions
- Revenue Impact: Critical infrastructure supporting all user chat sessions

ISSUE #1226 REMEDIATION: Creates missing factory module to resolve import failures
in supervisor_factory.py and unified_init.py that were blocking WebSocket functionality.
"""

from typing import Optional, Any
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManagerMode
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketManagerFactory:
    """Factory for creating isolated WebSocket manager instances.

    This factory ensures proper user isolation and SSOT compliance for WebSocket
    operations in multi-user environments. Each manager instance is scoped to
    a specific user context to prevent data contamination.
    """

    def __init__(self):
        """Initialize the WebSocket manager factory."""
        pass

    async def create_isolated_manager(self, user_id: str, connection_id: str):
        """Create an isolated WebSocket manager for a specific user.

        Args:
            user_id: The user identifier for isolation
            connection_id: The WebSocket connection identifier

        Returns:
            WebSocket manager instance isolated to the specified user
        """
        user_context = UserExecutionContext(
            user_id=user_id,
            websocket_client_id=connection_id
        )
        return await get_websocket_manager(user_context)

    def create_manager(self, user_context: Optional[UserExecutionContext] = None):
        """Create a WebSocket manager with the given user context.

        Args:
            user_context: Optional user execution context for isolation

        Returns:
            WebSocket manager instance
        """
        return get_websocket_manager(user_context)


def create_websocket_manager(user_context: Optional[UserExecutionContext] = None):
    """Create a WebSocket manager with the given user context.

    This function provides a direct interface to WebSocket manager creation
    while maintaining SSOT compliance and user isolation.

    Args:
        user_context: Optional user execution context for isolation

    Returns:
        WebSocket manager instance
    """
    return get_websocket_manager(user_context)


# Compatibility aliases for existing imports
IsolatedWebSocketManager = get_websocket_manager


# Factory instance for global access
_global_factory_instance = None


def get_factory() -> WebSocketManagerFactory:
    """Get the global WebSocket manager factory instance.

    Returns:
        Global factory instance
    """
    global _global_factory_instance
    if _global_factory_instance is None:
        _global_factory_instance = WebSocketManagerFactory()
    return _global_factory_instance


__all__ = [
    'WebSocketManagerFactory',
    'create_websocket_manager',
    'IsolatedWebSocketManager',
    'get_factory'
]