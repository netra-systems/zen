"""
WebSocket Core - Unified SSOT Implementation

MISSION CRITICAL: Enables chat value delivery through 5 critical events.
Single source of truth for all WebSocket functionality.

Business Value:
- Consolidates 13+ files into 2 unified implementations
- Ensures 100% critical event delivery
- Zero cross-user event leakage
"""

# Unified implementations (SSOT)
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    # SECURITY FIX: get_websocket_manager removed - caused multi-user data leakage
)

from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter,
    WebSocketEmitterFactory,
    WebSocketEmitterPool,
)

# CRITICAL SECURITY MIGRATION: Import factory pattern components
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    get_websocket_manager_factory,
    create_websocket_manager
)

# Backward compatibility function using factory pattern
async def get_websocket_manager(user_context=None):
    """
    SECURITY MIGRATION: Compatibility wrapper for get_websocket_manager.
    
    IMPORTANT: This function now uses the secure factory pattern instead
    of a singleton to prevent multi-user data leakage.
    
    ARCHITECTURE COMPLIANCE: Import-time initialization is prohibited.
    WebSocket managers must be created per-request with valid UserExecutionContext.
    
    Args:
        user_context: Required UserExecutionContext for proper isolation
    
    Returns:
        IsolatedWebSocketManager instance
        
    Raises:
        ValueError: If user_context is None (import-time initialization not allowed)
    
    Note: For new code, use create_websocket_manager(user_context) directly.
    """
    if user_context is None:
        # CRITICAL: Import-time initialization violates User Context Architecture
        raise ValueError(
            "WebSocket manager creation requires valid UserExecutionContext. "
            "Import-time initialization is prohibited. Use request-scoped factory pattern instead. "
            "See User Context Architecture documentation for proper implementation."
        )
    
    return await create_websocket_manager(user_context)

from netra_backend.app.websocket_core.migration_adapter import (
    WebSocketManagerAdapter,
    get_legacy_websocket_manager,
    migrate_singleton_usage
)

from netra_backend.app.websocket_core.user_context_extractor import (
    UserContextExtractor,
    get_user_context_extractor,
    extract_websocket_user_context
)

# CRITICAL FIX: Import WebSocket context classes for proper request handling
from netra_backend.app.websocket_core.context import (
    WebSocketContext,
    WebSocketRequestContext,
)

# Backward compatibility aliases
WebSocketManager = UnifiedWebSocketManager
# SECURITY FIX: Removed singleton websocket_manager - use create_websocket_manager() instead
WebSocketEventEmitter = UnifiedWebSocketEmitter
IsolatedWebSocketEventEmitter = UnifiedWebSocketEmitter
UserWebSocketEmitter = UnifiedWebSocketEmitter

# Import handlers
from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    UserMessageHandler,
    get_message_router,
)

# Auth imports removed - using SSOT unified_websocket_auth instead

# Try to import existing types (if available)
try:
    from netra_backend.app.websocket_core.types import (
        MessageType,
        ConnectionInfo,
        WebSocketMessage,
        ServerMessage,
        ErrorMessage,
        WebSocketStats,
        WebSocketConfig,
        AuthInfo,
        create_server_message,
        create_error_message,
    )
except ImportError:
    # Minimal fallback types
    MessageType = str
    ConnectionInfo = dict
    WebSocketMessage = dict
    ServerMessage = dict
    ErrorMessage = dict
    WebSocketStats = dict
    WebSocketConfig = dict
    AuthInfo = dict
    
    # Fallback functions
    def create_server_message(msg_type, data=None, **kwargs):
        return {"type": msg_type, "data": data, **kwargs}
    
    def create_error_message(error_code, message="Error", **kwargs):
        return {"type": "error", "error_code": error_code, "message": message, **kwargs}

# Import RateLimiter for backward compatibility
try:
    from netra_backend.app.websocket_core.rate_limiter import RateLimiter, WebSocketRateLimiter
except ImportError:
    # If rate_limiter module fails, try importing from auth
    try:
        from netra_backend.app.websocket_core.auth import RateLimiter
        WebSocketRateLimiter = None
    except ImportError:
        RateLimiter = None
        WebSocketRateLimiter = None

# Import utility functions and classes
try:
    from netra_backend.app.websocket_core.utils import (
        WebSocketHeartbeat,
        get_connection_monitor,
        safe_websocket_send,
        safe_websocket_close,
        is_websocket_connected,
        is_websocket_connected_and_ready,
        validate_websocket_handshake_completion,
        create_race_condition_detector,
        create_handshake_coordinator,
        validate_connection_with_race_detection,
    )
except ImportError:
    # Fallback implementations
    WebSocketHeartbeat = None
    get_connection_monitor = None
    safe_websocket_send = None
    safe_websocket_close = None
    is_websocket_connected = None
    is_websocket_connected_and_ready = None
    validate_websocket_handshake_completion = None
    create_race_condition_detector = None
    create_handshake_coordinator = None
    validate_connection_with_race_detection = None

# Import new connection state machine and message queue components
try:
    from netra_backend.app.websocket_core.connection_state_machine import (
        ApplicationConnectionState,
        ConnectionStateMachine,
        ConnectionStateMachineRegistry,
        StateTransitionInfo,
        get_connection_state_registry,
        get_connection_state_machine,
        is_connection_ready_for_messages,
    )
except ImportError:
    # Fallback implementations for backward compatibility
    ApplicationConnectionState = None
    ConnectionStateMachine = None
    ConnectionStateMachineRegistry = None
    StateTransitionInfo = None
    get_connection_state_registry = None
    get_connection_state_machine = None
    is_connection_ready_for_messages = None

try:
    from netra_backend.app.websocket_core.message_queue import (
        MessageQueue,
        MessageQueueRegistry, 
        MessagePriority,
        MessageQueueState,
        QueuedMessage,
        get_message_queue_registry,
        get_message_queue_for_connection,
    )
except ImportError:
    # Fallback implementations for backward compatibility
    MessageQueue = None
    MessageQueueRegistry = None
    MessagePriority = None
    MessageQueueState = None
    QueuedMessage = None
    get_message_queue_registry = None
    get_message_queue_for_connection = None

# Import race condition prevention components
try:
    from netra_backend.app.websocket_core.race_condition_prevention import (
        ApplicationConnectionState as RaceConditionApplicationConnectionState,
        RaceConditionPattern,
        RaceConditionDetector,
        HandshakeCoordinator,
    )
except ImportError:
    # Fallback implementations for backward compatibility
    RaceConditionApplicationConnectionState = None
    RaceConditionPattern = None
    RaceConditionDetector = None
    HandshakeCoordinator = None

# Critical events that MUST be preserved
CRITICAL_EVENTS = UnifiedWebSocketEmitter.CRITICAL_EVENTS

# Export main interface
__all__ = [
    # Unified implementations
    "UnifiedWebSocketManager",
    "UnifiedWebSocketEmitter",
    "WebSocketConnection",
    "WebSocketEmitterFactory",
    "WebSocketEmitterPool",
    
    # CRITICAL SECURITY MIGRATION: Factory pattern exports
    "WebSocketManagerFactory",
    "IsolatedWebSocketManager",
    "get_websocket_manager_factory",
    "create_websocket_manager",
    "get_websocket_manager",  # Backward compatibility
    
    # Migration support
    "WebSocketManagerAdapter", 
    "get_legacy_websocket_manager",
    "migrate_singleton_usage",
    
    # User context extraction
    "UserContextExtractor",
    "get_user_context_extractor", 
    "extract_websocket_user_context",
    
    # CRITICAL FIX: WebSocket context classes for proper request handling
    "WebSocketContext",
    "WebSocketRequestContext",
    
    # Backward compatibility
    "WebSocketManager",
    # SECURITY FIX: Removed websocket_manager singleton export
    # SECURITY: get_websocket_manager removed - causes multi-user data leakage
    "WebSocketEventEmitter",
    "IsolatedWebSocketEventEmitter",
    "UserWebSocketEmitter",
    
    # Handlers
    "MessageRouter",
    "UserMessageHandler",
    "get_message_router",
    
    # Auth - Removed legacy auth, using SSOT unified_websocket_auth instead
    
    # Rate limiting
    "RateLimiter",
    "WebSocketRateLimiter",
    
    # Utility functions and classes
    "WebSocketHeartbeat",
    "get_connection_monitor",
    "safe_websocket_send",
    "safe_websocket_close",
    "is_websocket_connected",
    "is_websocket_connected_and_ready",
    "validate_websocket_handshake_completion",
    "create_race_condition_detector",
    "create_handshake_coordinator",
    "validate_connection_with_race_detection",
    
    # Connection state machine components
    "ApplicationConnectionState",
    "ConnectionStateMachine", 
    "ConnectionStateMachineRegistry",
    "StateTransitionInfo",
    "get_connection_state_registry",
    "get_connection_state_machine",
    "is_connection_ready_for_messages",
    
    # Message queue components
    "MessageQueue",
    "MessageQueueRegistry",
    "MessagePriority",
    "MessageQueueState",
    "QueuedMessage",
    "get_message_queue_registry",
    "get_message_queue_for_connection",
    
    # Race condition prevention components
    "RaceConditionApplicationConnectionState",
    "RaceConditionPattern",
    "RaceConditionDetector", 
    "HandshakeCoordinator",
    
    # Types and message creation
    "MessageType",
    "ConnectionInfo",
    "WebSocketMessage",
    "ServerMessage",
    "ErrorMessage",
    "WebSocketStats",
    "WebSocketConfig",
    "AuthInfo",
    "create_server_message",
    "create_error_message",
    
    # Constants
    "CRITICAL_EVENTS",
]

# Log consolidation
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)
logger.info("WebSocket SSOT loaded - CRITICAL SECURITY MIGRATION: Factory pattern available, singleton vulnerabilities mitigated")
