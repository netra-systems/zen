# Shim module for backward compatibility
# Unified routes consolidated into main websocket.py
from netra_backend.app.routes.websocket import *
from netra_backend.app.routes.websocket import websocket_endpoint as unified_websocket_endpoint
from netra_backend.app.routes.websocket import websocket_health_check as unified_websocket_health

# Legacy configuration constants
UNIFIED_WEBSOCKET_CONFIG = {
    "heartbeat_interval": 30,
    "reconnect_delay": 1000,
    "max_retries": 5,
    "compression_enabled": True,
    "max_message_size": 1024 * 1024,  # 1MB
    "auth_required": True
}
