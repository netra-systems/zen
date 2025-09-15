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
from netra_backend.app.services.event_delivery_tracker import EventDeliveryTracker, EventDeliveryStatus, EventPriority, get_event_delivery_tracker
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from langchain_core.tools import BaseTool
from shared.types.core_types import UserID, RunID, ThreadID

class MockTool(BaseTool):
    """Mock tool for testing."""
    name: str = 'test_tool'
    description: str = 'A test tool'

    def _run(self, **kwargs):
        return 'Test result'

    async def _arun(self, **kwargs):
        return 'Test result'

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
    return UserExecutionContext(user_id='test_user_123', run_id='test_run_456', thread_id='test_thread_789')

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
    dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=mock_websocket_bridge, tools=[MockTool()])
    yield dispatcher
    await dispatcher.cleanup()

class TestEventDeliveryTracker:
    """Test the EventDeliveryTracker functionality."""

    def test_track_event(self, event_tracker):
        """Test basic event tracking."""
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run', priority=EventPriority.CRITICAL)
        assert event_id is not None
        assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.PENDING
        pending_events = event_tracker.get_pending_events()
        assert len(pending_events) == 1
        assert pending_events[0].event_id == event_id

    def test_confirm_event(self, event_tracker):
        """Test event confirmation."""
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run')
        assert event_tracker.mark_event_sent(event_id)
        assert event_tracker.confirm_event(event_id)
        assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.CONFIRMED
        metrics = event_tracker.get_metrics()
        assert metrics.events_confirmed == 1
        assert metrics.confirmation_rate == 100.0

    def test_fail_event(self, event_tracker):
        """Test event failure handling."""
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run')
        assert event_tracker.mark_event_sent(event_id)
        assert event_tracker.fail_event(event_id, 'Test error')
        assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.FAILED
        metrics = event_tracker.get_metrics()
        assert metrics.events_failed == 1

    def test_user_event_filtering(self, event_tracker):
        """Test filtering events by user."""
        event_id_1 = event_tracker.track_event('test', 'user1', 'run1')
        event_id_2 = event_tracker.track_event('test', 'user2', 'run2')
        event_id_3 = event_tracker.track_event('test', 'user1', 'run3')
        user1_events = event_tracker.get_pending_events('user1')
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
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=event_tracker):
            result = await tool_dispatcher.execute_tool('test_tool', {'param1': 'value1'})
            assert result.success
            pending_events = event_tracker.get_pending_events()
            tracked_events = [e for e in pending_events]
            event_types = [e.event_type for e in tracked_events]
            assert 'tool_executing' in event_types
            assert 'tool_completed' in event_types
            user_ids = [e.user_id for e in tracked_events]
            assert all((uid == 'test_user_123' for uid in user_ids))

    @pytest.mark.asyncio
    async def test_websocket_bridge_event_confirmation(self, tool_dispatcher, mock_websocket_bridge, event_tracker):
        """Test that WebSocket bridge confirms events when successful."""
        confirmed_events = []

        async def mock_notify_tool_executing(run_id, tool_name, agent_name=None, parameters=None, user_context=None):
            """Mock that extracts event_id and confirms it."""
            if parameters and 'event_id' in parameters:
                event_id = parameters['event_id']
                confirmed_events.append(event_id)
                event_tracker.confirm_event(event_id)
            return True

        async def mock_notify_tool_completed(run_id, tool_name, result=None, agent_name=None, execution_time_ms=None, user_context=None):
            """Mock that extracts event_id and confirms it."""
            if result and 'event_id' in result:
                event_id = result['event_id']
                confirmed_events.append(event_id)
                event_tracker.confirm_event(event_id)
            return True
        mock_websocket_bridge.notify_tool_executing = mock_notify_tool_executing
        mock_websocket_bridge.notify_tool_completed = mock_notify_tool_completed
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=event_tracker):
            result = await tool_dispatcher.execute_tool('test_tool', {'param1': 'value1'})
            assert result.success
            assert len(confirmed_events) == 2
            metrics = event_tracker.get_metrics()
            assert metrics.events_confirmed == 2
            assert metrics.confirmation_rate == 100.0

    @pytest.mark.asyncio
    async def test_websocket_failure_event_handling(self, tool_dispatcher, mock_websocket_bridge, event_tracker):
        """Test that WebSocket failures are handled correctly."""
        mock_websocket_bridge.notify_tool_executing = AsyncMock(return_value=False)
        mock_websocket_bridge.notify_tool_completed = AsyncMock(return_value=False)
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=event_tracker):
            result = await tool_dispatcher.execute_tool('test_tool', {'param1': 'value1'})
            assert result.success
            metrics = event_tracker.get_metrics()
            assert metrics.events_failed > 0

class TestAgentWebSocketBridgeEventConfirmation:
    """Test event confirmation in AgentWebSocketBridge."""

    @pytest.mark.asyncio
    async def test_notify_tool_executing_with_event_confirmation(self, event_tracker, user_context):
        """Test that notify_tool_executing confirms events."""
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        bridge = AgentWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        event_id = event_tracker.track_event(event_type='tool_executing', user_id=user_context.user_id, run_id=user_context.run_id)
        event_tracker.mark_event_sent(event_id)
        with patch('netra_backend.app.services.agent_websocket_bridge.get_event_delivery_tracker', return_value=event_tracker):
            success = await bridge.notify_tool_executing(run_id=user_context.run_id, tool_name='test_tool', parameters={'event_id': event_id, 'param1': 'value1'})
            assert success
            assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_notify_tool_completed_with_event_confirmation(self, event_tracker, user_context):
        """Test that notify_tool_completed confirms events."""
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        bridge = AgentWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        event_id = event_tracker.track_event(event_type='tool_completed', user_id=user_context.user_id, run_id=user_context.run_id)
        event_tracker.mark_event_sent(event_id)
        with patch('netra_backend.app.services.agent_websocket_bridge.get_event_delivery_tracker', return_value=event_tracker):
            success = await bridge.notify_tool_completed(run_id=user_context.run_id, tool_name='test_tool', result={'event_id': event_id, 'output': 'Test result'})
            assert success
            assert event_tracker.get_event_status(event_id) == EventDeliveryStatus.CONFIRMED

class TestEventRetryLogic:
    """Test event retry logic."""

    @pytest.mark.asyncio
    async def test_event_retry_on_failure(self, event_tracker):
        """Test that failed events are only retried when retry callback is provided."""
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run')
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, 'Network error')
        await asyncio.sleep(0.5)
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries == 0
        assert metrics.events_failed == 1

    @pytest.mark.asyncio
    async def test_retry_callback_functionality(self, event_tracker):
        """Test the new retry callback functionality."""
        retry_calls = []
        retry_success = True

        async def mock_retry_callback(event_id: str, event_type: str, data: dict) -> bool:
            """Mock retry callback that tracks calls."""
            retry_calls.append((event_id, event_type, data))
            return retry_success
        test_data = {'tool_name': 'test_tool', 'parameters': {'test': 'value'}}
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run', data=test_data, retry_callback=mock_retry_callback)
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, 'Mock failure')
        await asyncio.sleep(2.0)
        assert len(retry_calls) == 1
        called_event_id, called_event_type, called_data = retry_calls[0]
        assert called_event_id == event_id
        assert called_event_type == 'tool_executing'
        assert called_data == test_data
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
            return False
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run', retry_callback=failing_retry_callback)
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, 'Mock failure')
        await asyncio.sleep(2.0)
        assert len(retry_calls) == 1
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries >= 1

    @pytest.mark.asyncio
    async def test_retry_callback_exception_handling(self, event_tracker):
        """Test retry callback exception handling."""

        async def exception_retry_callback(event_id: str, event_type: str, data: dict) -> bool:
            """Mock retry callback that raises an exception."""
            raise Exception('Simulated callback exception')
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run', retry_callback=exception_retry_callback)
        event_tracker.mark_event_sent(event_id)
        event_tracker.fail_event(event_id, 'Mock failure')
        await asyncio.sleep(2.0)
        metrics = event_tracker.get_metrics()
        assert metrics.total_retries >= 1
        tracked_event = event_tracker._tracked_events.get(event_id)
        assert tracked_event is not None
        assert len(tracked_event.retry_errors) > 0
        assert 'Simulated callback exception' in tracked_event.retry_errors[-1]

    @pytest.mark.asyncio
    async def test_event_timeout_handling(self, event_tracker):
        """Test that events timeout correctly."""
        event_id = event_tracker.track_event(event_type='tool_executing', user_id='test_user', run_id='test_run', timeout_s=0.1)
        event_tracker.mark_event_sent(event_id)
        await asyncio.sleep(0.2)
        expired_events = event_tracker.get_expired_events()
        for event in expired_events:
            if event.event_id == event_id:
                event_tracker.metrics.events_timeout += 1
                event.status = EventDeliveryStatus.TIMEOUT
        metrics = event_tracker.get_metrics()
        assert metrics.events_timeout >= 1

@pytest.mark.asyncio
async def test_end_to_end_event_confirmation_flow():
    """Test the complete end-to-end event confirmation flow."""
    tracker = EventDeliveryTracker(default_timeout_s=5.0)
    await tracker.start()
    try:
        user_context = UserExecutionContext(user_id='test_user_e2e', run_id='test_run_e2e', thread_id='test_thread_e2e')
        mock_websocket_manager = AsyncMock()

        async def mock_send_to_user(user_id, notification):
            """Mock send that confirms events."""
            if 'event_id' in notification:
                event_id = notification['event_id']
                tracker.confirm_event(event_id)
            return True
        mock_websocket_manager.send_to_user = mock_send_to_user
        bridge = AgentWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_websocket_manager
        mock_tool = MockTool()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, websocket_bridge=bridge, tools=[mock_tool])
        if not dispatcher.has_tool('test_tool'):
            dispatcher.register_tool(mock_tool)
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.get_event_delivery_tracker', return_value=tracker), patch('netra_backend.app.services.agent_websocket_bridge.get_event_delivery_tracker', return_value=tracker):
            result = await dispatcher.execute_tool('test_tool', {'test_param': 'test_value'})
            assert result.success
            metrics = tracker.get_metrics()
            assert metrics.total_events_tracked >= 2
            assert metrics.confirmation_rate == 100.0
            assert metrics.events_failed == 0
        await dispatcher.cleanup()
    finally:
        await tracker.stop()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')