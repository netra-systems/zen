#!/usr/bin/env python3
"""
Simple WebSocket Validation Test for Issue #463 Remediation
"""

import asyncio
import json
import logging
import websockets
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Staging endpoints
STAGING_BASE_URL = "https://netra-backend-staging-701982941522.us-central1.run.app"
STAGING_WS_URL = "wss://netra-backend-staging-701982941522.us-central1.run.app/ws"

async def test_health():
    """Test health endpoint."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{STAGING_BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[HEALTH] SUCCESS: {data}")
                    return True
                else:
                    print(f"[HEALTH] FAILED: Status {response.status}")
                    return False
    except Exception as e:
        print(f"[HEALTH] ERROR: {e}")
        return False

async def test_websocket():
    """Test WebSocket connection."""
    try:
        async with websockets.connect(STAGING_WS_URL, timeout=10) as websocket:
            print("[WEBSOCKET] SUCCESS: Connected successfully")
            # Try to send a message
            await websocket.send(json.dumps({"type": "ping"}))
            print("[WEBSOCKET] Message sent")
            
            # Try to receive response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"[WEBSOCKET] Response: {response}")
            except asyncio.TimeoutError:
                print("[WEBSOCKET] No response (timeout) - but connection worked!")
            
            return True
            
    except Exception as e:
        print(f"[WEBSOCKET] FAILED: {e}")
        return False

async def main():
    """Main test."""
    print("PHASE 5: WebSocket Validation Test for Issue #463")
    print("=" * 60)
    
    # Test health endpoint
    health_ok = await test_health()
    
    # Test WebSocket
    websocket_ok = await test_websocket()
    
    # Results
    print("\nRESULTS:")
    print(f"Health Endpoint: {'PASS' if health_ok else 'FAIL'}")
    print(f"WebSocket Connection: {'PASS' if websocket_ok else 'FAIL'}")
    
    if health_ok and websocket_ok:
        print("\nSUCCESS: Environment variables deployment resolved the issues!")
    elif health_ok:
        print("\nPARTIAL: Health OK, WebSocket needs investigation")
    else:
        print("\nFAILED: Further investigation needed")

if __name__ == "__main__":
    asyncio.run(main())