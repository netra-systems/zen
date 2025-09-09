"""
Unit Tests for WebSocket Connection Lifecycle and Multi-User Business Logic

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Connection management serves all user tiers
- Business Goal: Reliable multi-user WebSocket infrastructure for concurrent AI chat sessions
- Value Impact: Enables secure, isolated, concurrent AI interactions worth $120K+ MRR
- Strategic Impact: Foundation for scalable multi-tenant AI platform supporting 100+ concurrent users

This test suite validates critical WebSocket connection lifecycle and multi-user business logic:
1. Connection Lifecycle - Connect, authenticate, maintain, disconnect, cleanup
2. User Isolation - Strict separation between different users' data and sessions
3. Multi-User Concurrency - Multiple users can interact simultaneously without interference  
4. Resource Management - Proper cleanup prevents memory leaks and connection exhaustion
5. Race Condition Prevention - Concurrent operations don't corrupt connection state
6. Connection Health - Monitoring, recovery, and graceful degradation
7. Security Boundaries - Each user can only access their own data and conversations

CRITICAL: Multi-user isolation prevents:
- Data leakage between customers (GDPR/security requirement)  
- Cross-user message delivery (privacy violation)
- Session hijacking (security vulnerability)
- Resource exhaustion attacks (availability issue)

Following TEST_CREATION_GUIDE.md:
- Real connection lifecycle validation (not infrastructure mocks)
- SSOT patterns for user isolation and connection management
- Proper test categorization (@pytest.mark.unit)
- Tests that FAIL HARD when isolation is broken
- Focus on connection management business value
"""

import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection
)
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, ensure_user_id, ensure_thread_id
from test_framework.base_unit_test import BaseUnitTest


class TestWebSocketConnectionLifecycleBusinessLogic(BaseUnitTest):
    """Test WebSocket connection lifecycle for reliable connection management."""
    
    def setUp(self):
        """Set up connection lifecycle testing."""
        self.manager = UnifiedWebSocketManager()
        
        # Create mock WebSocket factory
        self.connection_counter = 0
        
    def create_mock_websocket(self, host="127.0.0.1", port=None):
        """Create mock WebSocket with unique client info."""
        self.connection_counter += 1
        if port is None:
            port = 45000 + self.connection_counter
            
        mock_websocket = Mock()
        mock_websocket.client = Mock()
        mock_websocket.client.host = host
        mock_websocket.client.port = port
        mock_websocket.send_json = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        return mock_websocket

    @pytest.mark.unit
    async def test_connection_lifecycle_complete_flow(self):
        """Test complete connection lifecycle from connect to cleanup."""
        # Business value: Complete lifecycle ensures reliable connection management
        
        user_id = "lifecycle-user-123"
        thread_id = "lifecycle-thread-456"
        
        # Step 1: Connection establishment
        mock_websocket = self.create_mock_websocket()
        
        connection_id = await self.manager.add_connection(
            user_id=user_id,
            websocket=mock_websocket,
            thread_id=thread_id
        )
        
        # Validate connection was established
        assert connection_id is not None, "Must create connection ID"
        assert connection_id in self.manager.connections, "Must store connection"
        assert user_id in self.manager.user_connections, "Must map user to connection"
        
        connection = self.manager.connections[connection_id]
        assert connection.is_active is True, "Connection must be active after establishment"
        assert connection.user_id == user_id, "Must preserve user context"
        
        # Step 2: Connection usage (send messages)
        test_message = {"type": "test_message", "content": "Hello"}
        send_result = await self.manager.send_to_user(user_id, test_message)
        
        assert send_result is True, "Must successfully send messages during active lifecycle"
        mock_websocket.send_json.assert_called_once_with(test_message)
        
        # Validate activity tracking
        assert connection.messages_sent == 1, "Must track message activity"
        assert connection.last_activity is not None, "Must update activity timestamp"
        
        # Step 3: Connection termination
        await self.manager.remove_connection(connection_id)
        
        # Validate cleanup
        assert connection_id not in self.manager.connections, "Must remove connection from storage"
        assert connection.is_active is False, "Must mark connection as inactive"
        
        # Validate user mapping cleanup
        if user_id in self.manager.user_connections:
            user_connections = self.manager.user_connections[user_id]
            assert connection_id not in [conn.connection_id for conn in user_connections], "Must clean user mapping"

    @pytest.mark.unit
    async def test_connection_authentication_lifecycle_integration(self):
        """Test connection lifecycle integrates with authentication properly."""
        # Business value: Authenticated connections enable secure multi-user access
        
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock authentication success
        mock_websocket = self.create_mock_websocket()
        mock_websocket.client_state = Mock()
        mock_websocket.headers = {"authorization": "Bearer valid-token"}
        
        # Mock auth service
        mock_auth_service = Mock()
        mock_auth_result = Mock()
        mock_auth_result.success = True
        mock_auth_result.user_id = "auth-user-789"
        mock_auth_result.email = "auth@example.com"
        mock_auth_result.permissions = ["chat:use"]
        
        mock_user_context = Mock()
        mock_user_context.user_id = "auth-user-789"
        mock_user_context.websocket_client_id = "ws-auth-client"
        mock_user_context.thread_id = "auth-thread-101"
        
        mock_auth_service.authenticate_websocket.return_value = (mock_auth_result, mock_user_context)
        authenticator._auth_service = mock_auth_service
        
        # Authenticate connection
        auth_result = await authenticator.authenticate_websocket_connection(mock_websocket)
        
        # Validate authentication success
        assert auth_result.success is True, "Authentication must succeed for lifecycle integration"
        
        # Add authenticated connection to manager
        connection_id = await self.manager.add_connection(
            user_id=auth_result.user_context.user_id,
            websocket=mock_websocket,
            thread_id=auth_result.user_context.thread_id
        )
        
        # Validate authenticated connection properties
        connection = self.manager.connections[connection_id]
        assert connection.user_id == mock_auth_result.user_id, "Must preserve authenticated user ID"
        assert connection.thread_id == mock_user_context.thread_id, "Must preserve authenticated thread context"

    @pytest.mark.unit
    async def test_connection_health_monitoring_during_lifecycle(self):
        """Test connection health monitoring throughout connection lifecycle."""
        # Business value: Health monitoring enables proactive connection management
        
        user_id = "health-monitor-user"
        mock_websocket = self.create_mock_websocket()
        
        # Add connection
        connection_id = await self.manager.add_connection(user_id, mock_websocket)
        connection = self.manager.connections[connection_id]
        
        # Track initial health state
        initial_created_at = connection.created_at
        initial_activity = connection.last_activity
        initial_messages = connection.messages_sent
        
        # Simulate connection activity
        await asyncio.sleep(0.01)  # Small delay
        
        # Send message to update activity
        await self.manager.send_to_user(user_id, {"type": "health_check"})
        
        # Validate health tracking updates
        assert connection.last_activity > initial_activity, "Must update activity timestamp"
        assert connection.messages_sent == initial_messages + 1, "Must track message count"
        assert connection.created_at == initial_created_at, "Must preserve creation timestamp"
        assert connection.is_active is True, "Must remain active during healthy operation"
        
        # Get connection statistics for health monitoring
        stats = self.manager.get_connection_stats()
        
        assert stats["active_connections"] >= 1, "Must track active connections"
        assert stats["total_messages_sent"] >= 1, "Must track total message activity"

    @pytest.mark.unit
    async def test_connection_graceful_shutdown_lifecycle(self):
        """Test graceful connection shutdown preserves data integrity."""
        # Business value: Graceful shutdown prevents data loss and corruption
        
        user_id = "graceful-shutdown-user"
        mock_websocket = self.create_mock_websocket()
        
        # Add connection and send several messages
        connection_id = await self.manager.add_connection(user_id, mock_websocket)
        
        # Simulate message activity before shutdown
        for i in range(5):
            await self.manager.send_to_user(user_id, {"type": "message", "index": i})
        
        connection = self.manager.connections[connection_id]
        pre_shutdown_messages = connection.messages_sent
        pre_shutdown_activity = connection.last_activity
        
        # Perform graceful shutdown
        await connection.close(code=1000, reason="Graceful shutdown")
        await self.manager.remove_connection(connection_id)
        
        # Validate data preservation during shutdown
        assert connection.messages_sent == pre_shutdown_messages, "Must preserve message count during shutdown"
        assert connection.last_activity == pre_shutdown_activity, "Must preserve activity timestamp"
        assert connection.is_active is False, "Must mark as inactive after graceful shutdown"
        
        # Verify WebSocket close was called
        mock_websocket.close.assert_called_once_with(code=1000, reason="Graceful shutdown")


class TestMultiUserIsolationBusinessLogic(BaseUnitTest):
    """Test multi-user isolation for secure concurrent operations."""
    
    def setUp(self):
        """Set up multi-user isolation testing."""
        self.manager = UnifiedWebSocketManager()
        self.connection_counter = 0

    def create_mock_websocket_for_user(self, user_id):
        """Create mock WebSocket with user-specific client info."""
        self.connection_counter += 1
        
        mock_websocket = Mock()
        mock_websocket.client = Mock()
        mock_websocket.client.host = f"client-{user_id}.example.com"
        mock_websocket.client.port = 45000 + self.connection_counter
        mock_websocket.send_json = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        return mock_websocket

    @pytest.mark.unit
    async def test_user_data_isolation_prevents_cross_user_access(self):
        """Test user data isolation prevents cross-user data access."""
        # Business value: Data isolation prevents privacy violations and GDPR compliance issues
        
        # Create two different users
        user1_id = "isolated-user-1"
        user2_id = "isolated-user-2"
        
        mock_websocket1 = self.create_mock_websocket_for_user(user1_id)
        mock_websocket2 = self.create_mock_websocket_for_user(user2_id)
        
        # Add connections for both users
        conn1_id = await self.manager.add_connection(
            user1_id, mock_websocket1, thread_id="thread-user1-123"
        )
        conn2_id = await self.manager.add_connection(
            user2_id, mock_websocket2, thread_id="thread-user2-456"
        )
        
        # Send message to user 1
        user1_message = {
            "type": "confidential_data",
            "payload": {
                "user_private_info": "User 1 sensitive data",
                "account_details": "User 1 financial information"
            }
        }
        
        result = await self.manager.send_to_user(user1_id, user1_message)
        assert result is True, "Must successfully send to user 1"
        
        # Validate only user 1 received the message
        mock_websocket1.send_json.assert_called_once_with(user1_message)
        mock_websocket2.send_json.assert_not_called()
        
        # Validate connection isolation
        user1_connections = await self.manager.get_user_connections(user1_id)
        user2_connections = await self.manager.get_user_connections(user2_id)
        
        assert len(user1_connections) == 1, "User 1 must have exactly one connection"
        assert len(user2_connections) == 1, "User 2 must have exactly one connection"
        assert user1_connections[0].user_id == user1_id, "User 1 connection must be isolated"
        assert user2_connections[0].user_id == user2_id, "User 2 connection must be isolated"
        
        # Validate thread isolation
        assert user1_connections[0].thread_id == "thread-user1-123", "User 1 thread must be isolated"
        assert user2_connections[0].thread_id == "thread-user2-456", "User 2 thread must be isolated"

    @pytest.mark.unit
    async def test_concurrent_multi_user_message_delivery_isolation(self):
        """Test concurrent message delivery maintains user isolation."""
        # Business value: Concurrent isolation enables scalable multi-user platform
        
        # Create multiple users for concurrent testing
        users = [f"concurrent-user-{i}" for i in range(5)]
        websockets = {}
        connection_ids = {}
        
        # Set up all user connections
        for user_id in users:
            websocket = self.create_mock_websocket_for_user(user_id)
            websockets[user_id] = websocket
            connection_ids[user_id] = await self.manager.add_connection(
                user_id, websocket, thread_id=f"thread-{user_id}"
            )
        
        # Send different messages to each user concurrently
        async def send_user_message(user_id):
            message = {
                "type": "user_specific_data",
                "payload": {
                    "user_id": user_id,
                    "private_data": f"Confidential information for {user_id}",
                    "timestamp": time.time()
                }
            }
            return await self.manager.send_to_user(user_id, message)
        
        # Execute concurrent sends
        send_tasks = [send_user_message(user_id) for user_id in users]
        results = await asyncio.gather(*send_tasks)
        
        # Validate all sends succeeded
        assert all(result is True for result in results), "All concurrent sends must succeed"
        
        # Validate message isolation - each user only got their message
        for user_id in users:
            websocket = websockets[user_id]
            websocket.send_json.assert_called_once()
            
            # Get the message that was sent
            sent_message = websocket.send_json.call_args[0][0]
            assert sent_message["payload"]["user_id"] == user_id, f"User {user_id} must only receive their own message"
            assert sent_message["payload"]["private_data"] == f"Confidential information for {user_id}", "Must preserve user-specific data"

    @pytest.mark.unit
    async def test_user_connection_cleanup_isolation(self):
        """Test user connection cleanup maintains isolation boundaries."""
        # Business value: Proper cleanup prevents resource leaks and cross-user contamination
        
        # Create users with multiple connections each
        user1_id = "cleanup-user-1"
        user2_id = "cleanup-user-2"
        
        # User 1: 3 connections
        user1_connections = []
        for i in range(3):
            websocket = self.create_mock_websocket_for_user(f"{user1_id}-{i}")
            conn_id = await self.manager.add_connection(
                user1_id, websocket, thread_id=f"thread-{user1_id}-{i}"
            )
            user1_connections.append(conn_id)
        
        # User 2: 2 connections  
        user2_connections = []
        for i in range(2):
            websocket = self.create_mock_websocket_for_user(f"{user2_id}-{i}")
            conn_id = await self.manager.add_connection(
                user2_id, websocket, thread_id=f"thread-{user2_id}-{i}"
            )
            user2_connections.append(conn_id)
        
        # Validate initial state
        user1_conn_list = await self.manager.get_user_connections(user1_id)
        user2_conn_list = await self.manager.get_user_connections(user2_id)
        
        assert len(user1_conn_list) == 3, "User 1 must have 3 connections"
        assert len(user2_conn_list) == 2, "User 2 must have 2 connections"
        
        # Remove one connection from user 1
        await self.manager.remove_connection(user1_connections[1])
        
        # Validate user 1 cleanup doesn't affect user 2
        user1_conn_list_after = await self.manager.get_user_connections(user1_id)
        user2_conn_list_after = await self.manager.get_user_connections(user2_id)
        
        assert len(user1_conn_list_after) == 2, "User 1 must have 2 connections after cleanup"
        assert len(user2_conn_list_after) == 2, "User 2 connections must be unaffected"
        
        # Validate removed connection is not accessible
        assert user1_connections[1] not in self.manager.connections, "Removed connection must not be accessible"

    @pytest.mark.unit
    async def test_broadcast_message_respects_user_isolation(self):
        """Test broadcast messages respect user isolation boundaries."""
        # Business value: Controlled broadcasts enable system notifications without breaking isolation
        
        # Create users with different permission levels
        admin_user = "admin-user-123"
        regular_user1 = "regular-user-456"
        regular_user2 = "regular-user-789"
        
        admin_websocket = self.create_mock_websocket_for_user(admin_user)
        regular_websocket1 = self.create_mock_websocket_for_user(regular_user1)
        regular_websocket2 = self.create_mock_websocket_for_user(regular_user2)
        
        # Add connections
        await self.manager.add_connection(admin_user, admin_websocket)
        await self.manager.add_connection(regular_user1, regular_websocket1)
        await self.manager.add_connection(regular_user2, regular_websocket2)
        
        # Send broadcast message
        broadcast_message = {
            "type": "system_announcement",
            "payload": {
                "message": "System maintenance scheduled",
                "priority": "high",
                "applies_to": "all_users"
            },
            "timestamp": time.time()
        }
        
        result = await self.manager.broadcast_to_all(broadcast_message)
        assert result is True, "Broadcast must succeed"
        
        # Validate all users received the broadcast
        admin_websocket.send_json.assert_called_once_with(broadcast_message)
        regular_websocket1.send_json.assert_called_once_with(broadcast_message)
        regular_websocket2.send_json.assert_called_once_with(broadcast_message)
        
        # Validate each user's connection tracking is maintained
        admin_conn = await self.manager.get_user_connections(admin_user)
        regular1_conn = await self.manager.get_user_connections(regular_user1)
        regular2_conn = await self.manager.get_user_connections(regular_user2)
        
        assert admin_conn[0].messages_sent == 1, "Admin connection must track broadcast"
        assert regular1_conn[0].messages_sent == 1, "Regular user 1 connection must track broadcast"
        assert regular2_conn[0].messages_sent == 1, "Regular user 2 connection must track broadcast"


class TestConcurrentConnectionManagement(BaseUnitTest):
    """Test concurrent connection management for race condition prevention."""
    
    def setUp(self):
        """Set up concurrent connection testing."""
        self.manager = UnifiedWebSocketManager()

    @pytest.mark.unit
    async def test_concurrent_connection_addition_thread_safety(self):
        """Test concurrent connection additions are thread-safe."""
        # Business value: Thread safety prevents connection corruption during high load
        
        # Create concurrent connection addition tasks
        async def add_user_connection(user_index):
            user_id = f"concurrent_user_{user_index}"
            mock_websocket = Mock()
            mock_websocket.client = Mock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 45000 + user_index
            mock_websocket.send_json = AsyncMock()
            mock_websocket.close = AsyncMock()
            
            return await self.manager.add_connection(
                user_id, mock_websocket, thread_id=f"thread_{user_index}"
            )
        
        # Execute 20 concurrent connection additions
        connection_tasks = [add_user_connection(i) for i in range(20)]
        connection_ids = await asyncio.gather(*connection_tasks)
        
        # Validate all connections were created successfully
        assert len(connection_ids) == 20, "Must create all 20 connections concurrently"
        assert len(set(connection_ids)) == 20, "All connection IDs must be unique"
        assert all(conn_id in self.manager.connections for conn_id in connection_ids), "All connections must be stored"
        
        # Validate connection count
        stats = self.manager.get_connection_stats()
        assert stats["active_connections"] == 20, "Must track all concurrent connections"
        assert stats["unique_users"] == 20, "Must track all unique users"

    @pytest.mark.unit
    async def test_concurrent_message_sending_user_isolation(self):
        """Test concurrent message sending maintains user isolation."""
        # Business value: Message isolation under load prevents cross-user data leakage
        
        # Set up multiple users
        users = [f"message_user_{i}" for i in range(10)]
        websockets = {}
        
        # Add connections for all users
        for user_id in users:
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.client = Mock()
            mock_websocket.client.host = "127.0.0.1" 
            mock_websocket.client.port = 45000 + hash(user_id) % 1000
            
            websockets[user_id] = mock_websocket
            await self.manager.add_connection(user_id, mock_websocket)
        
        # Send concurrent messages to all users
        async def send_user_specific_message(user_id):
            message = {
                "type": "concurrent_test",
                "payload": {
                    "recipient": user_id,
                    "private_data": f"Secret data for {user_id}",
                    "timestamp": time.time()
                }
            }
            return await self.manager.send_to_user(user_id, message)
        
        # Execute concurrent sends
        send_tasks = [send_user_specific_message(user_id) for user_id in users]
        results = await asyncio.gather(*send_tasks)
        
        # Validate all sends succeeded
        assert all(result is True for result in results), "All concurrent message sends must succeed"
        
        # Validate message isolation - each user only got their specific message
        for user_id in users:
            websocket = websockets[user_id]
            websocket.send_json.assert_called_once()
            
            sent_message = websocket.send_json.call_args[0][0]
            assert sent_message["payload"]["recipient"] == user_id, f"User {user_id} must only get their message"
            assert sent_message["payload"]["private_data"] == f"Secret data for {user_id}", "Private data must be isolated"

    @pytest.mark.unit
    async def test_concurrent_connection_removal_stability(self):
        """Test concurrent connection removal maintains system stability."""
        # Business value: Stable removal prevents system corruption during disconnections
        
        # Create many connections
        connection_ids = []
        user_ids = []
        
        for i in range(15):
            user_id = f"removal_user_{i}"
            user_ids.append(user_id)
            
            mock_websocket = Mock()
            mock_websocket.client = Mock()
            mock_websocket.client.host = "127.0.0.1"
            mock_websocket.client.port = 45000 + i
            mock_websocket.close = AsyncMock()
            
            conn_id = await self.manager.add_connection(user_id, mock_websocket)
            connection_ids.append(conn_id)
        
        # Validate initial state
        assert len(self.manager.connections) == 15, "Must have 15 initial connections"
        
        # Remove connections concurrently (every other connection)
        removal_tasks = []
        removed_connection_ids = []
        
        for i in range(0, 15, 2):  # Remove connections at indices 0, 2, 4, 6, 8, 10, 12, 14
            removal_tasks.append(self.manager.remove_connection(connection_ids[i]))
            removed_connection_ids.append(connection_ids[i])
        
        # Execute concurrent removals
        await asyncio.gather(*removal_tasks)
        
        # Validate removal results
        remaining_connections = 15 - len(removed_connection_ids)
        assert len(self.manager.connections) == remaining_connections, f"Must have {remaining_connections} connections remaining"
        
        # Validate removed connections are gone
        for removed_id in removed_connection_ids:
            assert removed_id not in self.manager.connections, f"Connection {removed_id} must be removed"
        
        # Validate remaining connections are intact
        for i in range(1, 15, 2):  # Check connections at indices 1, 3, 5, 7, 9, 11, 13
            remaining_id = connection_ids[i]
            assert remaining_id in self.manager.connections, f"Connection {remaining_id} must remain"
            assert self.manager.connections[remaining_id].is_active is True, "Remaining connections must stay active"


class TestWebSocketSecurityBoundaries(BaseUnitTest):
    """Test WebSocket security boundaries for multi-user safety."""
    
    def setUp(self):
        """Set up security boundary testing."""
        self.manager = UnifiedWebSocketManager()

    @pytest.mark.unit
    async def test_user_cannot_access_other_user_connections(self):
        """Test users cannot access other users' connection information."""
        # Business value: Security boundaries prevent unauthorized access to user data
        
        # Create two users with sensitive data
        sensitive_user = "sensitive-user-123"
        attacker_user = "attacker-user-456"
        
        sensitive_websocket = Mock()
        sensitive_websocket.client = Mock()
        sensitive_websocket.client.host = "sensitive-client.internal"
        sensitive_websocket.client.port = 45001
        sensitive_websocket.send_json = AsyncMock()
        
        attacker_websocket = Mock()
        attacker_websocket.client = Mock()
        attacker_websocket.client.host = "attacker-client.external"
        attacker_websocket.client.port = 45002
        attacker_websocket.send_json = AsyncMock()
        
        # Add connections
        sensitive_conn_id = await self.manager.add_connection(
            sensitive_user, sensitive_websocket, thread_id="sensitive-thread-123"
        )
        attacker_conn_id = await self.manager.add_connection(
            attacker_user, attacker_websocket, thread_id="attacker-thread-456"
        )
        
        # Validate user can only access their own connections
        sensitive_connections = await self.manager.get_user_connections(sensitive_user)
        attacker_connections = await self.manager.get_user_connections(attacker_user)
        
        assert len(sensitive_connections) == 1, "Sensitive user must see only their connection"
        assert len(attacker_connections) == 1, "Attacker user must see only their connection"
        
        # Validate connection boundaries
        assert sensitive_connections[0].user_id == sensitive_user, "Must only return sensitive user's connection"
        assert attacker_connections[0].user_id == attacker_user, "Must only return attacker user's connection"
        
        # Validate thread isolation
        assert sensitive_connections[0].thread_id == "sensitive-thread-123", "Must preserve sensitive thread isolation"
        assert attacker_connections[0].thread_id == "attacker-thread-456", "Must preserve attacker thread isolation"

    @pytest.mark.unit
    async def test_message_delivery_security_boundaries(self):
        """Test message delivery respects security boundaries between users."""
        # Business value: Message security prevents data leakage and privacy violations
        
        # Create users with different security levels
        high_security_user = "classified-user-123"
        low_security_user = "public-user-456"
        
        high_security_websocket = Mock()
        high_security_websocket.send_json = AsyncMock()
        high_security_websocket.client = Mock()
        high_security_websocket.client.host = "classified.internal"
        high_security_websocket.client.port = 45001
        
        low_security_websocket = Mock()
        low_security_websocket.send_json = AsyncMock()
        low_security_websocket.client = Mock()
        low_security_websocket.client.host = "public.external"
        low_security_websocket.client.port = 45002
        
        # Add connections
        await self.manager.add_connection(high_security_user, high_security_websocket)
        await self.manager.add_connection(low_security_user, low_security_websocket)
        
        # Send classified message to high security user
        classified_message = {
            "type": "classified_data",
            "payload": {
                "classification": "SECRET",
                "data": "Highly classified financial optimization data",
                "access_level": "TOP_SECRET"
            },
            "security_context": "classified"
        }
        
        result = await self.manager.send_to_user(high_security_user, classified_message)
        assert result is True, "Must deliver classified message to authorized user"
        
        # Validate security boundaries - only high security user got the message
        high_security_websocket.send_json.assert_called_once_with(classified_message)
        low_security_websocket.send_json.assert_not_called()
        
        # Send public message to low security user
        public_message = {
            "type": "public_announcement",
            "payload": {
                "message": "System update completed successfully",
                "classification": "PUBLIC"
            }
        }
        
        result2 = await self.manager.send_to_user(low_security_user, public_message)
        assert result2 is True, "Must deliver public message to low security user"
        
        # Validate low security user got only their message
        low_security_websocket.send_json.assert_called_once_with(public_message)
        
        # Ensure high security user didn't get low security message
        assert high_security_websocket.send_json.call_count == 1, "High security user must only get classified message"

    @pytest.mark.unit
    def test_connection_statistics_preserve_user_privacy(self):
        """Test connection statistics don't leak user-specific information."""
        # Business value: Privacy-preserving statistics enable monitoring without exposing user data
        
        # Add connections for multiple users
        users = ["private-user-1", "private-user-2", "private-user-3"]
        
        for user_id in users:
            # Simulate adding connections (sync setup for statistics test)
            connection_id = f"conn-{user_id}-{uuid.uuid4().hex[:8]}"
            mock_websocket = Mock()
            mock_websocket.client = Mock()
            mock_websocket.client.host = f"client-{user_id}.private"
            mock_websocket.client.port = 45000 + hash(user_id) % 1000
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=mock_websocket,
                thread_id=f"thread-{user_id}"
            )
            
            self.manager.connections[connection_id] = connection
            if user_id not in self.manager.user_connections:
                self.manager.user_connections[user_id] = []
            self.manager.user_connections[user_id].append(connection)
        
        # Get statistics
        stats = self.manager.get_connection_stats()
        
        # Validate statistics don't expose user-specific information
        assert "user_list" not in stats, "Must not expose user list"
        assert "user_connections" not in stats, "Must not expose user connection mapping"
        assert "connection_details" not in stats, "Must not expose individual connection details"
        
        # Validate statistics provide useful aggregate information
        assert stats["unique_users"] == 3, "Must report aggregate user count"
        assert stats["active_connections"] == 3, "Must report aggregate connection count"
        assert "total_messages_sent" in stats, "Must provide aggregate message statistics"
        assert "timestamp" in stats, "Must include monitoring timestamp"


if __name__ == "__main__":
    # Run tests with proper connection lifecycle and multi-user validation
    pytest.main([__file__, "-v", "--tb=short"])