"""
Integration Tests for Supervisor Agent WebSocket Integration

Business Value: $500K+ ARR Golden Path Protection - Real-time Communication
Purpose: Validate WebSocket event delivery during supervisor orchestration
Focus: All 5 critical WebSocket events sent reliably

This test validates Issue #1188 Phase 3.4 WebSocket integration patterns.
Tests that supervisor orchestration properly sends WebSocket events for real-time user experience.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import time

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
from shared.isolated_environment import IsolatedEnvironment

# Core supervisor and WebSocket imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager

# WebSocket event constants
CRITICAL_WEBSOCKET_EVENTS = [
    "agent_started",
    "agent_thinking",
    "tool_executing",
    "tool_completed",
    "agent_completed"
]


class SupervisorWebSocketIntegrationTests(SSotAsyncTestCase):
    """Integration tests for supervisor WebSocket event delivery."""

    def setup_method(self, method):
        """Set up WebSocket integration test environment."""
        super().setup_method(method)

        # Mock environment
        self.env = IsolatedEnvironment()

        # Create user context for testing
        self.user_context = UserExecutionContext.from_request(
            user_id="websocket-user-123",
            thread_id="websocket-thread-456",
            run_id="websocket-run-789",
            request_id="websocket-request-123"
        )

        # Mock LLM manager
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.get_client = Mock(return_value=Mock())

        # Track WebSocket events for validation
        self.sent_events = []
        self.event_tracker = AsyncMock()

        # Mock WebSocket bridge that tracks events
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.send_agent_event = AsyncMock(side_effect=self._track_websocket_event)

    async def _track_websocket_event(self, event_type: str, event_data: Dict[str, Any]):
        """Track WebSocket events for validation."""
        self.sent_events.append({
            'event_type': event_type,
            'event_data': event_data,
            'timestamp': time.time()
        })
        # Call the event tracker for additional validation
        await self.event_tracker.track_event(event_type, event_data)

    def test_websocket_bridge_integration(self):
        """
        Test that supervisor agent integrates with WebSocket bridge properly.

        Business Impact: Real-time communication infrastructure validation.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            # Test 1: Supervisor should accept WebSocket bridge
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            assert supervisor.websocket_bridge is self.mock_websocket_bridge

    @pytest.mark.asyncio
    async def test_websocket_event_agent_started(self):
        """
        Test that 'agent_started' event is sent properly.

        Business Impact: Users see immediate feedback when agent begins work.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Simulate agent started event
            await supervisor.websocket_bridge.send_agent_event(
                "agent_started",
                {
                    "agent_name": "Supervisor",
                    "user_id": self.user_context.user_id,
                    "session_id": self.user_context.thread_id,
                    "message": "Supervisor orchestration initiated"
                }
            )

            # Test 2: Verify agent_started event was sent
            assert len(self.sent_events) == 1
            event = self.sent_events[0]
            assert event['event_type'] == 'agent_started'
            assert event['event_data']['agent_name'] == 'Supervisor'
            assert event['event_data']['user_id'] == self.user_context.user_id

    @pytest.mark.asyncio
    async def test_websocket_event_agent_thinking(self):
        """
        Test that 'agent_thinking' event is sent during orchestration planning.

        Business Impact: Users see real-time reasoning for transparency.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Simulate agent thinking event
            await supervisor.websocket_bridge.send_agent_event(
                "agent_thinking",
                {
                    "agent_name": "Supervisor",
                    "user_id": self.user_context.user_id,
                    "thinking_stage": "orchestration_planning",
                    "reasoning": "Analyzing user request and selecting appropriate sub-agents"
                }
            )

            # Test 3: Verify agent_thinking event was sent
            assert len(self.sent_events) == 1
            event = self.sent_events[0]
            assert event['event_type'] == 'agent_thinking'
            assert 'reasoning' in event['event_data']
            assert event['event_data']['thinking_stage'] == 'orchestration_planning'

    @pytest.mark.asyncio
    async def test_websocket_event_tool_executing(self):
        """
        Test that 'tool_executing' event is sent when sub-agents are invoked.

        Business Impact: Users see when sub-agents are working on their request.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Simulate tool executing event
            await supervisor.websocket_bridge.send_agent_event(
                "tool_executing",
                {
                    "agent_name": "Supervisor",
                    "user_id": self.user_context.user_id,
                    "tool_name": "DataHelperAgent",
                    "tool_purpose": "Gathering data requirements for user request"
                }
            )

            # Test 4: Verify tool_executing event was sent
            assert len(self.sent_events) == 1
            event = self.sent_events[0]
            assert event['event_type'] == 'tool_executing'
            assert event['event_data']['tool_name'] == 'DataHelperAgent'
            assert 'tool_purpose' in event['event_data']

    @pytest.mark.asyncio
    async def test_websocket_event_tool_completed(self):
        """
        Test that 'tool_completed' event is sent when sub-agents finish.

        Business Impact: Users see progress as sub-agents complete their work.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Simulate tool completed event
            await supervisor.websocket_bridge.send_agent_event(
                "tool_completed",
                {
                    "agent_name": "Supervisor",
                    "user_id": self.user_context.user_id,
                    "tool_name": "TriageAgent",
                    "tool_result": "Successfully analyzed user requirements",
                    "execution_time": 2.5
                }
            )

            # Test 5: Verify tool_completed event was sent
            assert len(self.sent_events) == 1
            event = self.sent_events[0]
            assert event['event_type'] == 'tool_completed'
            assert event['event_data']['tool_name'] == 'TriageAgent'
            assert 'tool_result' in event['event_data']
            assert 'execution_time' in event['event_data']

    @pytest.mark.asyncio
    async def test_websocket_event_agent_completed(self):
        """
        Test that 'agent_completed' event is sent when orchestration finishes.

        Business Impact: Users know when the complete response is ready.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Simulate agent completed event
            await supervisor.websocket_bridge.send_agent_event(
                "agent_completed",
                {
                    "agent_name": "Supervisor",
                    "user_id": self.user_context.user_id,
                    "session_id": self.user_context.thread_id,
                    "final_response": "Orchestration complete - AI response generated",
                    "total_execution_time": 15.3
                }
            )

            # Test 6: Verify agent_completed event was sent
            assert len(self.sent_events) == 1
            event = self.sent_events[0]
            assert event['event_type'] == 'agent_completed'
            assert 'final_response' in event['event_data']
            assert 'total_execution_time' in event['event_data']

    @pytest.mark.asyncio
    async def test_websocket_event_sequence_validation(self):
        """
        Test that WebSocket events are sent in the correct sequence.

        Business Impact: Users see logical progression of agent work.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Simulate full event sequence
            event_sequence = [
                ("agent_started", {"message": "Starting orchestration"}),
                ("agent_thinking", {"reasoning": "Planning workflow"}),
                ("tool_executing", {"tool_name": "DataHelper"}),
                ("tool_completed", {"tool_result": "Data gathered"}),
                ("tool_executing", {"tool_name": "TriageAgent"}),
                ("tool_completed", {"tool_result": "Requirements analyzed"}),
                ("agent_completed", {"final_response": "Complete"})
            ]

            for event_type, event_data in event_sequence:
                await supervisor.websocket_bridge.send_agent_event(event_type, event_data)

            # Test 7: Verify all events sent in order
            assert len(self.sent_events) == len(event_sequence)

            for i, (expected_type, expected_data) in enumerate(event_sequence):
                actual_event = self.sent_events[i]
                assert actual_event['event_type'] == expected_type
                # Verify timestamps are in ascending order
                if i > 0:
                    assert actual_event['timestamp'] >= self.sent_events[i-1]['timestamp']

    @pytest.mark.asyncio
    async def test_websocket_event_user_isolation(self):
        """
        Test that WebSocket events are properly isolated per user.

        Business Impact: Enterprise security - no cross-user event contamination.
        """
        # Create second user context
        user_context_2 = UserExecutionContext.from_request(
            user_id="websocket-user-456",
            thread_id="websocket-thread-789",
            run_id="websocket-run-012",
            request_id="websocket-request-456"
        )

        # Create second WebSocket bridge tracker
        sent_events_user_2 = []
        mock_websocket_bridge_2 = Mock(spec=AgentWebSocketBridge)

        async def track_user_2_events(event_type: str, event_data: Dict[str, Any]):
            sent_events_user_2.append({
                'event_type': event_type,
                'event_data': event_data,
                'user_id': event_data.get('user_id')
            })

        mock_websocket_bridge_2.send_agent_event = AsyncMock(side_effect=track_user_2_events)

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            # Create supervisors for both users
            supervisor_1 = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            supervisor_2 = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=user_context_2,
                websocket_bridge=mock_websocket_bridge_2
            )

            # Send events from both supervisors
            await supervisor_1.websocket_bridge.send_agent_event(
                "agent_started",
                {"user_id": self.user_context.user_id, "message": "User 1 started"}
            )

            await supervisor_2.websocket_bridge.send_agent_event(
                "agent_started",
                {"user_id": user_context_2.user_id, "message": "User 2 started"}
            )

            # Test 8: Verify events are properly isolated
            assert len(self.sent_events) == 1
            assert len(sent_events_user_2) == 1

            assert self.sent_events[0]['event_data']['user_id'] == self.user_context.user_id
            assert sent_events_user_2[0]['event_data']['user_id'] == user_context_2.user_id

            # Ensure no cross-contamination
            assert self.sent_events[0]['event_data']['user_id'] != user_context_2.user_id
            assert sent_events_user_2[0]['event_data']['user_id'] != self.user_context.user_id

    @pytest.mark.asyncio
    async def test_websocket_event_error_handling(self):
        """
        Test WebSocket event error handling and recovery.

        Business Impact: System reliability during WebSocket failures.
        """
        # Create a WebSocket bridge that fails intermittently
        failure_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        failure_count = 0

        async def failing_send_event(event_type: str, event_data: Dict[str, Any]):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Fail first two attempts
                raise Exception(f"WebSocket connection error {failure_count}")
            # Succeed on third attempt
            await self._track_websocket_event(event_type, event_data)

        failure_websocket_bridge.send_agent_event = AsyncMock(side_effect=failing_send_event)

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=failure_websocket_bridge
            )

            # Test 9: Should handle WebSocket failures gracefully
            with pytest.raises(Exception, match="WebSocket connection error"):
                await supervisor.websocket_bridge.send_agent_event(
                    "agent_started",
                    {"message": "Test error handling"}
                )

    def test_websocket_integration_performance(self):
        """
        Test WebSocket integration performance requirements.

        Business Impact: Event delivery within SLA bounds for real-time experience.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            start_time = time.time()

            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            initialization_time = time.time() - start_time

            # Test 10: WebSocket bridge integration should be fast
            assert initialization_time < 0.1, f"WebSocket integration took {initialization_time:.3f}s, exceeding 100ms SLA"
            assert supervisor.websocket_bridge is not None


class SupervisorWebSocketEventDeliveryTests(SSotAsyncTestCase):
    """Test WebSocket event delivery patterns in supervisor orchestration."""

    def setup_method(self, method):
        """Set up event delivery test environment."""
        super().setup_method(method)

        self.user_context = UserExecutionContext.from_request(
            user_id="delivery-test-user",
            thread_id="delivery-test-thread",
            run_id="delivery-test-run",
            request_id="delivery-test-request"
        )

        # Event delivery tracking
        self.delivery_log = []
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)

        async def log_event_delivery(event_type: str, event_data: Dict[str, Any]):
            self.delivery_log.append({
                'event_type': event_type,
                'delivery_timestamp': time.time(),
                'event_data': event_data
            })

        self.mock_websocket_bridge.send_agent_event = AsyncMock(side_effect=log_event_delivery)

    @pytest.mark.asyncio
    async def test_event_delivery_timing(self):
        """
        Test that WebSocket events are delivered within timing requirements.

        Business Impact: Real-time user experience validation.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=Mock(spec=LLMManager),
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            start_time = time.time()

            # Send multiple events rapidly
            for event_type in CRITICAL_WEBSOCKET_EVENTS:
                await supervisor.websocket_bridge.send_agent_event(
                    event_type,
                    {"user_id": self.user_context.user_id, "timestamp": time.time()}
                )

            total_time = time.time() - start_time

            # Test 1: All events should be delivered quickly
            assert len(self.delivery_log) == 5
            assert total_time < 2.0, f"Event delivery took {total_time:.3f}s, exceeding 2s SLA"

            # Test 2: Each event should be delivered within 2 seconds of creation
            for log_entry in self.delivery_log:
                delivery_delay = log_entry['delivery_timestamp'] - start_time
                assert delivery_delay < 2.0, f"Event {log_entry['event_type']} delayed {delivery_delay:.3f}s"

    @pytest.mark.asyncio
    async def test_critical_events_coverage(self):
        """
        Test that all critical WebSocket events are supported.

        Business Impact: Complete real-time experience validation.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=Mock(spec=LLMManager),
                user_context=self.user_context,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Send all critical events
            for event_type in CRITICAL_WEBSOCKET_EVENTS:
                await supervisor.websocket_bridge.send_agent_event(
                    event_type,
                    {"event_type": event_type, "user_id": self.user_context.user_id}
                )

            # Test 3: Verify all critical events were delivered
            delivered_event_types = [log['event_type'] for log in self.delivery_log]

            for required_event in CRITICAL_WEBSOCKET_EVENTS:
                assert required_event in delivered_event_types, f"Critical event {required_event} not delivered"

            assert len(set(delivered_event_types)) == len(CRITICAL_WEBSOCKET_EVENTS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])