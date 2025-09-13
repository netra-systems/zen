"""
E2E Staging Tests for Issue #631: HTTP 403 WebSocket Authentication Reproduction

Business Value:
- Reproduces $500K+ ARR blocking issue in live staging environment
- Validates HTTP 403 WebSocket authentication failures
- Provides real-world validation of auth service integration

CRITICAL: These tests reproduce actual HTTP 403 errors in staging environment.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Optional, Any
import websockets
import requests
import logging

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import IsolatedEnvironment

# Configure logging to capture WebSocket errors
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestWebSocket403ReproductionStaging(SSotAsyncTestCase):
    """E2E tests reproducing HTTP 403 WebSocket errors in staging environment."""

    def setUp(self):
        """Set up staging test environment."""
        super().setUp()
        
        # Get staging configuration
        self.staging_config = get_staging_config()
        self.auth_config = E2EAuthConfig.for_staging()
        self.auth_helper = E2EAuthHelper(config=self.auth_config, environment="staging")
        self.env = IsolatedEnvironment()
        
        # Staging URLs
        self.staging_backend_url = self.staging_config.get("BACKEND_URL", "https://netra-backend-staging.netra.ai")
        self.staging_websocket_url = self.staging_config.get("WEBSOCKET_URL", "wss://netra-backend-staging.netra.ai/ws")
        self.staging_auth_service_url = self.staging_config.get("AUTH_SERVICE_URL", None)
        
        logger.info(f"Staging Backend URL: {self.staging_backend_url}")
        logger.info(f"Staging WebSocket URL: {self.staging_websocket_url}")
        logger.info(f"Staging Auth Service URL: {self.staging_auth_service_url}")

    async def asyncSetUp(self):
        """Set up async test components."""
        await super().asyncSetUp()
        
        # Verify staging environment accessibility
        try:
            health_response = requests.get(f"{self.staging_backend_url}/health", timeout=10)
            if health_response.status_code not in [200, 404]:
                self.skipTest(f"Staging backend not accessible: {health_response.status_code}")
        except requests.exceptions.RequestException as e:
            self.skipTest(f"Cannot reach staging backend: {e}")

    async def test_reproduce_http_403_websocket_handshake(self):
        """
        CRITICAL REPRODUCTION TEST: Exact reproduction of staging 403 errors.
        
        This test reproduces the exact HTTP 403 WebSocket authentication failure
        pattern seen in Issue #631 staging environment.
        """
        logger.info("REPRODUCING: HTTP 403 WebSocket authentication failure in staging")
        
        # ARRANGE: Get authentication token from staging auth service
        try:
            # This might fail due to missing AUTH_SERVICE_URL configuration
            auth_token = await self.auth_helper.get_valid_jwt_token()
            logger.info(f"Retrieved auth token: {auth_token[:20]}...")
        except Exception as e:
            logger.error(f"Failed to get auth token - this may indicate AUTH_SERVICE_URL issue: {e}")
            # Continue test to reproduce 403 without token
            auth_token = None
        
        # ACT: Attempt WebSocket connection to staging
        websocket_headers = {}
        if auth_token:
            websocket_headers["Authorization"] = f"Bearer {auth_token}"
        
        websocket_headers.update({
            "Origin": "https://netra.ai",
            "User-Agent": "Netra-E2E-Test/1.0"
        })
        
        start_time = time.time()
        connection_error = None
        
        try:
            # This should reproduce the HTTP 403 error from Issue #631
            async with websockets.connect(
                self.staging_websocket_url,
                extra_headers=websocket_headers,
                timeout=30,  # Give enough time to see the 403 error
                ping_interval=None,  # Disable ping to avoid connection interference
                ping_timeout=None
            ) as websocket:
                
                logger.info("WebSocket connection established - this indicates issue may be resolved")
                
                # Test basic communication
                test_message = {"type": "ping", "timestamp": time.time()}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                logger.info(f"WebSocket response: {response}")
                
        except websockets.exceptions.WebSocketException as e:
            connection_error = e
            logger.error(f"WebSocket connection failed: {e}")
            
            # Check if this is the expected HTTP 403 error
            if "403" in str(e) or "Forbidden" in str(e):
                logger.error("REPRODUCED: HTTP 403 WebSocket authentication failure - Issue #631")
            else:
                logger.error(f"Different WebSocket error encountered: {e}")
        
        except asyncio.TimeoutError:
            connection_error = "Timeout during WebSocket handshake"
            logger.error("WebSocket handshake timeout - may indicate auth service communication failure")
        
        except Exception as e:
            connection_error = e
            logger.error(f"Unexpected WebSocket connection error: {e}")
        
        end_time = time.time()
        connection_duration = end_time - start_time
        
        # ASSERT: Document the reproduction results
        if connection_error:
            if "403" in str(connection_error) or "Forbidden" in str(connection_error):
                self.fail(
                    f"REPRODUCED Issue #631: HTTP 403 WebSocket authentication failure. "
                    f"Error: {connection_error}. "
                    f"Connection attempt duration: {connection_duration:.2f}s. "
                    f"This confirms the root cause - backend cannot authenticate with auth service."
                )
            else:
                self.fail(
                    f"WebSocket connection failed with different error: {connection_error}. "
                    f"Duration: {connection_duration:.2f}s. "
                    f"This may indicate a related authentication issue."
                )
        else:
            logger.info("WebSocket connection succeeded - Issue #631 may be resolved")

    async def test_websocket_connection_with_valid_jwt(self):
        """
        Test WebSocket connection with valid JWT token from staging auth service.
        
        This validates the expected successful authentication flow.
        """
        logger.info("Testing WebSocket connection with valid JWT token")
        
        # ARRANGE: Get valid JWT token
        try:
            auth_token = await self.auth_helper.get_valid_jwt_token()
            self.assertIsNotNone(auth_token, "Should be able to get valid JWT token from auth service")
        except Exception as e:
            self.skipTest(f"Cannot get valid JWT token - auth service integration issue: {e}")
        
        # ACT: Connect with valid token
        websocket_headers = {
            "Authorization": f"Bearer {auth_token}",
            "Origin": "https://netra.ai"
        }
        
        connection_successful = False
        
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                extra_headers=websocket_headers,
                timeout=15
            ) as websocket:
                connection_successful = True
                logger.info("WebSocket connection successful with valid JWT")
                
                # Test message exchange
                test_message = {"type": "auth_test", "user_id": "test-user"}
                await websocket.send(json.dumps(test_message))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                logger.info(f"WebSocket response: {response}")
                
        except Exception as e:
            logger.error(f"WebSocket connection failed even with valid JWT: {e}")
            self.fail(f"WebSocket connection should succeed with valid JWT token. Error: {e}")
        
        # ASSERT: Connection should succeed with valid token
        self.assertTrue(
            connection_successful,
            "WebSocket connection should succeed with valid JWT token from auth service"
        )

    async def test_websocket_connection_with_invalid_jwt(self):
        """
        Test WebSocket connection with invalid JWT token - should return 403.
        
        This validates proper error handling for invalid tokens.
        """
        logger.info("Testing WebSocket connection with invalid JWT token")
        
        # ARRANGE: Use invalid JWT token
        invalid_tokens = [
            "invalid-jwt-token",
            "Bearer invalid-token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",
            ""
        ]
        
        for invalid_token in invalid_tokens:
            with self.subTest(token=invalid_token[:20] + "..."):
                
                websocket_headers = {}
                if invalid_token:
                    websocket_headers["Authorization"] = f"Bearer {invalid_token}"
                websocket_headers["Origin"] = "https://netra.ai"
                
                # ACT: Attempt connection with invalid token
                got_403_error = False
                
                try:
                    async with websockets.connect(
                        self.staging_websocket_url,
                        extra_headers=websocket_headers,
                        timeout=10
                    ) as websocket:
                        logger.warning("WebSocket connection succeeded with invalid token - security issue!")
                        
                except websockets.exceptions.WebSocketException as e:
                    if "403" in str(e) or "Forbidden" in str(e):
                        got_403_error = True
                        logger.info(f"Expected 403 error for invalid token: {e}")
                    else:
                        logger.error(f"Unexpected error for invalid token: {e}")
                
                # ASSERT: Should get 403 error for invalid tokens
                self.assertTrue(
                    got_403_error,
                    f"Should get HTTP 403 error for invalid JWT token: {invalid_token[:20]}..."
                )

    def test_auth_service_url_staging_configuration(self):
        """
        Test AUTH_SERVICE_URL configuration in staging environment.
        
        This validates that staging has proper auth service URL configuration.
        """
        logger.info("Testing AUTH_SERVICE_URL configuration in staging")
        
        # ARRANGE: Check staging configuration
        staging_auth_url = self.staging_auth_service_url
        
        # ACT & ASSERT: Validate auth service URL configuration
        if not staging_auth_url:
            self.fail(
                "AUTH_SERVICE_URL not configured in staging environment. "
                "This is likely the root cause of Issue #631 - backend cannot communicate with auth service."
            )
        
        self.assertTrue(
            staging_auth_url.startswith(("http://", "https://")),
            f"AUTH_SERVICE_URL should be valid URL: {staging_auth_url}"
        )
        
        # Test auth service accessibility
        try:
            health_url = f"{staging_auth_url}/health"
            response = requests.get(health_url, timeout=10)
            
            logger.info(f"Auth service health check: {response.status_code}")
            
            # Should be able to reach auth service
            self.assertTrue(
                response.status_code in [200, 404, 405],  # Various acceptable responses
                f"Auth service should be accessible at {staging_auth_url}. "
                f"Status: {response.status_code}. "
                f"This may contribute to Issue #631 if auth service is unreachable."
            )
            
        except requests.exceptions.RequestException as e:
            self.fail(
                f"Cannot reach auth service at {staging_auth_url}. "
                f"This is likely contributing to Issue #631 WebSocket 403 errors. "
                f"Error: {e}"
            )

    async def test_websocket_connection_timeout_scenarios(self):
        """
        Test WebSocket connection timeout scenarios during auth.
        
        This validates timeout handling during authentication process.
        """
        logger.info("Testing WebSocket connection timeout scenarios")
        
        # ARRANGE: Use very short timeout to test timeout handling
        short_timeout = 1.0  # 1 second timeout
        
        try:
            auth_token = await self.auth_helper.get_valid_jwt_token()
        except Exception as e:
            self.skipTest(f"Cannot get auth token for timeout test: {e}")
        
        websocket_headers = {
            "Authorization": f"Bearer {auth_token}",
            "Origin": "https://netra.ai"
        }
        
        # ACT: Test connection with short timeout
        timeout_occurred = False
        start_time = time.time()
        
        try:
            async with websockets.connect(
                self.staging_websocket_url,
                extra_headers=websocket_headers,
                timeout=short_timeout
            ) as websocket:
                logger.info("WebSocket connection succeeded within short timeout")
                
        except asyncio.TimeoutError:
            timeout_occurred = True
            logger.info("WebSocket connection timed out as expected")
        except Exception as e:
            logger.error(f"WebSocket connection failed with error: {e}")
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # ASSERT: Validate timeout behavior
        if timeout_occurred:
            self.assertLessEqual(
                actual_duration, short_timeout + 1.0,  # Allow 1 second tolerance
                f"Timeout should occur within expected timeframe. "
                f"Actual: {actual_duration:.2f}s, Expected: <={short_timeout + 1.0}s"
            )
        else:
            logger.info(f"Connection completed in {actual_duration:.2f}s - no timeout needed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])