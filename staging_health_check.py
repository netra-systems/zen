#!/usr/bin/env python3
"""
Direct staging service health validation
Tests core staging endpoints to validate infrastructure recovery
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

# Staging service endpoints from .env.staging.tests
STAGING_SERVICES = {
    'backend': 'https://netra-backend-staging-pnovr5vsba-uc.a.run.app',
    'auth': 'https://auth.staging.netrasystems.ai',
    'frontend': 'https://frontend-701982941522.us-central1.run.app'
}

async def check_service_health(service_name, base_url, session):
    """Check if a service is responding and not returning 503 errors"""
    endpoints_to_test = [
        '/health',
        '/api/health',
        '/status',
        '/'  # Basic root endpoint
    ]

    results = {}

    for endpoint in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        try:
            start_time = time.time()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                elapsed = time.time() - start_time

                results[endpoint] = {
                    'status_code': response.status,
                    'response_time_ms': round(elapsed * 1000, 2),
                    'headers': dict(response.headers),
                    'accessible': response.status < 500,
                    'recovered_from_503': response.status != 503
                }

                # Try to get response text for small responses
                try:
                    if response.content_length and response.content_length < 1000:
                        text = await response.text()
                        results[endpoint]['response_preview'] = text[:200]
                except:
                    pass

        except asyncio.TimeoutError:
            results[endpoint] = {
                'error': 'timeout',
                'accessible': False,
                'recovered_from_503': 'unknown'
            }
        except Exception as e:
            results[endpoint] = {
                'error': str(e),
                'accessible': False,
                'recovered_from_503': 'unknown'
            }

    return results

async def validate_staging_infrastructure():
    """Main validation function"""
    print("=== STAGING INFRASTRUCTURE RECOVERY VALIDATION ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    overall_results = {}

    async with aiohttp.ClientSession() as session:
        for service_name, base_url in STAGING_SERVICES.items():
            print(f"Testing {service_name.upper()} service: {base_url}")

            results = await check_service_health(service_name, base_url, session)
            overall_results[service_name] = {
                'base_url': base_url,
                'endpoints': results
            }

            # Check if any endpoint is accessible
            any_accessible = any(r.get('accessible', False) for r in results.values())
            any_recovered = any(r.get('recovered_from_503', False) for r in results.values() if r.get('recovered_from_503') != 'unknown')

            if any_accessible:
                print(f"  [OK] {service_name.upper()} is accessible")
                if any_recovered:
                    print(f"  [OK] {service_name.upper()} has recovered from 503 errors")
            else:
                print(f"  [FAIL] {service_name.upper()} is not accessible")

            # Show accessible endpoints
            for endpoint, result in results.items():
                if result.get('accessible'):
                    status = result.get('status_code', 'unknown')
                    time_ms = result.get('response_time_ms', 'unknown')
                    print(f"    {endpoint}: HTTP {status} ({time_ms}ms)")

            print()

    # Summary
    total_services = len(STAGING_SERVICES)
    accessible_services = sum(1 for service_data in overall_results.values()
                            if any(r.get('accessible', False) for r in service_data['endpoints'].values()))

    print("=== SUMMARY ===")
    print(f"Services tested: {total_services}")
    print(f"Services accessible: {accessible_services}")
    print(f"Infrastructure recovery status: {'[RECOVERED]' if accessible_services > 0 else '[STILL DOWN]'}")

    # Save detailed results
    results_file = f"staging_health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(overall_results, f, indent=2)
    print(f"Detailed results saved to: {results_file}")

    return accessible_services > 0, overall_results

if __name__ == "__main__":
    recovered, results = asyncio.run(validate_staging_infrastructure())
    exit(0 if recovered else 1)