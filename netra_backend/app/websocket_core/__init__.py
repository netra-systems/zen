"""
WebSocket Core - Unified WebSocket Infrastructure

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Development Velocity
- Value Impact: Single WebSocket concept, eliminates 90+ redundant files
- Strategic Impact: Atomic consolidation, clean import structure

This package replaces the entire /websocket/ directory structure with 5 focused modules:
- manager.py: Connection lifecycle and message routing
- types.py: Data models and type definitions  
- handlers.py: Message processing and routing
- auth.py: Authentication and security
- utils.py: Shared utilities and helpers

CRITICAL: This is the ONLY WebSocket implementation in the system.
All imports should use this package, not the legacy /websocket/ directory.
"""

# Core WebSocket Manager - Single Source of Truth
from netra_backend.app.websocket_core.manager import (
    WebSocketManager,
    get_websocket_manager,
    websocket_context
)

# Type Definitions
from netra_backend.app.websocket_core.types import (
    # Core types
    WebSocketConnectionState,
    MessageType,
    ConnectionInfo,
    WebSocketMessage,
    ServerMessage,
    ErrorMessage,
    BroadcastMessage,
    JsonRpcMessage,
    
    # Statistics and metrics
    WebSocketStats,
    WebSocketValidationError,
    RateLimitInfo,
    ConnectionMetrics,
    RoomInfo,
    
    # Configuration and auth
    WebSocketConfig,
    AuthInfo,
    
    # Type aliases
    MessagePayload,
    ConnectionId,
    UserId,
    RoomId,
    ThreadId,
    MessageId,
    
    # Utility functions
    normalize_message_type,
    create_standard_message,
    create_error_message,
    create_server_message,
    is_jsonrpc_message,
    convert_jsonrpc_to_websocket_message
)

# Import BroadcastResult from the single source of truth
from netra_backend.app.schemas.websocket_models import BroadcastResult

# Message Handlers
from netra_backend.app.websocket_core.handlers import (
    MessageHandler,
    BaseMessageHandler,
    HeartbeatHandler,
    UserMessageHandler,
    JsonRpcHandler,
    ErrorHandler,
    MessageRouter,
    get_message_router,
    get_router_handler_count,
    list_registered_handlers,
    send_error_to_websocket,
    send_system_message
)

# Authentication and Security
from netra_backend.app.websocket_core.auth import (
    RateLimiter,
    WebSocketAuthenticator,
    ConnectionSecurityManager,
    get_websocket_authenticator,
    get_connection_security_manager,
    secure_websocket_context,
    validate_message_size,
    sanitize_user_input,
    validate_websocket_origin
)

# Utilities
from netra_backend.app.websocket_core.utils import (
    # ID and timestamp utilities
    generate_connection_id,
    generate_message_id,
    get_current_timestamp,
    get_current_iso_timestamp,
    
    # WebSocket utilities
    is_websocket_connected,
    safe_websocket_send,
    safe_websocket_close,
    
    # Helper classes
    WebSocketMessageQueue,
    WebSocketHeartbeat,
    WebSocketConnectionMonitor,
    get_connection_monitor,
    
    # Message utilities
    parse_websocket_message,
    validate_message_structure,
    extract_user_info_from_message,
    broadcast_to_websockets,
    format_websocket_error_response,
    create_connection_info,
    
    # Context managers
    websocket_message_queue_context,
    websocket_heartbeat_context
)

# Modern WebSocket abstraction
from netra_backend.app.websocket_core.modern_websocket_abstraction import (
    ModernWebSocketWrapper,
    ModernWebSocketManager,
    ModernWebSocketProtocol,
    get_modern_websocket_manager,
    websocket_connection_context,
    WebSocketClientProtocol,
    WebSocketServerProtocol
)

# Version info
__version__ = "1.0.0"
__description__ = "Unified WebSocket infrastructure for Netra backend"

# Export main interface for backward compatibility
__all__ = [
    # Core manager
    "WebSocketManager",
    "get_websocket_manager",
    "websocket_context",
    
    # Essential types
    "MessageType",
    "WebSocketMessage",
    "ServerMessage",
    "ErrorMessage",
    "BroadcastResult",
    "WebSocketStats",
    "ConnectionInfo",
    "AuthInfo",
    
    # Message handling
    "MessageRouter", 
    "get_message_router",
    "send_error_to_websocket",
    "send_system_message",
    
    # Authentication
    "WebSocketAuthenticator",
    "get_websocket_authenticator", 
    "secure_websocket_context",
    
    # Utilities
    "generate_connection_id",
    "is_websocket_connected",
    "safe_websocket_send",
    "safe_websocket_close",
    "get_connection_monitor",
    "create_standard_message",
    "create_error_message",
    
    # Modern WebSocket abstraction
    "ModernWebSocketWrapper",
    "ModernWebSocketManager",
    "get_modern_websocket_manager",
    "websocket_connection_context",
    "WebSocketClientProtocol",
    "WebSocketServerProtocol"
]

# Legacy compatibility - these will be removed in future versions
# Warn users about deprecated imports
import warnings
from typing import Dict

class LegacyWebSocketImportWarning(UserWarning):
    """Warning for deprecated WebSocket imports."""
    pass

def _warn_legacy_import(old_path: str, new_path: str) -> None:
    """Warn about legacy import usage."""
    warnings.warn(
        f"Import from '{old_path}' is deprecated. "
        f"Use 'from netra_backend.app.websocket_core import {new_path}' instead.",
        LegacyWebSocketImportWarning,
        stacklevel=3
    )

# Backward compatibility aliases (DEPRECATED)
UnifiedWebSocketManager = WebSocketManager  # Legacy name

def get_unified_manager() -> WebSocketManager:
    """Get WebSocket manager (legacy compatibility)."""
    _warn_legacy_import(
        "netra_backend.app.websocket.unified.manager.get_unified_manager",
        "get_websocket_manager"
    )
    return get_websocket_manager()

# Migration helper
def migrate_from_legacy_websocket() -> Dict[str, str]:
    """Return migration mapping for legacy imports."""
    return {
        "netra_backend.app.websocket.unified.manager.UnifiedWebSocketManager": "netra_backend.app.websocket_core.WebSocketManager",
        "netra_backend.app.websocket.unified.manager.get_unified_manager": "netra_backend.app.websocket_core.get_websocket_manager", 
        "netra_backend.app.websocket.connection.ConnectionInfo": "netra_backend.app.websocket_core.ConnectionInfo",
        "netra_backend.app.websocket.connection.ConnectionManager": "netra_backend.app.websocket_core.WebSocketManager",
        "netra_backend.app.websocket.unified_websocket_manager": "netra_backend.app.websocket_core",
        "netra_backend.app.websocket.rate_limiter.RateLimiter": "netra_backend.app.websocket_core.RateLimiter",
        "netra_backend.app.websocket.error_handler.WebSocketErrorHandler": "netra_backend.app.websocket_core.ErrorHandler",
        "netra_backend.app.websocket.room_manager.RoomManager": "netra_backend.app.websocket_core.WebSocketManager.join_room/leave_room"
    }