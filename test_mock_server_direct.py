#!/usr/bin/env python3
"""
Direct Mock WebSocket Server Test - Issue #860

Test the mock WebSocket server directly to ensure it can start and handle connections.
"""

import os
import asyncio
import sys
import websockets
from shared.isolated_environment import IsolatedEnvironment

# Set environment variables for Windows Docker bypass using SSOT IsolatedEnvironment
env = IsolatedEnvironment()
env.set('DOCKER_BYPASS', 'true', 'test_mock_server_direct')
env.set('USE_MOCK_WEBSOCKET', 'true', 'test_mock_server_direct')
env.set('MOCK_WEBSOCKET_URL', 'ws://localhost:8001/ws', 'test_mock_server_direct')

async def test_mock_server():
    """Test mock WebSocket server functionality."""
    print("Direct Mock Server Test - Issue #860")
    print("====================================")

    try:
        # Import and start mock server
        from tests.mission_critical.websocket_real_test_base import MockWebSocketServer, ensure_mock_websocket_server_running

        print("Starting mock WebSocket server...")
        server_url = await ensure_mock_websocket_server_running()
        print(f"Mock server URL: {server_url}")

        # Test connection
        print("Testing connection...")

        try:
            async with websockets.connect(server_url, ping_timeout=5, close_timeout=5) as websocket:
                print("Connected successfully!")

                # Send test message
                test_message = {"type": "ping", "user_id": "test_user", "data": "hello"}
                await websocket.send(str(test_message))
                print(f"Sent: {test_message}")

                # Receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"Received: {response}")

                print("SUCCESS: Mock WebSocket server working!")

        except Exception as conn_error:
            print(f"Connection test failed: {conn_error}")
            return False

    except Exception as server_error:
        print(f"Server startup failed: {server_error}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(test_mock_server())
    if success:
        print("RESULT: Mock server test PASSED")
        sys.exit(0)
    else:
        print("RESULT: Mock server test FAILED")
        sys.exit(1)