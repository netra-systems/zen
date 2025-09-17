#!/usr/bin/env python3
"""
Quick staging environment connectivity check for P1 critical tests.
This validates that staging is accessible before running the full test suite.
"""

import asyncio
import httpx
import websockets
import json
import time
from tests.e2e.staging_test_config import get_staging_config

async def check_staging_connectivity():
    """Quick check of staging environment connectivity"""
    config = get_staging_config()
    results = []

    print(f"Testing staging environment connectivity...")
    print(f"Backend URL: {config.backend_url}")
    print(f"WebSocket URL: {config.websocket_url}")
    print(f"=" * 60)

    # Test 1: Backend Health Check
    try:
        print("1. Testing backend health endpoint...")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{config.backend_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Backend health check PASSED: {health_data}")
                results.append({"test": "backend_health", "status": "PASS", "details": health_data})
            else:
                print(f"❌ Backend health check FAILED: {response.status_code} - {response.text}")
                results.append({"test": "backend_health", "status": "FAIL", "details": f"{response.status_code}: {response.text}"})
    except Exception as e:
        print(f"❌ Backend health check ERROR: {e}")
        results.append({"test": "backend_health", "status": "ERROR", "details": str(e)})

    # Test 2: WebSocket Connection (without auth - should fail with 403)
    try:
        print("\n2. Testing WebSocket connection (expect auth error)...")
        async with websockets.connect(
            config.websocket_url,
            close_timeout=10
        ) as ws:
            print("❌ WebSocket connection SUCCEEDED without auth (security issue!)")
            results.append({"test": "websocket_auth", "status": "FAIL", "details": "Connection succeeded without auth"})
    except websockets.exceptions.InvalidStatus as e:
        if "403" in str(e):
            print(f"✅ WebSocket auth check PASSED: Got expected 403 error: {e}")
            results.append({"test": "websocket_auth", "status": "PASS", "details": "Auth properly enforced"})
        else:
            print(f"❌ WebSocket connection FAILED with unexpected error: {e}")
            results.append({"test": "websocket_auth", "status": "FAIL", "details": str(e)})
    except Exception as e:
        print(f"❌ WebSocket connection ERROR: {e}")
        results.append({"test": "websocket_auth", "status": "ERROR", "details": str(e)})

    # Test 3: API Endpoints
    try:
        print("\n3. Testing API endpoints...")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{config.api_url}/info")
            if response.status_code in [200, 401, 403]:  # Any response indicates server is up
                print(f"✅ API endpoint ACCESSIBLE: {response.status_code}")
                results.append({"test": "api_endpoint", "status": "PASS", "details": f"Status: {response.status_code}"})
            else:
                print(f"❌ API endpoint FAILED: {response.status_code} - {response.text}")
                results.append({"test": "api_endpoint", "status": "FAIL", "details": f"{response.status_code}: {response.text}"})
    except Exception as e:
        print(f"❌ API endpoint ERROR: {e}")
        results.append({"test": "api_endpoint", "status": "ERROR", "details": str(e)})

    print(f"\n{'=' * 60}")
    print("STAGING CONNECTIVITY SUMMARY:")
    print(f"{'=' * 60}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")

    if errors > 0 or failed > 0:
        print("\n❌ STAGING ENVIRONMENT HAS CONNECTIVITY ISSUES!")
        print("Cannot proceed with P1 critical tests until infrastructure is resolved.")
        return False
    else:
        print("\n✅ STAGING ENVIRONMENT IS ACCESSIBLE!")
        print("Ready to proceed with P1 critical tests.")
        return True

if __name__ == "__main__":
    success = asyncio.run(check_staging_connectivity())
    exit(0 if success else 1)