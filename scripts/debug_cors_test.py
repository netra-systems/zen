#!/usr/bin/env python3
"""
Debug script to test CORS configuration against the running backend.
"""
import os
import sys
import requests

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cors_preflight(origin, url):
    """Test CORS preflight request."""
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type"
    }
    
    try:
        response = requests.options(url, headers=headers, timeout=10)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text
        }
    except Exception as e:
        return {"error": str(e)}

def test_actual_request(origin, url):
    """Test actual CORS request."""
    headers = {"Origin": origin}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text[:200] + "..." if len(response.text) > 200 else response.text
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main test function."""
    backend_url = "http://localhost:8000"
    test_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "https://app.staging.netrasystems.ai",
        "http://evil-site.com"
    ]
    
    print("="*60)
    print("CORS DEBUG TEST")
    print("="*60)
    
    # Test health endpoint
    health_url = f"{backend_url}/health"
    
    print(f"Testing endpoint: {health_url}")
    print()
    
    for origin in test_origins:
        print(f"Testing origin: {origin}")
        print("-" * 40)
        
        # Preflight test
        print("PREFLIGHT REQUEST:")
        preflight_result = test_cors_preflight(origin, health_url)
        if "error" in preflight_result:
            print(f"  ERROR: {preflight_result['error']}")
        else:
            print(f"  Status: {preflight_result['status_code']}")
            print(f"  Response: {preflight_result['text']}")
            cors_headers = {k: v for k, v in preflight_result['headers'].items() 
                          if k.lower().startswith('access-control')}
            if cors_headers:
                print("  CORS Headers:")
                for k, v in cors_headers.items():
                    print(f"    {k}: {v}")
            else:
                print("  No CORS headers found")
        
        print()
        
        # Actual request test
        print("ACTUAL REQUEST:")
        actual_result = test_actual_request(origin, health_url)
        if "error" in actual_result:
            print(f"  ERROR: {actual_result['error']}")
        else:
            print(f"  Status: {actual_result['status_code']}")
            cors_headers = {k: v for k, v in actual_result['headers'].items() 
                          if k.lower().startswith('access-control')}
            if cors_headers:
                print("  CORS Headers:")
                for k, v in cors_headers.items():
                    print(f"    {k}: {v}")
            else:
                print("  No CORS headers found")
        
        print()
        print("="*60)

if __name__ == "__main__":
    main()