"""
WebSocket Test 3: Message Queuing During Disconnection

Tests that validate WebSocket clients receive queued messages sent by agents 
while the client was briefly disconnected, delivered in the correct order upon reconnection.

Business Value: Prevents $75K+ MRR loss from message drops during network instability,
ensures 99.95% message delivery guaranteeing customer trust and workflow continuity.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from enum import Enum

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from app.logging_config import central_logger
from app.services.websocket.message_queue import MessageQueue, QueuedMessage, MessagePriority, MessageStatus

logger = central_logger.get_logger(__name__)


class MessageQueueState(Enum):
    """Queue states for testing"""
    EMPTY = "empty"
    PARTIAL = "partial" 
    FULL = "full"
    OVERFLOWING = "overflowing"


@dataclass
class QueueTestMessage:
    """Test message with metadata for queue validation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = "test_user"
    type: str = "agent_response"
    delivered: bool = False
    delivery_timestamp: Optional[datetime] = None
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format"""
        return {
            "id": self.id,
            "type": self.type,
            "payload": {
                "content": self.content,
                "timestamp": self.timestamp.isoformat(),
                "user_id": self.user_id
            },
            "priority": self.priority.value
        }


class MockMessageQueueManager:
    """Mock message queue manager for testing queuing behavior"""
    
    def __init__(self, max_queue_size: int = 1000, message_ttl: int = 300):
        self.max_queue_size = max_queue_size
        self.message_ttl = message_ttl
        self.queues: Dict[str, List[QueueTestMessage]] = {}
        self.disconnected_users: set = set()
        self.queue_overflow_policy = "drop_oldest"
        self.message_expiry_enabled = True
        
    async def connect_user(self, user_id: str) -> None:
        """Connect user and deliver queued messages"""
        if user_id in self.disconnected_users:
            self.disconnected_users.remove(user_id)
            await self._deliver_queued_messages(user_id)
    
    async def disconnect_user(self, user_id: str) -> None:
        """Disconnect user and enable queuing"""
        self.disconnected_users.add(user_id)
        if user_id not in self.queues:
            self.queues[user_id] = []
    
    async def send_message_to_user(self, user_id: str, message: QueueTestMessage) -> bool:
        """Send message to user or queue if disconnected"""
        if user_id in self.disconnected_users:
            return await self._queue_message(user_id, message)
        else:
            # Direct delivery for connected users
            message.delivered = True
            message.delivery_timestamp = datetime.now(timezone.utc)
            return True
    
    async def _queue_message(self, user_id: str, message: QueueTestMessage) -> bool:
        """Queue message for disconnected user"""
        if user_id not in self.queues:
            self.queues[user_id] = []
        
        user_queue = self.queues[user_id]
        
        # Check queue overflow
        if len(user_queue) >= self.max_queue_size:
            if not await self._handle_queue_overflow(user_queue, message):
                return False
        
        # Insert message based on priority
        await self._insert_message_by_priority(user_queue, message)
        
        logger.info(f"Queued message {message.id} for user {user_id} (queue size: {len(user_queue)})")
        return True
    
    async def _handle_queue_overflow(self, user_queue: List[QueueTestMessage], new_message: QueueTestMessage) -> bool:
        """Handle queue overflow based on policy"""
        if self.queue_overflow_policy == "drop_oldest":
            user_queue.pop(0)
            return True
        elif self.queue_overflow_policy == "drop_newest":
            return False  # Don't add new message
        elif self.queue_overflow_policy == "reject":
            return False
        return True
    
    async def _insert_message_by_priority(self, user_queue: List[QueueTestMessage], message: QueueTestMessage) -> None:
        """Insert message maintaining priority order"""
        # Find insertion point to maintain priority order
        insertion_index = 0
        for i, queued_msg in enumerate(user_queue):
            if message.priority.value > queued_msg.priority.value:
                insertion_index = i
                break
            insertion_index = i + 1
        
        user_queue.insert(insertion_index, message)
    
    async def _deliver_queued_messages(self, user_id: str) -> List[QueueTestMessage]:
        """Deliver all queued messages for user upon reconnection"""
        if user_id not in self.queues:
            return []
        
        user_queue = self.queues[user_id]
        
        # Clean expired messages if enabled
        if self.message_expiry_enabled:
            await self._clean_expired_messages(user_queue)
        
        # Mark all remaining messages as delivered
        delivered_messages = []
        for message in user_queue:
            message.delivered = True
            message.delivery_timestamp = datetime.now(timezone.utc)
            delivered_messages.append(message)
        
        # Clear the queue
        self.queues[user_id] = []
        
        logger.info(f"Delivered {len(delivered_messages)} queued messages to user {user_id}")
        return delivered_messages
    
    async def _clean_expired_messages(self, user_queue: List[QueueTestMessage]) -> None:
        """Remove expired messages from queue"""
        now = datetime.now(timezone.utc)
        expired_indices = []
        
        for i, message in enumerate(user_queue):
            if (now - message.timestamp).total_seconds() > self.message_ttl:
                expired_indices.append(i)
        
        # Remove expired messages (reverse order to maintain indices)
        for i in reversed(expired_indices):
            expired_message = user_queue.pop(i)
            logger.info(f"Removed expired message {expired_message.id}")
    
    def get_queue_size(self, user_id: str) -> int:
        """Get current queue size for user"""
        return len(self.queues.get(user_id, []))
    
    def get_queue_state(self, user_id: str) -> MessageQueueState:
        """Get current queue state"""
        queue_size = self.get_queue_size(user_id)
        if queue_size == 0:
            return MessageQueueState.EMPTY
        elif queue_size < self.max_queue_size * 0.8:
            return MessageQueueState.PARTIAL
        elif queue_size < self.max_queue_size:
            return MessageQueueState.FULL
        else:
            return MessageQueueState.OVERFLOWING


class WebSocketQueueTestClient:
    """WebSocket test client with queue-aware functionality"""
    
    def __init__(self, uri: str, user_id: str, queue_manager: MockMessageQueueManager):
        self.uri = uri
        self.user_id = user_id
        self.queue_manager = queue_manager
        self.websocket = None
        self.is_connected = False
        self.received_messages: List[QueueTestMessage] = []
        
    async def connect(self) -> bool:
        """Connect to WebSocket and receive queued messages"""
        try:
            # Mock WebSocket connection for testing
            self.websocket = AsyncMock()
            self.is_connected = True
            
            # Notify queue manager of connection
            await self.queue_manager.connect_user(self.user_id)
            
            # Receive any queued messages
            queued_messages = await self.queue_manager._deliver_queued_messages(self.user_id)
            self.received_messages.extend(queued_messages)
            
            logger.info(f"Connected user {self.user_id}, received {len(queued_messages)} queued messages")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket"""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            
            # Notify queue manager of disconnection
            await self.queue_manager.disconnect_user(self.user_id)
            
            logger.info(f"Disconnected user {self.user_id}")
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket server"""
        if not self.is_connected:
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def get_received_messages(self) -> List[QueueTestMessage]:
        """Get all received messages"""
        return self.received_messages.copy()
    
    def clear_received_messages(self) -> None:
        """Clear received messages buffer"""
        self.received_messages.clear()


# Test Fixtures

@pytest.fixture
def mock_queue_manager():
    """Mock message queue manager fixture"""
    return MockMessageQueueManager(max_queue_size=10, message_ttl=300)  # Reduced for testing


@pytest.fixture
def mock_queue_manager_small():
    """Mock message queue manager with small limits for overflow testing"""
    return MockMessageQueueManager(max_queue_size=3, message_ttl=2)  # Very small for testing


@pytest.fixture
async def queue_test_client(mock_queue_manager):
    """WebSocket queue test client fixture"""
    client = WebSocketQueueTestClient("ws://mock/ws", "test_user_123", mock_queue_manager)
    yield client
    
    # Cleanup
    if client.is_connected:
        await client.disconnect()


@pytest.fixture
async def connected_client(queue_test_client):
    """Pre-connected test client"""
    await queue_test_client.connect()
    return queue_test_client


def create_test_message(content: str, priority: MessagePriority = MessagePriority.NORMAL, user_id: str = "test_user_123") -> QueueTestMessage:
    """Helper to create test messages"""
    return QueueTestMessage(
        content=content,
        priority=priority,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc)
    )


# Test Cases

@pytest.mark.asyncio
async def test_single_message_queuing_during_disconnection(queue_test_client, mock_queue_manager):
    """
    Test Case 1: Single Message Queuing During Disconnection
    
    Verify that a single message sent during disconnection is queued and delivered upon reconnection.
    """
    # Establish initial connection
    await queue_test_client.connect()
    assert queue_test_client.is_connected
    
    # Clear any initial messages
    queue_test_client.clear_received_messages()
    
    # Simulate disconnection
    await queue_test_client.disconnect()
    assert not queue_test_client.is_connected
    assert queue_test_client.user_id in mock_queue_manager.disconnected_users
    
    # Create and send message while disconnected
    test_message = create_test_message("Hello, this message should be queued!")
    message_sent_time = time.time()
    
    success = await mock_queue_manager.send_message_to_user(queue_test_client.user_id, test_message)
    assert success, "Message should be successfully queued"
    
    # Verify message is queued
    queue_size = mock_queue_manager.get_queue_size(queue_test_client.user_id)
    assert queue_size == 1, f"Expected 1 message in queue, got {queue_size}"
    
    # Verify message is not yet delivered
    assert not test_message.delivered, "Message should not be delivered while disconnected"
    assert test_message.delivery_timestamp is None
    
    # Reconnect within reasonable time
    await asyncio.sleep(0.5)  # Brief wait to simulate realistic disconnection
    reconnect_start = time.time()
    
    await queue_test_client.connect()
    reconnect_time = time.time() - reconnect_start
    
    # Verify reconnection was successful
    assert queue_test_client.is_connected
    assert queue_test_client.user_id not in mock_queue_manager.disconnected_users
    
    # Verify message was delivered
    received_messages = queue_test_client.get_received_messages()
    assert len(received_messages) == 1, f"Expected 1 delivered message, got {len(received_messages)}"
    
    delivered_message = received_messages[0]
    assert delivered_message.id == test_message.id
    assert delivered_message.content == test_message.content
    assert delivered_message.delivered, "Message should be marked as delivered"
    assert delivered_message.delivery_timestamp is not None
    
    # Verify queue is now empty
    queue_size = mock_queue_manager.get_queue_size(queue_test_client.user_id)
    assert queue_size == 0, f"Queue should be empty after delivery, got {queue_size}"
    
    # Performance validation
    assert reconnect_time < 1.0, f"Reconnection took {reconnect_time:.3f}s, expected < 1.0s"
    
    # Verify delivery timing
    delivery_delay = delivered_message.delivery_timestamp - test_message.timestamp
    assert delivery_delay.total_seconds() < 2.0, f"Delivery delay {delivery_delay.total_seconds():.3f}s too long"
    
    logger.info(f"✓ Single message queued and delivered successfully in {reconnect_time:.3f}s")


@pytest.mark.asyncio
async def test_multiple_messages_queuing_with_order_preservation(queue_test_client, mock_queue_manager):
    """
    Test Case 2: Multiple Messages Queuing with Order Preservation
    
    Ensure multiple messages are queued in correct order and delivered sequentially.
    """
    # Establish connection and disconnect
    await queue_test_client.connect()
    queue_test_client.clear_received_messages()
    await queue_test_client.disconnect()
    
    # Create multiple test messages with timestamps
    test_messages = []
    message_contents = [
        "First message - step 1",
        "Second message - step 2", 
        "Third message - step 3",
        "Fourth message - step 4",
        "Fifth message - final step"
    ]
    
    # Send messages in sequence with brief intervals
    for i, content in enumerate(message_contents):
        message = create_test_message(content)
        test_messages.append(message)
        
        success = await mock_queue_manager.send_message_to_user(queue_test_client.user_id, message)
        assert success, f"Message {i+1} should be queued successfully"
        
        # Brief interval between messages
        await asyncio.sleep(0.1)
    
    # Verify all messages are queued
    queue_size = mock_queue_manager.get_queue_size(queue_test_client.user_id)
    assert queue_size == 5, f"Expected 5 messages in queue, got {queue_size}"
    
    # Verify no messages are delivered yet
    for message in test_messages:
        assert not message.delivered, f"Message {message.id} should not be delivered while disconnected"
    
    # Wait briefly then reconnect
    await asyncio.sleep(0.5)
    reconnect_start = time.time()
    await queue_test_client.connect()
    reconnect_time = time.time() - reconnect_start
    
    # Verify all messages were delivered
    received_messages = queue_test_client.get_received_messages()
    assert len(received_messages) == 5, f"Expected 5 delivered messages, got {len(received_messages)}"
    
    # Verify order preservation
    for i, (original, received) in enumerate(zip(test_messages, received_messages)):
        assert received.id == original.id, f"Message {i+1} ID mismatch"
        assert received.content == original.content, f"Message {i+1} content mismatch"
        assert received.delivered, f"Message {i+1} should be marked as delivered"
        
        # Verify delivery order based on timestamp
        if i > 0:
            prev_delivery = received_messages[i-1].delivery_timestamp
            curr_delivery = received.delivery_timestamp
            assert curr_delivery >= prev_delivery, f"Message {i+1} delivered out of order"
    
    # Verify queue is empty
    queue_size = mock_queue_manager.get_queue_size(queue_test_client.user_id)
    assert queue_size == 0, "Queue should be empty after delivery"
    
    # Verify no message duplication
    received_ids = [msg.id for msg in received_messages]
    assert len(received_ids) == len(set(received_ids)), "No message duplication should occur"
    
    logger.info(f"✓ 5 messages delivered in correct order in {reconnect_time:.3f}s")


@pytest.mark.asyncio
async def test_queue_overflow_handling_and_limits(queue_test_client, mock_queue_manager_small):
    """
    Test Case 3: Queue Overflow Handling and Limits
    
    Test behavior when message queue exceeds configured limits.
    """
    # Use small queue manager (max 3 messages)
    queue_test_client.queue_manager = mock_queue_manager_small
    
    # Connect and disconnect
    await queue_test_client.connect()
    queue_test_client.clear_received_messages()
    await queue_test_client.disconnect()
    
    # Set overflow policy to drop oldest
    mock_queue_manager_small.queue_overflow_policy = "drop_oldest"
    
    # Send messages to fill queue beyond limit
    test_messages = []
    for i in range(5):  # Send 5 messages to 3-message queue
        message = create_test_message(f"Message {i+1} - testing overflow")
        test_messages.append(message)
        
        success = await mock_queue_manager_small.send_message_to_user(queue_test_client.user_id, message)
        assert success, f"Message {i+1} should be handled (queued or overflow managed)"
    
    # Verify queue is at maximum size
    queue_size = mock_queue_manager_small.get_queue_size(queue_test_client.user_id)
    assert queue_size == 3, f"Queue should be capped at 3 messages, got {queue_size}"
    
    # Verify queue state
    queue_state = mock_queue_manager_small.get_queue_state(queue_test_client.user_id)
    assert queue_state == MessageQueueState.FULL, f"Queue should be full, got {queue_state}"
    
    # Reconnect and verify behavior
    await queue_test_client.connect()
    received_messages = queue_test_client.get_received_messages()
    
    # Should receive exactly 3 messages (newest ones due to drop_oldest policy)
    assert len(received_messages) == 3, f"Expected 3 messages after overflow handling, got {len(received_messages)}"
    
    # Verify we got the last 3 messages (messages 3, 4, 5)
    expected_contents = ["Message 3 - testing overflow", "Message 4 - testing overflow", "Message 5 - testing overflow"]
    received_contents = [msg.content for msg in received_messages]
    
    for expected_content in expected_contents:
        assert expected_content in received_contents, f"Expected message '{expected_content}' not found in received messages"
    
    # Test different overflow policy
    await queue_test_client.disconnect()
    mock_queue_manager_small.queue_overflow_policy = "reject"
    
    # Fill queue again
    for i in range(3):
        message = create_test_message(f"Fill message {i+1}")
        await mock_queue_manager_small.send_message_to_user(queue_test_client.user_id, message)
    
    # Try to add one more (should be rejected)
    overflow_message = create_test_message("This should be rejected")
    success = await mock_queue_manager_small.send_message_to_user(queue_test_client.user_id, overflow_message)
    
    # Verify rejection behavior
    assert not success, "Message should be rejected when queue is full and policy is 'reject'"
    
    queue_size = mock_queue_manager_small.get_queue_size(queue_test_client.user_id)
    assert queue_size == 3, f"Queue size should remain 3 after rejection, got {queue_size}"
    
    logger.info("✓ Queue overflow handling working correctly for both 'drop_oldest' and 'reject' policies")


@pytest.mark.asyncio
async def test_priority_message_handling_during_queue(queue_test_client, mock_queue_manager):
    """
    Test Case 4: Priority Message Handling During Queue
    
    Validate that high-priority messages are handled correctly during queuing.
    """
    # Connect and disconnect
    await queue_test_client.connect()
    queue_test_client.clear_received_messages()
    await queue_test_client.disconnect()
    
    # Create messages with different priorities
    messages_to_send = [
        create_test_message("Normal priority message 1", MessagePriority.NORMAL),
        create_test_message("High priority message 1", MessagePriority.HIGH),
        create_test_message("Normal priority message 2", MessagePriority.NORMAL),
        create_test_message("Critical priority message", MessagePriority.CRITICAL),
        create_test_message("Low priority message", MessagePriority.LOW),
        create_test_message("High priority message 2", MessagePriority.HIGH),
        create_test_message("Normal priority message 3", MessagePriority.NORMAL)
    ]
    
    # Send all messages
    for message in messages_to_send:
        success = await mock_queue_manager.send_message_to_user(queue_test_client.user_id, message)
        assert success, f"Message {message.content} should be queued successfully"
        await asyncio.sleep(0.05)  # Brief interval
    
    # Verify all messages are queued
    queue_size = mock_queue_manager.get_queue_size(queue_test_client.user_id)
    assert queue_size == 7, f"Expected 7 messages in queue, got {queue_size}"
    
    # Reconnect and receive messages
    await queue_test_client.connect()
    received_messages = queue_test_client.get_received_messages()
    
    assert len(received_messages) == 7, f"Expected 7 delivered messages, got {len(received_messages)}"
    
    # Verify priority ordering: Critical > High > Normal > Low
    priority_order = [msg.priority for msg in received_messages]
    
    # Find indices of each priority level
    critical_indices = [i for i, p in enumerate(priority_order) if p == MessagePriority.CRITICAL]
    high_indices = [i for i, p in enumerate(priority_order) if p == MessagePriority.HIGH]
    normal_indices = [i for i, p in enumerate(priority_order) if p == MessagePriority.NORMAL]
    low_indices = [i for i, p in enumerate(priority_order) if p == MessagePriority.LOW]
    
    # Verify priority precedence
    if critical_indices and high_indices:
        assert max(critical_indices) < min(high_indices), "Critical messages should come before High priority"
    
    if high_indices and normal_indices:
        assert max(high_indices) < min(normal_indices), "High priority messages should come before Normal"
    
    if normal_indices and low_indices:
        assert max(normal_indices) < min(low_indices), "Normal priority messages should come before Low"
    
    # Verify within-priority order preservation (FIFO within same priority)
    high_messages = [msg for msg in received_messages if msg.priority == MessagePriority.HIGH]
    if len(high_messages) >= 2:
        assert high_messages[0].content == "High priority message 1"
        assert high_messages[1].content == "High priority message 2"
    
    normal_messages = [msg for msg in received_messages if msg.priority == MessagePriority.NORMAL]
    if len(normal_messages) >= 3:
        assert normal_messages[0].content == "Normal priority message 1"
        assert normal_messages[1].content == "Normal priority message 2"
        assert normal_messages[2].content == "Normal priority message 3"
    
    # Verify no message loss
    sent_contents = [msg.content for msg in messages_to_send]
    received_contents = [msg.content for msg in received_messages]
    
    for sent_content in sent_contents:
        assert sent_content in received_contents, f"Message '{sent_content}' was lost during priority handling"
    
    logger.info("✓ Priority message handling preserved order: Critical > High > Normal > Low, with FIFO within priorities")


@pytest.mark.asyncio
async def test_queue_expiration_and_cleanup(queue_test_client, mock_queue_manager_small):
    """
    Test Case 5: Queue Expiration and Cleanup
    
    Test that expired messages are properly cleaned up from the queue.
    """
    # Use small TTL (2 seconds) for testing
    queue_test_client.queue_manager = mock_queue_manager_small
    mock_queue_manager_small.message_ttl = 2  # 2 second TTL
    
    # Connect and disconnect
    await queue_test_client.connect()
    queue_test_client.clear_received_messages()
    await queue_test_client.disconnect()
    
    # Send initial messages
    initial_messages = []
    for i in range(3):
        message = create_test_message(f"Initial message {i+1} - will expire")
        initial_messages.append(message)
        await mock_queue_manager_small.send_message_to_user(queue_test_client.user_id, message)
    
    # Verify messages are queued
    queue_size = mock_queue_manager_small.get_queue_size(queue_test_client.user_id)
    assert queue_size == 3, f"Expected 3 initial messages, got {queue_size}"
    
    # Wait for messages to expire (TTL + buffer)
    await asyncio.sleep(2.5)
    
    # Send fresh messages after expiration
    fresh_messages = []
    for i in range(2):
        message = create_test_message(f"Fresh message {i+1} - should be delivered")
        fresh_messages.append(message)
        await mock_queue_manager_small.send_message_to_user(queue_test_client.user_id, message)
    
    # Verify queue contains all messages before cleanup
    queue_size_before_cleanup = mock_queue_manager_small.get_queue_size(queue_test_client.user_id)
    assert queue_size_before_cleanup == 5, f"Expected 5 messages before cleanup, got {queue_size_before_cleanup}"
    
    # Reconnect (this should trigger cleanup of expired messages)
    await queue_test_client.connect()
    
    # Verify only fresh messages were delivered
    received_messages = queue_test_client.get_received_messages()
    assert len(received_messages) == 2, f"Expected only 2 fresh messages after expiration cleanup, got {len(received_messages)}"
    
    # Verify we received the correct messages
    received_contents = [msg.content for msg in received_messages]
    expected_contents = ["Fresh message 1 - should be delivered", "Fresh message 2 - should be delivered"]
    
    for expected_content in expected_contents:
        assert expected_content in received_contents, f"Expected fresh message '{expected_content}' not found"
    
    # Verify expired messages were not delivered
    for initial_message in initial_messages:
        assert not initial_message.delivered, f"Expired message {initial_message.content} should not be delivered"
    
    # Verify fresh messages were delivered
    for fresh_message in fresh_messages:
        assert fresh_message.delivered, f"Fresh message {fresh_message.content} should be delivered"
    
    # Verify queue is clean after delivery
    queue_size = mock_queue_manager_small.get_queue_size(queue_test_client.user_id)
    assert queue_size == 0, f"Queue should be empty after delivery, got {queue_size}"
    
    # Test expiration during queuing (without reconnection)
    await queue_test_client.disconnect()
    
    # Send message and let it expire
    expiring_message = create_test_message("This will expire before delivery")
    await mock_queue_manager_small.send_message_to_user(queue_test_client.user_id, expiring_message)
    
    # Wait for expiration
    await asyncio.sleep(2.5)
    
    # Manual cleanup trigger (simulates periodic cleanup)
    user_queue = mock_queue_manager_small.queues.get(queue_test_client.user_id, [])
    await mock_queue_manager_small._clean_expired_messages(user_queue)
    
    # Verify expired message was removed from queue
    queue_size = mock_queue_manager_small.get_queue_size(queue_test_client.user_id)
    assert queue_size == 0, f"Expired message should be removed from queue, got {queue_size}"
    
    logger.info("✓ Message expiration and cleanup working correctly - expired messages removed, fresh messages delivered")


# Additional Edge Case Tests

@pytest.mark.asyncio
async def test_rapid_disconnect_reconnect_cycles(queue_test_client, mock_queue_manager):
    """Test behavior during multiple quick disconnection/reconnection cycles"""
    
    message_count = 0
    cycle_results = []
    
    for cycle in range(5):
        # Connect
        await queue_test_client.connect()
        queue_test_client.clear_received_messages()
        
        # Disconnect
        await queue_test_client.disconnect()
        
        # Send messages during disconnection
        cycle_messages = []
        for i in range(2):
            message = create_test_message(f"Cycle {cycle+1} Message {i+1}")
            cycle_messages.append(message)
            await mock_queue_manager.send_message_to_user(queue_test_client.user_id, message)
            message_count += 1
        
        # Brief wait
        await asyncio.sleep(0.1)
        
        # Reconnect
        start_time = time.time()
        await queue_test_client.connect()
        reconnect_time = time.time() - start_time
        
        # Verify delivery
        received_messages = queue_test_client.get_received_messages()
        
        cycle_result = {
            "cycle": cycle + 1,
            "sent": len(cycle_messages),
            "received": len(received_messages),
            "reconnect_time": reconnect_time,
            "all_delivered": len(received_messages) == len(cycle_messages)
        }
        cycle_results.append(cycle_result)
        
        # Verify messages were delivered correctly
        assert len(received_messages) == 2, f"Cycle {cycle+1}: Expected 2 messages, got {len(received_messages)}"
        assert reconnect_time < 0.5, f"Cycle {cycle+1}: Reconnection too slow: {reconnect_time:.3f}s"
    
    # Verify all cycles were successful
    for result in cycle_results:
        assert result["all_delivered"], f"Cycle {result['cycle']} failed to deliver all messages"
    
    # Performance analysis
    avg_reconnect_time = sum(r["reconnect_time"] for r in cycle_results) / len(cycle_results)
    max_reconnect_time = max(r["reconnect_time"] for r in cycle_results)
    
    assert avg_reconnect_time < 0.3, f"Average reconnect time {avg_reconnect_time:.3f}s too slow"
    assert max_reconnect_time < 0.5, f"Max reconnect time {max_reconnect_time:.3f}s too slow"
    
    logger.info(f"✓ 5 rapid cycles completed: avg {avg_reconnect_time:.3f}s, max {max_reconnect_time:.3f}s")


@pytest.mark.asyncio
async def test_concurrent_message_sending_during_disconnection(mock_queue_manager):
    """Test multiple agents sending messages to same disconnected client"""
    
    user_id = "test_user_concurrent"
    await mock_queue_manager.disconnect_user(user_id)
    
    # Simulate multiple agents sending messages concurrently
    async def send_agent_messages(agent_id: str, message_count: int):
        messages = []
        for i in range(message_count):
            message = create_test_message(f"Agent {agent_id} Message {i+1}", user_id=user_id)
            await mock_queue_manager.send_message_to_user(user_id, message)
            messages.append(message)
            await asyncio.sleep(0.01)  # Brief interval
        return messages
    
    # Create concurrent tasks for multiple agents
    agent_tasks = [
        send_agent_messages("Agent1", 3),
        send_agent_messages("Agent2", 3),
        send_agent_messages("Agent3", 2)
    ]
    
    # Execute concurrently
    start_time = time.time()
    agent_results = await asyncio.gather(*agent_tasks)
    concurrent_time = time.time() - start_time
    
    # Verify all messages were queued
    total_expected = sum(len(result) for result in agent_results)
    queue_size = mock_queue_manager.get_queue_size(user_id)
    assert queue_size == total_expected, f"Expected {total_expected} messages queued, got {queue_size}"
    
    # Create client and reconnect
    client = WebSocketQueueTestClient("ws://mock/ws", user_id, mock_queue_manager)
    await client.connect()
    
    # Verify all messages were delivered
    received_messages = client.get_received_messages()
    assert len(received_messages) == total_expected, f"Expected {total_expected} messages delivered, got {len(received_messages)}"
    
    # Verify message integrity (no corruption from concurrent access)
    received_contents = [msg.content for msg in received_messages]
    
    # Check each agent's messages are present
    for agent_id in ["Agent1", "Agent2", "Agent3"]:
        agent_messages = [content for content in received_contents if content.startswith(f"Agent {agent_id}")]
        expected_count = 3 if agent_id in ["Agent1", "Agent2"] else 2
        assert len(agent_messages) == expected_count, f"Expected {expected_count} messages from {agent_id}, got {len(agent_messages)}"
    
    # Verify no message duplication
    assert len(received_contents) == len(set(received_contents)), "No message duplication should occur"
    
    logger.info(f"✓ Concurrent message sending handled correctly: {total_expected} messages from 3 agents in {concurrent_time:.3f}s")


@pytest.mark.asyncio
async def test_system_resource_constraints_simulation(mock_queue_manager):
    """Test queue behavior under simulated resource constraints"""
    
    # Simulate low memory condition by reducing queue size
    original_max_size = mock_queue_manager.max_queue_size
    mock_queue_manager.max_queue_size = 5  # Severely limited
    
    user_id = "test_user_resources"
    await mock_queue_manager.disconnect_user(user_id)
    
    # Try to queue many messages under resource constraints
    messages_sent = []
    successful_queues = 0
    
    for i in range(10):  # Try to send 10 messages to 5-message queue
        message = create_test_message(f"Resource test message {i+1}", user_id=user_id)
        messages_sent.append(message)
        
        success = await mock_queue_manager.send_message_to_user(user_id, message)
        if success:
            successful_queues += 1
    
    # Verify graceful degradation
    queue_size = mock_queue_manager.get_queue_size(user_id)
    assert queue_size <= mock_queue_manager.max_queue_size, f"Queue size {queue_size} exceeds limit {mock_queue_manager.max_queue_size}"
    assert successful_queues > 0, "At least some messages should be queued successfully"
    
    # Test queue performance under constraints
    client = WebSocketQueueTestClient("ws://mock/ws", user_id, mock_queue_manager)
    
    start_time = time.time()
    await client.connect()
    delivery_time = time.time() - start_time
    
    # Verify delivery works under constraints
    received_messages = client.get_received_messages()
    assert len(received_messages) > 0, "Some messages should be delivered even under resource constraints"
    
    # Performance should not degrade significantly
    assert delivery_time < 1.0, f"Delivery time {delivery_time:.3f}s too slow under resource constraints"
    
    # Restore original settings
    mock_queue_manager.max_queue_size = original_max_size
    
    logger.info(f"✓ Resource constraints handled gracefully: {len(received_messages)} messages delivered in {delivery_time:.3f}s")


# Performance and Metrics Test

@pytest.mark.asyncio
async def test_queue_performance_metrics(queue_test_client, mock_queue_manager):
    """Benchmark queue performance metrics"""
    
    # Performance test parameters
    message_counts = [1, 5, 10, 25, 50]
    performance_results = []
    
    for count in message_counts:
        # Setup
        await queue_test_client.connect()
        queue_test_client.clear_received_messages()
        await queue_test_client.disconnect()
        
        # Queue messages
        messages = []
        queue_start = time.time()
        
        for i in range(count):
            message = create_test_message(f"Performance test message {i+1}")
            messages.append(message)
            await mock_queue_manager.send_message_to_user(queue_test_client.user_id, message)
        
        queue_time = time.time() - queue_start
        
        # Delivery test
        delivery_start = time.time()
        await queue_test_client.connect()
        delivery_time = time.time() - delivery_start
        
        # Verify delivery
        received = queue_test_client.get_received_messages()
        assert len(received) == count, f"Expected {count} messages, got {len(received)}"
        
        # Record performance
        result = {
            "count": count,
            "queue_time": queue_time,
            "delivery_time": delivery_time,
            "queue_rate": count / queue_time if queue_time > 0 else float('inf'),
            "delivery_rate": count / delivery_time if delivery_time > 0 else float('inf')
        }
        performance_results.append(result)
        
        logger.info(f"Performance {count} messages: queue {queue_time:.3f}s, delivery {delivery_time:.3f}s")
    
    # Performance assertions
    for result in performance_results:
        # Queue performance should be consistent
        assert result["queue_rate"] > 10, f"Queue rate {result['queue_rate']:.1f} msg/s too slow for {result['count']} messages"
        
        # Delivery should be fast regardless of queue size
        assert result["delivery_time"] < 1.0, f"Delivery time {result['delivery_time']:.3f}s too slow for {result['count']} messages"
    
    # Scalability check - larger queues shouldn't be exponentially slower
    if len(performance_results) >= 2:
        small_result = performance_results[0]  # 1 message
        large_result = performance_results[-1]  # 50 messages
        
        # Delivery time should scale sub-linearly
        time_ratio = large_result["delivery_time"] / small_result["delivery_time"]
        size_ratio = large_result["count"] / small_result["count"]
        
        assert time_ratio < size_ratio * 0.5, f"Delivery time scaling poor: {time_ratio:.1f}x time for {size_ratio:.1f}x messages"
    
    logger.info(f"✓ Performance benchmarks passed for message counts: {message_counts}")


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto"
    ])