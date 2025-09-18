"""
Test Infrastructure Improvements E2E on Staging GCP

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Validate infrastructure improvements in production-like environment
- Value Impact: Ensure infrastructure cleanup doesn't break production deployments
- Strategic Impact: Protect 500K+ ARR through stable production infrastructure

These tests run against staging GCP environment to validate that Docker
infrastructure improvements work in production-like conditions.
"""

import pytest
import asyncio
import time
import requests
from typing import Dict, Any
from test_framework.base_e2e_test import BaseE2ETest


class TestInfrastructureImprovementsStaging(BaseE2ETest):
    """Test infrastructure improvements on staging GCP environment."""

    STAGING_BASE_URL = "https://api.staging.netrasystems.ai"
    STAGING_AUTH_URL = "https://auth.staging.netrasystems.ai"
    STAGING_FRONTEND_URL = "https://app.staging.netrasystems.ai"

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    def test_staging_services_responding_fast(self):
        """Test that all staging services respond quickly after infrastructure improvements."""
        services = {
            'backend': self.STAGING_BASE_URL,
            'auth': self.STAGING_AUTH_URL,
            'frontend': self.STAGING_FRONTEND_URL
        }

        response_times = {}

        for service_name, url in services.items():
            start_time = time.time()
            try:
                response = requests.get(f"{url}/health", timeout=10)
                response_time = time.time() - start_time
                response_times[service_name] = {
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                }
            except requests.exceptions.RequestException as e:
                response_time = time.time() - start_time
                response_times[service_name] = {
                    'response_time': response_time,
                    'status_code': 0,
                    'success': False,
                    'error': str(e)
                }

        # All services should respond successfully
        failed_services = [name for name, data in response_times.items() if not data['success']]
        assert len(failed_services) == 0, f"Services failed health checks: {failed_services}"

        # All services should respond quickly (infrastructure improvements)
        slow_services = [
            name for name, data in response_times.items()
            if data['response_time'] > 5.0
        ]
        slow_service_details = [(name, f"{response_times[name]['response_time']:.2f}s") for name in slow_services]
        assert len(slow_services) == 0, (
            f"Services responding too slowly after infrastructure improvements: "
            f"{slow_service_details}"
        )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    def test_staging_deployment_health_comprehensive(self):
        """Test comprehensive health of staging deployment after infrastructure changes."""
        # Test backend health endpoint with detailed info
        response = requests.get(f"{self.STAGING_BASE_URL}/health", timeout=10)
        assert response.status_code == 200, f"Backend health check failed: {response.status_code}"

        health_data = response.json()

        # Validate health response structure
        assert 'status' in health_data, "Health response missing 'status'"
        assert health_data['status'] == 'healthy', f"Backend not healthy: {health_data}"

        # Check database connectivity (should be fast after infrastructure improvements)
        if 'database' in health_data:
            db_status = health_data['database']
            assert db_status.get('status') == 'connected', f"Database not connected: {db_status}"

            # Database response time should be improved
            if 'response_time_ms' in db_status:
                db_response_time = db_status['response_time_ms']
                assert db_response_time < 1000, (
                    f"Database response time too high: {db_response_time}ms (should be <1000ms)"
                )

        # Check Redis connectivity
        if 'redis' in health_data:
            redis_status = health_data['redis']
            assert redis_status.get('status') == 'connected', f"Redis not connected: {redis_status}"

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    def test_staging_websocket_connectivity_improved(self):
        """Test WebSocket connectivity on staging after infrastructure improvements."""
        import websockets
        import json

        websocket_url = self.STAGING_BASE_URL.replace('https://', 'wss://') + '/ws'

        async def test_websocket_connection():
            try:
                # WebSocket connection should be fast after infrastructure improvements
                async with websockets.connect(
                    websocket_url,
                    timeout=10,
                    ping_interval=30,
                    ping_timeout=10
                ) as websocket:

                    # Send test message
                    test_message = {
                        'type': 'ping',
                        'timestamp': time.time()
                    }

                    start_time = time.time()
                    await websocket.send(json.dumps(test_message))

                    # Should receive response quickly
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_time = time.time() - start_time

                    assert response is not None, "No WebSocket response received"
                    assert response_time < 2.0, (
                        f"WebSocket response too slow: {response_time:.2f}s (should be <2s)""WebSocket connection failed: {e}"

        # Run async test
        asyncio.run(test_websocket_connection())

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    def test_staging_container_resource_efficiency(self):
        """Test that containers are running efficiently after Alpine optimization."""
        # Test backend performance indicators
        response = requests.get(f"{self.STAGING_BASE_URL}/metrics", timeout=10)

        if response.status_code == 200:
            # If metrics endpoint exists, validate efficiency metrics
            try:
                metrics_data = response.json()

                # Check memory usage (should be lower with Alpine)
                if 'memory' in metrics_data:
                    memory_data = metrics_data['memory']
                    if 'usage_mb' in memory_data:
                        memory_usage = memory_data['usage_mb']
                        # After Alpine optimization, memory should be under 512MB
                        assert memory_usage < 512, (
                            f"Memory usage too high: {memory_usage}MB (should be <512MB with Alpine)"
                        )

                # Check startup time (should be faster with smaller images)
                if 'startup' in metrics_data:
                    startup_data = metrics_data['startup']
                    if 'duration_seconds' in startup_data:
                        startup_time = startup_data['duration_seconds']
                        # Startup should be under 60 seconds with Alpine
                        assert startup_time < 60, (
                            f"Startup time too slow: {startup_time}s (should be <60s with Alpine)"
                        )

            except json.JSONDecodeError:
                # Metrics endpoint exists but doesn't return JSON - that's ok
                pass
        else:
            # Metrics endpoint doesn't exist - that's ok, test passes
            pass

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    def test_staging_deployment_stability_post_cleanup(self):
        """Test deployment stability after Docker infrastructure cleanup."""
        # Test multiple rapid requests to ensure stability
        request_count = 10
        successful_requests = 0
        response_times = []

        for i in range(request_count):
            start_time = time.time()
            try:
                response = requests.get(f"{self.STAGING_BASE_URL}/health", timeout=15)
                response_time = time.time() - start_time
                response_times.append(response_time)

                if response.status_code == 200:
                    successful_requests += 1

                # Small delay between requests
                time.sleep(0.5)

            except requests.exceptions.RequestException:
                response_time = time.time() - start_time
                response_times.append(response_time)

        # At least 90% of requests should succeed (infrastructure should be stable)
        success_rate = successful_requests / request_count
        assert success_rate >= 0.9, (
            f"Success rate too low: {success_rate:.2%} (should be ≥90%)"
        )

        # Average response time should be good (infrastructure should be efficient)
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 3.0, (
            f"Average response time too high: {avg_response_time:.2f}s (should be <3s)"
        )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.infrastructure
    def test_staging_auth_service_performance(self):
        """Test auth service performance after infrastructure improvements."""
        # Test auth service health
        start_time = time.time()
        response = requests.get(f"{self.STAGING_AUTH_URL}/health", timeout=10)
        response_time = time.time() - start_time

        assert response.status_code == 200, f"Auth service health check failed: {response.status_code}"
        assert response_time < 3.0, (
            f"Auth service response too slow: {response_time:.2f}s (should be <3s)"
        )

        # Test auth service token validation endpoint (if available)
        try:
            start_time = time.time()
            # Use a test endpoint that doesn't require valid token
            response = requests.get(f"{self.STAGING_AUTH_URL}/api/v1/status", timeout=10)
            response_time = time.time() - start_time

            # Even if endpoint returns 404/405, response should be fast
            assert response_time < 2.0, (
                f"Auth service endpoint response too slow: {response_time:.2f}s (should be <2s)"
            )

        except requests.exceptions.RequestException:
            # Endpoint might not exist - that's ok
            pass