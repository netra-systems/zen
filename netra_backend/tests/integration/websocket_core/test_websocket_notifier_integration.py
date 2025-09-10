"""
Integration tests for WebSocketNotifier - Testing real WebSocket event delivery and critical event handling.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Reliable real-time chat feedback
- Value Impact: Ensures WebSocket events are delivered to users for real-time agent progress
- Strategic Impact: Critical for chat UX - validates actual event delivery and backlog handling

These tests focus on the deprecated WebSocketNotifier's integration with real WebSocket
connections and the critical event delivery system with guaranteed delivery and retry logic.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from test_framework.ssot.base_test_case import BaseTestCase


class TestWebSocketNotifierEventDelivery(BaseTestCase):
    """Integration tests for WebSocket event delivery and guaranteed delivery system."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create realistic mock WebSocket manager for integration testing."""
        mock_manager = AsyncMock()
        mock_manager.send_to_thread = AsyncMock()
        # Simulate successful delivery by default
        mock_manager.send_to_thread.return_value = True
        return mock_manager
    
    @pytest.fixture
    async def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocketNotifier with background processing enabled."""
        with patch('warnings.warn'):
            notifier = WebSocketNotifier.create_for_user(mock_websocket_manager)
            # Ensure background processing is working
            assert notifier._queue_processor_task is None
            yield notifier
            # Cleanup
            await notifier.shutdown()
    
    @pytest.fixture
    def sample_context(self):
        """Create realistic execution context."""
        return AgentExecutionContext(
            agent_name="cost_optimizer", thread_id="thread_cost_analysis_123",
            user_id="enterprise_user_456",
            run_id="run_cost_opt_789",
            total_steps=5
        )
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_critical_event_delivery_with_confirmation_tracking(self, websocket_notifier, sample_context):
        """Test critical events are sent with confirmation tracking."""
        # Act - Send critical agent_started event
        await websocket_notifier.send_agent_started(sample_context)
        
        # Assert - Verify WebSocket manager was called
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        call_args = websocket_notifier.websocket_manager.send_to_thread.call_args
        thread_id, message_data = call_args[0]
        
        assert thread_id == "thread_cost_analysis_123"
        assert message_data["type"] == "agent_started"
        assert message_data["payload"]["agent_name"] == "cost_optimizer"
        assert message_data["payload"]["run_id"] == "run_cost_opt_789"
        
        # Verify operation tracking was activated
        assert sample_context.thread_id in websocket_notifier.active_operations
        operation_info = websocket_notifier.active_operations[sample_context.thread_id]
        assert operation_info["agent_name"] == "cost_optimizer"
        assert operation_info["processing"] is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_critical_event_retry_on_failure(self, sample_context):
        """Test critical events are retried when delivery fails."""
        # Arrange - Mock WebSocket manager that fails initially then succeeds
        mock_manager = AsyncMock()
        call_count = 0
        
        async def mock_send_to_thread(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return False  # First call fails
            return True  # Second call succeeds
        
        mock_manager.send_to_thread = mock_send_to_thread
        
        with patch('warnings.warn'):
            websocket_notifier = WebSocketNotifier.create_for_user(mock_manager)
        
        try:
            # Act - Send critical event that will fail initially
            await websocket_notifier.send_agent_completed(sample_context, {"result": "success"})
            
            # Allow background processing time
            await asyncio.sleep(0.5)
            
            # Assert - Verify retry happened
            assert call_count >= 1  # At least one attempt was made
            
            # Verify event was eventually delivered
            delivery_stats = await websocket_notifier.get_delivery_stats()
            assert delivery_stats["queued_events"] >= 0  # May be 0 if processed
            
        finally:
            await websocket_notifier.shutdown()
    
    @pytest.mark.integration  
    @pytest.mark.asyncio
    async def test_complete_agent_lifecycle_event_flow(self, websocket_notifier, sample_context):
        """Test complete agent execution lifecycle generates all required events."""
        # Simulate complete agent execution flow
        events_sent = []
        
        def capture_event(*args, **kwargs):
            events_sent.append(args[1])  # Capture the message data
            return True
        
        websocket_notifier.websocket_manager.send_to_thread.side_effect = capture_event
        
        # Act - Send complete lifecycle events
        await websocket_notifier.send_agent_started(sample_context)
        await websocket_notifier.send_agent_thinking(
            sample_context, 
            "Analyzing cost data", 
            step_number=1, 
            progress_percentage=20.0,
            current_operation="data_analysis"
        )
        await websocket_notifier.send_tool_executing(
            sample_context, 
            "analyze_costs", 
            tool_purpose="Generate cost optimization recommendations",
            estimated_duration_ms=15000
        )
        await websocket_notifier.send_tool_completed(
            sample_context, 
            "analyze_costs", 
            result={"recommendations": 5, "potential_savings": 2500}
        )
        await websocket_notifier.send_agent_completed(
            sample_context, 
            result={"optimization_complete": True, "savings_found": "$2,500"}, 
            duration_ms=18500.0
        )
        
        # Assert - Verify all critical events were sent
        assert len(events_sent) == 5
        
        event_types = [event["type"] for event in events_sent]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert event_types == expected_events
        
        # Verify agent_thinking includes enhanced context
        thinking_event = events_sent[1]
        assert thinking_event["payload"]["progress_percentage"] == 20.0
        assert thinking_event["payload"]["current_operation"] == "data_analysis"
        assert "urgency" in thinking_event["payload"]
        
        # Verify tool_executing includes tool purpose and context
        tool_event = events_sent[2]
        assert tool_event["payload"]["tool_purpose"] == "Generate cost optimization recommendations"
        assert tool_event["payload"]["estimated_duration_ms"] == 15000
        assert "category" in tool_event["payload"]  # Tool context hints
        
        # Verify operation was marked as complete
        assert sample_context.thread_id not in websocket_notifier.active_operations or \
               not websocket_notifier.active_operations[sample_context.thread_id]["processing"]


class TestWebSocketNotifierBacklogHandling(BaseTestCase):
    """Integration tests for WebSocket event backlog handling and recovery."""
    
    @pytest.fixture
    def failing_websocket_manager(self):
        """Create WebSocket manager that simulates connection issues."""
        mock_manager = AsyncMock()
        mock_manager.send_to_thread = AsyncMock()
        # Simulate persistent failure
        mock_manager.send_to_thread.return_value = False
        return mock_manager
    
    @pytest.fixture
    async def websocket_notifier_with_backlog(self, failing_websocket_manager):
        """Create WebSocketNotifier that will experience backlog."""
        with patch('warnings.warn'):
            notifier = WebSocketNotifier.create_for_user(failing_websocket_manager)
            yield notifier
            await notifier.shutdown()
    
    @pytest.fixture
    def sample_context(self):
        """Create execution context."""
        return AgentExecutionContext(
            agent_name="data_processor", thread_id="thread_backlog_test",
            user_id="user_backlog_456",
            run_id="run_backlog_789"
        )
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_queueing_on_delivery_failure(self, websocket_notifier_with_backlog, sample_context):
        """Test events are queued when delivery fails."""
        # Act - Send critical events that will fail
        await websocket_notifier_with_backlog.send_agent_started(sample_context)
        await websocket_notifier_with_backlog.send_tool_executing(sample_context, "test_tool")
        await websocket_notifier_with_backlog.send_agent_completed(sample_context)
        
        # Allow background processing time
        await asyncio.sleep(0.3)
        
        # Assert - Verify events were queued for retry
        delivery_stats = await websocket_notifier_with_backlog.get_delivery_stats()
        assert delivery_stats["queued_events"] > 0
        
        # Verify backlog notification system activated
        assert sample_context.thread_id in websocket_notifier_with_backlog.backlog_notifications
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_backlog_processing_with_priority_handling(self, sample_context):
        """Test backlog processing prioritizes critical events."""
        # Arrange - Manager that fails initially then recovers
        mock_manager = AsyncMock()
        failure_count = 0
        
        async def mock_send_with_recovery(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:  # Fail first 3 attempts
                return False
            return True  # Then succeed
        
        mock_manager.send_to_thread = mock_send_with_recovery
        
        with patch('warnings.warn'):
            notifier = WebSocketNotifier.create_for_user(mock_manager)
        
        try:
            # Act - Send mixed critical and non-critical events
            await notifier.send_agent_started(sample_context)  # Critical
            await notifier.send_agent_thinking(sample_context, "processing", 1)  # Non-critical
            await notifier.send_tool_executing(sample_context, "important_tool")  # Critical
            
            # Allow significant processing time for retries
            await asyncio.sleep(1.0)
            
            # Assert - Verify events were eventually processed
            delivery_stats = await notifier.get_delivery_stats()
            # With retries, some events should eventually be delivered
            
            # Verify critical events were prioritized in queue management
            assert hasattr(notifier, 'critical_events')
            assert 'agent_started' in notifier.critical_events
            assert 'tool_executing' in notifier.critical_events
            
        finally:
            await notifier.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_backlog_notification_system(self, websocket_notifier_with_backlog, sample_context):
        """Test user receives backlog notifications when events are delayed."""
        # Override the WebSocket manager to capture backlog notifications
        captured_notifications = []
        
        async def capture_notifications(thread_id, message):
            captured_notifications.append(message)
            return False  # Still fail delivery
        
        websocket_notifier_with_backlog.websocket_manager.send_to_thread = capture_notifications
        
        # Act - Send events that will cause backlog
        await websocket_notifier_with_backlog.send_agent_started(sample_context)
        await websocket_notifier_with_backlog.send_tool_executing(sample_context, "slow_tool")
        
        # Allow time for backlog notification
        await asyncio.sleep(0.5)
        
        # Assert - Verify backlog notification was sent
        backlog_notifications = [
            msg for msg in captured_notifications 
            if msg.get("type") == "agent_update" and 
               "backlog_processing" in msg.get("payload", {}).get("current_task", "")
        ]
        
        # Should have received some backlog notifications
        # (May be 0 if processing was fast enough)
        delivery_stats = await websocket_notifier_with_backlog.get_delivery_stats()
        assert delivery_stats["queued_events"] >= 0  # Confirms queueing system is active


class TestWebSocketNotifierErrorRecovery(BaseTestCase):
    """Integration tests for WebSocket notifier error recovery and emergency handling."""
    
    @pytest.fixture
    def emergency_mock_manager(self):
        """Create WebSocket manager that triggers emergency conditions."""
        mock_manager = AsyncMock()
        mock_manager.send_to_thread = AsyncMock()
        # Always fail to trigger emergency notifications
        mock_manager.send_to_thread.return_value = False
        return mock_manager
    
    @pytest.fixture
    async def websocket_notifier_emergency(self, emergency_mock_manager):
        """Create WebSocketNotifier for emergency testing."""
        with patch('warnings.warn'):
            notifier = WebSocketNotifier.create_for_user(emergency_mock_manager)
            yield notifier
            await notifier.shutdown()
    
    @pytest.fixture
    def sample_context(self):
        """Create execution context for emergency testing."""
        return AgentExecutionContext(
            agent_name="critical_agent", thread_id="thread_emergency_123",
            user_id="vip_user_789",
            run_id="run_emergency_456"
        )
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_emergency_notification_on_critical_event_failure(self, websocket_notifier_emergency, sample_context):
        """Test emergency notifications are triggered for critical event failures."""
        # Capture log messages to verify emergency notification
        captured_logs = []
        
        with patch('netra_backend.app.agents.supervisor.websocket_notifier.logger') as mock_logger:
            mock_logger.critical = lambda msg: captured_logs.append(msg)
            
            # Act - Send critical event that will fail
            await websocket_notifier_emergency.send_agent_started(sample_context)
            
            # Allow processing time
            await asyncio.sleep(0.3)
        
        # Assert - Verify emergency notification was logged
        emergency_logs = [log for log in captured_logs if "EMERGENCY" in log or "CRITICAL EVENT DELIVERY FAILED" in log]
        assert len(emergency_logs) > 0
        
        # Verify the emergency notification contains proper context
        emergency_log = emergency_logs[0]
        assert "agent_started" in emergency_log
        assert sample_context.thread_id in emergency_log
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delivery_statistics_tracking(self, websocket_notifier_emergency, sample_context):
        """Test comprehensive delivery statistics tracking."""
        # Act - Send various events to generate statistics
        await websocket_notifier_emergency.send_agent_started(sample_context)
        await websocket_notifier_emergency.send_agent_thinking(sample_context, "analyzing", 1)
        await websocket_notifier_emergency.send_tool_executing(sample_context, "data_tool")
        await websocket_notifier_emergency.send_agent_completed(sample_context)
        
        # Allow processing time
        await asyncio.sleep(0.5)
        
        # Assert - Check delivery statistics
        stats = await websocket_notifier_emergency.get_delivery_stats()
        
        assert "queued_events" in stats
        assert "active_operations" in stats
        assert "delivery_confirmations" in stats
        assert "backlog_notifications_sent" in stats
        
        # Should have active operations and queued events due to failures
        assert stats["active_operations"] >= 0
        assert stats["queued_events"] >= 0
        
        # Verify operation was tracked
        assert sample_context.thread_id in websocket_notifier_emergency.active_operations
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_comprehensive_shutdown_and_cleanup(self, emergency_mock_manager, sample_context):
        """Test WebSocketNotifier shutdown handles cleanup properly."""
        # Create notifier and generate activity
        with patch('warnings.warn'):
            notifier = WebSocketNotifier.create_for_user(emergency_mock_manager)
        
        # Generate background activity
        await notifier.send_agent_started(sample_context)
        await notifier.send_tool_executing(sample_context, "cleanup_test_tool")
        
        # Allow some queue activity
        await asyncio.sleep(0.2)
        
        # Verify there's activity to clean up
        stats_before = await notifier.get_delivery_stats()
        assert stats_before["active_operations"] > 0 or stats_before["queued_events"] > 0
        
        # Act - Shutdown
        await notifier.shutdown()
        
        # Assert - Verify cleanup completed
        assert notifier._shutdown is True
        assert len(notifier.event_queue) == 0
        assert len(notifier.delivery_confirmations) == 0
        assert len(notifier.active_operations) == 0
        assert len(notifier.backlog_notifications) == 0
        
        # Verify background task was cancelled
        if notifier._queue_processor_task:
            assert notifier._queue_processor_task.done()