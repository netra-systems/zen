"""Test WebSocket authentication fix"""
import asyncio
import websockets
import json
import jwt
from datetime import datetime, timedelta

def create_test_token():
    """Create a test JWT token"""
    secret_key = "development-secret-key-not-for-production"
    payload = {
        "sub": "b4a13f8c-3c7f-42fb-9826-843c98a0990c",  # Test user ID
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

async def test_websocket_connection():
    """Test WebSocket connection with authentication"""
    token = create_test_token()
    uri = f"ws://localhost:8001/ws?token={token}"
    
    print(f"Connecting to WebSocket at {uri[:50]}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] Connected successfully!")
            
            # Send a test message
            test_message = json.dumps({"type": "ping", "message": "test"})
            await websocket.send(test_message)
            print(f"[OK] Sent test message: {test_message}")
            
            # Wait for any response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"[OK] Received response: {response}")
            except asyncio.TimeoutError:
                print("[WARNING] No response received (timeout)")
            
            # Close the connection
            await websocket.close()
            print("[OK] Connection closed successfully")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"[ERROR] WebSocket error: {e}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    print("Testing WebSocket authentication fix...")
    asyncio.run(test_websocket_connection())
    print("\nTest complete!")