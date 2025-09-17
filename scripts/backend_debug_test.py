#!/usr/bin/env python3
"""
Backend Service Debug Test
Quick debug test to check what's happening with the backend service.
"""

import requests
import time


def debug_backend_service():
    """Debug the backend service responses."""
    backend_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"

    endpoints_to_test = [
        "/health",
        "/",
        "/docs",
        "/api/v1/health",
        "/api/health"
    ]

    print("BACKEND SERVICE DEBUG TEST")
    print("=" * 40)
    print(f"Testing backend: {backend_url}")
    print("")

    for endpoint in endpoints_to_test:
        url = f"{backend_url}{endpoint}"
        try:
            print(f"Testing: {endpoint}")
            response = requests.get(url, timeout=30)
            print(f"  Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('text'):
                print(f"  Response: {response.text[:200]}...")
            else:
                print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            print("")
        except requests.exceptions.RequestException as e:
            print(f"  ERROR: {e}")
            print("")


if __name__ == "__main__":
    debug_backend_service()