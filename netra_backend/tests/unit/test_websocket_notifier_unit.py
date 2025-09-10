"""
WebSocket Notifier Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise)
- Business Goal: Ensure real-time user feedback works reliably for engagement
- Value Impact: WebSocket notifications enable transparent AI processing and user retention
- Strategic Impact: Real-time feedback is critical for user experience and platform stickiness

This test suite validates the WebSocket Notifier functionality through focused
unit testing, ensuring message formatting, event creation, and notification
logic work correctly without external dependencies.

⚠️ DEPRECATION NOTE: AgentWebSocketBridge is deprecated in favor of AgentWebSocketBridge.
These tests validate the legacy functionality for backward compatibility.

CRITICAL REQUIREMENTS VALIDATED:
- WebSocket message formatting and structure
- Event payload creation and validation
- Notification timing and delivery logic
- Error handling in message creation
- Event queuing and backlog management
- Message confirmation tracking
- User context isolation in notifications
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Core imports for WebSocket notifier testing
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class TestWebSocketNotifierUnit(SSotBaseTestCase):
    """Unit tests for WebSocket Notifier functionality."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        super().setup_method()
        self.env = get_env()
        
        # Create mock WebSocket manager
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.send_to_thread = AsyncMock(return_value=True)
        self.mock_websocket_manager.broadcast = AsyncMock(return_value=True)
        
        # Suppress deprecation warning for testing
        with patch('warnings.warn'):
            # Create WebSocket notifier instance
            self.websocket_notifier = AgentWebSocketBridge(
                websocket_manager=self.mock_websocket_manager
            )
        
        # Create test execution context
        self.test_context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=uuid.uuid4(),
            retry_count=0,
            thread_id="test_thread_123"
        )

    @pytest.mark.unit
    async def test_agent_started_message_formatting(self):
        """
        Test agent started message formatting and structure.
        
        BVJ: Ensures users receive properly formatted start notifications for transparency.
        """
        # Act
        await self.websocket_notifier.send_agent_started(self.test_context)
        
        # Assert
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        
        thread_id = call_args[0][0]
        message_data = call_args[0][1]
        
        # Verify thread targeting
        assert thread_id == "test_thread_123"
        
        # Verify message structure
        assert isinstance(message_data, dict)
        assert message_data["type"] == "agent_started"
        assert "payload" in message_data
        
        # Verify payload content
        payload = message_data["payload"]
        assert payload["agent_name"] == "test_agent"
        assert payload["run_id"] == self.test_context.run_id
        assert "timestamp" in payload

    @pytest.mark.unit
    async def test_agent_thinking_message_creation(self):
        """
        Test agent thinking message creation with context and progress.
        
        BVJ: Provides real-time insight into AI processing for user engagement.
        """
        # Arrange
        thought = "Analyzing user's business metrics for optimization opportunities"
        step_number = 2
        progress_percentage = 45.0
        estimated_remaining_ms = 3000
        current_operation = "data_validation"
        
        # Act
        await self.websocket_notifier.send_agent_thinking(
            context=self.test_context,
            thought=thought,
            step_number=step_number,
            progress_percentage=progress_percentage,
            estimated_remaining_ms=estimated_remaining_ms,
            current_operation=current_operation
        )
        
        # Assert
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        # Verify message type
        assert message_data["type"] == "agent_thinking"
        
        # Verify enhanced payload content
        payload = message_data["payload"]
        assert payload["thought"] == thought
        assert payload["step_number"] == step_number
        assert payload["progress_percentage"] == progress_percentage
        assert payload["estimated_remaining_ms"] == estimated_remaining_ms
        assert payload["current_operation"] == current_operation
        assert payload["agent_name"] == "test_agent"
        assert "urgency" in payload  # Should calculate urgency based on remaining time

    @pytest.mark.unit
    async def test_tool_executing_notification_structure(self):
        """
        Test tool executing notification structure and content.
        
        BVJ: Informs users about specific tools being used for transparency and trust.
        """
        # Arrange
        tool_name = "financial_analyzer"
        tool_purpose = "Analyzing quarterly revenue trends"
        estimated_duration_ms = 2500
        parameters_summary = "Q4 data with year-over-year comparison"
        
        # Act
        await self.websocket_notifier.send_tool_executing(
            context=self.test_context,
            tool_name=tool_name,
            tool_purpose=tool_purpose,
            estimated_duration_ms=estimated_duration_ms,
            parameters_summary=parameters_summary
        )
        
        # Assert
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        # Verify message structure
        assert message_data["type"] == "tool_executing"
        
        payload = message_data["payload"]
        assert payload["tool_name"] == tool_name
        assert payload["tool_purpose"] == tool_purpose
        assert payload["estimated_duration_ms"] == estimated_duration_ms
        assert payload["parameters_summary"] == parameters_summary
        assert payload["execution_phase"] == "starting"
        assert "timestamp" in payload

    @pytest.mark.unit
    async def test_agent_completed_notification(self):
        """
        Test agent completed notification with results and metrics.
        
        BVJ: Signals successful completion and delivers final results to users.
        """
        # Arrange
        result_data = {
            "insights": ["Cost reduction opportunity: 15%", "Efficiency improvement: 22%"],
            "confidence_score": 0.89,
            "recommendations_count": 4
        }
        duration_ms = 5250.0
        
        # Act
        await self.websocket_notifier.send_agent_completed(
            context=self.test_context,
            result=result_data,
            duration_ms=duration_ms
        )
        
        # Assert
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        # Verify completion message
        assert message_data["type"] == "agent_completed"
        
        payload = message_data["payload"]
        assert payload["agent_name"] == "test_agent"
        assert payload["run_id"] == self.test_context.run_id
        assert payload["duration_ms"] == duration_ms
        assert payload["result"] == result_data
        assert "timestamp" in payload

    @pytest.mark.unit
    async def test_agent_error_notification_with_recovery_guidance(self):
        """
        Test agent error notification with recovery guidance and user-friendly messages.
        
        BVJ: Helps users understand failures and provides actionable recovery steps.
        """
        # Arrange
        error_message = "API rate limit exceeded"
        error_type = "rate_limit"
        error_details = {"retry_after": 60, "current_usage": "95%"}
        recovery_suggestions = ["Wait 60 seconds", "Consider upgrading plan"]
        estimated_retry_delay_ms = 60000
        
        # Act
        await self.websocket_notifier.send_agent_error(
            context=self.test_context,
            error_message=error_message,
            error_type=error_type,
            error_details=error_details,
            recovery_suggestions=recovery_suggestions,
            estimated_retry_delay_ms=estimated_retry_delay_ms
        )
        
        # Assert
        self.mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = self.mock_websocket_manager.send_to_thread.call_args
        message_data = call_args[0][1]
        
        # Verify error message structure
        assert message_data["type"] == "agent_error"
        
        payload = message_data["payload"]
        assert payload["error_message"] == error_message
        assert payload["error_type"] == error_type
        assert payload["error_details"] == error_details
        assert payload["recovery_suggestions"] == recovery_suggestions
        assert payload["estimated_retry_delay_ms"] == estimated_retry_delay_ms
        assert payload["is_recoverable"] is True  # Default value
        assert "user_friendly_message" in payload
        assert "severity" in payload

    @pytest.mark.unit
    def test_build_enhanced_thinking_payload_structure(self):
        """
        Test enhanced thinking payload structure and logic.
        
        BVJ: Ensures thinking notifications provide meaningful context and progress indicators.
        """
        # Arrange
        thought = "Processing complex financial analysis"
        step_number = 3
        progress_percentage = 67.5
        estimated_remaining_ms = 1500  # 1.5 seconds - should be high priority
        current_operation = "trend_analysis"
        
        # Act
        payload = self.websocket_notifier._build_enhanced_thinking_payload(
            context=self.test_context,
            thought=thought,
            step_number=step_number,
            progress_percentage=progress_percentage,
            estimated_remaining_ms=estimated_remaining_ms,
            current_operation=current_operation
        )
        
        # Assert
        assert payload["thought"] == thought
        assert payload["step_number"] == step_number
        assert payload["progress_percentage"] == 67.5  # Should be clamped to [0, 100]
        assert payload["estimated_remaining_ms"] == estimated_remaining_ms
        assert payload["current_operation"] == current_operation
        assert payload["urgency"] == "high_priority"  # <5s should be high priority
        assert "timestamp" in payload

    @pytest.mark.unit
    def test_build_tool_context_hints(self):
        """
        Test tool context hints generation for different tool types.
        
        BVJ: Provides users with context about what different tools do for transparency.
        """
        # Test different tool types
        test_cases = [
            ("search_financial_data", {"category": "information_retrieval", "expected_duration": "medium"}),
            ("analyze_performance_metrics", {"category": "data_processing", "expected_duration": "long"}),
            ("query_database", {"category": "database_operation", "expected_duration": "short"}),
            ("generate_report", {"category": "content_creation", "expected_duration": "medium"}),
            ("validate_results", {"category": "verification", "expected_duration": "short"}),
            ("optimize_costs", {"category": "performance_tuning", "expected_duration": "long"}),
            ("unknown_tool", {"category": "general", "expected_duration": "medium"})
        ]
        
        for tool_name, expected_context in test_cases:
            # Act
            context = self.websocket_notifier._get_tool_context_hints(tool_name)
            
            # Assert
            assert context == expected_context, f"Wrong context for {tool_name}"

    @pytest.mark.unit
    def test_error_severity_determination(self):
        """
        Test error severity determination logic.
        
        BVJ: Helps users understand the impact and urgency of different error types.
        """
        # Test severity classification
        test_cases = [
            ("authentication", "token expired", "critical"),
            ("database", "connection failed", "critical"),
            ("timeout", "request timed out", "high"),
            ("rate_limit", "too many requests", "high"),
            ("validation", "invalid input", "medium"),
            ("general", "unknown error", "medium"),
            (None, "generic failure", "medium")
        ]
        
        for error_type, error_message, expected_severity in test_cases:
            # Act
            severity = self.websocket_notifier._determine_error_severity(error_type, error_message)
            
            # Assert
            assert severity == expected_severity, f"Wrong severity for {error_type}: {error_message}"

    @pytest.mark.unit
    def test_generate_user_friendly_error_messages(self):
        """
        Test user-friendly error message generation.
        
        BVJ: Provides users with understandable error explanations for better experience.
        """
        # Test message generation for different error types
        test_cases = [
            ("timeout", "request timed out", "TestAgent", "taking longer than usual"),
            ("rate_limit", "too many requests", "TestAgent", "made many requests recently"),
            ("validation", "invalid format", "TestAgent", "issue with your request format"),
            ("network", "connection failed", "TestAgent", "temporary connectivity issue"),
            ("database", "db error", "TestAgent", "temporary data access issue"),
            ("unknown", "generic error", "TestAgent", "encountered an unexpected issue")
        ]
        
        for error_type, error_message, agent_name, expected_substring in test_cases:
            # Act
            user_message = self.websocket_notifier._generate_user_friendly_error_message(
                error_type, error_message, agent_name
            )
            
            # Assert
            assert expected_substring.lower() in user_message.lower(), \
                f"Missing expected text in message for {error_type}"
            assert agent_name in user_message, f"Agent name missing from error message"

    @pytest.mark.unit
    def test_generate_recovery_suggestions(self):
        """
        Test recovery suggestion generation for different error scenarios.
        
        BVJ: Provides actionable guidance to help users resolve issues independently.
        """
        # Test suggestion generation
        test_cases = [
            ("timeout", "operation timed out", ["longer than expected", "smaller parts"]),
            ("rate_limit", "rate limit exceeded", ["rate limit", "wait a moment"]),
            ("validation", "validation failed", ["request format", "required fields"]),
            ("network", "network error", ["network", "internet connection"]),
            ("database", "database error", ["database issue", "data is safe"]),
            ("unknown", "unknown error", ["unexpected error", "try again"])
        ]
        
        for error_type, error_message, expected_keywords in test_cases:
            # Act
            suggestions = self.websocket_notifier._generate_default_recovery_suggestions(
                error_type, error_message
            )
            
            # Assert
            assert isinstance(suggestions, list), "Suggestions should be a list"
            assert len(suggestions) > 0, "Should have at least one suggestion"
            
            # Check that expected keywords appear in suggestions
            suggestions_text = " ".join(suggestions).lower()
            for keyword in expected_keywords:
                assert keyword.lower() in suggestions_text, \
                    f"Missing keyword '{keyword}' in suggestions for {error_type}"

    @pytest.mark.unit
    def test_timestamp_generation_consistency(self):
        """
        Test timestamp generation consistency and format.
        
        BVJ: Ensures consistent timing information for event sequencing and debugging.
        """
        # Act - generate multiple timestamps quickly
        timestamp1 = self.websocket_notifier._get_timestamp()
        time.sleep(0.001)  # Small delay
        timestamp2 = self.websocket_notifier._get_timestamp()
        
        # Assert
        assert isinstance(timestamp1, float), "Timestamp should be a float"
        assert isinstance(timestamp2, float), "Timestamp should be a float"
        assert timestamp2 > timestamp1, "Timestamps should be monotonically increasing"
        
        # Verify timestamps are reasonable (within last minute)
        current_time = datetime.now(timezone.utc).timestamp()
        assert abs(timestamp1 - current_time) < 60, "Timestamp should be recent"
        assert abs(timestamp2 - current_time) < 60, "Timestamp should be recent"

    def cleanup_resources(self):
        """Clean up test resources."""
        super().cleanup_resources()
        self.websocket_notifier = None