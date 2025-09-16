#!/usr/bin/env python3
"""WebSocket endpoint health check"""

import asyncio
import websockets
import json
import time

async def test_websocket_endpoint(uri, timeout=10):
    """Test WebSocket connection"""
    try:
        start_time = time.time()
        async with websockets.connect(uri) as websocket:
            elapsed = time.time() - start_time

            # Send a test message
            test_message = json.dumps({"type": "test", "message": "health_check"})
            await websocket.send(test_message)

            # Try to receive a response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                return {
                    "success": True,
                    "connection_time": round(elapsed, 2),
                    "response": response[:200] if response else None
                }
            except asyncio.TimeoutError:
                return {
                    "success": True,  # Connection worked even if no response
                    "connection_time": round(elapsed, 2),
                    "response": "NO_RESPONSE_TIMEOUT"
                }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    print("=== WEBSOCKET ENDPOINT HEALTH CHECK ===")

    # Test WebSocket endpoint based on current configuration
    websocket_url = "wss://api-staging.netrasystems.ai/ws"

    print(f"Testing WebSocket: {websocket_url}")

    result = await test_websocket_endpoint(websocket_url)

    if result["success"]:
        print(f"  [OK] WebSocket connected in {result['connection_time']}s")
        if result.get("response"):
            print(f"  Response: {result['response']}")
    else:
        print(f"  [FAIL] {result['error']}")

    return result["success"]

if __name__ == "__main__":
    success = asyncio.run(main())