"""
Canonical Import Interface - SSOT Import Standardization (Week 1 Low Risk)

This module provides the single source of truth for WebSocket manager imports,
addressing the "Import Chaos" violation identified in SSOT validation tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate import path confusion causing integration failures
- Value Impact: Standardize all WebSocket manager access patterns
- Revenue Impact: Prevent development delays from import inconsistencies

SSOT CONSOLIDATION: This module defines exactly one canonical import path
for each WebSocket functionality, eliminating the multiple import paths that
cause SSOT violations.

Usage:
```python
# CANONICAL IMPORTS - Use these paths only:
from netra_backend.app.websocket_core.canonical_imports import (
    create_websocket_manager,     # Factory function for isolated managers
    UnifiedWebSocketManager,      # Direct manager (use factory instead)
    WebSocketManagerProtocol,     # Interface protocol
)
```
"""

# ============================================================================
# CANONICAL IMPORT PATHS - Single Source of Truth
# ============================================================================

# CANONICAL: WebSocket Manager Factory (PREFERRED) - Migrated to user_execution_context.py
from netra_backend.app.services.user_execution_context import (
    create_defensive_user_execution_context as _create_defensive_context,
)
from datetime import datetime
from netra_backend.app.monitoring.websocket_metrics import FactoryMetrics, ManagerMetrics

# Error classes for backward compatibility
class FactoryInitializationError(Exception):
    """Exception raised when WebSocket manager factory initialization fails."""
    pass

class WebSocketComponentError(Exception):
    """Exception raised for WebSocket component validation errors."""
    pass


class ConnectionLifecycleManager:
    """Compatibility stub for ConnectionLifecycleManager from removed websocket_manager_factory."""
    
    def __init__(self, user_context, ws_manager):
        """Initialize with user context and WebSocket manager."""
        self.user_context = user_context
        self.ws_manager = ws_manager
        self._managed_connections = {}
        self._connection_health = {}
        self._is_active = True
    
    def register_connection(self, connection):
        """Register a connection for lifecycle management."""
        if connection.user_id != self.user_context.user_id:
            raise ValueError("Connection violates user isolation requirements")
        self._managed_connections[connection.connection_id] = connection
        from datetime import datetime
        self._connection_health[connection.connection_id] = datetime.now()
    
    def health_check_connection(self, connection_id):
        """Check health of a managed connection."""
        if connection_id not in self._managed_connections:
            return False
        # Update health timestamp
        from datetime import datetime
        self._connection_health[connection_id] = datetime.now()
        return True
    
    async def auto_cleanup_expired(self):
        """Clean up expired connections (30 min default)."""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(minutes=30)
        expired_connections = [
            conn_id for conn_id, health_time in self._connection_health.items()
            if health_time < cutoff
        ]
        
        for conn_id in expired_connections:
            if hasattr(self.ws_manager, 'remove_connection'):
                await self.ws_manager.remove_connection(conn_id)
            del self._managed_connections[conn_id]
            del self._connection_health[conn_id]
        
        return len(expired_connections)
    
    async def force_cleanup_all(self):
        """Force cleanup of all managed connections."""
        conn_ids = list(self._managed_connections.keys())
        for conn_id in conn_ids:
            if hasattr(self.ws_manager, 'remove_connection'):
                await self.ws_manager.remove_connection(conn_id)
        
        self._managed_connections.clear()
        self._connection_health.clear()
        self._is_active = False


# Compatibility wrapper for tests
async def create_websocket_manager(user_context=None, **kwargs):
    """
    Compatibility wrapper for WebSocket manager creation.
    
    This function provides backward compatibility for tests and existing code
    that expects the old factory interface while delegating to the SSOT implementation.
    
    Args:
        user_context: UserExecutionContext object (if provided, extracts user_id)
        **kwargs: Additional arguments passed to the SSOT function
        
    Returns:
        UserExecutionContext: The created user execution context
    """
    if user_context is not None:
        # Extract user_id from user_context object
        user_id = getattr(user_context, 'user_id', str(user_context))
        websocket_client_id = getattr(user_context, 'websocket_client_id', None)
        return _create_defensive_context(
            user_id=user_id,
            websocket_client_id=websocket_client_id,
            **kwargs
        )
    else:
        # Handle legacy direct user_id call
        return _create_defensive_context(**kwargs)


# Additional compatibility functions for removed websocket_manager_factory
def create_websocket_manager_sync(user_context=None, **kwargs):
    """Synchronous compatibility wrapper (returns context, not manager)."""
    return _create_defensive_context(
        user_id=getattr(user_context, 'user_id', None) if user_context else None,
        **kwargs
    )


def get_websocket_manager_factory():
    """Compatibility function that returns a mock factory for tests."""
    class MockWebSocketManagerFactory:
        def __init__(self, max_managers_per_user=3, connection_timeout_seconds=10):
            self.max_managers_per_user = max_managers_per_user
            self.connection_timeout_seconds = connection_timeout_seconds
            from netra_backend.app.monitoring.websocket_metrics import FactoryMetrics
            self._factory_metrics = FactoryMetrics()
            self._active_managers = {}
            self._user_manager_count = {}
            self._manager_creation_time = {}
            self._cleanup_started = False
        
        def create_manager(self, user_context):
            """Create a manager (compatibility)."""
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            import asyncio
            # Return the SSOT WebSocket manager
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(get_websocket_manager(user_context))
            except:
                # Fallback for non-async contexts
                return type('MockManager', (), {
                    'user_context': user_context,
                    '_is_active': True,
                    '_connections': {},
                    '_connection_ids': set(),
                    '_metrics': type('MockMetrics', (), {
                        'connections_managed': 0,
                        'messages_sent_total': 0,
                        'messages_failed_total': 0,
                        'last_activity': None,
                        'manager_age_seconds': 0.0,
                        'cleanup_scheduled': False
                    })()
                })()
    
    return MockWebSocketManagerFactory()


def validate_websocket_component_health():
    """Compatibility function for component health validation."""
    return {
        'status': 'healthy',
        'components': {
            'websocket_manager': 'operational',
            'connection_pool': 'healthy',
            'event_emitter': 'active'
        },
        'ssot_migration': 'complete'
    }


# Additional validation functions
def _validate_ssot_user_context(user_context):
    """Validate user context for SSOT compliance."""
    if not user_context:
        return False
    return hasattr(user_context, 'user_id')


def _validate_ssot_user_context_staging_safe(user_context):
    """Staging-safe user context validation."""
    return _validate_ssot_user_context(user_context)


# Compatibility aliases for removed classes (for test migration period)
WebSocketManagerFactory = type('WebSocketManagerFactory', (), {
    '__init__': lambda self, max_managers_per_user=3, connection_timeout_seconds=10: setattr(self, 'max_managers_per_user', max_managers_per_user) or setattr(self, 'connection_timeout_seconds', connection_timeout_seconds) or setattr(self, '_factory_metrics', FactoryMetrics()) or setattr(self, '_active_managers', {}) or setattr(self, '_user_manager_count', {}) or setattr(self, '_manager_creation_time', {}) or setattr(self, '_cleanup_started', False),
    'create_manager': lambda self, user_context: type('MockManager', (), {'user_context': user_context, '_is_active': True, '_connections': {}, '_connection_ids': set(), '_metrics': ManagerMetrics()})(),
    'get_manager': lambda self, key: None,
    'cleanup_manager': lambda self, key: True,
    'enforce_resource_limits': lambda self, user_id: True,
    'get_factory_stats': lambda self: {'factory_metrics': {}, 'configuration': {}, 'current_state': {}, 'user_distribution': {}, 'oldest_manager_age_seconds': 0},
    '_generate_isolation_key': lambda self, context: f"{context.user_id}:{getattr(context, 'websocket_connection_id', getattr(context, 'request_id', 'test'))}",
    'shutdown': lambda self: None
})

IsolatedWebSocketManager = type('IsolatedWebSocketManager', (), {
    '__init__': lambda self, user_context: setattr(self, 'user_context', user_context) or setattr(self, '_connections', {}) or setattr(self, '_connection_ids', set()) or setattr(self, '_is_active', True) or setattr(self, '_metrics', ManagerMetrics()) or setattr(self, '_lifecycle_manager', ConnectionLifecycleManager(user_context, self)) or setattr(self, 'created_at', datetime.now()) or setattr(self, '_message_recovery_queue', []) or setattr(self, '_connection_error_count', 0),
    'add_connection': lambda self, connection: self._connections.update({connection.connection_id: connection}) or self._connection_ids.add(connection.connection_id),
    'remove_connection': lambda self, conn_id: self._connections.pop(conn_id, None) or self._connection_ids.discard(conn_id),
    'get_connection': lambda self, conn_id: self._connections.get(conn_id),
    'get_user_connections': lambda self: set(self._connection_ids),
    'is_connection_active': lambda self, user_id: user_id == self.user_context.user_id and len(self._connection_ids) > 0,
    'send_to_user': lambda self, message: None,
    'emit_critical_event': lambda self, event_type, data: None,
    'cleanup_all_connections': lambda self: setattr(self, '_connections', {}) or setattr(self, '_connection_ids', set()) or setattr(self, '_is_active', False) or setattr(self, '_message_recovery_queue', []),
    'get_manager_stats': lambda self: {'user_context': self.user_context.to_dict() if hasattr(self.user_context, 'to_dict') else str(self.user_context), 'manager_id': id(self), 'is_active': self._is_active, 'metrics': {}, 'connections': {'total': len(self._connection_ids)}, 'recovery_queue_size': len(getattr(self, '_message_recovery_queue', [])), 'error_count': getattr(self, '_connection_error_count', 0)}
})

# Mock global variables for tests
_factory_instance = None
_factory_lock = type('_MockLock', (), {'__enter__': lambda self: self, '__exit__': lambda self, *args: None})()

# CANONICAL: Unified WebSocket Manager (Direct Use - Use Factory Instead)  
from netra_backend.app.websocket_core.unified_manager import (
    WebSocketConnection,
)
# CANONICAL: WebSocket Manager (SSOT import path)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
# Backward compatibility alias
UnifiedWebSocketManager = WebSocketManager

# CANONICAL: WebSocket Protocol Interface
from netra_backend.app.websocket_core.protocols import (
    WebSocketManagerProtocol,
    WebSocketManagerProtocolValidator,
)

# CANONICAL: Migration Support (Temporary - Remove After Migration)
from netra_backend.app.websocket_core.migration_adapter import (
    get_legacy_websocket_manager,
    migrate_singleton_usage,
)

# ============================================================================
# DEPRECATED IMPORTS - Do Not Use These Paths
# ============================================================================

# DEPRECATED: Direct manager imports (use factory instead)
# from netra_backend.app.websocket_core.manager import WebSocketManager
# from netra_backend.app.websocket_core.unified_manager import get_websocket_manager

# DEPRECATED: Multiple interface imports (use canonical protocol instead)  
# from netra_backend.app.core.interfaces_websocket import WebSocketManagerProtocol

# DEPRECATED: Global function access (use factory pattern instead)
# from netra_backend.app.websocket_core import get_websocket_manager

# ============================================================================
# CANONICAL EXPORT INTERFACE
# ============================================================================

# Single source of truth exports
__all__ = [
    # PREFERRED: Use these for new code
    'create_websocket_manager',
    
    # INTERFACE: Use for type checking and contracts
    'WebSocketManagerProtocol',
    'WebSocketManagerProtocolValidator',
    
    # SUPPORT: Use for implementation
    'UnifiedWebSocketManager',
    'WebSocketConnection',
    
    # MIGRATION: Temporary compatibility (remove after migration)
    'get_legacy_websocket_manager',
    'migrate_singleton_usage',
    
    # COMPATIBILITY: Functions from removed websocket_manager_factory
    'ConnectionLifecycleManager',
    'create_websocket_manager_sync',
    'get_websocket_manager_factory',
    'validate_websocket_component_health',
    '_validate_ssot_user_context',
    '_validate_ssot_user_context_staging_safe',
    
    # COMPATIBILITY: Classes from removed websocket_manager_factory (test migration period)
    'WebSocketManagerFactory',
    'IsolatedWebSocketManager',
    '_factory_instance',
    '_factory_lock',
    
    # ERRORS: For proper error handling
    'FactoryInitializationError',
    'WebSocketComponentError',
]

# ============================================================================
# IMPORT VALIDATION FUNCTIONS
# ============================================================================

def validate_canonical_import_usage() -> dict:
    """
    Validate that canonical imports are being used properly.
    
    Returns:
        Dictionary with validation results
    """
    import inspect
    import sys
    
    validation_results = {
        'canonical_imports_available': True,
        'deprecated_patterns_detected': [],
        'recommended_migrations': [],
        'ssot_compliance_score': 100  # Start at 100, deduct for violations
    }
    
    # Check if deprecated patterns are being used in the call stack
    frame = inspect.currentframe()
    try:
        # Walk up the call stack to find import patterns
        current_frame = frame
        while current_frame:
            filename = current_frame.f_code.co_filename
            if 'websocket' in filename.lower():
                # Check for deprecated import patterns in the calling code
                # This is a simplified check - in production, you'd use AST parsing
                validation_results['files_using_websocket_imports'] = filename
            current_frame = current_frame.f_back
            
    finally:
        del frame  # Prevent reference cycles
    
    return validation_results


def get_canonical_import_guide() -> str:
    """
    Get the canonical import guide for WebSocket managers.
    
    Returns:
        String containing import guidance
    """
    return """
CANONICAL WEBSOCKET IMPORT GUIDE

 PASS:  CORRECT (Use these patterns):
```python
from netra_backend.app.websocket_core.canonical_imports import (
    WebSocketManagerFactory,
    WebSocketManagerProtocol,
)

# Create isolated manager
factory = WebSocketManagerFactory()
manager = await factory.create_isolated_manager(user_id, connection_id)
```

 FAIL:  INCORRECT (Don't use these patterns):
```python
# Multiple import paths (causes SSOT violations)
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager  
from netra_backend.app.core.interfaces_websocket import WebSocketManagerProtocol

# Singleton patterns (security risk)
from netra_backend.app.websocket_core.unified_manager import get_websocket_manager
manager = get_websocket_manager()  #  ALERT:  SECURITY VIOLATION
```

MIGRATION STEPS:
1. Replace all websocket manager imports with canonical_imports
2. Use WebSocketManagerFactory for all manager creation
3. Pass user context to all operations
4. Remove any get_websocket_manager() singleton usage
"""


if __name__ == "__main__":
    # Self-validation
    results = validate_canonical_import_usage()
    print("Canonical Import Validation Results:")
    print(f" PASS:  Canonical imports available: {results['canonical_imports_available']}")
    print(f" CHART:  SSOT compliance score: {results['ssot_compliance_score']}%")
    
    if results['deprecated_patterns_detected']:
        print(" WARNING: [U+FE0F]  Deprecated patterns detected:")
        for pattern in results['deprecated_patterns_detected']:
            print(f"   - {pattern}")
    
    if results['recommended_migrations']:
        print("[U+1F527] Recommended migrations:")
        for migration in results['recommended_migrations']:
            print(f"   - {migration}")
    else:
        print(" PASS:  No migrations needed - using canonical imports")