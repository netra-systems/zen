#!/usr/bin/env python3
"""
Simple test script to verify AgentWebSocketBridge configure method.
"""

def main():
    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool

        # Test 1: Check configure method exists
        bridge = AgentWebSocketBridge()
        assert hasattr(bridge, 'configure'), "Configure method missing"

        # Test 2: Test calling configure with None values (common test case)
        bridge.configure(
            connection_pool=None,
            agent_registry=None,
            health_monitor=None
        )

        # Test 3: Test calling configure with actual connection pool
        connection_pool = WebSocketConnectionPool()
        bridge.configure(
            connection_pool=connection_pool,
            agent_registry=None,
            health_monitor=None
        )

        print("SUCCESS: All configure method tests passed")
        return True

    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)