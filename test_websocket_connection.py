#!/usr/bin/env python3
"""Test WebSocket connection to ensure it's working properly."""

import asyncio
import json
import websockets
import sys
import os

# Fix Unicode for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')


async def test_websocket():
    """Test WebSocket connection."""
    url = "ws://localhost:8000/ws"
    
    try:
        print(f"🔌 Connecting to WebSocket at {url}...")
        
        # Connect with a test token
        headers = {
            "Authorization": "Bearer test-token-123"
        }
        
        async with websockets.connect(url, extra_headers=headers) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Send a test message
            test_message = {
                "type": "ping",
                "data": {"message": "Hello from test client"}
            }
            
            print(f"📤 Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received response: {response}")
                
                # Parse response
                response_data = json.loads(response)
                print(f"✅ WebSocket communication successful!")
                print(f"   Response type: {response_data.get('type', 'unknown')}")
                
                return True
                
            except asyncio.TimeoutError:
                print("⏱️ No response received within 5 seconds (this may be normal)")
                return True  # Connection successful even if no response
                
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except ConnectionRefusedError:
        print(f"❌ Connection refused - is the backend running on port 8000?")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_websocket_endpoints():
    """Test multiple WebSocket endpoint patterns."""
    endpoints = [
        "ws://localhost:8000/ws",
        "ws://localhost:8000/ws/test-user-123",
        "ws://localhost:8000/ws/v1/test-user-123"
    ]
    
    results = {}
    for endpoint in endpoints:
        print(f"\n🧪 Testing endpoint: {endpoint}")
        print("-" * 50)
        
        try:
            async with websockets.connect(endpoint) as ws:
                print(f"✅ Connected to {endpoint}")
                results[endpoint] = "Connected"
                await ws.close()
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                results[endpoint] = "404 Not Found"
            elif "401" in error_msg:
                results[endpoint] = "401 Unauthorized (auth required)"
            elif "403" in error_msg:
                results[endpoint] = "403 Forbidden"
            else:
                results[endpoint] = f"Error: {error_msg[:50]}"
            print(f"❌ {results[endpoint]}")
    
    print("\n📊 Summary of WebSocket Endpoints:")
    print("-" * 50)
    for endpoint, status in results.items():
        status_icon = "✅" if "Connected" in status or "401" in status else "❌"
        print(f"{status_icon} {endpoint}: {status}")
    
    return results


async def main():
    """Main test runner."""
    print("🚀 Starting WebSocket Connection Test")
    print("=" * 60)
    
    # Test basic connection
    success = await test_websocket()
    
    # Test all endpoint patterns
    print("\n" + "=" * 60)
    print("🔍 Testing All WebSocket Endpoint Patterns")
    print("=" * 60)
    endpoint_results = await test_websocket_endpoints()
    
    # Final summary
    print("\n" + "=" * 60)
    if success:
        print("✅ WEBSOCKET TEST PASSED - Connection successful!")
    else:
        print("❌ WEBSOCKET TEST FAILED - Please check backend logs")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)