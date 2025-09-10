"""
Unit Tests for WebSocket Event Timing and Performance - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure WebSocket events are delivered with optimal timing
- Value Impact: Fast event delivery maintains user engagement and platform responsiveness
- Strategic Impact: Performance directly impacts user experience and conversion rates

CRITICAL: Slow or delayed events make the platform feel unresponsive and drive users away.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from shared.types import UserID, ThreadID, RunID

class TestWebSocketEventTimingPerformance:
    """Test WebSocket event timing and performance characteristics."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager with timing capture."""
        manager = Mock()
        manager.send_to_user = AsyncMock()
        # Track call times for performance analysis
        manager.call_times = []
        
        async def timed_send_to_user(*args, **kwargs):
            manager.call_times.append(time.time())
            return None
        
        manager.send_to_user.side_effect = timed_send_to_user
        return manager
    
    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocket notifier with timing tracking."""
        return AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
    
    @pytest.fixture
    def mock_execution_context(self):
        """Mock execution context for testing."""
        context = Mock(spec=AgentExecutionContext)
        context.user_id = UserID("perf_test_user")
        context.thread_id = ThreadID("perf_test_thread")
        context.run_id = RunID("perf_test_run")
        context.agent_name = "performance_test_agent"
        return context

    @pytest.mark.unit
    async def test_single_event_delivery_timing(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test single event delivery completes within performance requirements.
        
        Business Value: Individual events must be fast to maintain responsiveness.
        Users expect immediate feedback when AI starts processing.
        """
        # Act: Measure single event timing
        start_time = time.time()
        await websocket_notifier.notify_agent_started(mock_execution_context)
        end_time = time.time()
        
        event_duration = end_time - start_time
        
        # Assert: Performance requirement - single event under 100ms
        assert event_duration < 0.1, f"Single event took {event_duration*1000:.1f}ms, should be under 100ms"
        
        # Verify event was sent
        mock_websocket_manager.send_to_user.assert_called_once()
        
        # Business requirement: Event contains timing information
        call_args = mock_websocket_manager.send_to_user.call_args
        event_data = call_args[0][1]
        assert "timestamp" in event_data

    @pytest.mark.unit
    async def test_rapid_event_sequence_timing(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test rapid sequence of events maintains performance.
        
        Business Value: Fast event sequences keep users engaged during agent processing.
        Delays between events make the system feel sluggish.
        """
        # Act: Send rapid sequence of events
        start_time = time.time()
        
        await websocket_notifier.notify_agent_started(mock_execution_context)
        await websocket_notifier.notify_agent_thinking(mock_execution_context, "Analyzing...")
        await websocket_notifier.notify_tool_executing(mock_execution_context, "analyzer", {})
        await websocket_notifier.notify_tool_completed(mock_execution_context, "analyzer", {"result": "done"})
        await websocket_notifier.notify_agent_completed(mock_execution_context, {"status": "completed"})
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Assert: Performance requirement - 5 events under 500ms
        assert total_duration < 0.5, f"5-event sequence took {total_duration*1000:.1f}ms, should be under 500ms"
        assert mock_websocket_manager.send_to_user.call_count == 5
        
        # Verify event ordering timing
        call_times = mock_websocket_manager.call_times
        assert len(call_times) == 5
        
        # Business requirement: Events sent in rapid succession
        max_gap = 0
        for i in range(1, len(call_times)):
            gap = call_times[i] - call_times[i-1]
            max_gap = max(max_gap, gap)
        
        assert max_gap < 0.05, f"Maximum gap between events {max_gap*1000:.1f}ms should be under 50ms"

    @pytest.mark.unit
    async def test_concurrent_user_event_timing(self, mock_websocket_manager):
        """
        Test concurrent events for multiple users maintain performance.
        
        Business Value: Platform must handle multiple paying customers simultaneously.
        Performance degradation with concurrent users loses revenue.
        """
        # Arrange: Create multiple notifiers for different users
        notifier1 = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        notifier2 = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        notifier3 = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        
        # Create contexts for 3 concurrent users
        contexts = []
        for i in range(3):
            context = Mock(spec=AgentExecutionContext)
            context.user_id = UserID(f"concurrent_user_{i}")
            context.thread_id = ThreadID(f"concurrent_thread_{i}")
            context.run_id = RunID(f"concurrent_run_{i}")
            context.agent_name = f"concurrent_agent_{i}"
            contexts.append(context)
        
        # Act: Send concurrent events
        start_time = time.time()
        
        tasks = []
        notifiers = [notifier1, notifier2, notifier3]
        
        for notifier, context in zip(notifiers, contexts):
            tasks.append(notifier.notify_agent_started(context))
            tasks.append(notifier.notify_agent_thinking(context, f"Processing for user {context.user_id}"))
            tasks.append(notifier.notify_agent_completed(context, {"user": str(context.user_id)}))
        
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        concurrent_duration = end_time - start_time
        
        # Assert: Performance requirement - 9 concurrent events under 1 second
        assert concurrent_duration < 1.0, f"9 concurrent events took {concurrent_duration*1000:.1f}ms, should be under 1000ms"
        assert mock_websocket_manager.send_to_user.call_count == 9
        
        # Business requirement: All users get their events
        call_args_list = mock_websocket_manager.send_to_user.call_args_list
        user_ids_in_events = set()
        
        for call_args in call_args_list:
            user_id = call_args[0][0]  # First argument is user_id
            user_ids_in_events.add(str(user_id))
        
        expected_user_ids = {f"concurrent_user_{i}" for i in range(3)}
        assert user_ids_in_events == expected_user_ids, "All concurrent users should receive events"

    @pytest.mark.unit
    async def test_event_delivery_under_network_delay_simulation(self, mock_websocket_manager, mock_execution_context):
        """
        Test event timing performance with simulated network delays.
        
        Business Value: Events must remain responsive even with network latency.
        Global customers experience varying network conditions.
        """
        # Arrange: Simulate network delay
        async def delayed_send_to_user(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms network delay simulation
            return None
        
        mock_websocket_manager.send_to_user.side_effect = delayed_send_to_user
        notifier = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        
        # Act: Send events with network delay
        start_time = time.time()
        await notifier.notify_agent_started(mock_execution_context)
        await notifier.notify_agent_completed(mock_execution_context, {"result": "success"})
        end_time = time.time()
        
        total_duration = end_time - start_time
        
        # Assert: Performance degrades gracefully with network delay
        # Expected: 2 events * 50ms delay = ~100ms base + processing overhead
        assert total_duration < 0.2, f"Events with network delay took {total_duration*1000:.1f}ms, should be under 200ms"
        assert mock_websocket_manager.send_to_user.call_count == 2
        
        # Business requirement: Events still deliver despite network issues
        assert total_duration > 0.09, "Should show measurable network delay impact"

    @pytest.mark.unit
    async def test_event_batching_performance_optimization(self, mock_websocket_manager, mock_execution_context):
        """
        Test that rapid events don't overwhelm WebSocket connection.
        
        Business Value: Efficient event delivery prevents connection saturation.
        Overwhelmed connections drop events and break user experience.
        """
        notifier = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        
        # Act: Send many rapid events (simulating very active agent)
        event_count = 10
        start_time = time.time()
        
        for i in range(event_count):
            await notifier.notify_agent_thinking(mock_execution_context, f"Processing step {i+1}...")
            # No artificial delay - test system limits
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Assert: High-frequency events complete efficiently
        events_per_second = event_count / total_duration if total_duration > 0 else float('inf')
        
        # Business requirement: Should handle at least 50 events per second
        assert events_per_second >= 50, f"Event throughput {events_per_second:.1f} events/sec too low"
        assert mock_websocket_manager.send_to_user.call_count == event_count
        
        # Performance requirement: Total time scales linearly with event count
        avg_time_per_event = total_duration / event_count
        assert avg_time_per_event < 0.01, f"Average {avg_time_per_event*1000:.1f}ms per event should be under 10ms"

    @pytest.mark.unit
    async def test_event_memory_efficiency(self, mock_websocket_manager, mock_execution_context):
        """
        Test that event generation doesn't accumulate memory.
        
        Business Value: Efficient memory usage prevents system crashes during long sessions.
        Memory leaks would make the platform unreliable for enterprise customers.
        """
        import gc
        import sys
        
        notifier = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        
        # Act: Generate many events and measure memory impact
        gc.collect()  # Clean start
        initial_objects = len(gc.get_objects())
        
        # Generate 50 events to test memory efficiency
        for i in range(50):
            await notifier.notify_agent_thinking(mock_execution_context, f"Memory test iteration {i}")
        
        gc.collect()  # Clean up after test
        final_objects = len(gc.get_objects())
        
        # Assert: Memory usage doesn't grow excessively
        object_growth = final_objects - initial_objects
        
        # Business requirement: Reasonable memory growth per event
        growth_per_event = object_growth / 50 if object_growth > 0 else 0
        assert growth_per_event < 10, f"Memory growth {growth_per_event} objects per event too high"
        
        # Verify events were actually sent
        assert mock_websocket_manager.send_to_user.call_count == 50

    @pytest.mark.unit
    async def test_event_error_recovery_timing(self, mock_websocket_manager, mock_execution_context):
        """
        Test event delivery timing when errors occur.
        
        Business Value: Error recovery must be fast to maintain user experience.
        Slow error recovery makes the platform feel broken.
        """
        # Arrange: Setup error then recovery
        call_count = 0
        
        async def error_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated WebSocket error")
            return None  # Success on subsequent calls
        
        mock_websocket_manager.send_to_user.side_effect = error_then_success
        notifier = AgentWebSocketBridge(websocket_manager=mock_websocket_manager)
        
        # Act: Send events with error recovery
        start_time = time.time()
        
        # First event fails, should recover gracefully
        await notifier.notify_agent_started(mock_execution_context)
        await notifier.notify_agent_completed(mock_execution_context, {"status": "completed"})
        
        end_time = time.time()
        error_recovery_duration = end_time - start_time
        
        # Assert: Error recovery doesn't significantly slow down event delivery
        assert error_recovery_duration < 0.5, f"Error recovery took {error_recovery_duration*1000:.1f}ms, should be under 500ms"
        assert call_count == 2, "Should have attempted both event deliveries"
        
        # Business requirement: System continues functioning after errors
        # (No additional assertions needed - successful completion indicates recovery)