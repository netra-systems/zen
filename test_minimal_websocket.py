#!/usr/bin/env python3
"""
Minimal WebSocket Test - Issue #860

Test just the WebSocket connection with minimal output to avoid encoding issues.
"""

import os
import asyncio
import sys

# Set environment variables
os.environ['DOCKER_BYPASS'] = 'true'
os.environ['USE_MOCK_WEBSOCKET'] = 'true'
os.environ['USE_STAGING_FALLBACK'] = 'false'
os.environ['MOCK_WEBSOCKET_URL'] = 'ws://localhost:8001/ws'

async def test_minimal():
    """Test WebSocket connection without emojis."""
    try:
        print("Starting minimal WebSocket test...")

        # Start mock server manually
        from tests.mission_critical.websocket_real_test_base import MockWebSocketServer

        server = MockWebSocketServer.get_instance()
        await server.start()

        print(f"Server started on port {server._port}")

        # Try connecting with websockets
        import websockets

        url = f"ws://localhost:{server._port}/ws"
        print(f"Connecting to: {url}")

        async with websockets.connect(url) as websocket:
            print("Connected successfully!")

            # Send simple message
            import json
            message = {"type": "ping", "user_id": "test"}
            await websocket.send(json.dumps(message))
            print("Message sent")

            # Receive response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"Response received: {response}")

        print("SUCCESS: Mock WebSocket connection working!")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_minimal())
    sys.exit(0 if success else 1)