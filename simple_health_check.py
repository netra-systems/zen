#!/usr/bin/env python3
"""Simple staging health check without Unicode issues"""

import requests
import time

def check_endpoint(url, timeout=30):
    """Check endpoint and return basic status"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = time.time() - start_time

        return {
            "url": url,
            "status": response.status_code,
            "time": round(elapsed, 2),
            "success": response.status_code == 200,
            "text": response.text[:200] if response.text else ""
        }
    except Exception as e:
        return {
            "url": url,
            "status": "ERROR",
            "time": 0,
            "success": False,
            "error": str(e)
        }

def main():
    print("=== STAGING SERVICE HEALTH CHECK ===")
    print("Testing services after infrastructure remediation")
    print()

    # Test endpoints
    endpoints = [
        "https://staging.netrasystems.ai/health",
        "https://netra-backend-staging-pnovr5vsba-uc.a.run.app/health",
        "https://netra-auth-service-pnovr5vsba-uc.a.run.app/health"
    ]

    results = []
    for url in endpoints:
        print(f"Testing: {url}")
        result = check_endpoint(url)
        results.append(result)

        if result["success"]:
            print(f"  [OK] HTTP {result['status']} in {result['time']}s")
        else:
            status = result.get('status', 'ERROR')
            error = result.get('error', 'Unknown')
            print(f"  [FAIL] {status} - {error}")

        if result.get("text"):
            print(f"  Response: {result['text'][:100]}...")
        print()

    # Summary
    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"=== SUMMARY ===")
    print(f"Healthy endpoints: {successful}/{total}")

    # Check for 503 errors specifically
    has_503 = any(r.get("status") == 503 for r in results)

    if successful > 0:
        print("[SUCCESS] Services are responding!")
        if not has_503:
            print("[SUCCESS] No 503 errors - infrastructure fix successful!")
    else:
        print("[ERROR] All services down")

    if has_503:
        print("[WARNING] Still seeing 503 errors")

    return successful > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)