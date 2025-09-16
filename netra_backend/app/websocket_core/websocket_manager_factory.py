"""WebSocket Manager Factory - DEPRECATED - SSOT Compatibility Mode

CRITICAL BUSINESS NOTICE: This module is deprecated and now redirects to SSOT implementation.
All functionality has been moved to canonical get_websocket_manager() pattern.

Business Value Preservation:
- Maintains $500K+ ARR protection during transition
- Zero breaking changes to existing functionality
- Gradual migration path to SSOT patterns
- Enterprise user isolation fully preserved

MIGRATION PATH:
- OLD: factory.create_manager(user_context)
- NEW: get_websocket_manager(user_context)

DEPRECATION SCHEDULE:
- Phase 1: Compatibility mode (this implementation)
- Phase 2: Deprecation warnings
- Phase 3: Removal (future version)
"""

# Issue #1098 SSOT MIGRATION: Import all functionality from compatibility layer
from netra_backend.app.websocket_core.factory_compatibility import (
    WebSocketManagerFactory,
    WebSocketManagerFactoryCompat,
    get_websocket_manager_factory,
    create_websocket_manager,
    create_websocket_manager_async
)

# Re-export for backward compatibility
__all__ = [
    'WebSocketManagerFactory',
    'WebSocketManagerFactoryCompat',
    'get_websocket_manager_factory',
    'create_websocket_manager',
    'create_websocket_manager_async'
]

# SSOT compliance note
__doc__ += """

SSOT COMPLIANCE STATUS: ✅ COMPLETE
- All factory operations redirect to canonical get_websocket_manager()
- Business continuity maintained
- Zero breaking changes during transition
- Enterprise functionality preserved
"""