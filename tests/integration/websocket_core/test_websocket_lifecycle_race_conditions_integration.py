"""
Integration Tests for WebSocket Lifecycle Race Conditions - Issue #335

CRITICAL PURPOSE: These tests MUST FAIL initially to demonstrate race conditions
in realistic WebSocket lifecycle scenarios.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent WebSocket race conditions in production deployment
- Value Impact: Protects Golden Path reliability during connection lifecycle events
- Revenue Impact: Prevents chat disruption that affects $500K+ ARR

TEST STRATEGY:
Integration-level tests that reproduce race conditions between:
1. Connection lifecycle events (connect/disconnect/close)
2. Message sending operations (agent events, tool notifications)
3. State transitions in realistic timing scenarios

EXPECTED BEHAVIOR: These tests should FAIL initially, demonstrating that
race conditions exist in the integration between components.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Integration test imports
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateMachine
)
from netra_backend.app.websocket_core.agent_handler import WebSocketAgentHandler
from shared.types.core_types import UserID, ConnectionID, ThreadID
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketLifecycleRaceConditions(SSotAsyncTestCase):
    """
    Integration tests for WebSocket lifecycle race conditions.

    These tests reproduce race conditions that occur during realistic
    connection lifecycle scenarios with concurrent operations.
    """

    async def asyncSetUp(self):
        """Set up integration test environment."""
        await super().asyncSetUp()

        self.user_id = UserID("integration_race_user")
        self.connection_id = ConnectionID("integration_race_conn")
        self.thread_id = ThreadID("integration_race_thread")

        # Create realistic mock WebSocket
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.close = AsyncMock()

        # Create manager in test mode
        self.manager = UnifiedWebSocketManager(mode="integration_test")

        # Track timing events for race condition analysis
        self.timing_events = []

    async def test_agent_event_during_connection_close_race(self):
        """
        TEST SHOULD FAIL: Agent events sent during connection close should be handled safely.

        Race condition scenario:
        1. Agent starts processing and prepares to send events
        2. User closes browser/tab, initiating WebSocket close
        3. Agent attempts to send agent_started, agent_thinking, tool_executing events
        4. WebSocket is closing/closed but events are sent anyway
        5. Results in send-after-close exceptions

        This is a critical Golden Path race condition affecting user experience.
        """
        # ARRANGE: Set up realistic connection with agent events
        mock_connection = self._create_operational_connection()
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

        # Create agent event sequence
        agent_events = [
            {"type": "agent_started", "data": {"agent": "supervisor", "thread_id": str(self.thread_id)}},
            {"type": "agent_thinking", "data": {"message": "Analyzing request..."}},
            {"type": "tool_executing", "data": {"tool": "data_helper", "params": {}}},
            {"type": "tool_completed", "data": {"tool": "data_helper", "result": "success"}},
            {"type": "agent_completed", "data": {"result": "Task completed"}}
        ]

        # Event coordination
        close_initiated = asyncio.Event()
        events_started = asyncio.Event()
        race_detected = False

        async def simulate_user_disconnect():
            """Simulate user closing browser during agent processing."""
            self.timing_events.append(("close_initiated", time.time()))
            close_initiated.set()

            # Wait for events to start, then initiate close
            await asyncio.sleep(0.01)
            mock_connection.state = ApplicationConnectionState.CLOSING
            self.timing_events.append(("connection_closing", time.time()))

            await asyncio.sleep(0.01)
            mock_connection.state = ApplicationConnectionState.CLOSED
            self.timing_events.append(("connection_closed", time.time()))

        async def simulate_agent_event_sequence():
            """Simulate agent sending events during processing."""
            events_started.set()
            self.timing_events.append(("events_started", time.time()))

            # Wait for close to potentially start
            await asyncio.sleep(0.005)

            # Send events that may race with connection close
            for i, event in enumerate(agent_events):
                self.timing_events.append((f"sending_event_{i}", time.time()))

                # This should fail if connection is closing/closed and validation exists
                try:
                    await self.manager.emit_agent_event(
                        self.user_id, event["type"], event["data"]
                    )
                    self.timing_events.append((f"event_{i}_sent", time.time()))
                except Exception as e:
                    self.timing_events.append((f"event_{i}_failed", time.time(), str(e)))
                    if "clos" in str(e).lower():
                        nonlocal race_detected
                        race_detected = True
                        raise

                # Small delay between events to create race window
                await asyncio.sleep(0.005)

        # ACT: Run user disconnect and agent events concurrently
        disconnect_task = asyncio.create_task(simulate_user_disconnect())
        events_task = asyncio.create_task(simulate_agent_event_sequence())

        # The race condition should be detected and handled properly
        with pytest.raises((RuntimeError, ValueError, ConnectionError)) as exc_info:
            await asyncio.gather(disconnect_task, events_task)

        # ASSERT: Race condition should be detected and prevented
        assert race_detected, "Race condition should have been detected and handled"
        assert "clos" in str(exc_info.value).lower(), "Error should indicate connection closing issue"

        # Verify timing shows race condition occurred
        self._assert_race_condition_timing()

    async def test_multiple_agent_concurrent_sends_during_close(self):
        """
        TEST SHOULD FAIL: Multiple concurrent agent sends during close should be handled.

        Scenario: Multiple agents trying to send events simultaneously while connection closes.
        """
        # ARRANGE: Multiple agents with different event types
        mock_connection = self._create_operational_connection()
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

        # Multiple concurrent operations
        concurrent_operations = [
            ("supervisor", "agent_started", {"message": "Starting analysis"}),
            ("data_helper", "tool_executing", {"tool": "query_builder"}),
            ("triage", "agent_thinking", {"step": "categorizing_request"}),
            ("optimizer", "tool_completed", {"optimization": "complete"}),
            ("supervisor", "agent_completed", {"final_result": "success"})
        ]

        close_event = asyncio.Event()
        send_results = []

        async def close_connection_during_sends():
            """Close connection while multiple sends are in progress."""
            await asyncio.sleep(0.02)  # Let sends start
            mock_connection.state = ApplicationConnectionState.CLOSING
            close_event.set()
            await asyncio.sleep(0.01)
            mock_connection.state = ApplicationConnectionState.CLOSED

        async def concurrent_send_operation(agent_name, event_type, data):
            """Simulate concurrent send from different agents."""
            # Wait briefly to ensure race condition timing
            await asyncio.sleep(0.01)

            try:
                await self.manager.emit_agent_event(self.user_id, event_type, data)
                return ("success", agent_name, event_type)
            except Exception as e:
                return ("failed", agent_name, event_type, str(e))

        # ACT: Run all operations concurrently
        close_task = asyncio.create_task(close_connection_during_sends())

        send_tasks = [
            asyncio.create_task(concurrent_send_operation(agent, event_type, data))
            for agent, event_type, data in concurrent_operations
        ]

        # Wait for operations to complete
        await close_task

        # At least some sends should fail due to connection closing
        send_results = await asyncio.gather(*send_tasks, return_exceptions=True)

        # ASSERT: Some operations should detect the race condition and fail appropriately
        failed_operations = [r for r in send_results if isinstance(r, Exception) or r[0] == "failed"]
        assert len(failed_operations) > 0, "Some operations should fail due to race condition"

        # Verify failures are related to connection state
        connection_related_failures = [
            f for f in failed_operations
            if isinstance(f, tuple) and len(f) > 3 and "clos" in f[3].lower()
        ]
        assert len(connection_related_failures) > 0, "Failures should be connection-close related"

    async def test_websocket_bridge_race_condition_integration(self):
        """
        TEST SHOULD FAIL: WebSocket bridge should handle race conditions during agent integration.

        Tests the integration between WebSocket manager and agent handler during
        connection state transitions.
        """
        # ARRANGE: Set up WebSocket bridge integration
        mock_connection = self._create_operational_connection()
        self.manager.active_connections[self.user_id] = {self.connection_id: mock_connection}

        # Create agent handler integration
        agent_handler = WebSocketAgentHandler(self.manager)

        # Simulate bridge workflow
        workflow_events = [
            ("initialize_agent_context", {"context": "user_request"}),
            ("start_agent_processing", {"agent": "supervisor"}),
            ("agent_bridge_notification", {"status": "thinking"}),
            ("tool_bridge_execution", {"tool": "data_retrieval"}),
            ("completion_bridge_event", {"result": "success"})
        ]

        connection_transitions = [
            (0.01, ApplicationConnectionState.PROCESSING),
            (0.03, ApplicationConnectionState.CLOSING),  # Close during processing
            (0.05, ApplicationConnectionState.CLOSED)
        ]

        # Event tracking
        workflow_results = []
        state_transitions = []

        async def simulate_connection_state_transitions():
            """Simulate connection state changes during workflow."""
            for delay, new_state in connection_transitions:
                await asyncio.sleep(delay)
                mock_connection.state = new_state
                state_transitions.append((time.time(), new_state))

        async def simulate_bridge_workflow():
            """Simulate agent bridge workflow events."""
            for i, (event_type, data) in enumerate(workflow_events):
                try:
                    # Each bridge event includes WebSocket communication
                    await self.manager.emit_agent_event(
                        self.user_id, "bridge_event",
                        {"bridge_type": event_type, "data": data}
                    )
                    workflow_results.append(("success", i, event_type))
                    await asyncio.sleep(0.015)  # Realistic processing delay
                except Exception as e:
                    workflow_results.append(("failed", i, event_type, str(e)))
                    if "clos" in str(e).lower():
                        raise  # Expected race condition

        # ACT: Run bridge workflow with concurrent state transitions
        state_task = asyncio.create_task(simulate_connection_state_transitions())
        workflow_task = asyncio.create_task(simulate_bridge_workflow())

        # Race condition should be detected in bridge integration
        with pytest.raises((RuntimeError, ValueError, ConnectionError)):
            await asyncio.gather(state_task, workflow_task)

        # ASSERT: Integration should properly detect and handle race conditions
        failed_workflows = [r for r in workflow_results if r[0] == "failed"]
        assert len(failed_workflows) > 0, "Some bridge events should fail due to race condition"

        # Verify proper timing of race condition
        closing_time = next((t for t, s in state_transitions if s == ApplicationConnectionState.CLOSING), None)
        assert closing_time is not None, "Connection should have transitioned to closing"

    def _create_operational_connection(self):
        """Helper to create a realistic operational WebSocket connection."""
        mock_connection = Mock()
        mock_connection.websocket = self.mock_websocket
        mock_connection.user_id = self.user_id
        mock_connection.connection_id = self.connection_id
        mock_connection.state = ApplicationConnectionState.PROCESSING_READY
        mock_connection.is_closing = False  # This flag should be checked but currently isn't
        return mock_connection

    def _assert_race_condition_timing(self):
        """Assert that timing events show a race condition occurred."""
        # Look for overlapping timing between close and send events
        close_times = [t for event, t in self.timing_events if "clos" in event]
        send_times = [t for event, t, *_ in self.timing_events if "sending" in event]

        assert len(close_times) > 0, "Close events should have occurred"
        assert len(send_times) > 0, "Send events should have occurred"

        # Verify some sends occurred during or after close started
        min_close_time = min(close_times)
        overlapping_sends = [t for t in send_times if t >= min_close_time]

        assert len(overlapping_sends) > 0, "Some sends should have overlapped with connection close"


class TestWebSocketStateTransitionValidation(SSotAsyncTestCase):
    """
    Integration tests for missing state transition validation.

    These tests demonstrate the lack of proper validation during
    state transitions that cause race conditions.
    """

    async def test_missing_state_validation_before_send(self):
        """
        TEST SHOULD FAIL: State validation before send operations should exist but doesn't.

        This test demonstrates that the system lacks proper state validation
        before attempting WebSocket send operations.
        """
        # ARRANGE: Create manager and connection
        manager = UnifiedWebSocketManager(mode="test")
        user_id = UserID("state_validation_test")
        connection_id = ConnectionID("state_validation_conn")

        # Create connection in various states
        test_states = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.CLOSING,
            ApplicationConnectionState.CLOSED,
            ApplicationConnectionState.FAILED
        ]

        for state in test_states:
            with self.subTest(state=state):
                mock_connection = Mock()
                mock_connection.websocket = AsyncMock()
                mock_connection.state = state
                mock_connection.user_id = user_id

                manager.active_connections[user_id] = {connection_id: mock_connection}

                # ACT: Attempt to send message without state validation
                test_message = {"type": "test", "data": f"state_{state}"}

                # ASSERT: Should fail for non-operational states (but currently doesn't)
                if not ApplicationConnectionState.is_operational(state):
                    with pytest.raises((RuntimeError, ValueError, ConnectionError)):
                        await manager.send_message(user_id, test_message)
                else:
                    # Operational states should work
                    await manager.send_message(user_id, test_message)
                    mock_connection.websocket.send_json.assert_called_once()

                # Clean up for next iteration
                manager.active_connections.clear()

    async def test_is_closing_flag_pattern_missing(self):
        """
        TEST SHOULD FAIL: Common is_closing flag pattern should exist but doesn't.

        Many WebSocket implementations use an `is_closing` flag to prevent
        send-after-close issues. This test verifies this pattern is implemented.
        """
        # ARRANGE: Create connection that should have is_closing flag
        mock_connection = Mock()
        mock_connection.websocket = AsyncMock()
        mock_connection.is_closing = True  # This flag should be checked

        # Create manager
        manager = UnifiedWebSocketManager(mode="test")
        user_id = UserID("closing_flag_test")

        # ACT: Check if manager validates is_closing flag
        with patch.object(manager, 'get_connection', return_value=mock_connection):
            with pytest.raises((RuntimeError, ValueError)):
                # This should fail because connection is_closing=True
                # But the validation doesn't exist yet (test will fail)
                await manager.send_message(user_id, {"type": "test"})

        # ASSERT: The pattern should exist but currently doesn't
        # This test documents the missing validation pattern


if __name__ == "__main__":
    # Run integration tests to demonstrate race conditions
    # EXPECTED: Tests should FAIL initially, proving race conditions exist
    pytest.main([__file__, "-v", "--tb=short"])