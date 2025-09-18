#!/usr/bin/env python3
"""
Phase 1 Infrastructure Health Validation Script
Per E2E worklog requirements - run infrastructure tests for staging GCP
"""

import sys
import asyncio
import time
import json
from pathlib import Path

# Setup path for imports
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import test configuration
try:
    from tests.e2e.staging_test_config import get_staging_config
    import httpx
    import websockets
except ImportError as e:
    print(f"Import error: {e}")
    print("Required packages may not be available")
    sys.exit(1)

async def test_staging_connectivity():
    """Phase 1: Test basic staging connectivity"""
    print("=== PHASE 1: INFRASTRUCTURE HEALTH VALIDATION ===")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    config = get_staging_config()
    results = {}

    # Test 1: HTTP connectivity to staging backend
    print("\n1. Testing HTTP connectivity to staging backend...")
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{config.backend_url}/health")
            duration = time.time() - start_time

            results['http_connectivity'] = {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'duration': duration,
                'url': config.backend_url
            }
            print(f"   ✅ HTTP connectivity: {response.status_code} in {duration:.2f}s")
    except Exception as e:
        results['http_connectivity'] = {
            'success': False,
            'error': str(e),
            'url': config.backend_url
        }
        print(f"   ❌ HTTP connectivity failed: {e}")

    # Test 2: WebSocket connectivity
    print("\n2. Testing WebSocket connectivity...")
    try:
        start_time = time.time()
        websocket = await asyncio.wait_for(
            websockets.connect(config.websocket_url),
            timeout=10
        )
        connection_time = time.time() - start_time

        # Test ping
        await websocket.ping()
        await websocket.close()

        results['websocket_connectivity'] = {
            'success': True,
            'connection_time': connection_time,
            'url': config.websocket_url
        }
        print(f"   ✅ WebSocket connectivity: Connected in {connection_time:.2f}s")
    except Exception as e:
        results['websocket_connectivity'] = {
            'success': False,
            'error': str(e),
            'url': config.websocket_url
        }
        print(f"   ❌ WebSocket connectivity failed: {e}")

    # Test 3: API endpoint basic test
    print("\n3. Testing API endpoint...")
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{config.api_url}/health")
            duration = time.time() - start_time

            results['api_connectivity'] = {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'duration': duration,
                'url': config.api_url
            }
            print(f"   ✅ API connectivity: {response.status_code} in {duration:.2f}s")
    except Exception as e:
        results['api_connectivity'] = {
            'success': False,
            'error': str(e),
            'url': config.api_url
        }
        print(f"   ❌ API connectivity failed: {e}")

    # Summary
    print("\n=== PHASE 1 RESULTS SUMMARY ===")
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get('success', False))

    print(f"Tests passed: {passed_tests}/{total_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")

    for test_name, result in results.items():
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        duration = result.get('duration', result.get('connection_time', 0))
        if duration:
            print(f"  {status} {test_name}: {duration:.2f}s")
        else:
            print(f"  {status} {test_name}: {result.get('error', 'Unknown error')}")

    # Save results to worklog update
    with open('phase1_results.json', 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'phase': 'Phase 1 Infrastructure Health',
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': passed_tests/total_tests*100,
            'results': results
        }, f, indent=2)

    print(f"\n📊 Results saved to phase1_results.json")

    # Determine next phase
    if passed_tests >= 2:  # At least basic connectivity working
        print("\n🚀 PHASE 1 PASSED - Proceeding to Phase 2: Critical Business Functions")
        return True
    else:
        print("\n🚨 PHASE 1 FAILED - Infrastructure issues detected, stopping for analysis")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_staging_connectivity())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)