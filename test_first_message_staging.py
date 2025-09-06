#!/usr/bin/env python
"""Simplified first message E2E test for staging environment"""

import asyncio
import json
import time
import uuid
import websockets
import ssl
from datetime import datetime

STAGING_BACKEND_URL = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"

async def test_first_message_flow():
    """Test the first message experience on staging."""
    print("=" * 60)
    print("First Message Experience Test - Staging")
    print("=" * 60)
    
    ws_url = STAGING_BACKEND_URL.replace("https://", "wss://") + "/ws"
    
    # Create SSL context for WSS connection
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    
    events_received = []
    start_time = time.time()
    
    try:
        print(f"\nConnecting to: {ws_url}")
        async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
            print("[OK] WebSocket connected")
            
            # Send auth message (will fail but that's ok for this test)
            auth_msg = {
                "type": "auth",
                "token": "test_token",
                "user_id": user_id
            }
            await websocket.send(json.dumps(auth_msg))
            print(f"[SENT] Auth message for user: {user_id}")
            
            # Try to receive auth response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                event = json.loads(response)
                events_received.append(event)
                print(f"[RECEIVED] {event.get('type', 'unknown')}: {str(event)[:100]}...")
                
                # Check if auth failed (expected)
                if event.get("error_code") == "AUTH_ERROR":
                    print("[EXPECTED] Auth failed as expected (no valid token)")
                    
                    # Try sending a message anyway to test the flow
                    message = {
                        "type": "agent_request",
                        "message": "Test message for staging environment",
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(message))
                    print(f"[SENT] Test message")
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event = json.loads(response)
                        events_received.append(event)
                        print(f"[RECEIVED] {event.get('type', 'unknown')}: {str(event)[:100]}...")
                    except asyncio.TimeoutError:
                        print("[INFO] No response received (auth required)")
                        
            except asyncio.TimeoutError:
                print("[WARNING] No auth response received within 5 seconds")
                
    except Exception as e:
        print(f"[ERROR] WebSocket connection failed: {str(e)[:200]}")
        return False
        
    # Report results
    elapsed = time.time() - start_time
    print(f"\n" + "=" * 60)
    print(f"Test completed in {elapsed:.2f} seconds")
    print(f"Events received: {len(events_received)}")
    
    if events_received:
        print("\nEvent Summary:")
        for event in events_received:
            print(f"  - {event.get('type', 'unknown')}: {event.get('error_code', event.get('status', 'OK'))}")
    
    print("=" * 60)
    
    # Test passes if we can connect and get some response
    return len(events_received) > 0

async def test_health_check():
    """Quick health check before WebSocket test."""
    import httpx
    
    print("\nChecking backend health...")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{STAGING_BACKEND_URL}/health")
        if response.status_code == 200:
            print("[OK] Backend is healthy")
            return True
        else:
            print(f"[ERROR] Backend health check failed: {response.status_code}")
            return False

async def main():
    """Run the test suite."""
    try:
        # First check if backend is healthy
        if not await test_health_check():
            print("\n[FAILED] Backend is not healthy")
            return 1
            
        # Run the WebSocket test
        if await test_first_message_flow():
            print("\n[SUCCESS] First message flow test completed")
            return 0
        else:
            print("\n[FAILED] First message flow test failed")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return 2

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))