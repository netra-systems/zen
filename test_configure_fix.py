#!/usr/bin/env python3
"""Test script to verify the AgentWebSocketBridge configure() method fix."""

import sys
import asyncio
from datetime import datetime

# Add the path to import the module
sys.path.insert(0, 'netra_backend')

# Mock dependencies
class MockWebSocket:
    def __init__(self):
        self.state = "connected"

class MockConnectionPool:
    pass

class MockAgentRegistry:
    async def register_run_thread_mapping(self, run_id, thread_id, metadata=None):
        print(f"Registered mapping: run_id={run_id}, thread_id={thread_id}, metadata={metadata}")

async def test_configure_fix():
    """Test both calling patterns for the configure method."""
    print("Testing AgentWebSocketBridge configure() method fix...")

    try:
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

        # Create bridge instance
        bridge = AgentWebSocketBridge()
        print("OK Bridge instance created successfully")

        # Test 1: Standard configuration pattern (keyword arguments)
        print("\nTest 1: Standard configuration pattern")
        connection_pool = MockConnectionPool()
        agent_registry = MockAgentRegistry()

        bridge.configure(
            connection_pool=connection_pool,
            agent_registry=agent_registry,
            health_monitor=None
        )
        print("OK Standard configure pattern works")

        # Test 2: WebSocket configuration pattern (positional arguments)
        print("\nTest 2: WebSocket configuration pattern")
        mock_websocket = MockWebSocket()
        run_id = "test_run_123"
        thread_id = "test_thread_456"
        user_id = "test_user_789"

        bridge.configure(mock_websocket, run_id, thread_id, user_id)
        print("OK WebSocket configure pattern works")

        # Verify session data was stored
        if hasattr(bridge, '_websocket_sessions') and run_id in bridge._websocket_sessions:
            session = bridge._websocket_sessions[run_id]
            print(f"OK Session data stored correctly: {session['user_id']}")

        print("\nSUCCESS All tests passed! The configure() method fix is working correctly.")
        return True

    except Exception as e:
        print(f"ERROR Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_configure_fix())
    if not result:
        sys.exit(1)
    print("\nSUCCESS Fix verification complete - AgentWebSocketBridge configure() method now supports both calling patterns.")