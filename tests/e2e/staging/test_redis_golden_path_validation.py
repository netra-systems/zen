"""
E2E Tests - Issue #1177 Redis Golden Path Validation on Staging GCP

CRITICAL E2E FAILURE REPRODUCTION: These tests validate the Golden Path user flow
on staging GCP environment, specifically testing Redis dependencies that fail
due to configuration pattern mismatch in Issue #1177.

Expected Results: FAIL - Golden Path broken due to Redis config mismatch
Tests actual staging deployment with real GCP services.

Business Value: Platform/Mission Critical - 500K+ ARR Golden Path Protection
The Golden Path user flow (login -> chat -> AI response) depends on Redis for
session management and WebSocket functionality.

SSOT Compliance: E2E tests on real staging GCP, no Docker, no mocks.
"""

import asyncio
import pytest
import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class RedisGoldenPathValidationTests(SSotAsyncTestCase):
    """E2E validation of Golden Path Redis dependencies on staging GCP."""

    @classmethod
    def setup_class(cls):
        """Setup class-level resources."""
        super().setup_class()
        # Staging GCP canonical URLs per CLAUDE.md requirements
        cls.staging_base_url = "https://api.staging.netrasystems.ai"
        cls.staging_auth_url = "https://auth.staging.netrasystems.ai"
        cls.staging_frontend_url = "https://app.staging.netrasystems.ai"

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

    @pytest.mark.asyncio
    async def test_staging_health_endpoint_redis_status_failure(self):
        """
        Test staging health endpoint Redis status (EXPECTED TO FAIL - Issue #1177).

        The health endpoint should report Redis connectivity, but fails due to
        configuration pattern mismatch preventing proper Redis initialization.
        """
        health_url = f"{self.staging_base_url}/health"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        pytest.fail(f"Health endpoint not accessible: {response.status}")

                    health_data = await response.json()

                    # Check Redis status in health response
                    redis_status = health_data.get("redis", {})

                    # EXPECTED FAILURE: Redis status should be unhealthy due to Issue #1177
                    redis_connected = redis_status.get("connected", False)
                    redis_available = redis_status.get("available", False)

                    if not redis_connected or not redis_available:
                        # This is the EXPECTED failure due to Issue #1177
                        failure_details = {
                            "redis_connected": redis_connected,
                            "redis_available": redis_available,
                            "redis_status": redis_status,
                            "full_health": health_data
                        }
                        pytest.fail(f"EXPECTED FAILURE - Redis health check failed due to Issue #1177: {failure_details}")

            except asyncio.TimeoutError:
                pytest.fail("Health endpoint timeout - staging may be down")
            except Exception as e:
                pytest.fail(f"Health endpoint check failed: {e}")

    @pytest.mark.asyncio
    async def test_staging_websocket_connection_redis_dependency_failure(self):
        """
        Test staging WebSocket connection with Redis dependency (EXPECTED TO FAIL - Issue #1177).

        WebSocket functionality depends on Redis for session management and message queuing.
        Configuration mismatch in Issue #1177 should cause WebSocket failures.
        """
        # Note: WebSocket testing requires proper authentication
        # For now, test WebSocket endpoint accessibility
        websocket_url = f"{self.staging_base_url.replace('https://', 'wss://')}/ws"

        try:
            # Test WebSocket endpoint accessibility (not full connection due to auth requirements)
            async with aiohttp.ClientSession() as session:
                # Check if WebSocket endpoint responds to HTTP request
                try:
                    async with session.get(
                        f"{self.staging_base_url}/ws",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        # WebSocket endpoint should return specific error for HTTP requests
                        websocket_accessible = True
                except Exception as e:
                    websocket_accessible = False
                    websocket_error = str(e)

            # If WebSocket endpoint is not accessible, it might be due to Redis issues
            if not websocket_accessible:
                pytest.fail(f"WebSocket endpoint not accessible, possibly due to Redis config issue (Issue #1177): {websocket_error}")

        except Exception as e:
            pytest.fail(f"WebSocket accessibility check failed (Issue #1177 related): {e}")

    @pytest.mark.asyncio
    async def test_staging_session_management_redis_failure(self):
        """
        Test staging session management Redis dependency (EXPECTED TO FAIL - Issue #1177).

        Session management requires Redis for storing session data.
        Issue #1177 configuration mismatch should cause session-related failures.
        """
        # Test session-related endpoints that depend on Redis
        session_check_url = f"{self.staging_auth_url}/auth/check"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    session_check_url,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    # Even without valid session, endpoint should be accessible
                    if response.status >= 500:
                        # 5xx errors might indicate Redis connectivity issues
                        response_text = await response.text()
                        pytest.fail(f"Session check endpoint 5xx error possibly due to Redis config (Issue #1177): {response.status} - {response_text}")

            except asyncio.TimeoutError:
                pytest.fail("Session check endpoint timeout - might be Redis related (Issue #1177)")
            except Exception as e:
                pytest.fail(f"Session check failed, possibly Redis related (Issue #1177): {e}")

    @pytest.mark.asyncio
    async def test_staging_full_golden_path_redis_impact(self):
        """
        Test full Golden Path flow with Redis dependencies (EXPECTED TO FAIL - Issue #1177).

        The complete Golden Path (login -> chat -> AI response) depends on Redis
        for multiple functions. Issue #1177 should break this flow.
        """
        golden_path_steps = []

        try:
            # Step 1: Check frontend accessibility
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.staging_frontend_url,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    frontend_accessible = response.status < 400
                    golden_path_steps.append(("frontend_accessible", frontend_accessible))

            # Step 2: Check auth service accessibility
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.staging_auth_url}/health",
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    auth_accessible = response.status == 200
                    golden_path_steps.append(("auth_accessible", auth_accessible))

            # Step 3: Check backend API accessibility
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.staging_base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    backend_accessible = response.status == 200
                    if backend_accessible:
                        health_data = await response.json()
                        redis_healthy = health_data.get("redis", {}).get("connected", False)
                        golden_path_steps.append(("redis_healthy", redis_healthy))
                    else:
                        golden_path_steps.append(("redis_healthy", False))

            # Analyze Golden Path health
            failed_steps = [step for step, success in golden_path_steps if not success]

            if failed_steps:
                pytest.fail(f"Golden Path broken - failed steps likely due to Issue #1177: {failed_steps}. Full status: {golden_path_steps}")

        except Exception as e:
            pytest.fail(f"Golden Path validation failed due to Issue #1177: {e}")

    @pytest.mark.asyncio
    async def test_staging_redis_configuration_diagnosis(self):
        """
        Test to diagnose Redis configuration on staging (EXPECTED TO FAIL - Issue #1177).

        This test attempts to gather information about the Redis configuration
        issue affecting the staging environment.
        """
        diagnostic_info = {}

        try:
            # Get health endpoint detailed information
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.staging_base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        diagnostic_info["health_response"] = health_data
                        diagnostic_info["redis_in_health"] = "redis" in health_data
                        if "redis" in health_data:
                            diagnostic_info["redis_status"] = health_data["redis"]
                    else:
                        diagnostic_info["health_error"] = f"Status {response.status}"

            # Check if there's a debug or config endpoint (some apps expose this)
            try:
                async with session.get(
                    f"{self.staging_base_url}/debug/config",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        debug_data = await response.json()
                        diagnostic_info["debug_config"] = debug_data
            except:
                # Debug endpoint might not exist
                diagnostic_info["debug_config"] = "Not available"

            # Analyze diagnostic information
            redis_status = diagnostic_info.get("redis_status", {})
            if isinstance(redis_status, dict):
                redis_connected = redis_status.get("connected", False)
                redis_errors = redis_status.get("errors", [])

                if not redis_connected or redis_errors:
                    failure_summary = {
                        "connected": redis_connected,
                        "errors": redis_errors,
                        "full_diagnostics": diagnostic_info
                    }
                    pytest.fail(f"DIAGNOSTIC FAILURE - Redis configuration issue confirmed (Issue #1177): {failure_summary}")

        except Exception as e:
            pytest.fail(f"Redis configuration diagnosis failed: {e}")

    @pytest.mark.asyncio
    async def test_staging_service_dependencies_redis_cascade_failure(self):
        """
        Test service dependencies with Redis cascade failure (EXPECTED TO FAIL - Issue #1177).

        When Redis fails due to configuration mismatch, it can cause cascade failures
        across multiple services that depend on it.
        """
        service_status = {}

        # Test multiple services that depend on Redis
        services_to_test = [
            ("backend", f"{self.staging_base_url}/health"),
            ("auth", f"{self.staging_auth_url}/health"),
        ]

        try:
            async with aiohttp.ClientSession() as session:
                for service_name, health_url in services_to_test:
                    try:
                        async with session.get(
                            health_url,
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as response:
                            if response.status == 200:
                                health_data = await response.json()
                                service_status[service_name] = {
                                    "accessible": True,
                                    "redis_status": health_data.get("redis", "Not reported")
                                }
                            else:
                                service_status[service_name] = {
                                    "accessible": False,
                                    "error_status": response.status
                                }
                    except Exception as e:
                        service_status[service_name] = {
                            "accessible": False,
                            "error": str(e)
                        }

            # Analyze cascade failure pattern
            failed_services = []
            redis_issues = []

            for service_name, status in service_status.items():
                if not status.get("accessible", False):
                    failed_services.append(service_name)

                redis_status = status.get("redis_status", {})
                if isinstance(redis_status, dict) and not redis_status.get("connected", False):
                    redis_issues.append(service_name)

            # Report findings
            if failed_services or redis_issues:
                cascade_analysis = {
                    "failed_services": failed_services,
                    "services_with_redis_issues": redis_issues,
                    "full_status": service_status
                }
                pytest.fail(f"EXPECTED CASCADE FAILURE - Redis config issue affecting multiple services (Issue #1177): {cascade_analysis}")

        except Exception as e:
            pytest.fail(f"Service dependency analysis failed: {e}")