"""Enhanced WebSocket Event Tests

Tests the improved WebSocket event emission with contextual information,
periodic updates, and actionable error messages.

Business Value: Ensures users always see meaningful progress updates, preventing abandonment.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

# Test the enhanced WebSocket functionality
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.periodic_update_manager import PeriodicUpdateManager
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.send_to_thread = AsyncMock(side_effect=self._capture_message)
        self.broadcast = AsyncMock()
    
    async def _capture_message(self, thread_id: str, message_data: dict) -> bool:
        """Capture sent messages for validation."""
        self.sent_messages.append({
            'thread_id': thread_id,
            'message': message_data,
            'timestamp': time.time()
        })
        return True
    
    def get_messages_by_type(self, message_type: str) -> list:
        """Get all messages of a specific type."""
        return [
            msg for msg in self.sent_messages 
            if msg['message'].get('type') == message_type
        ]


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager fixture."""
    return MockWebSocketManager()


@pytest.fixture  
def websocket_notifier(mock_websocket_manager):
    """WebSocket notifier with mock manager."""
    return WebSocketNotifier(mock_websocket_manager)


@pytest.fixture
def periodic_update_manager(websocket_notifier):
    """Periodic update manager fixture."""
    return PeriodicUpdateManager(websocket_notifier)


@pytest.fixture
def test_context():
    """Test execution context."""
    return AgentExecutionContext(
        run_id="test_run_123",
        agent_name="TestAgent",
        thread_id="thread_456",
        user_id="user_789",
        stream_updates=True
    )


class TestEnhancedWebSocketEvents:
    """Test enhanced WebSocket event functionality."""
    
    async def test_enhanced_agent_thinking_events(self, websocket_notifier, mock_websocket_manager, test_context):
        """Test enhanced agent thinking events with progress and context."""
        
        # Send enhanced thinking event
        await websocket_notifier.send_agent_thinking(
            test_context,
            "Analyzing user request for cost optimization",
            step_number=1,
            progress_percentage=25.0,
            estimated_remaining_ms=12000,
            current_operation="request_analysis"
        )
        
        # Validate event was sent
        thinking_messages = mock_websocket_manager.get_messages_by_type("agent_thinking")
        assert len(thinking_messages) == 1
        
        # Validate enhanced payload
        payload = thinking_messages[0]['message']['payload']
        assert payload['thought'] == "Analyzing user request for cost optimization"
        assert payload['step_number'] == 1
        assert payload['progress_percentage'] == 25.0
        assert payload['estimated_remaining_ms'] == 12000
        assert payload['current_operation'] == "request_analysis"
        assert payload['urgency'] == "medium_priority"  # 12s = medium priority
        assert 'timestamp' in payload
    
    async def test_enhanced_tool_executing_events(self, websocket_notifier, mock_websocket_manager, test_context):
        """Test enhanced tool executing events with purpose and timing."""
        
        # Send enhanced tool executing event
        await websocket_notifier.send_tool_executing(
            test_context,
            "database_query_analyzer",
            tool_purpose="Retrieving performance metrics",
            estimated_duration_ms=5000,
            parameters_summary="Query: SELECT * FROM metrics; Limit: 1000"
        )
        
        # Validate event was sent
        tool_messages = mock_websocket_manager.get_messages_by_type("tool_executing")
        assert len(tool_messages) == 1
        
        # Validate enhanced payload
        payload = tool_messages[0]['message']['payload']
        assert payload['tool_name'] == "database_query_analyzer"
        assert payload['tool_purpose'] == "Retrieving performance metrics"
        assert payload['estimated_duration_ms'] == 5000
        assert payload['parameters_summary'] == "Query: SELECT * FROM metrics; Limit: 1000"
        assert payload['execution_phase'] == "starting"
        assert payload['category'] == "database_operation"  # From context hints
        assert 'timestamp' in payload
    
    async def test_enhanced_error_events(self, websocket_notifier, mock_websocket_manager, test_context):
        """Test enhanced error events with recovery guidance."""
        
        # Send enhanced error event
        await websocket_notifier.send_agent_error(
            test_context,
            "Database connection timeout occurred",
            error_type="timeout",
            error_details={"connection_url": "postgres://...", "retry_count": 2},
            recovery_suggestions=["Check database status", "Try again in a moment"],
            is_recoverable=True,
            estimated_retry_delay_ms=5000
        )
        
        # Validate event was sent
        error_messages = mock_websocket_manager.get_messages_by_type("agent_error")
        assert len(error_messages) == 1
        
        # Validate enhanced payload
        payload = error_messages[0]['message']['payload']
        assert payload['error_message'] == "Database connection timeout occurred"
        assert payload['error_type'] == "timeout"
        assert payload['severity'] == "high"  # timeout = high severity
        assert payload['is_recoverable'] == True
        assert payload['estimated_retry_delay_ms'] == 5000
        assert "Check database status" in payload['recovery_suggestions']
        assert "The TestAgent is taking longer than usual" in payload['user_friendly_message']
        assert 'timestamp' in payload
    
    async def test_periodic_updates_for_long_operations(self, periodic_update_manager, mock_websocket_manager, test_context):
        """Test periodic updates for long-running operations."""
        
        # Track a long-running operation
        async def simulate_long_operation():
            async with periodic_update_manager.track_operation(
                test_context,
                "data_analysis",
                operation_type="data_processing",
                expected_duration_ms=8000,
                operation_description="Analyzing 50,000 data points"
            ):
                # Simulate 6 seconds of work
                await asyncio.sleep(6.0)
        
        # Run the operation with periodic updates
        await simulate_long_operation()
        
        # Validate operation started event
        started_messages = mock_websocket_manager.get_messages_by_type("operation_started")
        assert len(started_messages) == 1
        started_payload = started_messages[0]['message']['payload']
        assert started_payload['operation_name'] == "data_analysis"
        assert started_payload['operation_type'] == "data_processing"
        assert started_payload['expected_duration_ms'] == 8000
        assert started_payload['operation_description'] == "Analyzing 50,000 data points"
        
        # Validate periodic updates were sent (should be at least 1 after 6 seconds)
        periodic_messages = mock_websocket_manager.get_messages_by_type("periodic_update")
        assert len(periodic_messages) >= 1
        
        # Validate periodic update content
        if periodic_messages:
            periodic_payload = periodic_messages[0]['message']['payload']
            assert periodic_payload['operation_name'] == "data_analysis"
            assert periodic_payload['update_type'] == "periodic_progress"
            assert 'status_message' in periodic_payload
            assert 'timestamp' in periodic_payload
        
        # Validate operation completed event
        completed_messages = mock_websocket_manager.get_messages_by_type("operation_completed")
        assert len(completed_messages) == 1
        completed_payload = completed_messages[0]['message']['payload']
        assert completed_payload['operation_name'] == "data_analysis"
        assert completed_payload['status'] == "completed"
        assert completed_payload['duration_ms'] > 5000  # Should be around 6000ms
        assert 'result_summary' in completed_payload
    
    async def test_error_severity_classification(self, websocket_notifier, test_context):
        """Test error severity classification logic."""
        notifier = websocket_notifier
        
        # Test critical error
        assert notifier._determine_error_severity("database", "connection failed") == "critical"
        assert notifier._determine_error_severity("authentication", "invalid token") == "critical"
        
        # Test high error  
        assert notifier._determine_error_severity("timeout", "operation timed out") == "high"
        assert notifier._determine_error_severity("rate_limit", "too many requests") == "high"
        
        # Test medium error
        assert notifier._determine_error_severity("parsing", "invalid format") == "medium"
        assert notifier._determine_error_severity(None, "unknown error") == "medium"
    
    async def test_recovery_suggestions_generation(self, websocket_notifier, test_context):
        """Test contextual recovery suggestions generation."""
        notifier = websocket_notifier
        
        # Test timeout suggestions
        timeout_suggestions = notifier._generate_default_recovery_suggestions("timeout", "connection timeout")
        assert "operation took longer than expected" in timeout_suggestions[0].lower()
        assert "smaller parts" in " ".join(timeout_suggestions).lower()
        
        # Test rate limit suggestions
        rate_limit_suggestions = notifier._generate_default_recovery_suggestions("rate_limit", "too many requests")
        assert "rate limit" in rate_limit_suggestions[0].lower()
        assert "wait a moment" in " ".join(rate_limit_suggestions).lower()
        
        # Test validation suggestions
        validation_suggestions = notifier._generate_default_recovery_suggestions("validation", "invalid input")
        assert "check your request" in " ".join(validation_suggestions).lower()
        assert "required fields" in " ".join(validation_suggestions).lower()
    
    async def test_user_friendly_error_messages(self, websocket_notifier, test_context):
        """Test user-friendly error message generation."""
        notifier = websocket_notifier
        
        # Test different error types
        timeout_msg = notifier._generate_user_friendly_error_message("timeout", "slow query", "TestAgent")
        assert "taking longer than usual" in timeout_msg
        assert "TestAgent" in timeout_msg
        
        rate_limit_msg = notifier._generate_user_friendly_error_message("rate_limit", "quota exceeded", "TestAgent")
        assert "many requests recently" in rate_limit_msg
        
        validation_msg = notifier._generate_user_friendly_error_message("validation", "bad format", "TestAgent")
        assert "issue with your request format" in validation_msg
    
    async def test_tool_context_hints(self, websocket_notifier, test_context):
        """Test tool context hint generation."""
        notifier = websocket_notifier
        
        # Test various tool patterns
        search_hints = notifier._get_tool_context_hints("search_optimizer")
        assert search_hints['category'] == "information_retrieval"
        assert search_hints['expected_duration'] == "medium"
        
        analyze_hints = notifier._get_tool_context_hints("data_analyzer")
        assert analyze_hints['category'] == "data_processing"
        assert analyze_hints['expected_duration'] == "long"
        
        query_hints = notifier._get_tool_context_hints("database_query")
        assert query_hints['category'] == "database_operation"
        assert query_hints['expected_duration'] == "short"
    
    async def test_event_ordering_and_sequencing(self, websocket_notifier, mock_websocket_manager, test_context):
        """Test that events are sent in proper order without duplicates."""
        
        # Send a sequence of events rapidly
        events_to_send = [
            ("agent_thinking", "Starting analysis", {"step_number": 1}),
            ("tool_executing", "data_query", {"tool_purpose": "Getting data"}),
            ("agent_thinking", "Processing results", {"step_number": 2}), 
            ("tool_completed", "data_query", {"result": {"status": "success"}}),
            ("agent_thinking", "Finalizing report", {"step_number": 3}),
        ]
        
        # Send events with small delays to test ordering
        for event_type, param1, param2 in events_to_send:
            if event_type == "agent_thinking":
                await websocket_notifier.send_agent_thinking(test_context, param1, **param2)
            elif event_type == "tool_executing":
                await websocket_notifier.send_tool_executing(test_context, param1, **param2)
            elif event_type == "tool_completed":
                await websocket_notifier.send_tool_completed(test_context, param1, **param2)
            await asyncio.sleep(0.1)  # Small delay
        
        # Validate all events were sent and in order
        assert len(mock_websocket_manager.sent_messages) == 5
        
        # Check message types in order
        message_types = [msg['message']['type'] for msg in mock_websocket_manager.sent_messages]
        expected_types = ["agent_thinking", "tool_executing", "agent_thinking", "tool_completed", "agent_thinking"]
        assert message_types == expected_types
        
        # Check timestamps are sequential (within reasonable tolerance)
        timestamps = [msg['timestamp'] for msg in mock_websocket_manager.sent_messages]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], "Events not in chronological order"
    
    async def test_periodic_update_generation(self, periodic_update_manager, test_context):
        """Test contextual status message generation for periodic updates."""
        manager = periodic_update_manager
        
        # Test database operation messages
        db_message_1 = manager._generate_status_message("query_execution", "database_query", 3000, 0)
        db_message_2 = manager._generate_status_message("query_execution", "database_query", 8000, 1)
        
        assert "3s" in db_message_1
        assert "8s" in db_message_2
        assert "Querying database" in db_message_1
        assert "Processing large dataset" in db_message_2  # Different message after 1 update
        
        # Test LLM operation messages
        llm_message = manager._generate_status_message("report_generation", "llm_generation", 5000, 0)
        assert "5s" in llm_message
        assert "Generating AI response" in llm_message
        
        # Test completion summaries
        short_summary = manager._generate_completion_summary("analysis", 3000, 1)
        long_summary = manager._generate_completion_summary("analysis", 75000, 5)  # 75s
        
        assert "quickly" in short_summary
        assert "1m 15s" in long_summary

    async def test_contextual_tool_execution_info(self):
        """Test contextual tool execution information extraction."""
        from netra_backend.app.agents.enhanced_tool_execution import ContextualToolExecutor
        
        # Mock websocket manager
        mock_ws = MagicMock()
        executor = ContextualToolExecutor(mock_ws)
        
        # Test tool purpose extraction
        search_purpose = executor._get_tool_purpose("search_optimizer", None)
        assert search_purpose == "Finding relevant information"
        
        analyze_purpose = executor._get_tool_purpose("data_analyzer", None)
        assert analyze_purpose == "Performing data analysis"
        
        custom_purpose = executor._get_tool_purpose("custom_tool", None)
        assert "Executing custom_tool operation" in custom_purpose
        
        # Test duration estimation
        search_duration = executor._estimate_tool_duration("search_tool", None)
        assert search_duration == 3000  # 3 seconds
        
        analyze_duration = executor._estimate_tool_duration("analyze_performance", None)
        assert analyze_duration == 15000  # 15 seconds
        
        default_duration = executor._estimate_tool_duration("unknown_tool", None)
        assert default_duration == 5000  # Default 5 seconds
        
        # Test parameter summary creation
        mock_input = MagicMock()
        mock_input.model_dump.return_value = {
            "query": "SELECT * FROM metrics WHERE date > '2024-01-01'",
            "table_name": "performance_metrics",
            "limit": 1000,
            "filters": ["status=active", "region=us-east"]
        }
        
        summary = executor._create_parameters_summary(mock_input)
        assert "Query: SELECT * FROM metrics WHERE date >" in summary
        assert "Table: performance_metrics" in summary
        assert "Limit: 1000" in summary
        assert "Filters: 2 applied" in summary


class TestWebSocketEventReliability:
    """Test WebSocket event reliability and error handling."""
    
    async def test_graceful_websocket_failure_handling(self, test_context):
        """Test graceful handling when WebSocket manager fails."""
        
        # Create notifier with failing WebSocket manager
        failing_ws_manager = MagicMock()
        failing_ws_manager.send_to_thread = AsyncMock(side_effect=Exception("Connection lost"))
        
        notifier = WebSocketNotifier(failing_ws_manager)
        
        # Events should not raise exceptions even when WebSocket fails
        await notifier.send_agent_thinking(test_context, "Testing failure handling")
        await notifier.send_tool_executing(test_context, "test_tool")
        await notifier.send_agent_error(test_context, "Test error", "test_type")
        
        # Should complete without raising exceptions
        assert True
    
    async def test_websocket_manager_none_handling(self, test_context):
        """Test handling when WebSocket manager is None."""
        
        # Create notifier with None WebSocket manager
        notifier = WebSocketNotifier(None)
        
        # Events should be safely ignored
        await notifier.send_agent_thinking(test_context, "Testing None handling")
        await notifier.send_tool_executing(test_context, "test_tool")
        await notifier.send_periodic_update(test_context, "test_operation")
        
        # Should complete without raising exceptions
        assert True


class TestPeriodicUpdateManager:
    """Test periodic update manager functionality."""
    
    async def test_operation_tracking_lifecycle(self, periodic_update_manager, mock_websocket_manager, test_context):
        """Test full operation tracking lifecycle."""
        manager = periodic_update_manager
        
        # Simulate operation
        async def test_operation():
            async with manager.track_operation(
                test_context,
                "test_analysis",
                operation_type="data_processing",
                expected_duration_ms=3000,
                operation_description="Testing operation tracking"
            ):
                await asyncio.sleep(3.1)  # Just over 3 seconds
        
        # Execute operation
        await test_operation()
        
        # Validate events
        started_messages = mock_websocket_manager.get_messages_by_type("operation_started")
        completed_messages = mock_websocket_manager.get_messages_by_type("operation_completed")
        
        assert len(started_messages) == 1
        assert len(completed_messages) == 1
        
        # Validate started event
        started_payload = started_messages[0]['message']['payload']
        assert started_payload['operation_name'] == "test_analysis"
        assert started_payload['operation_type'] == "data_processing"
        assert started_payload['expected_duration_ms'] == 3000
        
        # Validate completed event
        completed_payload = completed_messages[0]['message']['payload']
        assert completed_payload['operation_name'] == "test_analysis"
        assert completed_payload['duration_ms'] > 3000
        assert completed_payload['status'] == "completed"
    
    async def test_forced_updates(self, periodic_update_manager, mock_websocket_manager, test_context):
        """Test forced update functionality."""
        manager = periodic_update_manager
        
        # Start tracking an operation
        operation_id = f"{test_context.run_id}_test_operation"
        manager.active_operations[operation_id] = {
            "context": test_context,
            "operation_name": "test_operation",
            "start_time": time.time(),
            "expected_duration_ms": 10000,
            "update_count": 0
        }
        
        # Force an update
        await manager.force_update(
            test_context,
            "test_operation", 
            "Reached important milestone",
            progress_percentage=50.0
        )
        
        # Validate forced update was sent
        periodic_messages = mock_websocket_manager.get_messages_by_type("periodic_update")
        assert len(periodic_messages) == 1
        
        payload = periodic_messages[0]['message']['payload']
        assert payload['status_message'] == "Reached important milestone"
        assert payload['progress_percentage'] == 50.0
        assert payload['current_step'] == "forced_update"


# Run the tests
if __name__ == "__main__":
    # Simple test runner for immediate validation
    async def run_tests():
        print("Running Enhanced WebSocket Event Tests...")
        
        # Create test fixtures
        mock_ws_manager = MockWebSocketManager()
        notifier = WebSocketNotifier(mock_ws_manager)
        update_manager = PeriodicUpdateManager(notifier)
        context = AgentExecutionContext(
            run_id="test_run",
            agent_name="TestAgent", 
            thread_id="test_thread",
            user_id="test_user",
            stream_updates=True
        )
        
        # Test enhanced thinking events
        print("Testing enhanced thinking events...")
        await notifier.send_agent_thinking(
            context, "Testing enhanced events",
            step_number=1, progress_percentage=30.0,
            estimated_remaining_ms=8000, current_operation="testing"
        )
        assert len(mock_ws_manager.sent_messages) == 1
        print("✓ Enhanced thinking events work")
        
        # Test enhanced tool events  
        print("Testing enhanced tool events...")
        await notifier.send_tool_executing(
            context, "test_analyzer",
            tool_purpose="Testing tool execution",
            estimated_duration_ms=5000,
            parameters_summary="Test parameters"
        )
        assert len(mock_ws_manager.sent_messages) == 2
        print("✓ Enhanced tool events work")
        
        # Test enhanced error events
        print("Testing enhanced error events...")
        await notifier.send_agent_error(
            context, "Test error", "timeout",
            recovery_suggestions=["Try again", "Check status"],
            is_recoverable=True
        )
        assert len(mock_ws_manager.sent_messages) == 3
        print("✓ Enhanced error events work")
        
        print("All enhanced WebSocket event tests passed!")
    
    # Run basic validation
    asyncio.run(run_tests())