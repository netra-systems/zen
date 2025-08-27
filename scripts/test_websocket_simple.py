#!/usr/bin/env python3
"""
Simple WebSocket Connection Test

Tests basic WebSocket connectivity to validate CORS configuration.
"""

import asyncio
import json
import sys
import time
import traceback
import websockets


async def test_websocket_connection(url: str = "ws://localhost:8000/ws", origin: str = None):
    """Test a simple WebSocket connection.
    
    Args:
        url: WebSocket URL to test
        origin: Origin header to send
    """
    print(f"[TEST] Testing WebSocket connection to: {url}")
    print(f"[TEST] Origin: {origin or 'None'}")
    
    try:
        # Connect to WebSocket (use simpler API for websockets 15.x)
        start_time = time.time()
        
        # Build headers list
        headers = {}
        if origin:
            headers["Origin"] = origin
        
        async with websockets.connect(url, extra_headers=headers) as websocket:
            connection_time = time.time() - start_time
            print(f"[OK] Connected in {connection_time:.3f}s")
            
            # Send a test message
            test_message = {
                "type": "ping",
                "data": {"test": True, "timestamp": time.time()}
            }
            
            await websocket.send(json.dumps(test_message))
            print("[SEND] Sent test message")
            
            # Try to receive a response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"[RECV] Received: {response[:100]}...")
                return True
            except asyncio.TimeoutError:
                print("[TIMEOUT] No response (but connection successful)")
                return True  # Connection is what we care about
                
    except Exception as e:
        print(f"[ERROR] Connection failed: {type(e).__name__}: {str(e)}")
        return False


async def main():
    """Main test runner."""
    print("[MAIN] Simple WebSocket Connection Test")
    print("=" * 50)
    
    # Test scenarios
    tests = [
        ("ws://localhost:8000/ws", "http://localhost:3000"),
        ("ws://localhost:8000/ws", "http://frontend:3000"),  
        ("ws://localhost:8000/ws", None),  # No origin
    ]
    
    results = []
    
    for url, origin in tests:
        success = await test_websocket_connection(url, origin)
        results.append(success)
        print()  # Add space between tests
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    successful = sum(results)
    total = len(results)
    
    print("=" * 50)
    print("[SUMMARY] Test Results")
    print(f"Successful: {successful}/{total}")
    print(f"Success Rate: {successful/total*100:.1f}%")
    
    if successful == total:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"[FAIL] {total-successful} tests failed")
        return 1


if __name__ == "__main__":
    try:
        import websockets
    except ImportError:
        print("[ERROR] websockets library not found. Install with: pip install websockets")
        sys.exit(1)
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)