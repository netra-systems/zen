#!/usr/bin/env python3
"""Test CORS configuration in staging environment."""

import requests
import json
from shared.isolated_environment import IsolatedEnvironment

def test_cors_headers():
    """Test CORS headers are properly set for staging environment."""
    
    # Test endpoints
    backend_url = "https://api.staging.netrasystems.ai"
    frontend_origin = "https://app.staging.netrasystems.ai"
    
    print(f"Testing CORS from {frontend_origin} to {backend_url}")
    print("=" * 60)
    
    # Test 1: OPTIONS preflight request
    print("\n1. Testing OPTIONS preflight request...")
    headers = {
        "Origin": frontend_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }
    
    try:
        response = requests.options(f"{backend_url}/api/agents/triage", headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers:")
        for header in response.headers:
            if "access-control" in header.lower():
                print(f"     {header}: {response.headers[header]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Actual POST request with Origin header
    print("\n2. Testing POST request with Origin header...")
    headers = {
        "Origin": frontend_origin,
        "Content-Type": "application/json"
    }
    
    data = {
        "message": "Test CORS configuration",
        "context": {}
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/agents/triage", 
            headers=headers,
            json=data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers:")
        for header in response.headers:
            if "access-control" in header.lower() or header.lower() == "vary":
                print(f"     {header}: {response.headers[header]}")
        
        # Check for missing Access-Control-Allow-Origin
        if "access-control-allow-origin" not in [h.lower() for h in response.headers]:
            print("    WARNING: [U+FE0F]  WARNING: Access-Control-Allow-Origin header is missing!")
        else:
            print("   [U+2713] Access-Control-Allow-Origin header is present")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 3: Test health endpoint (should always work)
    print("\n3. Testing health endpoint...")
    headers = {
        "Origin": frontend_origin
    }
    
    try:
        response = requests.get(f"{backend_url}/health", headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   CORS Headers:")
        for header in response.headers:
            if "access-control" in header.lower() or header.lower() == "vary":
                print(f"     {header}: {response.headers[header]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("CORS test complete")

if __name__ == "__main__":
    test_cors_headers()