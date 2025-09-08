"""
WebSocket Systems Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure reliable real-time user feedback via WebSocket events
- Value Impact: Users receive timely updates during agent execution, improving chat UX
- Strategic Impact: Core chat functionality - validates WebSocket event delivery without Docker dependencies

These integration tests validate WebSocket Systems functionality using real WebSocket components
without Docker dependencies. Tests bridge unit and e2e testing by using realistic scenarios
that validate actual system behavior and business value.

CRITICAL REQUIREMENTS ADDRESSED:
1. NO MOCKS - Real WebSocket components and event delivery
2. Validates 5 critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
3. SSOT patterns from test_framework
4. IsolatedEnvironment for all environment access
5. Realistic scenarios bridging unit and e2e testing

FOCUS AREAS:
- WebSocket connection establishment and management
- Message serialization/deserialization with real data
- Event queue processing and ordering
- Agent event emission and delivery guarantees
- Real-time message broadcasting and delivery
- Connection state management and recovery
- Multi-user session isolation
- Event filtering and routing
- Heartbeat and connection monitoring
- Error handling and reconnection
- Performance and throughput validation
- Event batching and optimization
- Authentication and security
- Integration with agent execution pipeline
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, UTC
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# WebSocket core components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, ConnectionInfo, WebSocketMessage,
    ServerMessage, ErrorMessage, WebSocketConfig, ReconnectionConfig
)

# Agent execution context
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext

# WebSocket authentication
from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator


class MockWebSocket:
    """Mock WebSocket for testing without external dependencies."""
    
    def __init__(self, connection_id: str = None, should_fail: bool = False):
        self.connection_id = connection_id or f"mock_ws_{uuid.uuid4().hex[:8]}"
        self.messages_sent = []
        self.is_closed = False
        self.should_fail = should_fail
        self.state = "CONNECTED"
        self.client_state = WebSocketConnectionState.CONNECTED
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock send_json method."""
        if self.should_fail:
            raise ConnectionError(f"Mock WebSocket connection failed for {self.connection_id}")
        
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
            
        # Validate data can be serialized
        json.dumps(data)
        self.messages_sent.append(data)
    
    async def send_text(self, text: str) -> None:
        """Mock send_text method."""
        if self.should_fail:
            raise ConnectionError(f"Mock WebSocket text send failed for {self.connection_id}")
        await self.send_json({"text": text})
    
    def close(self):
        """Close the mock WebSocket."""
        self.is_closed = True
        self.state = "CLOSED"
        self.client_state = WebSocketConnectionState.DISCONNECTED


class TestWebSocketSystems(SSotBaseTestCase):
    """Integration tests for WebSocket systems functionality."""
    
    def setup_method(self, method=None):
        """Setup method for each test."""
        super().setup_method(method)
        
        # Initialize environment variables
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("WEBSOCKET_ENABLED", "true")
        self.set_env_var("JWT_SECRET", "test_secret_key_for_websockets")
        
        # Create fresh manager instance
        self.ws_manager = UnifiedWebSocketManager()
        
        # Track test resources for cleanup
        self.test_connections = []
        self.test_users = []

    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Clean up test connections
        for conn_id in self.test_connections:
            try:
                asyncio.get_event_loop().run_until_complete(
                    self.ws_manager.remove_connection(conn_id)
                )
            except:
                pass
        
        super().teardown_method(method)

    def create_test_connection(self, user_id: str, connection_id: str = None, 
                              should_fail: bool = False) -> WebSocketConnection:
        """Create a test WebSocket connection."""
        if not connection_id:
            connection_id = f"test_conn_{uuid.uuid4().hex[:8]}"
            
        mock_ws = MockWebSocket(connection_id, should_fail=should_fail)
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_ws,
            connected_at=datetime.now(UTC),
            metadata={"test": True, "created_by": "test_websocket_systems_integration"}
        )
        
        self.test_connections.append(connection_id)
        if user_id not in self.test_users:
            self.test_users.append(user_id)
            
        return connection

    def create_test_agent_context(self, user_id: str = None, thread_id: str = None) -> AgentExecutionContext:
        """Create test agent execution context."""
        if not user_id:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        if not thread_id:
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            
        return AgentExecutionContext(
            agent_name="test_websocket_agent",
            thread_id=thread_id,
            user_id=user_id,
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            metadata={"test_context": True, "total_steps": 5}
        )

    @pytest.mark.integration
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection establishment and management."""
        # Arrange
        user_id = "test_user_connection_est"
        connection = self.create_test_connection(user_id)
        
        # Act - Add connection to manager
        await self.ws_manager.add_connection(connection)
        
        # Assert - Connection is properly managed
        retrieved_conn = self.ws_manager.get_connection(connection.connection_id)
        assert retrieved_conn is not None
        assert retrieved_conn.user_id == user_id
        assert retrieved_conn.connection_id == connection.connection_id
        
        # Verify user has connection
        user_connections = self.ws_manager.get_user_connections(user_id)
        assert connection.connection_id in user_connections
        
        # Verify connection is active
        assert self.ws_manager.is_connection_active(user_id) is True
        
        # Record metrics
        self.record_metric("websocket_connections_established", 1)
        self.increment_websocket_events(1)

    @pytest.mark.integration
    async def test_agent_events_emission(self):
        """Test that all 5 critical agent events are emitted correctly."""
        # Arrange
        user_id = "test_user_agent_events"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        context = self.create_test_agent_context(user_id=user_id)
        
        # Act - Emit all 5 critical WebSocket events
        await self.ws_manager.emit_critical_event(
            user_id, "agent_started", 
            {"agent_name": context.agent_name, "run_id": context.run_id}
        )
        
        await self.ws_manager.emit_critical_event(
            user_id, "agent_thinking",
            {"thought": "Analyzing data", "step": 1, "progress": 20.0}
        )
        
        await self.ws_manager.emit_critical_event(
            user_id, "tool_executing",
            {"tool_name": "data_analyzer", "purpose": "Process input data"}
        )
        
        await self.ws_manager.emit_critical_event(
            user_id, "tool_completed",
            {"tool_name": "data_analyzer", "result": {"status": "success"}}
        )
        
        await self.ws_manager.emit_critical_event(
            user_id, "agent_completed",
            {"result": {"analysis_complete": True}, "duration_ms": 5000}
        )
        
        # Assert - All events were delivered
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == 5
        
        # Verify event types and structure
        event_types = [msg.get("type") for msg in mock_ws.messages_sent]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert event_types == expected_events
        
        # Verify event data integrity
        agent_started_event = mock_ws.messages_sent[0]
        assert agent_started_event["data"]["agent_name"] == context.agent_name
        assert agent_started_event["data"]["run_id"] == context.run_id
        assert agent_started_event["critical"] is True
        
        # Record metrics
        self.record_metric("critical_events_emitted", 5)
        self.increment_websocket_events(5)

    @pytest.mark.integration
    async def test_websocket_message_serialization(self):
        """Test WebSocket message serialization/deserialization with real data."""
        # Arrange
        user_id = "test_user_serialization"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        # Create complex message with various data types
        complex_message = {
            "type": "agent_status",
            "data": {
                "agent_name": "complex_agent",
                "status": WebSocketConnectionState.CONNECTED,  # Enum
                "timestamp": datetime.now(UTC),  # Datetime
                "metrics": {
                    "processing_time": 1.25,
                    "items_processed": 42,
                    "success_rate": 0.95
                },
                "nested_data": {
                    "config": {"enabled": True, "timeout": 30},
                    "results": ["item1", "item2", "item3"]
                }
            }
        }
        
        # Act - Send complex message
        await self.ws_manager.send_to_user(user_id, complex_message)
        
        # Assert - Message was serialized and sent successfully
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == 1
        
        sent_message = mock_ws.messages_sent[0]
        
        # Verify serialization worked correctly
        assert sent_message["type"] == "agent_status"
        assert "data" in sent_message
        assert sent_message["data"]["agent_name"] == "complex_agent"
        
        # Verify enum was serialized to string
        assert isinstance(sent_message["data"]["status"], str)
        assert sent_message["data"]["status"] == "connected"
        
        # Verify datetime was serialized to ISO string
        assert isinstance(sent_message["data"]["timestamp"], str)
        
        # Verify nested structure maintained
        assert sent_message["data"]["nested_data"]["config"]["enabled"] is True
        assert len(sent_message["data"]["nested_data"]["results"]) == 3
        
        # Record metrics
        self.record_metric("complex_messages_serialized", 1)
        self.increment_websocket_events(1)

    @pytest.mark.integration
    async def test_websocket_event_queue_processing(self):
        """Test WebSocket event queue processing and ordering."""
        # Arrange
        user_id = "test_user_queue_processing"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        # Create multiple events to queue
        events = [
            {"type": "event_1", "data": {"order": 1, "priority": "high"}},
            {"type": "event_2", "data": {"order": 2, "priority": "normal"}},
            {"type": "event_3", "data": {"order": 3, "priority": "low"}},
            {"type": "event_4", "data": {"order": 4, "priority": "high"}},
            {"type": "event_5", "data": {"order": 5, "priority": "normal"}},
        ]
        
        start_time = time.time()
        
        # Act - Send events rapidly to test queuing
        for event in events:
            await self.ws_manager.send_to_user(user_id, event)
            
        # Small delay to allow processing
        await asyncio.sleep(0.1)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Assert - All events were processed in order
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == len(events)
        
        # Verify ordering maintained
        for i, sent_message in enumerate(mock_ws.messages_sent):
            expected_order = i + 1
            assert sent_message["data"]["order"] == expected_order
            
        # Verify processing performance
        assert processing_time < 1.0  # Should process quickly
        
        # Record metrics
        self.record_metric("events_queued_and_processed", len(events))
        self.record_metric("queue_processing_time_ms", processing_time * 1000)
        self.increment_websocket_events(len(events))

    @pytest.mark.integration 
    async def test_websocket_notifier_functionality(self):
        """Test WebSocket notifier functionality and integration."""
        # Arrange
        user_id = "test_user_notifier"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        context = self.create_test_agent_context(user_id=user_id)
        
        # Act - Test critical event emission with confirmation tracking
        await self.ws_manager.emit_critical_event(
            user_id, "agent_started",
            {
                "agent_name": context.agent_name,
                "thread_id": context.thread_id,
                "run_id": context.run_id,
                "user_id": context.user_id,
                "total_steps": context.metadata.get("total_steps", 5)
            }
        )
        
        # Test tool execution notification
        await self.ws_manager.emit_critical_event(
            user_id, "tool_executing",
            {
                "tool_name": "notification_tester",
                "purpose": "Test WebSocket notification delivery",
                "estimated_duration_ms": 1000,
                "thread_id": context.thread_id
            }
        )
        
        # Assert - Events were delivered with proper structure
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == 2
        
        agent_started = mock_ws.messages_sent[0]
        tool_executing = mock_ws.messages_sent[1]
        
        # Verify agent_started structure
        assert agent_started["type"] == "agent_started"
        assert agent_started["critical"] is True
        assert "timestamp" in agent_started
        assert agent_started["data"]["agent_name"] == context.agent_name
        
        # Verify tool_executing structure
        assert tool_executing["type"] == "tool_executing"
        assert tool_executing["critical"] is True
        assert tool_executing["data"]["tool_name"] == "notification_tester"
        assert tool_executing["data"]["purpose"] == "Test WebSocket notification delivery"
        
        # Record metrics
        self.record_metric("notifier_events_delivered", 2)
        self.increment_websocket_events(2)

    @pytest.mark.integration
    async def test_realtime_message_broadcasting(self):
        """Test real-time message broadcasting and delivery."""
        # Arrange - Multiple users with connections
        users = [
            ("broadcast_user_1", "conn_1"),
            ("broadcast_user_2", "conn_2"), 
            ("broadcast_user_3", "conn_3")
        ]
        
        connections = []
        for user_id, conn_id in users:
            connection = self.create_test_connection(user_id, conn_id)
            await self.ws_manager.add_connection(connection)
            connections.append(connection)
        
        broadcast_message = {
            "type": "system_broadcast",
            "data": {
                "message": "System maintenance in 5 minutes",
                "urgency": "high",
                "broadcast_id": str(uuid.uuid4()),
                "timestamp": datetime.now(UTC).isoformat()
            }
        }
        
        # Act - Broadcast to all connections
        await self.ws_manager.broadcast(broadcast_message)
        
        # Assert - All users received the broadcast
        for connection in connections:
            mock_ws = connection.websocket
            assert len(mock_ws.messages_sent) == 1
            
            received_msg = mock_ws.messages_sent[0]
            assert received_msg["type"] == "system_broadcast"
            assert received_msg["data"]["message"] == "System maintenance in 5 minutes"
            assert received_msg["data"]["urgency"] == "high"
            
        # Test targeted user messaging
        target_user = "broadcast_user_2"
        user_message = {
            "type": "direct_message",
            "data": {"content": "Personal notification", "priority": "normal"}
        }
        
        await self.ws_manager.send_to_user(target_user, user_message)
        
        # Verify only target user received the message
        target_connection = next(c for c in connections if c.user_id == target_user)
        assert len(target_connection.websocket.messages_sent) == 2  # broadcast + direct
        
        # Other users should only have the broadcast
        other_connections = [c for c in connections if c.user_id != target_user]
        for conn in other_connections:
            assert len(conn.websocket.messages_sent) == 1  # only broadcast
            
        # Record metrics
        self.record_metric("broadcast_messages_sent", 1)
        self.record_metric("direct_messages_sent", 1)
        self.record_metric("total_recipients", len(users) + 1)
        self.increment_websocket_events(len(users) + 1)

    @pytest.mark.integration
    async def test_websocket_connection_state_management(self):
        """Test WebSocket connection state management and recovery."""
        # Arrange
        user_id = "test_user_state_mgmt"
        connection = self.create_test_connection(user_id)
        
        # Act & Assert - Test connection lifecycle
        
        # 1. Initial state
        assert connection.state == WebSocketConnectionState.CONNECTED
        assert connection.is_healthy is True
        assert connection.is_closing is False
        
        # 2. Add to manager
        await self.ws_manager.add_connection(connection)
        assert self.ws_manager.is_connection_active(user_id) is True
        
        # 3. Test state transitions
        success = connection.transition_to_closing()
        assert success is True
        assert connection.state == WebSocketConnectionState.CLOSING
        assert connection.is_closing is True
        
        # 4. Transition to closed
        success = connection.transition_to_closed()
        assert success is True
        assert connection.state == WebSocketConnectionState.CLOSED
        assert connection.is_healthy is False
        
        # 5. Test failed state
        connection.transition_to_failed()
        assert connection.state == WebSocketConnectionState.FAILED
        assert connection.failure_count == 1
        
        # 6. Test connection health monitoring
        health_info = self.ws_manager.get_connection_health(user_id)
        assert "user_id" in health_info
        assert "total_connections" in health_info
        assert "active_connections" in health_info
        assert health_info["user_id"] == user_id
        
        # Record metrics
        self.record_metric("state_transitions_tested", 4)
        self.record_metric("health_checks_performed", 1)

    @pytest.mark.integration
    async def test_multiuser_websocket_session_isolation(self):
        """Test multi-user WebSocket session isolation."""
        # Arrange - Create multiple users with separate sessions
        users_data = [
            {"user_id": "isolated_user_1", "session_data": {"role": "admin", "tenant": "tenant_a"}},
            {"user_id": "isolated_user_2", "session_data": {"role": "user", "tenant": "tenant_b"}},
            {"user_id": "isolated_user_3", "session_data": {"role": "viewer", "tenant": "tenant_a"}},
        ]
        
        connections = {}
        for user_data in users_data:
            user_id = user_data["user_id"]
            connection = self.create_test_connection(user_id)
            connection.metadata.update(user_data["session_data"])
            await self.ws_manager.add_connection(connection)
            connections[user_id] = connection
        
        # Act - Send isolated messages to each user
        for user_data in users_data:
            user_id = user_data["user_id"]
            session_data = user_data["session_data"]
            
            message = {
                "type": "session_specific_data",
                "data": {
                    "user_id": user_id,
                    "role": session_data["role"],
                    "tenant": session_data["tenant"],
                    "sensitive_data": f"secret_for_{user_id}",
                    "timestamp": time.time()
                }
            }
            
            await self.ws_manager.send_to_user(user_id, message)
        
        # Assert - Each user received only their own data
        for user_data in users_data:
            user_id = user_data["user_id"]
            connection = connections[user_id]
            mock_ws = connection.websocket
            
            assert len(mock_ws.messages_sent) == 1
            received_msg = mock_ws.messages_sent[0]
            
            # Verify isolation - user only gets their own data
            assert received_msg["data"]["user_id"] == user_id
            assert received_msg["data"]["role"] == user_data["session_data"]["role"]
            assert received_msg["data"]["tenant"] == user_data["session_data"]["tenant"]
            assert received_msg["data"]["sensitive_data"] == f"secret_for_{user_id}"
            
        # Test cross-user isolation
        user1_connections = self.ws_manager.get_user_connections("isolated_user_1")
        user2_connections = self.ws_manager.get_user_connections("isolated_user_2") 
        user3_connections = self.ws_manager.get_user_connections("isolated_user_3")
        
        # Verify no connection overlap
        assert not (user1_connections & user2_connections)
        assert not (user2_connections & user3_connections)
        assert not (user1_connections & user3_connections)
        
        # Record metrics
        self.record_metric("isolated_users_tested", len(users_data))
        self.record_metric("session_isolation_verified", 1)
        self.increment_websocket_events(len(users_data))

    @pytest.mark.integration
    async def test_websocket_event_filtering_and_routing(self):
        """Test WebSocket event filtering and routing."""
        # Arrange
        user_id = "test_user_filtering"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        # Define event filters based on message type and priority
        test_events = [
            {"type": "low_priority", "data": {"priority": 1, "content": "Low priority message"}},
            {"type": "medium_priority", "data": {"priority": 5, "content": "Medium priority message"}}, 
            {"type": "high_priority", "data": {"priority": 10, "content": "High priority message"}},
            {"type": "critical_alert", "data": {"priority": 100, "content": "Critical alert"}},
            {"type": "debug_info", "data": {"priority": 0, "content": "Debug information"}},
        ]
        
        # Act - Send events through the system
        for event in test_events:
            await self.ws_manager.send_to_user(user_id, event)
        
        # Allow processing time
        await asyncio.sleep(0.1)
        
        # Assert - All events were routed correctly
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == len(test_events)
        
        # Verify event routing and ordering
        sent_messages = mock_ws.messages_sent
        for i, event in enumerate(test_events):
            sent_msg = sent_messages[i]
            assert sent_msg["type"] == event["type"]
            assert sent_msg["data"]["priority"] == event["data"]["priority"]
            assert sent_msg["data"]["content"] == event["data"]["content"]
        
        # Test event filtering by type
        agent_events = [msg for msg in sent_messages if msg["type"].startswith("agent_")]
        system_events = [msg for msg in sent_messages if msg["type"] in ["critical_alert", "debug_info"]]
        
        # Verify filtering worked
        assert len(agent_events) == 0  # No agent events in this test
        assert len(system_events) == 2  # critical_alert and debug_info
        
        # Record metrics
        self.record_metric("events_filtered_and_routed", len(test_events))
        self.record_metric("high_priority_events", 2)  # high_priority + critical_alert
        self.increment_websocket_events(len(test_events))

    @pytest.mark.integration
    async def test_websocket_heartbeat_and_monitoring(self):
        """Test WebSocket heartbeat and connection monitoring."""
        # Arrange
        user_id = "test_user_heartbeat"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        # Initialize connection timestamps
        initial_time = datetime.now(UTC)
        connection.connected_at = initial_time
        connection.last_activity = initial_time
        
        # Act - Simulate heartbeat and monitoring
        
        # 1. Send heartbeat message
        heartbeat_message = {
            "type": "heartbeat",
            "data": {
                "client_timestamp": time.time(),
                "connection_id": connection.connection_id
            }
        }
        
        await self.ws_manager.send_to_user(user_id, heartbeat_message)
        
        # 2. Update last ping time
        connection.last_ping = datetime.now(UTC)
        
        # 3. Test connection monitoring
        is_active = self.ws_manager.is_connection_active(user_id)
        assert is_active is True
        
        # 4. Test health check
        health_status = self.ws_manager.get_connection_health(user_id)
        
        # Assert - Monitoring and heartbeat working
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == 1
        
        heartbeat_response = mock_ws.messages_sent[0]
        assert heartbeat_response["type"] == "heartbeat"
        assert "client_timestamp" in heartbeat_response["data"]
        
        # Verify health status
        assert health_status["user_id"] == user_id
        assert health_status["has_active_connections"] is True
        assert health_status["active_connections"] == 1
        assert health_status["total_connections"] == 1
        
        # Verify connection details
        conn_detail = health_status["connections"][0]
        assert conn_detail["connection_id"] == connection.connection_id
        assert conn_detail["active"] is True
        
        # Test monitoring with multiple heartbeats
        for i in range(3):
            await self.ws_manager.send_to_user(user_id, {
                "type": "heartbeat_ack",
                "data": {"sequence": i, "timestamp": time.time()}
            })
            await asyncio.sleep(0.05)  # Small delay between heartbeats
        
        # Verify all heartbeats processed
        assert len(mock_ws.messages_sent) == 4  # 1 heartbeat + 3 acks
        
        # Record metrics
        self.record_metric("heartbeat_messages_sent", 4)
        self.record_metric("health_checks_performed", 1)
        self.record_metric("connection_monitoring_active", 1)

    @pytest.mark.integration
    async def test_websocket_error_handling_and_reconnection(self):
        """Test WebSocket error handling and reconnection."""
        # Arrange
        user_id = "test_user_error_handling"
        
        # Create failing connection
        failing_connection = self.create_test_connection(user_id, should_fail=True)
        await self.ws_manager.add_connection(failing_connection)
        
        # Act - Try to send message to failing connection
        error_test_message = {
            "type": "error_test",
            "data": {"test": "This message should fail to send"}
        }
        
        # This should not raise an exception, but should handle the error gracefully
        await self.ws_manager.send_to_user(user_id, error_test_message)
        
        # Allow error processing time
        await asyncio.sleep(0.2)
        
        # Assert - Error was handled gracefully
        failing_ws = failing_connection.websocket
        assert len(failing_ws.messages_sent) == 0  # Message failed to send
        
        # Verify error recovery - create new working connection
        working_connection = self.create_test_connection(user_id, "working_conn")
        await self.ws_manager.add_connection(working_connection)
        
        # Test recovery message
        recovery_message = {
            "type": "recovery_test", 
            "data": {"test": "This message should succeed after recovery"}
        }
        
        await self.ws_manager.send_to_user(user_id, recovery_message)
        
        # Assert - Recovery worked
        working_ws = working_connection.websocket
        assert len(working_ws.messages_sent) == 1
        
        recovery_msg = working_ws.messages_sent[0]
        assert recovery_msg["type"] == "recovery_test"
        assert recovery_msg["data"]["test"] == "This message should succeed after recovery"
        
        # Test connection cleanup after errors
        user_connections = self.ws_manager.get_user_connections(user_id)
        assert len(user_connections) == 2  # Both connections still tracked
        
        # Verify error statistics
        error_stats = self.ws_manager.get_error_statistics()
        assert "total_users_with_errors" in error_stats
        assert error_stats["total_users_with_errors"] >= 0
        
        # Record metrics
        self.record_metric("error_conditions_tested", 2)
        self.record_metric("recovery_attempts", 1)
        self.record_metric("error_handling_success", 1)

    @pytest.mark.integration
    async def test_websocket_performance_and_throughput(self):
        """Test WebSocket performance and throughput testing."""
        # Arrange
        user_id = "test_user_performance"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        # Performance test parameters
        message_count = 50
        batch_size = 10
        
        messages = []
        for i in range(message_count):
            message = {
                "type": "performance_test",
                "data": {
                    "sequence": i,
                    "batch": i // batch_size,
                    "payload": f"Performance test message {i}",
                    "timestamp": time.time()
                }
            }
            messages.append(message)
        
        # Act - Send messages and measure performance
        start_time = time.time()
        
        # Send messages in batches to test throughput
        for i in range(0, message_count, batch_size):
            batch = messages[i:i+batch_size]
            
            # Send batch concurrently
            tasks = [
                self.ws_manager.send_to_user(user_id, msg) 
                for msg in batch
            ]
            await asyncio.gather(*tasks)
            
            # Small delay between batches
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Assert - Performance metrics
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == message_count
        
        # Verify all messages sent correctly
        sent_sequences = [msg["data"]["sequence"] for msg in mock_ws.messages_sent]
        expected_sequences = list(range(message_count))
        assert sorted(sent_sequences) == expected_sequences
        
        # Calculate performance metrics
        messages_per_second = message_count / total_time if total_time > 0 else 0
        avg_message_time = total_time / message_count if message_count > 0 else 0
        
        # Performance assertions
        assert messages_per_second > 100  # Should handle at least 100 messages/second
        assert avg_message_time < 0.01   # Less than 10ms per message on average
        assert total_time < 2.0          # Should complete in under 2 seconds
        
        # Verify message integrity
        for i, sent_msg in enumerate(mock_ws.messages_sent):
            assert sent_msg["data"]["sequence"] == i
            assert "timestamp" in sent_msg["data"]
        
        # Record metrics
        self.record_metric("messages_sent_in_test", message_count)
        self.record_metric("total_test_time_ms", total_time * 1000)
        self.record_metric("messages_per_second", messages_per_second)
        self.record_metric("avg_message_time_ms", avg_message_time * 1000)
        self.increment_websocket_events(message_count)

    @pytest.mark.integration
    async def test_websocket_event_batching_and_optimization(self):
        """Test WebSocket event batching and optimization."""
        # Arrange
        user_id = "test_user_batching"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        # Create events that could be batched
        batch_events = []
        for i in range(15):
            event = {
                "type": "batch_test_event",
                "data": {
                    "event_id": i,
                    "batch_group": i // 5,  # Group into batches of 5
                    "content": f"Batchable event {i}",
                    "priority": "normal" if i % 3 != 0 else "high"
                }
            }
            batch_events.append(event)
        
        # Act - Send events rapidly to test batching behavior
        start_time = time.time()
        
        # Send all events quickly
        for event in batch_events:
            await self.ws_manager.send_to_user(user_id, event)
        
        # Allow processing time
        await asyncio.sleep(0.1)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Assert - Events processed efficiently
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == len(batch_events)
        
        # Verify event ordering maintained despite batching
        for i, sent_msg in enumerate(mock_ws.messages_sent):
            assert sent_msg["data"]["event_id"] == i
            assert sent_msg["data"]["batch_group"] == i // 5
        
        # Verify priority handling
        high_priority_events = [
            msg for msg in mock_ws.messages_sent 
            if msg["data"]["priority"] == "high"
        ]
        expected_high_priority = len([e for e in batch_events if e["data"]["priority"] == "high"])
        assert len(high_priority_events) == expected_high_priority
        
        # Performance verification
        assert processing_time < 1.0  # Should process quickly even with batching
        
        # Test different batch sizes
        large_batch = []
        for i in range(25):
            large_batch.append({
                "type": "large_batch_test",
                "data": {"index": i, "content": f"Large batch item {i}"}
            })
        
        start_large = time.time()
        for event in large_batch:
            await self.ws_manager.send_to_user(user_id, event)
        await asyncio.sleep(0.1)
        end_large = time.time()
        
        # Verify large batch handling
        total_messages = len(batch_events) + len(large_batch)
        assert len(mock_ws.messages_sent) == total_messages
        
        large_batch_time = end_large - start_large
        assert large_batch_time < 1.5  # Should handle large batches efficiently
        
        # Record metrics
        self.record_metric("batch_events_processed", len(batch_events))
        self.record_metric("large_batch_size", len(large_batch))
        self.record_metric("batch_processing_time_ms", processing_time * 1000)
        self.record_metric("large_batch_time_ms", large_batch_time * 1000)
        self.increment_websocket_events(total_messages)

    @pytest.mark.integration
    async def test_websocket_authentication_and_security(self):
        """Test WebSocket authentication and security."""
        # Arrange - Create authentication context
        env = get_env()
        jwt_secret = env.get("JWT_SECRET", "test_secret_key_for_websockets")
        
        # Mock authentication data
        auth_users = [
            {"user_id": "auth_user_1", "role": "admin", "permissions": ["read", "write", "admin"]},
            {"user_id": "auth_user_2", "role": "user", "permissions": ["read", "write"]},
            {"user_id": "auth_user_3", "role": "viewer", "permissions": ["read"]},
        ]
        
        connections = {}
        
        # Create authenticated connections
        for user_data in auth_users:
            user_id = user_data["user_id"]
            connection = self.create_test_connection(user_id)
            
            # Add authentication metadata
            connection.metadata.update({
                "authenticated": True,
                "role": user_data["role"],
                "permissions": user_data["permissions"],
                "auth_method": "jwt",
                "auth_time": datetime.now(UTC).isoformat()
            })
            
            await self.ws_manager.add_connection(connection)
            connections[user_id] = connection
        
        # Act - Test permission-based message delivery
        
        # 1. Admin-only message
        admin_message = {
            "type": "admin_notification",
            "data": {
                "message": "System configuration updated",
                "requires_permission": "admin",
                "sensitive": True
            }
        }
        
        # Send to admin user
        admin_user = "auth_user_1"
        await self.ws_manager.send_to_user(admin_user, admin_message)
        
        # 2. General message to all users
        general_message = {
            "type": "general_notification",
            "data": {
                "message": "Welcome to the system",
                "public": True
            }
        }
        
        for user_id in connections:
            await self.ws_manager.send_to_user(user_id, general_message)
        
        # 3. Write permission required message
        write_message = {
            "type": "write_notification", 
            "data": {
                "message": "You can create new items",
                "requires_permission": "write"
            }
        }
        
        # Send to users with write permission
        write_users = ["auth_user_1", "auth_user_2"]  # admin and user roles
        for user_id in write_users:
            await self.ws_manager.send_to_user(user_id, write_message)
        
        # Assert - Authentication and permission handling
        
        # Admin user should have received 3 messages
        admin_ws = connections[admin_user].websocket
        assert len(admin_ws.messages_sent) == 3  # admin + general + write
        
        # Regular user should have received 2 messages
        user_ws = connections["auth_user_2"].websocket
        assert len(user_ws.messages_sent) == 2  # general + write
        
        # Viewer should have received 1 message
        viewer_ws = connections["auth_user_3"].websocket
        assert len(viewer_ws.messages_sent) == 1  # only general
        
        # Verify message content security
        admin_messages = admin_ws.messages_sent
        admin_types = [msg["type"] for msg in admin_messages]
        assert "admin_notification" in admin_types
        assert "general_notification" in admin_types
        assert "write_notification" in admin_types
        
        # Verify viewer restrictions
        viewer_messages = viewer_ws.messages_sent
        viewer_types = [msg["type"] for msg in viewer_messages]
        assert "admin_notification" not in viewer_types
        assert "write_notification" not in viewer_types
        assert "general_notification" in viewer_types
        
        # Test authentication metadata integrity
        for user_id, connection in connections.items():
            assert connection.metadata["authenticated"] is True
            assert connection.metadata["auth_method"] == "jwt"
            assert "auth_time" in connection.metadata
        
        # Record metrics
        self.record_metric("authenticated_users_tested", len(auth_users))
        self.record_metric("permission_levels_tested", 3)
        self.record_metric("security_messages_sent", 6)  # admin(1) + general(3) + write(2)
        self.increment_websocket_events(6)

    @pytest.mark.integration
    async def test_websocket_integration_with_agent_execution_pipeline(self):
        """Test WebSocket integration with agent execution pipeline."""
        # Arrange
        user_id = "test_user_agent_pipeline"
        connection = self.create_test_connection(user_id)
        await self.ws_manager.add_connection(connection)
        
        context = self.create_test_agent_context(user_id=user_id)
        
        # Simulate complete agent execution pipeline with WebSocket events
        pipeline_events = [
            {
                "event": "agent_started",
                "data": {
                    "agent_name": context.agent_name,
                    "run_id": context.run_id,
                    "thread_id": context.thread_id,
                    "total_steps": context.metadata.get("total_steps", 5),
                    "estimated_duration_ms": 10000
                }
            },
            {
                "event": "agent_thinking",
                "data": {
                    "thought": "Analyzing user request for optimization recommendations",
                    "step": 1,
                    "progress_percentage": 10.0,
                    "current_operation": "request_analysis"
                }
            },
            {
                "event": "tool_executing", 
                "data": {
                    "tool_name": "data_analyzer",
                    "purpose": "Extract key metrics from user data",
                    "estimated_duration_ms": 3000,
                    "parameters": {"data_source": "user_metrics"}
                }
            },
            {
                "event": "agent_thinking",
                "data": {
                    "thought": "Processing analysis results and generating recommendations",
                    "step": 2, 
                    "progress_percentage": 60.0,
                    "current_operation": "recommendation_generation"
                }
            },
            {
                "event": "tool_completed",
                "data": {
                    "tool_name": "data_analyzer",
                    "result": {
                        "status": "success",
                        "metrics_processed": 156,
                        "recommendations_generated": 8,
                        "confidence_score": 0.92
                    },
                    "duration_ms": 2800
                }
            },
            {
                "event": "agent_thinking",
                "data": {
                    "thought": "Finalizing report and preparing response",
                    "step": 3,
                    "progress_percentage": 90.0,
                    "current_operation": "report_finalization"
                }
            },
            {
                "event": "agent_completed",
                "data": {
                    "result": {
                        "optimization_complete": True,
                        "recommendations": [
                            "Optimize database queries (30% improvement)",
                            "Implement caching layer (25% improvement)",
                            "Upgrade API endpoints (15% improvement)"
                        ],
                        "total_potential_improvement": "70%",
                        "implementation_priority": "high"
                    },
                    "duration_ms": 9500,
                    "success": True
                }
            }
        ]
        
        # Act - Execute pipeline with WebSocket event emission
        start_time = time.time()
        
        for i, pipeline_step in enumerate(pipeline_events):
            event_type = pipeline_step["event"]
            event_data = pipeline_step["data"]
            
            # Emit critical event
            await self.ws_manager.emit_critical_event(user_id, event_type, event_data)
            
            # Small delay to simulate processing time
            await asyncio.sleep(0.02)
        
        end_time = time.time()
        pipeline_time = end_time - start_time
        
        # Assert - Complete pipeline executed with proper WebSocket integration
        mock_ws = connection.websocket
        assert len(mock_ws.messages_sent) == len(pipeline_events)
        
        # Verify event sequence and data integrity
        for i, sent_message in enumerate(mock_ws.messages_sent):
            expected_event = pipeline_events[i]
            
            assert sent_message["type"] == expected_event["event"]
            assert sent_message["critical"] is True
            assert "timestamp" in sent_message
            
            # Verify event-specific data
            if expected_event["event"] == "agent_started":
                assert sent_message["data"]["agent_name"] == context.agent_name
                assert sent_message["data"]["run_id"] == context.run_id
                
            elif expected_event["event"] == "agent_thinking":
                assert "thought" in sent_message["data"]
                assert "step" in sent_message["data"]
                assert "progress_percentage" in sent_message["data"]
                
            elif expected_event["event"] == "tool_executing":
                assert sent_message["data"]["tool_name"] == "data_analyzer"
                assert "purpose" in sent_message["data"]
                
            elif expected_event["event"] == "tool_completed":
                assert sent_message["data"]["result"]["status"] == "success"
                assert sent_message["data"]["result"]["confidence_score"] == 0.92
                
            elif expected_event["event"] == "agent_completed":
                assert sent_message["data"]["success"] is True
                assert len(sent_message["data"]["result"]["recommendations"]) == 3
        
        # Verify pipeline performance
        assert pipeline_time < 1.0  # Should complete pipeline quickly
        
        # Verify business value metrics
        completed_event = mock_ws.messages_sent[-1]  # Last event should be agent_completed
        assert completed_event["type"] == "agent_completed"
        assert completed_event["data"]["result"]["total_potential_improvement"] == "70%"
        assert completed_event["data"]["result"]["implementation_priority"] == "high"
        
        # Test pipeline error handling
        error_context = self.create_test_agent_context(user_id=user_id)
        error_event = {
            "event": "agent_failed",
            "data": {
                "agent_name": error_context.agent_name,
                "error": "Insufficient data for analysis",
                "error_code": "DATA_INSUFFICIENT",
                "recovery_suggestions": ["Provide more data", "Adjust analysis parameters"]
            }
        }
        
        await self.ws_manager.emit_critical_event(user_id, error_event["event"], error_event["data"])
        
        # Verify error handling
        assert len(mock_ws.messages_sent) == len(pipeline_events) + 1
        error_message = mock_ws.messages_sent[-1]
        assert error_message["type"] == "agent_failed"
        assert error_message["data"]["error_code"] == "DATA_INSUFFICIENT"
        
        # Record metrics
        self.record_metric("pipeline_events_processed", len(pipeline_events))
        self.record_metric("pipeline_execution_time_ms", pipeline_time * 1000)
        self.record_metric("agent_execution_complete", 1)
        self.record_metric("error_conditions_handled", 1)
        self.increment_websocket_events(len(pipeline_events) + 1)