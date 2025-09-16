# Shim module for backward compatibility
from netra_backend.app.websocket_core.types import ConnectionInfo
from netra_backend.app.core.websocket_recovery_types import ConnectionState

# Export for backward compatibility
__all__ = ['ConnectionInfo', 'ConnectionState']
