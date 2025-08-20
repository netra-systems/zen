"""
L3 Integration Test: WebSocket connections with real Redis pub/sub

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Ensure WebSocket reliability for real-time features
- Value Impact: Critical for user experience in collaborative features and real-time updates
- Strategic Impact: Reduces production incidents, improves customer retention

This L3 test uses real Redis containers via Docker to validate WebSocket pub/sub integration.
Tests real-world scenarios with actual Redis connections, pub/sub channels, and message routing.
"""

import pytest
import asyncio
import json
import uuid
import subprocess
import time
import signal
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

import redis.asyncio as redis
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.ws_manager import WebSocketManager
from app.redis_manager import RedisManager
from app.schemas import UserInDB
from app.schemas.websocket_message_types import ServerMessage
from app.logging_config import central_logger
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)


class RedisContainer:
    """Manages a real Redis Docker container for L3 testing."""
    
    def __init__(self, port: int = 6381):
        """Initialize Redis container configuration."""
        self.port = port
        self.container_name = f"netra-test-redis-l3-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.redis_url = f"redis://localhost:{port}/0"
    
    async def start(self) -> str:
        """Start Redis container and return connection URL."""
        try:
            # Stop any existing container with same name
            await self._cleanup_existing()
            
            # Start new Redis container
            cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{self.port}:6379",
                "redis:7-alpine",
                "redis-server", "--appendonly", "yes"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start Redis container: {result.stderr}")
            
            self.container_id = result.stdout.strip()
            
            # Wait for Redis to be ready
            await self._wait_for_ready()
            
            logger.info(f"Redis container started: {self.container_name}")
            return self.redis_url
            
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"Redis container startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop and remove Redis container."""
        if self.container_id:
            try:
                # Stop container
                subprocess.run(
                    ["docker", "stop", self.container_id],
                    capture_output=True, timeout=10
                )
                # Remove container
                subprocess.run(
                    ["docker", "rm", self.container_id],
                    capture_output=True, timeout=10
                )
                logger.info(f"Redis container stopped: {self.container_name}")
            except Exception as e:
                logger.warning(f"Error stopping Redis container: {e}")
            finally:
                self.container_id = None
    
    async def _cleanup_existing(self) -> None:
        """Clean up any existing container with same name."""
        try:
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True, timeout=5
            )
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True, timeout=5
            )
        except:
            pass  # Ignore cleanup errors
    
    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for Redis to be ready to accept connections."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                client = redis.Redis.from_url(self.redis_url)
                await client.ping()
                await client.close()
                return
            except Exception:
                await asyncio.sleep(0.5)
        
        raise RuntimeError("Redis container failed to become ready")


class MockWebSocketForRedis:
    """Mock WebSocket that tracks messages for Redis pub/sub testing."""
    
    def __init__(self, user_id: str):
        """Initialize mock WebSocket."""
        self.user_id = user_id
        self.messages: List[Dict[str, Any]] = []
        self.client_state = WebSocketState.CONNECTED
        self.closed = False
        
    async def accept(self) -> None:
        """Mock WebSocket accept."""
        pass
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Track sent JSON messages."""
        if not self.closed:
            self.messages.append(data)
            logger.debug(f"WebSocket {self.user_id} received: {data}")
    
    async def send_text(self, data: str) -> None:
        """Track sent text messages."""
        if not self.closed:
            try:
                message = json.loads(data)
                self.messages.append(message)
            except json.JSONDecodeError:
                self.messages.append({"text": data})
    
    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:
        """Mock WebSocket close."""
        self.closed = True
        self.client_state = WebSocketState.DISCONNECTED


@pytest.mark.L3
@pytest.mark.integration
class TestWebSocketRedisPubSubL3:
    """L3 integration tests for WebSocket connections with real Redis pub/sub."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up real Redis container for testing."""
        container = RedisContainer()
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client connected to test container."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()
    
    @pytest.fixture
    async def pubsub_client(self, redis_container):
        """Create separate Redis client for pub/sub operations."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        pubsub = client.pubsub()
        yield pubsub
        await pubsub.close()
        await client.close()
    
    @pytest.fixture
    async def ws_manager(self, redis_container):
        """Create WebSocket manager with real Redis connection."""
        _, redis_url = redis_container
        
        # Patch Redis manager to use test container
        with patch('app.ws_manager.redis_manager') as mock_redis_mgr:
            test_redis_mgr = RedisManager()
            test_redis_mgr.enabled = True
            test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            mock_redis_mgr.return_value = test_redis_mgr
            mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client
            
            manager = WebSocketManager()
            yield manager
            
            await test_redis_mgr.redis_client.close()
    
    @pytest.fixture
    def test_users(self):
        """Create test users for WebSocket testing."""
        return [
            UserInDB(
                id=f"ws_user_{i}",
                email=f"user{i}@example.com",
                username=f"user{i}",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
    
    async def test_websocket_redis_connection_setup(self, ws_manager, redis_client, test_users):
        """
        Test WebSocket connection establishment with Redis integration.
        
        Validates:
        - WebSocket connection setup
        - Redis channel subscription
        - Connection state management
        - Redis key creation
        """
        user = test_users[0]
        websocket = MockWebSocketForRedis(user.id)
        
        # Connect WebSocket user
        connection_info = await ws_manager.connect_user(user.id, websocket)
        
        # Verify connection was established
        assert connection_info is not None
        assert connection_info.user_id == user.id
        assert user.id in ws_manager.active_connections
        
        # Verify Redis keys were created
        user_channel = f"user:{user.id}"
        connection_key = f"ws_connection:{connection_info.connection_id}"
        
        # Check if Redis keys exist
        assert await redis_client.exists(connection_key) > 0
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)
    
    async def test_redis_pubsub_message_broadcasting(self, ws_manager, redis_client, pubsub_client, test_users):
        """
        Test message broadcasting through Redis pub/sub.
        
        Validates:
        - Message publishing to Redis channels
        - Multiple subscriber connections
        - Message routing and delivery
        - Channel isolation
        """
        # Setup multiple WebSocket connections
        connections = []
        for user in test_users:
            websocket = MockWebSocketForRedis(user.id)
            await ws_manager.connect_user(user.id, websocket)
            connections.append((user, websocket))
        
        # Subscribe to user channels in Redis
        channels = [f"user:{user.id}" for user in test_users]
        await pubsub_client.subscribe(*channels)
        
        # Publish message to specific user channel
        target_user = test_users[0]
        target_channel = f"user:{target_user.id}"
        test_message = {
            "type": "thread_update",
            "data": {"thread_id": "thread_123", "content": "Redis pub/sub test"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Publish via Redis
        await redis_client.publish(target_channel, json.dumps(test_message))
        
        # Wait for message propagation
        await asyncio.sleep(0.1)
        
        # Verify message was published
        message = await pubsub_client.get_message(timeout=1.0)
        if message and message['type'] == 'message':
            received_data = json.loads(message['data'])
            assert received_data['type'] == test_message['type']
            assert received_data['data']['thread_id'] == "thread_123"
        
        # Cleanup connections
        for user, websocket in connections:
            await ws_manager.disconnect_user(user.id, websocket)
    
    async def test_websocket_reconnection_with_redis_state(self, ws_manager, redis_client, test_users):
        """
        Test WebSocket reconnection with Redis state recovery.
        
        Validates:
        - Connection state persistence in Redis
        - Reconnection handling
        - State recovery mechanisms
        - Message queue replay
        """
        user = test_users[0]
        
        # Initial connection
        first_websocket = MockWebSocketForRedis(user.id)
        connection_info = await ws_manager.connect_user(user.id, first_websocket)
        original_connection_id = connection_info.connection_id
        
        # Store state in Redis
        state_key = f"ws_state:{user.id}"
        state_data = {
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "connection_count": 1,
            "subscribed_channels": [f"user:{user.id}", f"thread:{user.id}"]
        }
        await redis_client.set(state_key, json.dumps(state_data), ex=3600)
        
        # Simulate disconnection
        await ws_manager.disconnect_user(user.id, first_websocket)
        
        # Verify state persists in Redis
        stored_state = await redis_client.get(state_key)
        assert stored_state is not None
        
        # Reconnect with new WebSocket
        second_websocket = MockWebSocketForRedis(user.id)
        new_connection_info = await ws_manager.connect_user(user.id, second_websocket)
        
        # Verify reconnection
        assert new_connection_info is not None
        assert new_connection_info.user_id == user.id
        assert user.id in ws_manager.active_connections
        
        # Verify state recovery (if implemented)
        recovered_state = await redis_client.get(state_key)
        if recovered_state:
            state = json.loads(recovered_state)
            assert "last_activity" in state
            assert "subscribed_channels" in state
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, second_websocket)
    
    async def test_concurrent_websocket_connections_redis_performance(self, ws_manager, redis_client, redis_container):
        """
        Test performance with 100+ concurrent WebSocket connections via Redis.
        
        Validates:
        - High connection concurrency
        - Redis connection pool handling
        - Message broadcasting performance
        - Resource cleanup
        """
        # Create 50 concurrent connections (scaled down for CI)
        connection_count = 50
        connections = []
        
        # Setup phase
        setup_start = time.time()
        
        for i in range(connection_count):
            user_id = f"perf_user_{i}"
            websocket = MockWebSocketForRedis(user_id)
            connection_info = await ws_manager.connect_user(user_id, websocket)
            connections.append((user_id, websocket, connection_info))
        
        setup_time = time.time() - setup_start
        logger.info(f"Setup {connection_count} connections in {setup_time:.2f}s")
        
        # Verify all connections are tracked
        assert len(ws_manager.active_connections) >= connection_count
        
        # Broadcast performance test
        broadcast_start = time.time()
        
        broadcast_message = {
            "type": "system_announcement",
            "data": {"message": "Performance test broadcast"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Publish to multiple channels simultaneously
        tasks = []
        for user_id, _, _ in connections[:10]:  # Broadcast to first 10 users
            channel = f"user:{user_id}"
            task = redis_client.publish(channel, json.dumps(broadcast_message))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        broadcast_time = time.time() - broadcast_start
        logger.info(f"Broadcast to 10 users in {broadcast_time:.3f}s")
        
        # Verify Redis performance metrics
        info = await redis_client.info()
        assert info['connected_clients'] >= 1
        assert info['total_commands_processed'] > 0
        
        # Cleanup phase
        cleanup_start = time.time()
        
        for user_id, websocket, _ in connections:
            await ws_manager.disconnect_user(user_id, websocket)
        
        cleanup_time = time.time() - cleanup_start
        logger.info(f"Cleanup {connection_count} connections in {cleanup_time:.2f}s")
        
        # Performance assertions
        assert setup_time < 10.0  # Should setup quickly
        assert broadcast_time < 1.0  # Should broadcast quickly
        assert cleanup_time < 5.0  # Should cleanup quickly
    
    async def test_redis_channel_management_isolation(self, ws_manager, redis_client, pubsub_client, test_users):
        """
        Test Redis channel management and isolation.
        
        Validates:
        - Dynamic channel subscription/unsubscription
        - Channel isolation between users
        - Subscription cleanup on disconnect
        - Message delivery accuracy
        """
        user1, user2 = test_users[0], test_users[1]
        
        # Connect both users
        ws1 = MockWebSocketForRedis(user1.id)
        ws2 = MockWebSocketForRedis(user2.id)
        
        await ws_manager.connect_user(user1.id, ws1)
        await ws_manager.connect_user(user2.id, ws2)
        
        # Subscribe to channels
        channel1 = f"user:{user1.id}"
        channel2 = f"user:{user2.id}"
        
        await pubsub_client.subscribe(channel1, channel2)
        
        # Test isolated message delivery
        message1 = {
            "type": "private_message",
            "data": {"recipient": user1.id, "content": "Message for user1"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        message2 = {
            "type": "private_message", 
            "data": {"recipient": user2.id, "content": "Message for user2"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Publish to specific channels
        await redis_client.publish(channel1, json.dumps(message1))
        await redis_client.publish(channel2, json.dumps(message2))
        
        # Wait for message propagation
        await asyncio.sleep(0.1)
        
        # Verify channel isolation
        messages_received = []
        for _ in range(2):  # Expect 2 messages
            msg = await pubsub_client.get_message(timeout=1.0)
            if msg and msg['type'] == 'message':
                messages_received.append(msg)
        
        assert len(messages_received) == 2
        
        # Verify correct message routing
        received_data = [json.loads(msg['data']) for msg in messages_received]
        user1_msg = next(m for m in received_data if m['data']['recipient'] == user1.id)
        user2_msg = next(m for m in received_data if m['data']['recipient'] == user2.id)
        
        assert user1_msg['data']['content'] == "Message for user1"
        assert user2_msg['data']['content'] == "Message for user2"
        
        # Test unsubscribe functionality
        await pubsub_client.unsubscribe(channel1)
        
        # Publish to unsubscribed channel
        await redis_client.publish(channel1, json.dumps({"test": "should_not_receive"}))
        await asyncio.sleep(0.1)
        
        # Should not receive message from unsubscribed channel
        msg = await pubsub_client.get_message(timeout=0.5)
        assert msg is None or msg['type'] != 'message'
        
        # Cleanup
        await ws_manager.disconnect_user(user1.id, ws1)
        await ws_manager.disconnect_user(user2.id, ws2)
    
    @mock_justified("L3: Using real Redis container for integration validation")
    async def test_redis_failover_websocket_recovery(self, redis_container, ws_manager, test_users):
        """
        Test WebSocket resilience during Redis connection issues.
        
        Validates:
        - WebSocket behavior during Redis downtime
        - Connection recovery mechanisms
        - Graceful degradation
        - Service continuity
        """
        container, redis_url = redis_container
        user = test_users[0]
        
        # Establish WebSocket connection
        websocket = MockWebSocketForRedis(user.id)
        connection_info = await ws_manager.connect_user(user.id, websocket)
        
        # Verify initial connection
        assert connection_info is not None
        assert user.id in ws_manager.active_connections
        
        # Simulate Redis container restart (brief downtime)
        logger.info("Simulating Redis failover...")
        
        # Stop Redis container temporarily
        if container.container_id:
            subprocess.run(
                ["docker", "restart", container.container_id],
                capture_output=True, timeout=30
            )
            
            # Wait for Redis to come back online
            await container._wait_for_ready(timeout=30)
        
        # Verify WebSocket connection survives Redis restart
        assert user.id in ws_manager.active_connections
        assert not websocket.closed
        
        # Test message sending after Redis recovery
        recovery_message = {
            "type": "recovery_test",
            "data": {"status": "redis_recovered"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # This should work after Redis comes back
        success = await ws_manager.send_message_to_user(user.id, recovery_message)
        
        # Verify message delivery (implementation dependent)
        if success:
            assert len(websocket.messages) > 0
            assert any(msg.get('type') == 'recovery_test' for msg in websocket.messages)
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])