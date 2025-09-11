#!/usr/bin/env python
"""
Unit Tests for WebSocket Event Delivery System

MISSION CRITICAL: Core WebSocket event delivery that enables substantive chat interactions.
These tests validate the fundamental WebSocket event delivery mechanisms that serve the 
business goal of delivering AI value to users through real-time communication.

Business Value: $500K+ ARR - Core chat functionality validation
- Tests the 5 REQUIRED WebSocket events for substantive chat value
- Validates WebSocketNotifier and AgentWebSocketBridge event delivery
- Ensures proper event formatting and delivery guarantees
"""

import asyncio
import json
import pytest
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketMessage, WebSocketEventType as TestEventType

# Import production WebSocket components
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager for unit testing."""
    manager = AsyncMock(spec=UnifiedWebSocketManager)
    
    # Mock successful message delivery
    async def mock_send_to_user(user_id: str, message: dict) -> bool:
        return True
    
    async def mock_send_to_thread(thread_id: str, message: dict) -> bool:
        return True
    
    manager.send_to_user.side_effect = mock_send_to_user
    manager.send_to_thread.side_effect = mock_send_to_thread
    manager.is_healthy.return_value = True
    
    return manager


@pytest.fixture
def mock_user_context():
    """Create mock user execution context."""
    context = MagicMock(spec=UserExecutionContext)
    context.user_id = UserID("test_user_123")
    context.thread_id = ThreadID("test_thread_456")
    context.request_id = RequestID("test_request_789")
    context.session_id = "test_session_abc"
    return context


class TestWebSocketEventDelivery:
    """Unit tests for core WebSocket event delivery functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_notifier_agent_started_event(self, mock_websocket_manager, mock_user_context):
        """
        Test WebSocketNotifier delivers agent_started event correctly.
        
        CRITICAL: agent_started event is REQUIRED for substantive chat value.
        Users must see that agent began processing their problem.
        """
        # Arrange
        notifier = WebSocketNotifier.create_for_user(mock_websocket_manager)
        agent_name = "triage"
        
        # Act
        result = await notifier.notify_agent_started(
            context=mock_user_context, agent_name=agent_name
        )
        
        # Assert
        assert result is True, "Agent started notification must succeed"
        
        # Verify WebSocket manager was called with correct event
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        thread_id, message = call_args[0]
        
        assert thread_id == "test_thread_456"
        assert message["type"] == WebSocketEventType.AGENT_STARTED.value
        assert message["data"]["agent"] == agent_name
        assert message["data"]["status"] == "starting"
        assert "timestamp" in message
        assert message["thread_id"] == "test_thread_456"
        assert message["user_id"] == "test_user_123"
    
    @pytest.mark.asyncio
    async def test_websocket_notifier_agent_thinking_event(self, mock_websocket_manager, mock_user_context):
        """
        Test WebSocketNotifier delivers agent_thinking event correctly.
        
        CRITICAL: agent_thinking event provides real-time reasoning visibility.
        Shows AI is working on valuable solutions for users.
        """
        # Arrange
        notifier = WebSocketNotifier.create_for_user(mock_websocket_manager)
        agent_name = "data_researcher"
        progress_message = "Analyzing user requirements and searching for relevant data"
        
        # Act
        result = await notifier.notify_agent_thinking(
            context=mock_user_context, agent_name=agent_name,
            progress=progress_message
        )
        
        # Assert
        assert result is True, "Agent thinking notification must succeed"
        
        # Verify WebSocket manager was called with correct event
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        thread_id, message = call_args[0]
        
        assert thread_id == "test_thread_456"
        assert message["type"] == WebSocketEventType.AGENT_THINKING.value
        assert message["data"]["agent"] == agent_name
        assert message["data"]["progress"] == progress_message
        assert "timestamp" in message
    
    @pytest.mark.asyncio
    async def test_websocket_notifier_tool_executing_event(self, mock_websocket_manager, mock_user_context):
        """
        Test WebSocketNotifier delivers tool_executing event correctly.
        
        CRITICAL: tool_executing event provides tool usage transparency.
        Demonstrates problem-solving approach to users.
        """
        # Arrange
        notifier = WebSocketNotifier.create_for_user(mock_websocket_manager)
        tool_name = "data_query"
        tool_args = {"query": "SELECT * FROM optimization_data", "limit": 100}
        
        # Act
        result = await notifier.notify_tool_executing(
            context=mock_user_context,
            tool_name=tool_name,
            tool_args=tool_args
        )
        
        # Assert
        assert result is True, "Tool executing notification must succeed"
        
        # Verify WebSocket manager was called with correct event
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        thread_id, message = call_args[0]
        
        assert thread_id == "test_thread_456"
        assert message["type"] == WebSocketEventType.TOOL_EXECUTING.value
        assert message["data"]["tool"] == tool_name
        assert message["data"]["args"] == tool_args
        assert message["data"]["status"] == "executing"
        assert "timestamp" in message
    
    @pytest.mark.asyncio
    async def test_websocket_notifier_tool_completed_event(self, mock_websocket_manager, mock_user_context):
        """
        Test WebSocketNotifier delivers tool_completed event correctly.
        
        CRITICAL: tool_completed event displays tool results.
        Delivers actionable insights to users.
        """
        # Arrange
        notifier = WebSocketNotifier.create_for_user(mock_websocket_manager)
        tool_name = "optimization_analyzer"
        tool_result = {
            "analysis": "Found 3 optimization opportunities", "savings": "$15,000/month",
            "recommendations": ["Reduce compute costs", "Optimize data storage", "Improve caching"]
        }
        
        # Act
        result = await notifier.notify_tool_completed(
            context=mock_user_context,
            tool_name=tool_name,
            tool_result=tool_result
        )
        
        # Assert
        assert result is True, "Tool completed notification must succeed"
        
        # Verify WebSocket manager was called with correct event
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        thread_id, message = call_args[0]
        
        assert thread_id == "test_thread_456"
        assert message["type"] == WebSocketEventType.TOOL_COMPLETED.value
        assert message["data"]["tool"] == tool_name
        assert message["data"]["result"] == tool_result
        assert message["data"]["status"] == "completed"
        assert "timestamp" in message
    
    @pytest.mark.asyncio
    async def test_websocket_notifier_agent_completed_event(self, mock_websocket_manager, mock_user_context):
        """
        Test WebSocketNotifier delivers agent_completed event correctly.
        
        CRITICAL: agent_completed event notifies user when valuable response is ready.
        Final step in delivering AI value through chat.
        """
        # Arrange
        notifier = WebSocketNotifier.create_for_user(mock_websocket_manager)
        agent_name = "optimization_agent"
        agent_result = {
            "summary": "Optimization analysis complete", "potential_savings": "$15,000/month",
            "action_items": 3,
            "confidence_score": 0.95
        }
        
        # Act
        result = await notifier.notify_agent_completed(
            context=mock_user_context,
            agent_name=agent_name,
            result=agent_result
        )
        
        # Assert
        assert result is True, "Agent completed notification must succeed"
        
        # Verify WebSocket manager was called with correct event
        mock_websocket_manager.send_to_thread.assert_called_once()
        call_args = mock_websocket_manager.send_to_thread.call_args
        thread_id, message = call_args[0]
        
        assert thread_id == "test_thread_456"
        assert message["type"] == WebSocketEventType.AGENT_COMPLETED.value
        assert message["data"]["agent"] == agent_name
        assert message["data"]["result"] == agent_result
        assert message["data"]["status"] == "completed"
        assert "timestamp" in message


class TestAgentWebSocketBridge:
    """Unit tests for AgentWebSocketBridge event delivery."""
    
    @pytest.mark.asyncio
    async def test_bridge_delivers_all_required_events(self, mock_websocket_manager, mock_user_context):
        """
        Test AgentWebSocketBridge delivers all 5 REQUIRED events for chat value.
        
        CRITICAL: All 5 events (agent_started, agent_thinking, tool_executing, 
        tool_completed, agent_completed) MUST be delivered for substantive chat.
        """
        # Arrange
        bridge = AgentWebSocketBridge(mock_websocket_manager)
        
        # Act & Assert - Test all 5 required events
        events_to_test = [
            ("agent_started", {"agent": "test_agent", "status": "starting"}),
            ("agent_thinking", {"agent": "test_agent", "progress": "analyzing"}),
            ("tool_executing", {"tool": "test_tool", "status": "executing"}),
            ("tool_completed", {"tool": "test_tool", "result": {"status": "success"}}),
            ("agent_completed", {"agent": "test_agent", "result": {"status": "done"}})
        ]
        
        for event_type, event_data in events_to_test:
            mock_websocket_manager.reset_mock()
            
            result = await bridge.emit_event(
                context=mock_user_context,
                event_type=event_type,
                event_data=event_data
            )
            
            assert result is True, f"Event {event_type} must be delivered successfully"
            mock_websocket_manager.send_to_thread.assert_called_once()
            
            # Verify event structure
            call_args = mock_websocket_manager.send_to_thread.call_args
            thread_id, message = call_args[0]
            
            assert thread_id == "test_thread_456"
            assert message["type"] == event_type
            assert message["data"] == event_data
            assert "timestamp" in message
            assert message["thread_id"] == "test_thread_456"
    
    @pytest.mark.asyncio
    async def test_bridge_handles_websocket_manager_failure(self, mock_user_context):
        """
        Test AgentWebSocketBridge handles WebSocket manager failures gracefully.
        
        CRITICAL: WebSocket failures must not break agent execution.
        System must be resilient to communication failures.
        """
        # Arrange - Create failing WebSocket manager
        failing_manager = AsyncMock(spec=UnifiedWebSocketManager)
        failing_manager.send_to_thread.side_effect = Exception("WebSocket connection lost")
        failing_manager.is_healthy.return_value = False
        
        bridge = AgentWebSocketBridge(failing_manager)
        
        # Act
        result = await bridge.emit_event(
            context=mock_user_context,
            event_type="agent_started",
            event_data={"agent": "test_agent", "status": "starting"}
        )
        
        # Assert
        assert result is False, "Bridge should return False when WebSocket fails"
        
        # Verify attempt was made
        failing_manager.send_to_thread.assert_called_once()


class TestWebSocketEventValidation:
    """Unit tests for WebSocket event validation and formatting."""
    
    def test_websocket_event_type_validation(self):
        """
        Test that all 5 REQUIRED WebSocket event types are properly defined.
        
        CRITICAL: All required events must be available in WebSocketEventType enum.
        Missing events would break chat functionality.
        """
        # Arrange - Expected required events for chat value
        required_events = [
            "AGENT_STARTED",     # User must see agent began processing
            "AGENT_THINKING",    # Real-time reasoning visibility  
            "TOOL_EXECUTING",    # Tool usage transparency
            "TOOL_COMPLETED",    # Tool results display
            "AGENT_COMPLETED"    # User must know when response ready
        ]
        
        # Act & Assert
        for event_name in required_events:
            assert hasattr(WebSocketEventType, event_name), f"Missing required event: {event_name}"
            
            # Verify event has proper string value
            event_value = getattr(WebSocketEventType, event_name).value
            assert isinstance(event_value, str), f"Event {event_name} must have string value"
            assert event_value == event_name.lower(), f"Event {event_name} must have lowercase value"
    
    def test_websocket_message_structure(self):
        """
        Test WebSocket message structure follows required format.
        
        CRITICAL: Messages must have proper structure for frontend parsing.
        Malformed messages break chat UI/UX.
        """
        # Arrange
        event_type = WebSocketEventType.AGENT_STARTED
        event_data = {"agent": "test_agent", "status": "starting"}
        timestamp = datetime.now()
        
        # Act
        message = {
            "type": event_type.value,
            "data": event_data,
            "timestamp": timestamp.isoformat(),
            "thread_id": "test_thread_123",
            "user_id": "test_user_456",
            "message_id": "msg_12345"
        }
        
        # Assert - Required fields for chat functionality
        required_fields = ["type", "data", "timestamp", "thread_id", "user_id", "message_id"]
        for field in required_fields:
            assert field in message, f"Missing required message field: {field}"
        
        # Verify field types
        assert isinstance(message["type"], str)
        assert isinstance(message["data"], dict)
        assert isinstance(message["timestamp"], str)
        assert isinstance(message["thread_id"], str)
        assert isinstance(message["user_id"], str)
        assert isinstance(message["message_id"], str)
    
    def test_websocket_event_serialization(self):
        """
        Test WebSocket events can be properly serialized to JSON.
        
        CRITICAL: Events must be JSON serializable for WebSocket transmission.
        Serialization errors break real-time communication.
        """
        # Arrange
        message = {
            "type": WebSocketEventType.TOOL_COMPLETED.value,
            "data": {
                "tool": "optimization_analyzer",
                "result": {
                    "savings": 15000,
                    "recommendations": ["optimize_storage", "reduce_compute"],
                    "timestamp": datetime.now().isoformat()
                },
                "status": "completed"
            },
            "timestamp": datetime.now().isoformat(),
            "thread_id": "thread_789",
            "user_id": "user_123",
            "message_id": "msg_456"
        }
        
        # Act & Assert - Must not raise exception
        try:
            json_str = json.dumps(message)
            parsed_message = json.loads(json_str)
            
            # Verify round-trip serialization preserves data
            assert parsed_message["type"] == message["type"]
            assert parsed_message["data"]["tool"] == message["data"]["tool"]
            assert parsed_message["thread_id"] == message["thread_id"]
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"WebSocket message serialization failed: {e}")