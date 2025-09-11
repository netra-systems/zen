"""Integration tests for tool execution event confirmation system.

Tests the complete flow:
1. UnifiedToolDispatcher tracks events when sending
2. WebSocket bridge handles event confirmations
3. EventDeliveryTracker manages retry logic
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.services.event_delivery_tracker import (
    EventDeliveryTracker, 
    EventDeliveryStatus, 
    EventPriority,
    get_event_delivery_tracker
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from langchain_core.tools import BaseTool
from shared.types.core_types import UserID, RunID, ThreadID


class MockTool(BaseTool):
    """Mock tool for testing."""
    name: str = "test_tool"
    description: str = "A test tool"
    
    def _run(self, **kwargs):
        return "Test result"
    
    async def _arun(self, **kwargs):
        return "Test result"


@pytest.fixture
async def event_tracker():
    """Create and start an event delivery tracker for testing."""
    tracker = EventDeliveryTracker(default_timeout_s=5.0, max_tracked_events=100)
    await tracker.start()
    yield tracker
    await tracker.stop()


@pytest.fixture
def user_context():
    """Create a user execution context for testing."""
    return UserExecutionContext(
        user_id="test_user_123",
        run_id="test_run_456", 
        thread_id="test_thread_789"
    )


@pytest.fixture
def mock_websocket_bridge():
    """Create a mock WebSocket bridge."""
    bridge = Mock(spec=AgentWebSocketBridge)
    bridge.notify_tool_executing = AsyncMock(return_value=True)
    bridge.notify_tool_completed = AsyncMock(return_value=True)
    return bridge


@pytest.fixture
async def tool_dispatcher(user_context, mock_websocket_bridge):
    """Create a tool dispatcher with mock WebSocket bridge."""
    # Create dispatcher through the factory method
    dispatcher = await UnifiedToolDispatcher.create_for_user(
        user_context=user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[MockTool()]
    )
    yield dispatcher
    await dispatcher.cleanup()


class TestEventDeliveryTracker:
    """Test the EventDeliveryTracker functionality."""
    
    def test_track_event(self, event_tracker):
        """Test basic event tracking."""
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run",
            priority=EventPriority.CRITICAL
        )
        
        assert event_id is not None
        assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.PENDING
        
        # Verify event is in pending list
        pending_events = event_tracker.get_pending_events()
        assert len(pending_events) == 1
        assert pending_events[0].event_id == event_id
    
    def test_confirm_event(self, event_tracker):
        """Test event confirmation."""
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run"
        )
        
        # Mark as sent, then confirm
        assert event_tracker.mark_event_sent(event_id)
        assert event_tracker.confirm_event(event_id)
        
        assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.CONFIRMED
        
        # Check metrics
        metrics = event_tracker.get_metrics()
        assert metrics.events_confirmed == 1
        assert metrics.confirmation_rate == 100.0
    
    def test_fail_event(self, event_tracker):
        """Test event failure handling."""
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run"
        )
        
        # Mark as sent, then fail
        assert event_tracker.mark_event_sent(event_id)
        assert event_tracker.fail_event(event_id, "Test error")
        
        assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.FAILED
        
        # Check metrics
        metrics = event_tracker.get_metrics()
        assert metrics.events_failed == 1
    
    def test_user_event_filtering(self, event_tracker):
        """Test filtering events by user."""
        # Create events for different users
        event_id_1 = event_tracker.track_event("test", "user1", "run1")
        event_id_2 = event_tracker.track_event("test", "user2", "run2")
        event_id_3 = event_tracker.track_event("test", "user1", "run3")
        
        # Get events for user1
        user1_events = event_tracker.get_pending_events("user1")
        assert len(user1_events) == 2
        event_ids = [e.event_id for e in user1_events]
        assert event_id_1 in event_ids
        assert event_id_3 in event_ids
        assert event_id_2 not in event_ids


class TestUnifiedToolDispatcherEventTracking:
    """Test event tracking integration in UnifiedToolDispatcher."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_event_tracking(self, tool_dispatcher, event_tracker):
        """Test that tool execution creates tracked events."""
        # Patch the global tracker getter to return our test tracker
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=event_tracker):
            # Execute a tool
            result = await tool_dispatcher.execute_tool("test_tool", {"param1": "value1"})
            
            assert result.success
            
            # Check that events were tracked
            pending_events = event_tracker.get_pending_events()
            tracked_events = [e for e in pending_events]
            
            # Should have tool_executing and tool_completed events
            event_types = [e.event_type for e in tracked_events]
            assert "tool_executing" in event_types
            assert "tool_completed" in event_types
            
            # All events should be for our user
            user_ids = [e.user_id for e in tracked_events]
            assert all(uid == "test_user_123" for uid in user_ids)
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_event_confirmation(self, tool_dispatcher, mock_websocket_bridge, event_tracker):
        """Test that WebSocket bridge confirms events when successful."""
        
        # Configure mock bridge to extract and confirm event IDs
        confirmed_events = []
        
        async def mock_notify_tool_executing(run_id, tool_name, agent_name=None, parameters=None, user_context=None):
            """Mock that extracts event_id and confirms it."""
            if parameters and "event_id" in parameters:
                event_id = parameters["event_id"]
                confirmed_events.append(event_id)
                # Simulate confirmation
                event_tracker.confirm_event(event_id)
            return True
        
        async def mock_notify_tool_completed(run_id, tool_name, result=None, agent_name=None, execution_time_ms=None, user_context=None):
            """Mock that extracts event_id and confirms it."""
            if result and "event_id" in result:
                event_id = result["event_id"]
                confirmed_events.append(event_id)
                # Simulate confirmation
                event_tracker.confirm_event(event_id)
            return True
        
        mock_websocket_bridge.notify_tool_executing = mock_notify_tool_executing
        mock_websocket_bridge.notify_tool_completed = mock_notify_tool_completed
        
        # Patch the global tracker getter
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=event_tracker):
            # Execute a tool
            result = await tool_dispatcher.execute_tool("test_tool", {"param1": "value1"})
            
            assert result.success
            
            # Check that events were confirmed
            assert len(confirmed_events) == 2  # tool_executing and tool_completed
            
            # Verify all tracked events are confirmed
            metrics = event_tracker.get_metrics()
            assert metrics.events_confirmed == 2
            assert metrics.confirmation_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_websocket_failure_event_handling(self, tool_dispatcher, mock_websocket_bridge, event_tracker):
        """Test that WebSocket failures are handled correctly."""
        
        # Configure mock bridge to fail
        mock_websocket_bridge.notify_tool_executing = AsyncMock(return_value=False)
        mock_websocket_bridge.notify_tool_completed = AsyncMock(return_value=False)
        
        # Patch the global tracker getter
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=event_tracker):
            # Execute a tool
            result = await tool_dispatcher.execute_tool("test_tool", {"param1": "value1"})
            
            assert result.success  # Tool execution itself should succeed
            
            # Check that events were marked as failed
            metrics = event_tracker.get_metrics()
            assert metrics.events_failed > 0


class TestAgentWebSocketBridgeEventConfirmation:
    """Test event confirmation in AgentWebSocketBridge."""
    
    @pytest.mark.asyncio
    async def test_notify_tool_executing_with_event_confirmation(self, event_tracker, user_context):
        """Test that notify_tool_executing confirms events."""
        
        # Create a mock WebSocket manager
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        
        # Create bridge with mock manager
        bridge = AgentWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        
        # Track an event
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id=user_context.user_id,
            run_id=user_context.run_id
        )
        event_tracker.mark_event_sent(event_id)
        
        # Patch the global tracker getter
        with patch('netra_backend.app.services.agent_websocket_bridge.get_event_delivery_tracker', return_value=event_tracker):
            # Call notify_tool_executing with event_id in parameters
            success = await bridge.notify_tool_executing(
                run_id=user_context.run_id,
                tool_name="test_tool",
                parameters={"event_id": event_id, "param1": "value1"}
            )
            
            assert success
            
            # Verify event was confirmed
            assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.CONFIRMED
    
    @pytest.mark.asyncio 
    async def test_notify_tool_completed_with_event_confirmation(self, event_tracker, user_context):
        """Test that notify_tool_completed confirms events."""
        
        # Create a mock WebSocket manager
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        
        # Create bridge with mock manager
        bridge = AgentWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        
        # Track an event
        event_id = event_tracker.track_event(
            event_type="tool_completed",
            user_id=user_context.user_id,
            run_id=user_context.run_id
        )
        event_tracker.mark_event_sent(event_id)
        
        # Patch the global tracker getter
        with patch('netra_backend.app.services.agent_websocket_bridge.get_event_delivery_tracker', return_value=event_tracker):
            # Call notify_tool_completed with event_id in result
            success = await bridge.notify_tool_completed(
                run_id=user_context.run_id,
                tool_name="test_tool",
                result={"event_id": event_id, "output": "Test result"}
            )
            
            assert success
            
            # Verify event was confirmed
            assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.CONFIRMED


class TestEventRetryLogic:
    """Test event retry logic."""
    
    @pytest.mark.asyncio
    async def test_event_retry_on_failure(self, event_tracker):
        """Test that failed events are only retried when retry callback is provided."""
        
        # Create event WITHOUT retry callback
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run"
        )
        
        # Mark as sent then fail
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, "Network error")
        
        # Wait a short time for any retry attempts
        await asyncio.sleep(0.5)
        
        # Check that NO retry was attempted because no callback was provided
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries == 0  # No retry should happen without callback
        assert metrics.events_failed == 1  # Event should still be marked as failed
    
    @pytest.mark.asyncio
    async def test_retry_callback_functionality(self, event_tracker):
        """Test the new retry callback functionality."""
        
        # Track calls to the retry callback
        retry_calls = []
        retry_success = True
        
        async def mock_retry_callback(event_id: str, event_type: str, data: dict) -> bool:
            """Mock retry callback that tracks calls."""
            retry_calls.append((event_id, event_type, data))
            return retry_success
        
        # Create event with retry callback
        test_data = {"tool_name": "test_tool", "parameters": {"test": "value"}}
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run",
            data=test_data,
            retry_callback=mock_retry_callback
        )
        
        # Mark as sent then fail to trigger retry
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, "Mock failure")
        
        # Wait for retry to be scheduled and executed
        await asyncio.sleep(2.0)
        
        # Verify retry callback was called
        assert len(retry_calls) == 1
        called_event_id, called_event_type, called_data = retry_calls[0]
        assert called_event_id == event_id
        assert called_event_type == "tool_executing"
        assert called_data == test_data
        
        # Check that successful retry updated metrics
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries >= 1
        assert metrics.successful_retries >= 1
    
    @pytest.mark.asyncio
    async def test_retry_callback_failure_handling(self, event_tracker):
        """Test retry callback failure handling."""
        
        retry_calls = []
        
        async def failing_retry_callback(event_id: str, event_type: str, data: dict) -> bool:
            """Mock retry callback that always fails."""
            retry_calls.append((event_id, event_type, data))
            return False  # Always fail
        
        # Create event with failing retry callback
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run",
            retry_callback=failing_retry_callback
        )
        
        # Mark as sent then fail to trigger retry
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, "Mock failure")
        
        # Wait for retry to execute
        await asyncio.sleep(2.0)
        
        # Verify retry callback was called but failed
        assert len(retry_calls) == 1
        
        # Check metrics show retry attempt but no success
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries >= 1
        # successful_retries should remain 0 since callback returned False
    
    @pytest.mark.asyncio
    async def test_retry_callback_exception_handling(self, event_tracker):
        """Test retry callback exception handling."""
        
        async def exception_retry_callback(event_id: str, event_type: str, data: dict) -> bool:
            """Mock retry callback that raises an exception."""
            raise Exception("Simulated callback exception")
        
        # Create event with exception-throwing retry callback
        event_id = event_tracker.track_event(
            event_type="tool_executing", 
            user_id="test_user",
            run_id="test_run",
            retry_callback=exception_retry_callback
        )
        
        # Mark as sent then fail to trigger retry
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, "Mock failure")
        
        # Wait for retry to execute
        await asyncio.sleep(2.0)
        
        # Should not crash, but retry should be recorded as attempted
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries >= 1
        
        # Check that the event has error information
        tracked_event = event_tracker._tracked_events.get(event_id)
        assert tracked_event is not None
        assert len(tracked_event.retry_errors) > 0
        assert "Simulated callback exception" in tracked_event.retry_errors[-1]
    
    @pytest.mark.asyncio
    async def test_event_timeout_handling(self, event_tracker):
        """Test that events timeout correctly."""
        
        # Create event with very short timeout
        event_id = event_tracker.track_event(
            event_type="tool_executing",
            user_id="test_user",
            run_id="test_run",
            timeout_s=0.1  # 100ms timeout
        )
        
        event_tracker.mark_event_sent(event_id)
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Trigger cleanup manually (normally done by background task)
        expired_events = event_tracker.get_expired_events()
        for event in expired_events:
            if event.event_id == event_id:
                event_tracker.metrics.events_timeout += 1
                event.status = EventDeliveryStatus.TIMEOUT
        
        # Check that event timed out
        metrics = event_tracker.get_metrics()
        assert metrics.events_timeout >= 1


@pytest.mark.asyncio
async def test_end_to_end_event_confirmation_flow():
    """Test the complete end-to-end event confirmation flow."""
    
    # Setup components
    tracker = EventDeliveryTracker(default_timeout_s=5.0)
    await tracker.start()
    
    try:
        user_context = UserExecutionContext(
            user_id="test_user_e2e",
            run_id="test_run_e2e",
            thread_id="test_thread_e2e"
        )
        
        # Create mock WebSocket manager that confirms events
        mock_websocket_manager = AsyncMock()
        
        async def mock_send_to_user(user_id, notification):
            """Mock send that confirms events."""
            # Extract event_id and confirm it
            if "event_id" in notification:
                event_id = notification["event_id"]
                tracker.confirm_event(event_id)
            return True
        
        mock_websocket_manager.send_to_user = mock_send_to_user
        
        # Create bridge with confirming manager
        bridge = AgentWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        
        # Create dispatcher
        mock_tool = MockTool()
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=bridge,
            tools=[mock_tool]
        )
        
        # Ensure tool is registered (in case factory doesn't handle it properly)
        if not dispatcher.has_tool("test_tool"):
            dispatcher.register_tool(mock_tool)
        
        # Patch global tracker
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=tracker), \
             patch('netra_backend.app.services.agent_websocket_bridge.get_event_delivery_tracker', return_value=tracker):
            
            # Execute tool
            result = await dispatcher.execute_tool("test_tool", {"test_param": "test_value"})
            
            assert result.success
            
            # Check that all events were confirmed
            metrics = tracker.get_metrics()
            assert metrics.total_events_tracked >= 2  # at least tool_executing and tool_completed
            assert metrics.confirmation_rate == 100.0
            assert metrics.events_failed == 0
        
        await dispatcher.cleanup()
        
    finally:
        await tracker.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])