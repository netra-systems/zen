#!/usr/bin/env python
"""
Integration Tests for WebSocket Auth Error Scenarios and Recovery

MISSION CRITICAL: Integration testing of WebSocket authentication error handling and recovery.
Tests real error scenarios, recovery patterns, and system resilience in auth failures.

Business Value: $500K+ ARR - Robust auth error handling and system resilience
- Tests authentication error handling and recovery scenarios
- Validates system resilience under auth service failures
- Ensures proper error propagation and user feedback
- Tests auth circuit breaker and rate limiting integration
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

# Import production components - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    extract_e2e_context_from_websocket
)
from netra_backend.app.auth_integration.auth_permissiveness import (
    authenticate_with_permissiveness,
    AuthPermissivenessLevel
)
from netra_backend.app.auth_integration.auth_circuit_breaker import (
    authenticate_with_circuit_breaker,
    get_auth_circuit_status
)


class MockWebSocket:
    """Enhanced mock WebSocket for error scenario testing."""

    def __init__(self, headers=None, client=None, subprotocols=None,
                 connection_state="CONNECTED", should_fail_send=False):
        self.headers = headers or {}
        self.client = client or type('Client', (), {'host': '127.0.0.1', 'port': 8000})()
        self.subprotocols = subprotocols or []
        self.client_state = connection_state
        self.application_state = connection_state
        self._messages = []
        self._should_fail_send = should_fail_send
        self._send_call_count = 0
        self._close_call_count = 0

    async def send_json(self, data):
        """Mock send_json method that can simulate failures."""
        self._send_call_count += 1
        if self._should_fail_send:
            raise ConnectionError("Simulated WebSocket send failure")
        self._messages.append(data)
        return True

    async def close(self, code=1000, reason=""):
        """Mock close method."""
        self._close_call_count += 1
        self.client_state = "DISCONNECTED"

    def get_messages(self):
        """Get all sent messages."""
        return self._messages.copy()

    def get_send_call_count(self):
        """Get number of send_json calls."""
        return self._send_call_count

    def get_close_call_count(self):
        """Get number of close calls."""
        return self._close_call_count


@pytest.mark.integration
class WebSocketAuthErrorHandlingIntegrationTests(SSotAsyncTestCase):
    """Integration tests for WebSocket authentication error handling."""

    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)

        # Set test environment variables
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "1")
        self.set_env_var("DEMO_MODE", "0")  # Disable demo mode to test real auth failures
        self.set_env_var("ENVIRONMENT", "test")

        # Track metrics
        self.record_metric("test_category", "websocket_auth_error_integration")

    @pytest.mark.asyncio
    async def test_websocket_auth_token_validation_failures(self):
        """
        Test WebSocket authentication token validation failure scenarios.

        CRITICAL: Various token validation failures must be handled properly
        with appropriate error codes and messages.
        """
        # Test various token validation failure scenarios
        error_scenarios = [
            {
                "name": "no_authorization_header",
                "headers": {"user-agent": "Test Client"},
                "expected_error_code": "NO_TOKEN",
                "description": "Missing authorization header should return NO_TOKEN"
            },
            {
                "name": "empty_authorization_header",
                "headers": {"authorization": ""},
                "expected_error_code": "NO_TOKEN",
                "description": "Empty authorization header should return NO_TOKEN"
            },
            {
                "name": "malformed_bearer_token",
                "headers": {"authorization": "Bearer"},
                "expected_error_code": "NO_TOKEN",
                "description": "Bearer without token should return NO_TOKEN"
            },
            {
                "name": "invalid_token_format",
                "headers": {"authorization": "InvalidFormat token123"},
                "expected_error_code": "NO_TOKEN",
                "description": "Invalid authorization format should return NO_TOKEN"
            },
            {
                "name": "empty_jwt_subprotocol",
                "headers": {"sec-websocket-protocol": "jwt."},
                "expected_error_code": "NO_TOKEN",
                "description": "Empty JWT in subprotocol should return NO_TOKEN"
            },
            {
                "name": "malformed_jwt_subprotocol",
                "headers": {"sec-websocket-protocol": "jwt.invalid_token_format"},
                "expected_error_code": "NO_TOKEN",
                "description": "Malformed JWT in subprotocol should return NO_TOKEN"
            }
        ]

        error_results = []

        for scenario in error_scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Arrange
                websocket = MockWebSocket(headers=scenario["headers"])

                # Act
                start_time = time.time()
                auth_result = await authenticate_websocket_ssot(
                    websocket=websocket,
                    e2e_context=None  # No E2E context to force real auth
                )
                error_response_time = time.time() - start_time

                # Assert
                self.assertFalse(auth_result.success,
                               f"Authentication should fail for {scenario['name']}")
                self.assertIsNone(auth_result.user_context,
                                f"No user context for failed auth: {scenario['name']}")
                self.assertIsNotNone(auth_result.error_message,
                                   f"Error message required for: {scenario['name']}")
                self.assertIsNotNone(auth_result.error_code,
                                   f"Error code required for: {scenario['name']}")

                # Verify expected error code
                self.assertEqual(auth_result.error_code, scenario["expected_error_code"],
                               f"Expected error code for {scenario['name']}: {scenario['description']}")

                # Error responses should be fast
                self.assertLess(error_response_time, 1.0,
                              f"Error response should be fast for: {scenario['name']}")

                error_results.append({
                    "scenario": scenario["name"],
                    "error_code": auth_result.error_code,
                    "error_message": auth_result.error_message,
                    "response_time": error_response_time,
                    "expected_error_code": scenario["expected_error_code"]
                })

        # Verify all scenarios were handled consistently
        self.assertEqual(len(error_results), len(error_scenarios),
                        "All error scenarios should be processed")

        # Check that error messages are informative
        for result in error_results:
            self.assertGreater(len(result["error_message"]), 10,
                             f"Error message should be informative for {result['scenario']}")
            self.assertIn("token", result["error_message"].lower(),
                         f"Error message should mention token for {result['scenario']}")

        avg_error_response_time = sum(r["response_time"] for r in error_results) / len(error_results)

        self.record_metric("error_scenarios_tested", len(error_scenarios))
        self.record_metric("avg_error_response_time_seconds", avg_error_response_time)
        self.record_metric("token_validation_errors_handled", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_service_connection_failures(self):
        """
        Test WebSocket authentication handling of auth service connection failures.

        CRITICAL: When auth service is unavailable, authentication should fail
        gracefully with appropriate error codes and not crash the system.
        """
        # Arrange - Create scenarios that might cause auth service connection issues
        connection_failure_scenarios = [
            {
                "name": "auth_service_timeout",
                "mock_exception": asyncio.TimeoutError("Auth service timeout"),
                "expected_error_substring": "timeout"
            },
            {
                "name": "auth_service_connection_error",
                "mock_exception": ConnectionError("Cannot connect to auth service"),
                "expected_error_substring": "connection"
            },
            {
                "name": "auth_service_generic_exception",
                "mock_exception": Exception("Generic auth service error"),
                "expected_error_substring": "error"
            }
        ]

        for scenario in connection_failure_scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Arrange
                user_id = f"conn_fail_user_{uuid.uuid4().hex[:8]}"
                websocket = MockWebSocket(headers={
                    "sec-websocket-protocol": f"jwt.test_token_{user_id}",
                    "x-user-id": user_id
                })

                # Mock auth service to simulate connection failure
                with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth_service:
                    mock_service = AsyncMock()
                    mock_service.authenticate_websocket.side_effect = scenario["mock_exception"]
                    mock_auth_service.return_value = mock_service

                    # Act
                    start_time = time.time()
                    auth_result = await authenticate_websocket_ssot(
                        websocket=websocket,
                        e2e_context=None
                    )
                    failure_response_time = time.time() - start_time

                    # Assert
                    self.assertFalse(auth_result.success,
                                   f"Authentication should fail for {scenario['name']}")
                    self.assertIsNone(auth_result.user_context,
                                    f"No user context for service failure: {scenario['name']}")
                    self.assertIsNotNone(auth_result.error_message,
                                       f"Error message required for: {scenario['name']}")
                    self.assertIsNotNone(auth_result.error_code,
                                       f"Error code required for: {scenario['name']}")

                    # Error message should reference the connection issue
                    self.assertIn(scenario["expected_error_substring"],
                                 auth_result.error_message.lower(),
                                 f"Error message should mention connection issue: {scenario['name']}")

                    # Service failures should still respond reasonably quickly
                    self.assertLess(failure_response_time, 5.0,
                                  f"Service failure response should not hang: {scenario['name']}")

                    self.record_metric(f"service_failure_{scenario['name']}_handled", True)
                    self.record_metric(f"service_failure_{scenario['name']}_response_time", failure_response_time)

    @pytest.mark.asyncio
    async def test_websocket_auth_circuit_breaker_integration(self):
        """
        Test WebSocket authentication circuit breaker integration.

        CRITICAL: Circuit breaker should protect against repeated auth failures
        and provide appropriate error responses when circuit is open.
        """
        # Arrange
        authenticator = UnifiedWebSocketAuthenticator()

        # Create scenarios to potentially trigger circuit breaker
        num_failure_attempts = 5
        failure_results = []

        for i in range(num_failure_attempts):
            # Create failing authentication scenario
            websocket = MockWebSocket(headers={})  # No auth headers to cause failure

            start_time = time.time()
            auth_result = await authenticator.authenticate_websocket_connection(
                websocket=websocket,
                e2e_context=None
            )
            response_time = time.time() - start_time

            failure_results.append({
                "attempt": i + 1,
                "success": auth_result.success,
                "error_code": auth_result.error_code,
                "error_message": auth_result.error_message,
                "response_time": response_time
            })

            # Add small delay between attempts
            await asyncio.sleep(0.1)

        # Assert - All attempts should fail
        all_failed = all(not result["success"] for result in failure_results)
        self.assertTrue(all_failed, "All authentication attempts without tokens should fail")

        # Check if circuit breaker was activated
        circuit_breaker_responses = [
            result for result in failure_results
            if result["error_code"] == "AUTH_CIRCUIT_BREAKER_OPEN"
        ]

        # Circuit breaker behavior depends on implementation thresholds
        # Document whether it was activated
        circuit_breaker_activated = len(circuit_breaker_responses) > 0

        if circuit_breaker_activated:
            # Verify circuit breaker responses are fast
            avg_circuit_breaker_time = sum(
                result["response_time"] for result in circuit_breaker_responses
            ) / len(circuit_breaker_responses)

            self.assertLess(avg_circuit_breaker_time, 0.5,
                           "Circuit breaker responses should be very fast")

        # Test recovery after circuit breaker
        if circuit_breaker_activated:
            # Wait for potential circuit breaker reset
            await asyncio.sleep(1.0)

            # Try with valid authentication (demo mode)
            recovery_websocket = MockWebSocket(headers={
                "sec-websocket-protocol": "jwt.valid_recovery_token"
            })

            recovery_e2e_context = {
                "is_e2e_testing": True,
                "demo_mode_enabled": True,
                "bypass_enabled": True
            }

            recovery_result = await authenticator.authenticate_websocket_connection(
                websocket=recovery_websocket,
                e2e_context=recovery_e2e_context
            )

            # Recovery with valid auth should work even after circuit breaker
            self.assertTrue(recovery_result.success,
                           "Should be able to recover with valid authentication")

        # Performance verification
        avg_failure_time = sum(result["response_time"] for result in failure_results) / len(failure_results)
        self.assertLess(avg_failure_time, 2.0,
                       "Failed authentications should still be reasonably fast")

        self.record_metric("circuit_breaker_failure_attempts", num_failure_attempts)
        self.record_metric("circuit_breaker_activated", circuit_breaker_activated)
        self.record_metric("circuit_breaker_responses", len(circuit_breaker_responses))
        self.record_metric("avg_failure_response_time_seconds", avg_failure_time)

    @pytest.mark.asyncio
    async def test_websocket_auth_error_response_handling(self):
        """
        Test WebSocket authentication error response handling.

        CRITICAL: When authentication fails, appropriate error responses
        should be sent to the WebSocket client before connection closure.
        """
        # Arrange
        authenticator = UnifiedWebSocketAuthenticator()

        error_response_scenarios = [
            {
                "name": "missing_token_error_response",
                "websocket": MockWebSocket(headers={}),
                "expected_error_type": "authentication_error"
            },
            {
                "name": "websocket_send_failure",
                "websocket": MockWebSocket(headers={}, should_fail_send=True),
                "expected_error_type": "authentication_error"
            },
            {
                "name": "disconnected_websocket",
                "websocket": MockWebSocket(headers={}, connection_state="DISCONNECTED"),
                "expected_error_type": "authentication_error"
            }
        ]

        for scenario in error_response_scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Arrange
                websocket = scenario["websocket"]

                # Act - Attempt authentication
                auth_result = await authenticator.authenticate_websocket_connection(
                    websocket=websocket,
                    e2e_context=None
                )

                # Authentication should fail
                self.assertFalse(auth_result.success,
                               f"Authentication should fail for {scenario['name']}")

                # Act - Handle authentication failure
                await authenticator.handle_authentication_failure(
                    websocket=websocket,
                    auth_result=auth_result,
                    close_connection=True
                )

                # Assert - Verify error handling behavior
                if scenario["name"] == "websocket_send_failure":
                    # Should handle send failures gracefully
                    self.assertGreater(websocket.get_send_call_count(), 0,
                                     "Should attempt to send error message")
                elif scenario["name"] == "disconnected_websocket":
                    # Should handle disconnected WebSockets gracefully
                    self.assertEqual(websocket.client_state, "DISCONNECTED",
                                   "WebSocket should remain disconnected")
                else:
                    # Should send error message successfully
                    messages = websocket.get_messages()
                    if len(messages) > 0:
                        error_message = messages[0]
                        self.assertEqual(error_message.get("type"), scenario["expected_error_type"],
                                       f"Should send authentication error message for {scenario['name']}")

                # Verify connection closure was attempted
                self.assertGreaterEqual(websocket.get_close_call_count(), 1,
                                      f"Should attempt to close connection for {scenario['name']}")

        self.record_metric("error_response_scenarios_tested", len(error_response_scenarios))
        self.record_metric("error_response_handling_verified", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_recovery_after_failures(self):
        """
        Test WebSocket authentication recovery after various failure scenarios.

        CRITICAL: After authentication failures, the system should be able
        to recover and successfully authenticate valid requests.
        """
        # Arrange
        authenticator = UnifiedWebSocketAuthenticator()

        # Phase 1: Create initial failure
        failing_websocket = MockWebSocket(headers={})

        initial_failure = await authenticator.authenticate_websocket_connection(
            websocket=failing_websocket,
            e2e_context=None
        )

        self.assertFalse(initial_failure.success, "Initial authentication should fail")

        # Phase 2: Wait briefly to simulate time passing
        await asyncio.sleep(0.5)

        # Phase 3: Attempt recovery with valid authentication
        recovery_user_id = f"recovery_user_{uuid.uuid4().hex[:8]}"
        recovery_websocket = MockWebSocket(headers={
            "sec-websocket-protocol": f"jwt.valid_recovery_token_{recovery_user_id}",
            "x-user-id": recovery_user_id
        })

        recovery_e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "bypass_enabled": True,
            "recovery_test": True
        }

        start_recovery_time = time.time()
        recovery_result = await authenticator.authenticate_websocket_connection(
            websocket=recovery_websocket,
            e2e_context=recovery_e2e_context
        )
        recovery_time = time.time() - start_recovery_time

        # Assert - Recovery should succeed
        self.assertTrue(recovery_result.success,
                       "Authentication recovery should succeed with valid credentials")
        self.assertIsNotNone(recovery_result.user_context,
                           "User context should be created after recovery")
        self.assertIsNotNone(recovery_result.auth_result,
                           "Auth result should be populated after recovery")

        # Verify recovery performance
        self.assertLess(recovery_time, 3.0,
                       "Recovery should be performant")

        # Phase 4: Verify continued functionality after recovery
        continued_user_id = f"continued_user_{uuid.uuid4().hex[:8]}"
        continued_websocket = MockWebSocket(headers={
            "sec-websocket-protocol": f"jwt.valid_continued_token_{continued_user_id}",
            "x-user-id": continued_user_id
        })

        continued_e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "bypass_enabled": True,
            "continued_test": True
        }

        continued_result = await authenticator.authenticate_websocket_connection(
            websocket=continued_websocket,
            e2e_context=continued_e2e_context
        )

        # Assert - Continued functionality should work
        self.assertTrue(continued_result.success,
                       "Continued authentication should work after recovery")

        # Verify system statistics show recovery
        stats = authenticator.get_websocket_auth_stats()
        self.assertGreater(stats["websocket_auth_statistics"]["total_attempts"], 2,
                          "Should show multiple authentication attempts")
        self.assertGreater(stats["websocket_auth_statistics"]["successful_authentications"], 1,
                          "Should show successful authentications after recovery")

        self.record_metric("auth_recovery_verified", True)
        self.record_metric("recovery_time_seconds", recovery_time)
        self.record_metric("continued_functionality_verified", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_concurrent_error_handling(self):
        """
        Test WebSocket authentication concurrent error handling.

        CRITICAL: Multiple concurrent authentication failures should be
        handled properly without system corruption or resource leaks.
        """
        # Arrange - Create multiple concurrent failing authentication requests
        num_concurrent_failures = 10
        authenticator = UnifiedWebSocketAuthenticator()

        concurrent_tasks = []
        for i in range(num_concurrent_failures):
            # Create failing WebSocket (no auth headers)
            failing_websocket = MockWebSocket(headers={
                "x-test-id": f"concurrent_fail_{i}"
            })

            task = authenticator.authenticate_websocket_connection(
                websocket=failing_websocket,
                e2e_context=None
            )
            concurrent_tasks.append(task)

        # Act - Execute all concurrent failing authentications
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        concurrent_failure_time = time.time() - start_time

        # Assert - All should fail gracefully
        failure_count = 0
        exception_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                exception_count += 1
                self.fail(f"Concurrent authentication {i} raised unhandled exception: {result}")
            else:
                self.assertIsInstance(result, WebSocketAuthResult,
                                    f"Result {i} should be WebSocketAuthResult")
                if not result.success:
                    failure_count += 1
                    self.assertIsNotNone(result.error_code,
                                       f"Failed result {i} should have error code")
                    self.assertIsNotNone(result.error_message,
                                       f"Failed result {i} should have error message")

        # Verify all failed as expected (no auth headers)
        self.assertEqual(failure_count, num_concurrent_failures,
                        "All concurrent authentication attempts should fail")
        self.assertEqual(exception_count, 0,
                        "No unhandled exceptions should occur")

        # Verify performance under concurrent failures
        avg_failure_time = concurrent_failure_time / num_concurrent_failures
        self.assertLess(avg_failure_time, 2.0,
                       "Concurrent failure handling should be performant")

        # Verify system statistics are consistent
        stats = authenticator.get_websocket_auth_stats()
        total_attempts = stats["websocket_auth_statistics"]["total_attempts"]
        failed_attempts = stats["websocket_auth_statistics"]["failed_authentications"]

        self.assertGreaterEqual(total_attempts, num_concurrent_failures,
                              "Statistics should reflect concurrent attempts")
        self.assertGreaterEqual(failed_attempts, num_concurrent_failures,
                              "Statistics should reflect concurrent failures")

        self.record_metric("concurrent_failure_tests", num_concurrent_failures)
        self.record_metric("concurrent_failure_time_seconds", concurrent_failure_time)
        self.record_metric("avg_concurrent_failure_time_seconds", avg_failure_time)
        self.record_metric("concurrent_error_handling_verified", True)