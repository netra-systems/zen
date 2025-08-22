#!/usr/bin/env python3
"""
Quick WebSocket 403 diagnosis test
"""
import asyncio
import json
import websockets
from websockets.exceptions import WebSocketException
import requests


async def test_websocket_connection():
    """Test WebSocket connection to diagnose 403 error."""
    
    # First, let's try to get a valid JWT token from auth service
    print("=" * 50)
    print("1. Testing Auth Service JWT Generation")
    print("=" * 50)
    
    try:
        # Get JWT token from auth service
        auth_response = requests.post(
            "http://localhost:8086/auth/dev-login",
            json={"user_id": "test_user", "password": "dev_mode"},
            timeout=10
        )
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            jwt_token = auth_data.get("access_token")
            print(f"SUCCESS: Auth service working - got JWT token: {jwt_token[:20]}...")
        else:
            print(f"ERROR: Auth service error: {auth_response.status_code} - {auth_response.text}")
            jwt_token = "fake_token_for_testing"
    except Exception as e:
        print(f"ERROR: Auth service connection failed: {e}")
        jwt_token = "fake_token_for_testing"
    
    # Test WebSocket endpoints
    endpoints_to_test = [
        ("ws://localhost:8000/ws", "Standard WebSocket endpoint"),
        ("ws://localhost:8000/ws/secure", "Secure WebSocket endpoint"),
        ("ws://localhost:8000/ws/test_user", "WebSocket with user ID"),
        ("ws://localhost:8000/ws/v1/test_user", "WebSocket v1 with user ID"),
    ]
    
    for ws_url, description in endpoints_to_test:
        print(f"\n{'=' * 50}")
        print(f"2. Testing {description}")
        print(f"URL: {ws_url}")
        print(f"{'=' * 50}")
        
        # Test different authentication methods
        auth_methods = [
            ("No Authentication", {}, None),
            ("Authorization Header", {"Authorization": f"Bearer {jwt_token}"}, None),
            ("Subprotocol Auth", {}, ["jwt-auth"]),
        ]
        
        for auth_name, headers, subprotocols in auth_methods:
            print(f"\n--- Testing {auth_name} ---")
            
            try:
                # Attempt WebSocket connection
                async with websockets.connect(
                    ws_url,
                    extra_headers=headers,
                    subprotocols=subprotocols,
                    timeout=5,
                    origin="http://localhost:3000"  # Add origin for CORS
                ) as websocket:
                    print(f"SUCCESS: Connection successful with {auth_name}")
                    
                    # Send a test message
                    test_message = {
                        "type": "ping",
                        "payload": {"test": True}
                    }
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2)
                        print(f"SUCCESS: Got response: {response[:100]}...")
                    except asyncio.TimeoutError:
                        print("WARNING: No response received (timeout)")
                    
            except WebSocketException as e:
                if "403" in str(e) or "Forbidden" in str(e):
                    print(f"ERROR: 403 FORBIDDEN ERROR with {auth_name}: {e}")
                else:
                    print(f"ERROR: WebSocket error with {auth_name}: {e}")
            except Exception as e:
                print(f"ERROR: Connection failed with {auth_name}: {e}")
    
    # Test backend health
    print(f"\n{'=' * 50}")
    print("3. Testing Backend Health")
    print(f"{'=' * 50}")
    
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Backend health: {health_response.status_code}")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"Backend status: {health_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"Backend health check failed: {e}")
    
    # Test WebSocket config
    try:
        config_response = requests.get("http://localhost:8000/ws/config", timeout=5)
        print(f"WebSocket config: {config_response.status_code}")
        if config_response.status_code == 200:
            config_data = config_response.json()
            print(f"WebSocket config: {json.dumps(config_data, indent=2)}")
    except Exception as e:
        print(f"WebSocket config check failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket_connection())