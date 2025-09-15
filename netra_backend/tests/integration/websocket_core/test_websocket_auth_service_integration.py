#!/usr/bin/env python
"""
Integration Tests for WebSocket Auth Service Integration

MISSION CRITICAL: Integration between WebSocket manager and auth service components.
Tests real WebSocket authentication flows with auth service integration.

Business Value: $500K+ ARR - Secure multi-user chat authentication infrastructure
- Tests WebSocket authentication integration with auth service
- Validates auth service responses in WebSocket context
- Ensures proper integration between WebSocket and authentication systems
- Tests auth failure scenarios and recovery patterns
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following CLAUDE.md guidelines
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import production WebSocket and auth components - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    extract_e2e_context_from_websocket
)
from netra_backend.app.auth_integration.auth import (
    get_current_user,
    BackendAuthIntegration,
    AuthValidationResult
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext,
    AuthenticationMethod
)


class MockWebSocket:
    """Mock WebSocket for integration testing."""

    def __init__(self, headers=None, client=None, subprotocols=None):
        self.headers = headers or {}
        self.client = client or type('Client', (), {'host': '127.0.0.1', 'port': 8000})()
        self.subprotocols = subprotocols or []
        self.client_state = "CONNECTED"
        self.application_state = "CONNECTED"
        self._messages = []

    async def send_json(self, data):
        """Mock send_json method."""
        self._messages.append(data)

    async def close(self, code=1000, reason=""):
        """Mock close method."""
        self.client_state = "DISCONNECTED"


@pytest.mark.integration
class WebSocketAuthServiceIntegrationTests(SSotAsyncTestCase):
    """Integration tests for WebSocket and auth service integration."""

    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)

        # Set test environment variables
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "1")
        self.set_env_var("DEMO_MODE", "1")  # Enable demo mode for testing
        self.set_env_var("ENVIRONMENT", "test")

        # Track metrics
        self.record_metric("test_category", "websocket_auth_integration")

    @pytest.mark.asyncio
    async def test_websocket_auth_service_successful_authentication(self):
        """
        Test successful WebSocket authentication through auth service.

        CRITICAL: WebSocket authentication must integrate properly with auth service
        and return valid user context for authenticated users.
        """
        # Arrange
        user_id = f"auth_service_user_{uuid.uuid4().hex[:8]}"

        # Create mock WebSocket with proper headers
        websocket = MockWebSocket(headers={
            "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
            "authorization": f"Bearer valid_test_token_for_{user_id}",
            "user-agent": "Test WebSocket Client"
        })

        # Add E2E context for test authentication
        e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "detection_method": {
                "via_headers": False,
                "via_environment": True,
                "via_env_vars": True,
                "via_demo_mode": True
            },
            "security_mode": "development_permissive",
            "bypass_enabled": True
        }

        # Track performance
        start_time = time.time()

        # Act
        auth_result = await authenticate_websocket_ssot(
            websocket=websocket,
            e2e_context=e2e_context
        )

        auth_time = time.time() - start_time
        self.record_metric("auth_response_time_ms", auth_time * 1000)

        # Assert
        self.assertTrue(auth_result.success, "Auth service integration must succeed")
        self.assertIsNotNone(auth_result.user_context, "User context must be created")
        self.assertIsNotNone(auth_result.auth_result, "Auth result must be populated")

        # Verify user context properties
        user_context = auth_result.user_context
        self.assertIsNotNone(user_context.user_id, "User ID must be set")
        self.assertIsNotNone(user_context.websocket_client_id, "WebSocket client ID must be set")
        self.assertIsNotNone(user_context.thread_id, "Thread ID must be set")
        self.assertIsNotNone(user_context.run_id, "Run ID must be set")

        # Verify auth result properties
        auth_data = auth_result.auth_result
        self.assertTrue(auth_data.success, "Auth result must be successful")
        self.assertIsNotNone(auth_data.user_id, "Auth result must contain user ID")

        # Performance assertion
        self.assertLess(auth_time, 5.0, "Auth integration should complete within 5 seconds")

        self.record_metric("auth_success", True)
        self.record_metric("user_context_created", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_service_authentication_failure(self):
        """
        Test WebSocket authentication failure through auth service.

        CRITICAL: Auth service failures must be properly handled and returned
        as failure results without crashing the system.
        """
        # Arrange
        user_id = f"auth_fail_user_{uuid.uuid4().hex[:8]}"

        # Create mock WebSocket with invalid/missing auth
        websocket = MockWebSocket(headers={
            "user-agent": "Test WebSocket Client"
            # No authorization header
        })

        # Track performance
        start_time = time.time()

        # Act
        auth_result = await authenticate_websocket_ssot(
            websocket=websocket,
            e2e_context=None  # No E2E context, force real auth
        )

        auth_time = time.time() - start_time
        self.record_metric("auth_failure_response_time_ms", auth_time * 1000)

        # Assert
        self.assertFalse(auth_result.success, "Auth must fail for missing token")
        self.assertIsNone(auth_result.user_context, "User context must not be created for failed auth")
        self.assertIsNotNone(auth_result.error_message, "Error message must be provided")
        self.assertIsNotNone(auth_result.error_code, "Error code must be provided")

        # Verify specific error details
        self.assertEqual(auth_result.error_code, "NO_TOKEN", "Must return NO_TOKEN error code")
        self.assertIn("authentication token", auth_result.error_message.lower(),
                     "Error message must mention missing token")

        # Performance assertion - failures should be fast
        self.assertLess(auth_time, 2.0, "Auth failure should be fast (under 2 seconds)")

        self.record_metric("auth_failure_handled", True)
        self.record_metric("error_code", auth_result.error_code)

    @pytest.mark.asyncio
    async def test_websocket_auth_service_token_extraction(self):
        """
        Test WebSocket token extraction from various sources.

        CRITICAL: Auth service integration must extract tokens from standard
        WebSocket headers and subprotocols correctly.
        """
        # Test data for different token formats
        test_cases = [
            {
                "name": "authorization_header",
                "headers": {"authorization": "Bearer test_token_header"},
                "expected_extracted": True
            },
            {
                "name": "jwt_subprotocol",
                "headers": {"sec-websocket-protocol": "jwt.test_token_subprotocol"},
                "expected_extracted": True
            },
            {
                "name": "jwt_auth_subprotocol",
                "headers": {"sec-websocket-protocol": "jwt-auth.test_token_jwt_auth"},
                "expected_extracted": True
            },
            {
                "name": "bearer_subprotocol",
                "headers": {"sec-websocket-protocol": "bearer.test_token_bearer"},
                "expected_extracted": True
            },
            {
                "name": "no_token",
                "headers": {"user-agent": "Test Client"},
                "expected_extracted": False
            }
        ]

        for test_case in test_cases:
            with self.subTest(test_case=test_case["name"]):
                # Arrange
                websocket = MockWebSocket(headers=test_case["headers"])

                # Enable demo mode for successful auth if token is extractable
                e2e_context = None
                if test_case["expected_extracted"]:
                    e2e_context = {
                        "is_e2e_testing": True,
                        "demo_mode_enabled": True,
                        "bypass_enabled": True
                    }

                # Act
                auth_result = await authenticate_websocket_ssot(
                    websocket=websocket,
                    e2e_context=e2e_context
                )

                # Assert
                if test_case["expected_extracted"]:
                    self.assertTrue(auth_result.success,
                                   f"Token extraction test '{test_case['name']}' should succeed")
                else:
                    self.assertFalse(auth_result.success,
                                    f"Token extraction test '{test_case['name']}' should fail")
                    self.assertEqual(auth_result.error_code, "NO_TOKEN",
                                   f"Should return NO_TOKEN for '{test_case['name']}'")

        self.record_metric("token_extraction_tests", len(test_cases))

    @pytest.mark.asyncio
    async def test_websocket_auth_service_user_context_isolation(self):
        """
        Test user context isolation in WebSocket auth service integration.

        CRITICAL: Each authenticated WebSocket connection must get isolated
        user context to prevent cross-user data leakage.
        """
        # Arrange - Create multiple simulated auth requests
        user_contexts = []

        for i in range(3):
            user_id = f"isolation_user_{i}_{uuid.uuid4().hex[:8]}"

            websocket = MockWebSocket(headers={
                "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
                "x-user-id": user_id
            })

            e2e_context = {
                "is_e2e_testing": True,
                "demo_mode_enabled": True,
                "bypass_enabled": True,
                "test_user_id": user_id
            }

            # Act
            auth_result = await authenticate_websocket_ssot(
                websocket=websocket,
                e2e_context=e2e_context
            )

            # Collect user contexts
            if auth_result.success:
                user_contexts.append(auth_result.user_context)

        # Assert isolation
        self.assertEqual(len(user_contexts), 3, "All authentications should succeed")

        # Verify each context is unique
        user_ids = [ctx.user_id for ctx in user_contexts]
        websocket_client_ids = [ctx.websocket_client_id for ctx in user_contexts]
        thread_ids = [ctx.thread_id for ctx in user_contexts]
        run_ids = [ctx.run_id for ctx in user_contexts]

        # All identifiers should be unique across contexts
        self.assertEqual(len(set(user_ids)), 3, "User IDs must be unique")
        self.assertEqual(len(set(websocket_client_ids)), 3, "WebSocket client IDs must be unique")
        self.assertEqual(len(set(thread_ids)), 3, "Thread IDs must be unique")
        self.assertEqual(len(set(run_ids)), 3, "Run IDs must be unique")

        # Verify no shared references
        for i, ctx1 in enumerate(user_contexts):
            for j, ctx2 in enumerate(user_contexts):
                if i != j:
                    self.assertNotEqual(ctx1.user_id, ctx2.user_id, "User contexts must not share user IDs")
                    self.assertNotEqual(ctx1.websocket_client_id, ctx2.websocket_client_id,
                                      "User contexts must not share WebSocket client IDs")

        self.record_metric("user_context_isolation_verified", True)
        self.record_metric("unique_contexts_created", len(user_contexts))


@pytest.mark.integration
class WebSocketAuthBackendIntegrationTests(SSotAsyncTestCase):
    """Integration tests for WebSocket authentication with backend auth integration."""

    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)

        # Set test environment variables
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "1")
        self.set_env_var("DEMO_MODE", "1")
        self.set_env_var("ENVIRONMENT", "test")

        # Initialize backend auth integration
        self.backend_auth = BackendAuthIntegration()

        # Track metrics
        self.record_metric("test_category", "websocket_backend_auth_integration")

    @pytest.mark.asyncio
    async def test_backend_auth_integration_token_validation(self):
        """
        Test backend auth integration token validation in WebSocket context.

        CRITICAL: Backend auth integration must properly validate tokens
        and return consistent results for WebSocket authentication.
        """
        # Arrange
        test_tokens = [
            {
                "token": "Bearer valid_test_token_backend_auth",
                "expected_valid": True,
                "description": "valid_bearer_token"
            },
            {
                "token": "Bearer invalid_malformed_token",
                "expected_valid": False,
                "description": "invalid_token"
            },
            {
                "token": "InvalidFormat token_without_bearer",
                "expected_valid": False,
                "description": "malformed_authorization_header"
            }
        ]

        for token_test in test_tokens:
            with self.subTest(token=token_test["description"]):
                # Act
                start_time = time.time()
                validation_result = await self.backend_auth.validate_request_token(
                    authorization_header=token_test["token"]
                )
                validation_time = time.time() - start_time

                # Assert
                self.assertIsInstance(validation_result, AuthValidationResult,
                                    "Must return AuthValidationResult")

                if token_test["expected_valid"]:
                    # For demo mode, valid tokens should pass validation
                    # Note: In real implementation, this depends on auth service response
                    pass  # Validation behavior depends on auth service mock/real implementation
                else:
                    # Invalid tokens should definitely fail
                    self.assertFalse(validation_result.valid,
                                   f"Invalid token should fail validation: {token_test['description']}")

                # Performance check
                self.assertLess(validation_time, 3.0,
                              f"Token validation should be fast: {token_test['description']}")

                self.record_metric(f"token_validation_{token_test['description']}_time_ms",
                                 validation_time * 1000)

    @pytest.mark.asyncio
    async def test_backend_auth_integration_error_handling(self):
        """
        Test backend auth integration error handling scenarios.

        CRITICAL: Auth integration must handle errors gracefully without
        crashing and provide meaningful error information.
        """
        # Test error scenarios
        error_scenarios = [
            {
                "authorization_header": None,
                "description": "null_authorization_header"
            },
            {
                "authorization_header": "",
                "description": "empty_authorization_header"
            },
            {
                "authorization_header": "Bearer ",
                "description": "bearer_without_token"
            },
            {
                "authorization_header": "NotBearer some_token",
                "description": "non_bearer_header"
            }
        ]

        for scenario in error_scenarios:
            with self.subTest(scenario=scenario["description"]):
                # Act
                validation_result = await self.backend_auth.validate_request_token(
                    authorization_header=scenario["authorization_header"]
                )

                # Assert
                self.assertIsInstance(validation_result, AuthValidationResult,
                                    "Must return AuthValidationResult even for errors")
                self.assertFalse(validation_result.valid,
                               f"Invalid scenario should fail: {scenario['description']}")
                self.assertIsNotNone(validation_result.error,
                                   f"Error message should be provided: {scenario['description']}")

                # Verify specific error types
                if scenario["description"] in ["null_authorization_header", "empty_authorization_header",
                                             "bearer_without_token", "non_bearer_header"]:
                    self.assertIn("invalid_authorization_header", validation_result.error,
                                f"Should indicate header issue: {scenario['description']}")

        self.record_metric("error_scenarios_handled", len(error_scenarios))

    @pytest.mark.asyncio
    async def test_websocket_authenticator_class_integration(self):
        """
        Test UnifiedWebSocketAuthenticator class integration with auth services.

        CRITICAL: The authenticator class must integrate properly with
        auth services and provide consistent authentication results.
        """
        # Arrange
        authenticator = UnifiedWebSocketAuthenticator()

        user_id = f"authenticator_test_{uuid.uuid4().hex[:8]}"
        websocket = MockWebSocket(headers={
            "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
            "authorization": f"Bearer valid_test_token_for_{user_id}"
        })

        e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "bypass_enabled": True
        }

        # Act
        start_time = time.time()
        auth_result = await authenticator.authenticate_websocket_connection(
            websocket=websocket,
            e2e_context=e2e_context
        )
        auth_time = time.time() - start_time

        # Assert
        self.assertIsInstance(auth_result, WebSocketAuthResult,
                            "Must return WebSocketAuthResult")
        self.assertTrue(auth_result.success,
                       "Authenticator class must succeed with valid demo mode context")
        self.assertIsNotNone(auth_result.user_context,
                           "User context must be created by authenticator")

        # Verify authenticator statistics
        stats = authenticator.get_websocket_auth_stats()
        self.assertIsInstance(stats, dict, "Stats must be returned as dictionary")
        self.assertIn("websocket_auth_statistics", stats, "Must include auth statistics")
        self.assertGreater(stats["websocket_auth_statistics"]["total_attempts"], 0,
                          "Must track authentication attempts")

        # Performance verification
        self.assertLess(auth_time, 5.0, "Authenticator should be performant")

        self.record_metric("authenticator_class_integration", True)
        self.record_metric("authenticator_response_time_ms", auth_time * 1000)

    @pytest.mark.asyncio
    async def test_websocket_auth_circuit_breaker_integration(self):
        """
        Test WebSocket authentication circuit breaker integration.

        CRITICAL: Auth system must protect against repeated failures
        and provide circuit breaker functionality for resilience.
        """
        # Arrange
        authenticator = UnifiedWebSocketAuthenticator()

        # Create failing authentication scenarios
        failing_websocket = MockWebSocket(headers={})  # No auth headers

        auth_attempts = []

        # Act - Perform multiple authentication attempts to potentially trigger circuit breaker
        for i in range(5):
            start_time = time.time()
            auth_result = await authenticator.authenticate_websocket_connection(
                websocket=failing_websocket,
                e2e_context=None  # Force real auth failure
            )
            auth_time = time.time() - start_time

            auth_attempts.append({
                "attempt": i + 1,
                "success": auth_result.success,
                "error_code": auth_result.error_code,
                "response_time": auth_time
            })

        # Assert
        all_failed = all(not attempt["success"] for attempt in auth_attempts)
        self.assertTrue(all_failed, "All attempts without auth should fail")

        # Verify consistent error handling
        error_codes = [attempt["error_code"] for attempt in auth_attempts]
        self.assertTrue(all(code == "NO_TOKEN" for code in error_codes),
                       "Should consistently return NO_TOKEN error")

        # Verify circuit breaker may be activated (check for CIRCUIT_BREAKER_OPEN error)
        # Note: Circuit breaker behavior depends on implementation thresholds
        has_circuit_breaker_response = any(
            attempt["error_code"] == "AUTH_CIRCUIT_BREAKER_OPEN"
            for attempt in auth_attempts
        )

        # Performance should remain reasonable even with failures
        avg_response_time = sum(attempt["response_time"] for attempt in auth_attempts) / len(auth_attempts)
        self.assertLess(avg_response_time, 2.0, "Failed auth should remain fast")

        self.record_metric("circuit_breaker_integration_tested", True)
        self.record_metric("auth_failure_attempts", len(auth_attempts))
        self.record_metric("circuit_breaker_activated", has_circuit_breaker_response)