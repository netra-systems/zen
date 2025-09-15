#!/usr/bin/env python3
"""
Integration test for /auth/validate-token-and-get-user endpoint

This test ensures that the endpoint exists and functions correctly to prevent
future regressions like Issue #1169 where the endpoint returned 404.

Business Value: Protects $500K+ ARR Golden Path authentication functionality
"""
import pytest
import asyncio
import aiohttp
import logging
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)


class TestAuthValidateTokenAndGetUserEndpoint(SSotAsyncTestCase):
    """
    Integration tests for auth validate-token-and-get-user endpoint

    This test suite validates that:
    1. The endpoint exists and is accessible (prevents 404 regression)
    2. The endpoint handles invalid tokens properly
    3. The endpoint returns the expected response structure
    4. The endpoint works across all environments (staging, production)
    """

    def setUp(self):
        """Set up test instance with environment configuration"""
        super().setUp()
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.prod_auth_url = "https://auth.netrasystems.ai"
        self.test_endpoint = "/auth/validate-token-and-get-user"

    async def test_endpoint_exists_staging(self):
        """
        Test that the endpoint exists in staging environment

        This is the critical test that would have caught Issue #1169
        """
        staging_auth_url = "https://auth.staging.netrasystems.ai"
        test_endpoint = "/auth/validate-token-and-get-user"
        url = f"{staging_auth_url}{test_endpoint}"

        async with aiohttp.ClientSession() as session:
            # Test with invalid token to ensure endpoint exists
            payload = {"token": "invalid_test_token"}
            headers = {"Content-Type": "application/json"}

            async with session.post(url, json=payload, headers=headers) as response:
                # Should NOT return 404 (that was the bug)
                self.assertNotEqual(response.status, 404,
                                   f"Endpoint {url} returned 404 - this is Issue #1169 regression!")

                # Should return 200 with error response for invalid token
                self.assertEqual(response.status, 200)

                data = await response.json()

                # Validate response structure
                self.assertIn("valid", data)
                self.assertFalse(data["valid"])  # Invalid token should return valid=false
                self.assertIn("error", data)

                logger.info(f"✅ Endpoint exists in staging: {url}")
                logger.info(f"Response: {data}")

    async def test_endpoint_response_structure(self):
        """Test that the endpoint returns the correct response structure"""
        url = f"{self.staging_auth_url}{self.test_endpoint}"

        async with aiohttp.ClientSession() as session:
            # Test with Authorization header
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_test_token"
            }

            async with session.post(url, json={}, headers=headers) as response:
                self.assertEqual(response.status, 200)
                data = await response.json()

                # Validate required fields exist
                required_fields = ["valid"]
                for field in required_fields:
                    self.assertIn(field, data, f"Response missing required field: {field}")

                # For invalid token, should have error
                if not data.get("valid", True):
                    self.assertIn("error", data, "Invalid token response should include error message")

    async def test_endpoint_handles_both_auth_methods(self):
        """Test that endpoint handles both Authorization header and request body token"""
        url = f"{self.staging_auth_url}{self.test_endpoint}"

        async with aiohttp.ClientSession() as session:
            test_token = "test_token_12345"

            # Test 1: Authorization header method
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {test_token}"
            }

            async with session.post(url, json={}, headers=headers) as response:
                self.assertEqual(response.status, 200)
                data1 = await response.json()
                self.assertIn("valid", data1)

            # Test 2: Request body method
            headers = {"Content-Type": "application/json"}
            payload = {"token": test_token}

            async with session.post(url, json=payload, headers=headers) as response:
                self.assertEqual(response.status, 200)
                data2 = await response.json()
                self.assertIn("valid", data2)

            # Both methods should work and return similar structure
            self.assertEqual(data1.get("valid"), data2.get("valid"))

    async def test_endpoint_handles_missing_token(self):
        """Test that endpoint handles missing token gracefully"""
        url = f"{self.staging_auth_url}{self.test_endpoint}"

        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/json"}

            async with session.post(url, json={}, headers=headers) as response:
                self.assertEqual(response.status, 200)
                data = await response.json()

                self.assertIn("valid", data)
                self.assertFalse(data["valid"])
                self.assertIn("error", data)
                self.assertIn("No token provided", data["error"])

    @pytest.mark.skip(reason="Production endpoint requires valid tokens for testing")
    async def test_endpoint_exists_production(self):
        """
        Test that the endpoint exists in production environment

        Note: Skipped by default to avoid hitting production unnecessarily
        """
        url = f"{self.prod_auth_url}{self.test_endpoint}"

        async with aiohttp.ClientSession() as session:
            payload = {"token": "invalid_test_token"}
            headers = {"Content-Type": "application/json"}

            async with session.post(url, json=payload, headers=headers) as response:
                # Should NOT return 404
                self.assertNotEqual(response.status, 404,
                                   f"Production endpoint {url} returned 404!")
                self.assertEqual(response.status, 200)

    def test_endpoint_in_openapi_spec(self):
        """Test that the endpoint is documented in the OpenAPI specification"""
        # This test validates that the endpoint is properly registered
        # by checking it exists in the auth service configuration
        from auth_service.auth_core.routes.auth_routes import router

        # Get all routes from the router
        routes = [route for route in router.routes]
        endpoint_paths = [getattr(route, 'path', None) for route in routes]

        self.assertIn("/auth/validate-token-and-get-user", endpoint_paths,
                     "Endpoint missing from auth routes - this indicates a registration issue")

    async def test_endpoint_cors_headers(self):
        """Test that the endpoint includes proper CORS headers"""
        url = f"{self.staging_auth_url}{self.test_endpoint}"

        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Origin": "https://app.staging.netrasystems.ai"
            }
            payload = {"token": "test_token"}

            async with session.post(url, json=payload, headers=headers) as response:
                self.assertEqual(response.status, 200)

                # Check for CORS headers
                cors_headers = response.headers
                logger.info(f"CORS headers: {dict(cors_headers)}")

                # Validate CORS is configured (exact headers may vary)
                self.assertTrue(
                    any(header.lower().startswith('access-control') for header in cors_headers),
                    "CORS headers missing from response"
                )


def run_async_test():
    """Helper function to run async tests"""
    async def run_all_tests():
        test_instance = TestAuthValidateTokenAndGetUserEndpoint()
        test_instance.setUp()

        # Run all async tests
        await test_instance.test_endpoint_exists_staging()
        await test_instance.test_endpoint_response_structure()
        await test_instance.test_endpoint_handles_both_auth_methods()
        await test_instance.test_endpoint_handles_missing_token()
        await test_instance.test_endpoint_cors_headers()

        print("✅ All async tests passed!")

    asyncio.run(run_all_tests())


if __name__ == "__main__":
    # Can be run directly for quick validation
    run_async_test()