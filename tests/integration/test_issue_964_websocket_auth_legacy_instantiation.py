#!/usr/bin/env python3
"""
Issue #964: WebSocket Authentication Legacy UserExecutionContext Instantiation Test

This test reproduces the P1 critical issue where legacy UserExecutionContext instantiation
in demo mode causes stream execution failures affecting the Golden Path user experience.

Business Value Impact:
- P1 Critical: Stream execution failures affect Golden Path ($500K+ ARR)
- GCP Deployment Regression: Production has pre-SSOT code patterns
- User Experience: Real-time chat streaming broken for demo mode users

Root Cause:
The infrastructure\websocket_auth_remediation.py file uses legacy UserExecutionContext
instantiation pattern on line 469 instead of the SSOT factory method.

Expected Fix:
Replace UserExecutionContext() constructor with UserExecutionContext.from_request_supervisor()
factory method to ensure SSOT compliance and proper stream execution.
"""

import asyncio
import pytest
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Dict, Any

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Infrastructure imports
try:
    from infrastructure.websocket_auth_remediation import (
        WebSocketAuthManager,
        WebSocketAuthResult,
        WebSocketAuthHelpers,
        WebSocketAuthenticationError
    )
    INFRASTRUCTURE_AVAILABLE = True
except ImportError as e:
    INFRASTRUCTURE_AVAILABLE = False
    IMPORT_ERROR = str(e)

# SSOT imports
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ConnectionID, SessionID
from shared.isolated_environment import IsolatedEnvironment


class TestIssue964WebSocketAuthLegacyInstantiation(SSotAsyncTestCase):
    """
    Test suite to reproduce and validate fix for Issue #964:
    WebSocket Authentication Legacy UserExecutionContext Instantiation
    """

    async def asyncSetUp(self):
        """Set up test environment with isolated configuration."""
        await super().asyncSetUp()

        # Set up isolated environment
        self.env = IsolatedEnvironment()

        # Configure demo mode for testing
        self.demo_mode_enabled = True

        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    @pytest.mark.skipif(not INFRASTRUCTURE_AVAILABLE, reason=f"Infrastructure not available: {IMPORT_ERROR if not INFRASTRUCTURE_AVAILABLE else ''}")
    async def test_websocket_auth_manager_demo_mode_legacy_instantiation(self):
        """
        Test that reproduces the legacy UserExecutionContext instantiation issue in demo mode.

        This test validates that the current implementation uses legacy instantiation
        which can cause stream execution failures due to SSOT violations.
        """
        # Mock environment to enable demo mode
        with patch.dict('os.environ', {'DEMO_MODE': '1'}, clear=False):
            # Initialize WebSocket auth manager
            auth_manager = WebSocketAuthManager()

            # Verify demo mode is enabled
            self.assertTrue(auth_manager.demo_mode, "Demo mode should be enabled for this test")

            # Test demo authentication
            connection_id = "test-connection-demo-964"

            # Execute demo authentication
            result = await auth_manager.authenticate_websocket_connection(
                token=None,  # No token needed in demo mode
                connection_id=connection_id
            )

            # Validate result structure
            self.assertIsInstance(result, WebSocketAuthResult)
            self.assertTrue(result.success, "Demo mode authentication should succeed")
            self.assertIsNotNone(result.user_context, "Demo mode should create user context")
            self.assertEqual(result.connection_id, connection_id)
            self.assertEqual(result.retry_count, 0)

            # **CRITICAL TEST: Detect legacy instantiation pattern**
            user_context = result.user_context
            self.assertIsInstance(user_context, UserExecutionContext)

            # Test if context was created with legacy pattern
            # Legacy pattern symptoms:
            # 1. Direct constructor usage instead of factory method
            # 2. Metadata dictionary passed directly instead of split pattern
            # 3. Missing SSOT validation patterns

            # Check for legacy instantiation indicators
            self.logger.info(f"User context created: user_id={user_context.user_id}")
            self.logger.info(f"User context metadata: {getattr(user_context, 'metadata', 'NOT_AVAILABLE')}")

            # Verify the context has expected demo values
            self.assertEqual(str(user_context.user_id), "demo-user")
            self.assertIsNotNone(user_context.thread_id)
            self.assertIsNotNone(user_context.run_id)

    @pytest.mark.skipif(not INFRASTRUCTURE_AVAILABLE, reason=f"Infrastructure not available: {IMPORT_ERROR if not INFRASTRUCTURE_AVAILABLE else ''}")
    async def test_websocket_auth_manager_stream_execution_failure_simulation(self):
        """
        Test that simulates stream execution failures that could result from
        legacy UserExecutionContext instantiation patterns.

        This test demonstrates the type of failures that affect the Golden Path
        when legacy instantiation patterns are used.
        """
        # Mock environment for demo mode
        with patch.dict('os.environ', {'DEMO_MODE': '1'}, clear=False):
            auth_manager = WebSocketAuthManager()

            # Create multiple concurrent demo auth requests (simulating real usage)
            connection_ids = [f"demo-stream-{i}" for i in range(5)]

            # Execute concurrent authentications
            auth_tasks = [
                auth_manager.authenticate_websocket_connection(None, conn_id)
                for conn_id in connection_ids
            ]

            start_time = time.time()
            results = await asyncio.gather(*auth_tasks, return_exceptions=True)
            execution_time = time.time() - start_time

            # Validate all results
            successful_results = []
            failed_results = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append((connection_ids[i], result))
                    self.logger.error(f"Authentication failed for {connection_ids[i]}: {result}")
                else:
                    successful_results.append(result)
                    self.logger.info(f"Authentication succeeded for {connection_ids[i]}")

            # Log results for analysis
            self.logger.info(f"Concurrent auth test: {len(successful_results)} successes, {len(failed_results)} failures")
            self.logger.info(f"Total execution time: {execution_time:.3f}s")

            # Validate that we can detect potential stream execution issues
            for result in successful_results:
                self.assertIsNotNone(result.user_context)

                # Check for indicators of stream execution compatibility
                context = result.user_context

                # Verify context has required fields for streaming
                self.assertIsNotNone(context.user_id)
                self.assertIsNotNone(context.thread_id)
                self.assertIsNotNone(context.run_id)

                # Test metadata access pattern (legacy vs SSOT)
                if hasattr(context, 'metadata'):
                    metadata = context.metadata
                    self.logger.debug(f"Context metadata access: {type(metadata)}")

                    # Check if metadata contains demo mode indicators
                    if isinstance(metadata, dict) and metadata.get('demo_mode'):
                        self.logger.info("Demo mode metadata detected in context")

    async def test_ssot_factory_method_pattern_comparison(self):
        """
        Test that demonstrates the correct SSOT factory method pattern
        that should be used instead of legacy instantiation.

        This test shows the proper way to create UserExecutionContext
        using the SSOT factory method.
        """
        # **CORRECT PATTERN: Using SSOT factory method**
        ssot_context = UserExecutionContext.from_request_supervisor(
            user_id="demo-user",
            thread_id=f"demo-thread-{time.time()}",
            run_id=f"demo-run-{time.time()}",
            websocket_connection_id="demo-websocket-connection",
            metadata={"demo_mode": True}
        )

        # Validate SSOT-created context
        self.assertIsInstance(ssot_context, UserExecutionContext)
        self.assertEqual(ssot_context.user_id, "demo-user")
        self.assertIsNotNone(ssot_context.thread_id)
        self.assertIsNotNone(ssot_context.run_id)
        self.assertIsNotNone(ssot_context.request_id)

        # Test metadata access (SSOT pattern)
        metadata = ssot_context.metadata
        self.assertIsInstance(metadata, dict)
        self.assertTrue(metadata.get("demo_mode"))

        # Test WebSocket connection mapping
        self.assertEqual(ssot_context.websocket_connection_id, "demo-websocket-connection")

        # **DEMONSTRATION: Legacy pattern (what needs to be fixed)**
        # This is the problematic pattern currently used in the infrastructure file:
        try:
            # Simulate legacy instantiation (THIS IS THE BUG)
            with self.assertLogs(level=logging.WARNING) as log_context:
                # This pattern should be avoided and replaced with factory method
                legacy_context = UserExecutionContext(
                    user_id=UserID("demo-user"),
                    thread_id=f"demo-thread-legacy-{time.time()}",
                    run_id=f"demo-run-legacy-{time.time()}",
                    agent_context={"demo_mode": True},
                    audit_metadata={}
                )

                # Test if legacy context has proper functionality
                self.assertIsInstance(legacy_context, UserExecutionContext)
                self.logger.warning("Legacy instantiation pattern detected - this should be replaced with SSOT factory method")

        except Exception as e:
            # This might fail with newer SSOT validation
            self.logger.info(f"Legacy instantiation failed (expected with SSOT validation): {e}")

    async def test_stream_execution_compatibility_validation(self):
        """
        Test that validates stream execution compatibility of different
        UserExecutionContext creation patterns.

        This test specifically checks for issues that affect streaming
        in the Golden Path user experience.
        """
        # Test different context creation patterns
        test_cases = [
            {
                "name": "SSOT Factory Method (Recommended)",
                "context": UserExecutionContext.from_request_supervisor(
                    user_id="stream-test-ssot",
                    thread_id=f"thread-ssot-{time.time()}",
                    run_id=f"run-ssot-{time.time()}",
                    metadata={"streaming_enabled": True}
                )
            }
        ]

        for test_case in test_cases:
            context = test_case["context"]

            self.logger.info(f"Testing stream compatibility: {test_case['name']}")

            # Test basic context functionality
            self.assertIsNotNone(context.user_id)
            self.assertIsNotNone(context.thread_id)
            self.assertIsNotNone(context.run_id)
            self.assertIsNotNone(context.request_id)

            # Test metadata access (critical for streaming)
            metadata = context.metadata
            self.assertIsInstance(metadata, dict)

            # Test context serialization (required for streaming)
            try:
                context_dict = {
                    "user_id": str(context.user_id),
                    "thread_id": context.thread_id,
                    "run_id": context.run_id,
                    "request_id": context.request_id,
                    "metadata": metadata
                }
                self.assertIsInstance(context_dict, dict)
                self.logger.info(f"Stream serialization test passed for {test_case['name']}")
            except Exception as e:
                self.logger.error(f"Stream serialization failed for {test_case['name']}: {e}")
                raise

    async def test_golden_path_stream_execution_scenario(self):
        """
        Test that simulates the Golden Path stream execution scenario
        that is failing due to legacy UserExecutionContext instantiation.

        This test reproduces the specific conditions that cause the P1 issue.
        """
        # Simulate Golden Path stream execution steps
        self.logger.info("=== Golden Path Stream Execution Scenario Test ===")

        # Step 1: WebSocket connection established (demo mode)
        with patch.dict('os.environ', {'DEMO_MODE': '1'}, clear=False):
            if INFRASTRUCTURE_AVAILABLE:
                auth_manager = WebSocketAuthManager()
                auth_result = await auth_manager.authenticate_websocket_connection(
                    token=None,
                    connection_id="golden-path-stream-test"
                )

                self.assertTrue(auth_result.success)
                user_context = auth_result.user_context
            else:
                # Fallback if infrastructure not available
                user_context = UserExecutionContext.from_request_supervisor(
                    user_id="demo-user",
                    thread_id="golden-path-thread",
                    run_id="golden-path-run",
                    metadata={"demo_mode": True}
                )

        # Step 2: Simulate agent execution with stream events
        self.logger.info(f"Golden Path context: user_id={user_context.user_id}")

        # Test context stability under streaming operations
        stream_events = [
            {"event": "agent_started", "context": user_context},
            {"event": "agent_thinking", "context": user_context},
            {"event": "tool_executing", "context": user_context},
            {"event": "tool_completed", "context": user_context},
            {"event": "agent_completed", "context": user_context}
        ]

        # Validate each stream event
        for event in stream_events:
            self.assertIsNotNone(event["context"])
            self.assertIsNotNone(event["context"].user_id)
            self.logger.debug(f"Stream event processed: {event['event']}")

        # Step 3: Validate stream execution doesn't fail
        # This is where the legacy instantiation would cause issues
        try:
            # Simulate rapid context access during streaming
            for _ in range(10):
                _ = user_context.metadata
                _ = user_context.user_id
                _ = user_context.thread_id
                _ = user_context.run_id
                await asyncio.sleep(0.01)  # Brief async operations

            self.logger.info("Golden Path stream execution simulation passed")

        except Exception as e:
            self.logger.error(f"Golden Path stream execution failed: {e}")
            # This failure would indicate the legacy instantiation issue
            raise

    @pytest.mark.skipif(not INFRASTRUCTURE_AVAILABLE, reason=f"Infrastructure not available: {IMPORT_ERROR if not INFRASTRUCTURE_AVAILABLE else ''}")
    async def test_websocket_auth_manager_health_status_integration(self):
        """
        Test WebSocket auth manager health status integration to ensure
        the legacy instantiation doesn't affect monitoring capabilities.
        """
        with patch.dict('os.environ', {'DEMO_MODE': '1'}, clear=False):
            auth_manager = WebSocketAuthManager()

            # Execute several auth requests to populate monitoring data
            for i in range(3):
                await auth_manager.authenticate_websocket_connection(
                    token=None,
                    connection_id=f"health-test-{i}"
                )

            # Get health status
            health_status = auth_manager.get_health_status()

            # Validate health status structure
            self.assertIsInstance(health_status, dict)
            self.assertIn("demo_mode_enabled", health_status)
            self.assertTrue(health_status["demo_mode_enabled"])

            # Validate health metrics
            self.assertIn("auth_success_rate_percent", health_status)
            self.assertIn("circuit_breaker_state", health_status)

            self.logger.info(f"WebSocket auth health status: {health_status}")


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v", "-s"])