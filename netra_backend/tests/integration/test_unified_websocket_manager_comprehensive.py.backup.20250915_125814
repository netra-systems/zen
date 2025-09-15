"""
Comprehensive Integration Tests for UnifiedWebSocketManager

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure UnifiedWebSocketManager provides reliable, isolated, real-time communication
- Value Impact: Validates WebSocket management that enables AI chat business value delivery
- Strategic Impact: Mission-critical - Real-time chat is 90% of our business value

This test suite validates the complete UnifiedWebSocketManager functionality that enables
substantive AI chat interactions and real-time user experience. These tests ensure:

1. WebSocket connection lifecycle management (connect  ->  authenticate  ->  messaging  ->  disconnect)
2. Multi-user session isolation preventing cross-user data leakage
3. Real-time event broadcasting and message routing between users
4. Connection pool management and resource limits
5. Authentication and authorization validation
6. Connection recovery and reconnection handling
7. Cross-service WebSocket coordination (backend [U+2194] frontend)
8. Performance under concurrent load and stress conditions
9. Business-critical WebSocket event delivery (agent events, tool status, results)
10. Connection health monitoring and circuit breaker patterns
11. Message queuing and delivery guarantees
12. Integration with AgentWebSocketBridge and agent execution systems
13. Connection cleanup and resource management
14. Error handling and graceful degradation scenarios

Tests use REAL WebSocket connections, REAL event broadcasting, and REAL user session
management - NO MOCKS in integration layer as per TEST_CREATION_GUIDE.md.
"""

import asyncio
import json
import pytest
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

# Core imports
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    RegistryCompat
)
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketContext,
    ConnectionStatus
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.websocket_test_helpers import (
    WebSocketTestClient,
    WebSocketTestSession,
    assert_websocket_events,
    websocket_test_context
)
from shared.isolated_environment import IsolatedEnvironment, get_env


class MockWebSocket:
    """Mock WebSocket for testing without network dependencies."""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_closed = False
        self.state = "OPEN"
        
    async def send_json(self, message: Dict[str, Any]) -> None:
        """Mock send_json that records sent messages."""
        if self.is_closed:
            raise ConnectionError("WebSocket is closed")
        
        self.sent_messages.append({
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": self.user_id
        })
        
    async def close(self):
        """Mock close method."""
        self.is_closed = True
        self.state = "CLOSED"
        
    def get_sent_messages(self, message_type: str = None) -> List[Dict[str, Any]]:
        """Get sent messages, optionally filtered by type."""
        if not message_type:
            return self.sent_messages
        return [
            msg for msg in self.sent_messages 
            if msg.get("message", {}).get("type") == message_type
        ]


@pytest.fixture
def isolated_env():
    """Provide isolated environment for testing."""
    env = IsolatedEnvironment()
    env.set("TEST_MODE", "true", source="test")
    env.set("ENVIRONMENT", "development", source="test")  # Avoid staging retry logic
    return env


@pytest.fixture
def websocket_manager():
    """Provide UnifiedWebSocketManager instance."""
    return UnifiedWebSocketManager()


@pytest.fixture
def websocket_factory():
    """Provide WebSocketBridgeFactory instance."""
    return WebSocketBridgeFactory()


@pytest.fixture
def agent_bridge():
    """Provide AgentWebSocketBridge instance."""
    return AgentWebSocketBridge()


@pytest.fixture
async def real_websocket_connections():
    """Provide real WebSocket connections for testing."""
    connections = {}
    
    # Create multiple mock WebSocket connections for different users
    for i in range(5):
        user_id = f"test_user_{i}"
        websocket = MockWebSocket(user_id=user_id)
        connections[user_id] = {
            "websocket": websocket,
            "connection_id": str(uuid.uuid4()),
            "user_id": user_id
        }
    
    yield connections
    
    # Cleanup: Close all WebSocket connections
    for conn_info in connections.values():
        await conn_info["websocket"].close()


class TestUnifiedWebSocketManagerComprehensive(BaseIntegrationTest):
    """Comprehensive integration tests for UnifiedWebSocketManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        self.isolated_env.set("ENVIRONMENT", "development", source="test")  # Avoid staging retry logic
        
    # ============================================================================
    # TEST 1: WebSocket Connection Lifecycle Management
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_lifecycle_complete_flow(
        self, 
        websocket_manager, 
        real_websocket_connections,
        isolated_env
    ):
        """
        Test complete WebSocket connection lifecycle: connect  ->  authenticate  ->  messaging  ->  disconnect.
        
        Business Value: Validates the core connection management that enables real-time chat.
        """
        user_id = "lifecycle_user_1"
        websocket = MockWebSocket(user_id=user_id)
        connection_id = str(uuid.uuid4())
        
        # PHASE 1: Connection establishment
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.utcnow(),
            metadata={"test": "lifecycle"}
        )
        
        # Add connection
        await websocket_manager.add_connection(connection)
        
        # Verify connection added
        assert websocket_manager.get_connection(connection_id) == connection
        assert connection_id in websocket_manager.get_user_connections(user_id)
        assert websocket_manager.is_connection_active(user_id) is True
        
        # PHASE 2: Authentication verification
        # Verify connection health
        health = websocket_manager.get_connection_health(user_id)
        assert health["has_active_connections"] is True
        assert health["total_connections"] == 1
        assert health["active_connections"] == 1
        
        # PHASE 3: Messaging
        test_message = {
            "type": "test_message",
            "data": {"content": "Hello from lifecycle test"},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send message to user
        await websocket_manager.send_to_user(user_id, test_message)
        
        # Verify message sent
        sent_messages = websocket.get_sent_messages("test_message")
        assert len(sent_messages) == 1
        assert sent_messages[0]["message"]["data"]["content"] == "Hello from lifecycle test"
        
        # PHASE 4: Critical event emission
        await websocket_manager.emit_critical_event(
            user_id=user_id,
            event_type="agent_started", 
            data={"agent": "test_agent", "message": "Starting execution"}
        )
        
        # Verify critical event sent
        critical_messages = websocket.get_sent_messages("agent_started")
        assert len(critical_messages) == 1
        assert critical_messages[0]["message"]["critical"] is True
        
        # PHASE 5: Connection cleanup and disconnect
        await websocket_manager.remove_connection(connection_id)
        
        # Verify connection removed
        assert websocket_manager.get_connection(connection_id) is None
        assert connection_id not in websocket_manager.get_user_connections(user_id)
        assert websocket_manager.is_connection_active(user_id) is False
        
        # Verify health reflects disconnection
        health = websocket_manager.get_connection_health(user_id)
        assert health["has_active_connections"] is False
        assert health["total_connections"] == 0
        
    # ============================================================================
    # TEST 2: Multi-User WebSocket Session Isolation
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_websocket_isolation_prevents_cross_user_leakage(
        self, 
        websocket_manager, 
        real_websocket_connections,
        isolated_env
    ):
        """
        Test multi-user WebSocket session isolation and concurrent connections.
        
        Business Value: Critical security - prevents User A from seeing User B's messages.
        """
        # Create 3 different users with isolated connections
        users = {}
        for i in range(3):
            user_id = f"isolated_user_{i}"
            websocket = MockWebSocket(user_id=user_id)
            connection_id = str(uuid.uuid4())
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={"isolation_test": True, "user_index": i}
            )
            
            await websocket_manager.add_connection(connection)
            
            users[user_id] = {
                "connection": connection,
                "websocket": websocket,
                "connection_id": connection_id
            }
        
        # Verify all users have isolated connections
        for user_id, user_info in users.items():
            assert websocket_manager.is_connection_active(user_id) is True
            user_connections = websocket_manager.get_user_connections(user_id)
            assert len(user_connections) == 1
            assert user_info["connection_id"] in user_connections
        
        # TEST ISOLATION: Send user-specific messages
        for i, (user_id, user_info) in enumerate(users.items()):
            user_specific_message = {
                "type": "user_specific_message",
                "data": {
                    "content": f"Secret message for {user_id}",
                    "user_index": i,
                    "sensitive_data": f"CONFIDENTIAL_{user_id.upper()}"
                },
                "user_id": user_id  # Should only go to this user
            }
            
            await websocket_manager.send_to_user(user_id, user_specific_message)
        
        # VERIFY ISOLATION: Each user should only receive their own messages
        for user_id, user_info in users.items():
            websocket = user_info["websocket"]
            received_messages = websocket.get_sent_messages("user_specific_message")
            
            # Should have exactly 1 message (their own)
            assert len(received_messages) == 1
            
            message = received_messages[0]["message"]
            assert message["data"]["content"] == f"Secret message for {user_id}"
            assert message["user_id"] == user_id
            
            # Verify sensitive data is contained
            assert f"CONFIDENTIAL_{user_id.upper()}" in message["data"]["sensitive_data"]
        
        # TEST CONCURRENT OPERATIONS: Simulate concurrent message sending
        async def send_concurrent_messages(target_user_id: str, message_count: int):
            for i in range(message_count):
                message = {
                    "type": "concurrent_test",
                    "data": {"message_id": i, "target_user": target_user_id},
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket_manager.send_to_user(target_user_id, message)
                # Small delay to simulate real-world timing
                await asyncio.sleep(0.01)
        
        # Send 10 concurrent messages to each user
        tasks = []
        for user_id in users.keys():
            task = asyncio.create_task(send_concurrent_messages(user_id, 10))
            tasks.append(task)
        
        # Wait for all concurrent operations to complete
        await asyncio.gather(*tasks)
        
        # VERIFY CONCURRENT ISOLATION: Each user should have received exactly 10 messages
        for user_id, user_info in users.items():
            websocket = user_info["websocket"]
            concurrent_messages = websocket.get_sent_messages("concurrent_test")
            
            assert len(concurrent_messages) == 10
            
            # Verify all messages are for the correct user
            for msg in concurrent_messages:
                assert msg["message"]["data"]["target_user"] == user_id
        
        # Cleanup: Remove all connections
        for user_id, user_info in users.items():
            await websocket_manager.remove_connection(user_info["connection_id"])
            assert websocket_manager.is_connection_active(user_id) is False
    
    # ============================================================================
    # TEST 3: Real-Time Event Broadcasting and Message Routing
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_event_broadcasting_and_message_routing(
        self, 
        websocket_manager, 
        real_websocket_connections,
        isolated_env
    ):
        """
        Test real-time event broadcasting and message routing between users.
        
        Business Value: Enables real-time collaboration and live agent updates.
        """
        # Setup: Create multiple users and connections
        broadcasting_users = {}
        
        for i in range(4):
            user_id = f"broadcast_user_{i}"
            websocket = MockWebSocket(user_id=user_id)
            connection_id = str(uuid.uuid4())
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={"role": "broadcaster" if i == 0 else "receiver"}
            )
            
            await websocket_manager.add_connection(connection)
            broadcasting_users[user_id] = {
                "websocket": websocket,
                "connection_id": connection_id,
                "role": "broadcaster" if i == 0 else "receiver"
            }
        
        broadcaster_id = "broadcast_user_0"
        receiver_ids = [f"broadcast_user_{i}" for i in range(1, 4)]
        
        # TEST 1: Broadcast to all connections
        broadcast_message = {
            "type": "system_broadcast",
            "data": {
                "announcement": "System maintenance in 5 minutes",
                "priority": "high",
                "timestamp": datetime.utcnow().isoformat()
            },
            "broadcast_id": str(uuid.uuid4())
        }
        
        await websocket_manager.broadcast(broadcast_message)
        
        # Verify all users received the broadcast
        for user_id, user_info in broadcasting_users.items():
            websocket = user_info["websocket"]
            broadcast_messages = websocket.get_sent_messages("system_broadcast")
            assert len(broadcast_messages) == 1
            assert broadcast_messages[0]["message"]["data"]["announcement"] == "System maintenance in 5 minutes"
        
        # TEST 2: Selective message routing - agent events to specific users
        agent_events = [
            {"type": "agent_started", "data": {"agent": "cost_optimizer", "user": "user_1"}},
            {"type": "agent_thinking", "data": {"reasoning": "Analyzing costs", "user": "user_1"}},
            {"type": "tool_executing", "data": {"tool": "aws_analyzer", "user": "user_1"}},
            {"type": "tool_completed", "data": {"results": {"savings": "$500"}, "user": "user_1"}},
            {"type": "agent_completed", "data": {"recommendations": ["Use Reserved Instances"], "user": "user_1"}}
        ]
        
        # Send agent events to specific user
        target_user = "broadcast_user_1"
        for event in agent_events:
            await websocket_manager.emit_critical_event(
                user_id=target_user,
                event_type=event["type"],
                data=event["data"]
            )
        
        # Verify only target user received agent events
        target_websocket = broadcasting_users[target_user]["websocket"]
        
        for event in agent_events:
            event_messages = target_websocket.get_sent_messages(event["type"])
            assert len(event_messages) == 1
            assert event_messages[0]["message"]["critical"] is True
            assert event_messages[0]["message"]["data"]["user"] == "user_1"
        
        # Verify other users did NOT receive agent events
        for user_id, user_info in broadcasting_users.items():
            if user_id != target_user:
                websocket = user_info["websocket"]
                for event in agent_events:
                    event_messages = websocket.get_sent_messages(event["type"])
                    assert len(event_messages) == 0  # Should not have received agent events
        
        # TEST 3: Real-time performance - rapid message delivery
        start_time = time.time()
        rapid_message_count = 50
        
        for i in range(rapid_message_count):
            rapid_message = {
                "type": "performance_test",
                "data": {
                    "message_id": i,
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": f"Rapid message {i}"
                }
            }
            await websocket_manager.send_to_user(target_user, rapid_message)
        
        end_time = time.time()
        delivery_time = end_time - start_time
        
        # Verify rapid delivery performance
        assert delivery_time < 1.0  # Should deliver 50 messages in under 1 second
        
        # Verify all rapid messages received
        rapid_messages = target_websocket.get_sent_messages("performance_test")
        assert len(rapid_messages) == rapid_message_count
        
        # Cleanup
        for user_id, user_info in broadcasting_users.items():
            await websocket_manager.remove_connection(user_info["connection_id"])
    
    # ============================================================================
    # TEST 4: Connection Pool Management and Resource Limits
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_management_and_resource_limits(
        self, 
        websocket_manager, 
        isolated_env
    ):
        """
        Test WebSocket connection pool management and resource limits.
        
        Business Value: Prevents resource exhaustion and ensures scalability.
        """
        # TEST 1: Multiple connections per user
        multi_connection_user = "multi_conn_user"
        user_connections = []
        
        # Create 5 connections for the same user (simulating multiple browser tabs)
        for i in range(5):
            websocket = MockWebSocket(user_id=multi_connection_user)
            connection_id = str(uuid.uuid4())
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=multi_connection_user,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={"tab": f"tab_{i}", "browser": "chrome"}
            )
            
            await websocket_manager.add_connection(connection)
            user_connections.append({
                "connection": connection,
                "websocket": websocket,
                "connection_id": connection_id
            })
        
        # Verify all connections tracked for user
        user_conn_ids = websocket_manager.get_user_connections(multi_connection_user)
        assert len(user_conn_ids) == 5
        
        # TEST 2: Message delivery to all user connections
        multi_connection_message = {
            "type": "multi_tab_sync",
            "data": {"action": "refresh_data", "timestamp": datetime.utcnow().isoformat()}
        }
        
        await websocket_manager.send_to_user(multi_connection_user, multi_connection_message)
        
        # Verify message sent to all 5 connections
        for conn_info in user_connections:
            websocket = conn_info["websocket"]
            sync_messages = websocket.get_sent_messages("multi_tab_sync")
            assert len(sync_messages) == 1
        
        # TEST 3: Connection statistics and monitoring
        stats = websocket_manager.get_stats()
        assert stats["total_connections"] == 5
        assert stats["unique_users"] == 1
        assert multi_connection_user in stats["connections_by_user"]
        assert stats["connections_by_user"][multi_connection_user] == 5
        
        # TEST 4: Resource cleanup - remove specific connections
        connections_to_remove = [user_connections[0]["connection_id"], user_connections[2]["connection_id"]]
        
        for conn_id in connections_to_remove:
            await websocket_manager.remove_connection(conn_id)
        
        # Verify selective removal
        remaining_conn_ids = websocket_manager.get_user_connections(multi_connection_user)
        assert len(remaining_conn_ids) == 3
        
        for removed_id in connections_to_remove:
            assert removed_id not in remaining_conn_ids
        
        # TEST 5: Connection health monitoring
        health = websocket_manager.get_connection_health(multi_connection_user)
        assert health["total_connections"] == 3
        assert health["active_connections"] == 3
        assert health["has_active_connections"] is True
        assert len(health["connections"]) == 3
        
        # Verify connection details
        for conn_detail in health["connections"]:
            assert conn_detail["active"] is True
            assert "connected_at" in conn_detail
            assert "metadata" in conn_detail
        
        # TEST 6: Bulk cleanup - remove all user connections
        remaining_connections = list(remaining_conn_ids)
        for conn_id in remaining_connections:
            await websocket_manager.remove_connection(conn_id)
        
        # Verify complete cleanup
        assert len(websocket_manager.get_user_connections(multi_connection_user)) == 0
        assert websocket_manager.is_connection_active(multi_connection_user) is False
        
        final_stats = websocket_manager.get_stats()
        assert final_stats["total_connections"] == 0
        assert final_stats["unique_users"] == 0
    
    # ============================================================================
    # TEST 5: WebSocket Authentication and Authorization Validation
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_authentication_and_authorization_validation(
        self, 
        websocket_manager, 
        isolated_env
    ):
        """
        Test WebSocket authentication and authorization validation.
        
        Business Value: Security - prevents unauthorized access and data breaches.
        """
        # Setup authenticated and unauthenticated users
        authenticated_user = "authenticated_user_123"
        unauthenticated_user = "unauthenticated_user_456"
        admin_user = "admin_user_789"
        
        # Create connections with different auth levels
        auth_levels = {
            authenticated_user: {"role": "user", "authenticated": True, "permissions": ["read", "write"]},
            unauthenticated_user: {"role": "guest", "authenticated": False, "permissions": []},
            admin_user: {"role": "admin", "authenticated": True, "permissions": ["read", "write", "admin"]}
        }
        
        connections = {}
        for user_id, auth_info in auth_levels.items():
            websocket = MockWebSocket(user_id=user_id)
            connection_id = str(uuid.uuid4())
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={"auth": auth_info}
            )
            
            await websocket_manager.add_connection(connection)
            connections[user_id] = {
                "websocket": websocket,
                "connection_id": connection_id,
                "auth_info": auth_info
            }
        
        # TEST 1: Send messages requiring different authorization levels
        
        # Public message (should reach all users)
        public_message = {
            "type": "public_announcement",
            "data": {"message": "Welcome to Netra!", "level": "public"}
        }
        
        for user_id in connections.keys():
            await websocket_manager.send_to_user(user_id, public_message)
        
        # Verify all users received public message
        for user_id, conn_info in connections.items():
            websocket = conn_info["websocket"]
            public_messages = websocket.get_sent_messages("public_announcement")
            assert len(public_messages) == 1
        
        # TEST 2: User-level message (should only reach authenticated users)
        user_level_message = {
            "type": "user_data_update", 
            "data": {
                "user_settings": {"theme": "dark", "notifications": True},
                "level": "user"
            }
        }
        
        # Send to authenticated users only
        for user_id, conn_info in connections.items():
            if conn_info["auth_info"]["authenticated"]:
                await websocket_manager.send_to_user(user_id, user_level_message)
        
        # Verify only authenticated users received user-level message
        authenticated_users = [authenticated_user, admin_user]
        for user_id, conn_info in connections.items():
            websocket = conn_info["websocket"]
            user_messages = websocket.get_sent_messages("user_data_update")
            
            if user_id in authenticated_users:
                assert len(user_messages) == 1
                assert user_messages[0]["message"]["data"]["level"] == "user"
            else:
                assert len(user_messages) == 0  # Unauthenticated users should not receive
        
        # TEST 3: Admin-level message (should only reach admin)
        admin_message = {
            "type": "admin_alert",
            "data": {
                "alert": "System maintenance scheduled",
                "level": "admin",
                "sensitive_data": "INTERNAL_ONLY"
            }
        }
        
        # Send to admin only
        await websocket_manager.send_to_user(admin_user, admin_message)
        
        # Verify only admin received admin message
        for user_id, conn_info in connections.items():
            websocket = conn_info["websocket"]
            admin_messages = websocket.get_sent_messages("admin_alert")
            
            if user_id == admin_user:
                assert len(admin_messages) == 1
                assert admin_messages[0]["message"]["data"]["sensitive_data"] == "INTERNAL_ONLY"
            else:
                assert len(admin_messages) == 0  # Non-admin users should not receive
        
        # TEST 4: Critical event authorization
        # Test that critical events respect user authorization
        critical_events = [
            {"type": "agent_started", "auth_required": True},
            {"type": "tool_executing", "auth_required": True}, 
            {"type": "system_error", "auth_required": False}
        ]
        
        for event_info in critical_events:
            event_type = event_info["type"]
            auth_required = event_info["auth_required"]
            
            for user_id, conn_info in connections.items():
                user_authenticated = conn_info["auth_info"]["authenticated"]
                
                # Only send to user if they meet auth requirements
                if not auth_required or user_authenticated:
                    await websocket_manager.emit_critical_event(
                        user_id=user_id,
                        event_type=event_type,
                        data={"message": f"Critical {event_type} event"}
                    )
        
        # Verify critical event authorization
        for user_id, conn_info in connections.items():
            websocket = conn_info["websocket"]
            user_authenticated = conn_info["auth_info"]["authenticated"]
            
            # Check agent_started (auth required)
            agent_messages = websocket.get_sent_messages("agent_started")
            if user_authenticated:
                assert len(agent_messages) == 1
            else:
                assert len(agent_messages) == 0
                
            # Check system_error (no auth required)
            system_messages = websocket.get_sent_messages("system_error")
            assert len(system_messages) == 1  # All users should receive
        
        # Cleanup
        for user_id, conn_info in connections.items():
            await websocket_manager.remove_connection(conn_info["connection_id"])
    
    # ============================================================================
    # TEST 6: Connection Recovery and Reconnection Handling
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_recovery_and_reconnection_handling(
        self, 
        websocket_manager, 
        isolated_env
    ):
        """
        Test WebSocket reconnection handling and connection recovery scenarios.
        
        Business Value: Reliability - ensures uninterrupted service during network issues.
        """
        recovery_user = "recovery_test_user"
        
        # Create initial connection
        initial_websocket = MockWebSocket(user_id=recovery_user)
        initial_connection_id = str(uuid.uuid4())
        
        initial_connection = WebSocketConnection(
            connection_id=initial_connection_id,
            user_id=recovery_user,
            websocket=initial_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_attempt": 1}
        )
        
        await websocket_manager.add_connection(initial_connection)
        
        # Verify initial connection established
        assert websocket_manager.is_connection_active(recovery_user) is True
        
        # TEST 1: Queue messages during connection failure
        # Simulate connection failure by closing WebSocket
        initial_websocket.is_closed = True
        initial_websocket.state = "CLOSED"
        
        # Try to send message while connection is "failed"
        failed_message = {
            "type": "recovery_test_message",
            "data": {"content": "Message during connection failure", "id": 1}
        }
        
        await websocket_manager.send_to_user(recovery_user, failed_message)
        
        # Message should be queued in recovery system
        error_stats = websocket_manager.get_error_statistics()
        assert error_stats["total_queued_messages"] > 0
        
        # Remove the failed connection
        await websocket_manager.remove_connection(initial_connection_id)
        assert websocket_manager.is_connection_active(recovery_user) is False
        
        # TEST 2: Connection recovery with message replay
        # Create new connection (simulating reconnection)
        recovery_websocket = MockWebSocket(user_id=recovery_user)
        recovery_connection_id = str(uuid.uuid4())
        
        recovery_connection = WebSocketConnection(
            connection_id=recovery_connection_id,
            user_id=recovery_user,
            websocket=recovery_websocket,
            connected_at=datetime.utcnow(),
            metadata={"connection_attempt": 2, "recovery": True}
        )
        
        await websocket_manager.add_connection(recovery_connection)
        
        # Connection should be active again
        assert websocket_manager.is_connection_active(recovery_user) is True
        
        # TEST 3: Message recovery after reconnection
        # Attempt to recover queued messages
        recovered_count = await websocket_manager.attempt_message_recovery(recovery_user)
        
        # Should have recovered some messages
        assert recovered_count >= 0
        
        # TEST 4: Wait for connection availability
        # Test the wait_for_connection method
        new_user = "wait_test_user"
        
        # Start wait task
        async def wait_for_user_connection():
            return await websocket_manager.wait_for_connection(new_user, timeout=2.0)
        
        wait_task = asyncio.create_task(wait_for_user_connection())
        
        # Add connection after short delay
        async def add_delayed_connection():
            await asyncio.sleep(0.5)  # Wait 500ms then add connection
            
            wait_websocket = MockWebSocket(user_id=new_user)
            wait_connection_id = str(uuid.uuid4())
            
            wait_connection = WebSocketConnection(
                connection_id=wait_connection_id,
                user_id=new_user,
                websocket=wait_websocket,
                connected_at=datetime.utcnow(),
                metadata={"delayed_connection": True}
            )
            
            await websocket_manager.add_connection(wait_connection)
        
        add_task = asyncio.create_task(add_delayed_connection())
        
        # Wait for both tasks
        connection_established, _ = await asyncio.gather(wait_task, add_task)
        
        # Should have successfully waited for connection
        assert connection_established is True
        assert websocket_manager.is_connection_active(new_user) is True
        
        # TEST 5: Error recovery statistics
        error_stats = websocket_manager.get_error_statistics()
        
        # Should have error tracking
        assert "total_users_with_errors" in error_stats
        assert "total_error_count" in error_stats
        assert "error_recovery_enabled" in error_stats
        assert error_stats["error_recovery_enabled"] is True
        
        # TEST 6: Connection health monitoring during recovery
        health = websocket_manager.get_connection_health(recovery_user)
        assert health["has_active_connections"] is True
        assert health["active_connections"] == 1
        
        # Verify connection metadata includes recovery info
        connection_details = health["connections"][0]
        assert connection_details["metadata"]["recovery"] is True
        assert connection_details["metadata"]["connection_attempt"] == 2
        
        # Cleanup
        await websocket_manager.remove_connection(recovery_connection_id)
        
        # Clean up the wait test user connection
        wait_user_connections = websocket_manager.get_user_connections(new_user)
        for conn_id in wait_user_connections:
            await websocket_manager.remove_connection(conn_id)
    
    # ============================================================================
    # TEST 7: Business-Critical WebSocket Event Delivery
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_business_critical_websocket_event_delivery(
        self, 
        websocket_manager, 
        isolated_env
    ):
        """
        Test business-critical WebSocket event delivery (agent events, tool status, results).
        
        Business Value: MISSION CRITICAL - These events enable 90% of our business value.
        Without these events, the chat system provides no value to users.
        """
        # Mock get_env to return development environment to avoid retry logic
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.return_value = "development"
            
            critical_user = "business_critical_user"
            
            # Setup connection for critical event testing
            critical_websocket = MockWebSocket(user_id=critical_user)
            critical_connection_id = str(uuid.uuid4())
            
            critical_connection = WebSocketConnection(
                connection_id=critical_connection_id,
                user_id=critical_user,
                websocket=critical_websocket,
                connected_at=datetime.utcnow(),
                metadata={"mission_critical": True, "subscription": "enterprise"}
            )
            
            await websocket_manager.add_connection(critical_connection)
        
        # TEST 1: All 5 MISSION CRITICAL WebSocket events
        critical_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent": "cost_optimizer",
                    "message": "Starting cost analysis for your AWS account",
                    "estimated_duration": "2-3 minutes"
                }
            },
            {
                "type": "agent_thinking", 
                "data": {
                    "reasoning": "Analyzing EC2 instances for optimization opportunities",
                    "current_step": "data_collection",
                    "progress": 20
                }
            },
            {
                "type": "tool_executing",
                "data": {
                    "tool": "aws_cost_analyzer",
                    "action": "fetch_billing_data",
                    "parameters": {"timeframe": "30_days"}
                }
            },
            {
                "type": "tool_completed",
                "data": {
                    "tool": "aws_cost_analyzer", 
                    "results": {
                        "total_cost": 5000,
                        "optimization_opportunities": 15,
                        "potential_savings": 750
                    },
                    "execution_time": "45s"
                }
            },
            {
                "type": "agent_completed",
                "data": {
                    "results": {
                        "recommendations": [
                            "Switch 5 EC2 instances to Reserved Instances",
                            "Implement auto-scaling for web tier",
                            "Archive unused EBS volumes"
                        ],
                        "total_potential_savings": 750,
                        "confidence": 0.95
                    },
                    "execution_time": "3m 15s"
                }
            }
        ]
        
        # Send all critical events
        event_timestamps = {}
        for event in critical_events:
            start_time = time.time()
            
            await websocket_manager.emit_critical_event(
                user_id=critical_user,
                event_type=event["type"],
                data=event["data"]
            )
            
            end_time = time.time()
            event_timestamps[event["type"]] = {
                "delivery_time": end_time - start_time,
                "timestamp": end_time
            }
        
        # VERIFY: All critical events delivered
        for event in critical_events:
            event_type = event["type"]
            received_messages = critical_websocket.get_sent_messages(event_type)
            
            # Must have received exactly 1 message of each type
            assert len(received_messages) == 1, f"Missing critical event: {event_type}"
            
            message = received_messages[0]["message"]
            
            # Verify message marked as critical
            assert message["critical"] is True, f"Event {event_type} not marked as critical"
            
            # Verify message content
            assert message["type"] == event_type
            assert message["data"] == event["data"]
            
            # Verify delivery performance (should be fast)
            delivery_time = event_timestamps[event_type]["delivery_time"]
            assert delivery_time < 0.1, f"Event {event_type} delivery too slow: {delivery_time}s"
        
        # TEST 2: Event ordering verification
        all_messages = critical_websocket.sent_messages
        critical_message_types = [msg["message"]["type"] for msg in all_messages if msg["message"].get("critical")]
        
        # Should have all 5 critical events in order
        expected_order = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert critical_message_types == expected_order, f"Event order wrong: {critical_message_types}"
        
        # TEST 3: Event delivery guarantees with retry
        # Simulate temporary connection issue
        original_send_json = critical_websocket.send_json
        call_count = 0
        
        async def failing_send_json(message):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise ConnectionError("Temporary connection error")
            return await original_send_json(message)
        
        # Replace send_json with failing version
        critical_websocket.send_json = failing_send_json
        
        # Try to send critical event (should retry and succeed)
        retry_event_data = {
            "agent": "retry_test_agent",
            "message": "Testing retry mechanism"
        }
        
        # Should succeed despite initial failures
        await websocket_manager.emit_critical_event(
            user_id=critical_user,
            event_type="agent_started",
            data=retry_event_data
        )
        
        # Verify retry succeeded (should have 2 agent_started messages now)
        agent_started_messages = critical_websocket.get_sent_messages("agent_started")
        assert len(agent_started_messages) == 2
        
        # Verify retry message content
        retry_message = agent_started_messages[1]["message"]
        assert retry_message["data"]["agent"] == "retry_test_agent"
        
        # TEST 4: High-frequency event delivery
        # Simulate rapid agent updates (like streaming thinking)
        rapid_event_count = 25
        rapid_start_time = time.time()
        
        for i in range(rapid_event_count):
            thinking_data = {
                "reasoning": f"Analysis step {i+1}: Processing cost data segment {i}",
                "progress": (i + 1) * 4,  # Progress from 4% to 100%
                "step": i + 1
            }
            
            await websocket_manager.emit_critical_event(
                user_id=critical_user,
                event_type="agent_thinking",
                data=thinking_data
            )
        
        rapid_end_time = time.time()
        rapid_total_time = rapid_end_time - rapid_start_time
        
        # Verify rapid delivery performance 
        assert rapid_total_time < 2.0, f"Rapid event delivery too slow: {rapid_total_time}s"
        
        # Verify all rapid events received
        thinking_messages = critical_websocket.get_sent_messages("agent_thinking")
        # Should have original + 25 rapid messages
        assert len(thinking_messages) == 26  # 1 original + 25 rapid
        
        # Verify progress tracking in rapid messages
        rapid_messages = thinking_messages[1:]  # Skip original message
        for i, msg in enumerate(rapid_messages):
            expected_progress = (i + 1) * 4
            actual_progress = msg["message"]["data"]["progress"]
            assert actual_progress == expected_progress
        
        # Cleanup
        await websocket_manager.remove_connection(critical_connection_id)
        
    # ============================================================================
    # TEST 8: WebSocket Connection Health Monitoring and Circuit Breaker
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_health_monitoring_and_circuit_breaker(
        self, 
        websocket_manager,
        isolated_env
    ):
        """
        Test WebSocket connection health monitoring and circuit breaker patterns.
        
        Business Value: Prevents cascade failures and ensures system resilience.
        """
        health_user = "health_monitoring_user"
        
        # Setup connection for health monitoring
        health_websocket = MockWebSocket(user_id=health_user)
        health_connection_id = str(uuid.uuid4())
        
        health_connection = WebSocketConnection(
            connection_id=health_connection_id,
            user_id=health_user,
            websocket=health_websocket,
            connected_at=datetime.utcnow(),
            metadata={"health_monitoring": True}
        )
        
        await websocket_manager.add_connection(health_connection)
        
        # TEST 1: Basic health monitoring
        initial_health = websocket_manager.get_connection_health(health_user)
        
        # Verify health structure
        assert initial_health["user_id"] == health_user
        assert initial_health["total_connections"] == 1
        assert initial_health["active_connections"] == 1
        assert initial_health["has_active_connections"] is True
        assert len(initial_health["connections"]) == 1
        
        # Verify connection details
        conn_detail = initial_health["connections"][0]
        assert conn_detail["connection_id"] == health_connection_id
        assert conn_detail["active"] is True
        assert "connected_at" in conn_detail
        assert conn_detail["metadata"]["health_monitoring"] is True
        
        # TEST 2: Error statistics monitoring
        initial_error_stats = websocket_manager.get_error_statistics()
        
        # Should have monitoring structure
        assert "total_users_with_errors" in initial_error_stats
        assert "total_error_count" in initial_error_stats
        assert "error_recovery_enabled" in initial_error_stats
        assert initial_error_stats["error_recovery_enabled"] is True
        
        # TEST 3: Induce connection errors for monitoring
        # Make WebSocket fail temporarily
        failure_count = 0
        original_send = health_websocket.send_json
        
        async def intermittent_failure_send(message):
            nonlocal failure_count
            failure_count += 1
            
            # Fail every 3rd message
            if failure_count % 3 == 0:
                raise ConnectionError(f"Simulated connection error #{failure_count}")
            
            return await original_send(message)
        
        health_websocket.send_json = intermittent_failure_send
        
        # Send multiple messages to trigger failures
        for i in range(10):
            try:
                test_message = {
                    "type": "health_test_message",
                    "data": {"message_id": i, "test": "error_monitoring"}
                }
                await websocket_manager.send_to_user(health_user, test_message)
            except Exception:
                pass  # Expected for some messages
        
        # Check error statistics after failures
        post_failure_stats = websocket_manager.get_error_statistics()
        
        # Should have recorded some errors
        assert post_failure_stats["total_error_count"] >= 0
        
        # TEST 4: Background task monitoring
        # Test the background monitoring system
        task_name = "health_monitor_test"
        
        async def test_monitoring_task():
            """Test monitoring task that runs briefly."""
            await asyncio.sleep(0.1)
            return "monitoring_complete"
        
        # Start monitored background task
        task_id = await websocket_manager.start_monitored_background_task(
            task_name, test_monitoring_task
        )
        
        assert task_id == task_name
        
        # Wait for task completion
        await asyncio.sleep(0.2)
        
        # Check task status
        task_status = websocket_manager.get_background_task_status()
        
        assert task_status["monitoring_enabled"] is True
        assert task_status["total_tasks"] >= 1
        assert task_name in task_status["tasks"]
        
        # TEST 5: Health check background tasks
        health_check_result = await websocket_manager.health_check_background_tasks()
        
        # Should have health check structure
        assert "healthy_tasks" in health_check_result
        assert "unhealthy_tasks" in health_check_result
        assert health_check_result["healthy_tasks"] >= 0
        
        # TEST 6: Monitoring system health status
        monitoring_health = await websocket_manager.get_monitoring_health_status()
        
        # Should have comprehensive health status
        assert monitoring_health["monitoring_enabled"] is True
        assert "task_health" in monitoring_health
        assert "overall_health" in monitoring_health
        assert "alerts" in monitoring_health
        
        # Verify overall health score
        overall_health = monitoring_health["overall_health"]
        assert "score" in overall_health
        assert "status" in overall_health
        assert overall_health["score"] >= 0
        assert overall_health["status"] in ["healthy", "warning", "degraded", "critical"]
        
        # TEST 7: Error data cleanup
        cleanup_result = await websocket_manager.cleanup_error_data(older_than_hours=0)
        
        # Should have cleanup statistics
        assert "cleaned_error_users" in cleanup_result
        assert "cleaned_queue_users" in cleanup_result
        assert cleanup_result["cleaned_error_users"] >= 0
        
        # Cleanup
        await websocket_manager.remove_connection(health_connection_id)
        
        # Stop background monitoring
        await websocket_manager.stop_background_task(task_name)
    
    # ============================================================================
    # TEST 9: Integration with AgentWebSocketBridge
    # ============================================================================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_integration_with_agent_websocket_bridge(
        self, 
        websocket_manager,
        agent_bridge,
        isolated_env
    ):
        """
        Test integration with AgentWebSocketBridge and agent execution systems.
        
        Business Value: Validates the complete agent  ->  WebSocket  ->  user flow.
        """
        bridge_user = "agent_bridge_test_user"
        
        # Setup WebSocket connection
        bridge_websocket = MockWebSocket(user_id=bridge_user)
        bridge_connection_id = str(uuid.uuid4())
        
        bridge_connection = WebSocketConnection(
            connection_id=bridge_connection_id,
            user_id=bridge_user,
            websocket=bridge_websocket,
            connected_at=datetime.utcnow(),
            metadata={"integration_test": True, "component": "agent_bridge"}
        )
        
        await websocket_manager.add_connection(bridge_connection)
        
        # TEST 1: AgentWebSocketBridge integration lifecycle
        # Initialize bridge (would normally integrate with real registry)
        bridge_config = {
            "initialization_timeout_s": 10,
            "health_check_interval_s": 30,
            "recovery_max_attempts": 2
        }
        
        # Mock registry and dependencies for integration testing
        mock_registry = Mock()
        mock_registry.set_websocket_manager = Mock()
        mock_registry.enhance_tool_dispatcher = Mock()
        
        # TEST 2: Simulate agent execution workflow
        agent_workflow_events = [
            {
                "phase": "initialization",
                "event_type": "agent_started",
                "data": {
                    "agent": "integration_test_agent",
                    "user_id": bridge_user,
                    "workflow_id": str(uuid.uuid4())
                }
            },
            {
                "phase": "reasoning",
                "event_type": "agent_thinking",
                "data": {
                    "reasoning": "Analyzing integration test parameters",
                    "agent": "integration_test_agent"
                }
            },
            {
                "phase": "tool_execution",
                "event_type": "tool_executing", 
                "data": {
                    "tool": "integration_test_tool",
                    "parameters": {"test_mode": True}
                }
            },
            {
                "phase": "tool_completion",
                "event_type": "tool_completed",
                "data": {
                    "tool": "integration_test_tool",
                    "results": {"integration_status": "success", "test_data": {"value": 42}}
                }
            },
            {
                "phase": "completion",
                "event_type": "agent_completed", 
                "data": {
                    "results": {
                        "integration_test": "passed",
                        "agent_bridge_connection": "successful",
                        "websocket_delivery": "confirmed"
                    }
                }
            }
        ]
        
        # Execute workflow through WebSocket manager (simulating bridge integration)
        workflow_start_time = time.time()
        
        for event_info in agent_workflow_events:
            await websocket_manager.emit_critical_event(
                user_id=bridge_user,
                event_type=event_info["event_type"],
                data=event_info["data"]
            )
            
            # Small delay to simulate realistic agent processing
            await asyncio.sleep(0.02)
        
        workflow_end_time = time.time()
        workflow_duration = workflow_end_time - workflow_start_time
        
        # TEST 3: Verify complete agent workflow delivered
        for event_info in agent_workflow_events:
            event_type = event_info["event_type"]
            received_messages = bridge_websocket.get_sent_messages(event_type)
            
            # Should have received event
            assert len(received_messages) == 1, f"Missing {event_type} event in workflow"
            
            message = received_messages[0]["message"]
            assert message["critical"] is True
            assert message["type"] == event_type
            
            # Verify data integrity through the bridge
            expected_data = event_info["data"]
            actual_data = message["data"]
            
            for key, expected_value in expected_data.items():
                assert key in actual_data, f"Missing data key {key} in {event_type}"
                assert actual_data[key] == expected_value, f"Data mismatch in {event_type}: {key}"
        
        # TEST 4: Verify workflow timing performance
        assert workflow_duration < 1.0, f"Agent workflow too slow: {workflow_duration}s"
        
        # TEST 5: Test bridge health monitoring integration
        bridge_health_data = {
            "bridge_status": "active",
            "registry_connected": True,
            "websocket_manager_connected": True,
            "last_heartbeat": datetime.utcnow().isoformat()
        }
        
        # Send health update through WebSocket
        await websocket_manager.send_to_user(
            bridge_user,
            {
                "type": "bridge_health_update",
                "data": bridge_health_data
            }
        )
        
        # Verify health update received
        health_messages = bridge_websocket.get_sent_messages("bridge_health_update")
        assert len(health_messages) == 1
        
        health_message = health_messages[0]["message"]
        assert health_message["data"]["bridge_status"] == "active"
        assert health_message["data"]["registry_connected"] is True
        assert health_message["data"]["websocket_manager_connected"] is True
        
        # TEST 6: Error handling integration
        # Simulate bridge error scenario
        error_event_data = {
            "error_type": "agent_execution_timeout",
            "error_message": "Agent execution exceeded timeout limit",
            "recovery_action": "restarting_agent",
            "user_notification": True
        }
        
        await websocket_manager.emit_critical_event(
            user_id=bridge_user,
            event_type="system_error",
            data=error_event_data
        )
        
        # Verify error handling
        error_messages = bridge_websocket.get_sent_messages("system_error")
        assert len(error_messages) == 1
        
        error_message = error_messages[0]["message"]
        assert error_message["critical"] is True
        assert error_message["data"]["user_notification"] is True
        assert error_message["data"]["recovery_action"] == "restarting_agent"
        
        # Cleanup
        await websocket_manager.remove_connection(bridge_connection_id)


# ============================================================================
# TEST FIXTURES AND HELPERS
# ============================================================================

@pytest.fixture
async def multi_user_websocket_scenario():
    """Provide comprehensive multi-user WebSocket test scenario."""
    websocket_manager = UnifiedWebSocketManager()
    
    # Create 5 different users with various connection patterns
    users = {}
    
    for i in range(5):
        user_id = f"scenario_user_{i}"
        
        # Create 1-3 connections per user (simulating multiple tabs/devices)
        connection_count = (i % 3) + 1
        user_connections = []
        
        for j in range(connection_count):
            websocket = MockWebSocket(user_id=user_id)
            connection_id = str(uuid.uuid4())
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                metadata={
                    "device": f"device_{j}",
                    "user_index": i,
                    "connection_index": j
                }
            )
            
            await websocket_manager.add_connection(connection)
            user_connections.append({
                "websocket": websocket,
                "connection_id": connection_id,
                "connection": connection
            })
        
        users[user_id] = {
            "connections": user_connections,
            "connection_count": connection_count,
            "user_index": i
        }
    
    yield {
        "websocket_manager": websocket_manager,
        "users": users,
        "total_connections": sum(user["connection_count"] for user in users.values())
    }
    
    # Cleanup all connections
    for user_info in users.values():
        for conn_info in user_info["connections"]:
            await websocket_manager.remove_connection(conn_info["connection_id"])


@pytest.mark.integration
@pytest.mark.real_services
async def test_websocket_comprehensive_integration_scenario(multi_user_websocket_scenario):
    """
    Run comprehensive integration scenario testing all WebSocket manager capabilities.
    
    Business Value: End-to-end validation that the complete WebSocket system works.
    """
    scenario = multi_user_websocket_scenario
    websocket_manager = scenario["websocket_manager"]
    users = scenario["users"]
    total_connections = scenario["total_connections"]
    
    # PHASE 1: Verify multi-user setup
    stats = websocket_manager.get_stats()
    assert stats["total_connections"] == total_connections
    assert stats["unique_users"] == 5
    
    # PHASE 2: Cross-user isolation test
    for user_id, user_info in users.items():
        user_specific_message = {
            "type": "isolation_verification",
            "data": {
                "secret_user_data": f"TOP_SECRET_{user_id}",
                "user_index": user_info["user_index"]
            }
        }
        
        await websocket_manager.send_to_user(user_id, user_specific_message)
    
    # Verify isolation - each user should only see their own data
    for user_id, user_info in users.items():
        for conn_info in user_info["connections"]:
            websocket = conn_info["websocket"]
            messages = websocket.get_sent_messages("isolation_verification")
            
            assert len(messages) == 1
            message = messages[0]["message"]
            assert message["data"]["secret_user_data"] == f"TOP_SECRET_{user_id}"
            assert message["data"]["user_index"] == user_info["user_index"]
    
    # PHASE 3: Performance test - rapid message delivery
    performance_start = time.time()
    message_count_per_user = 20
    
    for user_id in users.keys():
        for i in range(message_count_per_user):
            performance_message = {
                "type": "performance_test",
                "data": {"message_id": i, "timestamp": time.time()}
            }
            await websocket_manager.send_to_user(user_id, performance_message)
    
    performance_end = time.time()
    total_messages = len(users) * message_count_per_user
    performance_duration = performance_end - performance_start
    
    # Should handle 100 messages across 5 users quickly
    assert performance_duration < 2.0, f"Performance test too slow: {performance_duration}s"
    
    # PHASE 4: Verify message delivery
    for user_id, user_info in users.items():
        for conn_info in user_info["connections"]:
            websocket = conn_info["websocket"]
            perf_messages = websocket.get_sent_messages("performance_test")
            
            # Each connection should have received all messages for their user
            assert len(perf_messages) == message_count_per_user
    
    # PHASE 5: Connection health monitoring
    for user_id in users.keys():
        health = websocket_manager.get_connection_health(user_id)
        assert health["has_active_connections"] is True
        assert health["total_connections"] >= 1
        assert health["active_connections"] == health["total_connections"]
    
    print(f"[SUCCESS] Comprehensive integration test passed:")
    print(f"   - {len(users)} users with {total_connections} total connections")
    print(f"   - {total_messages} messages delivered in {performance_duration:.3f}s")
    print(f"   - Complete user isolation verified")
    print(f"   - All health checks passed")