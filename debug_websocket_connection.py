#!/usr/bin/env python3
"""
Debug WebSocket Connection Script
Test WebSocket connection to staging with detailed error handling
"""

import asyncio
import json
import time
import websockets
from tests.e2e.staging_test_config import get_staging_config

async def debug_websocket_connection():
    """Debug WebSocket connection to staging."""
    config = get_staging_config()
    
    print("=== WebSocket Connection Debug ===")
    print(f"WebSocket URL: {config.websocket_url}")
    
    # Get WebSocket headers with authentication
    ws_headers = config.get_websocket_headers()
    print(f"Headers: {list(ws_headers.keys())}")
    
    try:
        print("\n🔌 Attempting WebSocket connection...")
        async with websockets.connect(
            config.websocket_url,
            additional_headers=ws_headers,
            close_timeout=10
        ) as ws:
            print("✅ WebSocket connection established!")
            print(f"WebSocket state: {ws.state}")
            
            print("\n📡 Listening for messages...")
            messages_received = 0
            start_time = time.time()
            
            try:
                while messages_received < 5 and (time.time() - start_time) < 30:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5)
                        messages_received += 1
                        print(f"📨 Message {messages_received}: {message}")
                        
                        # Try to parse as JSON
                        try:
                            data = json.loads(message)
                            print(f"   📋 Parsed: {data}")
                        except json.JSONDecodeError:
                            print(f"   ⚠️ Non-JSON message")
                            
                        # If this is connection_established, try sending a ping
                        if messages_received == 1:
                            print("\n📤 Sending test ping...")
                            try:
                                await ws.send(json.dumps({"type": "ping", "timestamp": time.time()}))
                                print("✅ Ping sent successfully")
                            except Exception as send_error:
                                print(f"❌ Failed to send ping: {send_error}")
                                
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout waiting for message {messages_received + 1}")
                        break
                        
            except Exception as msg_error:
                print(f"❌ Error during message listening: {msg_error}")
            
            print(f"\n📊 Total messages received: {messages_received}")
            print(f"⏱️ Connection duration: {time.time() - start_time:.2f}s")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: code={e.code}, reason='{e.reason}'")
        
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed: {e.status_code}")
        
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_websocket_connection())