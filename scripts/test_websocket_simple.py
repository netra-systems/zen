#!/usr/bin/env python3
"""
Simple WebSocket test client to verify basic connectivity.
"""
import asyncio
import websockets
import json
import sys


async def test_websocket_connection():
    """Test basic WebSocket connection to the backend."""
    uri = "ws://localhost:8000/ws"
    
    print(f"Attempting to connect to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connection established!")
            
            # Send a ping message
            ping_message = {
                "type": "ping",
                "timestamp": "2025-08-24T00:00:00Z"
            }
            
            print(f"Sending ping: {ping_message}")
            await websocket.send(json.dumps(ping_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✓ Received response: {response}")
                return True
            except asyncio.TimeoutError:
                print("✗ No response received within 5 seconds")
                return False
                
    except websockets.exceptions.ConnectionRefused as e:
        print(f"✗ Connection refused: {e}")
        return False
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"✗ Invalid status code: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


async def main():
    """Main test function."""
    print("Simple WebSocket Connectivity Test")
    print("=" * 40)
    
    success = await test_websocket_connection()
    
    if success:
        print("\n✓ WebSocket test passed!")
        sys.exit(0)
    else:
        print("\n✗ WebSocket test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())