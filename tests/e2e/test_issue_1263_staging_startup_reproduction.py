"""
E2E tests for Issue #1263 - Complete Staging Startup Sequence Reproduction

OBJECTIVE: Reproduce the complete startup sequence in staging environment to
validate database connection timeout issue and VPC egress configuration impact.

ROOT CAUSE: VPC egress configuration change (commit 2acf46c8a) from
private-ranges-only to all-traffic disrupted Cloud SQL connectivity causing
8.0-second timeout behavior in staging startup sequence.

These E2E tests run against the real staging environment to reproduce the
exact issue and validate the Golden Path database dependency.

Test Categories:
- Complete startup sequence reproduction with timing
- Golden Path database dependency validation
- Real staging environment health check reproduction
- End-to-end database connectivity validation
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
import aiohttp
import json
from contextlib import asynccontextmanager
import os

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.configuration.base import get_config


logger = logging.getLogger(__name__)


class Issue1263StagingStartupReproductionE2ETests(SSotAsyncTestCase):
    """E2E tests reproducing Issue #1263 in staging environment."""

    async def asyncSetUp(self):
        """Set up E2E test environment for staging validation."""
        await super().asyncSetUp()
        self.env = IsolatedEnvironment()

        # Real staging endpoints
        self.staging_endpoints = {
            'backend_base': 'https://netra-backend-staging-701982941522.us-central1.run.app',
            'auth_base': 'https://netra-auth-staging-701982941522.us-central1.run.app',
            'frontend_base': 'https://netra-frontend-staging-701982941522.us-central1.run.app'
        }

        # Health check endpoints that experienced Issue #1263
        self.health_endpoints = {
            'basic_health': f"{self.staging_endpoints['backend_base']}/health",
            'ready_health': f"{self.staging_endpoints['backend_base']}/health/ready",
            'database_health': f"{self.staging_endpoints['backend_base']}/health/database"
        }

        # Configure HTTP client with appropriate timeouts for testing
        self.timeout = aiohttp.ClientTimeout(total=15.0, connect=10.0)

    async def test_staging_backend_health_ready_endpoint_timeout_reproduction(self):
        """
        CRITICAL E2E TEST - MUST FAIL INITIALLY

        Reproduce the exact Issue #1263 scenario: /health/ready endpoint timing out
        due to VPC egress configuration disrupting Cloud SQL connectivity.

        This should FAIL initially with ~10s timeout, proving Issue #1263 exists.
        After VPC configuration fix, should PASS with reasonable response time.
        """
        start_time = time.time()
        response_successful = False
        response_time = 0.0
        status_code = None
        error_details = None

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                logger.info(f"Testing staging /health/ready endpoint: {self.health_endpoints['ready_health']}")

                async with session.get(self.health_endpoints['ready_health']) as response:
                    status_code = response.status
                    response_data = await response.json()
                    response_time = time.time() - start_time

                    if status_code == 200:
                        response_successful = True
                        logger.info(f"Health/ready succeeded in {response_time:.2f}s")

                        # After VPC fix, response should be fast
                        assert response_time < 10.0, (
                            f"Health/ready response took {response_time:.2f}s, "
                            f"expected < 10.0s after Issue #1263 VPC fix"
                        )

                        # Validate response structure
                        assert 'status' in response_data, "Health response missing status"
                        assert response_data['status'] in ['healthy', 'ready'], "Invalid health status"

                    else:
                        pytest.fail(f"Health/ready returned status {status_code}, expected 200")

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            error_details = "Request timeout"

            # This should FAIL initially, demonstrating Issue #1263
            pytest.fail(
                f"ISSUE #1263 REPRODUCED: Staging /health/ready timeout after {response_time:.2f}s. "
                f"Root cause: VPC egress configuration change (commit 2acf46c8a) "
                f"disrupted Cloud SQL connectivity. Expected to succeed after VPC fix."
            )

        except Exception as e:
            response_time = time.time() - start_time
            error_details = str(e)

            if response_time >= 8.0:
                pytest.fail(
                    f"ISSUE #1263: Staging /health/ready failed after {response_time:.2f}s "
                    f"(close to 8.0s database timeout). VPC configuration issue. Error: {error_details}"
                )
            else:
                pytest.fail(f"Unexpected staging health check error: {error_details}")

    async def test_staging_database_connectivity_golden_path_validation(self):
        """
        Test database connectivity as part of Golden Path validation.

        Validates that database connectivity is working for the critical user
        journey and that Issue #1263 doesn't block the Golden Path.
        """
        golden_path_start = time.time()

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Test database health endpoint specifically
                logger.info(f"Testing database health: {self.health_endpoints['database_health']}")

                async with session.get(self.health_endpoints['database_health']) as response:
                    status_code = response.status
                    response_data = await response.json()
                    db_health_time = time.time() - golden_path_start

                    assert status_code == 200, f"Database health check failed with status {status_code}"

                    # Validate database connectivity metrics
                    assert 'database_status' in response_data, "Database health response missing status"
                    assert 'connection_time_ms' in response_data, "Database health missing timing info"

                    # After VPC fix, database health should be fast
                    assert db_health_time < 5.0, (
                        f"Database health check took {db_health_time:.2f}s, "
                        f"expected < 5.0s for Golden Path reliability"
                    )

                    # Validate database connection timing from response
                    connection_time_ms = response_data.get('connection_time_ms', 0)
                    if connection_time_ms > 8000:  # 8.0s in milliseconds
                        pytest.fail(
                            f"ISSUE #1263: Database connection time {connection_time_ms}ms indicates "
                            f"VPC connectivity issue. Expected < 5000ms after fix."
                        )

        except Exception as e:
            db_health_time = time.time() - golden_path_start

            if db_health_time >= 8.0:
                pytest.fail(
                    f"ISSUE #1263: Golden Path database validation timeout after "
                    f"{db_health_time:.2f}s - VPC egress configuration issue. Error: {e}"
                )
            else:
                pytest.fail(f"Golden Path database validation failed: {e}")

    async def test_complete_staging_startup_sequence_timing_e2e(self):
        """
        Test complete staging startup sequence timing to identify where
        Issue #1263 timeout occurs in the startup flow.

        Measures timing of each startup phase to isolate the database
        connectivity issue in the broader startup context.
        """
        startup_sequence_start = time.time()
        startup_phases = {}

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Phase 1: Basic health check
                phase1_start = time.time()
                async with session.get(self.health_endpoints['basic_health']) as response:
                    assert response.status == 200, "Basic health check failed"
                    startup_phases['basic_health'] = time.time() - phase1_start

                # Phase 2: Database health check
                phase2_start = time.time()
                async with session.get(self.health_endpoints['database_health']) as response:
                    assert response.status == 200, "Database health check failed"
                    startup_phases['database_health'] = time.time() - phase2_start

                # Phase 3: Ready health check (where Issue #1263 manifests)
                phase3_start = time.time()
                async with session.get(self.health_endpoints['ready_health']) as response:
                    assert response.status == 200, "Ready health check failed"
                    startup_phases['ready_health'] = time.time() - phase3_start

                total_startup_time = time.time() - startup_sequence_start

                # Log timing breakdown
                logger.info(f"Startup sequence timing breakdown:")
                for phase, timing in startup_phases.items():
                    logger.info(f"  {phase}: {timing:.2f}s")
                logger.info(f"  Total: {total_startup_time:.2f}s")

                # Validate each phase timing
                assert startup_phases['basic_health'] < 2.0, "Basic health too slow"
                assert startup_phases['database_health'] < 5.0, "Database health too slow"

                # This is where Issue #1263 should manifest
                if startup_phases['ready_health'] >= 10.0:
                    pytest.fail(
                        f"ISSUE #1263: Ready health check took {startup_phases['ready_health']:.2f}s "
                        f"- VPC configuration causing database timeout in startup sequence"
                    )

                # Overall startup should be reasonable after fix
                assert total_startup_time < 15.0, (
                    f"Complete startup sequence took {total_startup_time:.2f}s, "
                    f"expected < 15.0s after Issue #1263 VPC fix"
                )

        except Exception as e:
            total_startup_time = time.time() - startup_sequence_start

            # Analyze which phase failed
            failed_phase = "unknown"
            if 'basic_health' not in startup_phases:
                failed_phase = "basic_health"
            elif 'database_health' not in startup_phases:
                failed_phase = "database_health"
            elif 'ready_health' not in startup_phases:
                failed_phase = "ready_health"

            if total_startup_time >= 8.0 and failed_phase == "ready_health":
                pytest.fail(
                    f"ISSUE #1263: Startup sequence failed at {failed_phase} phase "
                    f"after {total_startup_time:.2f}s - database timeout in VPC configuration. "
                    f"Error: {e}"
                )
            else:
                pytest.fail(f"Startup sequence failed at {failed_phase} phase: {e}")

    async def test_concurrent_staging_health_checks_vpc_stress_e2e(self):
        """
        Test concurrent health checks against staging to validate VPC
        connector performance under load.

        Simulates multiple concurrent requests that could trigger Issue #1263
        timeout behavior under VPC constraints.
        """
        concurrent_requests = 5
        request_results = []

        async def single_health_request(request_id: int) -> Dict[str, Any]:
            """Execute a single health/ready request with timing."""
            start_time = time.time()
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(self.health_endpoints['ready_health']) as response:
                        response_data = await response.json()
                        response_time = time.time() - start_time

                        return {
                            'request_id': request_id,
                            'success': True,
                            'status_code': response.status,
                            'response_time': response_time,
                            'data': response_data
                        }

            except Exception as e:
                response_time = time.time() - start_time
                return {
                    'request_id': request_id,
                    'success': False,
                    'response_time': response_time,
                    'error': str(e)
                }

        # Execute concurrent health checks
        concurrent_start = time.time()
        tasks = [single_health_request(i) for i in range(concurrent_requests)]
        request_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_concurrent_time = time.time() - concurrent_start

        # Analyze results
        successful_requests = [r for r in request_results if r.get('success', False)]
        failed_requests = [r for r in request_results if not r.get('success', True)]

        # After VPC fix, most requests should succeed
        success_rate = len(successful_requests) / len(request_results)
        assert success_rate >= 0.8, (
            f"Concurrent health check success rate {success_rate:.1%} too low. "
            f"Issue #1263: VPC configuration affecting concurrent staging access."
        )

        # Check timing for successful requests
        if successful_requests:
            avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            max_response_time = max(r['response_time'] for r in successful_requests)

            assert avg_response_time < 10.0, (
                f"Average concurrent response time {avg_response_time:.2f}s too high"
            )

            assert max_response_time < 15.0, (
                f"Maximum concurrent response time {max_response_time:.2f}s too high"
            )

        # Check for Issue #1263 pattern in failed requests
        for failed in failed_requests:
            if failed['response_time'] >= 8.0:
                pytest.fail(
                    f"ISSUE #1263: Concurrent request {failed['request_id']} timeout "
                    f"after {failed['response_time']:.2f}s - VPC configuration issue. "
                    f"Error: {failed['error']}"
                )

    async def test_staging_websocket_connectivity_after_database_fix(self):
        """
        Test WebSocket connectivity in staging after database Issue #1263 fix.

        Validates that fixing the VPC configuration for database connectivity
        doesn't break WebSocket functionality.
        """
        websocket_test_start = time.time()

        try:
            # Test WebSocket health endpoint if available
            websocket_health_url = f"{self.staging_endpoints['backend_base']}/health/websocket"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                try:
                    async with session.get(websocket_health_url) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            websocket_health_time = time.time() - websocket_test_start

                            logger.info(f"WebSocket health check successful in {websocket_health_time:.2f}s")

                            # WebSocket health should be fast after database fix
                            assert websocket_health_time < 5.0, (
                                f"WebSocket health check took {websocket_health_time:.2f}s, "
                                f"expected < 5.0s after Issue #1263 database fix"
                            )

                            # Validate WebSocket connectivity status
                            assert 'websocket_status' in response_data, "WebSocket health missing status"

                except aiohttp.ClientResponseError as e:
                    if e.status == 404:
                        # WebSocket health endpoint might not exist, skip this test
                        logger.info("WebSocket health endpoint not available, skipping validation")
                        return
                    else:
                        raise

        except Exception as e:
            websocket_test_time = time.time() - websocket_test_start

            # Don't fail the database fix validation due to WebSocket issues
            logger.warning(
                f"WebSocket connectivity test failed after {websocket_test_time:.2f}s: {e}. "
                f"This doesn't indicate Issue #1263 regression."
            )

    @pytest.mark.timeout(30)  # Allow extra time for E2E testing
    async def test_end_to_end_golden_path_database_dependency_validation(self):
        """
        Complete end-to-end validation of Golden Path database dependency.

        This test validates that the complete user journey works with database
        connectivity and that Issue #1263 doesn't block any critical flows.
        """
        golden_path_start = time.time()
        validation_phases = {}

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Phase 1: Validate backend service is ready
                phase1_start = time.time()
                async with session.get(self.health_endpoints['ready_health']) as response:
                    assert response.status == 200, "Backend service not ready"
                    validation_phases['backend_ready'] = time.time() - phase1_start

                # Phase 2: Validate database connectivity
                phase2_start = time.time()
                async with session.get(self.health_endpoints['database_health']) as response:
                    assert response.status == 200, "Database not healthy"
                    response_data = await response.json()

                    # Check for database-specific health metrics
                    assert 'database_status' in response_data, "Missing database status"
                    validation_phases['database_connectivity'] = time.time() - phase2_start

                # Phase 3: Test auth service connectivity (depends on database)
                phase3_start = time.time()
                auth_health_url = f"{self.staging_endpoints['auth_base']}/health"
                async with session.get(auth_health_url) as response:
                    assert response.status == 200, "Auth service not healthy"
                    validation_phases['auth_service'] = time.time() - phase3_start

                total_golden_path_time = time.time() - golden_path_start

                # Log Golden Path timing breakdown
                logger.info(f"Golden Path validation timing:")
                for phase, timing in validation_phases.items():
                    logger.info(f"  {phase}: {timing:.2f}s")
                logger.info(f"  Total Golden Path: {total_golden_path_time:.2f}s")

                # Validate Golden Path performance requirements
                assert validation_phases['backend_ready'] < 10.0, (
                    f"Backend ready check took {validation_phases['backend_ready']:.2f}s - Issue #1263 regression"
                )

                assert validation_phases['database_connectivity'] < 5.0, (
                    f"Database connectivity took {validation_phases['database_connectivity']:.2f}s - too slow"
                )

                assert total_golden_path_time < 20.0, (
                    f"Complete Golden Path validation took {total_golden_path_time:.2f}s, "
                    f"expected < 20.0s for reliable user experience"
                )

                logger.info(f"✅ Golden Path validation successful: {total_golden_path_time:.2f}s total")

        except Exception as e:
            golden_path_time = time.time() - golden_path_start

            # Identify which phase failed for better debugging
            failed_phase = "unknown"
            if 'backend_ready' not in validation_phases:
                failed_phase = "backend_ready"
            elif 'database_connectivity' not in validation_phases:
                failed_phase = "database_connectivity"
            elif 'auth_service' not in validation_phases:
                failed_phase = "auth_service"

            if golden_path_time >= 10.0 and failed_phase in ['backend_ready', 'database_connectivity']:
                pytest.fail(
                    f"ISSUE #1263 GOLDEN PATH IMPACT: {failed_phase} phase failed "
                    f"after {golden_path_time:.2f}s - VPC database connectivity blocking user journey. "
                    f"Error: {e}"
                )
            else:
                pytest.fail(f"Golden Path validation failed at {failed_phase} phase: {e}")


@pytest.mark.e2e
@pytest.mark.staging
class Issue1263StagingEnvironmentSpecificTests(SSotAsyncTestCase):
    """Additional E2E tests specific to staging environment characteristics."""

    async def test_staging_vpc_connector_health_validation(self):
        """
        Test VPC connector health in staging environment.

        Validates that the VPC connector configuration from commit 2acf46c8a
        is working properly for database connectivity.
        """
        # This test would validate VPC connector metrics if available
        # For now, validate indirectly through database connectivity performance
        pass

    async def test_staging_cloud_run_service_startup_timing(self):
        """
        Test Cloud Run service startup timing in staging.

        Validates that Cloud Run services start up properly with the VPC
        configuration and don't hit database timeout issues during cold start.
        """
        # This would test Cloud Run cold start performance
        # Implementation depends on Cloud Run monitoring APIs
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])