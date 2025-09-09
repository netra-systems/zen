#!/usr/bin/env python
"""
Unit Tests for WebSocket Manager Event Integration

MISSION CRITICAL: WebSocket manager integration that enables business chat functionality.
Tests the core integration between WebSocketManager and agent event delivery systems.

Business Value: $500K+ ARR - Core real-time communication infrastructure validation
- Tests WebSocket manager's role in delivering agent events
- Validates connection management for user-scoped WebSocket events
- Ensures proper event routing and delivery guarantees
"""

import asyncio
import json
import pytest
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketMessage

# Import production WebSocket components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
def mock_websocket_connection():
    """Create mock WebSocket connection for testing."""
    connection = AsyncMock()
    connection.send = AsyncMock()
    connection.close = AsyncMock()
    connection.closed = False
    connection.state = 1  # OPEN state
    return connection


@pytest.fixture
def mock_user_context():
    """Create mock user execution context."""
    context = MagicMock(spec=UserExecutionContext)
    context.user_id = UserID("test_user_123")
    context.thread_id = ThreadID("test_thread_456")
    context.request_id = RequestID("test_request_789")
    context.session_id = "test_session_abc"
    return context


class TestUnifiedWebSocketManager:
    """Unit tests for UnifiedWebSocketManager event delivery integration."""
    
    @pytest.mark.asyncio
    async def test_manager_sends_agent_started_event_to_user(self, mock_websocket_connection, mock_user_context):
        """
        Test UnifiedWebSocketManager sends agent_started event to correct user.
        
        CRITICAL: agent_started events must reach the right user for chat functionality.
        Cross-user contamination would break multi-user isolation.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        user_id = "test_user_123"
        
        # Mock user connection
        manager._user_connections = {user_id: [mock_websocket_connection]}
        
        # Create agent_started event
        agent_event = {
            "type": WebSocketEventType.AGENT_STARTED.value,
            "data": {
                "agent": "optimization_agent",
                "status": "starting",
                "timestamp": datetime.now().isoformat()
            },
            "user_id": user_id,
            "thread_id": "test_thread_456",
            "message_id": "msg_agent_start_123"
        }
        
        # Act
        result = await manager.send_to_user(user_id, agent_event)
        
        # Assert
        assert result is True, "Agent started event must be delivered to user"
        
        # Verify WebSocket connection received the event
        mock_websocket_connection.send.assert_called_once()
        sent_message = mock_websocket_connection.send.call_args[0][0]
        parsed_message = json.loads(sent_message)
        
        assert parsed_message["type"] == WebSocketEventType.AGENT_STARTED.value
        assert parsed_message["data"]["agent"] == "optimization_agent"
        assert parsed_message["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_manager_sends_tool_executing_event_to_thread(self, mock_websocket_connection, mock_user_context):
        """
        Test UnifiedWebSocketManager sends tool_executing event to correct thread.
        
        CRITICAL: tool_executing events provide real-time tool transparency.
        Thread isolation ensures users only see their own tool executions.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        thread_id = "test_thread_456"
        user_id = "test_user_123"
        
        # Mock thread-to-user mapping and user connection
        manager._thread_to_user = {thread_id: user_id}
        manager._user_connections = {user_id: [mock_websocket_connection]}
        
        # Create tool_executing event
        tool_event = {
            "type": WebSocketEventType.TOOL_EXECUTING.value,
            "data": {
                "tool": "data_analyzer",
                "args": {"query": "SELECT * FROM metrics", "limit": 100},
                "status": "executing",
                "timestamp": datetime.now().isoformat()
            },
            "thread_id": thread_id,
            "user_id": user_id,
            "message_id": "msg_tool_exec_456"
        }
        
        # Act
        result = await manager.send_to_thread(thread_id, tool_event)
        
        # Assert
        assert result is True, "Tool executing event must be delivered to thread"
        
        # Verify WebSocket connection received the event
        mock_websocket_connection.send.assert_called_once()
        sent_message = mock_websocket_connection.send.call_args[0][0]
        parsed_message = json.loads(sent_message)
        
        assert parsed_message["type"] == WebSocketEventType.TOOL_EXECUTING.value
        assert parsed_message["data"]["tool"] == "data_analyzer"
        assert parsed_message["thread_id"] == thread_id
    
    @pytest.mark.asyncio
    async def test_manager_handles_multiple_user_connections(self, mock_user_context):
        """
        Test UnifiedWebSocketManager handles multiple connections per user.
        
        CRITICAL: Users may have multiple browser tabs/devices connected.
        All connections must receive agent events for seamless experience.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        user_id = "test_user_123"
        
        # Create multiple mock connections for same user
        connection1 = AsyncMock()
        connection1.send = AsyncMock()
        connection1.closed = False
        
        connection2 = AsyncMock()
        connection2.send = AsyncMock()
        connection2.closed = False
        
        connection3 = AsyncMock()
        connection3.send = AsyncMock()
        connection3.closed = False
        
        manager._user_connections = {user_id: [connection1, connection2, connection3]}
        
        # Create agent_completed event
        completion_event = {
            "type": WebSocketEventType.AGENT_COMPLETED.value,
            "data": {
                "agent": "triage_agent",
                "result": {
                    "analysis": "User needs optimization recommendations",
                    "next_steps": ["data_analysis", "optimization_strategy"]
                },
                "status": "completed"
            },
            "user_id": user_id,
            "message_id": "msg_agent_complete_789"
        }
        
        # Act
        result = await manager.send_to_user(user_id, completion_event)
        
        # Assert
        assert result is True, "Agent completed event must reach all user connections"
        
        # Verify all connections received the event
        connection1.send.assert_called_once()
        connection2.send.assert_called_once()
        connection3.send.assert_called_once()
        
        # Verify all connections got the same message
        for connection in [connection1, connection2, connection3]:
            sent_message = connection.send.call_args[0][0]
            parsed_message = json.loads(sent_message)
            assert parsed_message["type"] == WebSocketEventType.AGENT_COMPLETED.value
            assert parsed_message["data"]["agent"] == "triage_agent"
    
    @pytest.mark.asyncio
    async def test_manager_skips_closed_connections(self, mock_user_context):
        """
        Test UnifiedWebSocketManager skips closed/failed connections.
        
        CRITICAL: Failed connections must not break event delivery to healthy connections.
        System must be resilient to individual connection failures.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        user_id = "test_user_123"
        
        # Create healthy and failed connections
        healthy_connection = AsyncMock()
        healthy_connection.send = AsyncMock()
        healthy_connection.closed = False
        
        closed_connection = AsyncMock()
        closed_connection.send = AsyncMock()
        closed_connection.closed = True  # Connection is closed
        
        failed_connection = AsyncMock()
        failed_connection.send = AsyncMock(side_effect=Exception("Connection failed"))
        failed_connection.closed = False
        
        manager._user_connections = {user_id: [healthy_connection, closed_connection, failed_connection]}
        
        # Create agent_thinking event
        thinking_event = {
            "type": WebSocketEventType.AGENT_THINKING.value,
            "data": {
                "agent": "data_researcher",
                "progress": "Analyzing data requirements",
                "stage": "initial_analysis"
            },
            "user_id": user_id,
            "message_id": "msg_thinking_999"
        }
        
        # Act
        result = await manager.send_to_user(user_id, thinking_event)
        
        # Assert
        assert result is True, "Event delivery succeeds if at least one connection is healthy"
        
        # Verify only healthy connection received the event
        healthy_connection.send.assert_called_once()
        
        # Verify closed connection was skipped (not called)
        closed_connection.send.assert_not_called()
        
        # Verify failed connection was attempted but failed
        failed_connection.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manager_returns_false_when_no_user_connections(self, mock_user_context):
        """
        Test UnifiedWebSocketManager returns False when user has no connections.
        
        CRITICAL: System must clearly indicate when events cannot be delivered.
        This enables fallback mechanisms like email notifications.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        user_id = "offline_user_456"
        
        # No connections for this user
        manager._user_connections = {}
        
        # Create tool_completed event
        tool_event = {
            "type": WebSocketEventType.TOOL_COMPLETED.value,
            "data": {
                "tool": "cost_analyzer",
                "result": {"monthly_savings": 5000, "confidence": 0.92},
                "status": "completed"
            },
            "user_id": user_id,
            "message_id": "msg_offline_123"
        }
        
        # Act
        result = await manager.send_to_user(user_id, tool_event)
        
        # Assert
        assert result is False, "Event delivery must return False when user is offline"


class TestAgentWebSocketBridgeIntegration:
    """Unit tests for AgentWebSocketBridge integration with WebSocket manager."""
    
    @pytest.mark.asyncio
    async def test_bridge_initializes_with_websocket_manager(self, mock_user_context):
        """
        Test AgentWebSocketBridge properly initializes with WebSocket manager.
        
        CRITICAL: Bridge must be properly connected to WebSocket manager for event delivery.
        Improper initialization breaks all real-time chat functionality.
        """
        # Arrange
        mock_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_manager.is_healthy.return_value = True
        
        # Act
        bridge = AgentWebSocketBridge(mock_manager)
        
        # Assert
        assert bridge.websocket_manager is mock_manager
        assert bridge.is_healthy() is True
        
        # Verify bridge can access manager methods
        assert hasattr(bridge.websocket_manager, 'send_to_user')
        assert hasattr(bridge.websocket_manager, 'send_to_thread')
    
    @pytest.mark.asyncio
    async def test_bridge_factory_creates_with_websocket_manager(self, mock_user_context):
        """
        Test create_agent_websocket_bridge factory properly creates bridge with manager.
        
        CRITICAL: Factory pattern ensures consistent bridge creation across all agents.
        Factory must properly inject WebSocket manager for event delivery.
        """
        # Arrange
        mock_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_manager.is_healthy.return_value = True
        
        # Mock the factory's WebSocket manager discovery
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', 
                  return_value=mock_manager):
            
            # Act
            bridge = create_agent_websocket_bridge(mock_user_context)
            
            # Assert
            assert bridge is not None
            assert hasattr(bridge, 'websocket_manager')
            assert bridge.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_bridge_emits_all_required_events_through_manager(self, mock_user_context):
        """
        Test AgentWebSocketBridge emits all 5 REQUIRED events through WebSocket manager.
        
        CRITICAL: All 5 events must flow through the bridge to the manager.
        Missing events break the chat experience and business value delivery.
        """
        # Arrange
        mock_manager = AsyncMock(spec=UnifiedWebSocketManager)
        mock_manager.send_to_thread.return_value = True
        mock_manager.is_healthy.return_value = True
        
        bridge = AgentWebSocketBridge(mock_manager)
        
        # Required events for chat business value
        required_events = [
            ("agent_started", {"agent": "triage", "status": "starting"}),
            ("agent_thinking", {"agent": "triage", "progress": "analyzing request"}),
            ("tool_executing", {"tool": "data_query", "status": "executing"}),
            ("tool_completed", {"tool": "data_query", "result": {"data": "analysis"}}),
            ("agent_completed", {"agent": "triage", "status": "completed", "result": "done"})
        ]
        
        # Act & Assert - Test each required event
        for event_type, event_data in required_events:
            mock_manager.reset_mock()
            
            result = await bridge.emit_event(
                context=mock_user_context,
                event_type=event_type,
                event_data=event_data
            )
            
            assert result is True, f"Bridge must successfully emit {event_type} event"
            
            # Verify manager was called
            mock_manager.send_to_thread.assert_called_once()
            call_args = mock_manager.send_to_thread.call_args
            thread_id, message = call_args[0]
            
            assert thread_id == "test_thread_456"
            assert message["type"] == event_type
            assert message["data"] == event_data
    
    @pytest.mark.asyncio
    async def test_bridge_handles_manager_failure_gracefully(self, mock_user_context):
        """
        Test AgentWebSocketBridge handles WebSocket manager failures gracefully.
        
        CRITICAL: Bridge failures must not crash agent execution.
        Agents must continue working even if WebSocket delivery fails.
        """
        # Arrange
        failing_manager = AsyncMock(spec=UnifiedWebSocketManager)
        failing_manager.send_to_thread.side_effect = Exception("WebSocket manager failure")
        failing_manager.is_healthy.return_value = False
        
        bridge = AgentWebSocketBridge(failing_manager)
        
        # Act
        result = await bridge.emit_event(
            context=mock_user_context,
            event_type="agent_started",
            event_data={"agent": "test", "status": "starting"}
        )
        
        # Assert
        assert result is False, "Bridge should return False when manager fails"
        assert bridge.is_healthy() is False, "Bridge should report unhealthy when manager fails"
        
        # Verify manager was attempted
        failing_manager.send_to_thread.assert_called_once()


class TestWebSocketEventRouting:
    """Unit tests for WebSocket event routing and delivery guarantees."""
    
    @pytest.mark.asyncio
    async def test_user_id_routing_isolation(self, mock_websocket_connection):
        """
        Test WebSocket events are properly isolated by user_id.
        
        CRITICAL: User isolation prevents cross-user event contamination.
        Breaking this security boundary would leak user data.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        
        # Set up connections for different users
        user1_connection = AsyncMock()
        user1_connection.send = AsyncMock()
        user1_connection.closed = False
        
        user2_connection = AsyncMock()
        user2_connection.send = AsyncMock()
        user2_connection.closed = False
        
        manager._user_connections = {
            "user_123": [user1_connection],
            "user_456": [user2_connection]
        }
        
        # Create event for user1
        user1_event = {
            "type": WebSocketEventType.AGENT_STARTED.value,
            "data": {"agent": "user1_agent", "status": "starting"},
            "user_id": "user_123",
            "message_id": "user1_msg"
        }
        
        # Act
        result = await manager.send_to_user("user_123", user1_event)
        
        # Assert
        assert result is True, "Event delivery must succeed for target user"
        
        # Verify only user1 received the event
        user1_connection.send.assert_called_once()
        user2_connection.send.assert_not_called()
        
        # Verify event content
        sent_message = user1_connection.send.call_args[0][0]
        parsed_message = json.loads(sent_message)
        assert parsed_message["user_id"] == "user_123"
        assert parsed_message["data"]["agent"] == "user1_agent"
    
    @pytest.mark.asyncio
    async def test_thread_id_routing_isolation(self, mock_websocket_connection):
        """
        Test WebSocket events are properly isolated by thread_id.
        
        CRITICAL: Thread isolation ensures users only see events from their conversations.
        Cross-thread contamination would mix different user conversations.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        
        # Set up thread-to-user mappings and connections
        manager._thread_to_user = {
            "thread_123": "user_aaa",
            "thread_456": "user_bbb"
        }
        
        user_aaa_connection = AsyncMock()
        user_aaa_connection.send = AsyncMock()
        user_aaa_connection.closed = False
        
        user_bbb_connection = AsyncMock()
        user_bbb_connection.send = AsyncMock()
        user_bbb_connection.closed = False
        
        manager._user_connections = {
            "user_aaa": [user_aaa_connection],
            "user_bbb": [user_bbb_connection]
        }
        
        # Create event for thread_123 (belongs to user_aaa)
        thread_event = {
            "type": WebSocketEventType.TOOL_EXECUTING.value,
            "data": {"tool": "analyzer", "status": "executing"},
            "thread_id": "thread_123",
            "message_id": "thread_msg"
        }
        
        # Act
        result = await manager.send_to_thread("thread_123", thread_event)
        
        # Assert
        assert result is True, "Event delivery must succeed for target thread"
        
        # Verify only user_aaa (owner of thread_123) received the event
        user_aaa_connection.send.assert_called_once()
        user_bbb_connection.send.assert_not_called()
        
        # Verify event routing
        sent_message = user_aaa_connection.send.call_args[0][0]
        parsed_message = json.loads(sent_message)
        assert parsed_message["thread_id"] == "thread_123"
    
    @pytest.mark.asyncio
    async def test_event_serialization_preserves_all_fields(self):
        """
        Test WebSocket event serialization preserves all required fields.
        
        CRITICAL: Event serialization must preserve all data for frontend parsing.
        Lost fields break chat UI functionality and user experience.
        """
        # Arrange
        manager = UnifiedWebSocketManager()
        
        # Create comprehensive event with all fields
        complete_event = {
            "type": WebSocketEventType.AGENT_COMPLETED.value,
            "data": {
                "agent": "optimization_agent",
                "result": {
                    "summary": "Analysis complete",
                    "metrics": {"savings": 10000, "confidence": 0.95},
                    "recommendations": ["optimize_storage", "reduce_compute"]
                },
                "status": "completed",
                "execution_time_ms": 5000
            },
            "user_id": "test_user_123",
            "thread_id": "test_thread_456",
            "request_id": "test_request_789",
            "message_id": "msg_complete_123",
            "timestamp": datetime.now().isoformat()
        }
        
        # Act - Serialize and deserialize
        serialized = json.dumps(complete_event)
        deserialized = json.loads(serialized)
        
        # Assert - All fields preserved
        required_fields = ["type", "data", "user_id", "thread_id", "message_id", "timestamp"]
        for field in required_fields:
            assert field in deserialized, f"Required field {field} missing after serialization"
            assert deserialized[field] == complete_event[field], f"Field {field} value changed"
        
        # Assert - Nested data preserved
        assert deserialized["data"]["agent"] == "optimization_agent"
        assert deserialized["data"]["result"]["summary"] == "Analysis complete"
        assert deserialized["data"]["result"]["metrics"]["savings"] == 10000
        assert len(deserialized["data"]["result"]["recommendations"]) == 2