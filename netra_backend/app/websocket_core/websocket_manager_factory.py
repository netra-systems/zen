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

# Export all compatibility functions
__all__ = [
    'create_websocket_manager',
    'get_websocket_manager_factory', 
    'WebSocketManagerFactory',
    'IsolatedWebSocketManager'
]

logger.info("WebSocket Manager Factory compatibility module loaded - Golden Path ready")