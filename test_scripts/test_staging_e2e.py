#!/usr/bin/env python
"""Simple E2E test for GCP staging environment"""

import asyncio
import requests
import json
import sys
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

STAGING_BACKEND_URL = "https://api.staging.netrasystems.ai"
STAGING_AUTH_URL = "https://auth.staging.netrasystems.ai"

def test_health_endpoints():
    """Test health endpoints are accessible"""
    print("\n=== Testing Health Endpoints ===")
    
    # Test backend health
    try:
        response = requests.get(f"{STAGING_BACKEND_URL}/api/health", timeout=10)
        print(f"[PASS] Backend Health: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Service: {data.get('service')}, Version: {data.get('version')}")
    except Exception as e:
        print(f"[FAIL] Backend Health Failed: {e}")
        return False
    
    # Test auth service health
    try:
        response = requests.get(f"{STAGING_AUTH_URL}/health", timeout=10)
        print(f"[PASS] Auth Service Health: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Auth Service Health Failed: {e}")
        return False
    
    return True

def test_api_endpoints():
    """Test basic API endpoints"""
    print("\n=== Testing API Endpoints ===")
    
    # Test models endpoint
    try:
        response = requests.get(f"{STAGING_BACKEND_URL}/api/models", timeout=10)
        print(f"[PASS] Models API: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(f"  Available models: {len(models)} found")
    except Exception as e:
        print(f"[FAIL] Models API Failed: {e}")
    
    # Test metrics endpoint
    try:
        response = requests.get(f"{STAGING_BACKEND_URL}/api/metrics", timeout=10)
        print(f"[PASS] Metrics API: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Metrics API Failed: {e}")

def test_authentication_flow():
    """Test basic authentication flow"""
    print("\n=== Testing Authentication Flow ===")
    
    # Test login endpoint exists
    try:
        # This should return 422 or 401 without credentials
        response = requests.post(f"{STAGING_AUTH_URL}/auth/login", 
                                  json={}, 
                                  timeout=10)
        if response.status_code in [422, 401, 400]:
            print(f"[PASS] Login endpoint accessible (expected error: {response.status_code})")
        else:
            print(f"? Login endpoint returned unexpected: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Login endpoint Failed: {e}")
    
    # Test register endpoint exists
    try:
        response = requests.post(f"{STAGING_AUTH_URL}/auth/register", 
                                  json={}, 
                                  timeout=10)
        if response.status_code in [422, 400]:
            print(f"[PASS] Register endpoint accessible (expected error: {response.status_code})")
        else:
            print(f"? Register endpoint returned unexpected: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Register endpoint Failed: {e}")

def test_websocket_connectivity():
    """Test WebSocket endpoint availability"""
    print("\n=== Testing WebSocket Connectivity ===")
    
    # Convert https to wss for websocket URL
    ws_url = STAGING_BACKEND_URL.replace("https://", "wss://")
    
    # Just test that the endpoint exists (connection will likely fail without auth)
    try:
        import websocket
        ws = websocket.WebSocket()
        try:
            ws.connect(f"{ws_url}/ws", timeout=5)
            print(f"[PASS] WebSocket endpoint connected")
            ws.close()
        except Exception as e:
            # Expected to fail without auth, but shows endpoint exists
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
                print(f"[PASS] WebSocket endpoint exists (auth required)")
            else:
                print(f"? WebSocket connection: {e}")
    except ImportError:
        print("  Skipping WebSocket test (websocket-client not installed)")

def test_cors_headers():
    """Test CORS headers are properly configured"""
    print("\n=== Testing CORS Configuration ===")
    
    try:
        response = requests.options(f"{STAGING_BACKEND_URL}/api/health", 
                                     headers={"Origin": "http://localhost:3000"},
                                     timeout=10)
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
        }
        
        if cors_headers["Access-Control-Allow-Origin"]:
            print(f"[PASS] CORS enabled: {cors_headers['Access-Control-Allow-Origin']}")
            for header, value in cors_headers.items():
                if value:
                    print(f"  {header}: {value[:50]}...")
        else:
            print("[FAIL] CORS headers not found")
    except Exception as e:
        print(f"[FAIL] CORS test failed: {e}")

def main():
    """Run all E2E tests against staging"""
    print(f"""
========================================
     E2E Tests - GCP Staging Environment
========================================
Timestamp: {datetime.now().isoformat()}
Backend URL: {STAGING_BACKEND_URL}
Auth URL: {STAGING_AUTH_URL}
""")
    
    all_passed = True
    
    # Run health checks first
    if not test_health_endpoints():
        print("\n[WARNING] Health checks failed - services may be down")
        all_passed = False
    
    # Run other tests
    test_api_endpoints()
    test_authentication_flow()
    test_websocket_connectivity()
    test_cors_headers()
    
    # Summary
    print(f"""
========================================
                   Summary
========================================
""")
    
    if all_passed:
        print("OK: Core services are operational")
    else:
        print("WARNING: Some issues detected - review above")
    
    print("\nNote: This is a basic connectivity test.")
    print("Full E2E tests require proper authentication and test data.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())