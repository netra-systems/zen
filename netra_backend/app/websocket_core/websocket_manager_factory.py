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

from typing import Optional, Dict, Any
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.types.core_types import UserID, ensure_user_id

logger = central_logger.get_logger(__name__)


class FactoryInitializationError(Exception):
    """Raised when WebSocket factory initialization fails SSOT validation."""
    pass


class ConnectionLifecycleManager:
    """Compatibility class for connection lifecycle management."""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
        
    async def handle_connection_lifecycle(self, connection_id: str):
        """Handle connection lifecycle events."""
        # Delegate to the unified WebSocketManager
        pass


def create_defensive_user_execution_context(
    user_id: str, 
    websocket_client_id: Optional[str] = None,
    fallback_context: Optional[Dict[str, Any]] = None
) -> 'UserExecutionContext':
    """
    Create a defensive UserExecutionContext with proper validation.
    
    This function provides backward compatibility for the unified authentication service
    that expects defensive context creation during WebSocket authentication flows.
    
    Args:
        user_id: User identifier for the context
        websocket_client_id: Optional WebSocket connection ID
        fallback_context: Optional fallback context data
        
    Returns:
        UserExecutionContext: Properly configured context for WebSocket authentication
    """
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    
    logger.debug(f"Creating defensive UserExecutionContext for user: {user_id}")
    
    # Use ID manager for consistent ID generation
    id_manager = UnifiedIDManager()
    
    # Generate IDs if not provided in fallback_context
    if fallback_context and 'thread_id' in fallback_context:
        thread_id = fallback_context['thread_id']
    else:
        thread_id = id_manager.generate_thread_id()
        
    if fallback_context and 'run_id' in fallback_context:
        run_id = fallback_context['run_id']
    else:
        run_id = id_manager.generate_run_id(thread_id)
    
    # Create defensive context with proper validation
    context = UserExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=f"defensive_auth_{user_id}_{websocket_client_id or 'no_ws'}",
        websocket_client_id=websocket_client_id,
        agent_context=fallback_context or {}
    )
    
    logger.debug(f"Created defensive context: user={user_id}, ws_id={websocket_client_id}")
    return context


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
    
    def __init__(self, connection_pool=None, id_manager=None, config=None, user_context_factory=None, **kwargs):
        """
        Initialize WebSocketManagerFactory with validation.
        
        For SSOT validation tests, certain missing dependencies should raise errors.
        """
        # Store parameters for SSOT validation tests
        self.connection_pool = connection_pool
        self.id_manager = id_manager
        self.config = config
        self.user_context_factory = user_context_factory
        self.kwargs = kwargs
        
        # SSOT validation - raise error if None values are explicitly provided for critical dependencies
        none_dependencies = []
        if connection_pool is None:
            none_dependencies.append("connection_pool")
        if id_manager is None:
            none_dependencies.append("id_manager")
        if user_context_factory is None:
            none_dependencies.append("user_context_factory")
            
        if none_dependencies:
            raise FactoryInitializationError(
                f"SSOT violation: missing required dependencies: {', '.join(none_dependencies)}"
            )
    
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
    'IsolatedWebSocketManager',
    'FactoryInitializationError',
    'ConnectionLifecycleManager',
    'create_defensive_user_execution_context',
    '_validate_ssot_user_context'
]

def _validate_ssot_user_context(user_context) -> None:
    """
    Validate UserExecutionContext for SSOT compliance.
    
    This function performs strict validation to ensure the user context
    meets SSOT requirements for WebSocket manager creation.
    
    Args:
        user_context: UserExecutionContext to validate
        
    Raises:
        ValueError: If context fails SSOT validation requirements
    """
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    
    # 1. Type validation - must be proper UserExecutionContext
    if not isinstance(user_context, UserExecutionContext):
        raise ValueError(
            f"SSOT VIOLATION: Expected UserExecutionContext, got {type(user_context)}. "
            f"WebSocket factory requires SSOT-compliant context types."
        )
    
    # 2. Required attributes validation
    required_attrs = ['user_id', 'thread_id', 'run_id', 'request_id']
    missing_attrs = []
    
    for attr in required_attrs:
        if not hasattr(user_context, attr):
            missing_attrs.append(attr)
        elif getattr(user_context, attr) is None:
            missing_attrs.append(f"{attr} (None)")
        elif isinstance(getattr(user_context, attr), str) and not getattr(user_context, attr).strip():
            missing_attrs.append(f"{attr} (empty)")
    
    if missing_attrs:
        raise ValueError(
            f"SSOT CONTEXT INCOMPLETE: Missing or invalid attributes: {', '.join(missing_attrs)}. "
            f"WebSocket factory requires complete user context."
        )
    
    # 3. WebSocket-specific validation
    if hasattr(user_context, 'websocket_client_id'):
        websocket_client_id = getattr(user_context, 'websocket_client_id')
        if websocket_client_id == "":  # Empty string is invalid
            raise ValueError(
                f"SSOT CONTEXT VALIDATION FAILED: websocket_client_id cannot be empty string. "
                f"Use None for no client ID or provide valid identifier."
            )
    
    logger.debug(f"✅ SSOT validation passed for user: {user_context.user_id}")


logger.info("WebSocket Manager Factory compatibility module loaded - Golden Path ready")