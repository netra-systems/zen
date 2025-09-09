"""
Unit Tests for WebSocket Manager Business Logic

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - WebSocket management serves all user tiers  
- Business Goal: Reliable WebSocket connection management for multi-user AI chat platform
- Value Impact: Manages connection lifecycle, user isolation, and message broadcasting for $120K+ MRR
- Strategic Impact: Core infrastructure enabling real-time AI interactions and agent event delivery

This test suite validates the critical WebSocket manager business logic:
1. WebSocketManager/UnifiedWebSocketManager - SSOT connection management and message routing
2. WebSocketConnection - Individual connection state and message handling
3. Connection lifecycle management - Connect, disconnect, cleanup, and state tracking  
4. User isolation - Multi-tenant connection isolation preventing data leakage
5. Message broadcasting - Efficient delivery to single users or all connected users
6. Agent event delivery - Critical 5 events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
7. Error handling and recovery - Graceful failure handling and connection recovery

CRITICAL: WebSocket managers enable the Golden Path user flow by providing:
- Reliable connection management for chat interactions
- User isolation for secure multi-tenant operations  
- Agent event delivery for real-time AI processing updates
- Message routing for all WebSocket communication

Following TEST_CREATION_GUIDE.md:
- Real connection management logic (not infrastructure mocks)
- SSOT patterns using UnifiedWebSocketManager
- Proper test categorization (@pytest.mark.unit)  
- Tests that FAIL HARD when connection management fails
- Focus on connection management business value
"""

import asyncio
import json
import pytest
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from netra_backend.app.websocket_core.websocket_manager import (
    # Main WebSocket manager (alias to UnifiedWebSocketManager)
    WebSocketManager,
    # Protocol definition
    WebSocketManagerProtocol,
    # Utility function
    _serialize_message_safely
)
from netra_backend.app.websocket_core.unified_manager import (
    # Core manager implementation
    UnifiedWebSocketManager,
    WebSocketConnection
)
from netra_backend.app.websocket_core.connection_manager import (
    # SSOT alias for connection management
    WebSocketConnectionManager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, ConnectionID, ensure_user_id, ensure_thread_id
from test_framework.base_unit_test import BaseUnitTest


class TestWebSocketConnectionBusinessLogic(BaseUnitTest):
    """Test WebSocketConnection business logic for individual connection management."""
    
    def setUp(self):
        """Set up WebSocketConnection for testing."""
        # Create mock WebSocket
        self.mock_websocket = Mock()
        self.mock_websocket.client = Mock()
        self.mock_websocket.client.host = "127.0.0.1"
        self.mock_websocket.client.port = 45678
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.close = AsyncMock()
        
        # Create user context
        self.user_id = "test-user-123"
        self.thread_id = "thread-456"
        self.connection_id = "conn-789"
        
        # Create WebSocket connection
        self.connection = WebSocketConnection(
            connection_id=self.connection_id,
            user_id=self.user_id,
            websocket=self.mock_websocket,
            thread_id=self.thread_id
        )

    @pytest.mark.unit
    def test_websocket_connection_initialization_with_required_properties(self):
        """Test WebSocketConnection initializes with all required business properties."""
        # Business value: Proper initialization ensures connection can handle business operations
        
        # Validate required properties
        assert self.connection.connection_id == self.connection_id, "Must set connection ID"
        assert self.connection.user_id == self.user_id, "Must set user ID for isolation"
        assert self.connection.websocket == self.mock_websocket, "Must store WebSocket reference"
        assert self.connection.thread_id == self.thread_id, "Must set thread context"
        
        # Validate business-critical properties
        assert self.connection.is_active is True, "Must initialize as active"
        assert isinstance(self.connection.created_at, datetime), "Must track creation time"
        assert self.connection.last_activity is not None, "Must track activity for health monitoring"
        assert isinstance(self.connection.messages_sent, int), "Must track message statistics"
        assert self.connection.messages_sent == 0, "Must initialize message counter"

    @pytest.mark.unit
    async def test_websocket_connection_send_message_with_statistics_tracking(self):
        """Test WebSocketConnection sends messages and tracks statistics."""
        # Business value: Message sending enables chat functionality, statistics enable monitoring
        
        message_data = {
            "type": "agent_started",
            "payload": {
                "agent": "optimization_agent",
                "user_query": "Help me optimize costs"
            },
            "timestamp": time.time()
        }
        
        # Send message through connection
        result = await self.connection.send_message(message_data)
        
        # Validate message sending
        assert result is True, "Message sending must succeed"
        
        # Verify WebSocket send was called
        self.mock_websocket.send_json.assert_called_once_with(message_data)
        
        # Validate statistics tracking
        assert self.connection.messages_sent == 1, "Must increment message counter"
        assert self.connection.last_activity is not None, "Must update activity timestamp"

    @pytest.mark.unit
    async def test_websocket_connection_send_text_message_updates_activity(self):
        """Test WebSocketConnection send_text updates last activity."""
        # Business value: Activity tracking enables connection health monitoring
        
        original_activity = self.connection.last_activity
        
        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        # Send text message
        result = await self.connection.send_text("Hello from agent")
        
        # Validate text sending
        assert result is True, "Text sending must succeed"
        self.mock_websocket.send_text.assert_called_once_with("Hello from agent")
        
        # Validate activity tracking
        assert self.connection.last_activity > original_activity, "Must update last activity timestamp"

    @pytest.mark.unit
    async def test_websocket_connection_close_updates_state_properly(self):
        """Test WebSocketConnection close updates connection state."""
        # Business value: Proper connection cleanup prevents resource leaks
        
        # Verify initial state
        assert self.connection.is_active is True, "Connection should start as active"
        
        # Close connection
        await self.connection.close(code=1000, reason="Normal closure")
        
        # Validate state change
        assert self.connection.is_active is False, "Connection must be marked inactive"
        
        # Verify WebSocket close was called
        self.mock_websocket.close.assert_called_once_with(code=1000, reason="Normal closure")

    @pytest.mark.unit
    async def test_websocket_connection_handles_send_failure_gracefully(self):
        """Test WebSocketConnection handles WebSocket send failures gracefully."""
        # Business value: Graceful failure handling prevents connection crashes
        
        # Configure WebSocket to fail on send
        self.mock_websocket.send_json.side_effect = Exception("WebSocket send failed")
        
        message_data = {"type": "test_message", "data": "test"}
        
        # Send message (should handle exception)
        result = await self.connection.send_message(message_data)
        
        # Validate failure handling
        assert result is False, "Must return False on send failure"
        
        # Statistics should still be tracked for attempted send
        assert self.connection.messages_sent == 0, "Must not increment counter on failed send"

    @pytest.mark.unit
    def test_websocket_connection_to_dict_serialization(self):
        """Test WebSocketConnection to_dict serialization for monitoring."""
        # Business value: Connection serialization enables monitoring and debugging
        
        # Update some properties for testing
        self.connection.messages_sent = 5
        
        # Serialize connection
        conn_dict = self.connection.to_dict()
        
        # Validate serialization
        assert conn_dict["connection_id"] == self.connection_id, "Must include connection ID"
        assert conn_dict["user_id"] == self.user_id, "Must include user ID" 
        assert conn_dict["thread_id"] == self.thread_id, "Must include thread context"
        assert conn_dict["is_active"] is True, "Must include active state"
        assert conn_dict["messages_sent"] == 5, "Must include message statistics"
        assert "created_at" in conn_dict, "Must include creation timestamp"
        assert "last_activity" in conn_dict, "Must include activity timestamp"
        assert "client_info" in conn_dict, "Must include client information"
        
        # Validate client info
        client_info = conn_dict["client_info"]
        assert client_info["host"] == "127.0.0.1", "Must include client host"
        assert client_info["port"] == 45678, "Must include client port"


class TestUnifiedWebSocketManagerBusinessLogic(BaseUnitTest):
    """Test UnifiedWebSocketManager business logic for connection management."""
    
    def setUp(self):
        """Set up UnifiedWebSocketManager for testing."""
        # Create manager instance
        self.manager = UnifiedWebSocketManager()
        
        # Create mock user execution context
        self.user_context = Mock()
        self.user_context.user_id = "test-user-123"
        self.user_context.thread_id = "thread-456"
        self.user_context.websocket_client_id = "ws-client-789"

    @pytest.mark.unit
    def test_unified_websocket_manager_initialization(self):
        """Test UnifiedWebSocketManager initializes with proper business state."""
        # Business value: Proper initialization ensures manager can handle business operations
        
        manager = UnifiedWebSocketManager()
        
        # Validate initialization
        assert hasattr(manager, 'connections'), "Must initialize connections storage"
        assert hasattr(manager, 'user_connections'), "Must initialize user connection mapping"
        assert isinstance(manager.connections, dict), "Must use dict for connection storage"
        assert isinstance(manager.user_connections, dict), "Must use dict for user mapping"
        
        # Validate statistics initialization
        assert hasattr(manager, 'total_connections'), "Must track total connections"
        assert hasattr(manager, 'total_messages_sent'), "Must track message statistics"

    @pytest.mark.unit
    async def test_add_connection_with_user_isolation(self):
        """Test add_connection properly isolates users in multi-tenant system."""
        # Business value: User isolation prevents data leakage between customers
        
        # Create mock WebSocket
        mock_websocket = Mock()
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 45678
        
        # Add connection with user context
        connection_id = await self.manager.add_connection(
            self.user_context.user_id,
            mock_websocket,
            thread_id=self.user_context.thread_id
        )
        
        # Validate connection creation
        assert connection_id is not None, "Must create connection ID"
        assert connection_id in self.manager.connections, "Must store connection"
        assert self.user_context.user_id in self.manager.user_connections, "Must map user to connections"
        
        # Validate user isolation
        connection = self.manager.connections[connection_id]
        assert connection.user_id == self.user_context.user_id, "Must isolate by user ID"
        assert connection.thread_id == self.user_context.thread_id, "Must preserve thread context"
        
        # Validate statistics
        assert self.manager.total_connections >= 1, "Must track total connections"

    @pytest.mark.unit
    async def test_send_to_user_with_proper_user_isolation(self):
        """Test send_to_user only sends to specified user's connections."""
        # Business value: User-specific messaging enables private AI interactions
        
        # Create two users with connections
        user1_id = "user-1"
        user2_id = "user-2"
        
        mock_websocket1 = Mock()
        mock_websocket1.send_json = AsyncMock()
        mock_websocket1.client = Mock()
        mock_websocket1.client.host = "127.0.0.1"
        mock_websocket1.client.port = 45678
        
        mock_websocket2 = Mock() 
        mock_websocket2.send_json = AsyncMock()
        mock_websocket2.client = Mock()
        mock_websocket2.client.host = "127.0.0.1"
        mock_websocket2.client.port = 45679
        
        # Add connections for both users
        conn1_id = await self.manager.add_connection(user1_id, mock_websocket1)
        conn2_id = await self.manager.add_connection(user2_id, mock_websocket2)
        
        # Send message to user 1 only
        message_data = {
            "type": "agent_started",
            "payload": {"message": "Starting optimization analysis"},
            "timestamp": time.time()
        }
        
        result = await self.manager.send_to_user(user1_id, message_data)
        
        # Validate user isolation
        assert result is True, "Message sending to specific user must succeed"
        
        # Verify only user1's connection received the message
        mock_websocket1.send_json.assert_called_once_with(message_data)
        mock_websocket2.send_json.assert_not_called()
        
        # Validate statistics tracking
        user1_connection = self.manager.connections[conn1_id]
        user2_connection = self.manager.connections[conn2_id]
        assert user1_connection.messages_sent == 1, "Must track messages for user1"
        assert user2_connection.messages_sent == 0, "Must not affect user2 statistics"

    @pytest.mark.unit
    async def test_broadcast_to_all_reaches_multiple_users(self):
        """Test broadcast_to_all sends messages to all connected users."""
        # Business value: Broadcasting enables system-wide notifications and announcements
        
        # Create multiple user connections
        users = ["user-1", "user-2", "user-3"]
        mock_websockets = []
        
        for i, user_id in enumerate(users):
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.client = Mock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 45678 + i
            
            await self.manager.add_connection(user_id, mock_websocket)
            mock_websockets.append(mock_websocket)
        
        # Broadcast message to all users
        broadcast_message = {
            "type": "system_announcement",
            "payload": {"message": "System maintenance in 5 minutes"},
            "timestamp": time.time()
        }
        
        result = await self.manager.broadcast_to_all(broadcast_message)
        
        # Validate broadcast delivery
        assert result is True, "Broadcast must succeed"
        
        # Verify all connections received the message
        for mock_websocket in mock_websockets:
            mock_websocket.send_json.assert_called_once_with(broadcast_message)
        
        # Validate statistics
        assert self.manager.total_messages_sent >= 3, "Must track broadcast messages"

    @pytest.mark.unit
    async def test_send_agent_event_for_critical_business_events(self):
        """Test send_agent_event delivers critical agent execution events."""
        # Business value: Agent events enable real-time AI processing updates for chat
        
        # Create user connection
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 45678
        
        user_id = "agent-user-123"
        await self.manager.add_connection(user_id, mock_websocket)
        
        # Send critical agent event
        agent_event_data = {
            "type": "agent_thinking",
            "payload": {
                "agent": "cost_optimization_agent",
                "status": "analyzing_aws_spend", 
                "progress": 0.3,
                "thinking": "Analyzing EC2 instance utilization patterns..."
            },
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        result = await self.manager.send_agent_event(user_id, agent_event_data)
        
        # Validate agent event delivery
        assert result is True, "Agent event delivery must succeed"
        
        # Verify agent event was sent with proper format
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        
        assert sent_message["type"] == "agent_thinking", "Must preserve agent event type"
        assert sent_message["payload"]["agent"] == "cost_optimization_agent", "Must preserve agent context"
        assert sent_message["payload"]["thinking"] is not None, "Must include agent reasoning"
        assert sent_message["user_id"] == user_id, "Must include user context"

    @pytest.mark.unit
    async def test_remove_connection_cleans_up_user_mappings(self):
        """Test remove_connection properly cleans up user mappings and resources."""  
        # Business value: Proper cleanup prevents resource leaks and maintains system performance
        
        # Create user connection
        mock_websocket = Mock()
        mock_websocket.client = Mock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.client.port = 45678
        
        user_id = "cleanup-user-456"
        connection_id = await self.manager.add_connection(user_id, mock_websocket)
        
        # Verify connection exists
        assert connection_id in self.manager.connections, "Connection must exist before removal"
        assert user_id in self.manager.user_connections, "User mapping must exist"
        
        # Remove connection
        await self.manager.remove_connection(connection_id)
        
        # Validate cleanup
        assert connection_id not in self.manager.connections, "Must remove connection from storage"
        
        # If user has no more connections, user mapping should be cleaned
        if user_id in self.manager.user_connections:
            assert len(self.manager.user_connections[user_id]) == 0, "Must clean user connection list"

    @pytest.mark.unit
    async def test_get_user_connections_returns_isolated_connections(self):
        """Test get_user_connections returns only specified user's connections."""
        # Business value: User connection isolation enables proper multi-tenant operation
        
        # Create connections for different users
        user1_id = "isolated-user-1"
        user2_id = "isolated-user-2"
        
        mock_websocket1 = Mock()
        mock_websocket1.client = Mock()
        mock_websocket1.client.host = "127.0.0.1"
        mock_websocket1.client.port = 45678
        
        mock_websocket2 = Mock()
        mock_websocket2.client = Mock()
        mock_websocket2.client.host = "127.0.0.1"
        mock_websocket2.client.port = 45679
        
        conn1_id = await self.manager.add_connection(user1_id, mock_websocket1)
        conn2_id = await self.manager.add_connection(user2_id, mock_websocket2)
        
        # Get user1's connections
        user1_connections = await self.manager.get_user_connections(user1_id)
        
        # Validate isolation
        assert len(user1_connections) == 1, "Must return only user1's connections"
        assert user1_connections[0].connection_id == conn1_id, "Must return correct connection"
        assert user1_connections[0].user_id == user1_id, "Must maintain user isolation"
        
        # Verify user2's connection is not included
        for connection in user1_connections:
            assert connection.user_id != user2_id, "Must not include other users' connections"

    @pytest.mark.unit
    def test_get_connection_stats_provides_monitoring_data(self):
        """Test get_connection_stats provides comprehensive monitoring data."""
        # Business value: Connection statistics enable system monitoring and capacity planning
        
        # Create some connections to generate statistics
        self.manager.total_connections = 5
        self.manager.total_messages_sent = 150
        
        # Add mock connections to generate realistic stats
        self.manager.connections = {
            "conn-1": Mock(user_id="user-1", is_active=True, messages_sent=30),
            "conn-2": Mock(user_id="user-2", is_active=True, messages_sent=45),
            "conn-3": Mock(user_id="user-1", is_active=False, messages_sent=25)  # Inactive connection
        }
        
        # Get connection statistics
        stats = self.manager.get_connection_stats()
        
        # Validate comprehensive statistics
        assert "total_connections" in stats, "Must include total connection count"
        assert "active_connections" in stats, "Must track active connections"
        assert "inactive_connections" in stats, "Must track inactive connections"
        assert "total_messages_sent" in stats, "Must track message statistics"
        assert "unique_users" in stats, "Must count unique users"
        assert "avg_messages_per_connection" in stats, "Must calculate average messages"
        assert "timestamp" in stats, "Must include timestamp for monitoring"
        
        # Validate calculated values
        assert stats["active_connections"] >= 0, "Active connections must be non-negative"
        assert stats["unique_users"] >= 0, "Unique users must be non-negative"

    @pytest.mark.unit
    async def test_validate_message_format_for_business_requirements(self):
        """Test validate_message format ensures messages meet business requirements."""
        # Business value: Message validation prevents malformed messages that could crash chat
        
        # Test valid message format
        valid_message = {
            "type": "agent_started",
            "payload": {
                "agent": "optimization_agent",
                "query": "Optimize my cloud costs"
            },
            "timestamp": time.time()
        }
        
        is_valid = self.manager.validate_message(valid_message)
        assert is_valid is True, "Must accept valid message format"
        
        # Test invalid message format (missing type)
        invalid_message = {
            "payload": {"data": "test"},
            "timestamp": time.time()
        }
        
        is_invalid = self.manager.validate_message(invalid_message)
        assert is_invalid is False, "Must reject message without type"
        
        # Test invalid message format (not a dict)
        not_dict_message = "This is not a dictionary"
        
        is_not_dict_invalid = self.manager.validate_message(not_dict_message)
        assert is_not_dict_invalid is False, "Must reject non-dictionary messages"


class TestWebSocketManagerAliasingBusinessLogic(BaseUnitTest):
    """Test WebSocket manager aliasing for SSOT compliance."""
    
    @pytest.mark.unit
    def test_websocket_manager_aliases_to_unified_manager(self):
        """Test WebSocketManager aliases to UnifiedWebSocketManager for SSOT compliance."""
        # Business value: SSOT aliasing ensures consistent manager interface across system
        
        # Verify alias relationship
        assert WebSocketManager == UnifiedWebSocketManager, "WebSocketManager must alias UnifiedWebSocketManager"
        
        # Verify instances are same type
        manager1 = WebSocketManager()
        manager2 = UnifiedWebSocketManager()
        
        assert type(manager1) == type(manager2), "Aliased managers must be same type"
        assert isinstance(manager1, UnifiedWebSocketManager), "WebSocketManager must be UnifiedWebSocketManager instance"

    @pytest.mark.unit
    def test_websocket_connection_manager_aliases_to_unified_manager(self):
        """Test WebSocketConnectionManager aliases to UnifiedWebSocketManager."""
        # Business value: Connection manager alias provides backward compatibility
        
        # Create connection manager instance
        connection_manager = WebSocketConnectionManager()
        
        # Verify it's actually UnifiedWebSocketManager
        assert isinstance(connection_manager, UnifiedWebSocketManager), "Must be UnifiedWebSocketManager instance"
        
        # Verify it has all required manager methods
        required_methods = [
            'add_connection',
            'remove_connection', 
            'send_to_user',
            'broadcast_to_all',
            'get_connection_stats'
        ]
        
        for method_name in required_methods:
            assert hasattr(connection_manager, method_name), f"Must have {method_name} method"

    @pytest.mark.unit
    def test_websocket_manager_protocol_compliance(self):
        """Test WebSocket managers comply with WebSocketManagerProtocol."""
        # Business value: Protocol compliance ensures consistent interface across implementations
        
        # Create manager instances
        unified_manager = UnifiedWebSocketManager()
        alias_manager = WebSocketManager()
        connection_manager = WebSocketConnectionManager()
        
        # Verify protocol compliance for key methods
        protocol_methods = [
            'add_connection',
            'remove_connection',
            'send_to_user',
            'broadcast_to_all'
        ]
        
        managers = [unified_manager, alias_manager, connection_manager]
        
        for manager in managers:
            for method_name in protocol_methods:
                assert hasattr(manager, method_name), f"{manager.__class__.__name__} must implement {method_name}"
                
                # Verify method is callable
                method = getattr(manager, method_name)
                assert callable(method), f"{method_name} must be callable"


class TestWebSocketUtilityFunctions(BaseUnitTest):
    """Test WebSocket utility functions for message handling."""
    
    @pytest.mark.unit
    def test_serialize_message_safely_handles_complex_objects(self):
        """Test _serialize_message_safely handles complex objects safely."""
        # Business value: Safe serialization prevents JSON encoding errors that crash WebSocket
        
        # Create message with complex objects that might cause serialization issues
        from fastapi.websockets import WebSocketState
        
        complex_message = {
            "type": "agent_event",
            "websocket_state": WebSocketState.CONNECTED,  # Enum that needs special handling
            "timestamp": datetime.now(timezone.utc),  # Datetime object
            "user_context": {
                "user_id": "user-123",
                "metadata": {
                    "nested_enum": WebSocketState.DISCONNECTED,
                    "nested_datetime": datetime.now(timezone.utc)
                }
            },
            "payload": {
                "message": "Agent processing complete",
                "status": "success"
            }
        }
        
        # Serialize complex message
        serialized = _serialize_message_safely(complex_message)
        
        # Validate serialization success
        assert isinstance(serialized, dict), "Must return dictionary"
        assert serialized["type"] == "agent_event", "Must preserve simple values"
        assert serialized["payload"]["message"] == "Agent processing complete", "Must preserve nested simple values"
        
        # Verify complex objects were handled
        assert "websocket_state" in serialized, "Must include enum field"
        assert isinstance(serialized["websocket_state"], str), "Must convert enum to string"
        
        # Verify nested complex objects were handled
        assert "timestamp" in serialized, "Must include datetime field"
        assert isinstance(serialized["timestamp"], str), "Must convert datetime to string"

    @pytest.mark.unit
    def test_serialize_message_safely_preserves_json_serializable_data(self):
        """Test _serialize_message_safely preserves JSON-serializable data unchanged."""
        # Business value: Efficient serialization preserves performance for normal messages
        
        # Create message with only JSON-serializable data
        json_safe_message = {
            "type": "user_message",
            "payload": {
                "text": "Help me optimize my AWS costs",
                "thread_id": "thread-123",
                "metadata": {
                    "priority": 1,
                    "source": "web_chat"
                }
            },
            "timestamp": time.time(),
            "user_id": "user-456"
        }
        
        # Serialize JSON-safe message
        serialized = _serialize_message_safely(json_safe_message)
        
        # Validate preservation
        assert serialized == json_safe_message, "Must preserve JSON-safe data unchanged"
        
        # Verify it can be JSON encoded
        json_string = json.dumps(serialized)
        assert isinstance(json_string, str), "Must be JSON encodable"
        
        # Verify round-trip serialization
        deserialized = json.loads(json_string)
        assert deserialized["type"] == "user_message", "Must preserve message structure"


if __name__ == "__main__":
    # Run tests with proper WebSocket manager business logic validation
    pytest.main([__file__, "-v", "--tb=short"])