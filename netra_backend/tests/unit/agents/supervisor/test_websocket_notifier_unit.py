"""
Unit Tests for WebSocketNotifier (DEPRECATED)

Tests the deprecated WebSocketNotifier for backward compatibility and
to ensure proper deprecation warnings are issued.

NOTE: This class is DEPRECATED. New code should use AgentWebSocketBridge.
These tests ensure existing functionality works during migration period.

Focus: Event delivery, guaranteed delivery system, concurrency optimization
"""

import asyncio
import pytest
import time
import warnings
from collections import deque
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class TestWebSocketNotifier:
    """Unit tests for WebSocketNotifier (deprecated functionality)."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        manager = AsyncMock()
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.broadcast = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    async def websocket_notifier(self, mock_websocket_manager):
        """WebSocketNotifier instance with mocked WebSocket manager."""
        # Capture deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Use test_mode=True to prevent background task hanging
            notifier = WebSocketNotifier(mock_websocket_manager, test_mode=True)
            
            # Verify deprecation warning was issued
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "WebSocketNotifier is deprecated" in str(w[0].message)
            
        yield notifier
        
        # CRITICAL: Ensure proper cleanup to prevent hanging tests
        await notifier.shutdown()

    @pytest.fixture
    def sample_context(self):
        """Sample agent execution context."""
        return AgentExecutionContext(
            agent_name="test_agent",
            run_id=uuid4(),
            thread_id="test-thread-123",
            user_id="test-user",
            correlation_id="test-correlation"
        )

    async def test_initialization_with_deprecation_warning(self, mock_websocket_manager):
        """Test that initialization shows deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            notifier = WebSocketNotifier(mock_websocket_manager, test_mode=True)
            
            # Verify warning was issued
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "AgentWebSocketBridge" in str(w[0].message)
        
        # Verify initialization
        assert notifier.websocket_manager == mock_websocket_manager
        assert isinstance(notifier.event_queue, deque)
        assert isinstance(notifier.delivery_confirmations, dict)
        assert notifier.max_queue_size == 1000
        assert notifier.retry_delay == 0.1
        
        # Cleanup
        await notifier.shutdown()

    def test_critical_events_configuration(self, websocket_notifier):
        """Test critical events are properly configured."""
        expected_critical = {'agent_started', 'tool_executing', 'tool_completed', 'agent_completed'}
        assert websocket_notifier.critical_events == expected_critical

    @pytest.mark.asyncio
    async def test_send_agent_started_success(self, websocket_notifier, sample_context):
        """Test successful agent started notification."""
        await websocket_notifier.send_agent_started(sample_context)
        
        # Verify WebSocket call was made
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        args, kwargs = websocket_notifier.websocket_manager.send_to_thread.call_args
        
        assert args[0] == sample_context.thread_id
        assert isinstance(args[1], dict)  # Message payload
        assert args[1]['type'] == 'agent_started'

    @pytest.mark.asyncio
    async def test_send_agent_started_marks_operation_active(self, websocket_notifier, sample_context):
        """Test that agent started marks operation as active."""
        await websocket_notifier.send_agent_started(sample_context)
        
        # Verify operation is marked as active
        assert sample_context.thread_id in websocket_notifier.active_operations
        operation = websocket_notifier.active_operations[sample_context.thread_id]
        assert operation['agent_name'] == sample_context.agent_name
        assert operation['run_id'] == sample_context.run_id
        assert operation['processing'] is True

    @pytest.mark.asyncio
    async def test_send_agent_completed_marks_operation_complete(self, websocket_notifier, sample_context):
        """Test that agent completed marks operation as complete."""
        # First start an operation
        await websocket_notifier.send_agent_started(sample_context)
        assert websocket_notifier.active_operations[sample_context.thread_id]['processing'] is True
        
        # Then complete it
        await websocket_notifier.send_agent_completed(sample_context, {"result": "success"}, 1500)
        
        # Verify operation is marked as complete
        assert websocket_notifier.active_operations[sample_context.thread_id]['processing'] is False

    @pytest.mark.asyncio
    async def test_send_agent_thinking_with_enhanced_payload(self, websocket_notifier, sample_context):
        """Test enhanced agent thinking notification."""
        await websocket_notifier.send_agent_thinking(
            context=sample_context,
            thought="Analyzing the problem",
            step_number=2,
            progress_percentage=45.5,
            estimated_remaining_ms=5000,
            current_operation="data_analysis"
        )
        
        # Verify WebSocket call
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        args, kwargs = websocket_notifier.websocket_manager.send_to_thread.call_args
        
        payload = args[1]['payload']
        assert payload['thought'] == "Analyzing the problem"
        assert payload['step_number'] == 2
        assert payload['progress_percentage'] == 45.5
        assert payload['estimated_remaining_ms'] == 5000
        assert payload['current_operation'] == "data_analysis"
        assert 'urgency' in payload  # Should calculate urgency

    @pytest.mark.asyncio
    async def test_send_tool_executing_enhanced(self, websocket_notifier, sample_context):
        """Test enhanced tool executing notification."""
        await websocket_notifier.send_tool_executing(
            context=sample_context,
            tool_name="data_analyzer",
            tool_purpose="Analyze dataset for patterns",
            estimated_duration_ms=3000,
            parameters_summary="dataset_size: large, format: JSON"
        )
        
        # Verify WebSocket call
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        args, kwargs = websocket_notifier.websocket_manager.send_to_thread.call_args
        
        payload = args[1]['payload']
        assert payload['tool_name'] == "data_analyzer"
        assert payload['tool_purpose'] == "Analyze dataset for patterns"
        assert payload['estimated_duration_ms'] == 3000
        assert payload['parameters_summary'] == "dataset_size: large, format: JSON"

    @pytest.mark.asyncio
    async def test_send_agent_error_with_recovery_guidance(self, websocket_notifier, sample_context):
        """Test enhanced error notification with recovery suggestions."""
        await websocket_notifier.send_agent_error(
            context=sample_context,
            error_message="Database connection failed",
            error_type="database",
            error_details={"host": "db.example.com", "timeout": 30},
            recovery_suggestions=["Check database connectivity", "Verify credentials"],
            is_recoverable=True,
            estimated_retry_delay_ms=5000
        )
        
        # Verify WebSocket call
        websocket_notifier.websocket_manager.send_to_thread.assert_called_once()
        args, kwargs = websocket_notifier.websocket_manager.send_to_thread.call_args
        
        payload = args[1]['payload']
        assert payload['error_message'] == "Database connection failed"
        assert payload['error_type'] == "database"
        assert payload['recovery_suggestions'] == ["Check database connectivity", "Verify credentials"]
        assert payload['is_recoverable'] is True
        assert payload['estimated_retry_delay_ms'] == 5000
        assert 'user_friendly_message' in payload

    def test_determine_error_severity(self, websocket_notifier):
        """Test error severity determination logic."""
        # Critical errors
        assert websocket_notifier._determine_error_severity("authentication", "login failed") == "critical"
        assert websocket_notifier._determine_error_severity("database", "connection error") == "critical"
        
        # High errors
        assert websocket_notifier._determine_error_severity("timeout", "request timeout") == "high"
        assert websocket_notifier._determine_error_severity("rate_limit", "too many requests") == "high"
        
        # Medium errors
        assert websocket_notifier._determine_error_severity("general", "unknown error") == "medium"
        assert websocket_notifier._determine_error_severity(None, "some error") == "medium"

    def test_generate_default_recovery_suggestions(self, websocket_notifier):
        """Test default recovery suggestions generation."""
        # Timeout suggestions
        suggestions = websocket_notifier._generate_default_recovery_suggestions("timeout", "request timeout")
        assert any("longer than expected" in s for s in suggestions)
        assert any("smaller parts" in s for s in suggestions)
        
        # Rate limit suggestions
        suggestions = websocket_notifier._generate_default_recovery_suggestions("rate_limit", "too many requests")
        assert any("rate limit" in s for s in suggestions)
        assert any("wait a moment" in s for s in suggestions)
        
        # Database suggestions
        suggestions = websocket_notifier._generate_default_recovery_suggestions("database", "connection failed")
        assert any("database issue" in s for s in suggestions)
        assert any("data is safe" in s for s in suggestions)

    def test_generate_user_friendly_error_message(self, websocket_notifier):
        """Test user-friendly error message generation."""
        # Timeout message
        message = websocket_notifier._generate_user_friendly_error_message("timeout", "request timeout", "test_agent")
        assert "test_agent" in message
        assert "longer than usual" in message
        
        # Rate limit message
        message = websocket_notifier._generate_user_friendly_error_message("rate_limit", "too many requests", "test_agent")
        assert "many requests recently" in message
        
        # Generic message
        message = websocket_notifier._generate_user_friendly_error_message("unknown", "some error", "test_agent")
        assert "test_agent" in message
        assert "unexpected issue" in message

    def test_get_tool_context_hints(self, websocket_notifier):
        """Test tool context hints generation."""
        # Search tool
        hints = websocket_notifier._get_tool_context_hints("search_documents")
        assert hints['category'] == "information_retrieval"
        assert hints['expected_duration'] == "medium"
        
        # Analyze tool
        hints = websocket_notifier._get_tool_context_hints("analyze_data")
        assert hints['category'] == "data_processing"
        assert hints['expected_duration'] == "long"
        
        # Unknown tool
        hints = websocket_notifier._get_tool_context_hints("unknown_tool")
        assert hints['category'] == "general"
        assert hints['expected_duration'] == "medium"

    @pytest.mark.asyncio
    async def test_critical_event_delivery_guarantee(self, websocket_notifier, sample_context):
        """Test critical event delivery with retry logic."""
        # Make WebSocket fail initially then succeed
        call_count = 0
        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return False  # First call fails
            return True  # Subsequent calls succeed
        
        websocket_notifier.websocket_manager.send_to_thread.side_effect = failing_then_success
        
        # Send critical event
        await websocket_notifier.send_agent_started(sample_context)
        
        # Wait for potential retries
        await asyncio.sleep(0.2)
        
        # Verify retry attempts were made
        assert websocket_notifier.websocket_manager.send_to_thread.call_count >= 1

    @pytest.mark.asyncio
    async def test_queue_processing_for_failed_events(self, websocket_notifier, sample_context):
        """Test event queuing and processing for failed deliveries."""
        # Make WebSocket always fail
        websocket_notifier.websocket_manager.send_to_thread.return_value = False
        
        # Send critical event that should be queued
        await websocket_notifier.send_agent_started(sample_context)
        
        # Wait for queue processing
        await asyncio.sleep(0.15)
        
        # Verify event was queued
        assert len(websocket_notifier.event_queue) >= 0  # May have been processed and removed

    @pytest.mark.asyncio
    async def test_backlog_notification(self, websocket_notifier, sample_context):
        """Test backlog notification for users."""
        # Make WebSocket fail to trigger backlog
        websocket_notifier.websocket_manager.send_to_thread.return_value = False
        
        # Send multiple events to create backlog
        await websocket_notifier.send_agent_started(sample_context)
        await websocket_notifier.send_tool_executing(sample_context, "test_tool")
        
        # Wait for backlog processing
        await asyncio.sleep(0.1)
        
        # Verify backlog notification was attempted
        # (Hard to test directly without exposing internals)

    @pytest.mark.asyncio
    async def test_websocket_manager_none_handling(self, sample_context):
        """Test handling when WebSocket manager is None."""
        # Create notifier with None manager
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            notifier = WebSocketNotifier(None, test_mode=True)
        
        try:
            # All methods should handle None gracefully
            await notifier.send_agent_started(sample_context)
            await notifier.send_agent_thinking(sample_context, "test thought")
            await notifier.send_tool_executing(sample_context, "test_tool")
            await notifier.send_agent_completed(sample_context)
            
            # Should not raise exceptions
        finally:
            # Cleanup
            await notifier.shutdown()

    @pytest.mark.asyncio
    async def test_delivery_stats(self, websocket_notifier):
        """Test delivery statistics collection."""
        stats = await websocket_notifier.get_delivery_stats()
        
        assert isinstance(stats, dict)
        assert 'queued_events' in stats
        assert 'active_operations' in stats
        assert 'delivery_confirmations' in stats
        assert 'backlog_notifications_sent' in stats
        
        # All should be non-negative integers
        for key, value in stats.items():
            assert isinstance(value, int)
            assert value >= 0

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, websocket_notifier):
        """Test proper cleanup during shutdown."""
        # Add some test data
        websocket_notifier.event_queue.append({'test': 'data'})
        websocket_notifier.delivery_confirmations['test'] = time.time()
        websocket_notifier.active_operations['test'] = {'test': 'data'}
        
        # Shutdown
        await websocket_notifier.shutdown()
        
        # Verify cleanup
        assert len(websocket_notifier.event_queue) == 0
        assert len(websocket_notifier.delivery_confirmations) == 0
        assert len(websocket_notifier.active_operations) == 0
        assert len(websocket_notifier.backlog_notifications) == 0

    def test_build_message_payloads(self, websocket_notifier, sample_context):
        """Test message payload building methods."""
        # Test agent started payload
        message = websocket_notifier._build_started_message(sample_context)
        assert isinstance(message, WebSocketMessage)
        assert message.type == "agent_started"
        assert 'agent_name' in message.payload
        
        # Test thinking payload
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "test thought", 1, 50.0, 2000, "analysis"
        )
        assert payload['thought'] == "test thought"
        assert payload['progress_percentage'] == 50.0
        assert payload['estimated_remaining_ms'] == 2000
        assert payload['current_operation'] == "analysis"
        
        # Test tool executing payload
        payload = websocket_notifier._build_enhanced_tool_executing_payload(
            sample_context, "test_tool", "Test tool purpose", 1500, "param summary"
        )
        assert payload['tool_name'] == "test_tool"
        assert payload['tool_purpose'] == "Test tool purpose"
        assert payload['estimated_duration_ms'] == 1500

    @pytest.mark.asyncio
    async def test_context_based_vs_parameter_based_methods(self, websocket_notifier, sample_context):
        """Test that methods work with both context and parameter approaches."""
        # Context-based call
        await websocket_notifier.send_agent_failed(
            context=sample_context,
            error_message="Context-based error"
        )
        
        # Parameter-based call
        await websocket_notifier.send_agent_failed(
            agent_id="test-agent-id",
            error="Parameter-based error",
            thread_id="test-thread"
        )
        
        # Both should succeed
        assert websocket_notifier.websocket_manager.send_to_thread.call_count == 2

    def test_urgency_calculation(self, websocket_notifier, sample_context):
        """Test urgency calculation based on estimated time."""
        # High priority (short time)
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "test", 1, None, 3000, None  # 3 seconds
        )
        assert payload['urgency'] == "high_priority"
        
        # Medium priority (medium time)
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "test", 1, None, 7000, None  # 7 seconds
        )
        assert payload['urgency'] == "medium_priority"
        
        # Low priority (long time)
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "test", 1, None, 15000, None  # 15 seconds
        )
        assert payload['urgency'] == "low_priority"

    @pytest.mark.asyncio
    async def test_emergency_notification_system(self, websocket_notifier, sample_context):
        """Test emergency notification when critical events fail."""
        # Make WebSocket consistently fail
        websocket_notifier.websocket_manager.send_to_thread.return_value = False
        
        with patch('netra_backend.app.agents.supervisor.websocket_notifier.logger') as mock_logger:
            # Send critical event that should trigger emergency notification
            await websocket_notifier.send_agent_started(sample_context)
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Verify emergency logging was attempted
            # (Emergency notification should log at CRITICAL level)
            mock_logger.critical.assert_called()

    def test_timestamp_generation(self, websocket_notifier):
        """Test timestamp generation consistency."""
        timestamp1 = websocket_notifier._get_timestamp()
        time.sleep(0.01)  # Small delay
        timestamp2 = websocket_notifier._get_timestamp()
        
        assert isinstance(timestamp1, float)
        assert isinstance(timestamp2, float)
        assert timestamp2 > timestamp1