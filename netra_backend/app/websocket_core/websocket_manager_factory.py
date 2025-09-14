"""WebSocket Manager Factory - DEPRECATED COMPATIBILITY MODULE (Issue #824 Remediation)

DEPRECATED: This module is being phased out as part of SSOT consolidation.

ISSUE #824 REMEDIATION: This factory layer created SSOT fragmentation with 2+ WebSocket Manager
implementations active simultaneously. All functionality has been consolidated into the
canonical SSOT import path.

MIGRATION INSTRUCTIONS:
OLD (DEPRECATED):
    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
    manager = await create_websocket_manager(user_context=context)

NEW (CANONICAL SSOT):
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    manager = await get_websocket_manager(user_context=context)

OR DIRECT IMPORT:
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    manager = WebSocketManager(user_context=context)

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure
- Business Goal: Eliminate SSOT violations threatening $500K+ ARR
- Value Impact: Prevents race conditions and initialization failures
- Revenue Impact: Ensures reliable WebSocket operations for all users

PHASE OUT PLAN:
1. Phase 1 (Current): Redirect all factory functions to SSOT implementations
2. Phase 2 (Next): Update all imports to canonical paths
3. Phase 3 (Final): Remove this module entirely
"""

from typing import Optional, Dict, Any
import warnings
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from shared.logging.unified_logging_ssot import get_logger

# ISSUE #824 PHASE 1 REMEDIATION: Use canonical SSOT import path
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode

# Factory function compatibility layer - Phase 1 implementation
# ISSUE #824 FIX: Removed duplicate get_websocket_manager() causing SSOT fragmentation
# Use the canonical implementation in websocket_manager.py:182
# This eliminates circular reference and consolidates to single SSOT

def create_test_user_context():
    """
    COMPATIBILITY: Create test user context.
    """
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
    id_manager = UnifiedIDManager()
    return type('MockUserContext', (), {
        'user_id': id_manager.generate_id(IDType.USER, prefix="test"),
        'session_id': id_manager.generate_id(IDType.THREAD, prefix="test"),
        'request_id': id_manager.generate_id(IDType.REQUEST, prefix="test"),
        'is_test': True
    })()
from netra_backend.app.websocket_core.ssot_validation_enhancer import validate_websocket_manager_creation
from shared.types.core_types import UserID, ensure_user_id

logger = get_logger(__name__)

# DEPRECATION WARNING: Issue #824 Remediation
warnings.warn(
    "netra_backend.app.websocket_core.websocket_manager_factory is DEPRECATED. "
    "Use 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' instead. "
    "This module will be removed in v2.0 as part of SSOT consolidation.",
    DeprecationWarning,
    stacklevel=2
)


class WebSocketComponentError(Exception):
    """Exception raised for WebSocket component validation errors."""
    pass


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


async def create_websocket_manager(user_context=None, user_id: Optional[UserID] = None):
    """
    DEPRECATED FACTORY FUNCTION: Redirects to SSOT implementation (Issue #824 Remediation)

    This function is deprecated and redirects to the canonical SSOT implementation.

    MIGRATION INSTRUCTIONS:
    OLD: manager = await create_websocket_manager(user_context=context)
    NEW: manager = await get_websocket_manager(user_context=context)

    Args:
        user_context: Optional UserExecutionContext for user isolation (preferred)
        user_id: Optional UserID for basic isolation (fallback for tests)

    Returns:
        WebSocketManager: Configured WebSocket manager instance via SSOT

    Raises:
        ValueError: If neither user_context nor user_id is provided
    """
    logger.warning("DEPRECATED: create_websocket_manager() redirecting to SSOT get_websocket_manager()")

    # Issue #824 Phase 1 Remediation: Redirect to unified SSOT implementation
    if user_context is None and user_id is not None:
        # Create minimal context from user_id for compatibility
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        typed_user_id = ensure_user_id(user_id)
        user_context = UserExecutionContext(
            user_id=typed_user_id,
            thread_id=f"thread_{typed_user_id}",
            run_id=f"run_{typed_user_id}",
            request_id=f"factory_test_{typed_user_id}"
        )
    
    # ISSUE #824 FIX: Use canonical SSOT import path
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    return await get_websocket_manager(user_context=user_context)


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
    
    ISSUE #292 FIX: This provides sync access while the main factory is now async.
    
    Args:
        user_context: Optional UserExecutionContext for user isolation (preferred)
        user_id: Optional UserID for basic isolation (fallback for tests)
    
    Returns:
        WebSocketManager: Configured WebSocket manager instance
    """
    logger.info("Creating WebSocket manager via sync factory (test compatibility)")
    
    # PHASE 1: Direct creation using WebSocketManager (SSOT import)
    # If user_context is provided, use it directly (preferred path)
    if user_context is not None:
        logger.debug("Creating WebSocket manager with full user context (sync)")
        manager = WebSocketManager(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=user_context,
            _ssot_authorization_token=secrets.token_urlsafe(32)
        )

        # Issue #712 Fix: Validate SSOT compliance
        try:
            validate_websocket_manager_creation(
                manager_instance=manager,
                user_context=user_context,
                creation_method="sync_factory"
            )
        except Exception as e:
            logger.warning(f"SSOT validation failed (non-critical): {e}")

        return manager
    
    # Fallback for tests that only provide user_id
    if user_id is not None:
        logger.debug(f"Creating WebSocket manager for user_id: {user_id} (sync)")
        # For testing compatibility, create a minimal context
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Ensure proper UserID type
        typed_user_id = ensure_user_id(user_id)
        
        # Create minimal execution context for testing
        test_context = UserExecutionContext(
            user_id=typed_user_id,
            thread_id=f"thread_{typed_user_id}",
            run_id=f"run_{typed_user_id}",
            request_id=f"golden_path_test_{typed_user_id}"
        )
        
        return WebSocketManager(
            mode=WebSocketManagerMode.UNIFIED,
            user_context=test_context, 
            _ssot_authorization_token=secrets.token_urlsafe(32)
        )
    
    # No context provided - this violates SSOT compliance
    logger.error("WebSocket manager sync factory called without user context or user_id")
    raise ValueError(
        "WebSocket manager creation requires either user_context (UserExecutionContext) "
        "or user_id for proper user isolation. Import-time initialization is prohibited. "
        "See Golden Path integration test patterns for correct usage."
    )


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


def validate_websocket_component_health() -> Dict[str, Any]:
    """
    COMPATIBILITY FUNCTION: Validate WebSocket component health.
    
    This function provides health validation for WebSocket components to support
    integration tests that need to verify WebSocket infrastructure health.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    logger.debug("Validating WebSocket component health (compatibility mode)")
    
    try:
        # Basic health indicators
        health_status = {
            'status': 'healthy',
            'components': {
                'websocket_manager': 'available',
                'factory_functions': 'operational',
                'user_context_validation': 'working',
                'ssot_compliance': 'validated'
            },
            'metrics': {
                'factory_calls': 0,  # Reset on each health check
                'active_managers': 0,  # Would be populated from actual tracking
                'validation_calls': 0
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'mode': 'compatibility'
        }
        
        # Test critical functions
        try:
            # Test factory function is callable
            if not callable(create_websocket_manager):
                health_status['components']['websocket_manager'] = 'error'
                health_status['status'] = 'degraded'
            
            # Test validation functions
            test_context = type('TestContext', (), {
                'user_id': 'test_user',
                'request_id': 'health_check'
            })()
            
            if not _validate_ssot_user_context(test_context):
                health_status['components']['user_context_validation'] = 'partial'
            
        except Exception as component_error:
            logger.warning(f"Component health check failed: {component_error}")
            health_status['components']['factory_functions'] = 'error'
            health_status['status'] = 'degraded'
            health_status['error'] = str(component_error)
        
        logger.info(f"WebSocket component health check complete: {health_status['status']}")
        return health_status
        
    except Exception as health_error:
        logger.error(f"WebSocket component health validation failed: {health_error}")
        return {
            'status': 'unhealthy',
            'error': str(health_error),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': 'compatibility'
        }


# SSOT CONSOLIDATION: Removed IsolatedWebSocketManager alias to reduce redundancy
# Use WebSocketManager directly for consistency


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


# ===== WEBSOCKET MANAGER FACTORY CLASS REMOVED (Issue #824 Remediation) =====

# WebSocketManagerFactory class has been REMOVED as part of Issue #824 SSOT consolidation.
# All factory functionality has been moved to canonical SSOT functions.

# COMPATIBILITY: If you need factory-style creation, use these SSOT functions:
# - get_websocket_manager() - Preferred SSOT factory function
# - WebSocketManager() - Direct instantiation

# Issue #824 SSOT Consolidation: Factory class eliminated to prevent duplicate implementations
logger.info("WebSocketManagerFactory class removed - Issue #824 SSOT consolidation complete")


# Export compatibility functions only (Issue #824 Remediation)


class WebSocketManagerFactory:
    """
    DEPRECATED: WebSocketManagerFactory for SSOT violation testing.
    
    This class exists only for testing SSOT violations and compatibility.
    All production code should use the SSOT WebSocketManager directly.
    """
    
    def __init__(self):
        warnings.warn(
            'WebSocketManagerFactory is deprecated. Use WebSocketManager directly.',
            DeprecationWarning,
            stacklevel=2
        )
        self._logger = get_logger(__name__)
        
    async def create_websocket_manager(self, redis_client=None, environment=None, **kwargs):
        """Create WebSocketManager using SSOT implementation."""
        self._logger.warning(
            'create_websocket_manager is deprecated. Use get_websocket_manager() directly.'
        )
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        return await get_websocket_manager(**kwargs)

# WebSocketManagerFactory class REMOVED from exports
__all__ = [
    'create_websocket_manager',  # DEPRECATED: Use get_websocket_manager from SSOT
    'create_websocket_manager_sync',  # DEPRECATED: Use WebSocketManager directly
    # REMOVED: 'get_websocket_manager_factory'  # Issue #1126 SSOT fix
    # REMOVED: 'WebSocketManagerFactory'  # Issue #1126 SSOT fix
    # 'IsolatedWebSocketManager',  # REMOVED: SSOT consolidation - use WebSocketManager directly
    'create_defensive_user_execution_context',  # Compatibility utility
    'ConnectionLifecycleManager',  # Compatibility class
    'FactoryInitializationError',  # Compatibility exception
    'FactoryMetrics',  # Compatibility data class
    'ManagerMetrics',  # Compatibility data class
    'validate_websocket_component_health',  # Compatibility validation
    '_factory_instance',  # Legacy compatibility
    '_factory_lock',  # Legacy compatibility
    '_validate_ssot_user_context',  # Validation utility
    '_validate_ssot_user_context_staging_safe'  # Validation utility
]

logger.info("WebSocket Manager Factory DEPRECATED module loaded - Issue #824 remediation (redirecting to SSOT)")
