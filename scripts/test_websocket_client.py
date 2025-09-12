#!/usr/bin/env python3
"""
Simple WebSocket client to test connectivity to the WebSocket server.
"""
import asyncio
import json
import websockets
import sys
import time

async def test_websocket_connection():
    """Test WebSocket connection to the server."""
    uri = "ws://127.0.0.1:8080/ws"
    print(f"Testing WebSocket connection to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] WebSocket connection established successfully!")
            
            # Receive welcome message
            welcome_msg = await websocket.recv()
            print(f"[RECV] Received welcome message: {welcome_msg}")
            
            # Send a test message
            test_message = "Hello from WebSocket client!"
            print(f"[SEND] Sending test message: {test_message}")
            await websocket.send(test_message)
            
            # Receive echo response
            response = await websocket.recv()
            print(f"[RECV] Received response: {response}")
            
            # Parse the response
            try:
                response_data = json.loads(response)
                if response_data.get("type") == "echo" and response_data.get("data", {}).get("received") == test_message:
                    print("[SUCCESS] Echo test successful - WebSocket is working correctly!")
                    return True
                else:
                    print("[ERROR] Echo test failed - unexpected response format")
                    return False
            except json.JSONDecodeError:
                print("[ERROR] Failed to parse JSON response")
                return False
                
    except ConnectionRefusedError:
        print("[ERROR] Connection refused - server is not running or not accessible")
        return False
    except Exception as e:
        print(f"[ERROR] WebSocket test failed: {e}")
        return False

async def main():
    """Run the WebSocket connection test."""
    print("=" * 60)
    print("WebSocket Connection Test")
    print("=" * 60)
    
    # Test basic connectivity
    success = await test_websocket_connection()
    
    print("=" * 60)
    if success:
        print("[SUCCESS] WebSocket test completed successfully!")
        print("   - Connection established")
        print("   - Message exchange working")
        print("   - Server responding correctly")
        sys.exit(0)
    else:
        print("[FAILED] WebSocket test failed!")
        print("   - Check if server is running on ws://127.0.0.1:8080/ws")
        print("   - Check network connectivity")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())