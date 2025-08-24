# Shim module for backward compatibility
# Unified routes consolidated into main websocket.py
from netra_backend.app.routes.websocket import *
from netra_backend.app.routes.websocket import websocket_endpoint as unified_websocket_endpoint
from netra_backend.app.routes.websocket import websocket_health_check as unified_websocket_health
