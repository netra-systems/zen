"""
Unit tests for WebSocketNotifier - Testing core event creation and message building.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Chat reliability and real-time feedback
- Value Impact: Ensures WebSocket events are properly formatted for real-time user feedback
- Strategic Impact: Core component for chat UX - validates event creation without WebSocket dependencies

These tests focus on testing the deprecated WebSocketNotifier's core functionality
without requiring actual WebSocket connections or external dependencies.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class TestWebSocketNotifierCore:
    """Unit tests for WebSocketNotifier core functionality."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        mock_manager = AsyncMock()
        mock_manager.send_to_thread = AsyncMock()
        return mock_manager
    
    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocketNotifier instance with warnings suppressed."""
        with patch('warnings.warn'):  # Suppress deprecation warning in tests
            return AgentWebSocketBridge(mock_websocket_manager)
    
    @pytest.fixture
    def sample_context(self):
        """Create sample execution context."""
        return AgentExecutionContext(
            agent_name="test_agent",
            thread_id="test_thread_123",
            user_id="test_user_456",
            run_id="run_789"
        )
    
    def test_creates_agent_started_message_correctly(self, websocket_notifier, sample_context):
        """Test that agent started message is created with correct structure."""
        # Act
        message = websocket_notifier._build_started_message(sample_context)
        
        # Assert
        assert isinstance(message, WebSocketMessage)
        assert message.type == "agent_started"
        assert "agent_name" in message.payload
        assert "run_id" in message.payload
        assert "timestamp" in message.payload
        assert message.payload["agent_name"] == "test_agent"
        assert message.payload["run_id"] == "run_789"
    
    def test_builds_enhanced_thinking_payload_with_progress(self, websocket_notifier, sample_context):
        """Test enhanced thinking payload includes progress and timing information."""
        # Arrange
        thought = "Analyzing user request"
        step_number = 2
        progress_percentage = 45.5
        estimated_remaining_ms = 8000
        current_operation = "data_analysis"
        
        # Act
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, thought, step_number, progress_percentage, 
            estimated_remaining_ms, current_operation
        )
        
        # Assert
        assert payload["thought"] == thought
        assert payload["agent_name"] == "test_agent"
        assert payload["step_number"] == step_number
        assert payload["progress_percentage"] == 45.5
        assert payload["estimated_remaining_ms"] == 8000
        assert payload["current_operation"] == current_operation
        assert "urgency" in payload
        assert payload["urgency"] == "medium_priority"  # 8000ms = medium priority
    
    def test_urgency_calculation_for_thinking_payload(self, websocket_notifier, sample_context):
        """Test urgency calculation based on estimated remaining time."""
        # Test low priority (>10 seconds)
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "thinking", estimated_remaining_ms=15000
        )
        assert payload["urgency"] == "low_priority"
        
        # Test medium priority (5-10 seconds)
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "thinking", estimated_remaining_ms=7000
        )
        assert payload["urgency"] == "medium_priority"
        
        # Test high priority (<5 seconds)
        payload = websocket_notifier._build_enhanced_thinking_payload(
            sample_context, "thinking", estimated_remaining_ms=3000
        )
        assert payload["urgency"] == "high_priority"
    
    def test_builds_tool_executing_payload_with_context(self, websocket_notifier, sample_context):
        """Test tool executing payload includes tool context and hints."""
        # Arrange
        tool_name = "search_database"
        tool_purpose = "Finding relevant user data"
        estimated_duration_ms = 2500
        parameters_summary = "query: user_analytics"
        
        # Act
        payload = websocket_notifier._build_enhanced_tool_executing_payload(
            sample_context, tool_name, tool_purpose, estimated_duration_ms, parameters_summary
        )
        
        # Assert
        assert payload["tool_name"] == tool_name
        assert payload["agent_name"] == "test_agent"
        assert payload["tool_purpose"] == tool_purpose
        assert payload["estimated_duration_ms"] == estimated_duration_ms
        assert payload["parameters_summary"] == parameters_summary
        assert payload["execution_phase"] == "starting"
        
        # Should include tool context hints
        assert "category" in payload
        assert "expected_duration" in payload
    
    def test_get_tool_context_hints_categorization(self, websocket_notifier):
        """Test tool context hints provide proper categorization."""
        # Test search tools
        hints = websocket_notifier._get_tool_context_hints("search_user_data")
        assert hints["category"] == "information_retrieval"
        assert hints["expected_duration"] == "medium"
        
        # Test analyze tools  
        hints = websocket_notifier._get_tool_context_hints("analyze_performance")
        assert hints["category"] == "data_processing"
        assert hints["expected_duration"] == "long"
        
        # Test query tools
        hints = websocket_notifier._get_tool_context_hints("query_database")
        assert hints["category"] == "database_operation"
        assert hints["expected_duration"] == "short"
        
        # Test unknown tools
        hints = websocket_notifier._get_tool_context_hints("unknown_tool")
        assert hints["category"] == "general"
        assert hints["expected_duration"] == "medium"


class TestWebSocketNotifierErrorHandling:
    """Unit tests for WebSocketNotifier error handling and user-friendly messages."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return AsyncMock()
    
    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocketNotifier instance."""
        with patch('warnings.warn'):
            return AgentWebSocketBridge(mock_websocket_manager)
    
    @pytest.fixture
    def sample_context(self):
        """Create sample execution context."""
        return AgentExecutionContext(
            agent_name="cost_optimizer",
            thread_id="thread_123",
            user_id="user_456",
            run_id="run_789"
        )
    
    def test_determine_error_severity_classification(self, websocket_notifier):
        """Test error severity determination for different error types."""
        # Critical errors
        assert websocket_notifier._determine_error_severity("authentication", "auth failed") == "critical"
        assert websocket_notifier._determine_error_severity("database", "db connection lost") == "critical"
        assert websocket_notifier._determine_error_severity("network", "network timeout") == "critical"
        
        # High severity errors
        assert websocket_notifier._determine_error_severity("timeout", "request timeout") == "high"
        assert websocket_notifier._determine_error_severity("rate_limit", "too many requests") == "high"
        assert websocket_notifier._determine_error_severity("validation", "invalid input") == "high"
        
        # Medium severity (default)
        assert websocket_notifier._determine_error_severity("general", "generic error") == "medium"
        assert websocket_notifier._determine_error_severity("", "") == "medium"
        assert websocket_notifier._determine_error_severity(None, None) == "medium"
    
    def test_generate_recovery_suggestions_for_different_errors(self, websocket_notifier):
        """Test contextual recovery suggestions based on error type."""
        # Timeout errors
        suggestions = websocket_notifier._generate_default_recovery_suggestions("timeout", "operation timed out")
        assert any("longer than expected" in s for s in suggestions)
        assert any("smaller parts" in s for s in suggestions)
        
        # Rate limit errors
        suggestions = websocket_notifier._generate_default_recovery_suggestions("rate_limit", "rate limit exceeded")
        assert any("rate limit" in s for s in suggestions)
        assert any("wait a moment" in s for s in suggestions)
        
        # Validation errors
        suggestions = websocket_notifier._generate_default_recovery_suggestions("validation", "invalid parameters")
        assert any("request format" in s for s in suggestions)
        assert any("required fields" in s for s in suggestions)
        
        # Network errors
        suggestions = websocket_notifier._generate_default_recovery_suggestions("network", "connection failed")
        assert any("network connectivity" in s for s in suggestions)
        assert any("internet connection" in s for s in suggestions)
        
        # Database errors
        suggestions = websocket_notifier._generate_default_recovery_suggestions("database", "db error")
        assert any("database issue" in s for s in suggestions)
        assert any("data is safe" in s for s in suggestions)
    
    def test_generate_user_friendly_error_messages(self, websocket_notifier):
        """Test user-friendly error message generation."""
        agent_name = "cost_optimizer"
        
        # Timeout errors
        msg = websocket_notifier._generate_user_friendly_error_message("timeout", "timeout occurred", agent_name)
        assert agent_name in msg
        assert "longer than usual" in msg
        assert "high system load" in msg
        
        # Rate limit errors
        msg = websocket_notifier._generate_user_friendly_error_message("rate_limit", "rate limited", agent_name)
        assert "many requests recently" in msg
        assert "wait a moment" in msg
        
        # Validation errors
        msg = websocket_notifier._generate_user_friendly_error_message("validation", "invalid input", agent_name)
        assert "request format" in msg
        assert "check the details" in msg
        
        # Network errors
        msg = websocket_notifier._generate_user_friendly_error_message("network", "network error", agent_name)
        assert "connectivity issue" in msg
        assert "try again" in msg
        
        # Database errors
        msg = websocket_notifier._generate_user_friendly_error_message("database", "db issue", agent_name)
        assert "data access issue" in msg
        assert "information is safe" in msg
        
        # Generic errors
        msg = websocket_notifier._generate_user_friendly_error_message("unknown", "generic error", agent_name)
        assert agent_name in msg
        assert "unexpected issue" in msg


class TestWebSocketNotifierMessageBuilding:
    """Unit tests for comprehensive message building functionality."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return AsyncMock()
    
    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocketNotifier instance."""
        with patch('warnings.warn'):
            return AgentWebSocketBridge(mock_websocket_manager)
    
    @pytest.fixture
    def sample_context(self):
        """Create sample execution context."""
        return AgentExecutionContext(
            agent_name="data_analyzer",
            thread_id="thread_abc",
            user_id="user_xyz",
            run_id="run_123"
        )
    
    def test_builds_comprehensive_agent_error_payload(self, websocket_notifier, sample_context):
        """Test comprehensive agent error payload with recovery guidance."""
        # Arrange
        error_message = "Database connection failed"
        error_type = "database"
        error_details = {"connection": "localhost:5432", "retry_count": 3}
        recovery_suggestions = ["Check database status", "Verify connection settings"]
        is_recoverable = True
        estimated_retry_delay_ms = 5000
        
        # Act
        payload = websocket_notifier._build_enhanced_agent_error_payload(
            sample_context, error_message, error_type, error_details, 
            recovery_suggestions, is_recoverable, estimated_retry_delay_ms
        )
        
        # Assert
        assert payload["agent_name"] == "data_analyzer"
        assert payload["run_id"] == "run_123"
        assert payload["error_message"] == error_message
        assert payload["error_type"] == error_type
        assert payload["error_details"] == error_details
        assert payload["severity"] == "critical"  # database errors are critical
        assert payload["is_recoverable"] == is_recoverable
        assert payload["recovery_suggestions"] == recovery_suggestions
        assert payload["estimated_retry_delay_ms"] == estimated_retry_delay_ms
        assert "user_friendly_message" in payload
        assert "timestamp" in payload
    
    def test_builds_periodic_update_payload_with_progress(self, websocket_notifier, sample_context):
        """Test periodic update payload for long-running operations."""
        # Arrange
        operation_name = "large_data_analysis"
        progress_percentage = 67.5
        status_message = "Processing chunk 3 of 5"
        estimated_remaining_ms = 12000
        current_step = "data_transformation"
        
        # Act
        payload = websocket_notifier._build_periodic_update_payload(
            sample_context, operation_name, progress_percentage, status_message,
            estimated_remaining_ms, current_step
        )
        
        # Assert
        assert payload["operation_name"] == operation_name
        assert payload["agent_name"] == "data_analyzer"
        assert payload["run_id"] == "run_123"
        assert payload["progress_percentage"] == 67.5
        assert payload["status_message"] == status_message
        assert payload["estimated_remaining_ms"] == estimated_remaining_ms
        assert payload["current_step"] == current_step
        assert payload["update_type"] == "periodic_progress"
        assert "timestamp" in payload
    
    def test_builds_operation_lifecycle_payloads(self, websocket_notifier, sample_context):
        """Test operation started and completed payload building."""
        # Test operation started payload
        operation_name = "cost_optimization"
        operation_type = "analysis"
        expected_duration_ms = 30000
        operation_description = "Analyzing AWS costs for recommendations"
        
        started_payload = websocket_notifier._build_operation_started_payload(
            sample_context, operation_name, operation_type, expected_duration_ms, operation_description
        )
        
        assert started_payload["operation_name"] == operation_name
        assert started_payload["operation_type"] == operation_type
        assert started_payload["expected_duration_ms"] == expected_duration_ms
        assert started_payload["operation_description"] == operation_description
        assert started_payload["status"] == "started"
        assert started_payload["agent_name"] == "data_analyzer"
        
        # Test operation completed payload
        duration_ms = 28500.0
        result_summary = "Found 5 cost optimization opportunities"
        metrics = {"savings_identified": "$2,500", "categories_analyzed": 12}
        
        completed_payload = websocket_notifier._build_operation_completed_payload(
            sample_context, operation_name, duration_ms, result_summary, metrics
        )
        
        assert completed_payload["operation_name"] == operation_name
        assert completed_payload["duration_ms"] == duration_ms
        assert completed_payload["result_summary"] == result_summary
        assert completed_payload["metrics"] == metrics
        assert completed_payload["status"] == "completed"
        assert completed_payload["agent_name"] == "data_analyzer"
    
    def test_builds_subagent_lifecycle_payloads(self, websocket_notifier, sample_context):
        """Test sub-agent started and completed payload building."""
        subagent_name = "data_validator"
        subagent_id = "subagent_456"
        
        # Test sub-agent started payload
        started_payload = websocket_notifier._build_subagent_started_payload(
            sample_context, subagent_name, subagent_id
        )
        
        assert started_payload["subagent_name"] == subagent_name
        assert started_payload["subagent_id"] == subagent_id
        assert started_payload["parent_agent_name"] == "data_analyzer"
        assert started_payload["parent_run_id"] == "run_123"
        assert started_payload["status"] == "started"
        
        # Test sub-agent completed payload
        result = {"validation_passed": True, "issues_found": 0}
        duration_ms = 5500.0
        
        completed_payload = websocket_notifier._build_subagent_completed_payload(
            sample_context, subagent_name, subagent_id, result, duration_ms
        )
        
        assert completed_payload["subagent_name"] == subagent_name
        assert completed_payload["result"] == result
        assert completed_payload["duration_ms"] == duration_ms
        assert completed_payload["status"] == "completed"
        assert completed_payload["parent_agent_name"] == "data_analyzer"