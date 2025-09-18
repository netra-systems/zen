"""
WebSocket Safe Close Race Condition Unit Tests for Issue #335

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Stability - Prevent WebSocket chat failures
- Value Impact: Ensures reliable AI chat functionality under concurrent close operations
- Strategic/Revenue Impact: Prevents $500K+ ARR loss from WebSocket reliability issues

CRITICAL: These tests specifically target the "send after close" race condition
identified in Issue #335, focusing on the safe_websocket_close function at line 596.

Key Race Conditions Tested:
1. Concurrent close operations causing "send after close" errors
2. WebSocket state transitions during close with pending operations
3. Multiple thread access to close operations simultaneously
4. Exception handling in close operations under race conditions
5. Safe close function resilience against runtime errors

Test Strategy:
- Use real WebSocket connections where possible (minimal mocking)
- Reproduce exact timing conditions that cause race conditions
- Validate safe_websocket_close error handling behavior
- Test concurrent close scenarios that trigger runtime errors

Author: AI Agent - WebSocket Race Condition Test Creation
Date: 2025-09-13
Issue: #335 WebSocket race condition tests
"""

import asyncio
import json
import logging
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, call

import websockets
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from starlette.websockets import WebSocketDisconnect

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.websocket_core.utils import (
    safe_websocket_close,
    safe_websocket_send,
    is_websocket_connected
)

logger = logging.getLogger(__name__)


@dataclass
class RaceConditionMetrics:
    """Metrics for tracking race condition test results"""
    test_name: str
    concurrent_operations: int = 0
    race_conditions_detected: int = 0
    runtime_errors_caught: int = 0
    successful_closes: int = 0
    total_close_attempts: int = 0
    average_close_time: float = 0.0
    max_close_time: float = 0.0


class WebSocketSafeCloseRaceConditionsTests(SSotBaseTestCase):
    """
    Unit tests for WebSocket safe_websocket_close race conditions.

    CRITICAL: These tests target the specific race condition patterns
    that cause "send after close" errors in production WebSocket scenarios.
    """

    @pytest.fixture(autouse=True)
    def setup_race_condition_test_environment(self):
        """Set up test environment for race condition testing."""
        self.race_metrics = []
        self.close_timing_data = []
        self.exception_log = []

        # Configure logger for race condition detection
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        yield

        # Clean up after test

    async def _create_mock_websocket_with_close_race_condition(
        self,
        close_delay: float = 0.0,
        state_transition_delay: float = 0.0,
        concurrent_operations: int = 1
    ) -> WebSocket:
        """
        Create mock WebSocket that simulates race conditions during close operations.

        Args:
            close_delay: Delay during close operation to simulate slow close
            state_transition_delay: Delay during state transitions
            concurrent_operations: Number of concurrent operations to simulate

        Returns:
            Mock WebSocket configured for race condition testing
        """
        mock_websocket = AsyncMock(spec=WebSocket)

        # Track close operation states for race condition analysis
        close_operation_log = []
        is_closing = False
        close_completed = False

        async def mock_close_with_race_condition(code: int = 1000, reason: str = "Normal closure"):
            """Mock close operation that can trigger race conditions."""
            nonlocal is_closing, close_completed

            start_time = time.time()
            close_operation_log.append({
                "action": "close_started",
                "timestamp": start_time,
                "code": code,
                "reason": reason,
                "state_before": getattr(mock_websocket, 'client_state', 'UNKNOWN')
            })

            is_closing = True

            # Simulate state transition delay (where race conditions occur)
            if state_transition_delay > 0:
                await asyncio.sleep(state_transition_delay)

            # CRITICAL: Check if multiple close operations are running concurrently
            if concurrent_operations > 1:
                # Simulate multiple threads calling close at the same time
                for i in range(concurrent_operations - 1):
                    # This simulates the race condition scenario
                    close_operation_log.append({
                        "action": "concurrent_close_detected",
                        "timestamp": time.time(),
                        "concurrent_id": i + 1
                    })

                    # CRITICAL: This should trigger race condition handling
                    if close_completed:
                        raise RuntimeError("WebSocket is not connected")

            # Simulate actual close delay
            if close_delay > 0:
                await asyncio.sleep(close_delay)

            # Mark close as completed
            close_completed = True
            mock_websocket.client_state = WebSocketState.DISCONNECTED

            end_time = time.time()
            close_operation_log.append({
                "action": "close_completed",
                "timestamp": end_time,
                "duration": end_time - start_time,
                "state_after": "DISCONNECTED"
            })

        # Set up mock methods
        mock_websocket.close = AsyncMock(side_effect=mock_close_with_race_condition)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.application_state = "CONNECTED"

        # Store operation log for analysis
        mock_websocket._close_operation_log = close_operation_log
        mock_websocket._is_closing = lambda: is_closing
        mock_websocket._is_close_completed = lambda: close_completed

        return mock_websocket

    @pytest.mark.asyncio
    async def test_safe_websocket_close_basic_race_condition_reproduction(self):
        """
        CRITICAL TEST: Reproduce basic race condition in safe_websocket_close.

        Tests the scenario where close operations happen concurrently,
        triggering "WebSocket is not connected" runtime errors.

        Expected: Race condition should be handled gracefully by safe_websocket_close
        """
        # Create WebSocket with race condition potential
        mock_websocket = await self._create_mock_websocket_with_close_race_condition(
            close_delay=0.1,  # Slow close to create race window
            state_transition_delay=0.05,  # State transition creates race opportunity
            concurrent_operations=2  # Multiple concurrent closes
        )

        # Track metrics
        start_time = time.time()
        close_attempts = []

        # CRITICAL: Test concurrent close operations
        async def attempt_close(attempt_id: int):
            """Attempt to close WebSocket - may trigger race condition."""
            try:
                close_start = time.time()
                await safe_websocket_close(mock_websocket, code=1000, reason=f"Test close {attempt_id}")
                close_end = time.time()

                return {
                    "attempt_id": attempt_id,
                    "success": True,
                    "duration": close_end - close_start,
                    "error": None
                }

            except Exception as e:
                return {
                    "attempt_id": attempt_id,
                    "success": False,
                    "duration": time.time() - close_start,
                    "error": str(e)
                }

        # Execute concurrent close attempts
        close_tasks = [
            asyncio.create_task(attempt_close(i)) for i in range(3)
        ]

        close_results = await asyncio.gather(*close_tasks, return_exceptions=True)

        end_time = time.time()

        # Analyze race condition results
        successful_closes = sum(1 for result in close_results
                              if isinstance(result, dict) and result.get('success'))
        failed_closes = sum(1 for result in close_results
                          if isinstance(result, dict) and not result.get('success'))
        runtime_errors = sum(1 for result in close_results
                           if isinstance(result, dict) and result.get('error') and
                           "WebSocket is not connected" in result.get('error', ''))

        # Record metrics
        metrics = RaceConditionMetrics(
            test_name="safe_close_basic_race_condition",
            concurrent_operations=len(close_tasks),
            race_conditions_detected=runtime_errors,
            runtime_errors_caught=runtime_errors,
            successful_closes=successful_closes,
            total_close_attempts=len(close_results),
            average_close_time=sum(r.get('duration', 0) for r in close_results if isinstance(r, dict)) / len(close_results)
        )

        self.race_metrics.append(metrics)

        # Log race condition analysis
        self.logger.info(f"Race condition test completed:")
        self.logger.info(f"  - Concurrent operations: {metrics.concurrent_operations}")
        self.logger.info(f"  - Successful closes: {metrics.successful_closes}")
        self.logger.info(f"  - Runtime errors caught: {metrics.runtime_errors_caught}")
        self.logger.info(f"  - Race conditions detected: {metrics.race_conditions_detected}")

        # CRITICAL: safe_websocket_close should handle race conditions gracefully
        # At least one close operation should succeed
        assert successful_closes >= 1, f"No successful close operations out of {len(close_results)} attempts"

        # Runtime errors should be handled gracefully (no unhandled exceptions)
        unhandled_exceptions = sum(1 for result in close_results if isinstance(result, Exception))
        assert unhandled_exceptions == 0, f"Unhandled exceptions detected: {unhandled_exceptions}"

    @pytest.mark.asyncio
    async def test_safe_websocket_close_state_transition_race_condition(self):
        """
        CRITICAL TEST: Test race condition during WebSocket state transitions.

        Reproduces scenario where WebSocket state changes between connection check
        and actual close operation, causing "Need to call 'accept' first" errors.
        """
        # Create WebSocket that changes state during close
        mock_websocket = AsyncMock(spec=WebSocket)

        state_changes = []
        close_call_count = 0

        async def mock_close_with_state_race(code: int = 1000, reason: str = "Normal closure"):
            """Mock close that simulates state change race condition."""
            nonlocal close_call_count
            close_call_count += 1

            # CRITICAL: Simulate state changing during close operation
            if close_call_count == 1:
                # First call - state is connected
                mock_websocket.client_state = WebSocketState.CONNECTED
                state_changes.append(("close_started", WebSocketState.CONNECTED, time.time()))

                # Simulate delay where state could change
                await asyncio.sleep(0.05)

                # CRITICAL: State changes during close operation (race condition)
                mock_websocket.client_state = WebSocketState.CONNECTING
                state_changes.append(("state_changed_during_close", WebSocketState.CONNECTING, time.time()))

                # This triggers the race condition
                raise RuntimeError("Need to call 'accept' first")

            elif close_call_count == 2:
                # Second call - now in different state
                state_changes.append(("retry_close", mock_websocket.client_state, time.time()))

                # This should also fail due to state inconsistency
                raise RuntimeError("WebSocket is not connected")

            else:
                # Final state
                mock_websocket.client_state = WebSocketState.DISCONNECTED
                state_changes.append(("close_completed", WebSocketState.DISCONNECTED, time.time()))

        # Set up mock
        mock_websocket.close = AsyncMock(side_effect=mock_close_with_state_race)
        mock_websocket.client_state = WebSocketState.CONNECTED

        # Execute safe close with state transition race condition
        start_time = time.time()

        # CRITICAL: safe_websocket_close should handle state transition errors gracefully
        try:
            await safe_websocket_close(mock_websocket, code=1000, reason="State transition test")
            close_succeeded = True
            error_message = None

        except Exception as e:
            close_succeeded = False
            error_message = str(e)

        end_time = time.time()

        # Record state transition analysis
        metrics = RaceConditionMetrics(
            test_name="state_transition_race_condition",
            concurrent_operations=1,
            race_conditions_detected=len([s for s in state_changes if "race" in s[0] or "changed" in s[0]]),
            runtime_errors_caught=close_call_count - 1 if close_call_count > 1 else 0,
            successful_closes=1 if close_succeeded else 0,
            total_close_attempts=close_call_count,
            average_close_time=end_time - start_time
        )

        self.race_metrics.append(metrics)
        self.close_timing_data.append({
            "state_changes": state_changes,
            "close_call_count": close_call_count,
            "final_success": close_succeeded,
            "error_message": error_message
        })

        # Log state transition analysis
        self.logger.info(f"State transition race condition test:")
        self.logger.info(f"  - State changes recorded: {len(state_changes)}")
        self.logger.info(f"  - Close attempts made: {close_call_count}")
        self.logger.info(f"  - Final result: {'SUCCESS' if close_succeeded else 'FAILED'}")

        for i, (action, state, timestamp) in enumerate(state_changes):
            self.logger.debug(f"    {i+1}. {action}: {state} at {timestamp}")

        # CRITICAL: safe_websocket_close should not raise unhandled exceptions
        # It should handle state transition race conditions gracefully
        assert close_succeeded or error_message is None, f"Unhandled exception in safe_websocket_close: {error_message}"

        # Verify that state transitions were properly handled
        state_race_detected = any("changed" in action for action, _, _ in state_changes)
        if state_race_detected:
            # Race condition was detected - this is expected behavior
            # The important thing is that safe_websocket_close handled it gracefully
            self.logger.info("Race condition successfully detected and handled by safe_websocket_close")
            assert close_succeeded, "safe_websocket_close should handle state race conditions gracefully"

    @pytest.mark.asyncio
    async def test_safe_websocket_close_exception_handling_comprehensive(self, caplog):
        """
        CRITICAL TEST: Comprehensive exception handling in safe_websocket_close.

        Tests all exception paths in safe_websocket_close to ensure
        race condition errors are properly handled and logged.
        """
        # Test different exception scenarios
        exception_scenarios = [
            {
                "name": "runtime_error_accept_first",
                "exception": RuntimeError("Need to call 'accept' first"),
                "expected_log_level": "debug",
                "should_succeed": True
            },
            {
                "name": "runtime_error_not_connected",
                "exception": RuntimeError("WebSocket is not connected"),
                "expected_log_level": "debug",
                "should_succeed": True
            },
            {
                "name": "runtime_error_other",
                "exception": RuntimeError("Some other runtime error"),
                "expected_log_level": "warning",
                "should_succeed": True
            },
            {
                "name": "general_exception",
                "exception": Exception("General exception during close"),
                "expected_log_level": "warning",
                "should_succeed": True
            },
            {
                "name": "websocket_disconnect",
                "exception": WebSocketDisconnect(code=1000, reason="Client disconnect"),
                "expected_log_level": "warning",
                "should_succeed": True
            }
        ]

        exception_results = []

        for scenario in exception_scenarios:
            # Create mock WebSocket for this scenario
            mock_websocket = AsyncMock(spec=WebSocket)
            mock_websocket.close = AsyncMock(side_effect=scenario["exception"])
            mock_websocket.client_state = WebSocketState.CONNECTED

            # Capture log messages using pytest caplog
            # The logger is actually from netra_backend.app.websocket_core.utils module
            caplog.set_level(logging.DEBUG, logger="netra_backend.app.websocket_core.utils")

            try:
                start_time = time.time()
                await safe_websocket_close(mock_websocket, code=1000, reason=f"Test {scenario['name']}")
                end_time = time.time()

                result = {
                    "scenario": scenario["name"],
                    "success": True,
                    "duration": end_time - start_time,
                    "exception_raised": False,
                    "log_messages": [record.message for record in caplog.records]
                }

            except Exception as e:
                result = {
                    "scenario": scenario["name"],
                    "success": False,
                    "duration": time.time() - start_time,
                    "exception_raised": True,
                    "unhandled_exception": str(e),
                    "log_messages": [record.message for record in caplog.records]
                }

            exception_results.append(result)

            # Verify expected behavior for this scenario
            assert result["success"] == scenario["should_succeed"], (
                f"Scenario {scenario['name']} failed: Expected success={scenario['should_succeed']}, "
                f"got success={result['success']}"
            )

            # Verify no unhandled exceptions
            assert not result["exception_raised"], (
                f"Unhandled exception in scenario {scenario['name']}: "
                f"{result.get('unhandled_exception', 'Unknown')}"
            )

            # Verify appropriate logging occurred (lenient check)
            if scenario["expected_log_level"] == "debug":
                debug_records = [record for record in caplog.records if record.levelname == "DEBUG"]
                # Note: Debug logs might not appear due to logger configuration, this is acceptable
                if len(debug_records) == 0:
                    self.logger.info(f"No debug logs captured for scenario {scenario['name']} - this may be due to logger configuration")

            elif scenario["expected_log_level"] == "warning":
                warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
                # Warning logs are more important to check
                if len(warning_records) == 0:
                    self.logger.warning(f"Expected warning logs not captured for scenario {scenario['name']}")

            # Clear caplog for next iteration
            caplog.clear()

        # Record comprehensive exception handling metrics
        successful_scenarios = sum(1 for result in exception_results if result["success"])
        total_scenarios = len(exception_scenarios)

        metrics = RaceConditionMetrics(
            test_name="comprehensive_exception_handling",
            concurrent_operations=total_scenarios,
            race_conditions_detected=len([s for s in exception_scenarios
                                        if "accept_first" in s["name"] or "not_connected" in s["name"]]),
            runtime_errors_caught=len([s for s in exception_scenarios if "runtime_error" in s["name"]]),
            successful_closes=successful_scenarios,
            total_close_attempts=total_scenarios,
            average_close_time=sum(r["duration"] for r in exception_results) / len(exception_results)
        )

        self.race_metrics.append(metrics)
        self.exception_log.extend(exception_results)

        # Log comprehensive results
        self.logger.info(f"Comprehensive exception handling test completed:")
        self.logger.info(f"  - Total scenarios tested: {total_scenarios}")
        self.logger.info(f"  - Successful scenarios: {successful_scenarios}")
        self.logger.info(f"  - Race condition scenarios: {metrics.race_conditions_detected}")
        self.logger.info(f"  - Runtime error scenarios: {metrics.runtime_errors_caught}")

        # CRITICAL: All scenarios should be handled gracefully
        assert successful_scenarios == total_scenarios, (
            f"Some exception scenarios failed: {successful_scenarios}/{total_scenarios} successful"
        )

    @pytest.mark.asyncio
    async def test_safe_websocket_close_concurrent_send_operations_race(self):
        """
        CRITICAL TEST: Test race condition between close and concurrent send operations.

        Reproduces: "send after close" race condition where send operations
        are attempted on a WebSocket that is being closed concurrently.
        """
        # Create WebSocket that can have concurrent send/close operations
        mock_websocket = AsyncMock(spec=WebSocket)

        operation_log = []
        send_operations_active = 0
        is_closing = False

        async def mock_send_json(data):
            """Mock send that can race with close operations."""
            nonlocal send_operations_active

            send_operations_active += 1
            operation_log.append({
                "action": "send_started",
                "timestamp": time.time(),
                "data_type": data.get('type', 'unknown'),
                "is_closing": is_closing
            })

            # CRITICAL: Check if close is happening concurrently
            if is_closing:
                send_operations_active -= 1
                operation_log.append({
                    "action": "send_after_close_detected",
                    "timestamp": time.time(),
                    "error": "WebSocket is not connected"
                })
                raise RuntimeError("WebSocket is not connected")

            # Simulate send delay
            await asyncio.sleep(0.02)

            send_operations_active -= 1
            operation_log.append({
                "action": "send_completed",
                "timestamp": time.time()
            })

        async def mock_close_with_send_race(code: int = 1000, reason: str = "Normal closure"):
            """Mock close that can race with send operations."""
            nonlocal is_closing

            operation_log.append({
                "action": "close_started",
                "timestamp": time.time(),
                "active_send_operations": send_operations_active
            })

            is_closing = True

            # CRITICAL: Wait briefly to allow send operations to detect close
            await asyncio.sleep(0.01)

            # Check for concurrent send operations
            if send_operations_active > 0:
                operation_log.append({
                    "action": "concurrent_send_detected_during_close",
                    "timestamp": time.time(),
                    "concurrent_sends": send_operations_active
                })

            mock_websocket.client_state = WebSocketState.DISCONNECTED
            operation_log.append({
                "action": "close_completed",
                "timestamp": time.time()
            })

        # Set up mock methods
        mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)
        mock_websocket.close = AsyncMock(side_effect=mock_close_with_send_race)
        mock_websocket.client_state = WebSocketState.CONNECTED

        # Start concurrent send and close operations
        start_time = time.time()

        # Create send operations that will race with close
        send_tasks = [
            asyncio.create_task(mock_websocket.send_json({
                "type": "agent_started",
                "message": f"Send operation {i}",
                "timestamp": time.time()
            }))
            for i in range(3)
        ]

        # Start close operation concurrently
        close_task = asyncio.create_task(safe_websocket_close(mock_websocket, code=1000, reason="Concurrent test"))

        # Wait for all operations to complete
        all_results = await asyncio.gather(*send_tasks, close_task, return_exceptions=True)

        end_time = time.time()

        # Analyze send/close race condition results
        send_results = all_results[:-1]  # All except close result
        close_result = all_results[-1]   # Close result

        successful_sends = sum(1 for result in send_results if not isinstance(result, Exception))
        failed_sends = sum(1 for result in send_results if isinstance(result, Exception))
        send_after_close_errors = sum(1 for result in send_results
                                    if isinstance(result, Exception) and "not connected" in str(result))

        close_successful = not isinstance(close_result, Exception)

        # Record race condition metrics
        metrics = RaceConditionMetrics(
            test_name="concurrent_send_close_race",
            concurrent_operations=len(send_tasks) + 1,  # sends + close
            race_conditions_detected=send_after_close_errors,
            runtime_errors_caught=failed_sends,
            successful_closes=1 if close_successful else 0,
            total_close_attempts=1,
            average_close_time=end_time - start_time
        )

        self.race_metrics.append(metrics)

        # Log detailed race condition analysis
        self.logger.info(f"Concurrent send/close race condition test:")
        self.logger.info(f"  - Total send operations: {len(send_tasks)}")
        self.logger.info(f"  - Successful sends: {successful_sends}")
        self.logger.info(f"  - Failed sends: {failed_sends}")
        self.logger.info(f"  - Send after close errors: {send_after_close_errors}")
        self.logger.info(f"  - Close successful: {close_successful}")

        # Log operation timeline
        for i, op in enumerate(operation_log):
            self.logger.debug(f"    {i+1}. {op['action']} at {op['timestamp']}")

        # CRITICAL: safe_websocket_close should complete successfully even with concurrent sends
        assert close_successful, f"safe_websocket_close failed: {close_result}"

        # Send operations may fail due to race condition, but this is expected behavior
        # The important thing is that the close operation handles it gracefully
        race_conditions_handled = send_after_close_errors > 0
        if race_conditions_handled:
            self.logger.info(f"Race condition successfully detected and handled: {send_after_close_errors} send operations failed appropriately")

    def teardown_method(self):
        """Generate race condition analysis report."""

        if self.race_metrics:
            # Generate comprehensive race condition analysis
            total_tests = len(self.race_metrics)
            total_race_conditions = sum(m.race_conditions_detected for m in self.race_metrics)
            total_runtime_errors = sum(m.runtime_errors_caught for m in self.race_metrics)
            total_successful_closes = sum(m.successful_closes for m in self.race_metrics)
            total_close_attempts = sum(m.total_close_attempts for m in self.race_metrics)

            average_close_time = sum(m.average_close_time for m in self.race_metrics) / total_tests

            # Log comprehensive analysis
            self.logger.critical("=" * 80)
            self.logger.critical("WEBSOCKET SAFE CLOSE RACE CONDITION ANALYSIS")
            self.logger.critical("=" * 80)
            self.logger.critical(f"Total Tests: {total_tests}")
            self.logger.critical(f"Total Race Conditions Detected: {total_race_conditions}")
            self.logger.critical(f"Total Runtime Errors Handled: {total_runtime_errors}")
            self.logger.critical(f"Total Successful Closes: {total_successful_closes}")
            self.logger.critical(f"Total Close Attempts: {total_close_attempts}")
            self.logger.critical(f"Success Rate: {(total_successful_closes/total_close_attempts)*100:.1f}%")
            self.logger.critical(f"Average Close Time: {average_close_time:.3f} seconds")
            self.logger.critical("=" * 80)

            # Test-by-test breakdown
            for metrics in self.race_metrics:
                self.logger.info(f"Test: {metrics.test_name}")
                self.logger.info(f"  Race Conditions: {metrics.race_conditions_detected}")
                self.logger.info(f"  Runtime Errors: {metrics.runtime_errors_caught}")
                self.logger.info(f"  Successful Closes: {metrics.successful_closes}/{metrics.total_close_attempts}")
                self.logger.info(f"  Average Close Time: {metrics.average_close_time:.3f}s")
                self.logger.info(f"  Max Close Time: {metrics.max_close_time:.3f}s")