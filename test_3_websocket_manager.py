try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print("✅ WebSocket Manager Core: OK")
except Exception as e:
    print(f"❌ WebSocket Manager Core: FAILED - {str(e)}")