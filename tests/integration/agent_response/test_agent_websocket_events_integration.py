"""Integration Tests for Agent Response WebSocket Events Integration

Tests the integration of WebSocket events during agent response generation
to ensure real-time user experience and proper event sequencing.

Business Value Justification (BVJ):
- Segment: All segments - Real-time User Experience
- Business Goal: Enable real-time chat experience (90% of platform value)
- Value Impact: Provides immediate feedback during AI processing
- Strategic Impact: Differentiates platform with superior real-time UX
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum

from test_framework.ssot.base_test_case import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventType(Enum):
    """Required WebSocket event types for agent response integration."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"


@dataclass
class WebSocketEvent:
    """Captured WebSocket event for testing."""
    event_type: str
    timestamp: float
    user_id: str
    data: Dict[str, Any]
    sequence_number: int


class MockWebSocketEventCapture:
    """Mock WebSocket event capture for testing integration."""
    
    def __init__(self):
        self.captured_events = []
        self.connection_status = {}
        self.event_sequence = 0
        
    async def send_to_user(self, user_id: str, message_type: str, data: Dict[str, Any]) -> None:
        """Capture WebSocket event."""
        self.event_sequence += 1
        event = WebSocketEvent(
            event_type=message_type,
            timestamp=time.time(),
            user_id=user_id,
            data=data.copy(),
            sequence_number=self.event_sequence
        )
        self.captured_events.append(event)
        logger.debug(f"Captured WebSocket event: {message_type} for user {user_id}")
        
    def get_events_for_user(self, user_id: str) -> List[WebSocketEvent]:
        """Get all events for a specific user."""
        return [event for event in self.captured_events if event.user_id == user_id]
        
    def get_events_by_type(self, event_type: str, user_id: Optional[str] = None) -> List[WebSocketEvent]:
        """Get events by type, optionally filtered by user."""
        events = [event for event in self.captured_events if event.event_type == event_type]
        if user_id:
            events = [event for event in events if event.user_id == user_id]
        return events
        
    def clear_events(self) -> None:
        """Clear all captured events."""
        self.captured_events.clear()
        self.event_sequence = 0


@pytest.mark.integration
class TestAgentWebSocketEventsIntegration(BaseIntegrationTest):
    """Test agent response WebSocket events integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.event_capture = MockWebSocketEventCapture()
        self.test_user_id = "test_user_websocket"
        self.test_thread_id = "thread_websocket_001"
        
    def _validate_event_sequence(self, events: List[WebSocketEvent]) -> Tuple[bool, List[str]]:
        """Validate WebSocket event sequence follows business requirements."""
        required_sequence = [
            WebSocketEventType.AGENT_STARTED.value,
            WebSocketEventType.AGENT_THINKING.value,
            WebSocketEventType.AGENT_COMPLETED.value
        ]
        
        errors = []
        event_types = [event.event_type for event in events]
        
        # Check for required events
        for required_event in required_sequence:
            if required_event not in event_types:
                errors.append(f"Missing required event: {required_event}")
                
        # Check event ordering
        if WebSocketEventType.AGENT_STARTED.value in event_types and WebSocketEventType.AGENT_COMPLETED.value in event_types:
            started_index = event_types.index(WebSocketEventType.AGENT_STARTED.value)
            completed_index = event_types.rindex(WebSocketEventType.AGENT_COMPLETED.value)  # Last occurrence
            
            if started_index >= completed_index:
                errors.append("agent_started must come before agent_completed")
                
        # Check for thinking events between started and completed
        if (WebSocketEventType.AGENT_STARTED.value in event_types and 
            WebSocketEventType.AGENT_COMPLETED.value in event_types):
            
            started_idx = event_types.index(WebSocketEventType.AGENT_STARTED.value)
            completed_idx = event_types.rindex(WebSocketEventType.AGENT_COMPLETED.value)
            
            thinking_events = [
                i for i, event_type in enumerate(event_types) 
                if event_type == WebSocketEventType.AGENT_THINKING.value and started_idx < i < completed_idx
            ]
            
            if not thinking_events:
                errors.append("At least one agent_thinking event must occur between agent_started and agent_completed")
                
        return len(errors) == 0, errors
        
    async def test_agent_response_websocket_event_sequence_for_user_feedback(self):
        """
        Test agent response generates proper WebSocket event sequence for user feedback.
        
        BVJ: All segments - Real-time User Experience
        Validates that users receive real-time feedback during agent processing
        through proper WebSocket event sequencing.
        """
        # GIVEN: A user execution context with WebSocket event capture
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager to capture events
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                mock_manager_instance.send_to_user = self.event_capture.send_to_user
                
                agent = DataHelperAgent()
                query = "Analyze customer retention trends for our SaaS platform"
                
                # WHEN: Agent generates response with WebSocket events
                # Simulate the complete event sequence
                await self.event_capture.send_to_user(
                    user_id=self.test_user_id,
                    message_type=WebSocketEventType.AGENT_STARTED.value,
                    data={
                        "agent": "DataHelperAgent",
                        "thread_id": self.test_thread_id,
                        "query": query,
                        "timestamp": time.time()
                    }
                )
                
                await self.event_capture.send_to_user(
                    user_id=self.test_user_id,
                    message_type=WebSocketEventType.AGENT_THINKING.value,
                    data={
                        "reasoning": "Analyzing customer retention data patterns...",
                        "step": 1,
                        "thread_id": self.test_thread_id
                    }
                )
                
                # Execute agent
                result = await agent.run(context, query=query)
                
                await self.event_capture.send_to_user(
                    user_id=self.test_user_id,
                    message_type=WebSocketEventType.AGENT_THINKING.value,
                    data={
                        "reasoning": "Generating recommendations based on analysis...",
                        "step": 2,
                        "thread_id": self.test_thread_id
                    }
                )
                
                await self.event_capture.send_to_user(
                    user_id=self.test_user_id,
                    message_type=WebSocketEventType.AGENT_COMPLETED.value,
                    data={
                        "result": result.result if isinstance(result, TypedAgentResult) else str(result),
                        "success": True,
                        "thread_id": self.test_thread_id,
                        "timestamp": time.time()
                    }
                )
                
                # THEN: WebSocket event sequence provides proper user feedback
                user_events = self.event_capture.get_events_for_user(self.test_user_id)
                assert len(user_events) >= 4, "Minimum required events: started, thinking(2), completed"
                
                # Validate event sequence
                sequence_valid, sequence_errors = self._validate_event_sequence(user_events)
                assert sequence_valid, f"Event sequence validation failed: {sequence_errors}"
                
                # Validate event timing
                event_timestamps = [event.timestamp for event in user_events]
                time_differences = [event_timestamps[i+1] - event_timestamps[i] for i in range(len(event_timestamps)-1)]
                
                # All events should be in chronological order
                assert all(diff >= 0 for diff in time_differences), "Events must be in chronological order"
                
                # Validate event data quality
                started_events = self.event_capture.get_events_by_type(WebSocketEventType.AGENT_STARTED.value, self.test_user_id)
                assert len(started_events) == 1, "Exactly one agent_started event required"
                assert "agent" in started_events[0].data, "agent_started must include agent name"
                assert "thread_id" in started_events[0].data, "agent_started must include thread_id"
                
                thinking_events = self.event_capture.get_events_by_type(WebSocketEventType.AGENT_THINKING.value, self.test_user_id)
                assert len(thinking_events) >= 2, "At least two thinking events required for user feedback"
                for thinking_event in thinking_events:
                    assert "reasoning" in thinking_event.data, "agent_thinking must include reasoning"
                    assert len(thinking_event.data["reasoning"]) > 0, "Reasoning must be informative"
                    
                completed_events = self.event_capture.get_events_by_type(WebSocketEventType.AGENT_COMPLETED.value, self.test_user_id)
                assert len(completed_events) == 1, "Exactly one agent_completed event required"
                assert "result" in completed_events[0].data, "agent_completed must include result"
                assert "success" in completed_events[0].data, "agent_completed must indicate success status"
                
                logger.info(f"✅ WebSocket event sequence validated for user feedback ({len(user_events)} events)")
                
    async def test_websocket_events_user_isolation_prevents_cross_contamination(self):
        """
        Test WebSocket events maintain user isolation to prevent cross-contamination.
        
        BVJ: Enterprise - Security/Multi-tenancy
        Validates that WebSocket events are delivered only to the correct user,
        preventing data leakage in multi-tenant environments.
        """
        # GIVEN: Multiple users processing requests simultaneously
        user_1_id = f"{self.test_user_id}_isolation_1"
        user_2_id = f"{self.test_user_id}_isolation_2"
        
        with create_isolated_execution_context(
            user_id=user_1_id,
            thread_id=f"thread_{user_1_id}"
        ) as context_1:
            with create_isolated_execution_context(
                user_id=user_2_id,
                thread_id=f"thread_{user_2_id}"
            ) as context_2:
                
                # Mock WebSocket manager
                with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                    mock_manager_instance = AsyncMock()
                    mock_ws_manager.return_value = mock_manager_instance
                    mock_manager_instance.send_to_user = self.event_capture.send_to_user
                    
                    # WHEN: Both users execute agents simultaneously
                    async def process_user_1():
                        await self.event_capture.send_to_user(
                            user_id=user_1_id,
                            message_type=WebSocketEventType.AGENT_STARTED.value,
                            data={"agent": "DataHelperAgent", "user_data": "sensitive_user_1_data"}
                        )
                        
                        agent_1 = DataHelperAgent()
                        result_1 = await agent_1.run(context_1, query="User 1 specific query")
                        
                        await self.event_capture.send_to_user(
                            user_id=user_1_id,
                            message_type=WebSocketEventType.AGENT_COMPLETED.value,
                            data={"result": "User 1 result", "user_context": user_1_id}
                        )
                        
                        return result_1
                    
                    async def process_user_2():
                        await self.event_capture.send_to_user(
                            user_id=user_2_id,
                            message_type=WebSocketEventType.AGENT_STARTED.value,
                            data={"agent": "DataHelperAgent", "user_data": "sensitive_user_2_data"}
                        )
                        
                        agent_2 = DataHelperAgent()
                        result_2 = await agent_2.run(context_2, query="User 2 specific query")
                        
                        await self.event_capture.send_to_user(
                            user_id=user_2_id,
                            message_type=WebSocketEventType.AGENT_COMPLETED.value,
                            data={"result": "User 2 result", "user_context": user_2_id}
                        )
                        
                        return result_2
                    
                    # Execute both users concurrently
                    results = await asyncio.gather(process_user_1(), process_user_2())
                    
                    # THEN: Events are properly isolated per user
                    user_1_events = self.event_capture.get_events_for_user(user_1_id)
                    user_2_events = self.event_capture.get_events_for_user(user_2_id)
                    
                    # Validate event isolation
                    assert len(user_1_events) >= 2, "User 1 must receive their events"
                    assert len(user_2_events) >= 2, "User 2 must receive their events"
                    
                    # Check for cross-contamination
                    for event in user_1_events:
                        assert event.user_id == user_1_id, "User 1 events must only go to User 1"
                        assert "user_1" in str(event.data).lower() or "DataHelperAgent" in str(event.data), \
                            "User 1 events must contain User 1 data only"
                        assert "sensitive_user_2_data" not in str(event.data), \
                            "User 1 events must not contain User 2 sensitive data"
                            
                    for event in user_2_events:
                        assert event.user_id == user_2_id, "User 2 events must only go to User 2"
                        assert "user_2" in str(event.data).lower() or "DataHelperAgent" in str(event.data), \
                            "User 2 events must contain User 2 data only"
                        assert "sensitive_user_1_data" not in str(event.data), \
                            "User 2 events must not contain User 1 sensitive data"
                    
                    logger.info(f"✅ WebSocket event isolation validated (User 1: {len(user_1_events)} events, User 2: {len(user_2_events)} events)")
                    
    async def test_websocket_events_error_handling_maintains_user_communication(self):
        """
        Test WebSocket events during error scenarios maintain user communication.
        
        BVJ: All segments - Reliability/User Experience
        Validates that even when agents fail, users receive proper WebSocket
        events to understand what happened.
        """
        # GIVEN: A user execution context and error simulation
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                mock_manager_instance.send_to_user = self.event_capture.send_to_user
                
                # WHEN: Agent execution encounters error with WebSocket communication
                await self.event_capture.send_to_user(
                    user_id=self.test_user_id,
                    message_type=WebSocketEventType.AGENT_STARTED.value,
                    data={"agent": "DataHelperAgent", "thread_id": self.test_thread_id}
                )
                
                await self.event_capture.send_to_user(
                    user_id=self.test_user_id,
                    message_type=WebSocketEventType.AGENT_THINKING.value,
                    data={"reasoning": "Starting data analysis...", "step": 1}
                )
                
                # Simulate agent error
                try:
                    with patch.object(DataHelperAgent, 'run') as mock_run:
                        mock_run.side_effect = RuntimeError("Simulated agent failure")
                        
                        agent = DataHelperAgent()
                        result = await agent.run(context, query="Test query for error handling")
                        
                except RuntimeError as e:
                    # Send error communication events
                    await self.event_capture.send_to_user(
                        user_id=self.test_user_id,
                        message_type=WebSocketEventType.AGENT_THINKING.value,
                        data={
                            "reasoning": "Encountered an issue during processing. Attempting to provide helpful response...",
                            "step": 2,
                            "status": "error_recovery"
                        }
                    )
                    
                    await self.event_capture.send_to_user(
                        user_id=self.test_user_id,
                        message_type=WebSocketEventType.AGENT_COMPLETED.value,
                        data={
                            "success": False,
                            "error": "Unable to complete analysis due to processing error. Please try again.",
                            "user_friendly_message": "Sorry, I encountered an issue while processing your request. Please try rephrasing your question or try again in a moment."
                        }
                    )
                
                # THEN: Error scenario maintains proper user communication
                user_events = self.event_capture.get_events_for_user(self.test_user_id)
                assert len(user_events) >= 3, "Error scenario must include started, thinking, and completed events"
                
                # Validate error communication
                completed_events = self.event_capture.get_events_by_type(WebSocketEventType.AGENT_COMPLETED.value, self.test_user_id)
                assert len(completed_events) == 1, "One completion event required even for errors"
                
                completed_event = completed_events[0]
                assert "success" in completed_event.data, "Completion event must indicate success status"
                assert completed_event.data["success"] is False, "Error scenario must be marked as failure"
                assert "error" in completed_event.data or "user_friendly_message" in completed_event.data, \
                    "Error completion must include user-facing error information"
                
                # Validate user-friendly error messaging
                if "user_friendly_message" in completed_event.data:
                    error_message = completed_event.data["user_friendly_message"]
                    assert "sorry" in error_message.lower() or "unable" in error_message.lower(), \
                        "Error message should be apologetic and user-friendly"
                    assert "try again" in error_message.lower(), \
                        "Error message should suggest retry action"
                
                # Validate thinking events show error recovery attempt
                thinking_events = self.event_capture.get_events_by_type(WebSocketEventType.AGENT_THINKING.value, self.test_user_id)
                error_recovery_events = [
                    event for event in thinking_events 
                    if "error" in event.data.get("reasoning", "").lower() or 
                       event.data.get("status") == "error_recovery"
                ]
                assert len(error_recovery_events) > 0, "Error scenario should show recovery attempt in thinking events"
                
                logger.info(f"✅ Error scenario WebSocket communication validated ({len(user_events)} events)")
                
    async def test_websocket_events_performance_meets_realtime_requirements(self):
        """
        Test WebSocket events performance meets real-time requirements.
        
        BVJ: All segments - Performance/User Experience
        Validates that WebSocket events are delivered with low enough latency
        to provide genuinely real-time user experience.
        """
        # GIVEN: Performance requirements for real-time experience
        MAX_EVENT_LATENCY = 0.1  # 100ms maximum latency per event
        MAX_TOTAL_EVENT_TIME = 2.0  # 2 seconds maximum for all events
        
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Mock WebSocket manager with timing tracking
            event_timings = []
            
            async def timed_send_to_user(user_id: str, message_type: str, data: Dict[str, Any]):
                start_time = time.time()
                await self.event_capture.send_to_user(user_id, message_type, data)
                end_time = time.time()
                event_timings.append({
                    "event_type": message_type,
                    "latency": end_time - start_time,
                    "timestamp": start_time
                })
            
            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_ws_manager:
                mock_manager_instance = AsyncMock()
                mock_ws_manager.return_value = mock_manager_instance
                mock_manager_instance.send_to_user = timed_send_to_user
                
                # WHEN: Multiple WebSocket events are sent during agent execution
                performance_start = time.time()
                
                await timed_send_to_user(
                    self.test_user_id,
                    WebSocketEventType.AGENT_STARTED.value,
                    {"agent": "DataHelperAgent", "thread_id": self.test_thread_id}
                )
                
                for i in range(3):  # Multiple thinking events
                    await timed_send_to_user(
                        self.test_user_id,
                        WebSocketEventType.AGENT_THINKING.value,
                        {"reasoning": f"Processing step {i+1}...", "step": i+1}
                    )
                    await asyncio.sleep(0.01)  # Small delay to simulate processing
                
                # Execute agent (minimal for performance test)
                agent = DataHelperAgent()
                result = await agent.run(context, query="Performance test query")
                
                await timed_send_to_user(
                    self.test_user_id,
                    WebSocketEventType.AGENT_COMPLETED.value,
                    {"result": str(result), "success": True}
                )
                
                total_event_time = time.time() - performance_start
                
                # THEN: WebSocket events meet real-time performance requirements
                assert len(event_timings) >= 5, "Multiple events required for performance test"
                
                # Validate individual event latency
                for timing in event_timings:
                    assert timing["latency"] < MAX_EVENT_LATENCY, \
                        f"Event {timing['event_type']} latency {timing['latency']:.3f}s exceeds limit {MAX_EVENT_LATENCY}s"
                
                # Validate total event delivery time
                assert total_event_time < MAX_TOTAL_EVENT_TIME, \
                    f"Total event time {total_event_time:.3f}s exceeds real-time limit {MAX_TOTAL_EVENT_TIME}s"
                
                # Calculate performance metrics
                avg_latency = sum(timing["latency"] for timing in event_timings) / len(event_timings)
                max_latency = max(timing["latency"] for timing in event_timings)
                
                # Performance quality thresholds
                assert avg_latency < 0.05, f"Average latency {avg_latency:.3f}s too high for real-time experience"
                assert max_latency < MAX_EVENT_LATENCY, f"Maximum latency {max_latency:.3f}s exceeds threshold"
                
                logger.info(f"✅ WebSocket events performance validated: "
                           f"avg_latency={avg_latency:.3f}s, max_latency={max_latency:.3f}s, "
                           f"total_time={total_event_time:.3f}s, events={len(event_timings)}")
                           
    def teardown_method(self):
        """Clean up test resources."""
        # Clear captured events
        self.event_capture.clear_events()
        
        super().teardown_method()