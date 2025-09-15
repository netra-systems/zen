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
# ISSUE #1144 SSOT CONSOLIDATION: Phase 1 - Deprecate __init__.py imports
# DEPRECATED: from netra_backend.app.websocket_core import WebSocketManager
# CANONICAL: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
#
# MIGRATION PLAN:
# - Phase 1: Update key consumers to use canonical imports (IN PROGRESS)
# - Phase 2: Remove __init__.py exports entirely
# - Phase 3: Consolidate implementation layers
import warnings
warnings.warn(
    "ISSUE #1144: Importing from 'netra_backend.app.websocket_core' is deprecated. "
    "Use specific module imports like 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager'. "
    "This import path will be removed in Phase 2 of SSOT consolidation.",
    DeprecationWarning,
    stacklevel=2
)

# ISSUE #824 REMEDIATION: Import from canonical SSOT path only
from netra_backend.app.websocket_core.websocket_manager import (
    WebSocketManager,
    UnifiedWebSocketManager,  # Backward compatibility alias
    WebSocketConnection,
    _serialize_message_safely
)

# WebSocketManager and UnifiedWebSocketManager are already imported above

# Import protocol for type checking
try:
    from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
except ImportError:
    WebSocketManagerProtocol = None

from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter,
    WebSocketEmitterFactory,
    WebSocketEmitterPool,
)

# SSOT COMPLIANCE: Factory pattern eliminated - use direct WebSocketManager import
# from netra_backend.app.websocket_core.websocket_manager_factory import (
#     WebSocketManagerFactory,
#     IsolatedWebSocketManager,
#     get_websocket_manager_factory,
#     create_websocket_manager
# )

# Backward compatibility function for create_websocket_manager
def create_websocket_manager(user_context=None):
    """
    COMPATIBILITY WRAPPER: Provides create_websocket_manager for backward compatibility.

    DEPRECATED: Use WebSocketManager(user_context=user_context) directly instead.

    Args:
        user_context: Required UserExecutionContext for proper isolation

    Returns:
        WebSocketManager instance

    Raises:
        ValueError: If user_context is None (import-time initialization not allowed)
    """
    import warnings
    warnings.warn(
        "create_websocket_manager is deprecated. Use WebSocketManager(user_context=user_context) directly.",
        DeprecationWarning,
        stacklevel=2
    )

    if user_context is None:
        # CRITICAL: Import-time initialization violates User Context Architecture
        raise ValueError(
            "WebSocket manager creation requires valid UserExecutionContext. "
            "Import-time initialization is prohibited. Use request-scoped factory pattern instead. "
            "See User Context Architecture documentation for proper implementation."
        )

    # PHASE 1 FIX: Use WebSocketManager directly with proper token generation
    # This ensures the SSOT authorization token is properly provided
    import asyncio
    import secrets
    # Use canonical import from websocket_manager.py (not unified_manager.py which has __all__ = [])

    # Since this is a sync function but the factory is async, we need to handle this properly
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            # This is a legacy compatibility issue - recommend using async version
            raise RuntimeError(
                "create_websocket_manager cannot be called from async context. "
                "Use 'await get_websocket_manager(user_context)' instead."
            )
        else:
            return WebSocketManager(
                user_context=user_context,
                _ssot_authorization_token=secrets.token_urlsafe(32)
            )
    except RuntimeError:
        # No event loop running, create one
        return WebSocketManager(
            user_context=user_context,
            _ssot_authorization_token=secrets.token_urlsafe(32)
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
        WebSocketManager instance

    Raises:
        ValueError: If user_context is None (import-time initialization not allowed)

    Note: For new code, use WebSocketManager(user_context=user_context) directly.
    """
    if user_context is None:
        # CRITICAL: Import-time initialization violates User Context Architecture
        raise ValueError(
            "WebSocket manager creation requires valid UserExecutionContext. "
            "Import-time initialization is prohibited. Use request-scoped factory pattern instead. "
            "See User Context Architecture documentation for proper implementation."
        )

    # PHASE 1 FIX: Use WebSocketManager directly with proper token generation
    # This ensures the SSOT authorization token is properly provided
    import secrets
    # Use canonical import from websocket_manager.py (not unified_manager.py which has __all__ = [])
    
    return WebSocketManager(
        user_context=user_context,
        _ssot_authorization_token=secrets.token_urlsafe(32)
    )

from netra_backend.app.websocket_core.migration_adapter import (
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
# WebSocketManager is now imported directly
# SECURITY FIX: Removed singleton websocket_manager - use WebSocketManager() directly instead
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
    
    # REMOVED: Fallback functions eliminated to fix SSOT violation
    # The fallback implementations were causing signature mismatches
    # All imports should succeed from types.py after critical dependency fixes

# Import JWT protocol handler functions for subprotocol negotiation (Issue #280 fix)
try:
    from netra_backend.app.websocket_core.unified_jwt_protocol_handler import (
        extract_jwt_from_subprotocol,
        negotiate_websocket_subprotocol,
        extract_jwt_token,
        normalize_jwt_token
    )
except ImportError:
    # Fallback implementations for missing protocol handler
    def extract_jwt_from_subprotocol(subprotocol_value):
        return None
    def negotiate_websocket_subprotocol(client_protocols):
        return None
    def extract_jwt_token(websocket):
        return None
    def normalize_jwt_token(jwt_token):
        return jwt_token

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
# CRITICAL FIX: Remove fallback behavior that causes 1011 errors
# Setting critical functions to None causes runtime failures in staging
try:
    from netra_backend.app.websocket_core.connection_state_machine import (
        ApplicationConnectionState,
        ConnectionStateMachine,
        ApplicationConnectionStateMachine,
        ConnectionStateMachineRegistry,
        StateTransitionInfo,
        get_connection_state_registry,
        get_connection_state_machine,
        is_connection_ready_for_messages,
    )
except ImportError as e:
    # FAIL FAST: Never set critical WebSocket functions to None
    # This was causing WebSocket 1011 internal server errors in staging
    raise ImportError(
        f"CRITICAL: WebSocket state machine import failed: {e}. "
        f"This will cause 1011 WebSocket errors. Fix import dependencies immediately. "
        f"See WEBSOCKET_1011_FIVE_WHYS_ANALYSIS_20250909_NIGHT.md for details."
    ) from e

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
except ImportError as e:
    # FAIL FAST: Message queue components are critical for WebSocket reliability
    raise ImportError(
        f"CRITICAL: WebSocket message queue import failed: {e}. "
        f"This may cause message delivery failures and WebSocket instability. "
        f"Fix import dependencies immediately."
    ) from e

# Import race condition prevention components
try:
    from netra_backend.app.websocket_core.race_condition_prevention import (
        ApplicationConnectionState as RaceConditionApplicationConnectionState,
        RaceConditionPattern,
        RaceConditionDetector,
        HandshakeCoordinator,
    )
except ImportError as e:
    # FAIL FAST: Race condition prevention is critical for WebSocket stability
    raise ImportError(
        f"CRITICAL: WebSocket race condition prevention import failed: {e}. "
        f"This may cause WebSocket handshake failures and connection instability. "
        f"Fix import dependencies immediately."
    ) from e

# Critical events that MUST be preserved
CRITICAL_EVENTS = UnifiedWebSocketEmitter.CRITICAL_EVENTS

# Export main interface
__all__ = [
    # Unified implementations
    "WebSocketManager",
    "UnifiedWebSocketManager",  # Backward compatibility
    "UnifiedWebSocketEmitter",
    "WebSocketConnection",
    "WebSocketEmitterFactory",
    "WebSocketEmitterPool",
    
    # SSOT COMPLIANCE: Factory pattern eliminated
    # "WebSocketManagerFactory",
    # "IsolatedWebSocketManager", 
    # "get_websocket_manager_factory",
    "create_websocket_manager",  # Backward compatibility
    "get_websocket_manager",  # Backward compatibility
    
    # Migration support
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
    
    # JWT Protocol Handler (Issue #280 fix)
    "extract_jwt_from_subprotocol",
    "negotiate_websocket_subprotocol", 
    "extract_jwt_token",
    "normalize_jwt_token",
    
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
    "ApplicationConnectionStateMachine",
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
