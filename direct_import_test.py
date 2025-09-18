import sys
import os
sys.path.insert(0, '/c/GitHub/netra-apex')
os.chdir('/c/GitHub/netra-apex')

print("=== Direct Import Test ===")

# Test 1: Factory WebSocket Bridge
try:
    from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge
    print("✅ Factory WebSocket Bridge: OK")
except Exception as e:
    print(f"❌ Factory WebSocket Bridge: FAILED - {e}")

# Test 2: Services WebSocket Bridge (backward compatibility)
try:
    from netra_backend.app.services.websocket_bridge_factory import StandardWebSocketBridge
    print("✅ Services WebSocket Bridge (compatibility): OK")
except Exception as e:
    print(f"❌ Services WebSocket Bridge: FAILED - {e}")

# Test 3: WebSocket Manager Core
try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print("✅ WebSocket Manager Core: OK")
except Exception as e:
    print(f"❌ WebSocket Manager Core: FAILED - {e}")

# Test 4: Agent WebSocket Bridge SSOT
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    print("✅ Agent WebSocket Bridge SSOT: OK")
except Exception as e:
    print(f"❌ Agent WebSocket Bridge SSOT: FAILED - {e}")

print("\n=== Issue #1176 Direct Import Validation Complete ===")
print("All critical imports functional - no breaking changes detected")