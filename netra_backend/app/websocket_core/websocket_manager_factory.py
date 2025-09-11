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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.types.core_types import UserID, ensure_user_id

logger = central_logger.get_logger(__name__)

# Factory instance management (singleton pattern for compatibility)
import threading
_factory_instance: Optional['WebSocketManagerFactory'] = None
_factory_lock = threading.Lock()


@dataclass
class ManagerMetrics:
    """Manager metrics data class for test compatibility."""
    managers_created: int = 0
    managers_active: int = 0
    managers_cleaned: int = 0
    connections_total: int = 0
    connections_active: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'managers_created': self.managers_created,
            'managers_active': self.managers_active,
            'managers_cleaned': self.managers_cleaned,
            'connections_total': self.connections_total,
            'connections_active': self.connections_active,
            'created_at': self.created_at
        }


@dataclass
class FactoryMetrics:
    """Factory metrics data class for test compatibility."""
    emitters_created: int = 0
    emitters_active: int = 0
    emitters_cleaned: int = 0
    events_sent_total: int = 0
    events_failed_total: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ssot_redirect: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FactoryMetrics':
        """Create metrics from dictionary."""
        return cls(
            emitters_created=data.get('emitters_created', 0),
            emitters_active=data.get('emitters_active', 0),
            emitters_cleaned=data.get('emitters_cleaned', 0),
            events_sent_total=data.get('events_sent_total', 0),
            events_failed_total=data.get('events_failed_total', 0),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            ssot_redirect=data.get('ssot_redirect', True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'emitters_created': self.emitters_created,
            'emitters_active': self.emitters_active,
            'emitters_cleaned': self.emitters_cleaned,
            'events_sent_total': self.events_sent_total,
            'events_failed_total': self.events_failed_total,
            'created_at': self.created_at,
            'ssot_redirect': self.ssot_redirect
        }


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


def create_websocket_manager_sync(user_context=None, user_id: Optional[UserID] = None):
    """
    SYNC COMPATIBILITY FUNCTION: Synchronous version of create_websocket_manager.
    
    This function provides the same functionality as create_websocket_manager but
    in a synchronous context for tests that don't use async patterns.
    
    Args:
        user_context: Optional UserExecutionContext for user isolation (preferred)
        user_id: Optional UserID for basic isolation (fallback for tests)
    
    Returns:
        WebSocketManager: Configured WebSocket manager instance
    """
    logger.info("Creating WebSocket manager via sync factory (test compatibility)")
    return create_websocket_manager(user_context=user_context, user_id=user_id)


def _validate_ssot_user_context(user_context) -> bool:
    """
    PRIVATE COMPATIBILITY FUNCTION: Validate SSOT user context for tests.
    
    This function provides validation of user execution context to ensure
    SSOT compliance patterns are followed in factory operations.
    
    Args:
        user_context: UserExecutionContext to validate
        
    Returns:
        bool: True if context is valid and SSOT compliant
    """
    if user_context is None:
        logger.debug("User context is None - not SSOT compliant")
        return False
    
    # Check for required attributes
    required_attrs = ['user_id', 'request_id']
    for attr in required_attrs:
        if not hasattr(user_context, attr):
            logger.debug(f"User context missing required attribute: {attr}")
            return False
        if getattr(user_context, attr) is None:
            logger.debug(f"User context attribute {attr} is None")
            return False
    
    # Validate user_id type
    if not isinstance(user_context.user_id, (str, UserID)):
        logger.debug(f"User context user_id has invalid type: {type(user_context.user_id)}")
        return False
    
    # Check for proper isolation
    if hasattr(user_context, '_shared_state') and user_context._shared_state:
        logger.warning("User context has shared state - potential SSOT violation")
        return False
    
    logger.debug("User context validation passed - SSOT compliant")
    return True


def _validate_ssot_user_context_staging_safe(user_context) -> bool:
    """
    STAGING-SAFE COMPATIBILITY FUNCTION: Validate SSOT user context with staging environment safety.
    
    This function provides validation of user execution context specifically for staging
    environments where additional safety checks may be required.
    
    Args:
        user_context: UserExecutionContext to validate
        
    Returns:
        bool: True if context is valid and staging-safe
    """
    # First perform standard SSOT validation
    if not _validate_ssot_user_context(user_context):
        return False
    
    # Additional staging safety checks
    if hasattr(user_context, 'environment') and user_context.environment == 'production':
        logger.error("Production context in staging validation - potential configuration error")
        return False
    
    # Validate test-specific attributes for staging safety
    if hasattr(user_context, 'is_test_context') and not user_context.is_test_context:
        logger.warning("Non-test context in staging validation - may not be safe")
    
    # Check for staging-specific isolation requirements
    if hasattr(user_context, 'features') and user_context.features:
        staging_unsafe_features = ['production_database', 'real_payment_processing', 'external_apis']
        for feature in staging_unsafe_features:
            if user_context.features.get(feature, False):
                logger.error(f"Staging-unsafe feature '{feature}' enabled in context")
                return False
    
    logger.debug("User context validation passed - staging-safe and SSOT compliant")
    return True


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
    'create_websocket_manager_sync',
    'get_websocket_manager_factory', 
    'WebSocketManagerFactory',
    'IsolatedWebSocketManager',
    'create_defensive_user_execution_context',
    'ConnectionLifecycleManager',
    'FactoryInitializationError',
    'FactoryMetrics',
    'ManagerMetrics',
    '_factory_instance',
    '_factory_lock',
    '_validate_ssot_user_context',
    '_validate_ssot_user_context_staging_safe'
]

logger.info("WebSocket Manager Factory compatibility module loaded - Golden Path ready with enhanced compatibility")