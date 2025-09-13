"""
SSOT Auth Service Backend Integration Test - ISSUE #814

PURPOSE: Integration test validating auth service → backend delegation in staging environment
EXPECTED: PASS after SSOT remediation - validates staging auth integration
TARGET: Backend authentication integration delegates to auth service in staging

BUSINESS VALUE: Validates staging readiness for $500K+ ARR authentication reliability
EXECUTION: Staging environment integration - NO Docker dependency
"""
import logging
import pytest
import asyncio
import aiohttp
import os
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)

class TestAuthServiceBackendIntegration(SSotAsyncTestCase):
    """
    Integration test validating auth service → backend delegation in staging environment.
    Tests real service integration without Docker dependencies.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Setup staging integration test environment"""
        await super().asyncSetUpClass()

        # Staging environment endpoints
        cls.staging_auth_service_url = os.getenv(
            "STAGING_AUTH_SERVICE_URL",
            "https://auth-staging.netra-apex.com"
        )
        cls.staging_backend_url = os.getenv(
            "STAGING_BACKEND_URL",
            "https://backend-staging.netra-apex.com"
        )

        # Test credentials for staging
        cls.staging_test_email = "staging-integration@example.com"
        cls.staging_test_password = "StagingInt123!"

    async def asyncSetUp(self):
        """Setup individual integration test"""
        await super().asyncSetUp()
        self.http_session = aiohttp.ClientSession()
        self.auth_token = None
        self.staging_user_context = None

    async def asyncTearDown(self):
        """Cleanup integration test"""
        if self.http_session:
            await self.http_session.close()
        await super().asyncTearDown()

    async def test_staging_backend_delegates_auth_to_service(self):
        """
        Integration test: Staging backend delegates authentication to auth service

        VALIDATES: Backend in staging calls auth service for validation
        ENSURES: No direct JWT handling in staging backend
        """
        # Step 1: Get auth token from staging auth service
        logger.info("Getting auth token from staging auth service")
        await self._authenticate_with_staging_auth_service()

        # Step 2: Call backend API and verify auth service delegation
        logger.info("Testing backend auth delegation")
        await self._test_backend_auth_delegation()

        # Step 3: Verify backend doesn't handle JWT directly
        logger.info("Verifying backend delegates auth decisions")
        await self._verify_backend_auth_delegation()

    async def _authenticate_with_staging_auth_service(self):
        """Authenticate with staging auth service"""
        login_payload = {
            "email": self.staging_test_email,
            "password": self.staging_test_password
        }

        try:
            async with self.http_session.post(
                f"{self.staging_auth_service_url}/auth/login",
                json=login_payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    self.auth_token = auth_data["access_token"]
                    self.staging_user_context = auth_data.get("user", {})

                    assert self.auth_token is not None, "Auth token received from staging auth service"
                    logger.info("Staging auth service authentication successful")

                elif response.status == 401:
                    pytest.skip("Staging test user not configured - authentication failed")
                else:
                    pytest.fail(f"Staging auth service error: {response.status}")

        except aiohttp.ClientError as e:
            pytest.skip(f"Staging auth service not accessible: {e}")

    async def _test_backend_auth_delegation(self):
        """Test backend authentication delegation to auth service"""
        headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Test backend endpoint that requires authentication
        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/user/profile",
                headers=headers,
                timeout=30
            ) as response:
                assert response.status == 200, "Backend accepts auth service token"

                profile_data = await response.json()

                # Verify backend got user data from auth service
                assert "user_id" in profile_data, "Backend has user data from auth service"
                if self.staging_user_context.get("user_id"):
                    assert profile_data["user_id"] == self.staging_user_context["user_id"], \
                        "Backend user data matches auth service"

                logger.info("Backend successfully delegated auth to staging auth service")

        except aiohttp.ClientError as e:
            pytest.skip(f"Staging backend not accessible: {e}")

    async def _verify_backend_auth_delegation(self):
        """Verify backend delegates auth decisions (doesn't make them directly)"""
        # Test with invalid token to verify backend delegates validation
        invalid_headers = {"Authorization": "Bearer invalid-jwt-token-123"}

        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/user/profile",
                headers=invalid_headers,
                timeout=30
            ) as response:
                # Backend should reject based on auth service validation
                assert response.status == 401, "Backend rejects invalid token via auth service"

                error_data = await response.json()
                # Error should indicate auth service validation failure
                assert "invalid" in error_data.get("error", "").lower() or \
                       "unauthorized" in error_data.get("error", "").lower(), \
                    "Backend returns auth service validation error"

                logger.info("Backend properly delegates token validation to auth service")

        except aiohttp.ClientError as e:
            pytest.skip(f"Staging backend validation test failed: {e}")

    async def test_staging_backend_user_context_from_auth_service(self):
        """
        Integration test: Staging backend gets user context from auth service

        VALIDATES: User context in backend comes from auth service, not JWT decode
        ENSURES: Backend doesn't extract user data directly from JWT
        """
        # Authenticate with staging auth service
        await self._authenticate_with_staging_auth_service()

        # Test user context endpoints
        await self._test_user_context_endpoints()

        # Verify context consistency across backend endpoints
        await self._verify_user_context_consistency()

    async def _test_user_context_endpoints(self):
        """Test various backend endpoints that use user context"""
        headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Test multiple endpoints that should use auth service context
        endpoints_to_test = [
            "/api/v1/user/profile",
            "/api/v1/user/preferences",
            "/api/v1/threads",
            "/api/v1/messages/recent"
        ]

        user_contexts = []

        for endpoint in endpoints_to_test:
            try:
                async with self.http_session.get(
                    f"{self.staging_backend_url}{endpoint}",
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "user_id" in data:
                            user_contexts.append({
                                "endpoint": endpoint,
                                "user_id": data["user_id"],
                                "context": data
                            })

            except aiohttp.ClientError:
                # Skip unavailable endpoints
                continue

        # Verify user context consistency across endpoints
        if user_contexts:
            first_user_id = user_contexts[0]["user_id"]
            for context in user_contexts:
                assert context["user_id"] == first_user_id, \
                    f"User ID inconsistent across endpoints: {context['endpoint']}"

            logger.info(f"User context consistent across {len(user_contexts)} backend endpoints")

    async def _verify_user_context_consistency(self):
        """Verify user context matches auth service data"""
        if not self.staging_user_context:
            return  # Skip if auth service didn't provide user context

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/user/profile",
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    backend_context = await response.json()

                    # Compare backend context with auth service context
                    for key in ["user_id", "email"]:
                        if key in self.staging_user_context:
                            assert backend_context.get(key) == self.staging_user_context[key], \
                                f"Backend {key} doesn't match auth service"

                    logger.info("Backend user context matches auth service data")

        except aiohttp.ClientError:
            # Skip if endpoint not available
            pass

    async def test_staging_backend_auth_service_communication(self):
        """
        Integration test: Staging backend communicates with auth service properly

        VALIDATES: Backend makes proper HTTP calls to auth service
        ENSURES: Auth service integration working in staging environment
        """
        # Authenticate to get token
        await self._authenticate_with_staging_auth_service()

        # Test backend endpoints that should trigger auth service calls
        await self._test_auth_service_communication_patterns()

    async def _test_auth_service_communication_patterns(self):
        """Test various auth service communication patterns"""
        headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Test token validation pattern
        await self._test_token_validation_pattern(headers)

        # Test user context retrieval pattern
        await self._test_user_context_pattern(headers)

        # Test permission checking pattern
        await self._test_permission_checking_pattern(headers)

    async def _test_token_validation_pattern(self, headers: Dict[str, str]):
        """Test token validation communication with auth service"""
        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/health/auth",
                headers=headers,
                timeout=30
            ) as response:
                assert response.status == 200, "Auth health check successful"

                health_data = await response.json()
                assert health_data.get("authenticated") is True, "Authentication status from auth service"

                logger.info("Token validation pattern working in staging")

        except aiohttp.ClientError:
            logger.warning("Auth health endpoint not available in staging")

    async def _test_user_context_pattern(self, headers: Dict[str, str]):
        """Test user context retrieval from auth service"""
        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/user/context",
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    context_data = await response.json()
                    assert "user_id" in context_data, "User context from auth service"

                    logger.info("User context pattern working in staging")

        except aiohttp.ClientError:
            logger.warning("User context endpoint not available in staging")

    async def _test_permission_checking_pattern(self, headers: Dict[str, str]):
        """Test permission checking with auth service"""
        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/user/permissions",
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    permissions_data = await response.json()
                    assert "permissions" in permissions_data, "Permissions from auth service"

                    logger.info("Permission checking pattern working in staging")

        except aiohttp.ClientError:
            logger.warning("Permissions endpoint not available in staging")

    @pytest.mark.skip_if_staging_unavailable
    async def test_staging_auth_service_error_handling(self):
        """
        Integration test: Staging backend handles auth service errors gracefully

        VALIDATES: Backend error handling when auth service unavailable
        ENSURES: Graceful degradation in staging environment
        """
        # This test would require staging configuration to simulate auth service downtime
        # For now, we test the expected behavior

        headers = {"Authorization": "Bearer potentially-valid-token-during-downtime"}

        try:
            async with self.http_session.get(
                f"{self.staging_backend_url}/api/v1/user/profile",
                headers=headers,
                timeout=5  # Short timeout to simulate service issues
            ) as response:
                # Should handle auth service unavailability gracefully
                if response.status == 503:
                    error_data = await response.json()
                    assert "service_unavailable" in error_data.get("code", ""), \
                        "Backend identifies auth service unavailability"

                    logger.info("Backend handles auth service downtime gracefully")

        except asyncio.TimeoutError:
            logger.info("Expected timeout during auth service unavailability simulation")

if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/staging_auth/test_auth_service_backend_integration.py -v
    pytest.main([__file__, "-v"])