#!/usr/bin/env python3
"""
Debug WebSocket connection to staging environment
"""
import asyncio
import json
import websockets
import os
import sys

# Add to Python path
sys.path.insert(0, os.path.abspath('.'))

from tests.e2e.staging_test_config import get_staging_config

async def test_websocket_connection():
    config = get_staging_config()
    
    print(f"🔍 Testing WebSocket connection to: {config.websocket_url}")
    print(f"🔍 Backend health endpoint: {config.backend_url}/health")
    
    # Get WebSocket headers with auth
    headers = config.get_websocket_headers()
    print(f"🔍 Headers: {list(headers.keys())}")
    
    try:
        print("📞 Attempting WebSocket connection...")
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            subprotocols=["jwt-auth"],
            close_timeout=5,
            open_timeout=10
        ) as websocket:
            print("✅ WebSocket connection established!")
            
            # Wait for welcome message
            try:
                print("⏳ Waiting for welcome message...")
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"📨 Received: {message}")
                
                # Parse the message
                try:
                    data = json.loads(message)
                    print(f"📨 Parsed data: {data}")
                except json.JSONDecodeError:
                    print(f"⚠️  Not JSON: {message}")
                
                # Try sending a ping
                print("🏓 Sending ping...")
                ping_msg = {"type": "ping"}
                await websocket.send(json.dumps(ping_msg))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"🏓 Ping response: {response}")
                
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for messages")
            except Exception as e:
                print(f"❌ Error during message exchange: {e}")
                
    except websockets.exceptions.InvalidStatus as e:
        print(f"❌ WebSocket connection failed with invalid status: {e}")
        if "403" in str(e):
            print("🔐 This appears to be an authentication issue")
        elif "401" in str(e):
            print("🔐 This appears to be an authorization issue")
    except websockets.exceptions.ConnectionClosedOK as e:
        print(f"🔚 WebSocket connection closed normally: {e}")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting WebSocket debug session...")
    asyncio.run(test_websocket_connection())