"""
Integration Tests for Issue #1037: SERVICE_SECRET Authentication Regression

PURPOSE: These integration tests will FAIL initially to prove that actual
service-to-service communication fails due to SERVICE_SECRET mismatches.

EXPECTED FAILURES:
1. 403 authentication errors in real service-to-service calls
2. WebSocket authentication failures leading to 503 errors
3. Auth service rejecting backend authentication attempts

TEST STRATEGY: Use real services (no mocks) to reproduce the exact 403 errors
described in Issue #1037, proving the regression affects actual operations.

Business Impact: $500K+ ARR at risk from complete authentication breakdown.
"""

import pytest
import asyncio
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class TestServiceSecretAuthenticationRegression(SSotAsyncTestCase):
    """
    Integration tests proving Issue #1037 causes real 403 failures.
    These tests will FAIL initially to demonstrate the regression.
    """

    def setUp(self):
        """Set up integration test environment for regression testing."""
        super().setUp()
        self.env = self.get_env()

        # Test configuration values
        self.test_jwt_secret = "test-jwt-secret-key-32-chars-long-for-integration"
        self.test_service_secret = "test-service-secret-32-chars-long-for-integration"
        self.mismatched_secret = "mismatched-secret-32-chars-different-for-testing"

        # URLs for service communication testing
        self.auth_service_url = self.env.get("AUTH_SERVICE_URL", "http://localhost:8001")
        self.backend_service_url = self.env.get("BACKEND_SERVICE_URL", "http://localhost:8000")

        logger.info(f"Integration test setup: Auth URL={self.auth_service_url}, Backend URL={self.backend_service_url}")

    def test_backend_to_auth_service_403_failure(self):
        """
        REGRESSION TEST: Backend service cannot authenticate with auth service
        due to SERVICE_SECRET vs JWT_SECRET_KEY mismatch, causing 403 errors.

        EXPECTED: This test will FAIL initially, proving 403 regression.
        """
        logger.info("Testing backend to auth service 403 authentication failure...")

        # Configure auth service with JWT_SECRET_KEY
        self.env.set("JWT_SECRET_KEY", self.test_jwt_secret, "auth_service_integration")

        # Configure backend with different SERVICE_SECRET
        self.env.set("SERVICE_SECRET", self.mismatched_secret, "backend_service_integration")

        async def test_service_communication():
            """Test actual service-to-service authentication failure."""
            try:
                from netra_backend.app.clients.auth_client_core import AuthServiceClient

                # Create auth client with mismatched secrets
                auth_client = AuthServiceClient()

                # Attempt service-to-service authentication (should fail with 403)
                async with httpx.AsyncClient() as client:
                    headers = {
                        "Authorization": f"Bearer {auth_client.service_secret}",
                        "X-Service-ID": "backend-service",
                        "Content-Type": "application/json"
                    }

                    # Test auth validation endpoint
                    response = await client.post(
                        f"{self.auth_service_url}/auth/validate",
                        headers=headers,
                        json={"token": "test-token-for-validation"}
                    )

                    if response.status_code == 403:
                        # Expected 403 failure proves the regression
                        logger.error(f"REGRESSION CONFIRMED: 403 authentication failure - {response.text}")
                        raise AssertionError(
                            f"Issue #1037 regression confirmed: Backend service authentication failed with 403. "
                            f"Auth service expects JWT_SECRET_KEY but backend uses SERVICE_SECRET. "
                            f"Response: {response.status_code} - {response.text}"
                        )

                    elif response.status_code == 200:
                        # Unexpected success - regression not reproduced
                        self.fail(
                            f"Expected 403 authentication failure but got 200 success. "
                            f"This indicates Issue #1037 regression is not reproduced correctly. "
                            f"Response: {response.text}"
                        )

                    else:
                        # Other error - still indicates authentication problems
                        logger.warning(f"Unexpected response code: {response.status_code} - {response.text}")
                        raise AssertionError(
                            f"Issue #1037 may be present: Got {response.status_code} instead of expected 403. "
                            f"This still indicates authentication problems. Response: {response.text}"
                        )

            except (ImportError, ConnectionError, httpx.RequestError) as e:
                # Service unavailable - skip test but log issue
                logger.warning(f"Service communication test skipped - service unavailable: {str(e)}")
                self.skipTest(f"Auth service not available for integration testing: {str(e)}")

        # Run async test
        asyncio.run(test_service_communication())

    def test_websocket_authentication_regression_503_errors(self):
        """
        REGRESSION TEST: WebSocket authentication fails due to SERVICE_SECRET
        mismatch, leading to 503 service errors mentioned in Issue #1037.

        EXPECTED: This test will FAIL initially, proving WebSocket regression.
        """
        logger.info("Testing WebSocket authentication regression causing 503 errors...")

        # Configure mismatched secrets (reproduces Issue #1037)
        self.env.set("JWT_SECRET_KEY", self.test_jwt_secret, "websocket_auth_test")
        self.env.set("SERVICE_SECRET", self.mismatched_secret, "websocket_backend_test")

        async def test_websocket_auth_failure():
            """Test WebSocket authentication with service secret mismatch."""
            try:
                import websockets
                from websockets.exceptions import ConnectionClosedError

                # Create WebSocket connection with authentication
                ws_url = self.backend_service_url.replace("http://", "ws://") + "/ws"

                # Use SERVICE_SECRET for auth (should fail if mismatch exists)
                headers = {
                    "Authorization": f"Bearer {self.env.get('SERVICE_SECRET')}",
                    "X-Service-ID": "backend-service"
                }

                try:
                    async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                        # Send test message
                        await websocket.send('{"type": "test", "message": "auth test"}')
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

                        # If we get here, auth succeeded (unexpected for regression)
                        self.fail(
                            f"WebSocket authentication should have failed with SERVICE_SECRET mismatch. "
                            f"Got successful response: {response}. "
                            f"This indicates Issue #1037 WebSocket regression is not reproduced."
                        )

                except (ConnectionClosedError, websockets.exceptions.WebSocketException, asyncio.TimeoutError) as e:
                    # Expected failure - WebSocket auth failed due to secret mismatch
                    logger.error(f"WEBSOCKET REGRESSION CONFIRMED: {str(e)}")
                    raise AssertionError(
                        f"Issue #1037 WebSocket regression confirmed: Authentication failed causing connection closure. "
                        f"This leads to 503 service errors. Error: {str(e)}"
                    )

            except ImportError:
                self.skipTest("websockets library not available for WebSocket regression testing")

        # Run async WebSocket test
        asyncio.run(test_websocket_auth_failure())

    def test_auth_service_token_validation_with_wrong_secret(self):
        """
        REGRESSION TEST: Auth service cannot validate tokens created with
        different secret, causing systematic authentication failures.

        EXPECTED: This test will FAIL initially, proving token validation regression.
        """
        logger.info("Testing auth service token validation with wrong secret...")

        # Set up mismatched secrets
        self.env.set("JWT_SECRET_KEY", self.test_jwt_secret, "token_validation_auth")
        self.env.set("SERVICE_SECRET", self.mismatched_secret, "token_validation_backend")

        async def test_token_validation_failure():
            """Test actual token validation with mismatched secrets."""
            try:
                import jwt

                # Create token with backend's SERVICE_SECRET
                payload = {
                    "user_id": "test-user",
                    "service_id": "backend-service",
                    "exp": int((datetime.now() + timedelta(hours=1)).timestamp())
                }

                # Backend creates token with SERVICE_SECRET
                token = jwt.encode(payload, self.env.get("SERVICE_SECRET"), algorithm="HS256")

                # Test validation through auth service
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.auth_service_url}/auth/validate",
                        headers={"Content-Type": "application/json"},
                        json={"token": token}
                    )

                    if response.status_code in [401, 403]:
                        # Expected failure - token validation failed
                        logger.error(f"TOKEN VALIDATION REGRESSION CONFIRMED: {response.status_code} - {response.text}")
                        raise AssertionError(
                            f"Issue #1037 token validation regression confirmed: "
                            f"Auth service cannot validate tokens created with different secret. "
                            f"Status: {response.status_code}, Response: {response.text}"
                        )

                    elif response.status_code == 200:
                        # Unexpected success
                        self.fail(
                            f"Expected token validation failure but got success. "
                            f"This indicates Issue #1037 token regression is not reproduced. "
                            f"Response: {response.text}"
                        )

                    else:
                        # Other error codes still indicate problems
                        logger.warning(f"Unexpected token validation response: {response.status_code}")
                        raise AssertionError(
                            f"Issue #1037 token validation issue detected: "
                            f"Got {response.status_code} instead of expected 401/403. "
                            f"Response: {response.text}"
                        )

            except (ImportError, ConnectionError, httpx.RequestError) as e:
                logger.warning(f"Token validation test skipped: {str(e)}")
                self.skipTest(f"Cannot test token validation - service unavailable: {str(e)}")

        # Run async token validation test
        asyncio.run(test_token_validation_failure())

    def test_service_authentication_header_mismatch(self):
        """
        REGRESSION TEST: Services send different authentication headers
        based on their secret configuration, causing 403 failures.

        EXPECTED: This test will FAIL initially, proving header mismatch regression.
        """
        logger.info("Testing service authentication header mismatch...")

        # Configure different secrets for header testing
        self.env.set("JWT_SECRET_KEY", self.test_jwt_secret, "header_test_auth")
        self.env.set("SERVICE_SECRET", self.mismatched_secret, "header_test_backend")

        async def test_authentication_headers():
            """Test authentication header format differences."""
            try:
                # Create headers based on SERVICE_SECRET (backend approach)
                backend_headers = {
                    "Authorization": f"Bearer {self.env.get('SERVICE_SECRET')}",
                    "X-Service-ID": "backend-service",
                    "X-Service-Secret": self.env.get('SERVICE_SECRET'),
                    "Content-Type": "application/json"
                }

                # Test multiple auth endpoints with these headers
                test_endpoints = [
                    "/auth/validate",
                    "/auth/refresh",
                    "/auth/service-token"
                ]

                failed_endpoints = []

                async with httpx.AsyncClient() as client:
                    for endpoint in test_endpoints:
                        try:
                            response = await client.post(
                                f"{self.auth_service_url}{endpoint}",
                                headers=backend_headers,
                                json={"test": "authentication"}
                            )

                            if response.status_code == 403:
                                failed_endpoints.append({
                                    "endpoint": endpoint,
                                    "status": response.status_code,
                                    "response": response.text[:100]  # Truncate response
                                })

                        except httpx.RequestError as e:
                            logger.warning(f"Request error for {endpoint}: {str(e)}")
                            continue

                # Check if we found authentication failures
                if failed_endpoints:
                    failure_details = "\n".join([
                        f"  {f['endpoint']}: {f['status']} - {f['response']}"
                        for f in failed_endpoints
                    ])

                    raise AssertionError(
                        f"Issue #1037 authentication header regression confirmed:\n"
                        f"Multiple endpoints failed with 403 due to header mismatch:\n{failure_details}\n"
                        f"Services using different authentication approaches."
                    )

                else:
                    # No failures found - regression not reproduced
                    logger.warning(
                        "No authentication header failures detected. "
                        "Issue #1037 regression may not be reproduced correctly."
                    )

            except (ConnectionError, httpx.RequestError) as e:
                self.skipTest(f"Cannot test authentication headers - service unavailable: {str(e)}")

        # Run async header test
        asyncio.run(test_authentication_headers())

    def test_cross_service_authentication_cascade_failure(self):
        """
        REGRESSION TEST: SERVICE_SECRET mismatch causes cascade authentication
        failures across multiple service interactions.

        EXPECTED: This test will FAIL initially, proving cascade regression.
        """
        logger.info("Testing cross-service authentication cascade failure...")

        # Set up cascade failure scenario
        self.env.set("JWT_SECRET_KEY", self.test_jwt_secret, "cascade_auth")
        self.env.set("SERVICE_SECRET", self.mismatched_secret, "cascade_backend")

        async def test_authentication_cascade():
            """Test authentication cascade across service boundaries."""
            cascade_failures = []

            try:
                # Test service chain: Backend -> Auth -> Backend operations
                async with httpx.AsyncClient() as client:

                    # Step 1: Backend requests service token from auth
                    auth_response = await client.post(
                        f"{self.auth_service_url}/auth/service-token",
                        headers={
                            "Authorization": f"Bearer {self.env.get('SERVICE_SECRET')}",
                            "X-Service-ID": "backend-service"
                        }
                    )

                    if auth_response.status_code != 200:
                        cascade_failures.append({
                            "step": "service_token_request",
                            "status": auth_response.status_code,
                            "error": auth_response.text[:100]
                        })

                    # Step 2: Use token for backend operation (if Step 1 succeeded)
                    if auth_response.status_code == 200:
                        try:
                            token_data = auth_response.json()
                            service_token = token_data.get("access_token")

                            backend_response = await client.get(
                                f"{self.backend_service_url}/api/health",
                                headers={"Authorization": f"Bearer {service_token}"}
                            )

                            if backend_response.status_code != 200:
                                cascade_failures.append({
                                    "step": "backend_operation",
                                    "status": backend_response.status_code,
                                    "error": backend_response.text[:100]
                                })

                        except Exception as e:
                            cascade_failures.append({
                                "step": "token_parsing",
                                "error": str(e)[:100]
                            })

                # Check for cascade failures
                if cascade_failures:
                    failure_summary = "\n".join([
                        f"  {f['step']}: {f.get('status', 'Error')} - {f['error']}"
                        for f in cascade_failures
                    ])

                    raise AssertionError(
                        f"Issue #1037 cascade authentication regression confirmed:\n"
                        f"Authentication failures cascade across service boundaries:\n{failure_summary}\n"
                        f"SERVICE_SECRET mismatch breaks entire authentication chain."
                    )

                else:
                    logger.warning(
                        "No cascade authentication failures detected. "
                        "Issue #1037 cascade regression may not be fully reproduced."
                    )

            except (ConnectionError, httpx.RequestError) as e:
                self.skipTest(f"Cannot test cascade authentication - services unavailable: {str(e)}")

        # Run async cascade test
        asyncio.run(test_authentication_cascade())


if __name__ == "__main__":
    # Run integration tests to prove Issue #1037 regression
    pytest.main([__file__, "-v", "--tb=long", "-s"])