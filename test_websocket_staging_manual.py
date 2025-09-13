#!/usr/bin/env python3
"""
Manual test to check staging WebSocket connectivity for Issue #517
This test directly connects to staging to validate HTTP 500 vs other errors
"""

import asyncio
import websockets
import time
from websockets.exceptions import InvalidStatus, ConnectionClosedError

async def test_staging_websocket():
    """Test staging WebSocket connection to reproduce Issue #517 HTTP 500 errors"""
    
    staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
    print(f"Testing WebSocket connection to: {staging_ws_url}")
    
    test_results = {
        "connection_attempts": 0,
        "http_500_errors": 0,
        "http_404_errors": 0, 
        "http_403_errors": 0,
        "other_errors": 0,
        "successful_connections": 0,
        "error_details": []
    }
    
    # Test various connection scenarios
    test_scenarios = [
        {
            "name": "no_auth",
            "headers": {},
            "description": "No authentication headers"
        },
        {
            "name": "invalid_auth",
            "headers": {"Authorization": "Bearer invalid_token"},
            "description": "Invalid authentication token"
        },
        {
            "name": "malformed_auth",
            "headers": {"Authorization": "InvalidFormat"},
            "description": "Malformed authorization header"
        },
        {
            "name": "empty_auth",
            "headers": {"Authorization": ""},
            "description": "Empty authorization header"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n[TEST] {scenario['name']}: {scenario['description']}")
        test_results["connection_attempts"] += 1
        
        try:
            async with websockets.connect(
                staging_ws_url,
                additional_headers=scenario["headers"]
            ) as websocket:
                print(f"  ✅ SUCCESS: Connected successfully")
                test_results["successful_connections"] += 1
                
                # Try to send a message
                await websocket.send('{"type": "ping"}')
                print(f"  📤 Sent ping message")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    print(f"  📥 Response: {response}")
                except asyncio.TimeoutError:
                    print(f"  ⏰ No response within timeout")
                    
        except InvalidStatus as e:
            status_code = getattr(e, 'status_code', None)
            error_message = str(e)
            print(f"  ❌ HTTP Error: {status_code} - {e}")
            
            # Check for HTTP 500 in error message even if status_code is None
            if status_code == 500 or "HTTP 500" in error_message:
                test_results["http_500_errors"] += 1
                print(f"  🚨 HTTP 500 ERROR DETECTED - Issue #517 reproduced!")
            elif status_code == 404 or "HTTP 404" in error_message:
                test_results["http_404_errors"] += 1
                print(f"  🔍 HTTP 404 - Endpoint not found")
            elif status_code == 403 or "HTTP 403" in error_message:
                test_results["http_403_errors"] += 1
                print(f"  🔒 HTTP 403 - Authentication required (expected)")
            else:
                test_results["other_errors"] += 1
                print(f"  ⚠️ Other HTTP error: {status_code}")
            
            test_results["error_details"].append({
                "scenario": scenario["name"],
                "status_code": status_code,
                "error": str(e),
                "description": scenario["description"]
            })
            
        except Exception as e:
            print(f"  💥 Unexpected error: {e}")
            test_results["other_errors"] += 1
            test_results["error_details"].append({
                "scenario": scenario["name"],
                "error_type": type(e).__name__,
                "error": str(e),
                "description": scenario["description"]
            })
    
    # Summary report
    print(f"\n" + "="*60)
    print(f"ISSUE #517 TEST RESULTS SUMMARY")
    print(f"="*60)
    print(f"Total connection attempts: {test_results['connection_attempts']}")
    print(f"Successful connections:   {test_results['successful_connections']}")
    print(f"HTTP 500 errors:          {test_results['http_500_errors']} 🚨")
    print(f"HTTP 404 errors:          {test_results['http_404_errors']}")
    print(f"HTTP 403 errors:          {test_results['http_403_errors']}")
    print(f"Other errors:             {test_results['other_errors']}")
    
    print(f"\nDETAILED ERROR ANALYSIS:")
    for i, error in enumerate(test_results["error_details"], 1):
        print(f"{i}. {error['scenario']}: {error.get('status_code', error.get('error_type', 'Unknown'))} - {error['error']}")
    
    # Issue #517 analysis
    if test_results["http_500_errors"] > 0:
        print(f"\n🚨 ISSUE #517 CONFIRMED: {test_results['http_500_errors']} HTTP 500 errors detected")
        print("   This indicates ASGI scope errors are still present in staging WebSocket connections")
        return "REPRODUCED"
    elif test_results["http_404_errors"] > 0:
        print(f"\n🔍 ISSUE #517 STATUS UNCLEAR: {test_results['http_404_errors']} HTTP 404 errors")
        print("   WebSocket endpoint may not be deployed or configured correctly")
        print("   This is different from the expected HTTP 500 ASGI scope errors")
        return "ENDPOINT_NOT_FOUND"
    elif test_results["successful_connections"] > 0:
        print(f"\n✅ ISSUE #517 POTENTIALLY RESOLVED: {test_results['successful_connections']} successful connections")
        print("   No HTTP 500 errors detected - ASGI scope issues may be fixed")
        return "RESOLVED"
    else:
        print(f"\n⚠️ ISSUE #517 STATUS UNKNOWN: No clear pattern in errors")
        return "UNKNOWN"

if __name__ == "__main__":
    result = asyncio.run(test_staging_websocket())
    print(f"\nFINAL ASSESSMENT: {result}")