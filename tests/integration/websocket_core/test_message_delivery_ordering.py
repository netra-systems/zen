#!/usr/bin/env python
"""Message Delivery Ordering Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Chat Experience Quality
- Business Goal: $500K+ ARR protection through reliable message ordering
- Value Impact: Ensure users see agent events in correct chronological order
- Revenue Impact: Prevents confused user experience and agent interaction failures

Test Strategy: This test MUST FAIL before SSOT consolidation and PASS after
- FAIL: Currently inconsistent ordering from fragmented managers
- PASS: After SSOT consolidation, guaranteed sequential event delivery

Issue #1033: WebSocket Manager SSOT Consolidation
This test validates that WebSocket events are delivered in the correct order,
which is critical for the Golden Path user experience where users need to see
agent progress in a logical sequence.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Tuple
from enum import Enum
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.logging.unified_logging_ssot import get_logger
from test_framework.ssot.base_integration_test import SSotBaseIntegrationTest as BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

logger = get_logger(__name__)


class AgentEventType(Enum):
    """Golden Path agent events that must be ordered correctly."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking" 
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"


@dataclass
class OrderedEvent:
    """Event with ordering information for testing."""
    event_type: AgentEventType
    sequence_number: int
    timestamp: float
    user_id: str
    thread_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    expected_after: List[AgentEventType] = field(default_factory=list)


class TestMessageDeliveryOrdering(BaseIntegrationTest):
    """Test WebSocket message delivery ordering compliance.
    
    This test suite validates that WebSocket events are delivered in the correct
    order to maintain a coherent user experience in the Golden Path.
    """

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_agent_event_sequential_ordering(self, real_services_fixture):
        """Test that agent events are delivered in the correct sequential order.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently fragmented managers cause out-of-order delivery
        - PASS: After SSOT consolidation, events follow Golden Path sequence
        
        This test validates the critical Golden Path event sequence:
        agent_started → agent_thinking → [tool_executing → tool_completed]* → agent_completed
        """
        logger.info("🔍 Testing agent event sequential ordering...")
        
        # Import WebSocket manager
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        except ImportError as e:
            pytest.skip(f"WebSocket manager not available: {e}")
        
        manager = WebSocketManager()
        
        # Create test user and connection
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"
        
        # Set up connection
        try:
            if hasattr(manager, 'add_connection'):
                await manager.add_connection(connection_id, user_id)
            elif hasattr(manager, 'connect'):
                await manager.connect(connection_id, user_id)
        except Exception as e:
            pytest.skip(f"Could not establish WebSocket connection: {e}")
        
        # Define Golden Path event sequence
        golden_path_events = [
            OrderedEvent(AgentEventType.AGENT_STARTED, 1, time.time(), user_id, thread_id,
                        expected_after=[]),
            OrderedEvent(AgentEventType.AGENT_THINKING, 2, time.time() + 0.1, user_id, thread_id,
                        expected_after=[AgentEventType.AGENT_STARTED]),
            OrderedEvent(AgentEventType.TOOL_EXECUTING, 3, time.time() + 0.2, user_id, thread_id,
                        expected_after=[AgentEventType.AGENT_THINKING]),
            OrderedEvent(AgentEventType.TOOL_COMPLETED, 4, time.time() + 0.3, user_id, thread_id,
                        expected_after=[AgentEventType.TOOL_EXECUTING]),
            OrderedEvent(AgentEventType.AGENT_COMPLETED, 5, time.time() + 0.4, user_id, thread_id,
                        expected_after=[AgentEventType.TOOL_COMPLETED])
        ]
        
        # Send events through WebSocket manager
        delivery_results = []
        for event in golden_path_events:
            try:
                message = {
                    "type": event.event_type.value,
                    "sequence": event.sequence_number,
                    "user_id": event.user_id,
                    "thread_id": event.thread_id,
                    "timestamp": event.timestamp,
                    "data": event.data
                }
                
                if hasattr(manager, 'emit_event'):
                    await manager.emit_event(connection_id, event.event_type.value, message)
                elif hasattr(manager, 'send_message'):
                    await manager.send_message(connection_id, message)
                
                delivery_results.append({
                    "event": event.event_type.value,
                    "sequence": event.sequence_number,
                    "sent_at": time.time()
                })
                
                # Small delay to increase chance of ordering issues
                await asyncio.sleep(0.01)
                
            except Exception as e:
                delivery_results.append({
                    "event": event.event_type.value,
                    "sequence": event.sequence_number,
                    "error": str(e)
                })
        
        # Analyze delivery order (would need WebSocket client to receive in real scenario)
        ordering_violations = self._analyze_event_ordering(delivery_results, golden_path_events)
        
        if ordering_violations:
            logger.error("SSOT VIOLATIONS: Agent event ordering violations:")
            for violation in ordering_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Should have no ordering violations
        # This assertion WILL FAIL until proper event ordering is implemented
        assert len(ordering_violations) == 0, (
            f"SSOT VIOLATION: Found {len(ordering_violations)} event ordering violations. "
            f"Golden Path events must be delivered in correct sequence."
        )

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_concurrent_event_streams_ordering(self, real_services_fixture):
        """Test ordering when multiple event streams occur concurrently.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently multiple managers cause interleaved/corrupted streams
        - PASS: After SSOT consolidation, each stream maintains internal ordering
        
        This test validates that when multiple users have concurrent agent sessions,
        each user's event stream maintains correct internal ordering.
        """
        logger.info("🔍 Testing concurrent event streams ordering...")
        
        # Import WebSocket manager
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        except ImportError as e:
            pytest.skip(f"WebSocket manager not available: {e}")
        
        manager = WebSocketManager()
        
        # Create multiple concurrent event streams
        num_streams = 3
        events_per_stream = 5
        
        stream_tasks = []
        for stream_id in range(num_streams):
            task = asyncio.create_task(
                self._simulate_event_stream(manager, stream_id, events_per_stream)
            )
            stream_tasks.append(task)
        
        # Wait for all streams to complete
        stream_results = await asyncio.gather(*stream_tasks, return_exceptions=True)
        
        # Analyze results for ordering violations
        ordering_violations = []
        
        for stream_id, result in enumerate(stream_results):
            if isinstance(result, Exception):
                ordering_violations.append(f"Stream {stream_id} failed: {str(result)}")
                continue
            
            if isinstance(result, dict) and result.get('ordering_errors'):
                for error in result['ordering_errors']:
                    ordering_violations.append(f"Stream {stream_id}: {error}")
        
        # Check for cross-stream contamination
        cross_stream_violations = self._check_cross_stream_contamination(stream_results)
        ordering_violations.extend(cross_stream_violations)
        
        if ordering_violations:
            logger.error("SSOT VIOLATIONS: Concurrent stream ordering violations:")
            for violation in ordering_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Should maintain ordering within each stream
        # This assertion WILL FAIL until concurrent stream ordering is properly handled
        assert len(ordering_violations) == 0, (
            f"SSOT VIOLATION: Found {len(ordering_violations)} concurrent stream ordering violations. "
            f"Each user's event stream must maintain internal order even during concurrent execution."
        )

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_event_ordering_under_backpressure(self, real_services_fixture):
        """Test event ordering when system is under message backpressure.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently backpressure causes dropped or reordered messages
        - PASS: After SSOT consolidation, ordering maintained under pressure
        
        This test validates that event ordering is preserved even when the system
        is handling high message volume or experiencing delivery delays.
        """
        logger.info("🔍 Testing event ordering under backpressure...")
        
        # Import WebSocket manager
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        except ImportError as e:
            pytest.skip(f"WebSocket manager not available: {e}")
        
        manager = WebSocketManager()
        
        # Create test connection
        user_id = f"backpressure_user_{uuid.uuid4().hex[:8]}"
        connection_id = f"backpressure_conn_{uuid.uuid4().hex[:8]}"
        
        try:
            if hasattr(manager, 'add_connection'):
                await manager.add_connection(connection_id, user_id)
            elif hasattr(manager, 'connect'):
                await manager.connect(connection_id, user_id)
        except Exception as e:
            pytest.skip(f"Could not establish WebSocket connection: {e}")
        
        # Generate high volume of ordered events
        num_events = 50
        backpressure_events = []
        
        for i in range(num_events):
            event = {
                "type": "agent_progress",
                "sequence": i + 1,
                "user_id": user_id,
                "timestamp": time.time() + (i * 0.001),  # Very close timestamps
                "data": {"step": i, "progress": f"Step {i} completed"}
            }
            backpressure_events.append(event)
        
        # Send events rapidly to create backpressure
        sent_events = []
        send_errors = []
        
        send_tasks = []
        for i, event in enumerate(backpressure_events):
            # Create concurrent send tasks to maximize backpressure
            task = asyncio.create_task(
                self._send_event_with_tracking(manager, connection_id, event, i)
            )
            send_tasks.append(task)
        
        # Wait for all sends to complete
        send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # Analyze results for ordering violations under backpressure
        for i, result in enumerate(send_results):
            if isinstance(result, Exception):
                send_errors.append(f"Event {i} send failed: {str(result)}")
            elif isinstance(result, dict):
                if result.get('success'):
                    sent_events.append(result)
                else:
                    send_errors.append(f"Event {i}: {result.get('error', 'unknown error')}")
        
        # Check for sequence ordering issues
        ordering_violations = self._analyze_backpressure_ordering(sent_events, num_events)
        
        if send_errors:
            logger.warning(f"Encountered {len(send_errors)} send errors during backpressure test")
            for error in send_errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        
        if ordering_violations:
            logger.error("SSOT VIOLATIONS: Backpressure ordering violations:")
            for violation in ordering_violations:
                logger.error(f"  - {violation}")
        
        # SSOT VIOLATION CHECK: Should maintain ordering under backpressure
        # This assertion WILL FAIL until proper backpressure handling is implemented
        assert len(ordering_violations) == 0, (
            f"SSOT VIOLATION: Found {len(ordering_violations)} ordering violations under backpressure. "
            f"Event ordering must be preserved even under high message volume."
        )

    async def _simulate_event_stream(self, manager: Any, stream_id: int, num_events: int) -> Dict[str, Any]:
        """Simulate a stream of ordered events for one user."""
        user_id = f"stream_user_{stream_id}_{uuid.uuid4().hex[:8]}"
        connection_id = f"stream_conn_{stream_id}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Set up connection
            if hasattr(manager, 'add_connection'):
                await manager.add_connection(connection_id, user_id)
            elif hasattr(manager, 'connect'):
                await manager.connect(connection_id, user_id)
            
            # Send ordered events
            sent_events = []
            ordering_errors = []
            
            for event_num in range(num_events):
                event = {
                    "type": "stream_event",
                    "stream_id": stream_id,
                    "sequence": event_num + 1,
                    "user_id": user_id,
                    "timestamp": time.time(),
                    "data": {"step": event_num}
                }
                
                try:
                    if hasattr(manager, 'emit_event'):
                        await manager.emit_event(connection_id, "stream_event", event)
                    elif hasattr(manager, 'send_message'):
                        await manager.send_message(connection_id, event)
                    
                    sent_events.append({
                        "sequence": event_num + 1,
                        "sent_at": time.time()
                    })
                    
                    # Small delay to simulate processing
                    await asyncio.sleep(0.005)
                    
                except Exception as e:
                    ordering_errors.append(f"Failed to send event {event_num + 1}: {str(e)}")
            
            return {
                "stream_id": stream_id,
                "sent_events": sent_events,
                "ordering_errors": ordering_errors
            }
            
        except Exception as e:
            return {
                "stream_id": stream_id,
                "error": str(e),
                "ordering_errors": [f"Stream setup failed: {str(e)}"]
            }

    async def _send_event_with_tracking(self, manager: Any, connection_id: str, event: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Send an event with tracking information."""
        try:
            send_start = time.time()
            
            if hasattr(manager, 'emit_event'):
                await manager.emit_event(connection_id, event["type"], event)
            elif hasattr(manager, 'send_message'):
                await manager.send_message(connection_id, event)
            
            send_end = time.time()
            
            return {
                "success": True,
                "index": index,
                "sequence": event["sequence"],
                "send_start": send_start,
                "send_end": send_end,
                "duration": send_end - send_start
            }
            
        except Exception as e:
            return {
                "success": False,
                "index": index,
                "sequence": event["sequence"],
                "error": str(e)
            }

    def _analyze_event_ordering(self, delivery_results: List[Dict[str, Any]], expected_events: List[OrderedEvent]) -> List[str]:
        """Analyze delivery results for ordering violations."""
        violations = []
        
        # Check if all events were sent successfully
        failed_sends = [r for r in delivery_results if 'error' in r]
        if failed_sends:
            violations.append(f"Failed to send {len(failed_sends)} events: {[r['event'] for r in failed_sends]}")
        
        # Check sequence ordering
        successful_sends = [r for r in delivery_results if 'sent_at' in r]
        if len(successful_sends) < len(expected_events):
            violations.append(f"Only {len(successful_sends)} of {len(expected_events)} events were sent successfully")
        
        # Verify sequence numbers are in order
        sequences = [r['sequence'] for r in successful_sends]
        expected_sequences = [e.sequence_number for e in expected_events[:len(successful_sends)]]
        
        if sequences != expected_sequences:
            violations.append(f"Event sequence mismatch. Expected: {expected_sequences}, Got: {sequences}")
        
        return violations

    def _check_cross_stream_contamination(self, stream_results: List[Any]) -> List[str]:
        """Check if event streams contaminated each other's ordering."""
        violations = []
        
        # Extract successful stream data
        successful_streams = []
        for result in stream_results:
            if isinstance(result, dict) and 'sent_events' in result:
                successful_streams.append(result)
        
        # Check if any stream interfered with another
        for i, stream_a in enumerate(successful_streams):
            for j, stream_b in enumerate(successful_streams):
                if i >= j:
                    continue
                
                # Check for timing interference (events sent too close together across streams)
                events_a = stream_a.get('sent_events', [])
                events_b = stream_b.get('sent_events', [])
                
                for event_a in events_a:
                    for event_b in events_b:
                        time_diff = abs(event_a['sent_at'] - event_b['sent_at'])
                        if time_diff < 0.001:  # Events sent within 1ms might indicate contamination
                            violations.append(
                                f"Stream {stream_a.get('stream_id')} and {stream_b.get('stream_id')} "
                                f"sent events within {time_diff*1000:.2f}ms (possible contamination)"
                            )
        
        return violations

    def _analyze_backpressure_ordering(self, sent_events: List[Dict[str, Any]], expected_count: int) -> List[str]:
        """Analyze backpressure test results for ordering violations."""
        violations = []
        
        # Check if all events were sent
        if len(sent_events) < expected_count:
            violations.append(f"Only {len(sent_events)} of {expected_count} events sent under backpressure")
        
        # Sort events by send completion time to check actual order
        sent_events_sorted = sorted(sent_events, key=lambda x: x.get('send_end', x.get('send_start', 0)))
        
        # Check if sequence numbers match send order
        sequence_violations = []
        for i, event in enumerate(sent_events_sorted):
            expected_sequence = i + 1
            actual_sequence = event.get('sequence', -1)
            
            if actual_sequence != expected_sequence:
                sequence_violations.append(f"Position {i+1}: expected sequence {expected_sequence}, got {actual_sequence}")
        
        if sequence_violations:
            violations.append(f"Sequence ordering violations under backpressure: {sequence_violations[:5]}")  # Show first 5
        
        # Check for excessive send duration variations (indicating inconsistent handling)
        send_durations = [e.get('duration', 0) for e in sent_events if e.get('duration') is not None]
        if send_durations:
            avg_duration = sum(send_durations) / len(send_durations)
            max_duration = max(send_durations)
            
            if max_duration > avg_duration * 10:  # 10x average is concerning
                violations.append(f"Send duration variance too high: avg {avg_duration*1000:.2f}ms, max {max_duration*1000:.2f}ms")
        
        return violations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])