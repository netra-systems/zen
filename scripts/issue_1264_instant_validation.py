#!/usr/bin/env python3
"""
Issue #1264 Instant Validation Script

CRITICAL: Run this script immediately after the infrastructure team applies
the Cloud SQL PostgreSQL configuration fix.

This script provides instant validation of the fix without requiring
full test suite setup or complex dependencies.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Immediate fix validation
- Value Impact: Instant confirmation of infrastructure fix success
- Strategic Impact: Rapid Golden Path restoration validation

Usage:
    python scripts/issue_1264_instant_validation.py
"""

import asyncio
import time
import sys
import os
from pathlib import Path
from typing import Dict, Any, Tuple
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header():
    """Print validation header."""
    print("=" * 80)
    print("ISSUE #1264 INSTANT VALIDATION")
    print("=" * 80)
    print("Validating Cloud SQL PostgreSQL configuration fix")
    print("Expected: PASS once backend recovers; database configuration is already validated via asyncpg.")
    print("=" * 80)
    print()

def validate_environment() -> bool:
    """Validate environment is staging."""
    current_env = os.environ.get('ENVIRONMENT', 'development')

    if current_env.lower() != 'staging':
        print(f"❌ Environment Error: Not in staging environment")
        print(f"   Current: {current_env}")
        print(f"   Required: staging")
        print(f"   Set ENVIRONMENT=staging to run validation")
        return False

    print(f"✓ Environment validated: {current_env}")
    return True

async def test_database_connection() -> Tuple[bool, float, str]:
    """
    Test database connection with timeout monitoring.

    Returns:
        (success, connection_time, error_message)
    """
    try:
        # Import here to avoid dependency issues
        from shared.isolated_environment import IsolatedEnvironment
        from netra_backend.app.schemas.config import StagingConfig

        env = IsolatedEnvironment()
        config = StagingConfig()

        if not config.database_url:
            return False, 0.0, "No database URL configured"

        # Validate URL is PostgreSQL
        if not config.database_url.startswith('postgresql'):
            return False, 0.0, f"Database URL is not PostgreSQL: {config.database_url[:30]}..."

        print(f"Testing connection to: {config.database_url[:50]}...")

        # Test connection with asyncpg
        import asyncpg

        start_time = time.time()

        try:
            # Connection with 10 second timeout
            async with asyncio.timeout(10.0):
                conn = await asyncpg.connect(config.database_url)
                await conn.execute("SELECT 1")
                await conn.close()

            connection_time = time.time() - start_time
            return True, connection_time, "Connection successful"

        except asyncio.TimeoutError:
            connection_time = time.time() - start_time
            return False, connection_time, f"Connection timeout after {connection_time:.2f}s"

        except Exception as e:
            connection_time = time.time() - start_time
            return False, connection_time, f"Connection failed: {str(e)}"

    except ImportError as e:
        return False, 0.0, f"Import error: {str(e)} - run from project root with proper environment"

    except Exception as e:
        return False, 0.0, f"Validation error: {str(e)}"

async def test_health_endpoint() -> Tuple[bool, float, str]:
    """
    Test health endpoint accessibility.

    Returns:
        (success, response_time, error_message)
    """
    try:
        import aiohttp

        health_url = "https://api.staging.netrasystems.ai/health"
        print(f"Testing health endpoint: {health_url}")

        start_time = time.time()

        timeout = aiohttp.ClientTimeout(total=15.0)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(health_url) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        return True, response_time, "Health endpoint accessible"
                    else:
                        return False, response_time, f"Health endpoint returned {response.status}"

            except aiohttp.ClientError as e:
                response_time = time.time() - start_time
                return False, response_time, f"Health endpoint connection failed: {str(e)}"

    except ImportError:
        return False, 0.0, "aiohttp not available - skipping health endpoint test"

    except Exception as e:
        return False, 0.0, f"Health endpoint test error: {str(e)}"

async def test_websocket_connection() -> Tuple[bool, float, str]:
    """
    Test WebSocket connection establishment.

    Returns:
        (success, connection_time, error_message)
    """
    try:
        import websockets
        import ssl

        ws_url = "wss://api.staging.netrasystems.ai/ws"
        print(f"Testing WebSocket connection: {ws_url}")

        # Create SSL context for staging
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        start_time = time.time()

        try:
            async with asyncio.timeout(10.0):
                async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
                    connection_time = time.time() - start_time
                    await websocket.ping()
                    return True, connection_time, "WebSocket connection successful"

        except asyncio.TimeoutError:
            connection_time = time.time() - start_time
            return False, connection_time, "WebSocket connection timeout"

        except Exception as e:
            connection_time = time.time() - start_time
            return False, connection_time, f"WebSocket connection failed: {str(e)}"

    except ImportError:
        return False, 0.0, "websockets library not available - skipping WebSocket test"

    except Exception as e:
        return False, 0.0, f"WebSocket test error: {str(e)}"

async def run_instant_validation() -> Dict[str, Any]:
    """Run instant validation suite."""
    validation_start = time.time()

    print("Running instant validation tests...")
    print()

    # Test 1: Database Connection
    print("1. Testing database connectivity...")
    db_success, db_time, db_error = await test_database_connection()

    db_status = "✓" if db_success else "❌"
    print(f"   {db_status} Database: {db_time:.2f}s - {db_error}")

    if db_success and db_time > 8.0:
        print(f"   ⚠️  WARNING: Connection time {db_time:.2f}s exceeds 8s threshold")
        print(f"      This may indicate Issue #1264 is not fully resolved")

    print()

    # Test 2: Health Endpoint
    print("2. Testing health endpoint...")
    health_success, health_time, health_error = await test_health_endpoint()

    health_status = "✓" if health_success else "❌"
    print(f"   {health_status} Health: {health_time:.2f}s - {health_error}")
    print()

    # Test 3: WebSocket Connection
    print("3. Testing WebSocket connectivity...")
    ws_success, ws_time, ws_error = await test_websocket_connection()

    ws_status = "✓" if ws_success else "❌"
    print(f"   {ws_status} WebSocket: {ws_time:.2f}s - {ws_error}")
    print()

    # Overall Assessment
    total_time = time.time() - validation_start
    all_tests_passed = db_success and health_success and ws_success

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_validation_time": total_time,
        "database_connectivity": {
            "success": db_success,
            "connection_time": db_time,
            "error": db_error if not db_success else None
        },
        "health_endpoint": {
            "success": health_success,
            "response_time": health_time,
            "error": health_error if not health_success else None
        },
        "websocket_connectivity": {
            "success": ws_success,
            "connection_time": ws_time,
            "error": ws_error if not ws_success else None
        },
        "overall_success": all_tests_passed,
        "issue_1264_resolved": all_tests_passed and db_time < 8.0,
        "issue_1264_indicators": []
    }

    # Check for Issue #1264 indicators
    if not db_success:
        results["issue_1264_indicators"].append("Database connection failed - possible configuration issue")

    if db_time > 8.0:
        results["issue_1264_indicators"].append(f"Database connection time {db_time:.2f}s exceeds 8s threshold")

    if not health_success:
        results["issue_1264_indicators"].append("Health endpoint not accessible - backend likely not starting")

    if not ws_success:
        results["issue_1264_indicators"].append("WebSocket connection failed - backend not fully operational")

    return results

def print_results(results: Dict[str, Any]) -> None:
    """Print validation results."""
    print("=" * 80)
    print("INSTANT VALIDATION RESULTS")
    print("=" * 80)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Total Time: {results['total_validation_time']:.2f}s")
    print()

    # Individual test results
    db_result = results['database_connectivity']
    print(f"Database Connectivity: {'✓ PASS' if db_result['success'] else '❌ FAIL'}")
    print(f"  Connection Time: {db_result['connection_time']:.2f}s")
    if db_result['error']:
        print(f"  Error: {db_result['error']}")

    health_result = results['health_endpoint']
    print(f"Health Endpoint: {'✓ PASS' if health_result['success'] else '❌ FAIL'}")
    print(f"  Response Time: {health_result['response_time']:.2f}s")
    if health_result['error']:
        print(f"  Error: {health_result['error']}")

    ws_result = results['websocket_connectivity']
    print(f"WebSocket Connectivity: {'✓ PASS' if ws_result['success'] else '❌ FAIL'}")
    print(f"  Connection Time: {ws_result['connection_time']:.2f}s")
    if ws_result['error']:
        print(f"  Error: {ws_result['error']}")

    print()

    # Overall assessment
    if results['overall_success']:
        print("🎉 SUCCESS: All validation tests passed!")
        if results['issue_1264_resolved']:
            print("✓ Issue #1264 appears to be RESOLVED")
    if results['overall_success']:
        print('SUCCESS: All validation tests passed.')
        if results['issue_1264_resolved']:
            print('  Issue #1264 appears resolved; database connection times are within acceptable range.')
            print('  All infrastructure components are operational.')
        else:
            print('  Partial success - some Issue #1264 indicators remain.')
    else:
        print('VALIDATION FAILED: Some tests did not pass.')
        if results['database_connectivity']['success'] and not results['health_endpoint']['success']:
            print('  Database connectivity succeeded but health endpoint is down -> investigate backend deployment (Issue #1263).')
        else:
            print('  Issue #1264 may not be fully resolved.')

    # Issue #1264 indicators
    if results['issue_1264_indicators']:
        print()
        print("Issue #1264 Indicators:")
        for indicator in results['issue_1264_indicators']:
            print(f"  - {indicator}")

    print()
    print("=" * 80)

async def main():
    """Main validation function."""
    print_header()

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    print()

    try:
        # Run validation
        results = await run_instant_validation()

        # Print results
        print_results(results)

        # Save results
        results_file = "issue_1264_instant_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to: {results_file}")

        # Exit with appropriate code
        if results['overall_success']:
            print()
            print("🎉 VALIDATION SUCCESSFUL - Issue #1264 appears resolved!")
            sys.exit(0)
        else:
            print()
            print("❌ VALIDATION FAILED - Issue #1264 may not be resolved")
            print("   Infrastructure team may need to apply additional fixes")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Validation interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n💥 VALIDATION ERROR: {e}")
        print("   Check environment setup and network connectivity")
        sys.exit(1)

if __name__ == "__main__":
    # Set staging environment
    os.environ['ENVIRONMENT'] = 'staging'

    # Run validation
    asyncio.run(main())
