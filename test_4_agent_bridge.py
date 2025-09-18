try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    print("✅ AgentWebSocketBridge SSOT: OK")
except Exception as e:
    print(f"❌ AgentWebSocketBridge SSOT: FAILED - {str(e)}")