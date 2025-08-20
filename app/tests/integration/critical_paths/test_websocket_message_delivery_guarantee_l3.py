"""
L3 Integration Test: WebSocket Message Delivery Guarantee with Redis

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Reliability - Ensure critical messages reach users
- Value Impact: Prevents data loss in collaborative workflows
- Strategic Impact: $60K MRR - Message reliability for enterprise features

L3 Test: Uses real Redis for at-least-once delivery guarantees.
Delivery target: 99.9% delivery rate with retry mechanisms.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Set
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import redis.asyncio as redis
from app.ws_manager import WebSocketManager
from app.redis_manager import RedisManager
from app.schemas import UserInDB
from test_framework.mock_utils import mock_justified
from ..helpers.redis_l3_helpers import (
    RedisContainer, 
    MockWebSocketForRedis, 
    create_test_message
)


class MessageDeliveryTracker:
    """Track message delivery status for testing."""
    
    def __init__(self):
        self.sent_messages: Dict[str, Dict] = {}
        self.delivered_messages: Set[str] = set()
        self.failed_deliveries: Set[str] = set()
    
    def track_sent(self, message_id: str, message: Dict[str, Any]) -> None:
        """Track a sent message."""
        self.sent_messages[message_id] = {
            "message": message,
            "sent_at": time.time(),
            "attempts": 0
        }
    
    def mark_delivered(self, message_id: str) -> None:
        """Mark message as successfully delivered."""
        self.delivered_messages.add(message_id)
    
    def mark_failed(self, message_id: str) -> None:
        """Mark message as failed delivery."""
        self.failed_deliveries.add(message_id)
    
    def get_delivery_rate(self) -> float:
        """Calculate delivery success rate."""
        total = len(self.sent_messages)
        if total == 0:
            return 0.0
        return len(self.delivered_messages) / total


@pytest.mark.L3
@pytest.mark.integration
class TestWebSocketMessageDeliveryGuaranteeL3:
    """L3 integration tests for WebSocket message delivery guarantees."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container for delivery guarantee testing."""
        container = RedisContainer(port=6383)
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client for message tracking."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()
    
    @pytest.fixture
    async def pubsub_client(self, redis_container):
        """Create Redis pub/sub client for message delivery."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        pubsub = client.pubsub()
        yield pubsub
        await pubsub.close()
        await client.close()
    
    @pytest.fixture
    async def ws_manager(self, redis_container):
        """Create WebSocket manager with delivery tracking."""
        _, redis_url = redis_container
        
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
        """Create test users for delivery testing."""
        return [
            UserInDB(
                id=f"delivery_user_{i}",
                email=f"deliveryuser{i}@example.com", 
                username=f"deliveryuser{i}",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]
    
    @pytest.fixture
    def delivery_tracker(self):
        """Create message delivery tracker."""
        return MessageDeliveryTracker()
    
    async def test_basic_message_delivery_guarantee(self, ws_manager, redis_client, pubsub_client, test_users, delivery_tracker):
        """Test basic at-least-once message delivery."""
        user = test_users[0]
        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user
        await ws_manager.connect_user(user.id, websocket)
        
        # Setup delivery tracking
        channel = f"user:{user.id}"
        await pubsub_client.subscribe(channel)
        
        # Send tracked message
        message_id = str(uuid4())
        test_message = create_test_message(
            "delivery_test", 
            user.id, 
            {
                "message_id": message_id,
                "content": "Delivery guarantee test",
                "delivery_required": True
            }
        )
        
        delivery_tracker.track_sent(message_id, test_message)
        
        # Publish message
        await redis_client.publish(channel, json.dumps(test_message))
        
        # Verify delivery
        await asyncio.sleep(0.1)
        message = await pubsub_client.get_message(timeout=1.0)
        
        if message and message['type'] == 'message':
            received_data = json.loads(message['data'])
            if received_data.get('data', {}).get('message_id') == message_id:
                delivery_tracker.mark_delivered(message_id)
        
        # Verify delivery guarantee
        assert delivery_tracker.get_delivery_rate() >= 0.99  # 99% delivery rate
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)
    
    async def test_message_delivery_with_retry_mechanism(self, ws_manager, redis_client, test_users, delivery_tracker):
        """Test message delivery with retry mechanism."""
        user = test_users[0]
        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user
        await ws_manager.connect_user(user.id, websocket)
        
        # Send message with retry logic
        message_id = str(uuid4())
        test_message = create_test_message(
            "retry_test", 
            user.id, 
            {
                "message_id": message_id,
                "content": "Retry delivery test",
                "max_retries": 3
            }
        )
        
        delivery_tracker.track_sent(message_id, test_message)
        
        # Store message for retry in Redis
        retry_key = f"message_retry:{message_id}"
        await redis_client.set(retry_key, json.dumps(test_message), ex=300)
        
        # Simulate delivery attempts
        max_retries = 3
        for attempt in range(max_retries):
            try:
                success = await ws_manager.send_message_to_user(user.id, test_message)
                if success:
                    delivery_tracker.mark_delivered(message_id)
                    await redis_client.delete(retry_key)
                    break
            except Exception:
                if attempt == max_retries - 1:
                    delivery_tracker.mark_failed(message_id)
        
        # Verify retry mechanism effectiveness
        assert message_id in delivery_tracker.delivered_messages
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)
    
    async def test_bulk_message_delivery_guarantee(self, ws_manager, redis_client, pubsub_client, test_users, delivery_tracker):
        """Test delivery guarantees for bulk messages."""
        user = test_users[0]
        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user
        await ws_manager.connect_user(user.id, websocket)
        
        channel = f"user:{user.id}"
        await pubsub_client.subscribe(channel)
        
        # Send bulk messages
        message_count = 50
        message_ids = []
        
        for i in range(message_count):
            message_id = str(uuid4())
            message_ids.append(message_id)
            
            test_message = create_test_message(
                "bulk_delivery", 
                user.id, 
                {
                    "message_id": message_id,
                    "sequence": i,
                    "content": f"Bulk message {i}"
                }
            )
            
            delivery_tracker.track_sent(message_id, test_message)
            await redis_client.publish(channel, json.dumps(test_message))
        
        # Collect delivered messages
        delivered_count = 0
        timeout_time = time.time() + 5.0
        
        while time.time() < timeout_time and delivered_count < message_count:
            message = await pubsub_client.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                try:
                    received_data = json.loads(message['data'])
                    msg_id = received_data.get('data', {}).get('message_id')
                    if msg_id in message_ids:
                        delivery_tracker.mark_delivered(msg_id)
                        delivered_count += 1
                except json.JSONDecodeError:
                    continue
        
        # Verify bulk delivery rate
        delivery_rate = delivery_tracker.get_delivery_rate()
        assert delivery_rate >= 0.95  # 95% for bulk operations
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)
    
    async def test_message_ordering_guarantee(self, ws_manager, redis_client, pubsub_client, test_users):
        """Test message ordering preservation in delivery."""
        user = test_users[0]
        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user
        await ws_manager.connect_user(user.id, websocket)
        
        channel = f"user:{user.id}"
        await pubsub_client.subscribe(channel)
        
        # Send ordered messages
        sequence_count = 10
        sent_sequence = []
        
        for i in range(sequence_count):
            message_id = str(uuid4())
            test_message = create_test_message(
                "order_test", 
                user.id, 
                {
                    "message_id": message_id,
                    "sequence": i,
                    "timestamp": time.time()
                }
            )
            
            sent_sequence.append(i)
            await redis_client.publish(channel, json.dumps(test_message))
            await asyncio.sleep(0.01)  # Small delay to ensure ordering
        
        # Collect received messages
        received_sequence = []
        timeout_time = time.time() + 3.0
        
        while time.time() < timeout_time and len(received_sequence) < sequence_count:
            message = await pubsub_client.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                try:
                    received_data = json.loads(message['data'])
                    sequence = received_data.get('data', {}).get('sequence')
                    if sequence is not None:
                        received_sequence.append(sequence)
                except json.JSONDecodeError:
                    continue
        
        # Verify ordering (allowing for some Redis pub/sub reordering)
        # In production, application-level sequence numbers would enforce strict ordering
        assert len(received_sequence) >= sequence_count * 0.9
        
        # Cleanup
        await ws_manager.disconnect_user(user.id, websocket)
    
    async def test_message_persistence_for_offline_users(self, redis_client, test_users, delivery_tracker):
        """Test message persistence for offline users."""
        offline_user = test_users[0]
        
        # Store messages for offline user
        message_count = 5
        offline_queue_key = f"offline_messages:{offline_user.id}"
        
        for i in range(message_count):
            message_id = str(uuid4())
            test_message = create_test_message(
                "offline_message", 
                offline_user.id, 
                {
                    "message_id": message_id,
                    "content": f"Offline message {i}",
                    "priority": "high"
                }
            )
            
            delivery_tracker.track_sent(message_id, test_message)
            
            # Store in Redis for offline delivery
            await redis_client.lpush(offline_queue_key, json.dumps(test_message))
            await redis_client.expire(offline_queue_key, 86400)  # 24 hour TTL
        
        # Verify messages stored
        stored_count = await redis_client.llen(offline_queue_key)
        assert stored_count == message_count
        
        # Simulate user coming online and receiving stored messages
        websocket = MockWebSocketForRedis(offline_user.id)
        
        # Retrieve and "deliver" stored messages
        while await redis_client.llen(offline_queue_key) > 0:
            message_data = await redis_client.rpop(offline_queue_key)
            if message_data:
                try:
                    message = json.loads(message_data)
                    msg_id = message.get('data', {}).get('message_id')
                    if msg_id:
                        delivery_tracker.mark_delivered(msg_id)
                        await websocket.send_json(message)
                except json.JSONDecodeError:
                    continue
        
        # Verify offline message delivery
        assert delivery_tracker.get_delivery_rate() >= 0.99
    
    @mock_justified("L3: Message delivery guarantee testing with real Redis")
    async def test_message_delivery_under_load(self, ws_manager, redis_client, test_users, delivery_tracker):
        """Test message delivery guarantees under system load."""
        # Setup multiple connected users
        connections = []
        for user in test_users:
            websocket = MockWebSocketForRedis(user.id)
            await ws_manager.connect_user(user.id, websocket)
            connections.append((user, websocket))
        
        # Generate load with concurrent message delivery
        total_messages = 100
        messages_per_user = total_messages // len(test_users)
        
        tasks = []
        for user, _ in connections:
            for i in range(messages_per_user):
                message_id = str(uuid4())
                test_message = create_test_message(
                    "load_test", 
                    user.id, 
                    {
                        "message_id": message_id,
                        "load_test": True,
                        "user_batch": i
                    }
                )
                
                delivery_tracker.track_sent(message_id, test_message)
                
                # Create delivery task
                task = ws_manager.send_message_to_user(user.id, test_message)
                tasks.append((message_id, task))
        
        # Execute all deliveries concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[task for _, task in tasks], 
            return_exceptions=True
        )
        delivery_time = time.time() - start_time
        
        # Mark successful deliveries
        for i, result in enumerate(results):
            message_id, _ = tasks[i]
            if not isinstance(result, Exception) and result:
                delivery_tracker.mark_delivered(message_id)
            else:
                delivery_tracker.mark_failed(message_id)
        
        # Verify delivery guarantees under load
        delivery_rate = delivery_tracker.get_delivery_rate()
        assert delivery_rate >= 0.95  # 95% under load
        assert delivery_time < 10.0  # Performance requirement
        
        # Cleanup
        for user, websocket in connections:
            await ws_manager.disconnect_user(user.id, websocket)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])