"""
E2E Staging Tests for Issue #1263 - Live Infrastructure Validation

CRITICAL OBJECTIVE: E2E tests against LIVE staging infrastructure that reproduce
the actual 25.0s database timeout issue from real VPC connector and Cloud SQL
capacity constraints in the staging GCP environment.

ROOT CAUSE E2E VALIDATION:
- Tests against real https://api.staging.netrasystems.ai
- Live VPC connector capacity under actual load
- Real Cloud SQL instance connection limits
- Actual GCP Cloud Run container constraints
- Live infrastructure scaling behavior

E2E VALIDATION STRATEGY: These tests connect to REAL staging services to validate
the infrastructure issue exists in the actual deployment environment. They should
FAIL initially to prove the infrastructure capacity constraints are real.

Business Value Justification (BVJ):
- Segment: Platform/Production Infrastructure
- Business Goal: Production Readiness & Reliability
- Value Impact: Validates real-world infrastructure capacity for 500K+ ARR platform
- Strategic Impact: Ensures staging environment accurately represents production constraints
"""

import pytest
import asyncio
import time
import httpx
from typing import Dict, Any, Optional, List
from unittest.mock import patch
import os
from datetime import datetime, timedelta

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config,
    get_connection_monitor,
    monitor_connection_attempt,
    check_vpc_connector_performance
)
from shared.isolated_environment import IsolatedEnvironment


class Issue1263StagingInfrastructureE2ETests(SSotAsyncTestCase):
    """
    E2E tests against live staging infrastructure to reproduce Issue #1263.

    These tests connect to real staging services and validate the actual
    infrastructure capacity constraints that cause database timeouts.
    """

    async def asyncSetUp(self):
        """Set up E2E test environment with real staging endpoints."""
        await super().asyncSetUp()
        self.env = IsolatedEnvironment()

        # Reset monitoring for clean E2E state
        monitor = get_connection_monitor()
        monitor.reset_metrics()

        # Real staging infrastructure endpoints
        self.staging_endpoints = {
            'backend_api': 'https://api.staging.netrasystems.ai',
            'auth_service': 'https://auth.staging.netrasystems.ai',
            'frontend': 'https://app.staging.netrasystems.ai',
            'websocket': 'wss://api.staging.netrasystems.ai/ws'
        }

        # Real staging database configuration
        self.staging_db_config = {
            'host': 'postgres.staging.netrasystems.ai',
            'port': 5432,
            'database': 'netra_staging',
            'vpc_connector': 'projects/netra-staging/locations/us-central1/connectors/netra-staging-vpc-connector',
            'cloud_sql_instance': 'netra-staging:us-central1:postgres-staging'
        }

        # HTTP client for E2E testing
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def asyncTearDown(self):
        """Clean up E2E test resources."""
        await self.http_client.aclose()
        await super().asyncTearDown()

    async def test_staging_api_connectivity_under_database_stress_e2e(self):
        """
        CRITICAL E2E TEST - MUST FAIL INITIALLY

        Tests live staging API connectivity when database infrastructure is under stress.
        This reproduces Issue #1263 by hitting the real staging environment with
        requests that trigger database connection timeouts.

        Expected Initial Result: FAIL (API timeouts due to database infrastructure)
        Expected After Fix: PASS (API responds < 15s)
        """
        api_endpoint = f"{self.staging_endpoints['backend_api']}/health"
        stress_requests = 10  # Enough to stress VPC connector capacity

        async def make_stressed_api_request(request_id: int):
            """Make API request that stresses database connectivity."""
            request_start = time.time()

            try:
                # Hit health endpoint which requires database connectivity
                response = await self.http_client.get(
                    api_endpoint,
                    timeout=30.0,  # Allow time to observe timeout behavior
                    headers={'X-Request-ID': f'stress-test-{request_id}'}
                )

                request_duration = time.time() - request_start

                if response.status_code == 200:
                    return {
                        'request_id': request_id,
                        'duration': request_duration,
                        'status_code': response.status_code,
                        'success': True
                    }
                else:
                    return {
                        'request_id': request_id,
                        'duration': request_duration,
                        'status_code': response.status_code,
                        'success': False,
                        'error': f"HTTP {response.status_code}"
                    }

            except Exception as e:
                request_duration = time.time() - request_start
                return {
                    'request_id': request_id,
                    'duration': request_duration,
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                }

        e2e_test_start = time.time()

        # Execute concurrent requests to stress infrastructure
        stress_tasks = [
            make_stressed_api_request(i)
            for i in range(1, stress_requests + 1)
        ]

        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        total_e2e_time = time.time() - e2e_test_start

        # Analyze E2E stress test results
        successful_requests = [r for r in stress_results if not isinstance(r, Exception) and r.get('success', False)]
        failed_requests = [r for r in stress_results if isinstance(r, Exception) or not r.get('success', True)]

        # Extract response times for analysis
        response_times = [r['duration'] for r in successful_requests]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 30.0
        max_response_time = max(response_times) if response_times else 30.0

        # Record E2E results for monitoring
        for result in successful_requests:
            monitor_connection_attempt('staging', result['duration'], True)

        for result in failed_requests:
            duration = result.get('duration', 30.0) if isinstance(result, dict) else 30.0
            monitor_connection_attempt('staging', duration, False)

        # This assertion should FAIL initially - proving live staging infrastructure issue
        assert len(failed_requests) < 3, (
            f"ISSUE #1263 E2E REPRODUCTION: {len(failed_requests)}/{stress_requests} "
            f"requests failed against LIVE staging API {api_endpoint}. "
            f"Successful: {len(successful_requests)}, Failed: {len(failed_requests)}. "
            f"Average response time: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s. "
            f"Root Cause: Live VPC connector + Cloud SQL capacity constraints in staging GCP. "
            f"Expected < 3 failures after infrastructure scaling."
        )

        assert max_response_time < 15.0, (
            f"ISSUE #1263 E2E TIMEOUT: Maximum response time {max_response_time:.2f}s "
            f"from live staging infrastructure exceeds acceptable threshold. "
            f"Response times: {response_times}. "
            f"Live staging VPC/Cloud SQL capacity constraints confirmed. "
            f"Expected < 15.0s after infrastructure optimization."
        )

    async def test_live_staging_database_connection_capacity_e2e(self):
        """
        Test live staging database connection capacity through API endpoints.

        This E2E test validates the actual Cloud SQL connection limits and
        VPC connector throughput by hitting database-intensive endpoints.
        """
        # Endpoints that require database connectivity
        db_intensive_endpoints = [
            f"{self.staging_endpoints['backend_api']}/health",
            f"{self.staging_endpoints['backend_api']}/api/health",
            f"{self.staging_endpoints['auth_service']}/health"
        ]

        connection_capacity_results = {}

        for endpoint in db_intensive_endpoints:
            capacity_start = time.time()

            try:
                # Test connection capacity with realistic load
                response = await self.http_client.get(
                    endpoint,
                    timeout=25.0,  # Issue #1263 timeout threshold
                    headers={'X-E2E-Capacity-Test': 'true'}
                )

                connection_time = time.time() - capacity_start

                connection_capacity_results[endpoint] = {
                    'connection_time': connection_time,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'infrastructure_health': connection_time < 10.0
                }

            except Exception as e:
                connection_time = time.time() - capacity_start
                connection_capacity_results[endpoint] = {
                    'connection_time': connection_time,
                    'status_code': None,
                    'success': False,
                    'error': str(e),
                    'infrastructure_health': False
                }

            # Small delay between tests to avoid overwhelming infrastructure
            await asyncio.sleep(1.0)

        # Analyze live infrastructure capacity
        healthy_endpoints = [
            endpoint for endpoint, result in connection_capacity_results.items()
            if result.get('infrastructure_health', False)
        ]

        failed_endpoints = [
            endpoint for endpoint, result in connection_capacity_results.items()
            if not result.get('success', False)
        ]

        avg_live_connection_time = sum(
            result['connection_time'] for result in connection_capacity_results.values()
        ) / len(connection_capacity_results)

        # This should FAIL initially - proving live infrastructure capacity issues
        assert len(failed_endpoints) == 0, (
            f"LIVE STAGING INFRASTRUCTURE FAILURE: {len(failed_endpoints)} endpoints "
            f"failed due to database connectivity issues. Failed: {failed_endpoints}. "
            f"Capacity results: {connection_capacity_results}. "
            f"Issue #1263: Live staging VPC/Cloud SQL capacity insufficient. "
            f"Expected 0 endpoint failures after infrastructure scaling."
        )

        assert avg_live_connection_time < 12.0, (
            f"LIVE STAGING CAPACITY CONSTRAINT: Average connection time {avg_live_connection_time:.2f}s "
            f"indicates infrastructure capacity pressure. Healthy endpoints: {len(healthy_endpoints)}. "
            f"Issue #1263: Live infrastructure performance degraded. "
            f"Expected < 12.0s average after capacity optimization."
        )

    async def test_real_vpc_connector_throughput_validation_e2e(self):
        """
        Test real VPC connector throughput limits in live staging environment.

        This E2E test validates the actual VPC connector capacity constraints
        that contribute to Issue #1263 by measuring real network performance.
        """
        vpc_performance_tests = []

        # Test VPC connector throughput with different request patterns
        test_patterns = [
            {'name': 'burst_load', 'concurrent_requests': 8, 'delay_between': 0.1},
            {'name': 'sustained_load', 'concurrent_requests': 4, 'delay_between': 0.5},
            {'name': 'peak_load', 'concurrent_requests': 12, 'delay_between': 0.0}
        ]

        for pattern in test_patterns:
            pattern_start = time.time()

            async def vpc_throughput_request(request_id: int):
                """Single request to measure VPC connector performance."""
                request_start = time.time()

                try:
                    response = await self.http_client.get(
                        f"{self.staging_endpoints['backend_api']}/health",
                        timeout=20.0,
                        headers={'X-VPC-Test': pattern['name'], 'X-Request-ID': str(request_id)}
                    )

                    request_duration = time.time() - request_start
                    return {
                        'request_id': request_id,
                        'duration': request_duration,
                        'vpc_performance': request_duration < 8.0,  # VPC baseline
                        'success': response.status_code == 200
                    }

                except Exception as e:
                    request_duration = time.time() - request_start
                    return {
                        'request_id': request_id,
                        'duration': request_duration,
                        'vpc_performance': False,
                        'success': False,
                        'error': str(e)
                    }

            # Execute pattern requests
            pattern_tasks = []
            for i in range(pattern['concurrent_requests']):
                pattern_tasks.append(vpc_throughput_request(i))
                if pattern['delay_between'] > 0:
                    await asyncio.sleep(pattern['delay_between'])

            pattern_results = await asyncio.gather(*pattern_tasks, return_exceptions=True)
            pattern_duration = time.time() - pattern_start

            # Analyze VPC performance for this pattern
            successful_pattern_requests = [
                r for r in pattern_results
                if not isinstance(r, Exception) and r.get('success', False)
            ]

            vpc_healthy_requests = [
                r for r in successful_pattern_requests
                if r.get('vpc_performance', False)
            ]

            pattern_avg_time = sum(
                r['duration'] for r in successful_pattern_requests
            ) / len(successful_pattern_requests) if successful_pattern_requests else 20.0

            vpc_performance_tests.append({
                'pattern': pattern['name'],
                'total_requests': pattern['concurrent_requests'],
                'successful_requests': len(successful_pattern_requests),
                'vpc_healthy_requests': len(vpc_healthy_requests),
                'pattern_duration': pattern_duration,
                'average_request_time': pattern_avg_time,
                'vpc_health_rate': len(vpc_healthy_requests) / pattern['concurrent_requests'] * 100
            })

            # Delay between patterns to avoid overwhelming VPC connector
            await asyncio.sleep(2.0)

        # Analyze overall VPC connector performance
        overall_vpc_health = sum(
            test['vpc_health_rate'] for test in vpc_performance_tests
        ) / len(vpc_performance_tests)

        worst_pattern_performance = min(
            test['vpc_health_rate'] for test in vpc_performance_tests
        )

        peak_load_pattern = next(
            test for test in vpc_performance_tests if test['pattern'] == 'peak_load'
        )

        # This should FAIL initially - proving VPC connector capacity constraints
        assert overall_vpc_health >= 70.0, (
            f"VPC CONNECTOR CAPACITY CONSTRAINT: {overall_vpc_health:.1f}% overall VPC health "
            f"indicates real infrastructure capacity issues. Performance tests: {vpc_performance_tests}. "
            f"Issue #1263: Live VPC connector throughput insufficient for platform load. "
            f"Expected ≥70% VPC health after connector capacity scaling."
        )

        assert worst_pattern_performance >= 50.0, (
            f"VPC CONNECTOR UNDER STRESS: {worst_pattern_performance:.1f}% worst-case VPC performance "
            f"indicates capacity constraints during load spikes. Peak load: {peak_load_pattern}. "
            f"Issue #1263: VPC connector cannot handle peak traffic patterns. "
            f"Expected ≥50% performance under stress after infrastructure optimization."
        )

    async def test_live_cloud_sql_connection_limits_e2e(self):
        """
        Test live Cloud SQL connection limits through staging infrastructure.

        This E2E test validates the actual Cloud SQL instance connection capacity
        by monitoring database-dependent operations under realistic load.
        """
        # Monitor Cloud SQL performance through health endpoints over time
        monitoring_duration = 30.0  # 30 seconds of sustained monitoring
        monitoring_interval = 2.0   # Check every 2 seconds
        monitoring_checks = int(monitoring_duration / monitoring_interval)

        cloud_sql_performance = []

        for check_iteration in range(monitoring_checks):
            check_start = time.time()

            try:
                # Hit database-dependent endpoint to test Cloud SQL capacity
                response = await self.http_client.get(
                    f"{self.staging_endpoints['backend_api']}/health",
                    timeout=15.0,
                    headers={
                        'X-CloudSQL-Capacity-Test': 'true',
                        'X-Check-Iteration': str(check_iteration)
                    }
                )

                check_duration = time.time() - check_start

                cloud_sql_performance.append({
                    'iteration': check_iteration,
                    'duration': check_duration,
                    'status_code': response.status_code,
                    'cloud_sql_healthy': check_duration < 5.0 and response.status_code == 200,
                    'infrastructure_stress': check_duration > 10.0
                })

            except Exception as e:
                check_duration = time.time() - check_start
                cloud_sql_performance.append({
                    'iteration': check_iteration,
                    'duration': check_duration,
                    'status_code': None,
                    'cloud_sql_healthy': False,
                    'infrastructure_stress': True,
                    'error': str(e)
                })

            # Wait between checks
            await asyncio.sleep(monitoring_interval)

        # Analyze Cloud SQL capacity performance
        healthy_checks = [check for check in cloud_sql_performance if check.get('cloud_sql_healthy', False)]
        stressed_checks = [check for check in cloud_sql_performance if check.get('infrastructure_stress', False)]

        cloud_sql_health_rate = len(healthy_checks) / len(cloud_sql_performance) * 100
        infrastructure_stress_rate = len(stressed_checks) / len(cloud_sql_performance) * 100

        avg_check_duration = sum(
            check['duration'] for check in cloud_sql_performance
        ) / len(cloud_sql_performance)

        max_check_duration = max(check['duration'] for check in cloud_sql_performance)

        # This should FAIL initially - proving Cloud SQL capacity constraints
        assert cloud_sql_health_rate >= 80.0, (
            f"CLOUD SQL CAPACITY CONSTRAINT: {cloud_sql_health_rate:.1f}% Cloud SQL health rate "
            f"over {monitoring_duration}s monitoring indicates capacity issues. "
            f"Healthy checks: {len(healthy_checks)}/{len(cloud_sql_performance)}. "
            f"Performance data: {cloud_sql_performance}. "
            f"Issue #1263: Live Cloud SQL instance capacity insufficient for sustained load. "
            f"Expected ≥80% health rate after Cloud SQL scaling."
        )

        assert infrastructure_stress_rate < 30.0, (
            f"INFRASTRUCTURE STRESS DETECTED: {infrastructure_stress_rate:.1f}% of checks "
            f"showed infrastructure stress. Average duration: {avg_check_duration:.2f}s, "
            f"Max duration: {max_check_duration:.2f}s. Stressed checks: {len(stressed_checks)}. "
            f"Issue #1263: Infrastructure stress indicates capacity constraints. "
            f"Expected < 30% stress rate after optimization."
        )

    async def test_end_to_end_user_journey_infrastructure_impact_e2e(self):
        """
        CRITICAL E2E TEST - Complete user journey under infrastructure stress

        Tests the complete user journey from frontend to backend through the
        live staging infrastructure to validate real-world Issue #1263 impact.

        This represents the actual 500K+ ARR user experience impact.
        """
        user_journey_steps = []

        # Step 1: Frontend availability
        frontend_start = time.time()
        try:
            frontend_response = await self.http_client.get(
                self.staging_endpoints['frontend'],
                timeout=10.0,
                headers={'X-E2E-Journey': 'frontend-check'}
            )
            frontend_duration = time.time() - frontend_start
            user_journey_steps.append({
                'step': 'frontend_access',
                'duration': frontend_duration,
                'success': frontend_response.status_code == 200,
                'infrastructure_impact': frontend_duration > 5.0
            })
        except Exception as e:
            frontend_duration = time.time() - frontend_start
            user_journey_steps.append({
                'step': 'frontend_access',
                'duration': frontend_duration,
                'success': False,
                'error': str(e),
                'infrastructure_impact': True
            })

        # Step 2: Auth service connectivity
        auth_start = time.time()
        try:
            auth_response = await self.http_client.get(
                f"{self.staging_endpoints['auth_service']}/health",
                timeout=15.0,
                headers={'X-E2E-Journey': 'auth-check'}
            )
            auth_duration = time.time() - auth_start
            user_journey_steps.append({
                'step': 'auth_service',
                'duration': auth_duration,
                'success': auth_response.status_code == 200,
                'infrastructure_impact': auth_duration > 8.0
            })
        except Exception as e:
            auth_duration = time.time() - auth_start
            user_journey_steps.append({
                'step': 'auth_service',
                'duration': auth_duration,
                'success': False,
                'error': str(e),
                'infrastructure_impact': True
            })

        # Step 3: Backend API functionality
        backend_start = time.time()
        try:
            backend_response = await self.http_client.get(
                f"{self.staging_endpoints['backend_api']}/health",
                timeout=20.0,
                headers={'X-E2E-Journey': 'backend-check'}
            )
            backend_duration = time.time() - backend_start
            user_journey_steps.append({
                'step': 'backend_api',
                'duration': backend_duration,
                'success': backend_response.status_code == 200,
                'infrastructure_impact': backend_duration > 12.0
            })
        except Exception as e:
            backend_duration = time.time() - backend_start
            user_journey_steps.append({
                'step': 'backend_api',
                'duration': backend_duration,
                'success': False,
                'error': str(e),
                'infrastructure_impact': True
            })

        # Analyze complete user journey impact
        successful_steps = [step for step in user_journey_steps if step.get('success', False)]
        infrastructure_impacted_steps = [step for step in user_journey_steps if step.get('infrastructure_impact', False)]

        total_journey_time = sum(step['duration'] for step in user_journey_steps)
        user_experience_degraded = len(infrastructure_impacted_steps) > 0 or total_journey_time > 25.0

        # This should FAIL initially - proving user journey impact from infrastructure
        assert len(successful_steps) == len(user_journey_steps), (
            f"USER JOURNEY INFRASTRUCTURE FAILURE: {len(successful_steps)}/{len(user_journey_steps)} "
            f"journey steps successful. Failed steps affect 500K+ ARR user experience. "
            f"Journey steps: {user_journey_steps}. "
            f"Issue #1263: Infrastructure capacity constraints breaking user journeys. "
            f"Expected 100% journey step success after infrastructure optimization."
        )

        assert not user_experience_degraded, (
            f"USER EXPERIENCE DEGRADED: {len(infrastructure_impacted_steps)} steps impacted by infrastructure, "
            f"total journey time: {total_journey_time:.2f}s. Infrastructure impact steps: {infrastructure_impacted_steps}. "
            f"Issue #1263: Infrastructure constraints directly impacting 500K+ ARR user experience. "
            f"Expected no infrastructure impact on user journey after optimization."
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--durations=10'])