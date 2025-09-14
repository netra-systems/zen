"""
WebSocket Message Queue SSOT Violations Reproduction Tests

PURPOSE: Create FAILING tests that demonstrate the current 3-implementation problem
BUSINESS VALUE:
- Segment: Platform/Internal
- Goal: Stability & Architecture Compliance
- Impact: Prevents message loss, race conditions, and duplicate delivery issues
- Strategic Impact: Foundation for $500K+ ARR Golden Path reliability

MISSION CRITICAL: Issue #1011 - SSOT WebSocket Message Queue Consolidation Tests
These tests MUST FAIL initially to prove the current SSOT violations exist.
Once SSOT consolidation is complete, these tests will validate the resolution.

Current 3 implementations causing violations:
1. netra_backend.app.services.websocket.message_queue (Redis-based)
2. netra_backend.app.websocket_core.message_queue (ConnectionState-based)
3. netra_backend.app.websocket_core.message_buffer (Buffer-based)

Expected Test State: FAILING (demonstrates violations)
Expected Fix State: PASSING (after SSOT consolidation)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SsotAsyncTestCase
from shared.types.core_types import UserID, ConnectionID
from netra_backend.app.logging_config import central_logger

# Import all 3 message queue implementations to test violations
from netra_backend.app.services.websocket.message_queue import (
    MessageQueue as RedisMessageQueue,
    QueuedMessage as RedisQueuedMessage,
    MessagePriority as RedisMessagePriority,
    MessageStatus as RedisMessageStatus
)
from netra_backend.app.websocket_core.message_queue import (
    MessageQueue as ConnectionStateMessageQueue,
    QueuedMessage as ConnectionStateQueuedMessage,
    MessagePriority as ConnectionStateMessagePriority,
    MessageQueueState as ConnectionStateQueueState
)
from netra_backend.app.websocket_core.message_buffer import (
    WebSocketMessageBuffer,
    BufferedMessage,
    BufferPriority,
    BufferConfig
)

logger = central_logger.get_logger(__name__)


class TestWebSocketMessageQueueSsotViolations(SsotAsyncTestCase):
    """
    Test suite to reproduce and validate SSOT violations in message queue implementations.

    CRITICAL: These tests MUST FAIL initially to demonstrate violations.
    Success criteria: All tests fail, proving SSOT violations exist.
    """

    def setup_method(self, method):
        """Set up test environment for SSOT violation testing."""
        super().setup_method(method)
        self.user_id = UserID("test_user_123")
        self.connection_id = ConnectionID("conn_123")

        # Test message data
        self.test_message = {
            "type": "agent_thinking",
            "message": "Processing your request...",
            "user_id": str(self.user_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Initialize all 3 message queue implementations
        self.redis_queue = None
        self.connection_state_queue = None
        self.message_buffer = None

    async def _initialize_queues(self):
        """Initialize all message queue implementations for comparison."""
        # Redis-based message queue
        self.redis_queue = RedisMessageQueue()

        # Connection state message queue
        self.connection_state_queue = ConnectionStateMessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=100
        )

        # Message buffer
        self.message_buffer = WebSocketMessageBuffer(BufferConfig())
        await self.message_buffer.start()

    async def teardown_method(self, method):
        """Clean up test environment."""
        if self.message_buffer:
            await self.message_buffer.stop()

        if self.redis_queue:
            await self.redis_queue.stop_processing()

        if self.connection_state_queue:
            await self.connection_state_queue.close()

        await super().teardown_method(method)

    async def test_redis_message_queue_behavior_baseline(self):
        """Test Redis message queue behavior as baseline reference."""
        await self._initialize_queues()

        # Create Redis queued message
        redis_message = RedisQueuedMessage(
            user_id=str(self.user_id),
            type=self.test_message["type"],
            payload=self.test_message,
            priority=RedisMessagePriority.HIGH
        )

        # Test Redis queue operations
        enqueue_success = await self.redis_queue.enqueue(redis_message)
        assert enqueue_success, "Redis message queue should accept messages"

        # Get queue statistics
        stats = await self.redis_queue.get_queue_stats()
        assert stats["total_pending"] >= 0, "Redis queue should track pending messages"

        # Record baseline behavior for comparison
        self.record_custom_metric("redis_queue_pending", stats["total_pending"])
        self.record_custom_metric("redis_message_id", redis_message.id)

        logger.info(f"Redis queue baseline: {stats}")

    async def test_connection_state_message_queue_behavior_baseline(self):
        """Test ConnectionState message queue behavior as baseline reference."""
        await self._initialize_queues()

        # Test connection state queue operations
        enqueue_success = await self.connection_state_queue.enqueue_message(
            message_data=self.test_message,
            message_type=self.test_message["type"],
            priority=ConnectionStateMessagePriority.HIGH,
            message_id=str(uuid.uuid4())
        )
        assert enqueue_success, "ConnectionState message queue should accept messages"

        # Get queue statistics
        stats = self.connection_state_queue.get_queue_stats()
        assert stats["total_size"] >= 0, "ConnectionState queue should track message count"

        # Record baseline behavior for comparison
        self.record_custom_metric("connection_state_queue_size", stats["total_size"])
        self.record_custom_metric("connection_state_queue_state", stats["state"])

        logger.info(f"ConnectionState queue baseline: {stats}")

    async def test_message_buffer_behavior_baseline(self):
        """Test WebSocket message buffer behavior as baseline reference."""
        await self._initialize_queues()

        # Test message buffer operations
        buffer_success = await self.message_buffer.buffer_message(
            user_id=str(self.user_id),
            message=self.test_message,
            priority=BufferPriority.HIGH
        )
        assert buffer_success, "Message buffer should accept messages"

        # Get buffer statistics
        stats = self.message_buffer.get_buffer_stats()
        assert stats["total_buffered_messages"] >= 0, "Message buffer should track buffered count"

        # Record baseline behavior for comparison
        self.record_custom_metric("buffer_total_messages", stats["total_buffered_messages"])
        self.record_custom_metric("buffer_size_bytes", stats["buffer_size_bytes"])

        logger.info(f"Message buffer baseline: {stats}")

    async def test_ssot_violation_reproduction_three_implementations(self):
        """
        CRITICAL: Reproduce SSOT violation by demonstrating 3 separate implementations.
        This test MUST FAIL to prove violations exist.
        """
        await self._initialize_queues()

        # Prove 3 different implementations exist by checking class types
        redis_queue_type = type(self.redis_queue).__name__
        connection_state_queue_type = type(self.connection_state_queue).__name__
        buffer_type = type(self.message_buffer).__name__

        # Record the violation evidence
        implementation_types = [redis_queue_type, connection_state_queue_type, buffer_type]
        unique_implementations = set(implementation_types)

        self.record_custom_metric("total_implementations", len(implementation_types))
        self.record_custom_metric("unique_implementations", len(unique_implementations))
        self.record_custom_metric("implementation_types", list(unique_implementations))

        logger.error(f"SSOT VIOLATION: Found {len(unique_implementations)} different message queue implementations")
        logger.error(f"Implementations: {list(unique_implementations)}")

        # This assertion MUST FAIL to demonstrate SSOT violation
        assert len(unique_implementations) == 1, \
            f"SSOT VIOLATION: Expected 1 message queue implementation, found {len(unique_implementations)}: {list(unique_implementations)}"

    async def test_race_condition_between_queue_implementations(self):
        """
        Test race conditions that occur between different queue implementations.
        This test MUST FAIL to demonstrate the race condition problem.
        """
        await self._initialize_queues()

        # Simulate concurrent message handling across all 3 implementations
        message_ids = []

        # Send same message to all 3 queues simultaneously
        tasks = []

        # Redis queue task
        redis_message = RedisQueuedMessage(
            user_id=str(self.user_id),
            type="test_race_condition",
            payload={"message": "race condition test", "queue": "redis"},
            priority=RedisMessagePriority.HIGH
        )
        tasks.append(self.redis_queue.enqueue(redis_message))
        message_ids.append(redis_message.id)

        # ConnectionState queue task
        connection_message_id = str(uuid.uuid4())
        tasks.append(self.connection_state_queue.enqueue_message(
            message_data={"message": "race condition test", "queue": "connection_state"},
            message_type="test_race_condition",
            priority=ConnectionStateMessagePriority.HIGH,
            message_id=connection_message_id
        ))
        message_ids.append(connection_message_id)

        # Buffer task
        tasks.append(self.message_buffer.buffer_message(
            user_id=str(self.user_id),
            message={"message": "race condition test", "queue": "buffer"},
            priority=BufferPriority.HIGH
        ))
        message_ids.append(f"buffer_message_{int(datetime.now().timestamp())}")

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful enqueues
        successful_enqueues = sum(1 for result in results if result is True)

        self.record_custom_metric("race_condition_attempts", len(tasks))
        self.record_custom_metric("successful_enqueues", successful_enqueues)
        self.record_custom_metric("message_ids", message_ids)

        logger.warning(f"Race condition test: {successful_enqueues}/{len(tasks)} queues accepted the message")

        # This assertion MUST FAIL to demonstrate race condition
        # In proper SSOT implementation, there should be only 1 queue handling the message
        assert successful_enqueues <= 1, \
            f"RACE CONDITION VIOLATION: Message processed by {successful_enqueues} different queues, expected max 1"

    async def test_message_loss_due_to_multiple_queues(self):
        """
        Test message loss scenarios caused by having multiple queue implementations.
        This test MUST FAIL to demonstrate message loss potential.
        """
        await self._initialize_queues()

        # Send messages to different queues and check for consistency
        original_message_count = 5
        messages_sent = []

        # Send messages to all queues
        for i in range(original_message_count):
            message_data = {
                "id": f"msg_{i}",
                "content": f"Test message {i}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            messages_sent.append(message_data)

            # Send to Redis queue
            redis_msg = RedisQueuedMessage(
                user_id=str(self.user_id),
                type="message_loss_test",
                payload=message_data,
                priority=RedisMessagePriority.NORMAL
            )
            await self.redis_queue.enqueue(redis_msg)

            # Send to ConnectionState queue
            await self.connection_state_queue.enqueue_message(
                message_data=message_data,
                message_type="message_loss_test",
                priority=ConnectionStateMessagePriority.NORMAL
            )

            # Send to Buffer
            await self.message_buffer.buffer_message(
                user_id=str(self.user_id),
                message=message_data,
                priority=BufferPriority.NORMAL
            )

        # Check message counts in each queue
        redis_stats = await self.redis_queue.get_queue_stats()
        connection_stats = self.connection_state_queue.get_queue_stats()
        buffer_stats = self.message_buffer.get_buffer_stats()

        redis_pending = redis_stats.get("total_pending", 0)
        connection_pending = connection_stats.get("total_size", 0)
        buffer_pending = buffer_stats.get("total_buffered_messages", 0)

        total_messages_queued = redis_pending + connection_pending + buffer_pending

        self.record_custom_metric("original_message_count", original_message_count)
        self.record_custom_metric("redis_pending", redis_pending)
        self.record_custom_metric("connection_pending", connection_pending)
        self.record_custom_metric("buffer_pending", buffer_pending)
        self.record_custom_metric("total_messages_queued", total_messages_queued)

        logger.error(f"MESSAGE LOSS TEST: Original={original_message_count}, Queued={total_messages_queued}")

        # This assertion MUST FAIL to demonstrate message duplication/loss potential
        # With 3 separate queues, we have 3x duplication instead of proper SSOT
        assert total_messages_queued == original_message_count, \
            f"MESSAGE CONSISTENCY VIOLATION: Expected {original_message_count} messages, found {total_messages_queued} across all queues"

    async def test_duplicate_delivery_across_queue_systems(self):
        """
        Test duplicate message delivery potential across different queue systems.
        This test MUST FAIL to demonstrate duplicate delivery risk.
        """
        await self._initialize_queues()

        # Track delivery attempts across all systems
        delivered_messages = []

        # Mock delivery function to track calls
        async def mock_delivery_handler(message_data):
            delivered_messages.append({
                "message_data": message_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "handler": "mock_delivery"
            })
            return True

        # Set up message processors for all queues
        self.connection_state_queue.set_message_processor(
            lambda msg: mock_delivery_handler(msg.message_data)
        )

        # Register handler for Redis queue
        self.redis_queue.register_handler("duplicate_test", mock_delivery_handler)

        # Send same logical message to all queues
        test_message_data = {
            "logical_id": "unique_message_001",
            "content": "This message should be delivered only once",
            "type": "duplicate_test"
        }

        # Enqueue to Redis
        redis_msg = RedisQueuedMessage(
            user_id=str(self.user_id),
            type="duplicate_test",
            payload=test_message_data,
            priority=RedisMessagePriority.NORMAL
        )
        await self.redis_queue.enqueue(redis_msg)

        # Enqueue to ConnectionState queue
        await self.connection_state_queue.enqueue_message(
            message_data=test_message_data,
            message_type="duplicate_test",
            priority=ConnectionStateMessagePriority.NORMAL
        )

        # Buffer message
        await self.message_buffer.buffer_message(
            user_id=str(self.user_id),
            message=test_message_data,
            priority=BufferPriority.NORMAL
        )

        # Simulate delivery from ConnectionState queue (the one with processor)
        await self.connection_state_queue.flush_queue()

        # Simulate delivery from buffer
        await self.message_buffer.deliver_buffered_messages(
            str(self.user_id),
            mock_delivery_handler
        )

        # Simulate Redis queue processing (would require worker setup)
        # For test purposes, manually call delivery
        await mock_delivery_handler(test_message_data)

        # Check for duplicate deliveries
        unique_logical_ids = set()
        for delivery in delivered_messages:
            if isinstance(delivery["message_data"], dict):
                logical_id = delivery["message_data"].get("logical_id")
                if logical_id:
                    unique_logical_ids.add(logical_id)

        total_deliveries = len(delivered_messages)
        unique_deliveries = len(unique_logical_ids)

        self.record_custom_metric("total_deliveries", total_deliveries)
        self.record_custom_metric("unique_deliveries", unique_deliveries)
        self.record_custom_metric("delivered_messages", delivered_messages)

        logger.error(f"DUPLICATE DELIVERY TEST: {total_deliveries} total deliveries, {unique_deliveries} unique messages")

        # This assertion MUST FAIL to demonstrate duplicate delivery potential
        assert total_deliveries == unique_deliveries, \
            f"DUPLICATE DELIVERY VIOLATION: {total_deliveries} deliveries for {unique_deliveries} unique messages"


if __name__ == "__main__":
    # Run tests with verbose output to see violations
    pytest.main([__file__, "-v", "-s", "--tb=short"])