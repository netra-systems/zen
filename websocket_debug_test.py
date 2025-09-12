#!/usr/bin/env python3
"""
Debug test to reproduce WebSocket HTTP 500 errors in staging environment
"""
import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_websocket_connection():
    """Test WebSocket connection to staging and capture exact error details"""
    
    staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"
    
    print(f"[DEBUG] Attempting WebSocket connection to: {staging_websocket_url}")
    print(f"[DEBUG] Time: {datetime.now().isoformat()}")
    
    # Test headers - basic connection without authentication first
    headers = {
        "User-Agent": "WebSocket-Debug-Test/1.0",
        "Origin": "https://app.staging.netrasystems.ai"
    }
    
    try:
        print(f"[INFO] Connecting without authentication...")
        async with websockets.connect(
            staging_websocket_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10
        ) as ws:
            print(f"[SUCCESS] WebSocket connected successfully!")
            print(f"[INFO] Connection state: {ws.state}")
            
            # Send a simple ping
            ping_message = {"type": "ping", "timestamp": time.time()}
            await ws.send(json.dumps(ping_message))
            print(f"[INFO] Sent ping message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"[SUCCESS] Received response: {response}")
            except asyncio.TimeoutError:
                print(f"[INFO] No response within timeout (may be expected)")
            
    except websockets.exceptions.InvalidStatus as e:
        print(f"[ERROR] WebSocket InvalidStatus error: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        
        # Extract detailed error information
        status_code = None
        if hasattr(e, 'response'):
            response = e.response
            print(f"[DEBUG] Response object type: {type(response)}")
            print(f"[DEBUG] Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            
            # Try different ways to get status
            if hasattr(response, 'status_code'):
                status_code = response.status_code
                print(f"[DEBUG] Response status_code: {response.status_code}")
            elif hasattr(response, 'status'):
                status_code = response.status
                print(f"[DEBUG] Response status: {response.status}")
            
            if hasattr(response, 'headers'):
                print(f"[DEBUG] Response headers: {dict(response.headers)}")
            if hasattr(response, 'text'):
                print(f"[DEBUG] Response text: {response.text}")
        
        # Extract from exception message if needed
        if status_code is None:
            import re
            match = re.search(r'HTTP (\d+)', str(e))
            if match:
                status_code = int(match.group(1))
                print(f"[DEBUG] Extracted status code from message: {status_code}")
        
        if status_code == 500:
            print(f"[CRITICAL] HTTP 500 Server Error - This is the issue we need to fix!")
            print(f"[ANALYSIS] Server is rejecting WebSocket upgrade with internal server error")
            return "HTTP_500_SERVER_ERROR"
        elif status_code == 403:
            print(f"[INFO] HTTP 403 Forbidden - Authentication issue")
            return "HTTP_403_FORBIDDEN"
        elif status_code == 404:
            print(f"[ERROR] HTTP 404 Not Found - Route not found")
            return "HTTP_404_NOT_FOUND"
        else:
            print(f"[ERROR] Unexpected status code: {status_code}")
            return f"HTTP_{status_code}_ERROR"
            
    except Exception as e:
        print(f"[ERROR] Unexpected WebSocket error: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        return f"EXCEPTION_{type(e).__name__}"

async def test_with_auth():
    """Test WebSocket connection with authentication headers"""
    
    staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"
    
    print(f"\n[DEBUG] Testing with authentication headers...")
    
    # Create a test JWT token (basic structure for testing)
    import jwt
    import uuid
    from datetime import datetime, timedelta, timezone
    
    test_payload = {
        "sub": f"test-user-{uuid.uuid4().hex[:8]}",
        "email": "test@netrasystems.ai",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        "iss": "netra-auth-service"
    }
    
    # Use staging JWT secret
    staging_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
    test_token = jwt.encode(test_payload, staging_secret, algorithm="HS256")
    
    headers = {
        "User-Agent": "WebSocket-Debug-Test/1.0",
        "Origin": "https://app.staging.netrasystems.ai",
        "Authorization": f"Bearer {test_token}",
        "sec-websocket-protocol": f"jwt.{test_token[:20]}..."
    }
    
    try:
        print(f"[INFO] Connecting with authentication...")
        async with websockets.connect(
            staging_websocket_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10
        ) as ws:
            print(f"[SUCCESS] WebSocket authenticated connection successful!")
            
            # Send a test message
            test_message = {
                "type": "message", 
                "content": "Debug test message",
                "timestamp": time.time()
            }
            await ws.send(json.dumps(test_message))
            print(f"[INFO] Sent test message")
            
            # Wait for any responses
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                print(f"[SUCCESS] Received response: {response}")
                return "AUTH_SUCCESS"
            except asyncio.TimeoutError:
                print(f"[INFO] No response within timeout")
                return "AUTH_SUCCESS_NO_RESPONSE"
                
    except websockets.exceptions.InvalidStatus as e:
        print(f"[ERROR] WebSocket auth error: {e}")
        status_code = getattr(e.response, 'status', None) if hasattr(e, 'response') else getattr(e, 'status', None)
        
        if status_code == 500:
            print(f"[CRITICAL] HTTP 500 Server Error WITH AUTH - Authentication passed but server failed!")
            return "AUTH_HTTP_500_SERVER_ERROR"
        elif status_code == 403:
            print(f"[INFO] HTTP 403 Forbidden - Authentication rejected")
            return "AUTH_HTTP_403_FORBIDDEN"
        elif status_code == 401:
            print(f"[INFO] HTTP 401 Unauthorized - Authentication failed")
            return "AUTH_HTTP_401_UNAUTHORIZED"
        else:
            return f"AUTH_HTTP_{status_code}_ERROR"
    
    except Exception as e:
        print(f"[ERROR] Unexpected auth WebSocket error: {e}")
        return f"AUTH_EXCEPTION_{type(e).__name__}"

async def main():
    """Run WebSocket debug tests"""
    print("=" * 80)
    print("WebSocket Debug Test for Staging Environment")
    print("=" * 80)
    
    # Test without auth
    result1 = await test_websocket_connection()
    
    # Test with auth
    result2 = await test_with_auth()
    
    print("\n" + "=" * 80)
    print("SUMMARY OF RESULTS")
    print("=" * 80)
    print(f"No Auth Test: {result1}")
    print(f"With Auth Test: {result2}")
    
    # Analysis
    if "HTTP_500" in result1 or "HTTP_500" in result2:
        print("\n[CRITICAL FINDING] HTTP 500 Server Error Confirmed!")
        print("This indicates the WebSocket endpoint is accepting connections")
        print("but failing during the handshake or initialization process.")
        print("\nNext steps:")
        print("1. Check server-side WebSocket handler for exceptions")
        print("2. Verify application state and dependencies")
        print("3. Check WebSocket middleware configuration")
        print("4. Review GCP Cloud Run WebSocket support")
    
    elif "HTTP_403" in result1 and "AUTH_SUCCESS" in result2:
        print("\n[SUCCESS] WebSocket authentication working correctly!")
        print("The issue may have been resolved.")
    
    elif "HTTP_403" in result1 and "HTTP_403" in result2:
        print("\n[INFO] Authentication is being enforced correctly.")
        print("May need proper JWT token for staging environment.")
        
    else:
        print(f"\n[ANALYSIS] Mixed results - need further investigation.")

if __name__ == "__main__":
    asyncio.run(main())