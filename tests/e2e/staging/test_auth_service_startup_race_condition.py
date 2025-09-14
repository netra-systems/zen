"""
E2E Staging Test for Auth Service Startup Race Condition (Issue #926)

This test reproduces the race condition in a real staging environment
where the auth service fails to initialize properly under load or
during rapid startup/restart cycles.

Test Coverage:
- Auth service startup in real staging environment
- Health check endpoints during startup race conditions
- OAuth initialization timing issues
- Database connectivity during concurrent requests
- Real service integration during startup

Expected Behavior:
- Tests should FAIL initially, reproducing the production race condition
- Demonstrates actual service unavailability during startup
- Shows real-world impact of auth_service initialization failures
"""

import pytest
import asyncio
import logging
import time
import sys
import httpx
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestAuthServiceStartupRaceConditionE2E(SSotAsyncTestCase):
    """E2E staging tests for Auth Service startup race condition scenarios"""
    
    def setUp(self):
        """Setup for E2E staging race condition testing"""
        super().setUp()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.staging_auth_url = self._get_staging_auth_url()
        self.request_timeout = 10.0
        self.race_condition_results = []
        
    def _get_staging_auth_url(self) -> str:
        """Get staging auth service URL from environment"""
        # Try common staging URL patterns
        staging_urls = [
            get_env().get("AUTH_SERVICE_STAGING_URL"),
            get_env().get("STAGING_AUTH_URL"),
            "https://auth.staging.netrasystems.ai",
            "https://auth-staging.run.app",
            "http://localhost:8081"  # Local staging fallback
        ]
        
        for url in staging_urls:
            if url:
                return url.rstrip('/')
        
        # Default fallback
        return "https://auth.staging.netrasystems.ai"

    async def test_staging_auth_service_health_during_startup_race(self):
        """
        Test auth service health checks during startup in real staging environment
        Reproduces the race condition where health checks fail during initialization
        """
        # This test should FAIL initially - reproducing the real staging race condition
        
        async def check_auth_health_endpoint():
            """Check auth service health endpoint during startup"""
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                try:
                    # Test the main health endpoint
                    health_response = await client.get(f"{self.staging_auth_url}/health")
                    
                    if health_response.status_code == 200:
                        health_data = health_response.json()
                        return {
                            "success": True,
                            "status": health_data.get("status"),
                            "service": health_data.get("service"),
                            "response_time": health_response.elapsed.total_seconds()
                        }
                    elif health_response.status_code == 503:
                        # Service unavailable - likely race condition
                        error_data = health_response.json() if health_response.text else {}
                        return {
                            "success": False,
                            "error": "Service unavailable during startup",
                            "status_code": 503,
                            "details": error_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Unexpected status code: {health_response.status_code}",
                            "status_code": health_response.status_code
                        }
                        
                except httpx.TimeoutException:
                    return {"success": False, "error": "Health check timeout - service not responding"}
                except httpx.ConnectError:
                    return {"success": False, "error": "Connection failed - service may be starting up"}
                except Exception as e:
                    return {"success": False, "error": f"Health check failed: {str(e)}"}
        
        async def check_auth_specific_health():
            """Check the auth-specific health endpoint"""
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                try:
                    # Test /health/auth endpoint that checks auth_service specifically
                    auth_health_response = await client.get(f"{self.staging_auth_url}/health/auth")
                    
                    if auth_health_response.status_code == 200:
                        auth_data = auth_health_response.json()
                        return {
                            "success": True,
                            "golden_path_ready": auth_data.get("golden_path_ready"),
                            "capabilities": auth_data.get("capabilities"),
                            "response_time": auth_health_response.elapsed.total_seconds()
                        }
                    elif auth_health_response.status_code == 503:
                        # Auth service race condition - capabilities not ready
                        error_data = auth_health_response.json() if auth_health_response.text else {}
                        return {
                            "success": False,
                            "error": "Auth capabilities not ready during startup",
                            "status_code": 503,
                            "details": error_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Auth health unexpected status: {auth_health_response.status_code}",
                            "status_code": auth_health_response.status_code
                        }
                        
                except Exception as e:
                    return {"success": False, "error": f"Auth health check failed: {str(e)}"}
        
        # Run concurrent health checks to trigger race condition
        health_check_results = []
        
        # Run multiple rounds of concurrent health checks
        for round_num in range(5):
            # Start multiple concurrent health checks
            concurrent_tasks = []
            for i in range(8):
                if i % 2 == 0:
                    task = asyncio.create_task(check_auth_health_endpoint())
                else:
                    task = asyncio.create_task(check_auth_specific_health())
                concurrent_tasks.append(task)
            
            # Wait for all concurrent health checks
            round_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            for result in round_results:
                if isinstance(result, Exception):
                    health_check_results.append({"success": False, "error": str(result)})
                else:
                    health_check_results.append(result)
            
            # Small delay between rounds
            await asyncio.sleep(0.1)
        
        # Analyze health check race condition results
        failed_health_checks = [r for r in health_check_results if not r["success"]]
        unavailable_during_startup = [r for r in failed_health_checks 
                                    if "unavailable during startup" in r.get("error", "")]
        capabilities_not_ready = [r for r in failed_health_checks
                                if "capabilities not ready" in r.get("error", "")]
        timeout_failures = [r for r in failed_health_checks
                          if "timeout" in r.get("error", "").lower()]
        
        total_race_failures = len(unavailable_during_startup) + len(capabilities_not_ready)
        
        # Log race condition evidence
        self.logger.error(f"Staging health check race condition results:")
        self.logger.error(f"  Total health checks: {len(health_check_results)}")
        self.logger.error(f"  Failed health checks: {len(failed_health_checks)}")
        self.logger.error(f"  Race condition failures: {total_race_failures}")
        self.logger.error(f"  Service unavailable: {len(unavailable_during_startup)}")
        self.logger.error(f"  Capabilities not ready: {len(capabilities_not_ready)}")
        self.logger.error(f"  Timeout failures: {len(timeout_failures)}")
        
        # Expected: Should FAIL initially due to race condition in staging
        self.assertGreater(total_race_failures, 0,
                         f"Expected auth service startup race condition failures in staging. "
                         f"Got {total_race_failures} race condition failures out of {len(health_check_results)} checks.")
        
        # This should FAIL initially, confirming staging race condition
        self.fail(f"Staging auth service startup race condition reproduced: "
                 f"{total_race_failures} failures where auth service was not ready. "
                 f"This confirms Issue #926 affects real staging environment.")

    async def test_staging_oauth_initialization_race_condition(self):
        """
        Test OAuth initialization race condition in staging environment
        Reproduces OAuth provider not being ready during rapid service restarts
        """
        # This test should FAIL initially
        
        async def check_oauth_status():
            """Check OAuth provider status during startup"""
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                try:
                    oauth_response = await client.get(f"{self.staging_auth_url}/oauth/status")
                    
                    if oauth_response.status_code == 200:
                        oauth_data = oauth_response.json()
                        return {
                            "success": True,
                            "oauth_healthy": oauth_data.get("oauth_healthy"),
                            "available_providers": oauth_data.get("available_providers", []),
                            "google_status": oauth_data.get("oauth_providers", {}).get("google", {})
                        }
                    elif oauth_response.status_code == 503:
                        # OAuth not ready - race condition
                        error_data = oauth_response.json() if oauth_response.text else {}
                        return {
                            "success": False,
                            "error": "OAuth providers not ready during startup",
                            "status_code": 503,
                            "details": error_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"OAuth status unexpected response: {oauth_response.status_code}",
                            "status_code": oauth_response.status_code
                        }
                        
                except Exception as e:
                    return {"success": False, "error": f"OAuth status check failed: {str(e)}"}
        
        async def attempt_oauth_login_redirect():
            """Attempt to get OAuth login redirect URL"""
            async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=False) as client:
                try:
                    # Try to access Google OAuth login endpoint
                    oauth_url = f"{self.staging_auth_url}/auth/google"
                    response = await client.get(oauth_url)
                    
                    if response.status_code in [302, 307]:
                        # Successful redirect to Google OAuth
                        return {"success": True, "redirect_url": response.headers.get("location")}
                    elif response.status_code == 503:
                        # OAuth not configured/ready
                        return {"success": False, "error": "OAuth not ready for login redirect"}
                    else:
                        return {
                            "success": False, 
                            "error": f"Unexpected OAuth response: {response.status_code}"
                        }
                        
                except Exception as e:
                    return {"success": False, "error": f"OAuth login redirect failed: {str(e)}"}
        
        # Run concurrent OAuth status and login attempts
        oauth_results = []
        
        # Multiple rounds of concurrent OAuth operations
        for round_num in range(4):
            concurrent_tasks = []
            
            # Mix of OAuth status checks and login attempts
            for i in range(6):
                if i % 2 == 0:
                    task = asyncio.create_task(check_oauth_status())
                else:
                    task = asyncio.create_task(attempt_oauth_login_redirect())
                concurrent_tasks.append(task)
            
            round_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            for result in round_results:
                if isinstance(result, Exception):
                    oauth_results.append({"success": False, "error": str(result)})
                else:
                    oauth_results.append(result)
            
            await asyncio.sleep(0.05)
        
        # Analyze OAuth race condition results
        oauth_failures = [r for r in oauth_results if not r["success"]]
        oauth_not_ready = [r for r in oauth_failures 
                          if "not ready" in r.get("error", "")]
        oauth_config_failures = [r for r in oauth_failures
                               if "not configured" in r.get("error", "")]
        
        total_oauth_race_failures = len(oauth_not_ready) + len(oauth_config_failures)
        
        # Log OAuth race condition evidence
        self.logger.error(f"Staging OAuth race condition results:")
        self.logger.error(f"  Total OAuth operations: {len(oauth_results)}")
        self.logger.error(f"  OAuth failures: {len(oauth_failures)}")
        self.logger.error(f"  OAuth not ready: {len(oauth_not_ready)}")
        self.logger.error(f"  OAuth config failures: {len(oauth_config_failures)}")
        
        # Expected: Should FAIL initially due to OAuth race condition
        self.assertGreater(total_oauth_race_failures, 0,
                         f"Expected OAuth initialization race condition failures in staging. "
                         f"Got {total_oauth_race_failures} failures out of {len(oauth_results)} operations.")
        
        # This should FAIL initially
        self.fail(f"Staging OAuth initialization race condition reproduced: "
                 f"{total_oauth_race_failures} failures where OAuth was not ready. "
                 f"This confirms OAuth providers are not available during auth service startup.")

    async def test_staging_database_connectivity_during_startup_race(self):
        """
        Test database connectivity race condition during auth service startup in staging
        Reproduces database readiness check failures during initialization
        """
        # This test should FAIL initially
        
        async def check_readiness_endpoint():
            """Check readiness endpoint that validates database connectivity"""
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                try:
                    readiness_response = await client.get(f"{self.staging_auth_url}/health/ready")
                    
                    if readiness_response.status_code == 200:
                        ready_data = readiness_response.json()
                        return {
                            "success": True,
                            "status": ready_data.get("status"),
                            "database_status": ready_data.get("database_status"),
                            "environment": ready_data.get("environment")
                        }
                    elif readiness_response.status_code == 503:
                        # Not ready - likely database race condition
                        not_ready_data = readiness_response.json() if readiness_response.text else {}
                        return {
                            "success": False,
                            "error": "Service not ready - database connectivity failed",
                            "status_code": 503,
                            "reason": not_ready_data.get("reason"),
                            "details": not_ready_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Readiness check unexpected status: {readiness_response.status_code}",
                            "status_code": readiness_response.status_code
                        }
                        
                except Exception as e:
                    return {"success": False, "error": f"Readiness check failed: {str(e)}"}
        
        async def stress_test_concurrent_requests():
            """Stress test with concurrent requests during potential startup"""
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                try:
                    # Make rapid concurrent requests to stress auth service
                    response = await client.get(f"{self.staging_auth_url}/auth/status")
                    
                    if response.status_code == 200:
                        return {"success": True, "response_time": response.elapsed.total_seconds()}
                    else:
                        return {
                            "success": False,
                            "error": f"Auth status failed: {response.status_code}",
                            "status_code": response.status_code
                        }
                        
                except Exception as e:
                    return {"success": False, "error": f"Stress request failed: {str(e)}"}
        
        # Run high-concurrency readiness checks to trigger database race conditions
        readiness_results = []
        
        # Execute multiple rounds of high-concurrency checks
        for round_num in range(3):
            concurrent_tasks = []
            
            # Mix readiness checks with stress requests
            for i in range(12):
                if i % 3 == 0:
                    task = asyncio.create_task(check_readiness_endpoint())
                else:
                    task = asyncio.create_task(stress_test_concurrent_requests())
                concurrent_tasks.append(task)
            
            # Execute all tasks concurrently
            round_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            for result in round_results:
                if isinstance(result, Exception):
                    readiness_results.append({"success": False, "error": str(result)})
                else:
                    readiness_results.append(result)
            
            # Brief pause between rounds
            await asyncio.sleep(0.2)
        
        # Analyze database connectivity race conditions
        readiness_failures = [r for r in readiness_results if not r["success"]]
        db_connectivity_failures = [r for r in readiness_failures
                                  if "database connectivity failed" in r.get("error", "")]
        not_ready_failures = [r for r in readiness_failures
                            if r.get("status_code") == 503]
        
        # Look for specific database-related failures
        db_race_failures = len(db_connectivity_failures) + len(not_ready_failures)
        
        # Log database race condition evidence
        self.logger.error(f"Staging database connectivity race condition results:")
        self.logger.error(f"  Total readiness checks: {len(readiness_results)}")
        self.logger.error(f"  Readiness failures: {len(readiness_failures)}")
        self.logger.error(f"  Database connectivity failures: {len(db_connectivity_failures)}")
        self.logger.error(f"  Service not ready (503): {len(not_ready_failures)}")
        
        # Show sample failure details
        for failure in db_connectivity_failures[:2]:
            if "reason" in failure:
                self.logger.error(f"  Database failure reason: {failure['reason']}")
        
        # Expected: Should FAIL initially due to database race condition
        self.assertGreater(db_race_failures, 0,
                         f"Expected database connectivity race condition failures in staging. "
                         f"Got {db_race_failures} database-related failures out of {len(readiness_results)} checks.")
        
        # This should FAIL initially
        self.fail(f"Staging database connectivity race condition reproduced: "
                 f"{db_race_failures} failures where database was not ready during startup. "
                 f"This confirms database initialization race conditions affect staging.")

    def tearDown(self):
        """Clean up after E2E staging tests"""
        super().tearDown()
        
        # Log final race condition summary
        if self.race_condition_results:
            self.logger.info(f"Total race condition scenarios tested: {len(self.race_condition_results)}")
            
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_staging_full_startup_race_condition_reproduction(self):
        """
        Comprehensive E2E test reproducing the full startup race condition scenario
        in staging environment - combines all race condition patterns
        """
        # This test should FAIL initially - comprehensive race condition reproduction
        
        startup_race_results = {
            "health_checks": [],
            "oauth_operations": [],
            "database_readiness": [],
            "concurrent_requests": []
        }
        
        async def comprehensive_health_monitoring():
            """Monitor all health endpoints concurrently"""
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                endpoints = [
                    "/health",
                    "/health/auth", 
                    "/health/ready",
                    "/oauth/status",
                    "/auth/status"
                ]
                
                endpoint_results = {}
                for endpoint in endpoints:
                    try:
                        response = await client.get(f"{self.staging_auth_url}{endpoint}")
                        endpoint_results[endpoint] = {
                            "status_code": response.status_code,
                            "success": response.status_code in [200, 201],
                            "response_time": response.elapsed.total_seconds(),
                            "data": response.json() if response.text else {}
                        }
                    except Exception as e:
                        endpoint_results[endpoint] = {
                            "success": False,
                            "error": str(e)
                        }
                
                return endpoint_results
        
        # Execute comprehensive monitoring across multiple rounds
        for round_num in range(3):
            self.logger.info(f"Starting comprehensive race condition test round {round_num + 1}")
            
            # Launch concurrent comprehensive health monitoring
            concurrent_monitors = []
            for i in range(5):
                task = asyncio.create_task(comprehensive_health_monitoring())
                concurrent_monitors.append(task)
            
            # Wait for all monitoring tasks
            round_results = await asyncio.gather(*concurrent_monitors, return_exceptions=True)
            
            # Process results for each monitoring round
            for monitor_result in round_results:
                if isinstance(monitor_result, Exception):
                    startup_race_results["concurrent_requests"].append({
                        "success": False,
                        "error": str(monitor_result)
                    })
                else:
                    # Process each endpoint result
                    for endpoint, result in monitor_result.items():
                        if endpoint in ["/health", "/health/auth"]:
                            startup_race_results["health_checks"].append(result)
                        elif endpoint == "/oauth/status":
                            startup_race_results["oauth_operations"].append(result)
                        elif endpoint == "/health/ready":
                            startup_race_results["database_readiness"].append(result)
                        else:
                            startup_race_results["concurrent_requests"].append(result)
            
            # Pause between rounds
            await asyncio.sleep(0.3)
        
        # Comprehensive analysis of all race condition patterns
        total_operations = sum(len(results) for results in startup_race_results.values())
        
        # Count failures by category
        health_failures = len([r for r in startup_race_results["health_checks"] if not r.get("success", True)])
        oauth_failures = len([r for r in startup_race_results["oauth_operations"] if not r.get("success", True)])
        db_failures = len([r for r in startup_race_results["database_readiness"] if not r.get("success", True)])
        request_failures = len([r for r in startup_race_results["concurrent_requests"] if not r.get("success", True)])
        
        total_failures = health_failures + oauth_failures + db_failures + request_failures
        
        # Identify specific race condition indicators
        service_unavailable = len([r for results in startup_race_results.values() 
                                 for r in results if r.get("status_code") == 503])
        
        # Log comprehensive race condition analysis
        self.logger.error(f"Comprehensive startup race condition analysis:")
        self.logger.error(f"  Total operations: {total_operations}")
        self.logger.error(f"  Total failures: {total_failures}")
        self.logger.error(f"  Health check failures: {health_failures}")
        self.logger.error(f"  OAuth failures: {oauth_failures}")
        self.logger.error(f"  Database readiness failures: {db_failures}")
        self.logger.error(f"  Concurrent request failures: {request_failures}")
        self.logger.error(f"  Service unavailable (503) responses: {service_unavailable}")
        
        # Store results for tearDown logging
        self.race_condition_results = startup_race_results
        
        # Expected: Should FAIL initially with comprehensive race condition evidence
        self.assertGreater(total_failures, 0,
                         f"Expected comprehensive startup race condition failures in staging. "
                         f"Got {total_failures} failures out of {total_operations} operations.")
        
        # This should FAIL initially - comprehensive race condition proof
        self.fail(f"Comprehensive staging startup race condition reproduced: "
                 f"{total_failures} total failures across all auth service components. "
                 f"Service unavailable responses: {service_unavailable}. "
                 f"This provides comprehensive evidence that Issue #926 affects staging environment "
                 f"with race conditions in health checks, OAuth, database connectivity, and concurrent requests.")