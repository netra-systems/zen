"""Unit Tests for WebSocket Notifier Business Logic

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable real-time user feedback during AI execution
- Value Impact: Prevents user abandonment due to lack of feedback ($120K+ MRR protection)
- Strategic Impact: Core chat UX functionality that builds user trust

CRITICAL TEST PURPOSE:
These unit tests validate the business logic of AgentWebSocketBridge (DEPRECATED)
to ensure migration to AgentWebSocketBridge maintains functionality.

Test Coverage:
- Event delivery guarantees and retry logic
- Backlog handling and user notifications
- Critical event prioritization
- Concurrent user support optimization
- Error handling and graceful degradation
"""

import pytest
import time
import uuid
from unittest.mock import AsyncMock, Mock, patch
from collections import deque

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from test_framework.ssot.mocks import MockFactory


class TestWebSocketNotifierBusiness:
    """Unit tests for WebSocket Notifier business logic validation."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_factory = MockFactory()
        self.mock_websocket_manager = self.mock_factory.create_websocket_manager_mock()
        
        # Suppress deprecation warnings for unit testing
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.notifier = AgentWebSocketBridge(
                websocket_manager=self.mock_websocket_manager,
                test_mode=True  # Disable background tasks for testing
            )
    
    def teardown_method(self):
        """Clean up after each test."""
        self.mock_factory.cleanup()
    
    @pytest.mark.unit
    def test_websocket_notifier_initialization(self):
        """Test WebSocket Notifier proper initialization in test mode."""
        # Assert - verify core components are initialized
        assert self.notifier.websocket_manager is not None
        assert isinstance(self.notifier.event_queue, deque)
        assert isinstance(self.notifier.delivery_confirmations, dict)
        assert isinstance(self.notifier.active_operations, dict)
        
        # Verify performance settings
        assert self.notifier.max_queue_size == 1000
        assert self.notifier.retry_delay == 0.1
        assert self.notifier.critical_events == {'agent_started', 'tool_executing', 'tool_completed', 'agent_completed'}
        
        # Verify test mode settings
        assert self.notifier._test_mode == True
        assert self.notifier._auto_start_queue_processor == False
    
    @pytest.mark.unit
    async def test_send_agent_started_success(self):
        """Test successful agent started notification."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Act
        await self.notifier.send_agent_started(context)
        
        # Assert - verify WebSocket manager called
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        # Verify correct thread ID
        assert call_args[0][0] == "test-thread"
        
        # Verify message structure
        message_data = call_args[0][1]
        assert message_data["type"] == "agent_started"
        assert message_data["payload"]["agent_name"] == "test_agent"
        assert "timestamp" in message_data["payload"]
        
        # Verify operation tracking
        assert "test-thread" in self.notifier.active_operations
        assert self.notifier.active_operations["test-thread"]["agent_name"] == "test_agent"
    
    @pytest.mark.unit
    async def test_send_agent_thinking_with_progress(self):
        """Test agent thinking notification with progress information."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="thinking_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Act
        await self.notifier.send_agent_thinking(
            context=context,
            thought="Analyzing your request...",
            step_number=1,
            progress_percentage=25.0,
            estimated_remaining_ms=5000,
            current_operation="data_analysis"
        )
        
        # Assert - verify WebSocket manager called
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        message_data = call_args[0][1]
        payload = message_data["payload"]
        
        assert message_data["type"] == "agent_thinking"
        assert payload["thought"] == "Analyzing your request..."
        assert payload["step_number"] == 1
        assert payload["progress_percentage"] == 25.0
        assert payload["estimated_remaining_ms"] == 5000
        assert payload["current_operation"] == "data_analysis"
        assert payload["urgency"] == "medium_priority"  # > 5 seconds
    
    @pytest.mark.unit
    async def test_send_tool_executing_with_context(self):
        """Test tool executing notification with enhanced context."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="tool_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Act
        await self.notifier.send_tool_executing(
            context=context,
            tool_name="data_analyzer",
            tool_purpose="Analyze cost optimization opportunities",
            estimated_duration_ms=3000,
            parameters_summary="AWS account analysis"
        )
        
        # Assert - verify critical event handling
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        message_data = call_args[0][1]
        payload = message_data["payload"]
        
        assert message_data["type"] == "tool_executing"
        assert payload["tool_name"] == "data_analyzer"
        assert payload["tool_purpose"] == "Analyze cost optimization opportunities"
        assert payload["estimated_duration_ms"] == 3000
        assert payload["parameters_summary"] == "AWS account analysis"
        assert payload["execution_phase"] == "starting"
    
    @pytest.mark.unit
    async def test_send_agent_completed_with_cleanup(self):
        """Test agent completed notification with operation cleanup."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="completed_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Add active operation first
        self.notifier._mark_operation_active(context)
        
        result = {"recommendations": ["Optimize EC2 instances"], "savings": 1200}
        duration_ms = 2500.0
        
        # Act
        await self.notifier.send_agent_completed(
            context=context,
            result=result,
            duration_ms=duration_ms
        )
        
        # Assert - verify completion message
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        message_data = call_args[0][1]
        payload = message_data["payload"]
        
        assert message_data["type"] == "agent_completed"
        assert payload["agent_name"] == "completed_agent"
        assert payload["duration_ms"] == duration_ms
        assert payload["result"] == result
        
        # Verify operation marked as complete
        operation = self.notifier.active_operations.get("test-thread")
        assert operation is not None
        assert operation["processing"] == False
    
    @pytest.mark.unit
    async def test_send_agent_error_with_recovery_guidance(self):
        """Test agent error notification with enhanced error context."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="error_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Act
        await self.notifier.send_agent_error(
            context=context,
            error_message="Rate limit exceeded",
            error_type="rate_limit",
            error_details={"limit": 1000, "window": "1h"},
            recovery_suggestions=["Wait 60 seconds", "Upgrade plan"],
            is_recoverable=True,
            estimated_retry_delay_ms=60000
        )
        
        # Assert - verify error message structure
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        message_data = call_args[0][1]
        payload = message_data["payload"]
        
        assert message_data["type"] == "agent_error"
        assert payload["error_message"] == "Rate limit exceeded"
        assert payload["error_type"] == "rate_limit"
        assert payload["severity"] == "high"  # Rate limit is high severity
        assert payload["is_recoverable"] == True
        assert payload["estimated_retry_delay_ms"] == 60000
        assert payload["recovery_suggestions"] == ["Wait 60 seconds", "Upgrade plan"]
        assert "rate limit" in payload["user_friendly_message"].lower()
    
    @pytest.mark.unit
    async def test_critical_event_delivery_guarantees(self):
        """Test critical event delivery with retry logic."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="critical_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Mock WebSocket manager to fail first call, succeed second
        call_count = 0
        async def mock_send_with_failure(thread_id, message):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return False  # First call fails
            return True  # Second call succeeds
        
        self.mock_websocket_manager.send_to_thread.side_effect = mock_send_with_failure
        
        # Act
        await self.notifier.send_agent_started(context)
        
        # Assert - verify retry logic attempted
        # Note: In test mode, background queue processor is disabled
        # So we verify the event was queued for retry
        assert len(self.notifier.event_queue) == 1
        
        # Verify queued event is correct
        queued_event = self.notifier.event_queue[0]
        assert queued_event["event_type"] == "agent_started"
        assert queued_event["thread_id"] == "test-thread"
        assert queued_event["retry_count"] == 0
        assert queued_event["max_retries"] == 3  # Critical event gets more retries
    
    @pytest.mark.unit
    def test_operation_activity_tracking(self):
        """Test operation activity tracking for backlog management."""
        # Arrange
        context = AgentExecutionContext(
            agent_name="tracked_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        # Act
        self.notifier._mark_operation_active(context)
        
        # Assert - verify operation tracking
        assert "test-thread" in self.notifier.active_operations
        operation = self.notifier.active_operations["test-thread"]
        
        assert operation["agent_name"] == "tracked_agent"
        assert operation["run_id"] == context.run_id
        assert operation["processing"] == True
        assert operation["event_count"] == 0
        assert "start_time" in operation
        assert "last_event_time" in operation
        
        # Act - update activity
        self.notifier._update_operation_activity("test-thread")
        
        # Assert - verify activity updated
        updated_operation = self.notifier.active_operations["test-thread"]
        assert updated_operation["event_count"] == 1
        assert updated_operation["last_event_time"] > operation["last_event_time"]
    
    @pytest.mark.unit
    def test_error_severity_determination(self):
        """Test error severity determination for user experience."""
        # Test cases for error severity
        test_cases = [
            # Critical errors
            ("authentication", "Invalid token", "critical"),
            ("database", "Connection failed", "critical"),
            ("network", "Connection timeout", "critical"),
            # High errors
            ("rate_limit", "Too many requests", "high"),
            ("timeout", "Request timeout", "high"),
            ("validation", "Invalid input", "high"),
            # Medium errors (default)
            ("general", "Unknown error", "medium"),
            ("processing", "Processing failed", "medium"),
        ]
        
        for error_type, error_message, expected_severity in test_cases:
            # Act
            severity = self.notifier._determine_error_severity(error_type, error_message)
            
            # Assert
            assert severity == expected_severity, f"Error type '{error_type}' should be '{expected_severity}', got '{severity}'"
    
    @pytest.mark.unit
    def test_user_friendly_error_messages(self):
        """Test generation of user-friendly error messages."""
        # Test cases for user-friendly messages
        test_cases = [
            ("timeout", "Request timeout", "test_agent", "taking longer than usual"),
            ("rate_limit", "Too many requests", "cost_optimizer", "made many requests recently"),
            ("validation", "Invalid format", "data_analyzer", "issue with your request format"),
            ("network", "Connection failed", "report_generator", "temporary connectivity issue"),
            ("database", "Query failed", "insights_agent", "temporary data access issue"),
            ("general", "Unknown error", "helper_agent", "unexpected issue"),
        ]
        
        for error_type, error_message, agent_name, expected_phrase in test_cases:
            # Act
            friendly_message = self.notifier._generate_user_friendly_error_message(
                error_type, error_message, agent_name
            )
            
            # Assert
            assert expected_phrase in friendly_message.lower(), f"Message should contain '{expected_phrase}'"
            assert agent_name in friendly_message, f"Message should contain agent name '{agent_name}'"
    
    @pytest.mark.unit
    async def test_delivery_stats_tracking(self):
        """Test delivery statistics tracking for monitoring."""
        # Arrange - add some test data
        context = AgentExecutionContext(
            agent_name="stats_agent",
            run_id=uuid.uuid4(),
            thread_id="test-thread"
        )
        
        self.notifier._mark_operation_active(context)
        self.notifier.delivery_confirmations["test-id"] = time.time()
        self.notifier.backlog_notifications["test-thread"] = time.time()
        
        # Act
        stats = await self.notifier.get_delivery_stats()
        
        # Assert - verify stats structure
        assert "queued_events" in stats
        assert "active_operations" in stats
        assert "delivery_confirmations" in stats
        assert "backlog_notifications_sent" in stats
        
        assert stats["active_operations"] == 1
        assert stats["delivery_confirmations"] == 1
        assert stats["backlog_notifications_sent"] == 1
        assert stats["queued_events"] >= 0
    
    @pytest.mark.unit
    def test_tool_context_hints_generation(self):
        """Test tool context hints for better user experience."""
        # Test cases for tool context hints
        test_cases = [
            ("search_costs", "information_retrieval", "medium"),
            ("analyze_usage", "data_processing", "long"),
            ("query_database", "database_operation", "short"),
            ("generate_report", "content_creation", "medium"),
            ("validate_data", "verification", "short"),
            ("optimize_config", "performance_tuning", "long"),
            ("export_results", "data_export", "medium"),
            ("unknown_tool", "general", "medium"),
        ]
        
        for tool_name, expected_category, expected_duration in test_cases:
            # Act
            hints = self.notifier._get_tool_context_hints(tool_name)
            
            # Assert
            assert hints["category"] == expected_category
            assert hints["expected_duration"] == expected_duration