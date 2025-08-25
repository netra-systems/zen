# Shim module for backward compatibility
from netra_backend.app.websocket_core.recovery import ErrorRecoveryHandler
from netra_backend.app.core.error_context import ErrorContext
from netra_backend.app.schemas.startup_types import ErrorType

# Alias for backward compatibility - map WebSocketErrorRecoveryHandler to WebSocketRecoveryManager
from netra_backend.app.core.websocket_recovery_manager import WebSocketRecoveryManager
WebSocketErrorRecoveryHandler = WebSocketRecoveryManager
