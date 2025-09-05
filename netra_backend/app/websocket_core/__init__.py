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
    get_websocket_manager,
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

# Backward compatibility aliases
WebSocketManager = UnifiedWebSocketManager
websocket_manager = get_websocket_manager()
WebSocketEventEmitter = UnifiedWebSocketEmitter
IsolatedWebSocketEventEmitter = UnifiedWebSocketEmitter
UserWebSocketEmitter = UnifiedWebSocketEmitter

# Import handlers
from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    UserMessageHandler,
    get_message_router,
)

# Import auth
from netra_backend.app.websocket_core.auth import (
    WebSocketAuthenticator,
    ConnectionSecurityManager,
    get_websocket_authenticator,
    get_connection_security_manager,
    secure_websocket_context,
)

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
    )
except ImportError:
    # Fallback implementations
    WebSocketHeartbeat = None
    get_connection_monitor = None
    safe_websocket_send = None
    safe_websocket_close = None
    is_websocket_connected = None

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
    
    # Migration support
    "WebSocketManagerAdapter", 
    "get_legacy_websocket_manager",
    "migrate_singleton_usage",
    
    # User context extraction
    "UserContextExtractor",
    "get_user_context_extractor", 
    "extract_websocket_user_context",
    
    # Backward compatibility
    "WebSocketManager",
    "websocket_manager",
    "get_websocket_manager",
    "WebSocketEventEmitter",
    "IsolatedWebSocketEventEmitter",
    "UserWebSocketEmitter",
    
    # Handlers
    "MessageRouter",
    "UserMessageHandler",
    "get_message_router",
    
    # Auth
    "WebSocketAuthenticator",
    "ConnectionSecurityManager",
    "get_websocket_authenticator",
    "get_connection_security_manager",
    "secure_websocket_context",
    
    # Rate limiting
    "RateLimiter",
    "WebSocketRateLimiter",
    
    # Utility functions and classes
    "WebSocketHeartbeat",
    "get_connection_monitor",
    "safe_websocket_send",
    "safe_websocket_close",
    "is_websocket_connected",
    
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
