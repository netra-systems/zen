#!/usr/bin/env python3
"""
Quick deployment status checker for GCP staging services.
Checks service health without requiring gcloud auth approval.
"""
import requests
import sys
from datetime import datetime

def check_service_health(service_name, url, timeout=10):
    """Check health of a service endpoint."""
    try:
        response = requests.get(f"{url}/health", timeout=timeout)
        return {
            "service": service_name,
            "status": "HEALTHY" if response.status_code == 200 else "UNHEALTHY",
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "error": None
        }
    except requests.exceptions.RequestException as e:
        return {
            "service": service_name,
            "status": "ERROR",
            "status_code": None,
            "response_time": None,
            "error": str(e)
        }

def main():
    """Check deployment status of staging services."""
    print(f"GCP Staging Service Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Known staging service URLs from deployment output
    services = [
        ("Backend", "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"),
        ("Auth", "https://netra-auth-service-pnovr5vsba-uc.a.run.app"),
        # Note: Frontend typically doesn't have a health endpoint
    ]

    results = []
    for service_name, url in services:
        print(f"Checking {service_name}...")
        result = check_service_health(service_name, url)
        results.append(result)

        status_symbol = "[HEALTHY]" if result["status"] == "HEALTHY" else "[ERROR]"
        if result["error"]:
            print(f"{status_symbol} {service_name}: {result['status']} - {result['error']}")
        else:
            print(f"{status_symbol} {service_name}: {result['status']} (HTTP {result['status_code']}, {result['response_time']:.2f}s)")

    print("\n" + "=" * 80)
    healthy_count = sum(1 for r in results if r["status"] == "HEALTHY")
    total_count = len(results)

    if healthy_count == total_count:
        print(f"DEPLOYMENT SUCCESS: All {total_count} services are healthy")
        sys.exit(0)
    else:
        print(f"DEPLOYMENT STATUS: {healthy_count}/{total_count} services healthy")
        sys.exit(1)

if __name__ == "__main__":
    main()