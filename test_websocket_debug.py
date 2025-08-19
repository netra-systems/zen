"""
WebSocket Debug Test - Diagnose connection issues.
"""

import asyncio
import aiohttp
import websockets
import json

async def test_http_endpoints():
    """Test HTTP endpoints to verify system is accessible."""
    base_url = "http://localhost:54421"
    
    print("Testing HTTP endpoints...")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # Test root
            async with session.get(f"{base_url}/") as response:
                print(f"Root endpoint: {response.status}")
                
            # Test demo
            async with session.get(f"{base_url}/demo") as response:
                print(f"Demo endpoint: {response.status}")
                
            # Test docs
            async with session.get(f"{base_url}/docs") as response:
                print(f"Docs endpoint: {response.status}")
                
            # Test health if available
            async with session.get(f"{base_url}/health") as response:
                print(f"Health endpoint: {response.status}")
                
            return True
                
    except Exception as e:
        print(f"HTTP test failed: {e}")
        return False

async def test_websocket_connection():
    """Test WebSocket connection directly."""
    ws_urls = [
        "ws://localhost:54421/ws",
        "ws://localhost:54421/websocket", 
        "ws://localhost:8000/ws",
        "ws://localhost:8000/websocket"
    ]
    
    print("Testing WebSocket endpoints...")
    
    for ws_url in ws_urls:
        try:
            print(f"Trying WebSocket: {ws_url}")
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            ) as websocket:
                print(f"[SUCCESS] Connected to {ws_url}")
                
                # Send test message
                test_message = {
                    'type': 'test_message',
                    'data': 'Hello WebSocket'
                }
                
                await websocket.send(json.dumps(test_message))
                print("Test message sent")
                
                # Try to receive response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Received: {response[:100]}...")
                    return ws_url
                except asyncio.TimeoutError:
                    print("No response received (timeout)")
                    return ws_url  # Connection worked, just no response
                    
        except ConnectionRefusedError:
            print(f"Connection refused: {ws_url}")
        except Exception as e:
            print(f"WebSocket connection failed: {ws_url} - {e}")
    
    print("All WebSocket endpoints failed")
    return None

async def debug_system_status():
    """Debug system status and connectivity."""
    print("="*60)
    print("WEBSOCKET DEBUGGING - SYSTEM STATUS")
    print("="*60)
    
    # Test HTTP first
    http_ok = await test_http_endpoints()
    print(f"HTTP Status: {'OK' if http_ok else 'FAILED'}")
    
    # Test WebSocket
    working_ws_url = await test_websocket_connection()
    print(f"WebSocket Status: {'OK' if working_ws_url else 'FAILED'}")
    
    if working_ws_url:
        print(f"Working WebSocket URL: {working_ws_url}")
        return working_ws_url
    else:
        print("No working WebSocket URL found")
        return None

if __name__ == "__main__":
    result = asyncio.run(debug_system_status())
    if result:
        print(f"\n[SUCCESS] WebSocket available at: {result}")
    else:
        print("\n[FAILED] No WebSocket connection available")