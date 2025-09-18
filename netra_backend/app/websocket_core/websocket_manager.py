"""WebSocket Manager - SSOT Interface Layer for WebSocket Management

This module provides the unified WebSocket manager interface for the Golden Path.
It serves as the primary interface for WebSocket operations while maintaining
compatibility with legacy imports.

CRITICAL: This module supports the Golden Path user flow requirements:
- User isolation via ExecutionEngineFactory pattern
- WebSocket event emission (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- Connection state management for race condition prevention

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Enable reliable WebSocket communication for Golden Path
- Value Impact: Critical infrastructure for AI chat interactions
- Revenue Impact: Foundation for all AI-powered user interactions

ISSUE #954 PHASE 2 REMEDIATION: Converted to pure re-export interface layer.
This module now imports all functionality from unified_manager.py (SSOT) and re-exports
it for backward compatibility with the 698 imports that depend on this interface.

ISSUE #89 REMEDIATION: Migrated uuid.uuid4().hex[:8] patterns to UnifiedIDManager.
This eliminates ID collision risks and ensures consistent ID formats across WebSocket operations.
"""

# SSOT PHASE 2 CONSOLIDATION: All functionality now imported from unified_manager.py
from netra_backend.app.websocket_core.unified_manager import (
    # Core implementation class
    _UnifiedWebSocketManagerImplementation,

    # Factory functions
    get_websocket_manager,
    get_websocket_manager_async,
    create_websocket_manager,

    # Utility functions
    create_test_user_context,
    create_test_fallback_manager,
    check_websocket_service_available,
    get_manager_registry_status,
    validate_no_duplicate_managers_for_user,
    reset_manager_registry,

    # Registry and compatibility
    RegistryCompat,
    WebSocketManagerRegistry,

    # Factory wrapper
    _WSFactory,

    # Constants
    MAX_CONNECTIONS_PER_USER,

    # Compatibility aliases
    UnifiedWebSocketManager,
    WebSocketManager,
)

# Import shared types and functions from types module
from netra_backend.app.websocket_core.types import (
    WebSocketConnection,
    WebSocketManagerMode,
    create_isolated_mode,
    _serialize_message_safely,
    _get_enum_key_representation
)

# SSOT Protocol import consolidated from protocols module
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol

# Import logging
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)

# SSOT CONSOLIDATION: Compatibility aliases for legacy imports
# These maintain backward compatibility for the 698 imports that depend on this module
WebSocketConnectionManager = _UnifiedWebSocketManagerImplementation
WebSocketEventEmitter = _UnifiedWebSocketManagerImplementation  # Legacy alias
UnifiedWebSocketEmitter = _UnifiedWebSocketManagerImplementation  # Original emitter

# Export the protocol for type checking and SSOT compliance
__all__ = [
    'WebSocketManager',  # SSOT: Canonical WebSocket Manager import
    'WebSocketConnectionManager',  # SSOT: Backward compatibility alias (Issue #824)
    'WebSocketConnection',
    '_serialize_message_safely',
    'get_websocket_manager',  # SSOT: Synchronous factory function
    'get_websocket_manager_async',  # ISSUE #1184: Async factory function for proper await usage
    'check_websocket_service_available',  # Service availability check
    'create_test_user_context',  # Test context helper
    'create_test_fallback_manager',  # Test fallback helper
    'MAX_CONNECTIONS_PER_USER',  # Connection limit constant
    'WebSocketEventEmitter',  # Compatibility alias
    'UnifiedWebSocketEmitter',  # Original emitter
    # ISSUE #889 REMEDIATION: User-scoped manager registry functions
    'get_manager_registry_status',  # Registry monitoring
    'validate_no_duplicate_managers_for_user',  # Duplication validation
    'reset_manager_registry'  # Test cleanup utility
]

logger.info("WebSocket Manager interface module loaded - SSOT consolidation Phase 2 complete (Issue #954)")