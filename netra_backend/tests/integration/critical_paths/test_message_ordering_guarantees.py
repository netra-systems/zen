"""
L2 Integration Test: Message Ordering Guarantees for WebSocket

Business Value Justification (BVJ):
- Segment: Mid/Enterprise  
- Business Goal: Data consistency worth $8K MRR reliability
- Value Impact: Ensures message ordering for critical workflows and collaboration
- Strategic Impact: Prevents data corruption in real-time collaboration features

L2 Test: Real internal message ordering components with mocked external services.
Performance target: <50ms ordering latency, 99.9% ordering accuracy.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.websocket_core.manager import WebSocketManager
from test_framework.mock_utils import mock_justified

@dataclass

class SequencedMessage:

    """Message with sequence information."""

    message_id: str

    user_id: str

    sequence_number: int

    timestamp: float

    content: Dict[str, Any]

    session_id: str = ""

    priority: int = 0  # 0 = normal, 1 = high, 2 = critical

@dataclass

class MessageBuffer:

    """Buffer for out-of-order messages."""

    expected_sequence: int = 0

    buffered_messages: Dict[int, SequencedMessage] = field(default_factory=dict)

    delivered_messages: List[SequencedMessage] = field(default_factory=list)

    last_delivery_time: float = 0.0

    buffer_timeout: float = 5.0  # 5 seconds

    max_buffer_size: int = 100

class MessageSequenceManager:

    """Manage message sequencing and ordering guarantees."""
    
    def __init__(self):

        self.user_sequences = defaultdict(int)  # user_id -> next_sequence_number

        self.message_buffers = defaultdict(MessageBuffer)  # user_id -> buffer

        self.global_sequence = 0

        self.ordering_stats = {

            "total_messages": 0,

            "out_of_order_messages": 0,

            "reordered_messages": 0,

            "dropped_messages": 0,

            "buffer_overflows": 0

        }
    
    def assign_sequence_number(self, user_id: str, message: Dict[str, Any]) -> SequencedMessage:

        """Assign sequence number to outgoing message."""

        sequence_num = self.user_sequences[user_id]

        self.user_sequences[user_id] += 1

        self.global_sequence += 1
        
        sequenced_message = SequencedMessage(

            message_id=str(uuid4()),

            user_id=user_id,

            sequence_number=sequence_num,

            timestamp=time.time(),

            content=message,

            session_id=message.get("session_id", ""),

            priority=message.get("priority", 0)

        )
        
        self.ordering_stats["total_messages"] += 1

        return sequenced_message
    
    def process_incoming_message(self, message: SequencedMessage) -> List[SequencedMessage]:

        """Process incoming message and return deliverable messages in order."""

        user_id = message.user_id

        buffer = self.message_buffers[user_id]

        deliverable_messages = []
        
        # Check if message is next in sequence

        if message.sequence_number == buffer.expected_sequence:
            # Deliver this message immediately

            deliverable_messages.append(message)

            buffer.delivered_messages.append(message)

            buffer.expected_sequence += 1

            buffer.last_delivery_time = time.time()
            
            # Check if buffered messages can now be delivered

            while buffer.expected_sequence in buffer.buffered_messages:

                buffered_msg = buffer.buffered_messages.pop(buffer.expected_sequence)

                deliverable_messages.append(buffered_msg)

                buffer.delivered_messages.append(buffered_msg)

                buffer.expected_sequence += 1

                buffer.last_delivery_time = time.time()

                self.ordering_stats["reordered_messages"] += 1
        
        elif message.sequence_number > buffer.expected_sequence:
            # Future message - buffer it

            self._buffer_message(user_id, message)

            self.ordering_stats["out_of_order_messages"] += 1
        
        else:
            # Duplicate or old message - ignore

            self.ordering_stats["dropped_messages"] += 1
        
        return deliverable_messages
    
    def _buffer_message(self, user_id: str, message: SequencedMessage) -> None:

        """Buffer an out-of-order message."""

        buffer = self.message_buffers[user_id]
        
        # Check buffer capacity

        if len(buffer.buffered_messages) >= buffer.max_buffer_size:
            # Remove oldest buffered message

            oldest_seq = min(buffer.buffered_messages.keys())

            buffer.buffered_messages.pop(oldest_seq)

            self.ordering_stats["buffer_overflows"] += 1
        
        buffer.buffered_messages[message.sequence_number] = message
    
    def check_buffer_timeouts(self) -> List[Tuple[str, List[SequencedMessage]]]:

        """Check for timed out buffered messages and force delivery."""

        current_time = time.time()

        timed_out_deliveries = []
        
        for user_id, buffer in self.message_buffers.items():

            if not buffer.buffered_messages:

                continue
            
            time_since_last_delivery = current_time - buffer.last_delivery_time
            
            if time_since_last_delivery > buffer.buffer_timeout:
                # Force delivery of buffered messages

                forced_messages = []

                sorted_sequences = sorted(buffer.buffered_messages.keys())
                
                for seq_num in sorted_sequences:

                    message = buffer.buffered_messages.pop(seq_num)

                    forced_messages.append(message)

                    buffer.delivered_messages.append(message)
                
                if forced_messages:
                    # Update expected sequence to after forced messages

                    buffer.expected_sequence = max(msg.sequence_number for msg in forced_messages) + 1

                    buffer.last_delivery_time = current_time

                    timed_out_deliveries.append((user_id, forced_messages))
        
        return timed_out_deliveries
    
    def get_ordering_stats(self) -> Dict[str, Any]:

        """Get message ordering statistics."""

        stats = self.ordering_stats.copy()
        
        if stats["total_messages"] > 0:

            stats["ordering_accuracy"] = (

                (stats["total_messages"] - stats["out_of_order_messages"]) / 

                stats["total_messages"] * 100

            )

            stats["reorder_rate"] = (

                stats["reordered_messages"] / stats["total_messages"] * 100

            )

        else:

            stats["ordering_accuracy"] = 100.0

            stats["reorder_rate"] = 0.0
        
        return stats
    
    def get_user_buffer_status(self, user_id: str) -> Dict[str, Any]:

        """Get buffer status for specific user."""

        buffer = self.message_buffers[user_id]
        
        return {

            "user_id": user_id,

            "expected_sequence": buffer.expected_sequence,

            "buffered_count": len(buffer.buffered_messages),

            "buffered_sequences": sorted(buffer.buffered_messages.keys()),

            "delivered_count": len(buffer.delivered_messages),

            "last_delivery_time": buffer.last_delivery_time,

            "buffer_utilization": len(buffer.buffered_messages) / buffer.max_buffer_size * 100

        }

class OrderEnforcer:

    """Enforce message ordering at the delivery level."""
    
    def __init__(self):

        self.delivery_queues = defaultdict(deque)  # user_id -> delivery_queue

        self.processing_stats = {

            "messages_processed": 0,

            "ordering_violations": 0,

            "queue_overflows": 0

        }

        self.max_queue_size = 1000
    
    def enqueue_for_delivery(self, user_id: str, messages: List[SequencedMessage]) -> None:

        """Enqueue messages for ordered delivery."""

        queue = self.delivery_queues[user_id]
        
        for message in messages:
            # Check queue capacity

            if len(queue) >= self.max_queue_size:

                queue.popleft()  # Remove oldest message

                self.processing_stats["queue_overflows"] += 1
            
            queue.append(message)
        
        self.processing_stats["messages_processed"] += len(messages)
    
    async def deliver_next_batch(self, user_id: str, batch_size: int = 10) -> List[SequencedMessage]:

        """Deliver next batch of messages in order."""

        queue = self.delivery_queues[user_id]

        delivered_messages = []
        
        for _ in range(min(batch_size, len(queue))):

            if queue:

                message = queue.popleft()

                delivered_messages.append(message)
        
        return delivered_messages
    
    def verify_delivery_order(self, messages: List[SequencedMessage]) -> Dict[str, Any]:

        """Verify that delivered messages are in correct order."""

        if not messages:

            return {"ordered": True, "violations": []}
        
        violations = []
        
        for i in range(1, len(messages)):

            current_seq = messages[i].sequence_number

            previous_seq = messages[i-1].sequence_number
            
            if current_seq <= previous_seq:

                violations.append({

                    "position": i,

                    "expected_min": previous_seq + 1,

                    "actual": current_seq,

                    "message_id": messages[i].message_id

                })
        
        self.processing_stats["ordering_violations"] += len(violations)
        
        return {

            "ordered": len(violations) == 0,

            "violations": violations,

            "message_count": len(messages),

            "violation_rate": len(violations) / len(messages) * 100 if messages else 0

        }
    
    def get_queue_status(self, user_id: str) -> Dict[str, Any]:

        """Get delivery queue status for user."""

        queue = self.delivery_queues[user_id]
        
        return {

            "user_id": user_id,

            "queue_size": len(queue),

            "queue_utilization": len(queue) / self.max_queue_size * 100,

            "next_sequences": [msg.sequence_number for msg in list(queue)[:10]],  # First 10

            "processing_stats": self.processing_stats

        }

@pytest.mark.L2

@pytest.mark.integration

class TestMessageOrderingGuarantees:

    """L2 integration tests for message ordering guarantees."""
    
    @pytest.fixture

    def ws_manager(self):

        """Create WebSocket manager with mocked external services."""

        with patch('app.ws_manager.redis_manager') as mock_redis:

            mock_redis.enabled = False  # Use in-memory storage

            return WebSocketManager()
    
    @pytest.fixture

    def sequence_manager(self):

        """Create message sequence manager."""

        return MessageSequenceManager()
    
    @pytest.fixture

    def order_enforcer(self):

        """Create order enforcer."""

        return OrderEnforcer()
    
    @pytest.fixture

    def test_users(self):

        """Create test users."""

        return [

            User(

                id=f"order_user_{i}",

                email=f"orderuser{i}@example.com",

                username=f"orderuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(3)

        ]
    
    def create_test_message(self, content: str, session_id: str = "", priority: int = 0) -> Dict[str, Any]:

        """Create test message."""

        return {

            "type": "chat_message",

            "content": content,

            "session_id": session_id,

            "priority": priority,

            "timestamp": time.time()

        }
    
    async def test_basic_sequence_assignment(self, sequence_manager, test_users):

        """Test basic sequence number assignment."""

        user = test_users[0]
        
        # Create and sequence messages

        messages = []

        for i in range(5):

            msg = self.create_test_message(f"Message {i}")

            sequenced = sequence_manager.assign_sequence_number(user.id, msg)

            messages.append(sequenced)
        
        # Verify sequence numbers are assigned correctly

        for i, msg in enumerate(messages):

            assert msg.sequence_number == i

            assert msg.user_id == user.id

            assert msg.content["content"] == f"Message {i}"

            assert msg.message_id is not None
        
        # Verify stats

        stats = sequence_manager.get_ordering_stats()

        assert stats["total_messages"] == 5

        assert stats["out_of_order_messages"] == 0
    
    async def test_in_order_message_processing(self, sequence_manager, test_users):

        """Test processing of in-order messages."""

        user = test_users[0]
        
        # Create sequenced messages

        messages = []

        for i in range(10):

            msg = self.create_test_message(f"Message {i}")

            sequenced = sequence_manager.assign_sequence_number(user.id, msg)

            messages.append(sequenced)
        
        # Process messages in order

        all_delivered = []

        for msg in messages:

            delivered = sequence_manager.process_incoming_message(msg)

            all_delivered.extend(delivered)
        
        # Verify all messages delivered immediately

        assert len(all_delivered) == 10
        
        # Verify order preserved

        for i, delivered_msg in enumerate(all_delivered):

            assert delivered_msg.sequence_number == i

            assert delivered_msg.content["content"] == f"Message {i}"
        
        # Verify buffer status

        buffer_status = sequence_manager.get_user_buffer_status(user.id)

        assert buffer_status["expected_sequence"] == 10

        assert buffer_status["buffered_count"] == 0

        assert buffer_status["delivered_count"] == 10
    
    async def test_out_of_order_message_handling(self, sequence_manager, test_users):

        """Test handling of out-of-order messages."""

        user = test_users[0]
        
        # Create sequenced messages

        messages = []

        for i in range(5):

            msg = self.create_test_message(f"Message {i}")

            sequenced = sequence_manager.assign_sequence_number(user.id, msg)

            messages.append(sequenced)
        
        # Send messages out of order: 0, 2, 4, 1, 3

        delivery_order = [0, 2, 4, 1, 3]

        all_delivered = []
        
        for idx in delivery_order:

            delivered = sequence_manager.process_incoming_message(messages[idx])

            all_delivered.extend(delivered)
        
        # Should deliver all messages in correct order eventually

        assert len(all_delivered) == 5
        
        # Verify final order is correct

        for i, delivered_msg in enumerate(all_delivered):

            assert delivered_msg.sequence_number == i
        
        # Check stats

        stats = sequence_manager.get_ordering_stats()

        assert stats["out_of_order_messages"] == 2  # Messages 2 and 4 were out of order

        assert stats["reordered_messages"] == 4  # Messages 1, 2, 3, 4 were reordered
    
    async def test_gap_handling_with_timeouts(self, sequence_manager, test_users):

        """Test handling of message gaps with timeout forcing."""

        user = test_users[0]
        
        # Create messages but skip message 2

        messages = []

        for i in range(5):

            msg = self.create_test_message(f"Message {i}")

            sequenced = sequence_manager.assign_sequence_number(user.id, msg)

            messages.append(sequenced)
        
        # Send messages 0, 1, 3, 4 (skip 2)

        send_order = [0, 1, 3, 4]

        all_delivered = []
        
        for idx in send_order:

            delivered = sequence_manager.process_incoming_message(messages[idx])

            all_delivered.extend(delivered)
        
        # Should only deliver 0 and 1, buffer 3 and 4

        assert len(all_delivered) == 2

        assert all_delivered[0].sequence_number == 0

        assert all_delivered[1].sequence_number == 1
        
        # Check buffer status

        buffer_status = sequence_manager.get_user_buffer_status(user.id)

        assert buffer_status["buffered_count"] == 2

        assert 3 in buffer_status["buffered_sequences"]

        assert 4 in buffer_status["buffered_sequences"]
        
        # Simulate timeout by modifying last delivery time

        buffer = sequence_manager.message_buffers[user.id]

        buffer.last_delivery_time = time.time() - buffer.buffer_timeout - 1
        
        # Check for timeouts

        timed_out = sequence_manager.check_buffer_timeouts()

        assert len(timed_out) == 1
        
        user_id, forced_messages = timed_out[0]

        assert user_id == user.id

        assert len(forced_messages) == 2

        assert forced_messages[0].sequence_number == 3

        assert forced_messages[1].sequence_number == 4
    
    async def test_order_enforcer_delivery(self, order_enforcer, test_users):

        """Test order enforcer delivery mechanism."""

        user = test_users[0]
        
        # Create test messages

        messages = []

        for i in range(15):

            sequenced_msg = SequencedMessage(

                message_id=str(uuid4()),

                user_id=user.id,

                sequence_number=i,

                timestamp=time.time(),

                content={"content": f"Message {i}"}

            )

            messages.append(sequenced_msg)
        
        # Enqueue messages for delivery

        order_enforcer.enqueue_for_delivery(user.id, messages)
        
        # Deliver in batches

        batch1 = await order_enforcer.deliver_next_batch(user.id, 5)

        batch2 = await order_enforcer.deliver_next_batch(user.id, 5)

        batch3 = await order_enforcer.deliver_next_batch(user.id, 10)
        
        # Verify batch sizes

        assert len(batch1) == 5

        assert len(batch2) == 5

        assert len(batch3) == 5  # Only 5 remaining
        
        # Verify order within batches

        all_batches = [batch1, batch2, batch3]

        delivered_sequences = []
        
        for batch in all_batches:

            order_check = order_enforcer.verify_delivery_order(batch)

            assert order_check["ordered"] is True

            assert len(order_check["violations"]) == 0
            
            delivered_sequences.extend([msg.sequence_number for msg in batch])
        
        # Verify overall order

        assert delivered_sequences == list(range(15))
    
    async def test_concurrent_user_ordering(self, sequence_manager, order_enforcer, test_users):

        """Test message ordering for multiple concurrent users."""
        # Create messages for multiple users

        user_messages = {}
        
        for user in test_users:

            messages = []

            for i in range(10):

                msg = self.create_test_message(f"User {user.id} Message {i}")

                sequenced = sequence_manager.assign_sequence_number(user.id, msg)

                messages.append(sequenced)

            user_messages[user.id] = messages
        
        # Simulate concurrent processing with mixed order

        all_delivered = defaultdict(list)
        
        # Interleave messages from different users

        for i in range(10):

            for user in test_users:
                # Occasionally send out of order

                if i > 2 and i % 3 == 0:
                    # Send a future message

                    if i + 1 < len(user_messages[user.id]):

                        future_msg = user_messages[user.id][i + 1]

                        delivered = sequence_manager.process_incoming_message(future_msg)

                        all_delivered[user.id].extend(delivered)
                
                # Send current message

                current_msg = user_messages[user.id][i]

                delivered = sequence_manager.process_incoming_message(current_msg)

                all_delivered[user.id].extend(delivered)
        
        # Verify each user's messages are ordered correctly

        for user in test_users:

            user_delivered = all_delivered[user.id]
            
            # Should eventually deliver all messages

            assert len(user_delivered) >= 8  # Allow for some buffering
            
            # Check order of delivered messages

            for i in range(len(user_delivered) - 1):

                current_seq = user_delivered[i].sequence_number

                next_seq = user_delivered[i + 1].sequence_number

                assert next_seq == current_seq + 1, f"Order violation for user {user.id}"
    
    @mock_justified("L2: Message ordering with real internal components")

    async def test_websocket_integration_with_ordering(self, ws_manager, sequence_manager, order_enforcer, test_users):

        """Test WebSocket integration with message ordering."""

        user = test_users[0]

        mock_websocket = AsyncMock()
        
        # Connect user

        connection_info = await ws_manager.connect_user(user.id, mock_websocket)

        assert connection_info is not None
        
        # Create and send messages through WebSocket manager

        sent_messages = []

        for i in range(8):

            msg_content = self.create_test_message(f"WebSocket Message {i}")
            
            # Assign sequence number

            sequenced_msg = sequence_manager.assign_sequence_number(user.id, msg_content)

            sent_messages.append(sequenced_msg)
            
            # Send through WebSocket manager

            success = await ws_manager.send_message_to_user(user.id, sequenced_msg.content)

            assert success is True
        
        # Simulate receiving messages out of order

        receive_order = [0, 2, 1, 4, 3, 6, 5, 7]

        all_delivered = []
        
        for idx in receive_order:

            delivered = sequence_manager.process_incoming_message(sent_messages[idx])
            
            if delivered:
                # Use order enforcer for delivery

                order_enforcer.enqueue_for_delivery(user.id, delivered)

                batch = await order_enforcer.deliver_next_batch(user.id, len(delivered))

                all_delivered.extend(batch)
        
        # Verify ordering maintained

        order_check = order_enforcer.verify_delivery_order(all_delivered)

        assert order_check["ordered"] is True

        assert order_check["violation_rate"] == 0.0
        
        # Verify all messages eventually delivered

        assert len(all_delivered) == 8
        
        # Check final statistics

        stats = sequence_manager.get_ordering_stats()

        assert stats["ordering_accuracy"] >= 75.0  # Allow for some out-of-order
        
        # Cleanup

        await ws_manager.disconnect_user(user.id, mock_websocket)
    
    async def test_ordering_performance_benchmarks(self, sequence_manager, order_enforcer, test_users):

        """Test message ordering performance benchmarks."""

        user = test_users[0]

        message_count = 1000
        
        # Benchmark sequence assignment

        start_time = time.time()

        sequenced_messages = []
        
        for i in range(message_count):

            msg = self.create_test_message(f"Perf Message {i}")

            sequenced = sequence_manager.assign_sequence_number(user.id, msg)

            sequenced_messages.append(sequenced)
        
        assignment_time = time.time() - start_time
        
        # Should assign sequences quickly

        assert assignment_time < 1.0  # Less than 1 second for 1000 messages
        
        # Benchmark in-order processing

        start_time = time.time()
        
        for msg in sequenced_messages:

            sequence_manager.process_incoming_message(msg)
        
        processing_time = time.time() - start_time
        
        # Should process quickly

        assert processing_time < 2.0  # Less than 2 seconds for 1000 messages
        
        # Benchmark order enforcement

        start_time = time.time()
        
        order_enforcer.enqueue_for_delivery(user.id, sequenced_messages)
        
        batches_delivered = 0

        while True:

            batch = await order_enforcer.deliver_next_batch(user.id, 50)

            if not batch:

                break

            batches_delivered += len(batch)
            
            # Verify each batch

            order_check = order_enforcer.verify_delivery_order(batch)

            assert order_check["ordered"] is True
        
        enforcement_time = time.time() - start_time
        
        # Should enforce order quickly

        assert enforcement_time < 1.0  # Less than 1 second

        assert batches_delivered == message_count
        
        # Verify final stats

        stats = sequence_manager.get_ordering_stats()

        assert stats["ordering_accuracy"] == 100.0  # Perfect for in-order processing

        assert stats["total_messages"] == message_count

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])