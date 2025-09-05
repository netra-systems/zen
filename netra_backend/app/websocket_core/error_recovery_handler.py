# Shim module for backward compatibility
from netra_backend.app.websocket_core.recovery import ErrorRecoveryHandler
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.schemas.startup_types import ErrorType

# Alias for backward compatibility - map WebSocketErrorRecoveryHandler to WebSocketRecoveryManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
WebSocketRecoveryManager = UnifiedWebSocketManager
WebSocketErrorRecoveryHandler = WebSocketRecoveryManager
