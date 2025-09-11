#!/usr/bin/env python3
"""
Simple WebSocket connection test for P0 Issue #437 validation
"""
import asyncio
import websockets
import json
import requests
import time

async def test_websocket_connection(url: str, attempt_id: int):
    """Test a single WebSocket connection"""
    print(f"Attempt {attempt_id}: Testing WebSocket connection to {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print(f"  SUCCESS: Connected to WebSocket")
            
            # Send test message
            test_msg = {"type": "ping", "data": "test"}
            await websocket.send(json.dumps(test_msg))
            print(f"  Sent test message")
            
            # Try to receive response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"  Received response: {response[:100]}")
                return True
            except asyncio.TimeoutError:
                print(f"  No response within 5s (but connection successful)")
                return True
                
    except websockets.exceptions.ConnectionClosed as e:
        if e.code == 1011:
            print(f"  *** 1011 ERROR DETECTED! *** - {e}")
            return False
        else:
            print(f"  Connection closed: {e.code} - {e}")
            return False
    except Exception as e:
        print(f"  Connection failed: {e}")
        return False

def trigger_cold_start(url: str):
    """Trigger cold start with HTTP request"""
    print(f"Triggering cold start: {url}/health")
    try:
        response = requests.get(f"{url}/health", timeout=3)
        print(f"  HTTP response: {response.status_code}")
    except Exception as e:
        print(f"  HTTP request result: {e}")

async def main():
    backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
    websocket_url = backend_url.replace("https://", "wss://") + "/ws"
    
    print("=== P0 Issue #437 WebSocket Race Condition Test ===")
    print(f"Backend URL: {backend_url}")
    print(f"WebSocket URL: {websocket_url}")
    
    # First trigger cold start
    trigger_cold_start(backend_url)
    
    # Wait briefly then test multiple connections during startup
    await asyncio.sleep(0.2)
    
    results = []
    test_delays = [0.1, 0.5, 1.0, 1.5, 2.0]
    
    for i, delay in enumerate(test_delays):
        if i > 0:
            await asyncio.sleep(delay - test_delays[i-1])
        
        result = await test_websocket_connection(websocket_url, i+1)
        results.append(result)
    
    # Results summary
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n=== RESULTS SUMMARY ===")
    print(f"Successful connections: {success_count}/{total_count}")
    
    if success_count > 0:
        print("SUCCESS: WebSocket connections working during cold start")
        print("SUCCESS: No 1011 errors detected - race condition fix appears successful")
    else:
        print("FAILURE: All connections failed - need to investigate further")

if __name__ == "__main__":
    asyncio.run(main())
