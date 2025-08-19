#!/usr/bin/env python3
"""
Quick API Route Test Script

Tests key API routes to ensure they're accessible and working.
This script tests the routes that the frontend expects to exist.
"""

import asyncio
import json
import sys
from typing import Dict, List
from fastapi.testclient import TestClient

try:
    from app.main import app
    client = TestClient(app)
except ImportError as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)


def test_route(method: str, path: str, headers: Dict = None, json_data: Dict = None) -> Dict:
    """Test a single API route and return result."""
    try:
        if method.upper() == 'GET':
            response = client.get(path, headers=headers)
        elif method.upper() == 'POST':
            response = client.post(path, headers=headers, json=json_data)
        elif method.upper() == 'PATCH':
            response = client.patch(path, headers=headers, json=json_data)
        elif method.upper() == 'DELETE':
            response = client.delete(path, headers=headers, json=json_data)
        else:
            return {"status": "UNSUPPORTED", "method": method}
            
        return {
            "status": "SUCCESS" if response.status_code < 500 else "FAILED",
            "status_code": response.status_code,
            "accessible": response.status_code != 404
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def main():
    """Test critical API routes."""
    print("Testing Frontend API Route Configuration")
    print("=" * 60)
    
    # Test critical routes that frontend expects
    test_routes = [
        # Auth routes
        ("GET", "/api/auth/config"),
        ("GET", "/api/auth/me"),
        
        # User management routes
        ("GET", "/api/users/profile"),
        ("GET", "/api/users/settings"),
        ("GET", "/api/users/api-keys"),
        ("GET", "/api/users/sessions"),
        ("GET", "/api/users/notifications/settings"),
        ("GET", "/api/users/preferences"),
        
        # Core functionality routes
        ("GET", "/api/threads/"),
        ("GET", "/api/demo/"),
        ("GET", "/api/mcp/info"),
        
        # Generation and tools
        ("GET", "/api/generation/clickhouse_tables"),
        ("GET", "/api/tools/"),
        
        # Health and monitoring
        ("/health/", "GET"),
        ("GET", "/api/monitoring/health"),
    ]
    
    results = []
    total_tests = len(test_routes)
    accessible_count = 0
    
    for method, path in test_routes:
        print(f"Testing {method} {path}...", end=" ")
        result = test_route(method, path)
        
        if result["status"] == "SUCCESS":
            if result["accessible"]:
                print("OK ACCESSIBLE")
                accessible_count += 1
            else:
                print(f"FAIL NOT FOUND (404)")
        elif result["status"] == "FAILED":
            print(f"WARN FAILED ({result.get('status_code', 'Unknown')})")
            if result.get("accessible", False):
                accessible_count += 1
        else:
            print(f"ERROR: {result.get('error', 'Unknown error')}")
        
        results.append({
            "method": method,
            "path": path,
            **result
        })
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total routes tested: {total_tests}")
    print(f"Accessible routes: {accessible_count}")
    print(f"Success rate: {accessible_count/total_tests*100:.1f}%")
    
    # Show any failed routes
    failed_routes = [r for r in results if not r.get("accessible", False)]
    if failed_routes:
        print(f"\n❌ FAILED/MISSING ROUTES ({len(failed_routes)}):")
        for route in failed_routes:
            print(f"  {route['method']} {route['path']} - {route.get('status_code', 'ERROR')}")
    
    # Show successful routes  
    successful_routes = [r for r in results if r.get("accessible", False)]
    if successful_routes:
        print(f"\n✅ ACCESSIBLE ROUTES ({len(successful_routes)}):")
        for route in successful_routes:
            status_code = route.get('status_code', 'N/A')
            print(f"  {route['method']} {route['path']} - {status_code}")
    
    return accessible_count == total_tests


if __name__ == "__main__":
    success = main()
    if not success:
        print("\n⚠️  Some routes are not accessible. Check the configuration.")
        sys.exit(1)
    else:
        print("\n🎉 All critical API routes are accessible!")
        sys.exit(0)