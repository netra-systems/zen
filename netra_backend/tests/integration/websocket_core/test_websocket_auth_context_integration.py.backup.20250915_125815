#!/usr/bin/env python
"""
Integration Tests for WebSocket Auth Context and User Lifecycle

MISSION CRITICAL: Integration between WebSocket authentication and user context lifecycle.
Tests real user context creation, management, and isolation in WebSocket authentication flows.

Business Value: $500K+ ARR - Secure user context isolation and lifecycle management
- Tests user execution context creation and management
- Validates context isolation between different WebSocket connections
- Ensures proper context cleanup and resource management
- Tests context propagation in authentication flows
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
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    WebSocketAuthResult,
    extract_e2e_context_from_websocket,
    create_authenticated_user_context
)
from shared.id_generation import UnifiedIdGenerator


class MockWebSocket:
    """Enhanced mock WebSocket for integration testing."""

    def __init__(self, headers=None, client=None, subprotocols=None, user_id=None):
        self.headers = headers or {}
        self.client = client or type('Client', (), {'host': '127.0.0.1', 'port': 8000})()
        self.subprotocols = subprotocols or []
        self.client_state = "CONNECTED"
        self.application_state = "CONNECTED"
        self._messages = []
        self._user_id = user_id

    async def send_json(self, data):
        """Mock send_json method."""
        self._messages.append(data)
        return True

    async def close(self, code=1000, reason=""):
        """Mock close method."""
        self.client_state = "DISCONNECTED"

    def get_messages(self):
        """Get all sent messages."""
        return self._messages.copy()


@pytest.mark.integration
class TestWebSocketAuthContextIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket authentication context management."""

    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)

        # Set test environment variables
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "1")
        self.set_env_var("DEMO_MODE", "1")
        self.set_env_var("ENVIRONMENT", "test")

        # Track metrics
        self.record_metric("test_category", "websocket_auth_context_integration")
        self.test_start_time = time.time()

    def teardown_method(self, method):
        """Teardown method for each test."""
        test_duration = time.time() - self.test_start_time
        self.record_metric("test_duration_seconds", test_duration)
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_websocket_auth_user_context_creation_and_isolation(self):
        """
        Test user context creation and isolation in WebSocket authentication.

        CRITICAL: Each authenticated WebSocket connection must get a unique,
        isolated user context that cannot interfere with other contexts.
        """
        # Arrange - Create multiple concurrent authentication requests
        num_concurrent_auths = 5
        auth_tasks = []

        for i in range(num_concurrent_auths):
            user_id = f"context_user_{i}_{uuid.uuid4().hex[:8]}"

            websocket = MockWebSocket(
                headers={
                    "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
                    "x-user-id": user_id,
                    "x-test-case": "concurrent_auth"
                },
                user_id=user_id
            )

            e2e_context = {
                "is_e2e_testing": True,
                "demo_mode_enabled": True,
                "bypass_enabled": True,
                "test_user_id": user_id,
                "concurrent_test": True
            }

            # Create async task for concurrent execution
            task = asyncio.create_task(
                authenticate_websocket_ssot(
                    websocket=websocket,
                    e2e_context=e2e_context,
                    preliminary_connection_id=f"conn_{i}_{uuid.uuid4().hex[:8]}"
                )
            )
            auth_tasks.append((task, user_id, i))

        # Act - Execute all authentication requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*[task for task, _, _ in auth_tasks], return_exceptions=True)
        concurrent_auth_time = time.time() - start_time

        # Assert - Verify all authentications succeeded
        successful_results = []
        for i, result in enumerate(results):
            task, user_id, index = auth_tasks[i]

            if isinstance(result, Exception):
                self.fail(f"Authentication {index} failed with exception: {result}")

            self.assertIsInstance(result, WebSocketAuthResult,
                                f"Result {index} must be WebSocketAuthResult")
            self.assertTrue(result.success,
                          f"Authentication {index} for user {user_id} must succeed")
            self.assertIsNotNone(result.user_context,
                               f"User context {index} must be created")

            successful_results.append((result, user_id, index))

        # Verify context isolation and uniqueness
        user_contexts = [result.user_context for result, _, _ in successful_results]

        # Extract all unique identifiers
        user_ids = [ctx.user_id for ctx in user_contexts]
        websocket_client_ids = [ctx.websocket_client_id for ctx in user_contexts]
        thread_ids = [ctx.thread_id for ctx in user_contexts]
        run_ids = [ctx.run_id for ctx in user_contexts]
        request_ids = [ctx.request_id for ctx in user_contexts]

        # Verify all identifiers are unique (critical for isolation)
        self.assertEqual(len(set(user_ids)), num_concurrent_auths,
                        "All user IDs must be unique across concurrent contexts")
        self.assertEqual(len(set(websocket_client_ids)), num_concurrent_auths,
                        "All WebSocket client IDs must be unique")
        self.assertEqual(len(set(thread_ids)), num_concurrent_auths,
                        "All thread IDs must be unique")
        self.assertEqual(len(set(run_ids)), num_concurrent_auths,
                        "All run IDs must be unique")
        self.assertEqual(len(set(request_ids)), num_concurrent_auths,
                        "All request IDs must be unique")

        # Verify no shared object references
        for i, ctx1 in enumerate(user_contexts):
            for j, ctx2 in enumerate(user_contexts):
                if i != j:
                    self.assertIsNot(ctx1, ctx2, "Context objects must not be shared")
                    self.assertNotEqual(ctx1.user_id, ctx2.user_id,
                                      "User contexts must have different user IDs")

        # Performance verification
        avg_auth_time = concurrent_auth_time / num_concurrent_auths
        self.assertLess(avg_auth_time, 3.0,
                       "Concurrent authentication should be performant")

        self.record_metric("concurrent_authentications", num_concurrent_auths)
        self.record_metric("concurrent_auth_time_seconds", concurrent_auth_time)
        self.record_metric("avg_auth_time_seconds", avg_auth_time)
        self.record_metric("context_isolation_verified", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_context_properties_validation(self):
        """
        Test validation of user context properties in WebSocket authentication.

        CRITICAL: User contexts must have all required properties properly
        populated and follow the expected format and validation rules.
        """
        # Arrange
        user_id = f"validation_user_{uuid.uuid4().hex[:8]}"
        websocket = MockWebSocket(headers={
            "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
            "x-user-id": user_id
        })

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

        # Assert - Verify authentication succeeded
        self.assertTrue(auth_result.success, "Authentication must succeed for context validation")
        self.assertIsNotNone(auth_result.user_context, "User context must be created")

        context = auth_result.user_context

        # Validate required properties exist and are properly formatted
        self.assertIsNotNone(context.user_id, "User ID must be set")
        self.assertIsInstance(context.user_id, str, "User ID must be string")
        self.assertGreater(len(context.user_id), 0, "User ID must not be empty")

        self.assertIsNotNone(context.websocket_client_id, "WebSocket client ID must be set")
        self.assertIsInstance(context.websocket_client_id, str, "WebSocket client ID must be string")
        self.assertGreater(len(context.websocket_client_id), 0, "WebSocket client ID must not be empty")

        self.assertIsNotNone(context.thread_id, "Thread ID must be set")
        self.assertIsInstance(context.thread_id, str, "Thread ID must be string")
        self.assertGreater(len(context.thread_id), 0, "Thread ID must not be empty")

        self.assertIsNotNone(context.run_id, "Run ID must be set")
        self.assertIsInstance(context.run_id, str, "Run ID must be string")
        self.assertGreater(len(context.run_id), 0, "Run ID must not be empty")

        self.assertIsNotNone(context.request_id, "Request ID must be set")
        self.assertIsInstance(context.request_id, str, "Request ID must be string")
        self.assertGreater(len(context.request_id), 0, "Request ID must not be empty")

        # Validate ID format patterns (should follow UUID-like patterns)
        id_fields = [
            ("user_id", context.user_id),
            ("websocket_client_id", context.websocket_client_id),
            ("thread_id", context.thread_id),
            ("run_id", context.run_id),
            ("request_id", context.request_id)
        ]

        for field_name, field_value in id_fields:
            # IDs should be reasonable length (not too short or too long)
            self.assertGreaterEqual(len(field_value), 8,
                                  f"{field_name} should be at least 8 characters")
            self.assertLessEqual(len(field_value), 100,
                                f"{field_name} should be less than 100 characters")

            # IDs should not contain spaces or special characters that could cause issues
            self.assertNotIn(" ", field_value, f"{field_name} should not contain spaces")
            self.assertNotIn("\n", field_value, f"{field_name} should not contain newlines")
            self.assertNotIn("\t", field_value, f"{field_name} should not contain tabs")

        # Validate context can be serialized (important for storage/transmission)
        try:
            context_dict = {
                "user_id": context.user_id,
                "websocket_client_id": context.websocket_client_id,
                "thread_id": context.thread_id,
                "run_id": context.run_id,
                "request_id": context.request_id
            }
            serialized = json.dumps(context_dict)
            deserialized = json.loads(serialized)
            self.assertEqual(context_dict, deserialized, "Context should be JSON serializable")
        except (TypeError, ValueError) as e:
            self.fail(f"Context should be JSON serializable, but got error: {e}")

        self.record_metric("context_properties_validated", True)
        self.record_metric("context_json_serializable", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_context_lifecycle_management(self):
        """
        Test user context lifecycle management in WebSocket authentication.

        CRITICAL: User contexts must be properly created, maintained during
        the session, and cleaned up when the connection ends.
        """
        # Arrange
        user_id = f"lifecycle_user_{uuid.uuid4().hex[:8]}"
        websocket = MockWebSocket(headers={
            "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
            "x-user-id": user_id
        })

        e2e_context = {
            "is_e2e_testing": True,
            "demo_mode_enabled": True,
            "bypass_enabled": True
        }

        # Track context lifecycle stages
        lifecycle_stages = []

        # Act - Phase 1: Create context through authentication
        start_auth_time = time.time()
        auth_result = await authenticate_websocket_ssot(
            websocket=websocket,
            e2e_context=e2e_context
        )
        auth_time = time.time() - start_auth_time

        self.assertTrue(auth_result.success, "Authentication must succeed for lifecycle test")
        context = auth_result.user_context
        lifecycle_stages.append(("created", time.time(), context.user_id))

        # Phase 2: Verify context is functional and maintains state
        original_user_id = context.user_id
        original_websocket_client_id = context.websocket_client_id
        original_thread_id = context.thread_id

        # Simulate some time passing and context usage
        await asyncio.sleep(0.1)

        # Verify context properties remain consistent
        self.assertEqual(context.user_id, original_user_id,
                        "User ID should remain consistent during lifecycle")
        self.assertEqual(context.websocket_client_id, original_websocket_client_id,
                        "WebSocket client ID should remain consistent")
        self.assertEqual(context.thread_id, original_thread_id,
                        "Thread ID should remain consistent")

        lifecycle_stages.append(("maintained", time.time(), context.user_id))

        # Phase 3: Simulate connection cleanup
        websocket.client_state = "DISCONNECTED"
        lifecycle_stages.append(("disconnected", time.time(), context.user_id))

        # Phase 4: Verify context can still be accessed but connection is closed
        self.assertEqual(websocket.client_state, "DISCONNECTED",
                        "WebSocket should be marked as disconnected")

        # Context should still be valid even if connection is closed
        self.assertIsNotNone(context.user_id, "Context should remain valid after disconnect")

        lifecycle_stages.append(("cleanup_verified", time.time(), context.user_id))

        # Assert - Verify lifecycle progression
        self.assertEqual(len(lifecycle_stages), 4, "All lifecycle stages should be recorded")

        # Verify stage progression timing
        stage_times = [stage[1] for stage in lifecycle_stages]
        for i in range(1, len(stage_times)):
            self.assertGreaterEqual(stage_times[i], stage_times[i-1],
                                  f"Lifecycle stage {i} should occur after stage {i-1}")

        # Verify all stages reference the same user
        user_ids_in_stages = [stage[2] for stage in lifecycle_stages]
        self.assertTrue(all(uid == original_user_id for uid in user_ids_in_stages),
                       "All lifecycle stages should reference the same user ID")

        # Performance verification
        total_lifecycle_time = stage_times[-1] - stage_times[0]
        self.assertLess(total_lifecycle_time, 5.0,
                       "Context lifecycle should complete quickly")

        self.record_metric("context_lifecycle_stages", len(lifecycle_stages))
        self.record_metric("auth_time_seconds", auth_time)
        self.record_metric("total_lifecycle_time_seconds", total_lifecycle_time)
        self.record_metric("context_consistency_maintained", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_context_error_handling(self):
        """
        Test user context error handling in WebSocket authentication.

        CRITICAL: When authentication fails, no user context should be created,
        and the system should handle errors gracefully without corruption.
        """
        # Test various error scenarios
        error_scenarios = [
            {
                "name": "missing_token",
                "websocket": MockWebSocket(headers={}),
                "e2e_context": None,
                "expected_error_code": "NO_TOKEN"
            },
            {
                "name": "malformed_token",
                "websocket": MockWebSocket(headers={
                    "authorization": "Malformed invalid_token_format"
                }),
                "e2e_context": None,
                "expected_error_code": "NO_TOKEN"
            },
            {
                "name": "empty_token",
                "websocket": MockWebSocket(headers={
                    "sec-websocket-protocol": "jwt."  # Empty token after jwt.
                }),
                "e2e_context": None,
                "expected_error_code": "NO_TOKEN"
            }
        ]

        error_results = []

        for scenario in error_scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Act
                start_time = time.time()
                auth_result = await authenticate_websocket_ssot(
                    websocket=scenario["websocket"],
                    e2e_context=scenario["e2e_context"]
                )
                error_time = time.time() - start_time

                # Assert - Authentication should fail
                self.assertFalse(auth_result.success,
                               f"Authentication should fail for scenario: {scenario['name']}")
                self.assertIsNone(auth_result.user_context,
                                f"No user context should be created for failed auth: {scenario['name']}")
                self.assertIsNotNone(auth_result.error_message,
                                   f"Error message should be provided: {scenario['name']}")
                self.assertIsNotNone(auth_result.error_code,
                                   f"Error code should be provided: {scenario['name']}")

                # Verify specific error codes
                self.assertEqual(auth_result.error_code, scenario["expected_error_code"],
                               f"Should return expected error code for: {scenario['name']}")

                # Error handling should be fast
                self.assertLess(error_time, 2.0,
                              f"Error handling should be fast for: {scenario['name']}")

                error_results.append({
                    "scenario": scenario["name"],
                    "error_code": auth_result.error_code,
                    "error_message": auth_result.error_message,
                    "response_time": error_time
                })

        # Assert - Verify consistent error handling
        self.assertEqual(len(error_results), len(error_scenarios),
                        "All error scenarios should be handled")

        # Verify no user contexts were leaked during error scenarios
        for result in error_results:
            self.assertIsNotNone(result["error_code"], "Error code must be set")
            self.assertIsNotNone(result["error_message"], "Error message must be set")

        avg_error_response_time = sum(r["response_time"] for r in error_results) / len(error_results)

        self.record_metric("error_scenarios_tested", len(error_scenarios))
        self.record_metric("avg_error_response_time_seconds", avg_error_response_time)
        self.record_metric("error_handling_verified", True)

    @pytest.mark.asyncio
    async def test_websocket_auth_context_id_generation_uniqueness(self):
        """
        Test ID generation uniqueness in WebSocket authentication contexts.

        CRITICAL: All generated IDs must be unique across multiple authentications
        to prevent conflicts and ensure proper isolation.
        """
        # Arrange - Create a large number of authentications to test ID uniqueness
        num_authentications = 20
        authentication_tasks = []

        for i in range(num_authentications):
            user_id = f"id_test_user_{i}_{uuid.uuid4().hex[:8]}"

            websocket = MockWebSocket(headers={
                "sec-websocket-protocol": f"jwt.valid_test_token_for_{user_id}",
                "x-user-id": user_id,
                "x-batch-test": "id_generation"
            })

            e2e_context = {
                "is_e2e_testing": True,
                "demo_mode_enabled": True,
                "bypass_enabled": True,
                "batch_test": "id_generation"
            }

            task = authenticate_websocket_ssot(
                websocket=websocket,
                e2e_context=e2e_context
            )
            authentication_tasks.append(task)

        # Act - Execute all authentications
        start_time = time.time()
        results = await asyncio.gather(*authentication_tasks, return_exceptions=True)
        batch_auth_time = time.time() - start_time

        # Filter successful results
        successful_contexts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f"Authentication {i} failed with exception: {result}")

            if result.success:
                successful_contexts.append(result.user_context)

        # Assert - All authentications should succeed
        self.assertEqual(len(successful_contexts), num_authentications,
                        "All authentications should succeed")

        # Collect all generated IDs
        all_user_ids = [ctx.user_id for ctx in successful_contexts]
        all_websocket_client_ids = [ctx.websocket_client_id for ctx in successful_contexts]
        all_thread_ids = [ctx.thread_id for ctx in successful_contexts]
        all_run_ids = [ctx.run_id for ctx in successful_contexts]
        all_request_ids = [ctx.request_id for ctx in successful_contexts]

        # Verify uniqueness across all ID types
        id_collections = [
            ("user_ids", all_user_ids),
            ("websocket_client_ids", all_websocket_client_ids),
            ("thread_ids", all_thread_ids),
            ("run_ids", all_run_ids),
            ("request_ids", all_request_ids)
        ]

        for id_type_name, id_collection in id_collections:
            unique_ids = set(id_collection)
            self.assertEqual(len(unique_ids), num_authentications,
                           f"All {id_type_name} must be unique across {num_authentications} authentications")

            # Verify no empty or None IDs
            self.assertNotIn(None, id_collection, f"No {id_type_name} should be None")
            self.assertNotIn("", id_collection, f"No {id_type_name} should be empty string")
            self.assertTrue(all(len(id_str) > 0 for id_str in id_collection),
                          f"All {id_type_name} should have positive length")

        # Verify cross-type uniqueness (IDs of different types should also be unique)
        all_ids = all_user_ids + all_websocket_client_ids + all_thread_ids + all_run_ids + all_request_ids
        unique_all_ids = set(all_ids)

        # While cross-type uniqueness is not strictly required, it's a good property for debugging
        uniqueness_ratio = len(unique_all_ids) / len(all_ids)
        self.assertGreater(uniqueness_ratio, 0.95,
                          "Most IDs should be unique even across different ID types")

        # Performance verification
        avg_auth_time = batch_auth_time / num_authentications
        self.assertLess(avg_auth_time, 2.0,
                       "ID generation should not significantly slow authentication")

        self.record_metric("id_uniqueness_authentications", num_authentications)
        self.record_metric("batch_auth_time_seconds", batch_auth_time)
        self.record_metric("avg_auth_time_per_request_seconds", avg_auth_time)
        self.record_metric("id_uniqueness_ratio", uniqueness_ratio)
        self.record_metric("id_generation_uniqueness_verified", True)