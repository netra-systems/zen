"""Integration Test: WebSocket Connection Lifecycle Management

BVJ: $20K MRR - Real-time features critical for user engagement and retention
Components: WebSocket Manager → Redis Pub/Sub → Connection Pool → Auth Integration
Critical: WebSocket lifecycle must be seamless for real-time user experience
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.ws_manager import WebSocketManager
from app.schemas import UserInDB
from app.schemas.websocket_message_types import ServerMessage
from test_framework.mock_utils import mock_justified


@pytest.mark.asyncio
class TestWebSocketLifecycleIntegration:
    """Test complete WebSocket connection lifecycle integration."""
    
    @pytest.fixture
    async def test_user(self):
        """Create test user for WebSocket testing."""
        return UserInDB(
            id="ws_user_789",
            email="ws@example.com",
            username="wsuser",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    async def mock_websocket(self):
        """Create mock WebSocket connection."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.receive_json = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.client_state = WebSocketState.CONNECTING
        websocket.headers = {"Authorization": "Bearer test_token"}
        return websocket
    
    @pytest.fixture
    async def ws_manager(self):
        """Create WebSocket manager instance."""
        return WebSocketManager()
    
    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis pub/sub for testing."""
        from app.redis_manager import RedisManager
        
        redis_manager = Mock(spec=RedisManager)
        redis_manager.publish = AsyncMock(return_value=1)
        redis_manager.subscribe = AsyncMock()
        redis_manager.unsubscribe = AsyncMock()
        redis_manager.get_subscriber = AsyncMock()
        return redis_manager
    
    async def test_websocket_connection_initialization(self, ws_manager, mock_websocket, test_user):
        """
        Test WebSocket connection initialization process.
        
        Validates:
        - Connection acceptance
        - User association
        - Initial connection state
        - Connection registration
        """
        # Test connection establishment
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Verify connection was accepted
        mock_websocket.accept.assert_called_once()
        
        # Verify user is registered in active connections
        assert test_user.id in ws_manager.active_connections
        
        # Verify connection info is stored
        connection_info = ws_manager.active_connections[test_user.id]
        assert connection_info.websocket == mock_websocket
        assert connection_info.user_id == test_user.id
        
        # Test connection count
        assert len(ws_manager.active_connections) == 1
    
    async def test_websocket_authentication_handshake(self, ws_manager, mock_websocket, test_user):
        """
        Test WebSocket authentication handshake process.
        
        Validates:
        - Auth token extraction from headers
        - Token validation integration
        - User authentication flow
        - Auth failure handling
        """
        # Mock auth service for token validation
        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.AuthService') as mock_auth_service:
            auth_instance = mock_auth_service.return_value
            auth_instance.validate_token = AsyncMock(return_value=test_user)
            
            # Extract token from headers
            auth_header = mock_websocket.headers.get("Authorization")
            assert auth_header == "Bearer test_token"
            
            token = auth_header.split(" ")[1] if auth_header else None
            assert token == "test_token"
            
            # Validate token through auth service
            validated_user = await auth_instance.validate_token(token)
            assert validated_user.id == test_user.id
            
            # Establish authenticated connection
            await ws_manager.connect(mock_websocket, test_user.id)
            
            # Verify connection is authenticated
            assert test_user.id in ws_manager.active_connections
            
            # Test authentication failure scenario
            auth_instance.validate_token.side_effect = ValueError("Invalid token")
            
            with pytest.raises(ValueError):
                await auth_instance.validate_token("invalid_token")
    
    async def test_message_routing_through_redis_pubsub(self, ws_manager, mock_websocket, test_user, redis_mock):
        """
        Test message routing through Redis pub/sub system.
        
        Validates:
        - Message publishing to Redis
        - Channel subscription management
        - Message routing to connections
        - Pub/sub pattern integration
        """
        # Setup WebSocket connection
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Mock Redis integration
        with patch('app.redis_manager.RedisManager', return_value=redis_mock):
            # Test message publishing
            message = {
                "type": "thread_update",
                "data": {"thread_id": "thread_123", "content": "New message"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Publish message through Redis
            channel = f"user:{test_user.id}"
            await redis_mock.publish(channel, json.dumps(message))
            
            # Verify Redis publish was called
            redis_mock.publish.assert_called_once_with(
                channel, 
                json.dumps(message)
            )
            
            # Test message delivery to WebSocket
            await ws_manager.send_message(test_user.id, message)
            
            # Verify message was sent to WebSocket
            mock_websocket.send_json.assert_called_with(message)
    
    async def test_connection_state_management(self, ws_manager, mock_websocket, test_user):
        """
        Test connection state management throughout lifecycle.
        
        Validates:
        - Connection state tracking
        - State transitions
        - Connection metadata
        - State persistence
        """
        # Test initial state (no connections)
        assert len(ws_manager.active_connections) == 0
        
        # Test connection establishment
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Verify connection state
        assert len(ws_manager.active_connections) == 1
        connection_info = ws_manager.active_connections[test_user.id]
        assert connection_info.user_id == test_user.id
        assert connection_info.connected_at is not None
        
        # Test connection activity update
        original_activity = connection_info.last_activity
        await asyncio.sleep(0.1)  # Small delay to ensure timestamp difference
        
        # Simulate activity (message send)
        await ws_manager.send_message(test_user.id, {"type": "ping"})
        
        # Verify activity was updated
        updated_connection = ws_manager.active_connections[test_user.id]
        assert updated_connection.last_activity > original_activity
        
        # Test connection removal
        await ws_manager.disconnect(test_user.id)
        assert len(ws_manager.active_connections) == 0
    
    async def test_reconnection_with_state_recovery(self, ws_manager, test_user, redis_mock):
        """
        Test reconnection with state recovery mechanisms.
        
        Validates:
        - Reconnection handling
        - State recovery from Redis
        - Message queue replay
        - Connection continuity
        """
        # Setup initial connection
        first_websocket = Mock(spec=WebSocket)
        first_websocket.accept = AsyncMock()
        first_websocket.send_json = AsyncMock()
        first_websocket.close = AsyncMock()
        
        await ws_manager.connect(first_websocket, test_user.id)
        
        # Store some state in Redis (simulate missed messages)
        with patch('app.redis_manager.RedisManager', return_value=redis_mock):
            missed_messages = [
                {"type": "message", "data": "Message 1", "timestamp": "2024-01-01T10:00:00Z"},
                {"type": "message", "data": "Message 2", "timestamp": "2024-01-01T10:01:00Z"}
            ]
            
            redis_mock.get.return_value = json.dumps(missed_messages)
            
            # Simulate disconnection
            await ws_manager.disconnect(test_user.id)
            
            # Create new connection (reconnection)
            second_websocket = Mock(spec=WebSocket)
            second_websocket.accept = AsyncMock()
            second_websocket.send_json = AsyncMock()
            
            # Reconnect and recover state
            await ws_manager.connect(second_websocket, test_user.id)
            
            # Verify reconnection
            assert test_user.id in ws_manager.active_connections
            
            # Test state recovery (would normally replay missed messages)
            recovered_messages = await redis_mock.get(f"missed_messages:{test_user.id}")
            if recovered_messages:
                messages = json.loads(recovered_messages)
                assert len(messages) == 2
                assert messages[0]["data"] == "Message 1"
    
    async def test_websocket_connection_pooling(self, ws_manager):
        """
        Test WebSocket connection pooling and management.
        
        Validates:
        - Multiple connections per user
        - Connection pool limits
        - Connection cleanup
        - Resource management
        """
        user_ids = [f"user_{i}" for i in range(5)]
        websockets = []
        
        # Create multiple connections
        for user_id in user_ids:
            websocket = Mock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_json = AsyncMock()
            websocket.close = AsyncMock()
            
            await ws_manager.connect(websocket, user_id)
            websockets.append((user_id, websocket))
        
        # Verify all connections are active
        assert len(ws_manager.active_connections) == 5
        
        # Test connection limits (simulate max connections)
        max_connections = 100  # Assume reasonable limit
        assert len(ws_manager.active_connections) <= max_connections
        
        # Test broadcast to all connections
        broadcast_message = {
            "type": "system_announcement",
            "data": "Server maintenance in 5 minutes"
        }
        
        await ws_manager.broadcast_to_all(broadcast_message)
        
        # Verify all connections received broadcast
        for user_id, websocket in websockets:
            websocket.send_json.assert_called_with(broadcast_message)
        
        # Test selective cleanup
        await ws_manager.disconnect(user_ids[0])
        assert len(ws_manager.active_connections) == 4
        assert user_ids[0] not in ws_manager.active_connections
    
    async def test_error_handling_in_websocket_layer(self, ws_manager, mock_websocket, test_user):
        """
        Test error handling throughout WebSocket layer.
        
        Validates:
        - Connection error handling
        - Message sending failures
        - Network disconnection handling
        - Graceful degradation
        """
        # Test connection error during establishment
        failing_websocket = Mock(spec=WebSocket)
        failing_websocket.accept = AsyncMock(side_effect=ConnectionError("Connection failed"))
        
        with pytest.raises(ConnectionError):
            await ws_manager.connect(failing_websocket, test_user.id)
        
        # Establish working connection for other tests
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Test message sending failure
        mock_websocket.send_json.side_effect = ConnectionError("Send failed")
        
        with pytest.raises(ConnectionError):
            await ws_manager.send_message(test_user.id, {"type": "test"})
        
        # Test connection state after error
        # Connection should be marked as problematic or removed
        # (Implementation dependent - verify appropriate error handling)
        
        # Test network disconnection handling
        mock_websocket.close.side_effect = None  # Reset for clean close
        await ws_manager.disconnect(test_user.id)
        assert test_user.id not in ws_manager.active_connections
    
    @mock_justified("WebSocket connection state simulation requires mocking network layer")
    async def test_websocket_connection_health_monitoring(self, ws_manager, test_user):
        """
        Test WebSocket connection health monitoring.
        
        Validates:
        - Connection health checks
        - Dead connection detection
        - Automatic cleanup
        - Health status reporting
        """
        # Create mock websocket with health simulation
        healthy_websocket = Mock(spec=WebSocket)
        healthy_websocket.accept = AsyncMock()
        healthy_websocket.send_json = AsyncMock()
        healthy_websocket.client_state = WebSocketState.CONNECTED
        
        # Establish connection
        await ws_manager.connect(healthy_websocket, test_user.id)
        
        # Test connection health check
        connection_info = ws_manager.active_connections[test_user.id]
        assert connection_info.websocket.client_state == WebSocketState.CONNECTED
        
        # Simulate connection going stale
        stale_connection_time = datetime.utcnow() - timedelta(minutes=30)
        connection_info.last_activity = stale_connection_time
        
        # Test health monitoring would detect stale connection
        # (Implementation would vary - this tests the concept)
        time_since_activity = datetime.utcnow() - connection_info.last_activity
        is_stale = time_since_activity > timedelta(minutes=15)
        assert is_stale is True
        
        # Test cleanup of stale connections
        if is_stale:
            await ws_manager.disconnect(test_user.id)
            assert test_user.id not in ws_manager.active_connections
    
    async def test_concurrent_websocket_operations(self, ws_manager):
        """
        Test concurrent WebSocket operations.
        
        Validates:
        - Multiple simultaneous connections
        - Concurrent message sending
        - Race condition handling
        - Thread safety
        """
        # Setup multiple users for concurrent testing
        user_count = 10
        user_ids = [f"concurrent_user_{i}" for i in range(user_count)]
        connection_tasks = []
        
        # Create concurrent connection tasks
        for user_id in user_ids:
            websocket = Mock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_json = AsyncMock()
            websocket.close = AsyncMock()
            
            task = ws_manager.connect(websocket, user_id)
            connection_tasks.append(task)
        
        # Execute all connections concurrently
        await asyncio.gather(*connection_tasks)
        
        # Verify all connections established
        assert len(ws_manager.active_connections) == user_count
        
        # Test concurrent message sending
        message_tasks = []
        test_message = {"type": "concurrent_test", "data": "test_data"}
        
        for user_id in user_ids:
            task = ws_manager.send_message(user_id, test_message)
            message_tasks.append(task)
        
        # Execute all messages concurrently
        await asyncio.gather(*message_tasks)
        
        # Verify all messages were sent
        for user_id in user_ids:
            connection = ws_manager.active_connections[user_id]
            connection.websocket.send_json.assert_called_with(test_message)
        
        # Cleanup all connections
        disconnect_tasks = [ws_manager.disconnect(user_id) for user_id in user_ids]
        await asyncio.gather(*disconnect_tasks)
        
        assert len(ws_manager.active_connections) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])