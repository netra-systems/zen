try:
    from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge
    print("✅ Factory WebSocket Bridge Factory: OK")
except Exception as e:
    print(f"❌ Factory WebSocket Bridge Factory: FAILED - {str(e)}")