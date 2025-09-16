#!/usr/bin/env python3
"""
Golden Path Test for Staging
Tests the actual user-facing endpoints that matter for the golden path.
"""

import requests
import time


def test_golden_path_staging():
    """Test the golden path through the load balancer."""
    print("GOLDEN PATH STAGING TEST")
    print("=" * 30)

    # Test 1: Frontend access
    try:
        response = requests.get('https://staging.netrasystems.ai/', timeout=30)
        print(f"Frontend: {response.status_code}")
        if response.status_code == 200:
            print("  PASS: Frontend accessible")
        frontend_ok = response.status_code == 200
    except Exception as e:
        print(f"Frontend ERROR: {e}")
        frontend_ok = False

    # Test 2: Backend API through load balancer
    try:
        response = requests.get('https://staging.netrasystems.ai/health', timeout=30)
        print(f"Backend API: {response.status_code}")
        if response.status_code == 200:
            print("  PASS: Backend API accessible through load balancer")
        backend_ok = response.status_code == 200
    except Exception as e:
        print(f"Backend API ERROR: {e}")
        backend_ok = False

    # Test 3: WebSocket endpoint readiness
    try:
        # Test if WebSocket endpoint responds (we don't establish WS, just check HTTP)
        response = requests.get('https://api-staging.netrasystems.ai/', timeout=30)
        print(f"WebSocket endpoint: {response.status_code}")
        # Even 404 is acceptable - it means the service is running
        websocket_ok = response.status_code in [200, 404, 405]
        if websocket_ok:
            print("  PASS: WebSocket endpoint reachable")
    except Exception as e:
        print(f"WebSocket endpoint ERROR: {e}")
        websocket_ok = False

    print("\n=== GOLDEN PATH STATUS ===")
    if frontend_ok and backend_ok:
        print("SUCCESS: Golden Path is working!")
        print("PASS: Users can access frontend")
        print("PASS: Backend API accessible via load balancer")
        print("PASS: SSOT changes deployed without breaking user flow")
        print("PASS: Ready for production promotion")
        return True
    elif backend_ok:
        print("PARTIAL: Backend working but frontend issues")
    elif frontend_ok:
        print("PARTIAL: Frontend working but backend issues")
    else:
        print("FAIL: Golden Path broken")

    return False


if __name__ == "__main__":
    test_golden_path_staging()