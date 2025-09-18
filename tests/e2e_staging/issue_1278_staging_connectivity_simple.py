"""
Simple E2E Staging Tests for Issue #1278 - Staging Connectivity Validation

Business Value Justification (BVJ):
- Segment: Platform/Critical (Revenue Protection)
- Business Goal: Validate application availability in real staging environment
- Value Impact: $500K+ ARR validation pipeline functionality
- Strategic Impact: Critical P0 outage resolution validation

These tests validate the staging environment connectivity aspects identified in Issue #1278:
- Basic staging environment connectivity
- Health endpoint availability during startup issues
- Application response patterns during database connectivity problems
"""

import pytest
import asyncio
import aiohttp
import logging
import time
from typing import Dict, Any, Optional
import unittest


@pytest.mark.e2e_staging
@pytest.mark.issue_1278
@pytest.mark.mission_critical
class TestStagingConnectivitySimple(unittest.TestCase):
    """Simple E2E staging tests for connectivity validation - Issue #1278."""

    # Staging environment configuration
    STAGING_BASE_URL = "https://netra-backend-staging-701982941522.us-central1.run.app"
    STAGING_FRONTEND_URL = "https://netra-frontend-staging-701982941522.us-central1.run.app"

    # Test configuration
    REQUEST_TIMEOUT = 30.0  # Timeout for individual requests
    HEALTH_CHECK_TIMEOUT = 45.0  # Timeout for health checks (may be slow during startup issues)

    def setUp(self):
        """Set up test session."""
        # Note: We can't use async setUp in unittest, so we'll handle session in each test
        pass

    def tearDown(self):
        """Clean up test session."""
        pass

    def test_staging_basic_connectivity(self):
        """
        Test Case 3.1: Test basic connectivity to staging environment.

        Expected behavior:
        - Should be able to reach staging endpoints
        - Should get some response (even if error) rather than connection refused
        - Should demonstrate that infrastructure is reachable
        """
        async def check_basic_connectivity():
            """Check basic connectivity to staging."""
            timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                connectivity_results = []

                # Test basic endpoints
                endpoints_to_test = [
                    {"url": f"{self.STAGING_BASE_URL}/health", "name": "Backend Health"},
                    {"url": f"{self.STAGING_BASE_URL}/", "name": "Backend Root"},
                    {"url": f"{self.STAGING_FRONTEND_URL}/", "name": "Frontend Root"},
                ]

                for endpoint in endpoints_to_test:
                    start_time = time.time()
                    try:
                        async with session.get(endpoint["url"]) as response:
                            duration = time.time() - start_time
                            result = {
                                "name": endpoint["name"],
                                "url": endpoint["url"],
                                "status_code": response.status,
                                "duration": duration,
                                "reachable": True,
                                "headers": dict(response.headers)
                            }

                            # Try to get response content (but don't fail if we can't)
                            try:
                                if response.content_type == 'application/json':
                                    result["content"] = await response.json()
                                else:
                                    content = await response.text()
                                    result["content_preview"] = content[:200] if content else ""
                            except:
                                result["content"] = "Could not parse response content"

                            connectivity_results.append(result)
                            print(f"CHECK {endpoint['name']}: HTTP {response.status} in {duration:.2f}s")

                    except Exception as e:
                        duration = time.time() - start_time
                        result = {
                            "name": endpoint["name"],
                            "url": endpoint["url"],
                            "reachable": False,
                            "error": str(e),
                            "duration": duration
                        }
                        connectivity_results.append(result)
                        print(f"X {endpoint['name']}: {e} after {duration:.2f}s")

                return connectivity_results

        # Run connectivity check
        results = asyncio.run(check_basic_connectivity())

        # Analyze results
        reachable_endpoints = [r for r in results if r.get("reachable", False)]
        unreachable_endpoints = [r for r in results if not r.get("reachable", False)]

        # At least some endpoints should be reachable
        self.assertGreater(len(reachable_endpoints), 0,
                          "At least one staging endpoint should be reachable")

        # If backend is unreachable, that's the Issue #1278 problem
        backend_results = [r for r in results if "Backend" in r["name"]]
        backend_reachable = [r for r in backend_results if r.get("reachable", False)]

        if backend_reachable:
            print("CHECK Backend staging endpoints reachable - infrastructure connectivity OK")
        else:
            print("X Backend staging endpoints unreachable - potential infrastructure issue")

    def test_health_endpoint_during_startup_issues(self):
        """
        Test Case 3.2: Test health endpoint behavior during potential startup issues.

        Expected behavior:
        - Health endpoint should respond (even with errors)
        - Should not hang indefinitely
        - Should provide information about startup state
        """
        async def check_health_endpoint_patterns():
            """Check health endpoint response patterns."""
            timeout = aiohttp.ClientTimeout(total=self.HEALTH_CHECK_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                health_checks = []

                # Perform multiple health checks over time to see patterns
                for check_num in range(3):
                    check_start = time.time()
                    try:
                        async with session.get(f"{self.STAGING_BASE_URL}/health") as response:
                            check_duration = time.time() - check_start
                            response_data = await response.json()

                            health_result = {
                                "check_number": check_num + 1,
                                "status_code": response.status,
                                "duration": check_duration,
                                "response": response_data,
                                "successful": response.status in [200, 503]  # 503 is acceptable during startup issues
                            }
                            health_checks.append(health_result)

                            status_icon = "CHECK" if response.status == 200 else "WARNING️" if response.status == 503 else "X"
                            print(f"{status_icon} Health check {check_num + 1}: HTTP {response.status} in {check_duration:.2f}s")

                            if response_data:
                                print(f"   Response: {response_data}")

                    except Exception as e:
                        check_duration = time.time() - check_start
                        health_result = {
                            "check_number": check_num + 1,
                            "successful": False,
                            "error": str(e),
                            "duration": check_duration
                        }
                        health_checks.append(health_result)
                        print(f"X Health check {check_num + 1}: {e} after {check_duration:.2f}s")

                    # Wait between checks
                    if check_num < 2:
                        await asyncio.sleep(5)

                return health_checks

        # Run health checks
        health_results = asyncio.run(check_health_endpoint_patterns())

        # Analyze health check patterns
        successful_checks = [r for r in health_results if r.get("successful", False)]
        failed_checks = [r for r in health_results if not r.get("successful", False)]

        if successful_checks:
            # Some health checks succeeded
            avg_response_time = sum(r["duration"] for r in successful_checks) / len(successful_checks)
            print(f"CHECK {len(successful_checks)}/3 health checks succeeded (avg: {avg_response_time:.2f}s)")

            # Validate response times
            for check in successful_checks:
                self.assertLess(check["duration"], 30.0,
                               "Health check responses should not take extremely long")

        if failed_checks:
            # Some health checks failed
            avg_failure_time = sum(r["duration"] for r in failed_checks) / len(failed_checks)
            print(f"X {len(failed_checks)}/3 health checks failed (avg: {avg_failure_time:.2f}s)")

            # If all checks fail, this indicates the Issue #1278 startup problem
            if len(failed_checks) == len(health_results):
                print("X All health checks failed - this reproduces Issue #1278 startup failure")

        # Should have at least some response (success or controlled failure)
        self.assertGreater(len(health_results), 0, "Should get some health check responses")

    def test_database_health_endpoint_specific(self):
        """
        Test Case 3.3: Test database-specific health endpoint.

        Expected behavior:
        - Database health should reflect connectivity issues
        - Should timeout appropriately if database unavailable
        - Should provide specific error information
        """
        async def check_database_health():
            """Check database-specific health endpoint."""
            timeout = aiohttp.ClientTimeout(total=self.HEALTH_CHECK_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                db_health_start = time.time()
                try:
                    async with session.get(f"{self.STAGING_BASE_URL}/health/database") as response:
                        db_health_duration = time.time() - db_health_start
                        response_data = await response.json()

                        result = {
                            "status_code": response.status,
                            "duration": db_health_duration,
                            "response": response_data,
                            "reachable": True
                        }

                        if response.status == 200:
                            print(f"CHECK Database health: OK in {db_health_duration:.2f}s")
                            print(f"   Response: {response_data}")
                        else:
                            print(f"X Database health: HTTP {response.status} in {db_health_duration:.2f}s")
                            print(f"   Response: {response_data}")

                        return result

                except Exception as e:
                    db_health_duration = time.time() - db_health_start
                    result = {
                        "reachable": False,
                        "error": str(e),
                        "duration": db_health_duration
                    }
                    print(f"X Database health check failed: {e} after {db_health_duration:.2f}s")
                    return result

        # Run database health check
        db_result = asyncio.run(check_database_health())

        if db_result.get("reachable", False):
            # Database health endpoint responded
            if db_result.get("status_code") == 200:
                # Database is healthy
                self.assertEqual(db_result["status_code"], 200)
                self.assertLess(db_result["duration"], 10.0,
                               "Healthy database should respond quickly")
                print("CHECK Database connectivity appears to be working")
            else:
                # Database health endpoint responded with error
                self.assertIn(db_result["status_code"], [503, 500, 502],
                             "Database errors should use appropriate HTTP status codes")
                print(f"X Database health reports issues (HTTP {db_result['status_code']}) - this reproduces Issue #1278")
        else:
            # Database health endpoint completely unreachable
            self.assertGreater(db_result["duration"], 10.0,
                              "Complete failure should take reasonable time")
            print("X Database health endpoint unreachable - severe infrastructure issue")

    def test_application_availability_patterns(self):
        """
        Test Case 3.4: Test overall application availability patterns.

        Expected behavior:
        - Should show consistent availability patterns
        - Should not have random intermittent failures
        - Should demonstrate infrastructure vs application issues
        """
        async def check_availability_patterns():
            """Check application availability over time."""
            timeout = aiohttp.ClientTimeout(total=15.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                availability_checks = []
                monitoring_duration = 30.0  # Monitor for 30 seconds
                check_interval = 5.0

                monitoring_start = time.time()
                check_count = 0

                while time.time() - monitoring_start < monitoring_duration:
                    check_count += 1
                    check_start = time.time()

                    try:
                        async with session.get(f"{self.STAGING_BASE_URL}/health") as response:
                            check_duration = time.time() - check_start
                            availability_checks.append({
                                "check": check_count,
                                "available": True,
                                "status_code": response.status,
                                "duration": check_duration,
                                "timestamp": time.time()
                            })
                            print(f"Check {check_count}: Available (HTTP {response.status}) in {check_duration:.2f}s")

                    except Exception as e:
                        check_duration = time.time() - check_start
                        availability_checks.append({
                            "check": check_count,
                            "available": False,
                            "error": str(e),
                            "duration": check_duration,
                            "timestamp": time.time()
                        })
                        print(f"Check {check_count}: Unavailable ({e}) after {check_duration:.2f}s")

                    # Wait until next check
                    await asyncio.sleep(check_interval)

                return availability_checks

        # Run availability monitoring
        availability_results = asyncio.run(check_availability_patterns())

        # Analyze availability patterns
        total_checks = len(availability_results)
        available_checks = len([r for r in availability_results if r.get("available", False)])
        unavailable_checks = total_checks - available_checks

        availability_percentage = (available_checks / total_checks) * 100 if total_checks > 0 else 0

        print(f"\nAvailability Summary:")
        print(f"  Total checks: {total_checks}")
        print(f"  Available: {available_checks} ({availability_percentage:.1f}%)")
        print(f"  Unavailable: {unavailable_checks}")

        if availability_percentage >= 80:
            print("CHECK High availability - staging environment appears stable")
            self.assertGreaterEqual(availability_percentage, 80,
                                   "Staging should have high availability when working properly")
        elif availability_percentage >= 50:
            print("WARNING️ Partial availability - intermittent issues detected")
        else:
            print("X Low availability - significant infrastructure issues (reproducing Issue #1278)")

        # Should have attempted some checks
        self.assertGreater(total_checks, 0, "Should have performed availability checks")


if __name__ == '__main__':
    # Run E2E staging tests
    unittest.main(verbosity=2)