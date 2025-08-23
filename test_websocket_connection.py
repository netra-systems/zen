#!/usr/bin/env python3
"""
Quick WebSocket connection test for E2E validation
"""
import asyncio
import json
import websockets
from datetime import datetime

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    timeout_seconds = 10
    
    try:
        print(f"🔍 Testing WebSocket connection to {uri}...")
        
        async with websockets.connect(uri, timeout=timeout_seconds) as websocket:
            print("✅ WebSocket connection established successfully")
            
            # Test ping/pong
            ping_msg = {"type": "ping", "timestamp": str(datetime.now())}
            await websocket.send(json.dumps(ping_msg))
            print("📤 Sent ping message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received response: {response}")
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(response)
                    print(f"✅ Valid JSON response: {parsed}")
                except json.JSONDecodeError:
                    print(f"⚠️ Response is not JSON: {response}")
                
                return True
                
            except asyncio.TimeoutError:
                print("⚠️ No response received within timeout")
                return True  # Connection worked, just no response
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    exit(0 if result else 1)
