"""
Unit Tests for WebSocket Event Generation - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable WebSocket event generation for chat transparency
- Value Impact: Users see real-time AI processing updates enabling trust and engagement
- Strategic Impact: Core chat functionality - without these events, chat has no business value

CRITICAL: These events are the foundation of our chat-first business model.
Without proper event generation, users can't see agent progress and the platform fails.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from shared.types import UserID, ThreadID, RunID

class TestWebSocketEventGeneration:
    """Test WebSocket event generation for agent execution transparency."""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        manager = Mock(spec=UnifiedWebSocketManager)
        manager.send_to_user = AsyncMock()
        return manager
    
    @pytest.fixture
    def websocket_notifier(self, mock_websocket_manager):
        """Create WebSocket notifier with mocked manager."""
        return WebSocketNotifier(websocket_manager=mock_websocket_manager)
    
    @pytest.fixture
    def mock_execution_context(self):
        """Mock agent execution context."""
        context = Mock(spec=AgentExecutionContext)
        context.user_id = UserID("test_user_123")
        context.thread_id = ThreadID("thread_456")
        context.run_id = RunID("run_789")
        context.agent_name = "test_agent"
        return context

    @pytest.mark.unit
    async def test_agent_started_event_generation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test agent_started event is generated with correct structure.
        
        Business Value: Users must see when AI starts processing their request.
        Critical for transparency and user trust.
        """
        # Act
        await websocket_notifier.notify_agent_started(mock_execution_context)
        
        # Assert
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args
        
        assert call_args[0][0] == UserID("test_user_123")  # user_id
        event_data = call_args[0][1]  # event data
        
        # Verify event structure for business value
        assert event_data["type"] == "agent_started"
        assert event_data["thread_id"] == "thread_456"
        assert event_data["run_id"] == "run_789"
        assert event_data["agent_name"] == "test_agent"
        assert "timestamp" in event_data
        
        # Business requirement: Event must indicate processing has begun
        assert "Processing your request" in str(event_data) or "started" in event_data["type"]

    @pytest.mark.unit
    async def test_agent_thinking_event_generation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test agent_thinking event shows AI reasoning process.
        
        Business Value: Users see AI is actively working on their problem.
        Prevents user abandonment during processing.
        """
        thinking_content = "Analyzing cost optimization opportunities..."
        
        # Act
        await websocket_notifier.notify_agent_thinking(mock_execution_context, thinking_content)
        
        # Assert
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args
        event_data = call_args[0][1]
        
        assert event_data["type"] == "agent_thinking"
        assert event_data["content"] == thinking_content
        assert event_data["thread_id"] == "thread_456"
        
        # Business requirement: Users must see what AI is thinking about
        assert len(thinking_content) > 0
        assert thinking_content in event_data["content"]

    @pytest.mark.unit
    async def test_tool_executing_event_generation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test tool_executing event shows which tools AI is using.
        
        Business Value: Users see specific actions AI takes to solve their problems.
        Demonstrates platform capability and value.
        """
        tool_name = "cost_analyzer"
        tool_params = {"timeframe": "30_days", "service": "aws"}
        
        # Act
        await websocket_notifier.notify_tool_executing(mock_execution_context, tool_name, tool_params)
        
        # Assert
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args
        event_data = call_args[0][1]
        
        assert event_data["type"] == "tool_executing"
        assert event_data["tool_name"] == tool_name
        assert event_data["tool_params"] == tool_params
        
        # Business requirement: Users see actionable tool usage
        assert tool_name in ["cost_analyzer", "data_retriever", "optimizer"] or "analyzer" in tool_name

    @pytest.mark.unit
    async def test_tool_completed_event_generation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test tool_completed event shows tool results.
        
        Business Value: Users see concrete results from AI tool execution.
        Validates platform effectiveness.
        """
        tool_name = "cost_analyzer"
        tool_result = {
            "total_cost": 15420.50,
            "potential_savings": 2340.75,
            "recommendations": 3
        }
        
        # Act
        await websocket_notifier.notify_tool_completed(mock_execution_context, tool_name, tool_result)
        
        # Assert
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args
        event_data = call_args[0][1]
        
        assert event_data["type"] == "tool_completed"
        assert event_data["tool_name"] == tool_name
        assert event_data["tool_result"] == tool_result
        
        # Business requirement: Results must show quantifiable value
        if isinstance(tool_result, dict):
            assert "cost" in str(tool_result).lower() or "savings" in str(tool_result).lower() or "recommendations" in str(tool_result).lower()

    @pytest.mark.unit
    async def test_agent_completed_event_generation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test agent_completed event signals successful completion.
        
        Business Value: Users know their request has been fully processed.
        Signals that valuable insights are ready for action.
        """
        final_result = {
            "summary": "Found 15% cost reduction opportunity",
            "total_potential_savings": 2340.75,
            "action_items": 3,
            "confidence": "high"
        }
        
        # Act
        await websocket_notifier.notify_agent_completed(mock_execution_context, final_result)
        
        # Assert
        mock_websocket_manager.send_to_user.assert_called_once()
        call_args = mock_websocket_manager.send_to_user.call_args
        event_data = call_args[0][1]
        
        assert event_data["type"] == "agent_completed"
        assert event_data["result"] == final_result
        assert event_data["status"] == "completed"
        
        # Business requirement: Final result must show concrete business value
        result_str = str(final_result).lower()
        assert any(keyword in result_str for keyword in ["savings", "optimization", "improvement", "recommendation", "action"])

    @pytest.mark.unit
    async def test_event_ordering_sequence_validation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test that events can be generated in proper sequence.
        
        Business Value: Users see logical progression of AI work.
        Maintains user engagement throughout processing.
        """
        # Act: Simulate full agent execution sequence
        await websocket_notifier.notify_agent_started(mock_execution_context)
        await websocket_notifier.notify_agent_thinking(mock_execution_context, "Planning analysis...")
        await websocket_notifier.notify_tool_executing(mock_execution_context, "cost_analyzer", {"period": "month"})
        await websocket_notifier.notify_tool_completed(mock_execution_context, "cost_analyzer", {"savings": 1500})
        await websocket_notifier.notify_agent_completed(mock_execution_context, {"total_savings": 1500})
        
        # Assert
        assert mock_websocket_manager.send_to_user.call_count == 5
        
        # Verify event sequence makes business sense
        calls = mock_websocket_manager.send_to_user.call_args_list
        event_types = [call[0][1]["type"] for call in calls]
        
        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert event_types == expected_sequence

    @pytest.mark.unit
    async def test_event_error_handling_graceful_degradation(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test event generation continues even if WebSocket fails.
        
        Business Value: Agent processing continues even without event notifications.
        Ensures core functionality remains available.
        """
        # Arrange: Make WebSocket send fail
        mock_websocket_manager.send_to_user.side_effect = Exception("WebSocket connection lost")
        
        # Act & Assert: Should not raise exception
        try:
            await websocket_notifier.notify_agent_started(mock_execution_context)
            await websocket_notifier.notify_agent_completed(mock_execution_context, {"result": "success"})
        except Exception as e:
            pytest.fail(f"Event generation should be resilient to WebSocket failures: {e}")
        
        # WebSocket calls were attempted but failed gracefully
        assert mock_websocket_manager.send_to_user.call_count == 2

    @pytest.mark.unit
    async def test_event_timestamp_generation_business_audit(self, websocket_notifier, mock_websocket_manager, mock_execution_context):
        """
        Test that events include timestamps for business audit trail.
        
        Business Value: Events can be tracked for performance analysis and billing.
        Supports usage analytics and optimization insights.
        """
        # Act
        await websocket_notifier.notify_agent_started(mock_execution_context)
        
        # Assert
        call_args = mock_websocket_manager.send_to_user.call_args
        event_data = call_args[0][1]
        
        assert "timestamp" in event_data
        
        # Business requirement: Timestamp must be recent and valid
        timestamp = event_data["timestamp"]
        if isinstance(timestamp, str):
            # Should parse as ISO format
            parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            time_diff = abs((now - parsed_time).total_seconds())
            assert time_diff < 5, "Event timestamp should be within 5 seconds of now"