"""Unit tests for WebSocketNotifier - Real-time event notifications for agents.

Business Value Justification (BVJ):
- Segment: Platform/Internal - User Experience & System Reliability
- Business Goal: Real-time user feedback and system transparency
- Value Impact: Enables users to track agent progress and system status in real-time
- Strategic Impact: Prevents user abandonment by providing immediate feedback on system operations

CRITICAL: Tests validate WebSocket event delivery, queue management, and error handling.
All tests use SSOT patterns and IsolatedEnvironment for environment access.

DEPRECATION NOTE: This module is deprecated in favor of AgentWebSocketBridge, but tests
ensure existing functionality works correctly during migration period.
"""

import asyncio
import time
import uuid
from collections import deque
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketNotifier(SSotAsyncTestCase):
    """Unit tests for WebSocketNotifier - Real-time agent event notifications."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        
        # Create mock WebSocket manager
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.send_to_thread.return_value = True
        
        # Create WebSocketNotifier in test mode (disables background tasks)
        self.notifier = WebSocketNotifier(
            websocket_manager=self.mock_websocket_manager,
            test_mode=True  # Prevents background queue processor from hanging tests
        )
        
        # Create test context
        self.test_run_id = uuid.uuid4()
        self.test_context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=self.test_run_id,
            retry_count=0,
            thread_id="test_thread_123"
        )
        
        # Record setup metrics
        self.record_metric("websocket_notifier_setup", True)

    async def test_send_agent_started_notification(self):
        """
        BVJ: Validates agent started notifications inform users that processing has begun.
        Critical for user experience - users need immediate feedback when agents start.
        """
        # Send agent started notification
        start_time = time.time()
        await self.notifier.send_agent_started(self.test_context)
        notification_time = time.time() - start_time
        
        # Verify WebSocket message was sent
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        # Verify message structure
        thread_id, message_data = call_args[0]
        assert thread_id == self.test_context.thread_id, "Should send to correct thread"
        assert message_data["type"] == "agent_started", "Should be agent_started message"
        assert message_data["payload"]["agent_name"] == "test_agent", "Should include agent name"
        assert message_data["payload"]["run_id"] == str(self.test_run_id), "Should include run ID"
        
        # Verify operation tracking for backlog management
        assert self.test_context.thread_id in self.notifier.active_operations, "Should track active operation"
        operation_info = self.notifier.active_operations[self.test_context.thread_id]
        assert operation_info["processing"] is True, "Should mark operation as processing"
        
        # Record performance metrics
        self.record_metric("agent_started_notification_time", notification_time)
        self.record_metric("active_operations_tracked", 1)
        
        # Business value assertion: Fast notification delivery
        assert notification_time < 0.1, f"Notification should be fast: {notification_time}s"

    async def test_send_agent_thinking_with_progress(self):
        """
        BVJ: Validates thinking notifications provide progress updates for user engagement.
        Prevents user confusion during long-running operations by showing active progress.
        """
        # Send thinking notification with progress
        thought = "Analyzing user requirements..."
        progress_percentage = 45.0
        estimated_remaining_ms = 2000
        
        await self.notifier.send_agent_thinking(
            context=self.test_context,
            thought=thought,
            step_number=3,
            progress_percentage=progress_percentage,
            estimated_remaining_ms=estimated_remaining_ms,
            current_operation="requirement_analysis"
        )
        
        # Verify message was sent
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        thread_id, message_data = call_args[0]
        
        # Verify enhanced thinking payload
        payload = message_data["payload"]
        assert payload["thought"] == thought, "Should include thinking content"
        assert payload["progress_percentage"] == progress_percentage, "Should include progress"
        assert payload["estimated_remaining_ms"] == estimated_remaining_ms, "Should include time estimate"
        assert payload["current_operation"] == "requirement_analysis", "Should include current operation"
        assert payload["urgency"] == "medium_priority", "Should calculate urgency based on remaining time"
        
        # Record progress metrics
        self.record_metric("thinking_notifications_sent", 1)
        self.record_metric("progress_percentage_max", progress_percentage)

    async def test_send_tool_executing_with_context(self):
        """
        BVJ: Validates tool execution notifications provide transparency about system operations.
        Users need to understand what tools are being used to solve their problems.
        """
        # Send tool executing notification with context
        tool_name = "data_analyzer"
        tool_purpose = "Analyzing customer data patterns"
        estimated_duration_ms = 3000
        parameters_summary = "dataset_size=1000, analysis_type=pattern"
        
        await self.notifier.send_tool_executing(
            context=self.test_context,
            tool_name=tool_name,
            tool_purpose=tool_purpose,
            estimated_duration_ms=estimated_duration_ms,
            parameters_summary=parameters_summary
        )
        
        # Verify critical event delivery
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        thread_id, message_data = call_args[0]
        
        # Verify enhanced tool payload
        payload = message_data["payload"]
        assert payload["tool_name"] == tool_name, "Should include tool name"
        assert payload["tool_purpose"] == tool_purpose, "Should include purpose"
        assert payload["estimated_duration_ms"] == estimated_duration_ms, "Should include duration estimate"
        assert payload["parameters_summary"] == parameters_summary, "Should include parameters"
        assert payload["execution_phase"] == "starting", "Should indicate execution phase"
        
        # Verify tool context hints
        assert "category" in payload, "Should include tool category context"
        assert "expected_duration" in payload, "Should include duration context"
        
        # Record tool execution metrics
        self.record_metric("tool_executing_notifications", 1)
        self.record_metric("tool_context_provided", 1)

    async def test_send_agent_completed_with_results(self):
        """
        BVJ: Validates completion notifications provide closure and results to users.
        Critical for user satisfaction - users need clear indication of successful completion.
        """
        # Send completion notification with results
        result_data = {
            "analysis_complete": True,
            "recommendations": ["optimize_query", "add_index"],
            "performance_improvement": "45%"
        }
        duration_ms = 5500.0
        
        await self.notifier.send_agent_completed(
            context=self.test_context,
            result=result_data,
            duration_ms=duration_ms
        )
        
        # Verify critical event delivery
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        thread_id, message_data = call_args[0]
        
        # Verify completion payload
        payload = message_data["payload"]
        assert payload["agent_name"] == "test_agent", "Should include agent name"
        assert payload["run_id"] == self.test_run_id, "Should include run ID"
        assert payload["duration_ms"] == duration_ms, "Should include execution duration"
        assert payload["result"] == result_data, "Should include result data"
        
        # Verify operation completion tracking
        operation_info = self.notifier.active_operations.get(self.test_context.thread_id)
        if operation_info:
            assert operation_info["processing"] is False, "Should mark operation as complete"
        
        # Record completion metrics
        self.record_metric("agent_completed_notifications", 1)
        self.record_metric("completion_duration_ms", duration_ms)

    async def test_critical_event_delivery_with_retry(self):
        """
        BVJ: Validates critical events are delivered with retry logic for system reliability.
        Ensures important notifications reach users even under network issues or high load.
        """
        # Setup WebSocket manager to fail first attempt, succeed on retry
        self.mock_websocket_manager.send_to_thread.side_effect = [False, True]  # Fail then succeed
        
        # Mock critical event delivery
        with patch.object(self.notifier, '_queue_for_retry', new_callable=AsyncMock) as mock_queue:
            with patch.object(self.notifier, '_trigger_emergency_notification', new_callable=AsyncMock) as mock_emergency:
                # Send critical event (agent_started)
                await self.notifier.send_agent_started(self.test_context)
                
                # Verify retry was queued for failed critical event
                mock_queue.assert_called_once()
                mock_emergency.assert_called_once()
        
        # Record critical event handling metrics
        self.record_metric("critical_event_failures", 1)
        self.record_metric("emergency_notifications_triggered", 1)

    async def test_event_queue_backlog_management(self):
        """
        BVJ: Validates backlog management prevents memory exhaustion under high load.
        Critical for system stability during peak usage periods.
        """
        # Fill event queue to test backlog management
        test_events = []
        for i in range(self.notifier.max_queue_size + 10):  # Exceed max size
            event_data = {
                'message_id': f'test_{i}',
                'thread_id': self.test_context.thread_id,
                'event_type': 'agent_thinking' if i % 2 == 0 else 'agent_started',
                'retry_count': 0,
                'max_retries': 3 if i % 2 == 1 else 1  # Critical events have more retries
            }
            test_events.append(event_data)
        
        # Manually fill the queue
        self.notifier.event_queue = deque(test_events)
        
        # Add one more event to trigger backlog management
        new_event = {
            'message_id': 'overflow_test',
            'thread_id': self.test_context.thread_id,
            'event_type': 'agent_started',  # Critical event
            'retry_count': 0,
            'max_retries': 3
        }
        
        await self.notifier._queue_for_retry(new_event)
        
        # Verify queue size is managed
        assert len(self.notifier.event_queue) <= self.notifier.max_queue_size, "Queue should not exceed max size"
        
        # Verify critical events are preserved
        critical_events = [e for e in self.notifier.event_queue if e['event_type'] in self.notifier.critical_events]
        non_critical_events = [e for e in self.notifier.event_queue if e['event_type'] not in self.notifier.critical_events]
        
        # Critical events should be preserved over non-critical ones
        assert len(critical_events) > 0, "Should preserve critical events"
        
        # Record backlog management metrics
        self.record_metric("queue_overflow_handled", 1)
        self.record_metric("critical_events_preserved", len(critical_events))

    async def test_delivery_stats_monitoring(self):
        """
        BVJ: Validates delivery statistics provide monitoring data for system health.
        Enables proactive monitoring and optimization of WebSocket delivery performance.
        """
        # Setup some test state
        self.notifier.event_queue.append({'test': 'event'})
        self.notifier.active_operations[self.test_context.thread_id] = {'test': 'operation'}
        self.notifier.delivery_confirmations['test_id'] = time.time()
        self.notifier.backlog_notifications[self.test_context.thread_id] = time.time()
        
        # Get delivery stats
        stats = await self.notifier.get_delivery_stats()
        
        # Verify stats structure
        assert isinstance(stats, dict), "Should return stats dictionary"
        assert "queued_events" in stats, "Should include queued events count"
        assert "active_operations" in stats, "Should include active operations count"
        assert "delivery_confirmations" in stats, "Should include confirmations count"
        assert "backlog_notifications_sent" in stats, "Should include backlog notifications count"
        
        # Verify stats values
        assert stats["queued_events"] == 1, "Should count queued events correctly"
        assert stats["active_operations"] == 1, "Should count active operations correctly"
        assert stats["delivery_confirmations"] == 1, "Should count confirmations correctly"
        assert stats["backlog_notifications_sent"] == 1, "Should count backlog notifications correctly"
        
        # Record monitoring metrics
        self.record_metric("stats_monitoring_available", 1)
        self.record_metric("total_stats_categories", len(stats))

    async def test_websocket_notifier_deprecation_warning(self):
        """
        BVJ: Validates deprecation warnings guide developers to newer implementation.
        Supports smooth migration to AgentWebSocketBridge without breaking existing code.
        """
        # Capture deprecation warning during initialization
        with pytest.warns(DeprecationWarning, match="WebSocketNotifier is deprecated"):
            deprecated_notifier = WebSocketNotifier(
                websocket_manager=self.mock_websocket_manager,
                test_mode=True
            )
        
        # Verify notifier still works despite deprecation
        assert deprecated_notifier is not None, "Deprecated notifier should still function"
        assert deprecated_notifier.websocket_manager is not None, "Should have WebSocket manager"
        
        # Record deprecation handling metrics
        self.record_metric("deprecation_warnings_issued", 1)

    async def test_error_severity_determination(self):
        """
        BVJ: Validates error severity classification for appropriate user communication.
        Ensures users receive appropriately prioritized error information and recovery guidance.
        """
        # Test critical error severity
        critical_severity = self.notifier._determine_error_severity("database", "Connection failed")
        assert critical_severity == "critical", "Database errors should be critical"
        
        # Test high error severity
        high_severity = self.notifier._determine_error_severity("timeout", "Request timeout")
        assert high_severity == "high", "Timeout errors should be high severity"
        
        # Test medium error severity
        medium_severity = self.notifier._determine_error_severity("validation", "Invalid input")
        assert medium_severity == "medium", "Validation errors should be medium severity"
        
        # Test unknown error type defaults to medium
        default_severity = self.notifier._determine_error_severity("unknown", "Unknown error")
        assert default_severity == "medium", "Unknown errors should default to medium"
        
        # Test recovery suggestions generation
        suggestions = self.notifier._generate_default_recovery_suggestions("timeout", "Operation timeout")
        assert len(suggestions) > 0, "Should generate recovery suggestions"
        assert any("longer than expected" in s for s in suggestions), "Should mention timeout context"
        
        # Record error handling metrics
        self.record_metric("error_severities_tested", 4)
        self.record_metric("recovery_suggestions_generated", len(suggestions))

    async def test_shutdown_cleanup(self):
        """
        BVJ: Validates proper resource cleanup prevents memory leaks and hanging processes.
        Critical for system stability and resource management in production environments.
        """
        # Add some test data to be cleaned up
        self.notifier.event_queue.append({'test': 'event'})
        self.notifier.delivery_confirmations['test'] = time.time()
        self.notifier.active_operations['test'] = {'test': 'op'}
        self.notifier.backlog_notifications['test'] = time.time()
        
        # Record pre-shutdown state
        pre_shutdown_queue_size = len(self.notifier.event_queue)
        pre_shutdown_confirmations = len(self.notifier.delivery_confirmations)
        
        # Perform shutdown
        await self.notifier.shutdown()
        
        # Verify cleanup
        assert len(self.notifier.event_queue) == 0, "Event queue should be cleared"
        assert len(self.notifier.delivery_confirmations) == 0, "Confirmations should be cleared"
        assert len(self.notifier.active_operations) == 0, "Active operations should be cleared"
        assert len(self.notifier.backlog_notifications) == 0, "Backlog notifications should be cleared"
        assert self.notifier._shutdown is True, "Shutdown flag should be set"
        
        # Record cleanup metrics
        self.record_metric("shutdown_cleanup_completed", 1)
        self.record_metric("events_cleaned_up", pre_shutdown_queue_size)
        self.record_metric("confirmations_cleaned_up", pre_shutdown_confirmations)

    def teardown_method(self, method=None):
        """Cleanup test fixtures and verify metrics."""
        # Ensure notifier is properly shut down
        if hasattr(self, 'notifier'):
            # Run shutdown in async context if needed
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(self.notifier.shutdown())
            except RuntimeError:
                # Event loop might be closed, create new one
                asyncio.run(self.notifier.shutdown())
        
        # Verify test completed successfully
        assert self.get_test_context() is not None, "Test context should be available"
        
        # Record final metrics
        self.record_metric("test_completed", True)
        
        # Call parent teardown
        super().teardown_method(method)