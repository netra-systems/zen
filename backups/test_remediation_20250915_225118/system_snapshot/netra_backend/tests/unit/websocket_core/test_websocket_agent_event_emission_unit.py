"""
Unit Tests for WebSocket Agent Event Emission - Issue #861 Phase 1

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Development Velocity & User Experience Quality
- Value Impact: Validates the 5 critical WebSocket events that deliver 90% of chat value
- Strategic Impact: Ensures real-time user feedback during $500K+ ARR agent processing

Test Coverage Focus:
- All 5 critical WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Event timing and sequencing validation  
- Event payload structure and content validation
- Error handling during event emission
- Event delivery confirmation and retry logic
- Multi-user event isolation

CRITICAL GOLDEN PATH EVENTS (must all be emitted):
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency  
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

REQUIREMENTS per CLAUDE.md:
- Use SSotBaseTestCase for unified test infrastructure
- Test actual WebSocket event emission, not just handlers
- Focus on business-critical golden path event sequence
- Validate event content matches user expectations
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from fastapi import WebSocket

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.handlers import AgentRequestHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage, create_server_message
from shared.isolated_environment import IsolatedEnvironment


class WebSocketAgentEventEmissionTests(SSotAsyncTestCase):
    """Test suite for WebSocket agent event emission validation."""

    def setup_method(self, method):
        """Set up test fixtures and WebSocket event tracking."""
        super().setup_method(method)
        
        # Create test environment
        self.env = IsolatedEnvironment()
        self.test_user_id = "event_test_user_" + str(uuid.uuid4())[:8]
        self.test_turn_id = "turn_" + str(uuid.uuid4())[:8]
        
        # Create mock WebSocket with event tracking
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.sent_events = []  # Track all sent events
        
        # Mock send_text to capture events
        async def track_sent_events(event_data):
            try:
                event_obj = json.loads(event_data)
                self.sent_events.append(event_obj)
            except json.JSONDecodeError:
                self.sent_events.append({"raw": event_data})
        
        self.mock_websocket.send_text = AsyncMock(side_effect=track_sent_events)
        
        # Create agent request handler for testing event emission
        self.handler = AgentRequestHandler()
        
        # Expected event sequence for golden path
        self.expected_event_sequence = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
        self.sent_events.clear()

    def create_agent_request_message(self, user_request: str, **kwargs) -> WebSocketMessage:
        """Create an agent request message for testing."""
        payload = {
            "message": user_request,
            "turn_id": self.test_turn_id,
            "require_multi_agent": kwargs.get("require_multi_agent", False),
            "real_llm": kwargs.get("real_llm", False),
            **kwargs
        }
        
        return WebSocketMessage(
            type=MessageType.AGENT_REQUEST,
            payload=payload,
            timestamp=time.time(),
            message_id=f"msg_{uuid.uuid4()}",
            user_id=self.test_user_id,
            thread_id=kwargs.get("thread_id", f"thread_{uuid.uuid4()}")
        )

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type from sent events."""
        return [event for event in self.sent_events 
                if event.get("event") == event_type or event.get("type") == event_type]

    def verify_event_sequence(self) -> bool:
        """Verify that all 5 critical events were sent in correct order."""
        event_types = []
        for event in self.sent_events:
            event_type = event.get("event") or event.get("type")
            if event_type in self.expected_event_sequence:
                event_types.append(event_type)
        
        return event_types == self.expected_event_sequence

    # Test 1: Complete Event Sequence Emission
    async def test_complete_golden_path_event_sequence(self):
        """Test that all 5 critical WebSocket events are emitted in correct order.
        
        Business Impact: This is the core user experience - users must see all agent progress.
        Golden Path Impact: Failure here means users don't know agent is working.
        """
        message = self.create_agent_request_message(
            "Analyze my data and provide insights",
            require_multi_agent=True,
            real_llm=True
        )
        
        # Process the agent request
        result = await self.handler.handle_message(
            self.test_user_id, 
            self.mock_websocket, 
            message
        )
        
        # Verify handler succeeded
        assert result is True
        
        # Verify all 5 events were sent
        assert len(self.sent_events) >= 5
        
        # Verify event sequence is correct
        assert self.verify_event_sequence(), f"Expected sequence {self.expected_event_sequence}, got event types: {[e.get('event', e.get('type')) for e in self.sent_events]}"
        
        # Verify each critical event was sent exactly once
        for event_type in self.expected_event_sequence:
            events = self.get_events_by_type(event_type)
            assert len(events) == 1, f"Expected exactly 1 {event_type} event, got {len(events)}"

    # Test 2: Agent Started Event Validation
    async def test_agent_started_event_structure_and_content(self):
        """Test agent_started event has correct structure and content.
        
        Business Impact: Users need immediate feedback that agent has begun processing.
        """
        message = self.create_agent_request_message("Start analysis task")
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Find agent_started event
        started_events = self.get_events_by_type("agent_started")
        assert len(started_events) == 1
        
        started_event = started_events[0]
        
        # Verify required fields
        assert started_event["event"] == "agent_started"
        assert started_event["type"] == "agent_started"
        assert started_event["status"] == "Agent execution started"
        assert started_event["user_id"] == self.test_user_id
        assert started_event["turn_id"] == self.test_turn_id
        assert "timestamp" in started_event
        assert isinstance(started_event["timestamp"], (int, float))

    # Test 3: Agent Thinking Event Validation
    async def test_agent_thinking_event_structure_and_content(self):
        """Test agent_thinking event shows processing status.
        
        Business Impact: Users see real-time indication that agent is actively reasoning.
        """
        message = self.create_agent_request_message("Complex reasoning task")
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Find agent_thinking event
        thinking_events = self.get_events_by_type("agent_thinking")
        assert len(thinking_events) == 1
        
        thinking_event = thinking_events[0]
        
        # Verify event content
        assert thinking_event["event"] == "agent_thinking"
        assert thinking_event["type"] == "agent_thinking" 
        assert thinking_event["status"] == "Agent is analyzing request"
        assert thinking_event["user_id"] == self.test_user_id
        assert thinking_event["turn_id"] == self.test_turn_id

    # Test 4: Tool Executing Event Validation
    async def test_tool_executing_event_structure_and_content(self):
        """Test tool_executing event provides tool transparency.
        
        Business Impact: Users understand what tools/capabilities agent is using.
        """
        message = self.create_agent_request_message("Use analysis tools")
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Find tool_executing event
        executing_events = self.get_events_by_type("tool_executing")
        assert len(executing_events) == 1
        
        executing_event = executing_events[0]
        
        # Verify tool execution details
        assert executing_event["event"] == "tool_executing"
        assert executing_event["type"] == "tool_executing"
        assert executing_event["status"] == "Executing analysis tools"
        assert executing_event["tool_name"] == "analysis_tool"
        assert executing_event["user_id"] == self.test_user_id
        assert executing_event["turn_id"] == self.test_turn_id

    # Test 5: Tool Completed Event Validation  
    async def test_tool_completed_event_structure_and_content(self):
        """Test tool_completed event shows tool results.
        
        Business Impact: Users see that tool execution finished and what was accomplished.
        """
        message = self.create_agent_request_message("Tool completion test")
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Find tool_completed event
        completed_events = self.get_events_by_type("tool_completed")
        assert len(completed_events) == 1
        
        completed_event = completed_events[0]
        
        # Verify completion details
        assert completed_event["event"] == "tool_completed"
        assert completed_event["type"] == "tool_completed"
        assert completed_event["status"] == "Tool execution completed"
        assert completed_event["tool_name"] == "analysis_tool"
        assert completed_event["result"] == "Analysis complete"
        assert completed_event["user_id"] == self.test_user_id
        assert completed_event["turn_id"] == self.test_turn_id

    # Test 6: Agent Completed Event Validation
    async def test_agent_completed_event_structure_and_content(self):
        """Test agent_completed event contains final response and metadata.
        
        Business Impact: Users get final response with orchestration details.
        Golden Path Impact: This is the culmination event - users see the result.
        """
        message = self.create_agent_request_message(
            "Final response test",
            require_multi_agent=True,
            real_llm=True
        )
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Find agent_completed event
        completed_events = self.get_events_by_type("agent_completed")
        assert len(completed_events) == 1
        
        completed_event = completed_events[0]
        
        # Verify final response structure
        assert completed_event["event"] == "agent_completed"
        assert completed_event["type"] == "agent_completed"
        assert completed_event["status"] == "success"
        assert "content" in completed_event
        assert "message" in completed_event
        assert completed_event["agents_involved"] == ["supervisor", "triage", "optimization"]
        assert isinstance(completed_event["orchestration_time"], (int, float))
        assert isinstance(completed_event["response_time"], (int, float))
        assert completed_event["turn_id"] == self.test_turn_id
        assert completed_event["user_id"] == self.test_user_id
        assert completed_event["real_llm_used"] is True

    # Test 7: Single Agent vs Multi-Agent Event Differences
    async def test_single_agent_vs_multi_agent_event_differences(self):
        """Test event content differs appropriately between single and multi-agent scenarios.
        
        Business Impact: Users understand complexity and orchestration involved.
        """
        # Test single agent scenario
        single_message = self.create_agent_request_message(
            "Simple single agent task",
            require_multi_agent=False
        )
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, single_message)
        
        single_completed = self.get_events_by_type("agent_completed")[0]
        
        # Clear events for multi-agent test
        self.sent_events.clear()
        
        # Test multi-agent scenario  
        multi_message = self.create_agent_request_message(
            "Complex multi-agent task",
            require_multi_agent=True
        )
        
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, multi_message)
        
        multi_completed = self.get_events_by_type("agent_completed")[0]
        
        # Verify differences
        assert single_completed["agents_involved"] == ["triage"]
        assert multi_completed["agents_involved"] == ["supervisor", "triage", "optimization"]
        assert single_completed["orchestration_time"] < multi_completed["orchestration_time"]

    # Test 8: Event Timing and Delays
    async def test_event_timing_and_realistic_delays(self):
        """Test that events have realistic timing delays between them.
        
        Business Impact: Events should feel natural, not instantaneous or too slow.
        """
        start_time = time.time()
        
        message = self.create_agent_request_message("Timing test")
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Should have taken some time due to asyncio.sleep delays
        assert total_duration >= 0.4  # At least 4 * 0.1 second delays
        
        # Verify timestamps are in ascending order
        event_timestamps = [event["timestamp"] for event in self.sent_events if "timestamp" in event]
        assert len(event_timestamps) >= 5
        assert event_timestamps == sorted(event_timestamps)

    # Test 9: Error Handling During Event Emission
    async def test_event_emission_error_handling(self):
        """Test graceful handling when WebSocket send fails during event emission.
        
        Business Impact: System should handle network issues gracefully.
        """
        # Make the first send_text call fail, then succeed
        send_call_count = 0
        
        async def failing_send_text(event_data):
            nonlocal send_call_count
            send_call_count += 1
            if send_call_count == 1:  # First call fails
                raise Exception("WebSocket send failed")
            else:
                # Track successful sends
                event_obj = json.loads(event_data)
                self.sent_events.append(event_obj)
        
        self.mock_websocket.send_text = AsyncMock(side_effect=failing_send_text)
        
        message = self.create_agent_request_message("Error handling test")
        
        # Should handle error and potentially retry or continue
        result = await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Handler should indicate failure due to first event send failure
        assert result is False
        
        # Should have attempted to send first event
        assert send_call_count >= 1

    # Test 10: Event Payload Content Validation
    async def test_event_payload_content_reflects_user_request(self):
        """Test that event content relates to the user's actual request.
        
        Business Impact: Events should be contextual and relevant to user's request.
        """
        user_request = "Analyze customer churn patterns in Q3 data"
        
        message = self.create_agent_request_message(user_request)
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify agent_completed event contains user request context
        completed_events = self.get_events_by_type("agent_completed")
        completed_event = completed_events[0]
        
        # Content should reference the user's request
        assert user_request in completed_event.get("content", "")
        assert user_request in completed_event.get("message", "")

    # Test 11: Multi-User Event Isolation  
    async def test_multi_user_event_isolation(self):
        """Test that events are properly isolated between different users.
        
        Business Impact: Critical for multi-tenant system - users must not see each other's events.
        """
        # Create two different users and handlers
        user1_id = "user1_" + str(uuid.uuid4())[:8]
        user2_id = "user2_" + str(uuid.uuid4())[:8]
        
        # Create separate websockets for each user
        websocket1 = MagicMock(spec=WebSocket)
        websocket2 = MagicMock(spec=WebSocket)
        
        user1_events = []
        user2_events = []
        
        async def track_user1_events(event_data):
            event_obj = json.loads(event_data)
            user1_events.append(event_obj)
        
        async def track_user2_events(event_data):
            event_obj = json.loads(event_data)
            user2_events.append(event_obj)
        
        websocket1.send_text = AsyncMock(side_effect=track_user1_events)
        websocket2.send_text = AsyncMock(side_effect=track_user2_events)
        
        # Create messages for each user
        message1 = self.create_agent_request_message("User 1 request")
        message1.user_id = user1_id
        
        message2 = self.create_agent_request_message("User 2 request") 
        message2.user_id = user2_id
        
        # Process both messages concurrently
        await asyncio.gather(
            self.handler.handle_message(user1_id, websocket1, message1),
            self.handler.handle_message(user2_id, websocket2, message2)
        )
        
        # Verify each user got their own events
        assert len(user1_events) >= 5
        assert len(user2_events) >= 5
        
        # Verify user isolation - each user only sees their own user_id in events
        for event in user1_events:
            if "user_id" in event:
                assert event["user_id"] == user1_id
        
        for event in user2_events:
            if "user_id" in event:
                assert event["user_id"] == user2_id

    # Test 12: Event JSON Serialization Correctness
    async def test_event_json_serialization_correctness(self):
        """Test that all events serialize properly as JSON.
        
        Business Impact: Events must be valid JSON for frontend consumption.
        """
        message = self.create_agent_request_message("Serialization test")
        await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
        
        # Verify all events are valid JSON structures
        for i, event in enumerate(self.sent_events):
            try:
                # Re-serialize to verify it's valid JSON
                json_str = json.dumps(event)
                parsed_back = json.loads(json_str)
                assert parsed_back == event
            except (TypeError, json.JSONDecodeError) as e:
                pytest.fail(f"Event {i} failed JSON serialization: {e}\nEvent: {event}")

    # Test 13: Event Emission Performance
    async def test_event_emission_performance_under_load(self):
        """Test event emission performance with multiple concurrent requests.
        
        Business Impact: System must handle multiple users simultaneously without degradation.
        """
        # Create multiple concurrent requests
        num_requests = 5
        tasks = []
        
        for i in range(num_requests):
            user_id = f"perf_user_{i}"
            websocket = MagicMock(spec=WebSocket)
            events_for_user = []
            
            async def track_events(event_data, user_events=events_for_user):
                event_obj = json.loads(event_data)
                user_events.append(event_obj)
            
            websocket.send_text = AsyncMock(side_effect=track_events)
            
            message = self.create_agent_request_message(f"Performance test {i}")
            message.user_id = user_id
            
            task = self.handler.handle_message(user_id, websocket, message)
            tasks.append((task, events_for_user))
        
        # Measure performance
        start_time = time.time()
        results = await asyncio.gather(*[task for task, _ in tasks])
        end_time = time.time()
        
        # Verify all requests succeeded
        assert all(results)
        
        # Verify reasonable performance (should handle 5 requests in under 5 seconds)
        assert end_time - start_time < 5.0
        
        # Verify each user got complete event sequence
        for _, events in tasks:
            event_types = [e.get("event", e.get("type")) for e in events]
            for expected_event in self.expected_event_sequence:
                assert expected_event in event_types

    # Test 14: Event Content Consistency Across Message Types  
    async def test_event_content_consistency_across_message_types(self):
        """Test that event content is consistent regardless of how agent was triggered.
        
        Business Impact: Consistent user experience across different entry points.
        """
        # Test with different message types that could trigger agent processing
        test_cases = [
            (MessageType.AGENT_REQUEST, "Handle agent request"),
            (MessageType.START_AGENT, "Start agent processing")
        ]
        
        for message_type, request_text in test_cases:
            # Clear previous events
            self.sent_events.clear()
            
            message = WebSocketMessage(
                type=message_type,
                payload={
                    "user_request" if message_type == MessageType.START_AGENT else "message": request_text,
                    "turn_id": f"turn_{message_type.value}"
                },
                timestamp=time.time(),
                user_id=self.test_user_id,
                thread_id=f"thread_{message_type.value}"
            )
            
            await self.handler.handle_message(self.test_user_id, self.mock_websocket, message)
            
            # Verify consistent event structure regardless of trigger
            assert len(self.sent_events) >= 5
            assert self.verify_event_sequence()
            
            # Verify all events have required fields
            for event in self.sent_events:
                assert "timestamp" in event
                assert event.get("user_id") == self.test_user_id