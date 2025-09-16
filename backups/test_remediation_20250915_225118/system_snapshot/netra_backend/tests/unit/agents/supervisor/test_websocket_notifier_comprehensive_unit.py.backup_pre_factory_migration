"""
Comprehensive Unit Tests for WebSocketNotifier

Tests the deprecated WebSocketNotifier class focusing on message creation,
payload building, delivery guarantees, and event queuing functionality.

CRITICAL REQUIREMENTS from CLAUDE.md:
1. Uses absolute imports 
2. Follows SSOT patterns from test_framework/ssot/
3. Uses StronglyTypedUserExecutionContext and proper type safety
4. Tests MUST RAISE ERRORS (no try/except blocks that hide failures)
5. Focuses on individual methods/functions in isolation

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures deprecated WebSocket notification system works correctly during transition period.

NOTE: This component is DEPRECATED. Use AgentWebSocketBridge instead.
These tests ensure stability during the transition period.
"""

import asyncio
import pytest
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.schemas.registry import AgentStatus


class TestWebSocketNotifierUnit(SSotBaseTestCase):
    """Comprehensive unit tests for WebSocketNotifier business logic."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocketManager with controlled behavior."""
        manager = AsyncMock()
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.broadcast = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """WebSocketNotifier instance with test mode enabled."""
        # Suppress deprecation warning for testing
        with patch('warnings.warn'):
            notifier = WebSocketNotifier(mock_websocket_manager, test_mode=True)
        return notifier

    @pytest.fixture
    def sample_context(self):
        """Sample agent execution context with strongly typed IDs."""
        return AgentExecutionContext(
            agent_name="test_agent",
            run_id=str(uuid.uuid4()),
            thread_id="test-thread-123",
            user_id="test-user-456",
            correlation_id="test-correlation-789",
            retry_count=0
        )

    def test_init_shows_deprecation_warning(self, mock_websocket_manager):
        """Test that initialization shows deprecation warning."""
        with patch('warnings.warn') as mock_warn:
            WebSocketNotifier(mock_websocket_manager, test_mode=True)
            
            # Verify deprecation warning was shown
            mock_warn.assert_called_once()
            call_args = mock_warn.call_args[0]
            assert "deprecated" in call_args[0].lower()
            assert "AgentWebSocketBridge" in call_args[0]

    def test_init_configures_test_mode(self, mock_websocket_manager):
        """Test that test mode configuration works correctly."""
        with patch('warnings.warn'):
            notifier = WebSocketNotifier(mock_websocket_manager, test_mode=True)
            
            # Verify test mode configuration
            assert notifier._test_mode is True
            assert notifier._auto_start_queue_processor is False
            assert isinstance(notifier.event_queue, deque)
            assert isinstance(notifier.delivery_confirmations, dict)
            assert isinstance(notifier.active_operations, dict)

    def test_init_configures_performance_settings(self, mock_websocket_manager):
        """Test that performance settings are configured correctly."""
        with patch('warnings.warn'):
            notifier = WebSocketNotifier(mock_websocket_manager, test_mode=True)
            
            # Verify performance settings
            assert notifier.max_queue_size == 1000
            assert notifier.retry_delay == 0.1  # 100ms
            assert notifier.backlog_notification_interval == 5.0  # 5 seconds
            assert notifier.critical_events == {'agent_started', 'tool_executing', 'tool_completed', 'agent_completed'}

    @pytest.mark.asyncio
    async def test_send_agent_started_success(self, websocket_notifier, sample_context, mock_websocket_manager):
        """Test successful agent started notification."""
        # Mock the critical event sending
        with patch.object(websocket_notifier, '_send_critical_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await websocket_notifier.send_agent_started(sample_context)
            
            # Verify critical event was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == sample_context.thread_id  # thread_id
            assert isinstance(call_args[0][1], WebSocketMessage)  # message
            assert call_args[0][2] == 'agent_started'  # event_type

    @pytest.mark.asyncio
    async def test_send_agent_thinking_with_enhanced_payload(self, websocket_notifier, sample_context, mock_websocket_manager):
        """Test agent thinking notification with enhanced payload."""
        await websocket_notifier.send_agent_thinking(
            context=sample_context,
            thought="Processing user request",
            step_number=2,
            progress_percentage=40.0,
            estimated_remaining_ms=5000,
            current_operation="data_analysis"
        )
        
        # Verify WebSocket message was sent
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        
        # Verify thread_id and message structure
        assert call_args[0][0] == sample_context.thread_id
        message_data = call_args[0][1]
        assert message_data["type"] == "agent_thinking"
        
        # Verify enhanced payload
        payload = message_data["payload"]
        assert payload["thought"] == "Processing user request"
        assert payload["step_number"] == 2
        assert payload["progress_percentage"] == 40.0
        assert payload["estimated_remaining_ms"] == 5000
        assert payload["current_operation"] == "data_analysis"
        assert payload["urgency"] == "high_priority"  # 5000ms = 5 seconds, which is <= 5 seconds
        assert payload["total_steps"] == 0  # Default value when not set

    @pytest.mark.asyncio
    async def test_send_tool_executing_with_context(self, websocket_notifier, sample_context, mock_websocket_manager):
        """Test tool executing notification with enhanced context."""
        with patch.object(websocket_notifier, '_send_critical_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await websocket_notifier.send_tool_executing(
                context=sample_context,
                tool_name="data_analyzer",
                tool_purpose="Analyze user data patterns",
                estimated_duration_ms=3000,
                parameters_summary="Processing 1000 records"
            )
            
            # Verify critical event was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][2] == 'tool_executing'  # event_type
            
            # Verify message payload
            message = call_args[0][1]
            payload = message.payload
            assert payload["tool_name"] == "data_analyzer"
            assert payload["tool_purpose"] == "Analyze user data patterns"
            assert payload["estimated_duration_ms"] == 3000
            assert payload["parameters_summary"] == "Processing 1000 records"

    @pytest.mark.asyncio
    async def test_send_agent_completed_marks_operation_complete(self, websocket_notifier, sample_context):
        """Test agent completed notification marks operation as complete."""
        # Mark operation as active first
        websocket_notifier._mark_operation_active(sample_context)
        assert sample_context.thread_id in websocket_notifier.active_operations
        
        with patch.object(websocket_notifier, '_send_critical_event', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await websocket_notifier.send_agent_completed(
                context=sample_context,
                result={"success": True, "output": "Task completed"},
                duration_ms=2500.0
            )
            
            # Verify operation marked as not processing
            operation = websocket_notifier.active_operations[sample_context.thread_id]
            assert operation['processing'] is False

    def test_build_enhanced_thinking_payload_urgency_calculation(self, websocket_notifier, sample_context):
        """Test urgency calculation in enhanced thinking payload."""
        # Test high priority (short duration)
        high_priority = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "Quick task", 1, 50.0, 2000, "validation"
        )
        assert high_priority["urgency"] == "high_priority"
        
        # Test medium priority (medium duration)
        medium_priority = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "Medium task", 2, 75.0, 7000, "processing"
        )
        assert medium_priority["urgency"] == "medium_priority"
        
        # Test low priority (long duration)
        low_priority = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "Long task", 3, 25.0, 15000, "analysis"
        )
        assert low_priority["urgency"] == "low_priority"

    def test_get_tool_context_hints(self, websocket_notifier):
        """Test tool context hints generation."""
        # Test known tool patterns
        search_hints = websocket_notifier._get_tool_context_hints("search_database")
        assert search_hints["category"] == "information_retrieval"
        assert search_hints["expected_duration"] == "medium"
        
        analyze_hints = websocket_notifier._get_tool_context_hints("analyze_data")
        assert analyze_hints["category"] == "data_processing"
        assert analyze_hints["expected_duration"] == "long"
        
        # Test unknown tool
        unknown_hints = websocket_notifier._get_tool_context_hints("unknown_tool")
        assert unknown_hints["category"] == "general"
        assert unknown_hints["expected_duration"] == "medium"

    def test_determine_error_severity(self, websocket_notifier):
        """Test error severity determination logic."""
        # Test critical errors
        critical_auth = websocket_notifier._determine_error_severity("authentication", "Auth failed")
        assert critical_auth == "critical"
        
        critical_db = websocket_notifier._determine_error_severity("database", "Connection lost")
        assert critical_db == "critical"
        
        # Test high priority errors
        high_timeout = websocket_notifier._determine_error_severity("timeout", "Request timeout")
        assert high_timeout == "high"
        
        high_rate = websocket_notifier._determine_error_severity("rate_limit", "Too many requests")
        assert high_rate == "high"
        
        # Test medium priority (default)
        medium_general = websocket_notifier._determine_error_severity("general", "Unknown error")
        assert medium_general == "medium"
        
        medium_none = websocket_notifier._determine_error_severity(None, "Error message")
        assert medium_none == "medium"

    def test_generate_default_recovery_suggestions(self, websocket_notifier):
        """Test recovery suggestions generation."""
        # Test timeout suggestions
        timeout_suggestions = websocket_notifier._generate_default_recovery_suggestions("timeout", "Operation timed out")
        assert "longer than expected" in timeout_suggestions[0]
        assert "smaller parts" in timeout_suggestions[1]
        
        # Test rate limit suggestions
        rate_suggestions = websocket_notifier._generate_default_recovery_suggestions("rate_limit", "Rate limit exceeded")
        assert "rate limit" in rate_suggestions[0]
        assert "wait a moment" in rate_suggestions[1]
        
        # Test validation suggestions
        validation_suggestions = websocket_notifier._generate_default_recovery_suggestions("validation", "Invalid input")
        assert "request format" in validation_suggestions[0]
        assert "required fields" in validation_suggestions[1]
        
        # Test database suggestions
        db_suggestions = websocket_notifier._generate_default_recovery_suggestions("database", "DB connection failed")
        assert "database issue" in db_suggestions[0]
        assert "data is safe" in db_suggestions[1]

    def test_generate_user_friendly_error_message(self, websocket_notifier):
        """Test user-friendly error message generation."""
        # Test timeout message
        timeout_msg = websocket_notifier._generate_user_friendly_error_message("timeout", "Timeout occurred", "data_agent")
        assert "data_agent" in timeout_msg
        assert "longer than usual" in timeout_msg
        
        # Test rate limit message
        rate_msg = websocket_notifier._generate_user_friendly_error_message("rate_limit", "Rate exceeded", "search_agent")
        assert "many requests recently" in rate_msg
        assert "wait a moment" in rate_msg
        
        # Test network message
        network_msg = websocket_notifier._generate_user_friendly_error_message("network", "Connection failed", "api_agent")
        assert "connectivity issue" in network_msg
        assert "try again" in network_msg
        
        # Test generic message
        generic_msg = websocket_notifier._generate_user_friendly_error_message(None, "Unknown error", "test_agent")
        assert "test_agent" in generic_msg
        assert "encountered an issue" in generic_msg

    def test_mark_operation_active(self, websocket_notifier, sample_context):
        """Test operation marking as active."""
        websocket_notifier._mark_operation_active(sample_context)
        
        # Verify operation is recorded
        assert sample_context.thread_id in websocket_notifier.active_operations
        operation = websocket_notifier.active_operations[sample_context.thread_id]
        
        assert operation['agent_name'] == sample_context.agent_name
        assert operation['run_id'] == sample_context.run_id
        assert operation['processing'] is True
        assert operation['event_count'] == 0
        assert isinstance(operation['start_time'], float)
        assert isinstance(operation['last_event_time'], float)

    @pytest.mark.asyncio
    async def test_mark_operation_complete(self, websocket_notifier, sample_context):
        """Test operation marking as complete."""
        # First mark as active
        websocket_notifier._mark_operation_active(sample_context)
        assert websocket_notifier.active_operations[sample_context.thread_id]['processing'] is True
        
        # Then mark as complete (need async context for asyncio.create_task)
        websocket_notifier._mark_operation_complete(sample_context)
        
        # Verify operation marked as not processing
        operation = websocket_notifier.active_operations[sample_context.thread_id]
        assert operation['processing'] is False

    def test_update_operation_activity(self, websocket_notifier, sample_context):
        """Test operation activity updating."""
        # Mark operation active first
        websocket_notifier._mark_operation_active(sample_context)
        original_event_count = websocket_notifier.active_operations[sample_context.thread_id]['event_count']
        original_last_event = websocket_notifier.active_operations[sample_context.thread_id]['last_event_time']
        
        # Wait a bit and update activity
        time.sleep(0.01)
        websocket_notifier._update_operation_activity(sample_context.thread_id)
        
        # Verify activity was updated
        operation = websocket_notifier.active_operations[sample_context.thread_id]
        assert operation['event_count'] == original_event_count + 1
        assert operation['last_event_time'] > original_last_event

    @pytest.mark.asyncio
    async def test_get_delivery_stats(self, websocket_notifier, sample_context):
        """Test delivery statistics collection."""
        # Add some test data
        websocket_notifier._mark_operation_active(sample_context)
        websocket_notifier.delivery_confirmations["test-msg-1"] = time.time()
        websocket_notifier.backlog_notifications[sample_context.thread_id] = time.time()
        
        stats = await websocket_notifier.get_delivery_stats()
        
        # Verify stats structure
        assert isinstance(stats, dict)
        assert 'queued_events' in stats
        assert 'active_operations' in stats
        assert 'delivery_confirmations' in stats
        assert 'backlog_notifications_sent' in stats
        
        # Verify current values
        assert stats['active_operations'] == 1
        assert stats['delivery_confirmations'] == 1
        assert stats['backlog_notifications_sent'] == 1

    @pytest.mark.asyncio
    async def test_shutdown_cleans_resources(self, websocket_notifier, sample_context):
        """Test shutdown properly cleans up resources."""
        # Add some test data
        websocket_notifier._mark_operation_active(sample_context)
        websocket_notifier.delivery_confirmations["test-msg"] = time.time()
        websocket_notifier.event_queue.append({"test": "data"})
        websocket_notifier.backlog_notifications[sample_context.thread_id] = time.time()
        
        # Verify data exists
        assert len(websocket_notifier.active_operations) > 0
        assert len(websocket_notifier.delivery_confirmations) > 0
        assert len(websocket_notifier.event_queue) > 0
        assert len(websocket_notifier.backlog_notifications) > 0
        
        # Shutdown
        await websocket_notifier.shutdown()
        
        # Verify cleanup
        assert len(websocket_notifier.active_operations) == 0
        assert len(websocket_notifier.delivery_confirmations) == 0
        assert len(websocket_notifier.event_queue) == 0
        assert len(websocket_notifier.backlog_notifications) == 0
        assert websocket_notifier._shutdown is True
        assert websocket_notifier._queue_processor_task is None

    def test_build_agent_status_changed_payload(self, websocket_notifier, sample_context):
        """Test agent status changed payload building."""
        old_status = AgentStatus.IDLE
        new_status = AgentStatus.EXECUTING
        
        payload = websocket_notifier._build_agent_status_changed_payload(sample_context, old_status, new_status)
        
        # Verify payload structure
        assert payload["agent_name"] == sample_context.agent_name
        assert payload["run_id"] == sample_context.run_id
        assert payload["old_status"] == old_status.value
        assert payload["new_status"] == new_status.value
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_send_websocket_message_safe_handles_none_thread_id(self, websocket_notifier, mock_websocket_manager):
        """Test safe WebSocket message sending handles None thread_id."""
        test_message = WebSocketMessage(type="agent_thinking", payload={"data": "test"})
        
        # Test with None thread_id
        await websocket_notifier._send_websocket_message_safe(None, test_message)
        
        # Should call broadcast instead of send_to_thread
        mock_websocket_manager.broadcast.assert_called_once_with(test_message.model_dump())
        mock_websocket_manager.send_to_thread.assert_not_called()

    def test_get_timestamp_returns_utc_float(self, websocket_notifier):
        """Test timestamp generation returns UTC float."""
        timestamp = websocket_notifier._get_timestamp()
        
        # Verify timestamp is a float
        assert isinstance(timestamp, float)
        
        # Verify timestamp is recent (within last 5 seconds)
        current_time = datetime.now(timezone.utc).timestamp()
        assert abs(current_time - timestamp) < 5.0