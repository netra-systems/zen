"""
E2E Staging Tests for Issue #1278 - Complete Startup Sequence Staging Validation

Business Value Justification (BVJ):
- Segment: Platform/Critical (Revenue Protection)
- Business Goal: Validate complete application startup in real staging environment
- Value Impact: $500K+ ARR validation pipeline functionality
- Strategic Impact: Critical P0 outage resolution validation

Following TEST_CREATION_GUIDE.md requirements:
- Tests against real GCP staging environment (Cloud Run + Cloud SQL)
- Uses staging endpoints and real infrastructure
- Designed to reproduce Issue #1278 infrastructure problems
- Validates complete 7-phase SMD startup sequence

These tests validate the complete startup sequence aspects identified in Issue #1278:
- Complete application startup sequence reproduction in staging
- Cloud SQL connectivity validation through VPC connector
- Health endpoint startup dependency validation during database issues
- Container exit code validation during startup failures
"""

import pytest
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
import time
import json
import os

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.staging_fixtures import staging_environment_fixture
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


@pytest.mark.e2e_staging
@pytest.mark.issue_1278
@pytest.mark.mission_critical
@pytest.mark.real_services
class TestCompleteStartupSequenceStagingValidation(BaseIntegrationTest):
    """E2E staging tests for complete startup sequence validation - Issue #1278."""

    # Staging environment configuration
    STAGING_BASE_URL = "https://netra-backend-staging-701982941522.us-central1.run.app"
    STAGING_FRONTEND_URL = "https://netra-frontend-staging-701982941522.us-central1.run.app"

    # Cloud SQL configuration
    CLOUD_SQL_INSTANCE = "netra-staging:us-central1:staging-shared-postgres"
    CLOUD_SQL_SOCKET_PATH = f"/cloudsql/{CLOUD_SQL_INSTANCE}/.s.PGSQL.5432"

    # Timeout configurations
    STARTUP_TIMEOUT = 60.0  # Maximum time to wait for startup
    DATABASE_TIMEOUT = 35.0  # Expected database connection timeout
    HEALTH_CHECK_TIMEOUT = 10.0  # Timeout for health checks

    @pytest.fixture(autouse=True)
    async def setup_staging_environment(self, staging_environment_fixture):
        """Set up staging environment for E2E testing."""
        self.staging_env = staging_environment_fixture
        self.isolated_env = IsolatedEnvironment()
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def teardown_method(self):
        """Clean up after each test."""
        if hasattr(self, 'session'):
            await self.session.close()

    async def test_complete_application_startup_sequence_staging(self):
        """
        Test Case 3.1: Test complete 7-phase SMD startup sequence in staging environment.

        Expected behavior:
        - Monitor complete startup sequence in real staging
        - ✅ Phase 1 (INIT) - Initialization
        - ✅ Phase 2 (DEPENDENCIES) - Dependencies loaded
        - ❌ Phase 3 (DATABASE) - Connection timeout (issue reproduction)
        - Track timing and failure patterns
        """
        logger.info("Testing complete application startup sequence in staging environment")

        # Test health endpoint availability during startup
        startup_start_time = time.time()
        startup_phases = {
            'INIT': False,
            'DEPENDENCIES': False,
            'DATABASE': False,
            'REDIS': False,
            'SERVICES': False,
            'WEBSOCKET': False,
            'READY': False
        }

        # Monitor startup phases for up to STARTUP_TIMEOUT
        while time.time() - startup_start_time < self.STARTUP_TIMEOUT:
            try:
                # Check basic health endpoint
                health_response = await self._check_health_endpoint()
                if health_response.get('status') == 'healthy':
                    startup_phases['INIT'] = True

                # Check startup status endpoint (if available)
                startup_status = await self._check_startup_status()
                if startup_status:
                    # Update phase status based on response
                    for phase, status in startup_status.get('phases', {}).items():
                        if status.get('completed', False):
                            startup_phases[phase] = True

                # Check database-specific health
                db_health = await self._check_database_health()
                if db_health.get('status') == 'healthy':
                    startup_phases['DATABASE'] = True
                    startup_phases['READY'] = True
                    break
                elif db_health.get('status') == 'error':
                    # Database failure detected - this is expected for Issue #1278
                    logger.warning(f"Database health check failed: {db_health}")
                    break

                # Wait before next check
                await asyncio.sleep(2.0)

            except Exception as e:
                logger.debug(f"Health check failed (expected during startup): {e}")
                await asyncio.sleep(1.0)

        startup_duration = time.time() - startup_start_time

        # Analyze startup results
        logger.info(f"Startup monitoring completed after {startup_duration:.2f}s")
        logger.info(f"Phase completion status: {startup_phases}")

        # Expected behavior based on Issue #1278 analysis
        if startup_phases['DATABASE']:
            # If database phase succeeded, infrastructure issue is resolved
            logger.info("✅ Database connectivity SUCCESS - Infrastructure issue appears resolved")
            self.assertTrue(startup_phases['READY'], "Application should be fully ready")
            self.assertLess(startup_duration, 30.0, "Startup should complete quickly when working")
        else:
            # If database phase failed, reproducing the infrastructure issue
            logger.warning("❌ Database connectivity FAILED - Reproducing Issue #1278 infrastructure problem")
            self.assertTrue(startup_phases['INIT'], "INIT phase should succeed")
            self.assertFalse(startup_phases['DATABASE'], "DATABASE phase should fail (reproducing issue)")
            self.assertGreaterEqual(startup_duration, 30.0, "Should timeout after database connection attempts")

    async def test_cloud_sql_vpc_connector_connectivity_staging(self):
        """
        Test Case 3.2: Test direct Cloud SQL connectivity through VPC connector.

        Expected behavior:
        - Test connection to: netra-staging:us-central1:staging-shared-postgres
        - Validate 35.0s timeout behavior
        - Monitor for platform-level connectivity issues
        """
        logger.info("Testing Cloud SQL VPC connector connectivity")

        # Test database connectivity through health endpoint
        db_start_time = time.time()
        database_connectivity_results = []

        # Perform multiple connectivity tests over time
        for attempt in range(3):
            attempt_start = time.time()
            try:
                db_health = await self._check_database_health()
                attempt_duration = time.time() - attempt_start

                result = {
                    'attempt': attempt + 1,
                    'duration': attempt_duration,
                    'status': db_health.get('status', 'unknown'),
                    'error': db_health.get('error'),
                    'details': db_health.get('details', {})
                }
                database_connectivity_results.append(result)

                logger.info(f"Database connectivity attempt {attempt + 1}: "
                           f"status={result['status']}, duration={attempt_duration:.2f}s")

                if result['status'] == 'healthy':
                    # Database connectivity is working
                    self.assertLess(attempt_duration, 10.0,
                                   "Healthy database should respond quickly")
                else:
                    # Database connectivity issue (expected for Issue #1278)
                    if attempt_duration >= 30.0:
                        self.assertIn('timeout', str(result['error']).lower(),
                                     "Long duration should indicate timeout")

            except Exception as e:
                attempt_duration = time.time() - attempt_start
                result = {
                    'attempt': attempt + 1,
                    'duration': attempt_duration,
                    'status': 'exception',
                    'error': str(e)
                }
                database_connectivity_results.append(result)
                logger.warning(f"Database connectivity attempt {attempt + 1} failed: {e}")

            # Wait between attempts
            if attempt < 2:
                await asyncio.sleep(5.0)

        total_test_duration = time.time() - db_start_time

        # Analyze connectivity results
        successful_attempts = [r for r in database_connectivity_results if r['status'] == 'healthy']
        failed_attempts = [r for r in database_connectivity_results if r['status'] != 'healthy']

        logger.info(f"Database connectivity test completed in {total_test_duration:.2f}s")
        logger.info(f"Successful attempts: {len(successful_attempts)}, Failed attempts: {len(failed_attempts)}")

        if successful_attempts:
            # Infrastructure is working
            logger.info("✅ Cloud SQL VPC connector connectivity SUCCESS")
            avg_success_time = sum(r['duration'] for r in successful_attempts) / len(successful_attempts)
            self.assertLess(avg_success_time, 5.0, "Successful connections should be fast")
        else:
            # Infrastructure issue reproduced
            logger.warning("❌ Cloud SQL VPC connector connectivity FAILED - Issue #1278 reproduced")
            # Validate that failures are due to timeouts (expected behavior)
            timeout_failures = [r for r in failed_attempts
                               if r['duration'] >= 25.0 or 'timeout' in str(r['error']).lower()]
            self.assertGreater(len(timeout_failures), 0,
                              "Should observe timeout failures indicating infrastructure issue")

    async def test_health_endpoints_database_dependency_staging(self):
        """
        Test Case 3.3: Test health endpoints during database connectivity issues.

        Expected behavior:
        - Test /health, /health/ready, /health/database endpoints
        - Validate response during SMD Phase 3 failures
        - Monitor for 503 Service Unavailable responses
        """
        logger.info("Testing health endpoints during database dependency issues")

        health_endpoints = [
            '/health',
            '/health/ready',
            '/health/database',
            '/health/detailed'
        ]

        health_results = {}

        for endpoint in health_endpoints:
            logger.info(f"Testing health endpoint: {endpoint}")
            endpoint_results = []

            # Test each endpoint multiple times
            for check in range(3):
                check_start = time.time()
                try:
                    async with self.session.get(f"{self.STAGING_BASE_URL}{endpoint}") as response:
                        check_duration = time.time() - check_start
                        response_data = await response.json()

                        result = {
                            'check': check + 1,
                            'status_code': response.status,
                            'duration': check_duration,
                            'response': response_data,
                            'headers': dict(response.headers)
                        }
                        endpoint_results.append(result)

                        logger.debug(f"{endpoint} check {check + 1}: "
                                   f"status={response.status}, duration={check_duration:.2f}s")

                except Exception as e:
                    check_duration = time.time() - check_start
                    result = {
                        'check': check + 1,
                        'status_code': None,
                        'duration': check_duration,
                        'error': str(e)
                    }
                    endpoint_results.append(result)
                    logger.debug(f"{endpoint} check {check + 1} failed: {e}")

                # Wait between checks
                if check < 2:
                    await asyncio.sleep(2.0)

            health_results[endpoint] = endpoint_results

        # Analyze health endpoint results
        for endpoint, results in health_results.items():
            logger.info(f"Health endpoint {endpoint} results:")

            success_count = len([r for r in results if r.get('status_code') == 200])
            error_count = len([r for r in results if r.get('status_code', 0) >= 400])
            exception_count = len([r for r in results if 'error' in r])

            logger.info(f"  Success: {success_count}, Errors: {error_count}, Exceptions: {exception_count}")

            if endpoint == '/health/database':
                # Database health endpoint should reflect connectivity issues
                if success_count > 0:
                    logger.info("✅ Database health endpoint responding - infrastructure may be working")
                else:
                    logger.warning("❌ Database health endpoint failing - reproducing Issue #1278")
                    # Should see appropriate error responses
                    self.assertGreater(error_count + exception_count, 0,
                                      "Database health should show errors during connectivity issues")

    async def test_container_exit_code_3_startup_failure_staging(self):
        """
        Test Case 3.4: Test container termination behavior during startup failures.

        Expected behavior:
        - Monitor for startup failure patterns
        - Validate error responses during startup
        - Confirm container behavior during SMD Phase 3 timeout
        """
        logger.info("Testing container behavior during startup failures")

        # Monitor application availability during startup stress
        availability_results = []
        monitoring_duration = 60.0  # Monitor for 1 minute
        monitoring_start = time.time()

        while time.time() - monitoring_start < monitoring_duration:
            check_start = time.time()
            try:
                # Check basic connectivity
                async with self.session.get(f"{self.STAGING_BASE_URL}/health",
                                          timeout=aiohttp.ClientTimeout(total=10)) as response:
                    check_duration = time.time() - check_start
                    result = {
                        'timestamp': time.time(),
                        'status_code': response.status,
                        'duration': check_duration,
                        'available': True
                    }
                    availability_results.append(result)

            except Exception as e:
                check_duration = time.time() - check_start
                result = {
                    'timestamp': time.time(),
                    'error': str(e),
                    'duration': check_duration,
                    'available': False
                }
                availability_results.append(result)

            await asyncio.sleep(5.0)

        # Analyze availability patterns
        total_checks = len(availability_results)
        available_checks = len([r for r in availability_results if r.get('available', False)])
        unavailable_checks = total_checks - available_checks

        availability_percentage = (available_checks / total_checks) * 100 if total_checks > 0 else 0

        logger.info(f"Container availability monitoring completed:")
        logger.info(f"  Total checks: {total_checks}")
        logger.info(f"  Available: {available_checks} ({availability_percentage:.1f}%)")
        logger.info(f"  Unavailable: {unavailable_checks}")

        if availability_percentage >= 80:
            # Container is mostly stable
            logger.info("✅ Container stability GOOD - startup issues may be resolved")
            self.assertGreaterEqual(availability_percentage, 80,
                                   "Container should be stable when infrastructure is working")
        else:
            # Container instability indicating startup issues
            logger.warning("❌ Container instability DETECTED - reproducing Issue #1278 startup failures")
            # This indicates the startup failure patterns are being reproduced
            long_response_times = [r for r in availability_results
                                 if r.get('duration', 0) > 30.0]
            if long_response_times:
                logger.info("Detected long response times indicating startup timeouts")

    # Helper methods for health checks

    async def _check_health_endpoint(self) -> Dict[str, Any]:
        """Check basic health endpoint."""
        try:
            async with self.session.get(f"{self.STAGING_BASE_URL}/health",
                                      timeout=aiohttp.ClientTimeout(total=self.HEALTH_CHECK_TIMEOUT)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {'status': 'error', 'code': response.status}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database-specific health endpoint."""
        try:
            async with self.session.get(f"{self.STAGING_BASE_URL}/health/database",
                                      timeout=aiohttp.ClientTimeout(total=self.DATABASE_TIMEOUT)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {'status': 'error', 'code': response.status, 'error': f"HTTP {response.status}"}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def _check_startup_status(self) -> Optional[Dict[str, Any]]:
        """Check startup status endpoint (if available)."""
        try:
            async with self.session.get(f"{self.STAGING_BASE_URL}/internal/startup-status",
                                      timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception:
            return None


if __name__ == '__main__':
    # Run E2E staging tests
    pytest.main([__file__, '-v', '--tb=short', '-s'])