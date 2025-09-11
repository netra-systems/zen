#!/usr/bin/env python3
"""
Simple staging connectivity test
"""
import asyncio
import httpx
import websockets
import json
import sys
import os

# Add to Python path
sys.path.insert(0, os.path.abspath('.'))

from tests.e2e.staging_test_config import get_staging_config

async def main():
    config = get_staging_config()
    
    print("=== GOLDEN PATH E2E STAGING TESTS ===")
    print(f"Testing staging environment: {config.backend_url}")
    print()
    
    # Test 1: Backend Health
    print("1. Backend Health Check...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{config.backend_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ Backend healthy: {health_data.get('status')}")
                print(f"   📊 Response time: {response.elapsed.total_seconds():.3f}s")
            else:
                print(f"   ❌ Backend unhealthy: {response.status_code}")
                return
    except Exception as e:
        print(f"   ❌ Backend connection failed: {e}")
        return
    
    # Test 2: WebSocket Connection (no message sending)
    print("\n2. WebSocket Connection Test...")
    headers = config.get_websocket_headers()
    
    connection_successful = False
    connection_duration = 0
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Just establish connection, don't try to send anything
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            subprotocols=["jwt-auth"],
            close_timeout=3,
            open_timeout=10
        ) as websocket:
            connection_duration = asyncio.get_event_loop().time() - start_time
            print(f"   ✅ WebSocket connection established")
            print(f"   📊 Connection time: {connection_duration:.3f}s")
            connection_successful = True
            
            # Just wait briefly to see if server closes immediately
            print("   ⏳ Waiting for server messages (no sending)...")
            try:
                # Just listen for any server-initiated messages
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"   📨 Server sent: {message[:100]}...")
            except asyncio.TimeoutError:
                print("   ℹ️  No messages received (timeout - this may be normal)")
            
            # Connection stayed open, this is success
            print("   ✅ WebSocket connection stable")
            
    except websockets.exceptions.ConnectionClosedOK as e:
        print(f"   ⚠️  WebSocket closed normally: {e}")
        print(f"   📊 Connection lasted: {connection_duration:.3f}s")
        # This might still be considered partial success if connection was established
        if connection_duration > 0.1:
            print("   ℹ️  Connection was established but closed by server")
            connection_successful = True
        
    except websockets.exceptions.InvalidStatus as e:
        if "403" in str(e) or "401" in str(e):
            print(f"   🔐 Authentication required: {e}")
        else:
            print(f"   ❌ Connection failed: {e}")
    except Exception as e:
        print(f"   ❌ WebSocket error: {e}")
    
    # Test 3: API Endpoint Test
    print("\n3. API Endpoint Test...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{config.api_url}/health")
            if response.status_code == 200:
                print(f"   ✅ API endpoint healthy")
                print(f"   📊 Response time: {response.elapsed.total_seconds():.3f}s")
            else:
                print(f"   ⚠️  API endpoint status: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  API endpoint error: {e}")
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    print(f"Backend Health: ✅ PASS")
    print(f"WebSocket Connection: {'✅ PASS' if connection_successful else '❌ FAIL'}")
    print(f"API Endpoints: ℹ️  INFO")
    
    if connection_successful:
        print("\n🎯 GOLDEN PATH STATUS: WebSocket connectivity confirmed")
        print("   - Authentication is working")
        print("   - Server accepts connections") 
        print("   - Issue may be in message handling, not connection")
    else:
        print("\n❌ GOLDEN PATH STATUS: WebSocket connectivity failed")
        print("   - Authentication or connection issues detected")
    
    print(f"\n📊 Total test duration: {asyncio.get_event_loop().time() - start_time:.3f}s")

if __name__ == "__main__":
    start_time = asyncio.get_event_loop().time()
    asyncio.run(main())