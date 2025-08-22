#!/usr/bin/env python3
"""
Simple Integration Test for Auth Service and WebSocket Configuration

Tests basic connectivity without Unicode characters to avoid Windows issues.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import aiohttp

# Add project root to path

from dev_launcher.service_discovery import ServiceDiscovery


async def test_service_health(session, service_name, url):
    """Test if a service is healthy."""
    health_url = f"{url}/health"
    
    try:
        async with session.get(health_url, timeout=5) as response:
            if response.status == 200:
                health_data = await response.json()
                print(f"[PASS] {service_name} service healthy at {url}")
                return True, health_data
            else:
                print(f"[FAIL] {service_name} service returned HTTP {response.status}")
                return False, None
                
    except Exception as e:
        print(f"[FAIL] {service_name} service connection failed: {e}")
        return False, None


async def test_cors_headers(session, url):
    """Test CORS headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST"
    }
    
    try:
        async with session.options(f"{url}/health", headers=headers, timeout=5) as response:
            cors_origin = response.headers.get("Access-Control-Allow-Origin")
            if cors_origin:
                print(f"[PASS] CORS headers present: {cors_origin}")
                return True
            else:
                print("[FAIL] CORS headers missing")
                return False
                
    except Exception as e:
        print(f"[FAIL] CORS test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("Netra Integration Test")
    print("=" * 40)
    
    # Read service discovery
    service_discovery = ServiceDiscovery(project_root)
    
    try:
        backend_info = service_discovery.read_backend_info()
        auth_info = service_discovery.read_auth_info()
        frontend_info = service_discovery.read_frontend_info()
    except Exception as e:
        print(f"[ERROR] Service discovery failed: {e}")
        return 1
    
    # Test results
    results = []
    
    async with aiohttp.ClientSession() as session:
        # Test backend service
        if backend_info:
            backend_url = backend_info.get("api_url", "http://localhost:8000")
            success, data = await test_service_health(session, "Backend", backend_url)
            results.append(("backend_health", success))
            
            if success:
                # Test CORS
                cors_success = await test_cors_headers(session, backend_url)
                results.append(("cors_headers", cors_success))
        else:
            print("[FAIL] Backend service not found in discovery")
            results.append(("backend_health", False))
        
        # Test auth service
        if auth_info:
            auth_url = auth_info.get("url", "http://localhost:8082")
            success, data = await test_service_health(session, "Auth", auth_url)
            results.append(("auth_health", success))
        else:
            print("[FAIL] Auth service not found in discovery")
            results.append(("auth_health", False))
        
        # Test frontend service if available
        if frontend_info:
            frontend_url = frontend_info.get("url", "http://localhost:3000")
            success, data = await test_service_health(session, "Frontend", frontend_url)
            results.append(("frontend_health", success))
        else:
            print("[INFO] Frontend service not found in discovery (may not be running)")
    
    # Print summary
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {test_name}: {status}")
    
    # Save results
    results_file = project_root / "simple_test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "results": dict(results),
            "passed": passed,
            "total": total
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    
    # Print configuration info
    print("\nCurrent Configuration:")
    if backend_info:
        print(f"  Backend: {backend_info.get('api_url', 'N/A')}")
    if auth_info:
        print(f"  Auth Service: {auth_info.get('url', 'N/A')}")
    if frontend_info:
        print(f"  Frontend: {frontend_info.get('url', 'N/A')}")
    
    print("\nFrontend .env.local should use:")
    if backend_info:
        print(f"  NEXT_PUBLIC_API_URL={backend_info.get('api_url', 'http://localhost:8000')}")
        backend_ws = backend_info.get('api_url', 'http://localhost:8000').replace('http://', 'ws://') + '/ws'
        print(f"  NEXT_PUBLIC_WEBSOCKET_URL={backend_ws}")
    if auth_info:
        print(f"  NEXT_PUBLIC_AUTH_SERVICE_URL={auth_info.get('url', 'http://localhost:8082')}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)