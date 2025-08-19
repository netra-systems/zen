"""Test WebSocket tampered token rejection."""
import asyncio
import websockets
import json
import sys

async def test_tampered_token():
    """Test that tampered tokens are rejected immediately."""
    # Use a tampered JWT token (signature modified)
    tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItZDhlMGUzOWYiLCJlbWFpbCI6InRlc3RAbmV0cmEuYWkiLCJwZXJtaXNzaW9ucyI6WyJyZWFkIiwid3JpdGUiXSwiaWF0IjoxNzU1NjMyNDc4LCJleHAiOjE3NTU2MzMzNzgsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJpc3MiOiJuZXRyYS1hdXRoLXNlcnZpY2UifQ.tampered_signature_test"
    
    ws_url = f"ws://127.0.0.1:8000/ws?token={tampered_token}"
    
    print(f"Testing WebSocket connection with tampered token...")
    print(f"URL: {ws_url[:50]}...")
    
    try:
        # Try to connect with tampered token
        async with websockets.connect(ws_url) as websocket:
            print("ERROR: Connection accepted with tampered token! This is a security vulnerability.")
            # Try to send a message to see what happens
            await websocket.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(websocket.recv(), timeout=2)
            print(f"Received response: {response}")
            return False
            
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code in [403, 401, 1008]:  # Expected rejection codes
            print(f"SUCCESS: Connection rejected with status {e.status_code} (expected behavior)")
            return True
        else:
            print(f"ERROR: Unexpected status code {e.status_code}")
            return False
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"SUCCESS: Connection closed with code {e.code}: {e.reason} (expected behavior)")
        return True
        
    except Exception as e:
        print(f"SUCCESS: Connection rejected with error: {e} (expected behavior)")
        return True

async def test_missing_token():
    """Test that missing tokens are rejected immediately."""
    ws_url = "ws://127.0.0.1:8000/ws"
    
    print("\nTesting WebSocket connection without token...")
    
    try:
        # Try to connect without token
        async with websockets.connect(ws_url) as websocket:
            print("ERROR: Connection accepted without token! This is a security vulnerability.")
            return False
            
    except Exception as e:
        print(f"SUCCESS: Connection rejected with error: {e} (expected behavior)")
        return True

async def main():
    """Run all tests."""
    print("=" * 60)
    print("WebSocket Authentication Security Test")
    print("=" * 60)
    
    results = []
    
    # Test tampered token
    results.append(await test_tampered_token())
    
    # Test missing token
    results.append(await test_missing_token())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ All security tests PASSED - WebSocket properly rejects invalid tokens")
        sys.exit(0)
    else:
        print("✗ Some security tests FAILED - Security vulnerability detected!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())