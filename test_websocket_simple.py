#!/usr/bin/env python3
"""
Simple WebSocket connection test to identify 403 issue
"""
import asyncio
import json
import websockets
from websockets.exceptions import WebSocketException
import requests


async def test_simple_websocket():
    """Simple WebSocket test."""
    
    # Test endpoints with different methods
    test_cases = [
        {
            "url": "ws://localhost:8000/ws",
            "description": "Standard WebSocket endpoint",
            "headers": {},
            "subprotocols": None
        },
        {
            "url": "ws://localhost:8000/ws", 
            "description": "WebSocket with fake auth header",
            "headers": {"Authorization": "Bearer fake_token_123"},
            "subprotocols": None
        },
        {
            "url": "ws://localhost:8000/ws/secure",
            "description": "Secure WebSocket endpoint",
            "headers": {},
            "subprotocols": None
        },
        {
            "url": "ws://localhost:8000/ws/secure",
            "description": "Secure WebSocket with auth header",
            "headers": {"Authorization": "Bearer fake_token_123"},
            "subprotocols": None
        }
    ]
    
    for case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Testing: {case['description']}")
        print(f"URL: {case['url']}")
        print(f"Headers: {case['headers']}")
        print(f"{'=' * 60}")
        
        try:
            # Create connection arguments
            connect_args = {
                "origin": "http://localhost:3000"  # Add origin for CORS
            }
            
            if case['headers']:
                connect_args["extra_headers"] = case['headers']
                
            if case['subprotocols']:
                connect_args["subprotocols"] = case['subprotocols']
            
            # Attempt WebSocket connection with timeout
            websocket = await asyncio.wait_for(
                websockets.connect(case['url'], **connect_args),
                timeout=5
            )
            
            try:
                print("SUCCESS: WebSocket connection established!")
                
                # Try to send a ping message
                ping_msg = json.dumps({"type": "ping", "timestamp": asyncio.get_event_loop().time()})
                await websocket.send(ping_msg)
                print("SUCCESS: Ping message sent")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    print(f"SUCCESS: Got response: {response[:200]}...")
                except asyncio.TimeoutError:
                    print("WARNING: No response received within timeout")
                    
            finally:
                await websocket.close()
                
        except WebSocketException as e:
            error_str = str(e)
            if "403" in error_str or "Forbidden" in error_str:
                print(f"ERROR: 403 FORBIDDEN - {error_str}")
            elif "401" in error_str or "Unauthorized" in error_str:
                print(f"ERROR: 401 UNAUTHORIZED - {error_str}")
            elif "404" in error_str:
                print(f"ERROR: 404 NOT FOUND - {error_str}")
            else:
                print(f"ERROR: WebSocket error - {error_str}")
                
        except Exception as e:
            print(f"ERROR: Connection failed - {e}")
            
    # Test backend health to confirm it's working
    print(f"\n{'=' * 60}")
    print("Testing Backend Health")
    print(f"{'=' * 60}")
    
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Backend health status: {health_response.status_code}")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"Backend health: {health_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"Backend health check failed: {e}")
        
    # Test WebSocket configuration endpoint
    try:
        config_response = requests.get("http://localhost:8000/ws/config", timeout=5)
        print(f"WebSocket config status: {config_response.status_code}")
        if config_response.status_code == 200:
            config_data = config_response.json()
            ws_config = config_data.get('websocket_config', {})
            print(f"Authentication required: {ws_config.get('authentication_required', 'unknown')}")
            print(f"Available endpoints: {ws_config.get('available_endpoints', [])}")
            print(f"Environment: {ws_config.get('environment', 'unknown')}")
    except Exception as e:
        print(f"WebSocket config check failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple_websocket())