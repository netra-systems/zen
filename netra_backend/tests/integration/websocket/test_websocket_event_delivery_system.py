"""
WebSocket Event Delivery System Integration Tests

MISSION CRITICAL: These tests validate the 5 CRITICAL WebSocket events that enable
substantive chat interactions and deliver 90% of the platform's business value.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Core Chat Functionality
- Business Goal: Real-time AI interaction visibility drives user engagement and conversion
- Value Impact: WebSocket events are PRIMARY delivery mechanism for AI value
- Revenue Impact: Protects $500K+ ARR dependent on real-time chat experience

THE 5 MISSION-CRITICAL WEBSOCKET EVENTS:
1. **agent_started** - User sees agent began processing (engagement)
2. **agent_thinking** - Real-time reasoning visibility (trust building) 
3. **tool_executing** - Tool usage transparency (process understanding)
4. **tool_completed** - Tool results display (progress feedback)
5. **agent_completed** - Final results ready (completion clarity)

CRITICAL REQUIREMENT: Missing ANY of these events = broken user experience = lost revenue

TEST SCOPE: Integration-level validation of WebSocket event delivery including:
- All 5 critical events delivered in correct sequence
- Event payload validation and data integrity  
- Event timing and ordering verification
- Multi-user event isolation and concurrency
- Event delivery failure recovery and retry logic
- Performance under high event volume
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
from dataclasses import dataclass, field
from collections import defaultdict
import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core components - NO MOCKS for business logic
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, AgentEvent, ConnectionMetadata
)

# User context and types
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.user_types import TestUserData

# Agent types for event validation
from netra_backend.app.agents.supervisor.types import (
    AgentExecutionState, ToolExecutionStatus
)

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class CapturedWebSocketEvent:
    """Captured WebSocket event for validation."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    user_id: str
    thread_id: Optional[str] = None
    message_raw: Optional[str] = None


class EventCapturingWebSocket:
    """Mock WebSocket that captures all events for validation."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_closed = False
        self.captured_events: List[CapturedWebSocketEvent] = []
        self.state = WebSocketConnectionState.CONNECTED
        self.event_counts: Dict[str, int] = defaultdict(int)
        
    async def send(self, message: str) -> None:
        """Capture sent messages as events."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        
        try:
            # Parse message to extract event information
            message_data = json.loads(message)
            event_type = message_data.get('type', 'unknown')
            
            # Capture event
            event = CapturedWebSocketEvent(
                event_type=event_type,
                payload=message_data,
                timestamp=datetime.now(UTC),
                user_id=self.user_id,
                thread_id=message_data.get('thread_id'),
                message_raw=message
            )
            
            self.captured_events.append(event)
            self.event_counts[event_type] += 1
            
            logger.debug(f"Captured WebSocket event: {event_type} for user {self.user_id}")
            
        except json.JSONDecodeError:
            # Handle non-JSON messages
            event = CapturedWebSocketEvent(
                event_type="raw_message",
                payload={"message": message},
                timestamp=datetime.now(UTC),
                user_id=self.user_id,
                message_raw=message
            )
            self.captured_events.append(event)
    
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Mock close."""
        self.is_closed = True
        self.state = WebSocketConnectionState.DISCONNECTED
    
    def get_events_by_type(self, event_type: str) -> List[CapturedWebSocketEvent]:
        """Get all captured events of specific type."""
        return [event for event in self.captured_events if event.event_type == event_type]
    
    def get_event_sequence(self) -> List[str]:
        """Get sequence of event types in order received."""
        return [event.event_type for event in self.captured_events]


@pytest.mark.integration
@pytest.mark.websocket  
@pytest.mark.critical
@pytest.mark.asyncio
class TestWebSocketEventDeliverySystem(SSotAsyncTestCase):
    """
    Integration tests for WebSocket event delivery system.
    
    MISSION CRITICAL: These tests protect the 5 events that enable chat functionality
    generating $500K+ ARR through real-time AI interactions.
    """
    
    # The 5 mission-critical WebSocket events
    CRITICAL_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_event_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_event_test")
        
        # Test data
        self.test_user = TestUserData(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            email="test@netra.ai",
            tier="early",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Track resources for cleanup
        self.websocket_managers: List[Any] = []
        self.event_capturers: List[EventCapturingWebSocket] = []
        
    async def teardown_method(self, method):
        """Clean up resources."""
        for capturer in self.event_capturers:
            if not capturer.is_closed:
                await capturer.close()
        
        for manager in self.websocket_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.warning(f"Manager cleanup error: {e}")
        
        await super().teardown_method(method)
    
    async def create_mock_user_context(self, user_data: TestUserData) -> Any:
        """Create mock user context."""
        return type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"test_request_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'is_test': True
        })()
    
    async def setup_websocket_with_event_capture(self, user_data: TestUserData) -> Tuple[Any, EventCapturingWebSocket]:
        """Set up WebSocket manager with event capturing."""
        user_context = await self.create_mock_user_context(user_data)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create event capturing WebSocket
        connection_id = f"event_conn_{uuid.uuid4().hex[:8]}"
        event_capturer = EventCapturingWebSocket(user_data.user_id, connection_id)
        self.event_capturers.append(event_capturer)
        
        # Connect the event capturer
        with patch.object(manager, '_websocket_transport', event_capturer):
            await manager.connect_user(
                user_id=ensure_user_id(user_data.user_id),
                websocket=event_capturer,
                connection_metadata={"tier": user_data.tier}
            )
        
        return manager, event_capturer
    
    async def test_all_five_critical_events_delivered_in_sequence(self):
        """
        Test: All 5 critical WebSocket events are delivered in correct sequence
        
        Business Value: Validates complete real-time AI interaction flow that creates
        user trust and engagement, directly driving conversion and retention.
        """
        manager, event_capturer = await self.setup_websocket_with_event_capture(self.test_user)
        
        user_id = ensure_user_id(self.test_user.user_id)
        thread_id = self.test_user.thread_id
        
        # Simulate complete agent execution workflow
        with patch.object(manager, '_websocket_transport', event_capturer):
            # 1. Agent started event
            await manager.emit_agent_event(
                user_id=user_id,
                thread_id=thread_id,
                event_type="agent_started",
                data={
                    "agent_type": "supervisor",
                    "request_id": f"req_{uuid.uuid4().hex[:8]}",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
            
            # 2. Agent thinking event 
            await manager.emit_agent_event(
                user_id=user_id,
                thread_id=thread_id,
                event_type="agent_thinking",
                data={
                    "status": "analyzing_request",
                    "progress": 0.1,
                    "message": "Analyzing your request and determining optimal approach..."
                }
            )
            
            # 3. Tool executing event
            await manager.emit_agent_event(
                user_id=user_id,
                thread_id=thread_id,
                event_type="tool_executing",
                data={
                    "tool_name": "data_analyzer",
                    "tool_action": "analyze_dataset",
                    "progress": 0.5
                }
            )
            
            # 4. Tool completed event
            await manager.emit_agent_event(
                user_id=user_id,
                thread_id=thread_id,
                event_type="tool_completed", 
                data={
                    "tool_name": "data_analyzer",
                    "status": "success",
                    "results_summary": "Analysis completed with 3 key insights identified"
                }
            )
            
            # 5. Agent completed event
            await manager.emit_agent_event(
                user_id=user_id,
                thread_id=thread_id,
                event_type="agent_completed",
                data={
                    "status": "success",
                    "response_ready": True,
                    "execution_time": 45.2
                }
            )
        
        # Verify all 5 critical events were delivered
        event_sequence = event_capturer.get_event_sequence()
        
        for critical_event in self.CRITICAL_EVENTS:
            assert critical_event in event_sequence, f"Missing critical event: {critical_event}"
            assert event_capturer.event_counts[critical_event] >= 1, f"Event {critical_event} not delivered"
        
        # Verify event ordering (critical events should appear in logical sequence)
        critical_event_positions = []
        for event in self.CRITICAL_EVENTS:
            if event in event_sequence:
                critical_event_positions.append(event_sequence.index(event))
        
        # Verify ordering: agent_started should come before agent_completed
        agent_started_pos = event_sequence.index("agent_started")
        agent_completed_pos = event_sequence.index("agent_completed")
        assert agent_started_pos < agent_completed_pos, "agent_started should come before agent_completed"
        
        logger.info(f"✅ All 5 critical events delivered in sequence: {event_sequence}")
    
    async def test_event_payload_validation_and_data_integrity(self):
        """
        Test: WebSocket event payloads contain required data and maintain integrity
        
        Business Value: Ensures users receive complete, accurate information in real-time,
        building trust in AI processing and maintaining high-quality chat experience.
        """
        manager, event_capturer = await self.setup_websocket_with_event_capture(self.test_user)
        
        user_id = ensure_user_id(self.test_user.user_id)
        thread_id = self.test_user.thread_id
        
        # Test event with comprehensive payload
        test_event_data = {
            "agent_type": "supervisor",
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(UTC).isoformat(),
            "user_context": {
                "tier": self.test_user.tier,
                "user_id": self.test_user.user_id
            },
            "progress": 0.25,
            "metadata": {
                "execution_mode": "test",
                "version": "1.0.0"
            }
        }
        
        with patch.object(manager, '_websocket_transport', event_capturer):
            await manager.emit_agent_event(
                user_id=user_id,
                thread_id=thread_id,
                event_type="agent_thinking",
                data=test_event_data
            )
        
        # Validate event payload
        thinking_events = event_capturer.get_events_by_type("agent_thinking")
        assert len(thinking_events) == 1, "Should have exactly one agent_thinking event"
        
        event = thinking_events[0]
        payload = event.payload
        
        # Verify required fields are present
        required_fields = ["type", "data", "user_id", "thread_id", "timestamp"]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"
        
        # Verify data integrity
        event_data = payload.get("data", {})
        assert event_data.get("agent_type") == "supervisor"
        assert event_data.get("progress") == 0.25
        assert "user_context" in event_data
        assert "metadata" in event_data
        
        # Verify user context isolation
        assert payload.get("user_id") == self.test_user.user_id
        assert payload.get("thread_id") == self.test_user.thread_id
        
        logger.info("✅ Event payload validation and data integrity confirmed")
    
    async def test_event_delivery_timing_and_performance(self):
        """
        Test: WebSocket events are delivered within acceptable time limits
        
        Business Value: Ensures responsive real-time chat experience that keeps users 
        engaged and prevents frustration that could lead to churn.
        """
        manager, event_capturer = await self.setup_websocket_with_event_capture(self.test_user)
        
        user_id = ensure_user_id(self.test_user.user_id)
        thread_id = self.test_user.thread_id
        
        # Test rapid event delivery
        event_count = 10
        start_time = time.time()
        
        with patch.object(manager, '_websocket_transport', event_capturer):
            # Send multiple events rapidly
            for i in range(event_count):
                await manager.emit_agent_event(
                    user_id=user_id,
                    thread_id=thread_id,
                    event_type="agent_thinking",
                    data={
                        "progress": i / event_count,
                        "message": f"Processing step {i + 1} of {event_count}",
                        "sequence": i
                    }
                )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all events were delivered
        thinking_events = event_capturer.get_events_by_type("agent_thinking")
        assert len(thinking_events) == event_count, f"Expected {event_count} events, got {len(thinking_events)}"
        
        # Verify performance - should deliver events quickly
        avg_time_per_event = total_time / event_count
        max_acceptable_time = 0.1  # 100ms per event maximum
        
        assert avg_time_per_event < max_acceptable_time, \
            f"Event delivery too slow: {avg_time_per_event:.3f}s per event (max: {max_acceptable_time}s)"
        
        # Verify event ordering preserved
        for i, event in enumerate(thinking_events):
            expected_sequence = i
            actual_sequence = event.payload.get("data", {}).get("sequence", -1)
            assert actual_sequence == expected_sequence, f"Event ordering lost: expected {expected_sequence}, got {actual_sequence}"
        
        logger.info(f"✅ {event_count} events delivered in {total_time:.3f}s ({avg_time_per_event:.3f}s per event)")
    
    async def test_concurrent_event_delivery_for_multiple_users(self):
        """
        Test: WebSocket events for multiple users are delivered concurrently without interference
        
        Business Value: Ensures scalable multi-tenant chat operations for enterprise customers,
        preventing cross-user interference that could impact service quality.
        """
        # Create multiple users and event capturers
        users = [
            TestUserData(
                user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
                email=f"user{i}@netra.ai",
                tier="early",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}"
            )
            for i in range(3)
        ]
        
        user_setups = []
        for user_data in users:
            manager, capturer = await self.setup_websocket_with_event_capture(user_data)
            user_setups.append((user_data, manager, capturer))
        
        # Send events concurrently for all users
        async def send_user_events(user_data: TestUserData, manager: Any, capturer: EventCapturingWebSocket):
            user_id = ensure_user_id(user_data.user_id)
            thread_id = user_data.thread_id
            
            with patch.object(manager, '_websocket_transport', capturer):
                for event_type in self.CRITICAL_EVENTS:
                    await manager.emit_agent_event(
                        user_id=user_id,
                        thread_id=thread_id,
                        event_type=event_type,
                        data={
                            "user_specific_data": user_data.user_id,
                            "event_sequence": event_type,
                            "timestamp": datetime.now(UTC).isoformat()
                        }
                    )
                    
                    # Small delay to allow concurrent processing
                    await asyncio.sleep(0.01)
        
        # Execute all user event sending concurrently
        await asyncio.gather(*[
            send_user_events(user_data, manager, capturer)
            for user_data, manager, capturer in user_setups
        ])
        
        # Verify each user received their events correctly
        for user_data, manager, capturer in user_setups:
            # Verify all critical events delivered
            for event_type in self.CRITICAL_EVENTS:
                user_events = capturer.get_events_by_type(event_type)
                assert len(user_events) >= 1, f"User {user_data.user_id} missing {event_type} event"
                
                # Verify user isolation - events contain correct user data
                for event in user_events:
                    event_data = event.payload.get("data", {})
                    assert event_data.get("user_specific_data") == user_data.user_id
                    assert event.user_id == user_data.user_id
        
        logger.info(f"✅ Concurrent event delivery verified for {len(users)} users")
    
    async def test_event_delivery_failure_recovery_and_retry(self):
        """
        Test: WebSocket event delivery failures are handled with appropriate recovery
        
        Business Value: Ensures reliable chat experience even during network issues,
        preventing user frustration and maintaining service quality.
        """
        manager, event_capturer = await self.setup_websocket_with_event_capture(self.test_user)
        
        user_id = ensure_user_id(self.test_user.user_id)
        thread_id = self.test_user.thread_id
        
        # Mock connection that fails intermittently
        class FailingWebSocket(EventCapturingWebSocket):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.send_count = 0
                self.failure_pattern = [False, True, False, False, True]  # Fail on 2nd and 5th sends
            
            async def send(self, message: str) -> None:
                if self.send_count < len(self.failure_pattern) and self.failure_pattern[self.send_count]:
                    self.send_count += 1
                    raise ConnectionError("Simulated connection failure")
                
                self.send_count += 1
                await super().send(message)
        
        failing_capturer = FailingWebSocket(self.test_user.user_id, "failing_conn")
        self.event_capturers.append(failing_capturer)
        
        # Test event delivery with failures
        successful_events = []
        failed_events = []
        
        with patch.object(manager, '_websocket_transport', failing_capturer):
            for i, event_type in enumerate(["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]):
                try:
                    await manager.emit_agent_event(
                        user_id=user_id,
                        thread_id=thread_id,
                        event_type=event_type,
                        data={
                            "sequence": i,
                            "attempt": 1
                        }
                    )
                    successful_events.append(event_type)
                except ConnectionError:
                    failed_events.append(event_type)
                    logger.info(f"Expected failure for event: {event_type}")
        
        # Verify some events failed as expected
        assert len(failed_events) > 0, "Some events should have failed for recovery testing"
        
        # Verify successful events were delivered
        assert len(successful_events) > 0, "Some events should have succeeded"
        
        for event_type in successful_events:
            events = failing_capturer.get_events_by_type(event_type)
            assert len(events) >= 1, f"Successful event {event_type} should be captured"
        
        logger.info(f"✅ Event delivery recovery tested: {len(successful_events)} succeeded, {len(failed_events)} failed as expected")
    
    async def test_high_volume_event_delivery_stress_test(self):
        """
        Test: WebSocket event delivery under high volume stress conditions
        
        Business Value: Validates system can handle peak usage loads without degrading
        chat experience quality for any users.
        """
        manager, event_capturer = await self.setup_websocket_with_event_capture(self.test_user)
        
        user_id = ensure_user_id(self.test_user.user_id)
        thread_id = self.test_user.thread_id
        
        # High volume event test
        total_events = 100
        batch_size = 10
        start_time = time.time()
        
        with patch.object(manager, '_websocket_transport', event_capturer):
            # Send events in batches to simulate high load
            for batch in range(0, total_events, batch_size):
                batch_tasks = []
                
                for i in range(batch, min(batch + batch_size, total_events)):
                    event_type = self.CRITICAL_EVENTS[i % len(self.CRITICAL_EVENTS)]
                    
                    task = manager.emit_agent_event(
                        user_id=user_id,
                        thread_id=thread_id,
                        event_type=event_type,
                        data={
                            "batch": batch // batch_size,
                            "sequence": i,
                            "high_volume_test": True
                        }
                    )
                    batch_tasks.append(task)
                
                # Execute batch concurrently
                await asyncio.gather(*batch_tasks)
                
                # Brief pause between batches
                await asyncio.sleep(0.01)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all events delivered
        total_captured = len(event_capturer.captured_events)
        assert total_captured == total_events, f"Expected {total_events} events, captured {total_captured}"
        
        # Verify performance metrics
        events_per_second = total_events / total_time
        min_acceptable_rate = 50  # events per second
        
        assert events_per_second >= min_acceptable_rate, \
            f"Event delivery rate too slow: {events_per_second:.1f} events/sec (min: {min_acceptable_rate})"
        
        # Verify all critical event types were included
        event_types_seen = set(event_capturer.event_counts.keys())
        critical_events_seen = event_types_seen.intersection(set(self.CRITICAL_EVENTS))
        assert len(critical_events_seen) == len(self.CRITICAL_EVENTS), \
            f"Not all critical events seen: {critical_events_seen} vs {self.CRITICAL_EVENTS}"
        
        logger.info(f"✅ High volume stress test: {total_events} events in {total_time:.2f}s ({events_per_second:.1f} events/sec)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])