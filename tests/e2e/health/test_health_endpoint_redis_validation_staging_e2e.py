"""
E2E tests for health endpoint Redis validation issues in staging environment.

These tests validate the complete end-to-end behavior of health endpoints
when Redis configuration is missing or invalid in staging environment.

Issue #598: Health endpoint should return 503 initially, 200 after configuration fix.
Test Plan Step 4: Execute tests that reproduce Redis configuration validation failures.
"""

import pytest
import asyncio
import aiohttp
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestHealthEndpointRedisValidationStagingE2E(SSotAsyncTestCase):
    """E2E tests for health endpoint Redis validation in staging environment."""

    # GCP Staging environment URL - must be accessible for E2E testing
    STAGING_BASE_URL = "https://netra-backend-staging-123456789-uc.a.run.app"
    STAGING_HEALTH_ENDPOINTS = [
        "/health",
        "/health/",
        "/health/ready",
        "/health/startup",
        "/health/backend"
    ]

    def setUp(self):
        """Set up E2E test environment."""
        super().setUp()

        # Enable environment isolation for test configuration
        self.env = get_env()
        self.env.enable_isolation()

        # Configure for staging environment validation
        self.env.set("ENVIRONMENT", "staging", source="e2e_health_redis")
        self.env.set("TEST_EXECUTION_MODE", "e2e", source="e2e_health_redis")

        # HTTP session for reuse across requests
        self.session = None

    def tearDown(self):
        """Clean up E2E test environment."""
        if self.session:
            asyncio.create_task(self.session.close())
        super().tearDown()

    async def get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for staging requests."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "netra-e2e-health-test/1.0"}
            )
        return self.session

    async def make_health_request(self, endpoint: str, expect_success: bool = True) -> Dict[str, Any]:
        """Make HTTP request to staging health endpoint."""
        url = f"{self.STAGING_BASE_URL}{endpoint}"

        session = await self.get_http_session()

        try:
            async with session.get(url) as response:
                response_data = {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }

                # Try to parse JSON response
                try:
                    response_data["json"] = await response.json()
                except Exception:
                    response_data["text"] = await response.text()

                return response_data

        except aiohttp.ClientError as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "url": url,
                "status_code": None
            }

    async def test_staging_health_endpoint_basic_accessibility(self):
        """Test that staging health endpoints are accessible."""
        for endpoint in self.STAGING_HEALTH_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = await self.make_health_request(endpoint)

                # Should be able to reach the endpoint (even if it returns 503)
                self.assertIsNotNone(response.get("status_code"),
                                   f"Could not reach staging endpoint {endpoint}: {response}")

                # Should not have connection errors
                self.assertNotIn("error", response,
                               f"Connection error for {endpoint}: {response}")

    async def test_staging_basic_health_response_format(self):
        """Test that staging health endpoint returns proper response format."""
        response = await self.make_health_request("/health")

        # Should have a status code
        self.assertIsNotNone(response.get("status_code"))

        # Should have JSON response
        self.assertIn("json", response, "Health endpoint should return JSON")

        json_data = response["json"]

        # Should have basic health response structure
        self.assertIn("status", json_data, "Health response should have 'status' field")

        # Status should be a known value
        status = json_data["status"]
        self.assertIn(status, ["healthy", "unhealthy", "degraded"],
                     f"Unexpected health status: {status}")

    async def test_staging_ready_endpoint_redis_configuration_validation(self):
        """Test staging ready endpoint response with Redis configuration issues."""
        response = await self.make_health_request("/health/ready")

        status_code = response.get("status_code")

        # CRITICAL TEST: If Redis configuration is missing, should return 503
        if status_code == 503:
            # This indicates the Redis configuration issue is present
            json_data = response.get("json", {})

            # Should provide meaningful error information
            self.assertIn("status", json_data)
            self.assertEqual(json_data["status"], "unhealthy")

            # Should indicate the specific issue
            message = json_data.get("message", "")
            self.assertTrue(
                any(keyword in message.lower() for keyword in ["redis", "configuration", "service", "readiness"]),
                f"Error message should indicate Redis/configuration issue: {message}"
            )

        elif status_code == 200:
            # If Redis is properly configured, should return healthy
            json_data = response.get("json", {})
            self.assertIn("status", json_data)
            self.assertIn(json_data["status"], ["ready", "healthy"])

        else:
            # Any other status code is unexpected
            self.fail(f"Unexpected status code {status_code} for ready endpoint: {response}")

    async def test_staging_startup_endpoint_detailed_checks(self):
        """Test staging startup endpoint provides detailed component checks."""
        response = await self.make_health_request("/health/startup")

        status_code = response.get("status_code")

        # Startup endpoint should provide detailed information regardless of status
        if status_code in [200, 503]:
            json_data = response.get("json", {})

            # Should have component checks
            if "checks" in json_data:
                checks = json_data["checks"]

                # Should check Redis specifically
                if "redis" in checks:
                    redis_check = checks["redis"]

                    # Redis check should have status information
                    self.assertIn("status", redis_check)

                    # If Redis fails, should provide error details
                    if redis_check["status"] in ["not_ready", "failed"]:
                        self.assertTrue(
                            "error" in redis_check or "message" in redis_check,
                            "Failed Redis check should provide error details"
                        )

    async def test_staging_backend_endpoint_capabilities_check(self):
        """Test staging backend endpoint capability checks."""
        response = await self.make_health_request("/health/backend")

        status_code = response.get("status_code")

        if status_code in [200, 503]:
            json_data = response.get("json", {})

            # Should have capabilities information
            if "capabilities" in json_data:
                capabilities = json_data["capabilities"]

                # Should check database connectivity (which might be affected by Redis issues)
                self.assertIn("database_connectivity", capabilities)

                # Should have golden path readiness information
                self.assertIn("golden_path_ready", json_data)

    async def test_staging_health_endpoint_headers_and_cors(self):
        """Test staging health endpoint CORS and header configuration."""
        response = await self.make_health_request("/health")

        headers = response.get("headers", {})

        # Should have proper content type
        content_type = headers.get("content-type", "")
        self.assertIn("application/json", content_type)

        # Should handle CORS properly (if configured)
        # Note: CORS headers may not be present in all staging configurations

    async def test_staging_health_all_endpoints_consistency(self):
        """Test that all staging health endpoints are consistent in their response format."""
        responses = {}

        for endpoint in self.STAGING_HEALTH_ENDPOINTS:
            responses[endpoint] = await self.make_health_request(endpoint)

        # All endpoints should be reachable
        for endpoint, response in responses.items():
            with self.subTest(endpoint=endpoint):
                self.assertIsNotNone(response.get("status_code"),
                                   f"Endpoint {endpoint} not reachable")

                # Should return JSON (if not connection error)
                if response.get("status_code") is not None:
                    self.assertTrue(
                        "json" in response or "text" in response,
                        f"Endpoint {endpoint} should return content"
                    )

    async def test_staging_health_redis_specific_error_scenarios(self):
        """Test specific Redis error scenarios in staging health endpoints."""
        # Test the ready endpoint specifically for Redis configuration issues
        ready_response = await self.make_health_request("/health/ready")
        startup_response = await self.make_health_request("/health/startup")

        # If Redis configuration is missing, both should reflect this
        ready_status = ready_response.get("status_code")
        startup_status = startup_response.get("status_code")

        if ready_status == 503:
            # Ready endpoint indicates configuration issues
            ready_json = ready_response.get("json", {})

            # Check if this is specifically a Redis configuration issue
            message = ready_json.get("message", "").lower()
            details = str(ready_json.get("details", {})).lower()

            redis_related = any(keyword in message or keyword in details
                              for keyword in ["redis", "configuration", "service unavailable"])

            if redis_related:
                # This confirms the Redis configuration validation issue
                # Startup endpoint should also reflect the issue
                startup_json = startup_response.get("json", {})

                if "checks" in startup_json:
                    checks = startup_json["checks"]
                    if "redis" in checks:
                        redis_check = checks["redis"]
                        self.assertIn("status", redis_check)
                        self.assertIn(redis_check["status"], ["not_ready", "failed", "error"])


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.staging
class TestHealthEndpointRedisValidationStagingE2EAsync:
    """Async-based E2E tests for staging health endpoint Redis validation."""

    STAGING_BASE_URL = "https://netra-backend-staging-123456789-uc.a.run.app"

    async def test_redis_configuration_issue_reproduction(self):
        """Reproduce the Redis configuration validation issue in staging."""
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Test the ready endpoint which should show Redis configuration issues
            url = f"{self.STAGING_BASE_URL}/health/ready"

            async with session.get(url) as response:
                status_code = response.status

                try:
                    json_data = await response.json()
                except Exception:
                    json_data = {"text": await response.text()}

                # If this test passes with status_code == 503, it confirms the issue
                # If it passes with status_code == 200, Redis is properly configured

                assert status_code in [200, 503], f"Unexpected status code: {status_code}"

                if status_code == 503:
                    # Confirms the Redis configuration validation issue
                    assert "status" in json_data
                    assert json_data["status"] in ["unhealthy", "not_ready"]

                    # Should provide meaningful error information
                    message = json_data.get("message", "")
                    assert len(message) > 0, "Should provide error message"

                elif status_code == 200:
                    # Redis is properly configured
                    assert "status" in json_data
                    assert json_data["status"] in ["ready", "healthy"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])