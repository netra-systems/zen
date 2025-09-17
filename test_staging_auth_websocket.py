#!/usr/bin/env python3
"""
Authenticated WebSocket Staging Test Script for Issue #1032

This script tests WebSocket with a mock JWT token to simulate authenticated connection.
This is more realistic as the Redis timeout typically occurs during user context loading.
"""
import asyncio
import websockets
import json
import time
from datetime import datetime

# Mock JWT token for testing (this won't be valid but will trigger auth flow)
MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYzMDAwMDAwMH0.test"

async def test_websocket_with_auth():
    uri = "wss://api.staging.netrasystems.ai/ws"
    
    print(f"[{datetime.now()}] Testing WebSocket with auth token...")
    print(f"[{datetime.now()}] Connecting to staging WebSocket: {uri}")
    start_time = time.time()
    
    try:
        # Try to connect with auth headers
        headers = {
            "Authorization": f"Bearer {MOCK_TOKEN}",
            "Origin": "https://staging.netrasystems.ai"
        }
        
        async with websockets.connect(
            uri, 
            subprotocols=["websocket"],
            extra_headers=headers
        ) as websocket:
            connect_time = time.time() - start_time
            print(f"[{datetime.now()}] ✅ Connected in {connect_time:.2f} seconds")
            
            # Send a test message that might trigger Redis lookup
            test_message = json.dumps({
                "type": "user_message",
                "content": "test message",
                "timestamp": datetime.now().isoformat()
            })
            
            await websocket.send(test_message)
            print(f"[{datetime.now()}] Sent authenticated test message")
            
            # Wait for response with timeout
            response = await asyncio.wait_for(websocket.recv(), timeout=15)
            response_time = time.time() - start_time
            print(f"[{datetime.now()}] ✅ Received response in {response_time:.2f} seconds")
            print(f"Response: {response[:200]}...")
            
            # Check if response time indicates Redis timeout issue
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
    except websockets.exceptions.ConnectionClosedError as e:
        elapsed = time.time() - start_time
        print(f"[{datetime.now()}] 🔒 Connection closed (auth rejected) after {elapsed:.2f} seconds: {e}")
        if elapsed > 5:
            print("❌ Slow rejection suggests Redis timeout issue")
            return False
        else:
            print("✅ Fast rejection suggests Redis is working (auth just failed)")
            return True
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{datetime.now()}] ❌ WebSocket error after {elapsed:.2f} seconds: {e}")
        return False

async def test_basic_connection():
    """Test basic connection without auth first"""
    uri = "wss://api.staging.netrasystems.ai/ws"
    
    print(f"[{datetime.now()}] Testing basic WebSocket connection...")
    print(f"[{datetime.now()}] Connecting to: {uri}")
    start_time = time.time()
    
    try:
        async with websockets.connect(uri, subprotocols=["websocket"]) as websocket:
            connect_time = time.time() - start_time
            print(f"[{datetime.now()}] ✅ Basic connection in {connect_time:.2f} seconds")
            return True
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{datetime.now()}] ❌ Basic connection failed after {elapsed:.2f} seconds: {e}")
        return False

async def run_comprehensive_test():
    print("=" * 60)
    print("COMPREHENSIVE WEBSOCKET STAGING TEST")
    print("=" * 60)
    
    # Test 1: Basic connection
    print("\n1. Testing basic connection...")
    basic_result = await test_basic_connection()
    
    # Test 2: Authenticated connection
    print("\n2. Testing authenticated connection...")
    auth_result = await test_websocket_with_auth()
    
    # Results
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"Basic Connection: {'✅ PASS' if basic_result else '❌ FAIL'}")
    print(f"Auth Connection: {'✅ PASS' if auth_result else '❌ FAIL'}")
    
    if basic_result and auth_result:
        print("\n✅ Overall Result: WebSocket working properly in staging")
        print("   Fix may already be deployed OR issue may be environment-specific")
    elif basic_result and not auth_result:
        print("\n⚠️ Overall Result: Basic connection works, auth flow has Redis timeout")
        print("   This suggests the Redis authentication issue exists in staging")
        print("   Deployment of the Redis auth fix is needed")
    else:
        print("\n❌ Overall Result: WebSocket infrastructure issues in staging")
        print("   May need broader infrastructure debugging")
    
    return basic_result and auth_result

if __name__ == "__main__":
    result = asyncio.run(run_comprehensive_test())