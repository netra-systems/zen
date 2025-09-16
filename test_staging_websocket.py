#!/usr/bin/env python3
"""
WebSocket Staging Test Script for Issue #1032

This script tests if the Redis authentication timeout issue exists in staging.
Expected behavior:
- If Redis auth is broken: Connection hangs for 5+ seconds
- If Redis auth is working: Quick connection (<1 second)
"""
import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_websocket():
    uri = "wss://api-staging.netrasystems.ai/ws"
    
    print(f"[{datetime.now()}] Connecting to staging WebSocket: {uri}")
    start_time = time.time()
    
    try:
        # Try to connect with timeout
        async with websockets.connect(uri, subprotocols=["websocket"]) as websocket:
            connect_time = time.time() - start_time
            print(f"[{datetime.now()}] ✅ Connected in {connect_time:.2f} seconds")
            
            # Send a test message
            test_message = json.dumps({
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            })
            
            await websocket.send(test_message)
            print(f"[{datetime.now()}] Sent test message")
            
            # Wait for response with timeout
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            response_time = time.time() - start_time
            print(f"[{datetime.now()}] ✅ Received response in {response_time:.2f} seconds")
            print(f"Response: {response[:100]}...")
            
            # Check if response time is acceptable
            if response_time > 5:
                print(f"⚠️ WARNING: Response took {response_time:.2f}s (>5s threshold)")
                print("This indicates the Redis timeout issue may still be present")
                return False
            else:
                print(f"✅ Response time acceptable ({response_time:.2f}s < 5s)")
                return True
                
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"[{datetime.now()}] ❌ WebSocket timeout after {elapsed:.2f} seconds")
        print("This confirms the Redis authentication issue exists in staging")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{datetime.now()}] ❌ WebSocket error after {elapsed:.2f} seconds: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    if result:
        print("\n✅ WebSocket working properly in staging - fix may already be deployed")
    else:
        print("\n❌ WebSocket has timeout issues in staging - deployment needed")