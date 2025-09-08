#!/usr/bin/env python3
"""
Simple WebSocket HTTP 500 Test
Tests if WebSocket endpoints return 500 errors
"""

import requests
import sys

def test_websocket_endpoints():
    """Test WebSocket related endpoints for HTTP 500 errors."""
    
    base_url = "https://api.staging.netrasystems.ai"
    endpoints = [
        "/ws/health",
        "/ws/config", 
        "/ws/beacon"
    ]
    
    results = []
    
    print("Testing WebSocket endpoints for HTTP 500 errors...")
    print("=" * 60)
    
    for endpoint in endpoints:
        url = base_url + endpoint
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 500:
                print(f"  ERROR: HTTP 500 on {endpoint}")
                results.append({"endpoint": endpoint, "status": 500, "error": True})
            elif response.status_code == 200:
                print(f"  SUCCESS: HTTP 200 on {endpoint}")
                results.append({"endpoint": endpoint, "status": 200, "error": False})
            else:
                print(f"  UNEXPECTED: HTTP {response.status_code} on {endpoint}")
                results.append({"endpoint": endpoint, "status": response.status_code, "error": True})
                
        except requests.exceptions.RequestException as e:
            print(f"  CONNECTION ERROR: {endpoint} - {e}")
            results.append({"endpoint": endpoint, "status": "error", "error": True})
    
    print("=" * 60)
    
    # Summary
    error_count = sum(1 for r in results if r["error"])
    success_count = len(results) - error_count
    
    print(f"Summary: {success_count}/{len(results)} endpoints working")
    
    if error_count == 0:
        print("SUCCESS: All WebSocket endpoints working!")
        return True
    else:
        print(f"FAILURE: {error_count} endpoints have errors")
        return False

def test_websocket_connection():
    """Test actual WebSocket connection (simplified)."""
    print("\nTesting WebSocket connection...")
    
    try:
        import websocket
        
        def on_message(ws, message):
            print(f"Received: {message}")
            ws.close()
            
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket connection closed")
            
        def on_open(ws):
            print("WebSocket connection opened")
            ws.send('{"type": "ping"}')
        
        # Test the basic test endpoint (no auth required)
        ws_url = "wss://api.staging.netrasystems.ai/ws/test"
        print(f"Connecting to {ws_url}")
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        ws.run_forever(timeout=5)
        return True
        
    except ImportError:
        print("websocket-client not installed, skipping connection test")
        return False
    except Exception as e:
        print(f"WebSocket connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("WebSocket HTTP 500 Fix Validation Test")
    print("Testing staging environment...")
    
    # Test HTTP endpoints
    endpoints_ok = test_websocket_endpoints()
    
    # Test WebSocket connection
    connection_ok = test_websocket_connection()
    
    if endpoints_ok and connection_ok:
        print("\nSUCCESS: WebSocket fixes appear to be working!")
        sys.exit(0)
    elif endpoints_ok:
        print("\nPARTIAL SUCCESS: Endpoints working but connection issues remain")
        sys.exit(1)
    else:
        print("\nFAILURE: HTTP 500 errors still present")
        sys.exit(1)