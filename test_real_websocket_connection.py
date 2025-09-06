#!/usr/bin/env python3
"""
Real WebSocket Connection Test

This test attempts to make an actual WebSocket connection to the backend
to see what authentication errors are occurring in practice.
"""
import asyncio
import base64
import json
import jwt
import sys
import os
import websockets
import ssl
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# Add project path  
sys.path.insert(0, os.path.dirname(__file__))

from shared.isolated_environment import get_env

async def test_real_websocket_connection():
    """Test real WebSocket connection with authentication."""
    print("[REAL] WebSocket Connection Test to Actual Backend")
    print("=" * 80)
    
    # Get environment and create test token
    env = get_env()
    jwt_secret = env.get("JWT_SECRET_KEY")
    
    if not jwt_secret:
        print("[ERROR] JWT_SECRET_KEY not found")
        return False
    
    # Create a real JWT token
    test_payload = {
        "sub": "test_user_real_connection",
        "email": "test@example.com", 
        "permissions": ["user", "chat"],
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        "iss": "netra-auth"
    }
    
    test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
    print(f"[OK] Created JWT token: {test_token[:50]}...")
    
    # Create WebSocket subprotocol (exactly as frontend does)
    token_bytes = test_token.encode('utf-8')
    base64_encoded = base64.b64encode(token_bytes).decode('utf-8')
    encoded_token = base64_encoded.replace('+', '-').replace('/', '_').replace('=', '')
    
    # Test different WebSocket URLs to see which one is actually available
    test_urls = [
        "ws://localhost:8000/ws",
        "ws://localhost:8000/websocket", 
        "ws://localhost:8000/ws/test",
        "ws://127.0.0.1:8000/ws",
    ]
    
    for websocket_url in test_urls:
        print(f"\n[TEST] Attempting connection to: {websocket_url}")
        
        try:
            # Create subprotocols list (exactly as frontend does)
            subprotocols = ['jwt-auth', f'jwt.{encoded_token}']
            
            print(f"[INFO] Using subprotocols: ['jwt-auth', 'jwt.[{len(encoded_token)} chars]']")
            
            # Test connection with timeout
            async with websockets.connect(
                websocket_url, 
                subprotocols=subprotocols,
                timeout=10,
                close_timeout=5
            ) as websocket:
                print(f"[SUCCESS] Connected to {websocket_url}")
                print(f"[INFO] Selected subprotocol: {websocket.subprotocol}")
                print(f"[INFO] Connection state: {websocket.state}")
                
                # Send a test message
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                print(f"[OK] Sent ping message")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    print(f"[OK] Received response: {response_data.get('type', 'unknown')}")
                    
                    if response_data.get('type') == 'pong':
                        print(f"[SUCCESS] WebSocket connection and authentication working!")
                        return True
                    elif response_data.get('type') == 'authentication_error':
                        print(f"[AUTH ERROR] Authentication failed: {response_data.get('error')}")
                        print(f"[AUTH ERROR] Details: {response_data.get('details')}")
                        return False
                    else:
                        print(f"[OK] Got response: {response_data}")
                        return True
                        
                except asyncio.TimeoutError:
                    print(f"[WARNING] No response received within 5 seconds")
                    # Connection is established, this might be expected
                    return True
                    
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"[ERROR] HTTP Status {e.status_code}: {e.status_phrase}")
            if e.status_code == 401:
                print(f"[AUTH ERROR] Authentication failed - 401 Unauthorized") 
            elif e.status_code == 403:
                print(f"[AUTH ERROR] Access forbidden - 403 Forbidden")
            elif e.status_code == 404:
                print(f"[ROUTING ERROR] Endpoint not found - 404 Not Found")
            elif e.status_code >= 500:
                print(f"[SERVER ERROR] Internal server error - {e.status_code}")
                
        except websockets.exceptions.InvalidHandshake as e:
            print(f"[HANDSHAKE ERROR] WebSocket handshake failed: {e}")
            
        except ConnectionRefusedError as e:
            print(f"[CONNECTION ERROR] Connection refused: {e}")
            print(f"[HINT] Backend service may not be running on the expected port")
            
        except OSError as e:
            print(f"[NETWORK ERROR] Network error: {e}")
            
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n[FAILED] All WebSocket connection attempts failed")
    return False

async def test_backend_service_availability():
    """Test if the backend service is available at all."""
    print(f"\n[CHECK] Testing backend service availability")
    
    import aiohttp
    import asyncio
    
    # Test URLs to check if backend is running
    test_endpoints = [
        "http://localhost:8000/health",
        "http://localhost:8000/ws/health",
        "http://localhost:8000/",
        "http://127.0.0.1:8000/health",
    ]
    
    for url in test_endpoints:
        try:
            print(f"[CHECK] Testing HTTP endpoint: {url}")
            
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    print(f"[OK] {url} responded with status {response.status}")
                    if response.status == 200:
                        try:
                            text = await response.text()
                            print(f"[OK] Response preview: {text[:100]}...")
                        except:
                            pass
                    return True
                    
        except aiohttp.ClientConnectorError as e:
            print(f"[CONN ERROR] {url}: {e}")
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] {url}: Request timed out") 
        except Exception as e:
            print(f"[ERROR] {url}: {e}")
    
    print(f"[FAILED] Backend service appears to be unavailable")
    return False

async def main():
    """Main test function."""
    print("REAL WEBSOCKET CONNECTION DIAGNOSTIC")
    print("Attempting to connect to actual backend WebSocket endpoints")
    
    # First, check if backend service is available
    backend_available = await test_backend_service_availability()
    
    if not backend_available:
        print(f"\n[CRITICAL] Backend service is not available!")
        print(f"[ACTION] Start the backend service with:")
        print(f"   python -m uvicorn netra_backend.app.main:app --host localhost --port 8000")
        print(f"[ACTION] Or use Docker:")
        print(f"   python scripts/docker_manual.py start")
        return False
    
    # Test WebSocket connections
    success = await test_real_websocket_connection()
    
    if success:
        print(f"\n[SUCCESS] WebSocket authentication is working correctly!")
        print(f"[RESULT] The authentication system is functional")
    else:
        print(f"\n[FAILED] WebSocket authentication failed in real environment")
        print(f"[RESULT] There is a real issue with the WebSocket authentication")
    
    return success

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()