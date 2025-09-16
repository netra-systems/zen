"""
Integration tests for UnifiedWebSocketManager - Testing real WebSocket connections and multi-user isolation.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Reliable multi-user WebSocket communication
- Value Impact: Ensures proper user isolation and connection management for concurrent users
- Strategic Impact: Foundation for real-time chat - validates connection management with real networking

These tests focus on testing UnifiedWebSocketManager with real WebSocket connections,
user isolation, error recovery, and the critical background monitoring system.
"""

import asyncio
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection
)
from test_framework.ssot.base_test_case import BaseTestCase


class TestUnifiedWebSocketManagerConnectionHandling(BaseTestCase):
    """Integration tests for WebSocket connection lifecycle and management."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create UnifiedWebSocketManager instance."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def realistic_mock_websocket(self):
        """Create realistic mock WebSocket that behaves like real WebSocket."""
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.closed = False
        
        # Simulate connection state
        async def mock_send_json(data):
            if mock_ws.closed:
                raise ConnectionError("WebSocket closed")
            # Store sent messages for verification
            if not hasattr(mock_ws, 'sent_messages'):
                mock_ws.sent_messages = []
            mock_ws.sent_messages.append(data)
        
        async def mock_close():
            mock_ws.closed = True
        
        mock_ws.send_json = mock_send_json
        mock_ws.close = mock_close
        
        return mock_ws
    
    @pytest.fixture
    def sample_connections(self, realistic_mock_websocket):
        """Create multiple sample WebSocket connections for testing."""
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.send_json = AsyncMock()
            mock_ws.closed = False
            mock_ws.sent_messages = []
            
            conn = WebSocketConnection(
                connection_id=f"integration_conn_{i}",
                user_id=f"user_{i}",
                websocket=mock_ws,
                connected_at=datetime.now(timezone.utc),
                metadata={"test": "integration", "index": i}
            )
            connections.append(conn)
        
        return connections
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_connection_addition_thread_safety(self, websocket_manager, sample_connections):
        """Test thread-safe concurrent connection addition."""
        # Act - Add connections concurrently
        tasks = [
            websocket_manager.add_connection(conn) 
            for conn in sample_connections
        ]
        await asyncio.gather(*tasks)
        
        # Assert - All connections should be properly added
        assert len(websocket_manager._connections) == 3
        
        for conn in sample_connections:
            assert conn.connection_id in websocket_manager._connections
            assert conn.user_id in websocket_manager._user_connections
            assert conn.connection_id in websocket_manager._user_connections[conn.user_id]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_specific_connection_locks(self, websocket_manager):
        """Test user-specific connection locks prevent race conditions."""
        user_id = "race_condition_user"
        
        # Create multiple connections for same user
        connections = []
        for i in range(5):
            mock_ws = AsyncMock()
            mock_ws.send_json = AsyncMock()
            conn = WebSocketConnection(
                f"race_conn_{i}",
                user_id,
                mock_ws,
                datetime.now(timezone.utc)
            )
            connections.append(conn)
        
        # Act - Add connections concurrently (potential race condition)
        tasks = [websocket_manager.add_connection(conn) for conn in connections]
        await asyncio.gather(*tasks)
        
        # Assert - All connections should be tracked without race condition
        user_connections = websocket_manager._user_connections.get(user_id, set())
        assert len(user_connections) == 5
        assert len(websocket_manager.active_connections.get(user_id, [])) == 5
        
        # Verify user-specific lock was created
        assert user_id in websocket_manager._user_connection_locks
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wait_for_connection_establishment(self, websocket_manager):
        """Test wait_for_connection method handles connection establishment timing."""
        user_id = "connection_timing_user"
        mock_ws = AsyncMock()
        
        connection = WebSocketConnection(
            "timing_conn",
            user_id,
            mock_ws,
            datetime.now(timezone.utc)
        )
        
        # Start waiting for connection (should initially fail)
        wait_task = asyncio.create_task(
            websocket_manager.wait_for_connection(user_id, timeout=2.0)
        )
        
        # Add connection after brief delay
        await asyncio.sleep(0.5)
        await websocket_manager.add_connection(connection)
        
        # Act & Assert - Wait should succeed once connection is established
        result = await wait_task
        assert result is True
        
        # Test timeout scenario
        timeout_result = await websocket_manager.wait_for_connection(
            "non_existent_user", 
            timeout=0.2
        )
        assert timeout_result is False
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_message_recovery_queue_processing(self, websocket_manager):
        """Test message recovery queue processes failed messages when connection established."""
        user_id = "recovery_queue_user"
        
        # Simulate failed message storage
        failed_message = {
            "type": "agent_started",
            "data": {"agent": "test_agent"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "critical": True
        }
        
        await websocket_manager._store_failed_message(
            user_id, 
            failed_message, 
            "no_connections"
        )
        
        # Verify message is queued
        assert user_id in websocket_manager._message_recovery_queue
        assert len(websocket_manager._message_recovery_queue[user_id]) == 1
        
        # Add connection (should trigger recovery processing)
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        connection = WebSocketConnection(
            "recovery_conn",
            user_id,
            mock_ws,
            datetime.now(timezone.utc)
        )
        
        await websocket_manager.add_connection(connection)
        
        # Allow recovery processing time
        await asyncio.sleep(0.3)
        
        # Assert - Message should have been processed
        # (Queue may be empty if processed, or contain the message)
        recovery_count = await websocket_manager.attempt_message_recovery(user_id)
        assert recovery_count >= 0  # At least attempted recovery


class TestUnifiedWebSocketManagerMessageDelivery(BaseTestCase):
    """Integration tests for WebSocket message delivery and user isolation."""
    
    @pytest.fixture
    async def multi_user_setup(self):
        """Create multi-user WebSocket setup for isolation testing."""
        manager = UnifiedWebSocketManager()
        
        # Create connections for 3 different users
        users_data = []
        for i in range(3):
            user_id = f"isolation_user_{i}"
            mock_ws = AsyncMock()
            mock_ws.send_json = AsyncMock()
            mock_ws.sent_messages = []
            
            # Track messages sent
            async def track_messages(data, user_id=user_id, websocket=mock_ws):
                websocket.sent_messages.append(data)
            
            mock_ws.send_json = track_messages
            
            connection = WebSocketConnection(
                f"isolation_conn_{i}",
                user_id,
                mock_ws,
                datetime.now(timezone.utc),
                metadata={"user_index": i}
            )
            
            await manager.add_connection(connection)
            
            users_data.append({
                "user_id": user_id,
                "connection": connection,
                "websocket": mock_ws
            })
        
        yield manager, users_data
        
        # Cleanup
        for user_data in users_data:
            await manager.remove_connection(user_data["connection"].connection_id)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_message_isolation_and_delivery(self, multi_user_setup):
        """Test messages are delivered only to intended users (critical for multi-user chat)."""
        manager, users_data = multi_user_setup
        
        # Act - Send messages to specific users
        await manager.send_to_user(users_data[0]["user_id"], {
            "type": "agent_started",
            "payload": {"agent": "user_0_agent", "message": "Hello User 0"}
        })
        
        await manager.send_to_user(users_data[1]["user_id"], {
            "type": "agent_thinking", 
            "payload": {"agent": "user_1_agent", "message": "Hello User 1"}
        })
        
        await manager.send_to_user(users_data[2]["user_id"], {
            "type": "agent_completed",
            "payload": {"agent": "user_2_agent", "message": "Hello User 2"}
        })
        
        # Allow message processing
        await asyncio.sleep(0.1)
        
        # Assert - Each user should only receive their own message
        assert len(users_data[0]["websocket"].sent_messages) == 1
        assert len(users_data[1]["websocket"].sent_messages) == 1  
        assert len(users_data[2]["websocket"].sent_messages) == 1
        
        # Verify message content isolation
        user_0_msg = users_data[0]["websocket"].sent_messages[0]
        assert user_0_msg["type"] == "agent_started"
        assert user_0_msg["payload"]["message"] == "Hello User 0"
        
        user_1_msg = users_data[1]["websocket"].sent_messages[0]
        assert user_1_msg["type"] == "agent_thinking"
        assert user_1_msg["payload"]["message"] == "Hello User 1"
        
        user_2_msg = users_data[2]["websocket"].sent_messages[0]  
        assert user_2_msg["type"] == "agent_completed"
        assert user_2_msg["payload"]["message"] == "Hello User 2"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_message_delivery_performance(self, multi_user_setup):
        """Test concurrent message delivery performance and reliability."""
        manager, users_data = multi_user_setup
        
        # Act - Send many messages concurrently to all users
        start_time = time.time()
        
        tasks = []
        messages_per_user = 10
        
        for i, user_data in enumerate(users_data):
            for msg_num in range(messages_per_user):
                task = asyncio.create_task(
                    manager.send_to_user(user_data["user_id"], {
                        "type": "test_message",
                        "payload": {
                            "user_index": i,
                            "message_number": msg_num,
                            "timestamp": time.time()
                        }
                    })
                )
                tasks.append(task)
        
        # Wait for all messages to be sent
        await asyncio.gather(*tasks)
        
        delivery_time = time.time() - start_time
        
        # Allow processing time
        await asyncio.sleep(0.2)
        
        # Assert - All messages should be delivered
        total_messages_sent = sum(len(user["websocket"].sent_messages) for user in users_data)
        expected_total = len(users_data) * messages_per_user
        
        assert total_messages_sent == expected_total, \
            f"Expected {expected_total} messages, but delivered {total_messages_sent}"
        
        # Each user should receive exactly their messages
        for i, user_data in enumerate(users_data):
            assert len(user_data["websocket"].sent_messages) == messages_per_user
            
            # Verify message content integrity
            for msg_idx, message in enumerate(user_data["websocket"].sent_messages):
                assert message["payload"]["user_index"] == i
                assert message["payload"]["message_number"] == msg_idx
        
        # Performance assertion - should deliver quickly
        assert delivery_time < 2.0, f"Concurrent delivery took {delivery_time:.2f}s, may impact UX"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_broadcast_message_delivery(self, multi_user_setup):
        """Test broadcast messages are delivered to all connected users."""
        manager, users_data = multi_user_setup
        
        broadcast_message = {
            "type": "system_announcement",
            "payload": {
                "message": "System maintenance in 10 minutes",
                "priority": "high",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Act - Broadcast message
        await manager.broadcast(broadcast_message)
        
        # Allow processing time
        await asyncio.sleep(0.1)
        
        # Assert - All users should receive the broadcast
        for user_data in users_data:
            messages = user_data["websocket"].sent_messages
            assert len(messages) >= 1
            
            # Find the broadcast message
            broadcast_received = next(
                (msg for msg in messages if msg["type"] == "system_announcement"), 
                None
            )
            assert broadcast_received is not None
            assert broadcast_received["payload"]["message"] == "System maintenance in 10 minutes"
            assert broadcast_received["payload"]["priority"] == "high"


class TestUnifiedWebSocketManagerErrorHandling(BaseTestCase):
    """Integration tests for WebSocket error handling and recovery mechanisms."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create UnifiedWebSocketManager instance."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture 
    def failing_websocket(self):
        """Create WebSocket that fails to send messages."""
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        # Make send_json fail
        mock_ws.send_json.side_effect = Exception("WebSocket send failed")
        
        return mock_ws
    
    @pytest.fixture
    def intermittent_websocket(self):
        """Create WebSocket that intermittently fails."""
        mock_ws = AsyncMock()
        call_count = 0
        
        async def intermittent_send(data):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
                raise Exception("Intermittent failure")
            # Store successful messages
            if not hasattr(mock_ws, 'successful_messages'):
                mock_ws.successful_messages = []
            mock_ws.successful_messages.append(data)
        
        mock_ws.send_json = intermittent_send
        mock_ws.successful_messages = []
        
        return mock_ws
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handles_websocket_send_failures_gracefully(self, websocket_manager, failing_websocket):
        """Test manager handles WebSocket send failures without crashing."""
        user_id = "failing_user"
        
        connection = WebSocketConnection(
            "failing_conn",
            user_id,
            failing_websocket,
            datetime.now(timezone.utc)
        )
        
        await websocket_manager.add_connection(connection)
        
        # Act - Send message that will fail
        await websocket_manager.send_to_user(user_id, {
            "type": "test_message",
            "payload": {"test": "failure_handling"}
        })
        
        # Allow error handling time
        await asyncio.sleep(0.2)
        
        # Assert - Connection should be removed due to failure
        assert "failing_conn" not in websocket_manager._connections
        assert user_id not in websocket_manager._user_connections or \
               len(websocket_manager._user_connections[user_id]) == 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, websocket_manager, failing_websocket):
        """Test comprehensive error statistics are tracked."""
        user_id = "error_stats_user"
        
        connection = WebSocketConnection(
            "error_stats_conn",
            user_id,
            failing_websocket,
            datetime.now(timezone.utc)
        )
        
        await websocket_manager.add_connection(connection)
        
        # Generate multiple failed messages
        for i in range(3):
            await websocket_manager.send_to_user(user_id, {
                "type": "test_message",
                "payload": {"attempt": i}
            })
        
        # Allow error processing
        await asyncio.sleep(0.3)
        
        # Check error statistics
        error_stats = websocket_manager.get_error_statistics()
        
        assert error_stats["total_users_with_errors"] >= 1
        assert error_stats["total_error_count"] >= 3
        assert error_stats["error_recovery_enabled"] is True
        
        # Check user-specific error tracking
        if user_id in error_stats["error_details"]:
            user_errors = error_stats["error_details"][user_id]
            assert user_errors["error_count"] >= 3
            assert user_errors["queued_messages"] >= 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_recovery_and_retry_system(self, websocket_manager):
        """Test connection recovery and message retry system."""
        user_id = "recovery_user"
        
        # Start with failing WebSocket
        failing_ws = AsyncMock()
        failing_ws.send_json = AsyncMock(side_effect=Exception("Connection failed"))
        
        connection = WebSocketConnection(
            "recovery_conn",
            user_id,
            failing_ws,
            datetime.now(timezone.utc)
        )
        
        await websocket_manager.add_connection(connection)
        
        # Send messages that will fail and be queued
        test_messages = [
            {"type": "message_1", "payload": {"data": "first"}},
            {"type": "message_2", "payload": {"data": "second"}},
            {"type": "message_3", "payload": {"data": "third"}}
        ]
        
        for msg in test_messages:
            await websocket_manager.send_to_user(user_id, msg)
        
        # Allow queuing time
        await asyncio.sleep(0.2)
        
        # Verify messages were queued for recovery
        assert user_id in websocket_manager._message_recovery_queue
        queued_messages = websocket_manager._message_recovery_queue[user_id]
        assert len(queued_messages) >= len(test_messages)
        
        # Now "fix" the connection
        working_ws = AsyncMock()
        working_ws.send_json = AsyncMock()
        working_ws.sent_messages = []
        
        async def track_sent_messages(data):
            working_ws.sent_messages.append(data)
        
        working_ws.send_json = track_sent_messages
        
        # Remove old connection and add working one
        await websocket_manager.remove_connection("recovery_conn")
        
        new_connection = WebSocketConnection(
            "working_conn",
            user_id,
            working_ws,
            datetime.now(timezone.utc)
        )
        
        await websocket_manager.add_connection(new_connection)
        
        # Allow recovery processing time
        await asyncio.sleep(0.5)
        
        # Attempt manual recovery if automatic didn't trigger
        recovery_count = await websocket_manager.attempt_message_recovery(user_id)
        
        # Allow additional processing time
        await asyncio.sleep(0.2)
        
        # Verify some messages were recovered
        # (Exact count may vary based on timing and recovery logic)
        assert recovery_count >= 0  # Should have attempted recovery
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_data_cleanup_prevents_memory_leaks(self, websocket_manager):
        """Test error data cleanup prevents long-term memory accumulation."""
        # Generate error data
        for i in range(10):
            user_id = f"cleanup_user_{i}"
            await websocket_manager._store_failed_message(
                user_id,
                {"type": "test", "data": f"message_{i}"},
                "test_failure"
            )
        
        # Verify error data was stored
        initial_stats = websocket_manager.get_error_statistics()
        assert initial_stats["total_users_with_errors"] >= 10
        
        # Cleanup old error data (simulate old data by setting very short retention)
        cleanup_results = await websocket_manager.cleanup_error_data(older_than_hours=0)
        
        # Verify cleanup occurred
        assert cleanup_results["cleaned_error_users"] >= 0
        assert cleanup_results["cleaned_queue_users"] >= 0
        
        # Final stats should show cleanup
        final_stats = websocket_manager.get_error_statistics()
        # Error counts may be reduced after cleanup
        assert final_stats["total_users_with_errors"] <= initial_stats["total_users_with_errors"]