#!/usr/bin/env python3
"""
WebSocket Connection Test for Phase 3 Validation
Tests WebSocket connection establishment to deployed backend.
"""

import asyncio
import websockets
import ssl
import json
from urllib.parse import urlparse

async def test_websocket_connection(uri, timeout=10):
    """Test WebSocket connection establishment."""
    print(f"Testing WebSocket connection to: {uri}")
    
    try:
        # Parse URI to check if it's wss://
        parsed = urlparse(uri)
        if parsed.scheme == 'wss':
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        else:
            ssl_context = None
            
        print(f"Attempting connection with timeout={timeout}s...")
        
        async with websockets.connect(uri, ssl=ssl_context) as websocket:
            print("✅ WebSocket connection established successfully!")
            print(f"Connection state: {websocket.state}")
            
            # Try to send a ping
            try:
                await websocket.ping()
                print("✅ Ping successful")
            except Exception as ping_error:
                print(f"⚠️  Ping failed: {ping_error}")
            
            # Try to send a test message
            try:
                test_message = json.dumps({"type": "test", "message": "Phase 3 validation"})
                await websocket.send(test_message)
                print("✅ Test message sent successfully")
                
                # Try to receive response (with short timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    print(f"✅ Received response: {response}")
                except asyncio.TimeoutError:
                    print("⏰ No response received (timeout - this may be normal)")
                    
            except Exception as msg_error:
                print(f"⚠️  Message send failed: {msg_error}")
                
    except OSError as e:
        print(f"❌ Network error: {e}")
        return False, f"Network error: {e}"
        
    except Exception as e:
        error_str = str(e).lower()
        if "status" in error_str and hasattr(e, 'status_code'):
            print(f"❌ Invalid status code: {e.status_code}")
            return False, f"Status {e.status_code}"
        elif "uri" in error_str:
            print(f"❌ Invalid URI: {e}")
            return False, "Invalid URI"
        elif "connection" in error_str and "closed" in error_str:
            print(f"❌ Connection closed: {e}")
            return False, f"Connection closed: {e}"
        else:
            print(f"❌ Unexpected error: {type(e).__name__}: {e}")
            return False, f"Error: {type(e).__name__}"
        
    return True, "Success"

async def main():
    print("=== PHASE 3: WEBSOCKET CONNECTION VALIDATION ===\n")
    
    base_url = "netra-backend-staging-pnovr5vsba-uc.a.run.app"
    endpoints = [
        f"wss://{base_url}/websocket",
        f"wss://{base_url}/ws/test", 
        f"wss://{base_url}/ws/health"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"\n--- Testing {endpoint} ---")
        success, message = await test_websocket_connection(endpoint)
        results[endpoint] = {"success": success, "message": message}
        print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'} - {message}\n")
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n=== SUMMARY ===")
    for endpoint, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{status}: {endpoint}")
        print(f"         {result['message']}")
    
    successful_connections = sum(1 for r in results.values() if r["success"])
    total_tests = len(results)
    print(f"\nOverall: {successful_connections}/{total_tests} connections successful")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())