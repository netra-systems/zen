"""
WebSocket Manager Factory: SSOT Factory Interface for WebSocket Management

This module provides a centralized factory interface for creating WebSocket managers
and related components, consolidating imports from various websocket_core modules.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Maintain SSOT compliance while providing backward compatibility
- Value Impact: Ensures consistent WebSocket manager creation across all components
- Revenue Impact: Prevents WebSocket-related failures that could affect $500K+ ARR chat functionality

Key Components:
- WebSocketManagerFactory: Factory class for creating WebSocket managers
- create_websocket_manager: Function for creating WebSocket manager instances
- IsolatedWebSocketManager: User isolation-aware WebSocket manager
- Factory functions for user context creation

SSOT Design:
This module serves as a compatibility layer, re-exporting components from their
canonical locations while maintaining existing import paths used by tests and
mission-critical modules.
"""

# Re-export core WebSocket manager components from their canonical locations
from netra_backend.app.websocket_core.websocket_manager import (
    WebSocketManagerFactory,
    UnifiedWebSocketManager as IsolatedWebSocketManager  # Alias for compatibility
)

# Re-export factory functions from canonical imports
from netra_backend.app.websocket_core.canonical_imports import (
    create_websocket_manager,
    create_websocket_manager_sync
)

# Re-export utilities
from netra_backend.app.websocket_core.utils import (
    create_websocket_manager as create_websocket_manager_async
)

# Import user context creation functions (consolidated for factory usage)
try:
    from netra_backend.app.services.user_execution_context import (
        create_user_execution_context,
        create_defensive_user_execution_context
    )
except ImportError:
    # Fallback for tests or modules that might not have this available
    def create_user_execution_context(*args, **kwargs):
        raise NotImplementedError("User execution context creation not available")

    def create_defensive_user_execution_context(*args, **kwargs):
        raise NotImplementedError("Defensive user execution context creation not available")

# SSOT logging
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)

# Factory instance for singleton pattern compatibility
_factory_instance = None

def get_websocket_manager_factory():
    """
    Get or create the singleton WebSocket manager factory instance.

    Returns:
        WebSocketManagerFactory: Singleton factory instance
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = WebSocketManagerFactory()
        logger.info("Created WebSocket manager factory singleton instance")
    return _factory_instance

def create_websocket_manager_with_context(user_context=None, **kwargs):
    """
    Create a WebSocket manager with proper user context isolation.

    This is the recommended factory function for creating WebSocket managers
    with full user context isolation and SSOT compliance.

    Args:
        user_context: User execution context for isolation
        **kwargs: Additional arguments for manager creation

    Returns:
        WebSocket manager instance with proper isolation
    """
    try:
        # Use the canonical factory function
        return create_websocket_manager(user_context=user_context, **kwargs)
    except Exception as e:
        logger.error(f"Failed to create WebSocket manager with context: {e}")
        raise

def create_isolated_websocket_manager(user_id: str, thread_id: str, run_id: str = None, **kwargs):
    """
    Create an isolated WebSocket manager for specific user context.

    This function creates a fully isolated WebSocket manager instance
    with proper user context boundaries.

    Args:
        user_id: Unique user identifier
        thread_id: Thread identifier for conversation
        run_id: Optional run identifier
        **kwargs: Additional arguments for manager creation

    Returns:
        IsolatedWebSocketManager: Manager with user isolation
    """
    try:
        # Create user context first
        user_context = create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )

        # Create manager with context
        return create_websocket_manager_with_context(user_context=user_context, **kwargs)

    except Exception as e:
        logger.error(f"Failed to create isolated WebSocket manager: {e}")
        raise

# Legacy compatibility functions
def get_websocket_manager(*args, **kwargs):
    """Legacy compatibility function."""
    logger.warning("Using deprecated get_websocket_manager - use create_websocket_manager instead")
    return create_websocket_manager(*args, **kwargs)

# Export all public interfaces
__all__ = [
    # Core classes
    'WebSocketManagerFactory',
    'IsolatedWebSocketManager',

    # Factory functions
    'create_websocket_manager',
    'create_websocket_manager_sync',
    'create_websocket_manager_async',
    'create_websocket_manager_with_context',
    'create_isolated_websocket_manager',

    # Singleton access
    'get_websocket_manager_factory',

    # User context functions
    'create_user_execution_context',
    'create_defensive_user_execution_context',

    # Legacy compatibility
    'get_websocket_manager'
]

logger.info("WebSocket manager factory module loaded - SSOT consolidation active")