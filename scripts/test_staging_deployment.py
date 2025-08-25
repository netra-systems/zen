#!/usr/bin/env python3
"""
Comprehensive staging deployment validation script.
Tests all critical endpoints and services on staging environment.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any
import aiohttp
import ssl
from pathlib import Path

# Add project root to path

# Constants
STAGING_API_URL = "https://api.staging.netrasystems.ai"
STAGING_AUTH_URL = "https://auth.staging.netrasystems.ai"
STAGING_FRONTEND_URL = "https://app.staging.netrasystems.ai"

# Test results storage
test_results = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "environment": "staging",
    "services": {},
    "endpoints": {},
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "errors": []
}


async def test_endpoint(session: aiohttp.ClientSession, name: str, url: str, method: str = "GET", 
                       headers: Dict = None, expected_status: List[int] = None) -> Dict:
    """Test a single endpoint"""
    if expected_status is None:
        expected_status = [200, 307, 308]
    
    result = {
        "name": name,
        "url": url,
        "method": method,
        "status": None,
        "response_time": None,
        "passed": False,
        "error": None,
        "body": None
    }
    
    try:
        start = datetime.now(timezone.utc)
        async with session.request(method, url, headers=headers, allow_redirects=False) as response:
            end = datetime.now(timezone.utc)
            result["response_time"] = (end - start).total_seconds()
            result["status"] = response.status
            
            if response.status in expected_status:
                result["passed"] = True
                if response.status == 200:
                    try:
                        result["body"] = await response.json()
                    except:
                        result["body"] = await response.text()
            else:
                result["error"] = f"Unexpected status: {response.status}"
                try:
                    result["body"] = await response.text()
                except:
                    pass
                    
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def test_service_health(session: aiohttp.ClientSession) -> None:
    """Test health endpoints for all services"""
    health_tests = [
        ("Backend API Health", f"{STAGING_API_URL}/health/", "GET", None, [200, 307]),
        ("Auth Service Health", f"{STAGING_AUTH_URL}/auth/health", "GET", None, [200]),
        ("Frontend Health", f"{STAGING_FRONTEND_URL}/", "GET", None, [200, 304]),
    ]
    
    for name, url, method, headers, expected in health_tests:
        result = await test_endpoint(session, name, url, method, headers, expected)
        test_results["services"][name] = result
        test_results["total_tests"] += 1
        if result["passed"]:
            test_results["passed"] += 1
            print(f"[PASS] {name}: {result['status']} ({result['response_time']:.2f}s)")
        else:
            test_results["failed"] += 1
            print(f"[FAIL] {name}: {result.get('error', 'Failed')}")


async def test_api_endpoints(session: aiohttp.ClientSession) -> None:
    """Test main API endpoints"""
    api_tests = [
        ("API Threads List", f"{STAGING_API_URL}/api/threads", "GET", 
         {"Authorization": "Bearer test"}, [401, 403]),
        ("API Workspaces", f"{STAGING_API_URL}/api/workspaces", "GET",
         {"Authorization": "Bearer test"}, [401, 403]),
        ("API Agents", f"{STAGING_API_URL}/api/agents", "GET",
         {"Authorization": "Bearer test"}, [401, 403]),
    ]
    
    for name, url, method, headers, expected in api_tests:
        result = await test_endpoint(session, name, url, method, headers, expected)
        test_results["endpoints"][name] = result
        test_results["total_tests"] += 1
        if result["passed"]:
            test_results["passed"] += 1
            print(f"[PASS] {name}: {result['status']} ({result['response_time']:.2f}s)")
        else:
            test_results["failed"] += 1
            print(f"[FAIL] {name}: {result.get('error', 'Failed')}")


async def test_auth_flow(session: aiohttp.ClientSession) -> None:
    """Test OAuth authentication flow"""
    auth_tests = [
        ("OAuth Login Endpoint", f"{STAGING_AUTH_URL}/auth/login", "GET", None, [200, 302, 307]),
        ("OAuth Callback", f"{STAGING_AUTH_URL}/auth/callback", "GET", None, [400, 422]),
        ("Token Endpoint", f"{STAGING_AUTH_URL}/auth/token", "POST", 
         {"Content-Type": "application/json"}, [400, 422]),
    ]
    
    for name, url, method, headers, expected in auth_tests:
        result = await test_endpoint(session, name, url, method, headers, expected)
        test_results["endpoints"][name] = result
        test_results["total_tests"] += 1
        if result["passed"]:
            test_results["passed"] += 1
            print(f"[PASS] {name}: {result['status']} ({result['response_time']:.2f}s)")
        else:
            test_results["failed"] += 1
            print(f"[FAIL] {name}: {result.get('error', 'Failed')}")


async def test_websocket_connectivity() -> None:
    """Test WebSocket connectivity"""
    ws_url = f"wss://api.staging.netrasystems.ai/ws"
    result = {
        "name": "WebSocket Connection",
        "url": ws_url,
        "passed": False,
        "error": None
    }
    
    try:
        # Create SSL context that accepts staging certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        session = aiohttp.ClientSession()
        try:
            ws = await session.ws_connect(ws_url, ssl=ssl_context, timeout=5)
            await ws.close()
            result["passed"] = True
        except Exception as e:
            result["error"] = str(e)
        finally:
            await session.close()
    except Exception as e:
        result["error"] = str(e)
    
    test_results["endpoints"]["WebSocket"] = result
    test_results["total_tests"] += 1
    if result["passed"]:
        test_results["passed"] += 1
        print(f"[PASS] WebSocket Connection: Connected")
    else:
        test_results["failed"] += 1
        print(f"[FAIL] WebSocket Connection: {result['error']}")


async def main():
    """Run all staging deployment tests"""
    print("\n" + "="*60)
    print("STAGING DEPLOYMENT VALIDATION TEST SUITE")
    print("="*60)
    print(f"Timestamp: {test_results['timestamp']}")
    print(f"Environment: STAGING")
    print("="*60 + "\n")
    
    # Create session with SSL verification disabled for staging
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        print("[TEST] Testing Service Health Endpoints...")
        print("-" * 40)
        await test_service_health(session)
        
        print("\n[TEST] Testing API Endpoints...")
        print("-" * 40)
        await test_api_endpoints(session)
        
        print("\n[TEST] Testing Authentication Flow...")
        print("-" * 40)
        await test_auth_flow(session)
    
    print("\n[TEST] Testing WebSocket Connectivity...")
    print("-" * 40)
    await test_websocket_connectivity()
    
    # Generate summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {test_results['total_tests']}")
    print(f"[PASS] Passed: {test_results['passed']}")
    print(f"[FAIL] Failed: {test_results['failed']}")
    print(f"Success Rate: {(test_results['passed']/test_results['total_tests']*100):.1f}%")
    
    # Save results to file
    report_dir = Path(__file__).parent.parent / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"staging_validation_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n[REPORT] Detailed report saved to: {report_file}")
    
    # Return exit code based on results
    if test_results["failed"] > 0:
        print("\n[WARNING] Some tests failed. Check the report for details.")
        return 1
    else:
        print("\n[SUCCESS] All tests passed! Staging deployment is healthy.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)