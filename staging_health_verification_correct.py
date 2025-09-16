#!/usr/bin/env python3
"""
Staging Service Health Verification Script
Checks health endpoints after infrastructure remediation using correct domains
"""

import requests
import time
import json
from typing import Dict, Any

def check_endpoint(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Check a single endpoint and return detailed status"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        end_time = time.time()

        return {
            "url": url,
            "status_code": response.status_code,
            "response_time": round(end_time - start_time, 2),
            "content_length": len(response.content),
            "success": response.status_code == 200,
            "headers": dict(response.headers),
            "content": response.text[:500] if response.text else ""  # First 500 chars
        }
    except requests.exceptions.Timeout:
        return {
            "url": url,
            "status_code": "TIMEOUT",
            "response_time": timeout,
            "success": False,
            "error": "Request timed out"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "url": url,
            "status_code": "CONNECTION_ERROR",
            "response_time": 0,
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "url": url,
            "status_code": "ERROR",
            "response_time": 0,
            "success": False,
            "error": str(e)
        }

def main():
    """Main health check function"""
    print("=== STAGING SERVICE HEALTH VERIFICATION ===")
    print("Checking services after infrastructure remediation...")
    print("Using correct *.netrasystems.ai domains\n")

    # Correct service endpoints based on current staging configuration
    endpoints = [
        "https://staging.netrasystems.ai/health",  # Backend via load balancer
        "https://staging.netrasystems.ai/api/health",  # Alternative backend health
        "https://netra-backend-staging-pnovr5vsba-uc.a.run.app/health",  # Direct Cloud Run URL
        "https://netra-auth-service-pnovr5vsba-uc.a.run.app/health",  # Auth service
    ]

    results = []

    for endpoint in endpoints:
        print(f"Checking: {endpoint}")
        result = check_endpoint(endpoint)
        results.append(result)

        if result["success"]:
            print(f"[SUCCESS] HTTP {result['status_code']} in {result['response_time']}s")
        else:
            status = result.get('status_code', 'ERROR')
            error = result.get('error', 'Unknown error')
            print(f"[FAILED] {status} - {error}")

        if result.get("content"):
            print(f"Response preview: {result['content'][:200]}...")
        print()

    # Summary
    print("=== SUMMARY ===")
    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"Endpoints healthy: {successful}/{total}")

    if successful >= 2:  # At least backend and auth should work
        print("[SUCCESS] SERVICES HEALTHY - Infrastructure remediation successful!")
    elif successful > 0:
        print("[WARNING] PARTIAL SUCCESS - Some services responding")
    else:
        print("[ERROR] ALL SERVICES DOWN - Infrastructure issues remain")

    # Check for specific improvements
    direct_cloud_run_working = any(
        r["success"] for r in results
        if "run.app" in r["url"]
    )

    load_balancer_working = any(
        r["success"] for r in results
        if "netrasystems.ai" in r["url"]
    )

    print(f"\nDirect Cloud Run URLs working: {'✅' if direct_cloud_run_working else '❌'}")
    print(f"Load balancer URLs working: {'✅' if load_balancer_working else '❌'}")

    # Check for 503 errors (the main issue we were fixing)
    has_503_errors = any(
        r.get("status_code") == 503 for r in results
    )

    if not has_503_errors and successful > 0:
        print("✅ NO 503 SERVICE UNAVAILABLE ERRORS - Container startup issue resolved!")
    elif has_503_errors:
        print("❌ Still seeing 503 errors - Container startup issues may persist")

    # Detailed results
    print("\n=== DETAILED RESULTS ===")
    for result in results:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()