#!/usr/bin/env python3
"""
Diagnostic script to analyze staging deployment failure
"""

import requests
import time
import json

def test_staging_endpoints():
    """Test staging endpoints to diagnose failure mode"""
    endpoints = {
        'backend_health': 'https://netra-backend-staging-pnovr5vsba-uc.a.run.app/health',
        'auth_health': 'https://netra-auth-service-pnovr5vsba-uc.a.run.app/health',
        'frontend': 'https://netra-frontend-staging-pnovr5vsba-uc.a.run.app'
    }

    results = {}

    for name, url in endpoints.items():
        print(f"\nTesting {name}: {url}")
        try:
            response = requests.get(url, timeout=60)
            results[name] = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_time': response.elapsed.total_seconds(),
                'content_length': len(response.text),
                'content_preview': response.text[:200] if response.text else None
            }
            print(f"  Status: {response.status_code}")
            print(f"  Response time: {response.elapsed.total_seconds():.2f}s")
            print(f"  Content length: {len(response.text)}")

            if response.status_code != 200:
                print(f"  Error response: {response.text[:500]}")

        except requests.exceptions.Timeout:
            results[name] = {'error': 'timeout'}
            print(f"  ERROR: Timeout after 60s")
        except requests.exceptions.ConnectionError as e:
            results[name] = {'error': f'connection_error: {str(e)}'}
            print(f"  ERROR: Connection error: {e}")
        except Exception as e:
            results[name] = {'error': f'exception: {str(e)}'}
            print(f"  ERROR: {e}")

    return results

def analyze_response_patterns(results):
    """Analyze response patterns to determine failure mode"""
    print("\n=== FAILURE ANALYSIS ===")

    backend_result = results.get('backend_health', {})
    auth_result = results.get('auth_health', {})
    frontend_result = results.get('frontend', {})

    # Check if services are responding
    if backend_result.get('status_code') == 503:
        print("❌ Backend: 503 Service Unavailable - Container startup failed")

    if auth_result.get('status_code') == 503:
        print("❌ Auth: 503 Service Unavailable - Container startup failed")

    if frontend_result.get('status_code') == 200:
        print("✅ Frontend: Working correctly")

    # Determine likely causes
    if (backend_result.get('status_code') == 503 and
        auth_result.get('status_code') == 503 and
        frontend_result.get('status_code') == 200):

        print("\n🔍 DIAGNOSIS:")
        print("- Frontend (Node.js) starts successfully")
        print("- Backend and Auth services (Python) fail to start")
        print("- This suggests a Python-specific startup issue")
        print("\nLIKELY CAUSES:")
        print("1. Database connection timeout (our target fix)")
        print("2. Missing environment variables")
        print("3. Import errors in Python dependencies")
        print("4. Memory/CPU resource limits exceeded")
        print("5. VPC connector misconfiguration")

        print("\nRECOMMENDATIONS:")
        print("1. Check Cloud Run logs for actual error messages")
        print("2. Verify environment variables are properly set")
        print("3. Test database connectivity from Cloud Run")
        print("4. Verify VPC connector for database access")

def main():
    print("=== STAGING DEPLOYMENT DIAGNOSTIC ===")
    print("Analyzing container startup failures...\n")

    # Test multiple times to see if it's intermittent
    for attempt in range(1, 4):
        print(f"\n--- Attempt {attempt}/3 ---")
        results = test_staging_endpoints()

        if attempt == 1:
            analyze_response_patterns(results)

        if attempt < 3:
            print("\nWaiting 30 seconds before next attempt...")
            time.sleep(30)

    print("\n=== DIAGNOSTIC COMPLETE ===")
    print("\nNEXT STEPS:")
    print("1. Access Cloud Run logs to see exact startup errors")
    print("2. Check if our timeout environment variables are properly set")
    print("3. Verify database connectivity from staging environment")

if __name__ == "__main__":
    main()