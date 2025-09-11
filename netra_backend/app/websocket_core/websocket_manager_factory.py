"""WebSocket Manager Factory - SSOT Compatibility Module

CRITICAL GOLDEN PATH COMPATIBILITY: This module provides factory functions for creating
WebSocketManager instances to support Golden Path integration tests that depend on
the factory pattern.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure 
- Business Goal: Enable Golden Path integration testing (protects $500K+ ARR)
- Value Impact: Maintains test compatibility during SSOT refactoring
- Revenue Impact: Ensures chat functionality testing works reliably

COMPLIANCE NOTES:
- This is a COMPATIBILITY MODULE only - new code should import WebSocketManager directly
- Maintains factory pattern compatibility for existing Golden Path tests
- Follows SSOT principles by wrapping the unified WebSocketManager implementation
- Provides proper user isolation and context management

IMPORT GUIDANCE:
- DEPRECATED: from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
- RECOMMENDED: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
"""

from typing import Optional
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.types.core_types import UserID, ensure_user_id

logger = central_logger.get_logger(__name__)


def create_websocket_manager(user_context=None, user_id: Optional[UserID] = None):
    """
    Factory function to create WebSocketManager instances with proper SSOT compliance.
    
    GOLDEN PATH COMPATIBILITY: This function maintains compatibility with Golden Path
    integration tests while following SSOT patterns under the hood.
    
    Args:
        user_context: Optional UserExecutionContext for user isolation (preferred)
        user_id: Optional UserID for basic isolation (fallback for tests)
    
    Returns:
        WebSocketManager: Configured WebSocket manager instance
        
    Raises:
        ValueError: If neither user_context nor user_id is provided
    """
    logger.info("Creating WebSocket manager via factory (Golden Path compatibility)")
    
    # If user_context is provided, use it directly (preferred path)
    if user_context is not None:
        logger.debug("Creating WebSocket manager with full user context")
        return WebSocketManager(user_context=user_context)
    
    # Fallback for tests that only provide user_id
    if user_id is not None:
        logger.debug(f"Creating WebSocket manager for user_id: {user_id}")
        # For testing compatibility, create a minimal context
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Ensure proper UserID type
        typed_user_id = ensure_user_id(user_id)
        
        # Create minimal execution context for testing
        test_context = UserExecutionContext(
            user_id=typed_user_id,
            request_id=f"golden_path_test_{typed_user_id}",
            environment="test"
        )
        
        return WebSocketManager(user_context=test_context)
    
    # No context provided - this violates SSOT compliance
    logger.error("WebSocket manager factory called without user context or user_id")
    raise ValueError(
        "WebSocket manager creation requires either user_context (UserExecutionContext) "
        "or user_id for proper user isolation. Import-time initialization is prohibited. "
        "See Golden Path integration test patterns for correct usage."
    )


# Legacy compatibility aliases for existing tests
def get_websocket_manager_factory():
    """
    COMPATIBILITY FUNCTION: Returns factory function for legacy test compatibility.
    
    Returns:
        callable: The create_websocket_manager factory function
    """
    logger.warning("get_websocket_manager_factory is deprecated. Use create_websocket_manager directly.")
    return create_websocket_manager


class WebSocketManagerFactory:
    """
    COMPATIBILITY CLASS: Legacy factory class for backward compatibility.
    
    This class provides the same interface as the previous factory implementation
    but uses the SSOT WebSocketManager under the hood.
    """
    
    @staticmethod
    def create(user_context=None, user_id: Optional[UserID] = None):
        """Create WebSocket manager using static factory method."""
        return create_websocket_manager(user_context=user_context, user_id=user_id)
    
    @classmethod
    def create_for_user(cls, user_id: UserID):
        """Create WebSocket manager for specific user ID."""
        return create_websocket_manager(user_id=user_id)
    
    @classmethod  
    def create_isolated(cls, user_context):
        """Create isolated WebSocket manager with user context."""
        return create_websocket_manager(user_context=user_context)


# For compatibility with any tests that expect the manager class directly
IsolatedWebSocketManager = WebSocketManager


# ===== ADDITIONAL COMPATIBILITY CLASSES AND FUNCTIONS =====

class FactoryInitializationError(Exception):
    """Exception raised when WebSocket factory initialization fails."""
    pass


class ConnectionLifecycleManager:
    """
    COMPATIBILITY CLASS: Legacy connection lifecycle manager.
    
    This class provides compatibility for tests that expect connection lifecycle
    management functionality. In the SSOT implementation, lifecycle management
    is handled directly by the WebSocketManager.
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self._active_connections = {}
        logger.debug("ConnectionLifecycleManager initialized (compatibility mode)")
    
    async def register_connection(self, connection_id: str, user_id: UserID):
        """Register a new WebSocket connection."""
        self._active_connections[connection_id] = {
            "user_id": user_id,
            "registered_at": __import__("time").time()
        }
        logger.debug(f"Connection registered: {connection_id} for user {user_id}")
        return True
    
    async def unregister_connection(self, connection_id: str):
        """Unregister a WebSocket connection."""
        self._active_connections.pop(connection_id, None)
        logger.debug(f"Connection unregistered: {connection_id}")
        return True
    
    def get_active_connections(self):
        """Get all active connections."""
        return self._active_connections.copy()
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections."""
        import time
        current_time = time.time()
        stale_threshold = 3600  # 1 hour
        
        stale_connections = [
            conn_id for conn_id, info in self._active_connections.items()
            if current_time - info["registered_at"] > stale_threshold
        ]
        
        for conn_id in stale_connections:
            await self.unregister_connection(conn_id)
        
        return len(stale_connections)


def create_defensive_user_execution_context(user_id: UserID, **kwargs):
    """
    COMPATIBILITY FUNCTION: Create defensive user execution context.
    
    This function provides backward compatibility for tests that expect
    defensive context creation patterns. The SSOT implementation handles
    user context creation through the standard UserExecutionContext.
    
    Args:
        user_id: User ID for context creation
        **kwargs: Additional context parameters
    
    Returns:
        UserExecutionContext: Configured user execution context
    """
    logger.info(f"Creating defensive user execution context for user: {user_id}")
    
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Ensure proper UserID type
        typed_user_id = ensure_user_id(user_id)
        
        # Create defensive context with validation
        context = UserExecutionContext(
            user_id=typed_user_id,
            request_id=kwargs.get("request_id", f"defensive_context_{typed_user_id}"),
            environment=kwargs.get("environment", "test"),
            thread_id=kwargs.get("thread_id"),
            session_id=kwargs.get("session_id"),
            features=kwargs.get("features", {}),
            configuration_overrides=kwargs.get("configuration_overrides", {})
        )
        
        # Add defensive validation
        if not context.user_id:
            raise FactoryInitializationError("User ID required for defensive context")
        
        logger.debug(f"Defensive user execution context created: {context.request_id}")
        return context
        
    except Exception as e:
        logger.error(f"Failed to create defensive user execution context: {e}")
        raise FactoryInitializationError(f"Context creation failed: {e}")


# ===== ENHANCED WEBSOCKET MANAGER FACTORY CLASS =====

class WebSocketManagerFactory:
    """
    ENHANCED COMPATIBILITY CLASS: Extended factory class for backward compatibility.
    
    This class provides the same interface as the previous factory implementation
    but uses the SSOT WebSocketManager under the hood. Enhanced with additional
    compatibility methods expected by legacy tests.
    """
    
    @staticmethod
    def create(user_context=None, user_id: Optional[UserID] = None):
        """Create WebSocket manager using static factory method."""
        return create_websocket_manager(user_context=user_context, user_id=user_id)
    
    @classmethod
    def create_for_user(cls, user_id: UserID):
        """Create WebSocket manager for specific user ID."""
        return create_websocket_manager(user_id=user_id)
    
    @classmethod  
    def create_isolated(cls, user_context):
        """Create isolated WebSocket manager with user context."""
        return create_websocket_manager(user_context=user_context)
    
    @classmethod
    def create_defensive(cls, user_id: UserID, **kwargs):
        """Create WebSocket manager with defensive user context."""
        defensive_context = create_defensive_user_execution_context(user_id, **kwargs)
        return create_websocket_manager(user_context=defensive_context)
    
    @classmethod
    def create_with_lifecycle_manager(cls, user_id: UserID):
        """Create WebSocket manager with connection lifecycle manager."""
        manager = create_websocket_manager(user_id=user_id)
        lifecycle_manager = ConnectionLifecycleManager(manager)
        
        # Attach lifecycle manager to the WebSocket manager for compatibility
        manager._lifecycle_manager = lifecycle_manager
        return manager
    
    @classmethod
    def create_validated(cls, user_context):
        """Create WebSocket manager with validation."""
        if not user_context:
            raise FactoryInitializationError("User context required for validated creation")
        
        if not hasattr(user_context, 'user_id') or not user_context.user_id:
            raise FactoryInitializationError("Valid user_id required in context")
        
        return create_websocket_manager(user_context=user_context)


# Export all compatibility functions and classes
__all__ = [
    'create_websocket_manager',
    'get_websocket_manager_factory', 
    'WebSocketManagerFactory',
    'IsolatedWebSocketManager',
    'create_defensive_user_execution_context',
    'ConnectionLifecycleManager',
    'FactoryInitializationError'
]

logger.info("WebSocket Manager Factory compatibility module loaded - Golden Path ready with enhanced compatibility")