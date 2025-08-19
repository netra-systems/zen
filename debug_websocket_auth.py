#!/usr/bin/env python3
"""Debug WebSocket authentication with JWT token"""

import asyncio
import websockets
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tests.unified.jwt_token_helpers import JWTTestHelper

async def test_websocket_auth():
    """Test WebSocket authentication with valid JWT token"""
    print("Testing WebSocket authentication...")
    
    # Create JWT helper and token
    jwt_helper = JWTTestHelper()
    payload = jwt_helper.create_valid_payload()
    token = jwt_helper.create_token(payload)
    
    # Create authenticated URL
    ws_url = f"ws://localhost:8000/ws?token={token}"
    print(f"Connecting to: {ws_url}")
    
    try:
        # Try to connect with the token in URL
        async with websockets.connect(ws_url) as websocket:
            print("SUCCESS: Connected to WebSocket with authentication!")
            
            # Try sending a ping message
            ping_message = '{"type": "ping", "timestamp": "test"}'
            await websocket.send(ping_message)
            print("SUCCESS: Sent ping message")
            
            # Try to receive a response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"SUCCESS: Received response: {response}")
            except asyncio.TimeoutError:
                print("INFO: No response received within 5 seconds (normal for ping)")
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"ERROR: Connection closed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_websocket_auth())
        if success:
            print("\nSUCCESS: WebSocket authentication working!")
        else:
            print("\nFAILED: WebSocket authentication not working")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        sys.exit(1)