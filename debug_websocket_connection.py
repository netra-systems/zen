#!/usr/bin/env python3
"""
Debug WebSocket Connection Script

This script tests if we can establish basic WebSocket connections to understand 
why the concurrent connection tests are failing.
"""
import asyncio
import websockets
import json
import sys
from typing import Dict, Any

async def test_basic_connection():
    """Test basic WebSocket connection"""
    ws_url = "ws://localhost:8000/ws"
    print(f"Testing connection to {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("PASS: Basic connection established successfully")
            
            # Try to send a simple message
            test_message = {"type": "ping", "timestamp": "test"}
            await websocket.send(json.dumps(test_message))
            print("PASS: Message sent successfully")
            
            # Try to receive a response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"PASS: Response received: {response}")
            except asyncio.TimeoutError:
                print("WARN: No response received within 5 seconds")
                
    except ConnectionRefusedError:
        print("FAIL: Connection refused - server may not be running on port 8000")
        return False
    except Exception as e:
        print(f"FAIL: Connection failed: {e}")
        return False
    
    return True

async def test_multiple_connections():
    """Test multiple concurrent connections"""
    ws_url = "ws://localhost:8000/ws"
    connections = []
    
    try:
        print(f"\nTesting multiple connections to {ws_url}")
        
        # Try to establish 3 connections concurrently
        for i in range(3):
            try:
                websocket = await websockets.connect(ws_url)
                connections.append(websocket)
                print(f"PASS: Connection {i+1} established")
            except Exception as e:
                print(f"FAIL: Connection {i+1} failed: {e}")
                break
        
        print(f"PASS: Successfully established {len(connections)} concurrent connections")
        
        # Clean up connections
        for i, websocket in enumerate(connections):
            await websocket.close()
            print(f"PASS: Connection {i+1} closed")
            
    except Exception as e:
        print(f"FAIL: Multiple connection test failed: {e}")
        return False
    
    return len(connections) > 0

async def test_with_auth_headers():
    """Test connection with authentication headers"""
    ws_url = "ws://localhost:8000/ws"
    
    # Mock JWT token for testing
    mock_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJleHAiOjk5OTk5OTk5OTl9.test"
    headers = {"Authorization": mock_token}
    
    try:
        print(f"\nTesting connection with auth headers to {ws_url}")
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            print("PASS: Authenticated connection established")
            return True
    except Exception as e:
        print(f"FAIL: Authenticated connection failed: {e}")
        return False

async def main():
    """Main test function"""
    print("Debugging WebSocket Connection Issues")
    print("=" * 50)
    
    # Test 1: Basic connection
    basic_success = await test_basic_connection()
    
    if not basic_success:
        print("\nFAIL: Basic connection failed. Server may not be running.")
        print("Please ensure the server is running on port 8000")
        sys.exit(1)
    
    # Test 2: Multiple connections
    multi_success = await test_multiple_connections()
    
    # Test 3: Authenticated connection
    auth_success = await test_with_auth_headers()
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"   Basic Connection: {'PASS' if basic_success else 'FAIL'}")
    print(f"   Multiple Connections: {'PASS' if multi_success else 'FAIL'}")
    print(f"   Authenticated Connection: {'PASS' if auth_success else 'FAIL'}")
    
    if basic_success and multi_success:
        print("\nWebSocket connections appear to be working!")
        print("The issue may be in the test implementation or authentication.")
    else:
        print("\nWebSocket connection issues detected.")
        print("Check server configuration and ensure it's running properly.")

if __name__ == "__main__":
    asyncio.run(main())