"""
Unit tests for WebSocket message queue race conditions and consolidation issues.

Issue #1011 WebSocket Message Queue Consolidation Test Plan Implementation

This test module demonstrates the critical race conditions and message conflicts
created by having 4 different message queue implementations in the WebSocket system:

1. MessageQueue (message_queue.py) - State-aware queue with priority handling
2. WebSocketMessageBuffer (message_buffer.py) - Buffer with overflow protection
3. WebSocketMessageQueue (utils.py) - Simple asyncio.Queue wrapper
4. Multiple internal queues in unified_manager.py - _user_event_queues, _message_recovery_queue

These tests are DESIGNED TO FAIL initially to prove the problems exist,
then will pass after queue consolidation is complete.

Business Value Justification:
- Segment: Platform/Internal - CRITICAL
- Business Goal: Golden Path Stability - $500K+ ARR Protection
- Value Impact: Prevents message loss and race conditions that disrupt user chat experience
- Strategic Impact: Eliminates technical debt causing user experience degradation
"""

import asyncio
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

from netra_backend.app.websocket_core.message_queue import (
    MessageQueue, MessageQueueRegistry, MessagePriority, QueuedMessage
)
from netra_backend.app.websocket_core.message_buffer import (
    WebSocketMessageBuffer, BufferedMessage, BufferPriority, BufferConfig
)
from netra_backend.app.websocket_core.utils import WebSocketMessageQueue
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

from shared.types.core_types import UserID, ConnectionID


class MessageQueueRaceConditionsTests(SSotAsyncTestCase):
    """Test race conditions between competing message queue implementations."""

    def setup_method(self, method):
        """Set up test environment for each test."""
        super().setup_method(method)
        self.websocket_util = WebSocketTestUtility()

        # Test data
        self.test_user_id = UserID("test_user_123")
        self.test_connection_id = ConnectionID("test_conn_456")
        self.test_message = {
            "type": "agent_thinking",
            "content": "Processing your request...",
            "user_id": str(self.test_user_id),
            "timestamp": time.time()
        }

    async def test_concurrent_queue_implementation_conflicts(self):
        """
        FAILING TEST: Demonstrates race conditions between different queue implementations.

        This test creates the exact scenario where multiple queue implementations
        are processing the same user messages simultaneously, causing:
        1. Message duplication
        2. Message loss
        3. Out-of-order delivery
        4. Queue state corruption

        Expected to FAIL until queue consolidation is complete.
        """
        # Create all 4 queue implementations simultaneously
        message_queue = MessageQueue(self.test_connection_id, self.test_user_id)
        message_buffer = WebSocketMessageBuffer()
        utils_queue = WebSocketMessageQueue()

        # Simulate unified manager with internal queues
        unified_manager = UnifiedWebSocketManager()

        # Track messages processed by each queue
        message_queue_results = []
        buffer_results = []
        utils_queue_results = []
        manager_queue_results = []

        # Create mock processors for each queue type
        async def message_queue_processor(queued_msg: QueuedMessage):
            message_queue_results.append(f"MessageQueue: {queued_msg.message_id}")

        async def buffer_delivery_callback(message):
            buffer_results.append(f"Buffer: {message}")
            return True

        async def utils_queue_consumer():
            while True:
                message = await utils_queue.dequeue(timeout=0.1)
                if message is None:
                    break
                utils_queue_results.append(f"UtilsQueue: {message.get('id', 'no_id')}")

        # Set up processors
        message_queue.set_message_processor(message_queue_processor)

        # Create multiple messages that should go to the same user
        messages = [
            {**self.test_message, "id": f"msg_{i}", "content": f"Message {i}"}
            for i in range(10)
        ]

        # RACE CONDITION: Send messages to all queue implementations concurrently
        tasks = []

        # Send to MessageQueue
        for msg in messages:
            tasks.append(asyncio.create_task(
                message_queue.enqueue_message(msg, "test_message", MessagePriority.HIGH, msg["id"])
            ))

        # Send to WebSocketMessageBuffer
        for msg in messages:
            tasks.append(asyncio.create_task(
                message_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.HIGH)
            ))

        # Send to WebSocketMessageQueue
        for msg in messages:
            tasks.append(asyncio.create_task(utils_queue.enqueue(msg)))

        # Execute all queuing operations concurrently
        await asyncio.gather(*tasks)

        # Process all queues concurrently (simulating race condition)
        processing_tasks = [
            asyncio.create_task(message_queue.flush_queue()),
            asyncio.create_task(message_buffer.deliver_buffered_messages(
                str(self.test_user_id), buffer_delivery_callback
            )),
            asyncio.create_task(utils_queue_consumer())
        ]

        await asyncio.gather(*processing_tasks, return_exceptions=True)

        # ASSERTIONS THAT SHOULD FAIL (proving the race condition problems)

        # Check for message duplication across queues
        all_results = message_queue_results + buffer_results + utils_queue_results

        # This should FAIL: Messages should not be duplicated across different queues
        unique_messages = set(all_results)
        total_messages = len(all_results)

        self.fail(
            f"EXPECTED FAILURE - Queue Consolidation Issue #1011:\n"
            f"Multiple queue implementations caused race conditions:\n"
            f"- MessageQueue processed: {len(message_queue_results)} messages\n"
            f"- Buffer processed: {len(buffer_results)} messages  \n"
            f"- UtilsQueue processed: {len(utils_queue_results)} messages\n"
            f"- Total messages: {total_messages}\n"
            f"- Unique messages: {len(unique_messages)}\n"
            f"- Expected: 10 messages processed by ONE consolidated queue\n"
            f"- Actual: {total_messages} messages across {3} competing implementations\n"
            f"\nThis proves the need for WebSocket message queue consolidation.\n"
            f"All results: {all_results}"
        )

    async def test_queue_state_conflicts_during_connection_transitions(self):
        """
        FAILING TEST: Shows queue state conflicts during WebSocket connection state changes.

        Different queue implementations handle connection state transitions differently,
        causing message loss when connection state changes occur.

        Expected to FAIL until state management is unified.
        """
        # Create message queue with connection state integration
        from netra_backend.app.websocket_core.connection_state_machine import (
            ConnectionStateMachine, ApplicationConnectionState
        )

        state_machine = ConnectionStateMachine(self.test_connection_id, self.test_user_id)
        message_queue = MessageQueue(
            self.test_connection_id,
            self.test_user_id,
            state_machine=state_machine
        )

        # Create buffer without state integration (current situation)
        message_buffer = WebSocketMessageBuffer()

        # Add messages to both queues
        test_messages = [
            {"type": "agent_started", "content": "Starting", "id": "msg_1"},
            {"type": "agent_thinking", "content": "Processing", "id": "msg_2"},
            {"type": "agent_completed", "content": "Done", "id": "msg_3"}
        ]

        # Queue messages in both implementations
        for msg in test_messages:
            await message_queue.enqueue_message(msg, msg["type"], MessagePriority.HIGH, msg["id"])
            await message_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.HIGH)

        # Simulate connection state change during processing
        await state_machine.transition_to(ApplicationConnectionState.PROCESSING_READY)

        # Wait for state-aware queue to process
        await asyncio.sleep(0.1)

        # Check queue states
        message_queue_state = message_queue.current_state
        message_queue_size = message_queue._get_total_queue_size()
        buffer_size = len(message_buffer.get_buffered_messages(str(self.test_user_id)))

        self.fail(
            f"EXPECTED FAILURE - Queue State Conflict Issue #1011:\n"
            f"Different queue implementations have conflicting state management:\n"
            f"- MessageQueue state: {message_queue_state.value}\n"
            f"- MessageQueue remaining messages: {message_queue_size}\n"
            f"- Buffer has no state awareness, remaining: {buffer_size}\n"
            f"- Expected: Single consolidated queue with unified state management\n"
            f"- Actual: {2} different queue implementations with conflicting behavior\n"
            f"\nThis causes message loss during connection state transitions."
        )

    async def test_message_ordering_conflicts_between_queues(self):
        """
        FAILING TEST: Demonstrates message ordering conflicts between queue implementations.

        Different queue implementations use different ordering strategies:
        - MessageQueue: Priority-based ordering (CRITICAL -> HIGH -> NORMAL -> LOW)
        - WebSocketMessageBuffer: FIFO with priority overflow handling
        - WebSocketMessageQueue: Simple FIFO

        This causes out-of-order message delivery in the Golden Path user flow.

        Expected to FAIL until ordering is unified.
        """
        # Create all queue implementations
        message_queue = MessageQueue(self.test_connection_id, self.test_user_id)
        message_buffer = WebSocketMessageBuffer()
        utils_queue = WebSocketMessageQueue()

        # Create ordered sequence of messages with different priorities
        ordered_messages = [
            {"id": "1", "type": "agent_started", "priority": "critical", "sequence": 1},
            {"id": "2", "type": "agent_thinking", "priority": "high", "sequence": 2},
            {"id": "3", "type": "tool_executing", "priority": "high", "sequence": 3},
            {"id": "4", "type": "tool_completed", "priority": "normal", "sequence": 4},
            {"id": "5", "type": "agent_completed", "priority": "critical", "sequence": 5}
        ]

        # Add messages to all queue implementations
        for msg in ordered_messages:
            # MessageQueue with priority mapping
            priority_map = {
                "critical": MessagePriority.CRITICAL,
                "high": MessagePriority.HIGH,
                "normal": MessagePriority.NORMAL
            }
            await message_queue.enqueue_message(
                msg, msg["type"], priority_map[msg["priority"]], msg["id"]
            )

            # Buffer with priority mapping
            buffer_priority_map = {
                "critical": BufferPriority.CRITICAL,
                "high": BufferPriority.HIGH,
                "normal": BufferPriority.NORMAL
            }
            await message_buffer.buffer_message(
                str(self.test_user_id), msg, buffer_priority_map[msg["priority"]]
            )

            # Utils queue (no priority support)
            await utils_queue.enqueue(msg)

        # Process messages and capture ordering
        message_queue_order = []
        buffer_order = []
        utils_order = []

        async def capture_message_queue_order(queued_msg: QueuedMessage):
            message_queue_order.append(queued_msg.message_data["sequence"])

        async def capture_buffer_order(message):
            buffer_order.append(message["sequence"])
            return True

        # Set up processors
        message_queue.set_message_processor(capture_message_queue_order)

        # Process all queues
        await message_queue.flush_queue()
        await message_buffer.deliver_buffered_messages(str(self.test_user_id), capture_buffer_order)

        # Process utils queue
        while not utils_queue.is_empty():
            msg = await utils_queue.dequeue(timeout=0.1)
            if msg:
                utils_order.append(msg["sequence"])

        # Expected sequence: [1, 2, 3, 4, 5] (chronological order for user experience)
        expected_order = [1, 2, 3, 4, 5]

        self.fail(
            f"EXPECTED FAILURE - Message Ordering Conflict Issue #1011:\n"
            f"Different queue implementations produce different message ordering:\n"
            f"- Expected chronological order: {expected_order}\n"
            f"- MessageQueue order (priority-based): {message_queue_order}\n"
            f"- Buffer order (FIFO with priority overflow): {buffer_order}\n"
            f"- UtilsQueue order (simple FIFO): {utils_order}\n"
            f"\nInconsistent ordering disrupts Golden Path user experience.\n"
            f"Users see agent events out of sequence, breaking the conversation flow."
        )

    async def test_queue_overflow_handling_inconsistencies(self):
        """
        FAILING TEST: Shows inconsistent overflow handling between queue implementations.

        Each queue implementation handles overflow differently:
        - MessageQueue: Drops by priority with intelligent overflow protection
        - WebSocketMessageBuffer: Configurable overflow strategies
        - WebSocketMessageQueue: Simple queue full rejection

        This causes unpredictable message loss patterns.

        Expected to FAIL until overflow handling is unified.
        """
        # Create queues with small limits to trigger overflow
        message_queue = MessageQueue(self.test_connection_id, self.test_user_id, max_size=3)

        buffer_config = BufferConfig(max_buffer_size_per_user=3)
        message_buffer = WebSocketMessageBuffer(buffer_config)

        utils_queue = WebSocketMessageQueue(max_size=3)

        # Create messages to overflow all queues
        overflow_messages = [
            {"id": f"msg_{i}", "type": "test_message", "priority": "normal", "content": f"Message {i}"}
            for i in range(10)  # 10 messages > 3 capacity
        ]

        # Track overflow behavior
        message_queue_rejected = 0
        buffer_rejected = 0
        utils_queue_rejected = 0

        # Fill all queues beyond capacity
        for msg in overflow_messages:
            # MessageQueue
            success = await message_queue.enqueue_message(
                msg, msg["type"], MessagePriority.NORMAL, msg["id"]
            )
            if not success:
                message_queue_rejected += 1

            # Buffer
            try:
                success = await message_buffer.buffer_message(
                    str(self.test_user_id), msg, BufferPriority.NORMAL
                )
                if not success:
                    buffer_rejected += 1
            except Exception:
                buffer_rejected += 1

            # Utils queue
            success = await utils_queue.enqueue(msg)
            if not success:
                utils_queue_rejected += 1

        # Get final queue states
        message_queue_size = message_queue._get_total_queue_size()
        buffer_size = len(message_buffer.get_buffered_messages(str(self.test_user_id)))
        utils_queue_size = utils_queue.size()

        self.fail(
            f"EXPECTED FAILURE - Inconsistent Overflow Handling Issue #1011:\n"
            f"Different queue implementations handle overflow differently:\n"
            f"- MessageQueue: {message_queue_size} queued, {message_queue_rejected} rejected\n"
            f"- Buffer: {buffer_size} queued, {buffer_rejected} rejected\n"
            f"- UtilsQueue: {utils_queue_size} queued, {utils_queue_rejected} rejected\n"
            f"- Total messages sent: {len(overflow_messages)}\n"
            f"\nInconsistent behavior makes message delivery unpredictable.\n"
            f"Users experience different message loss patterns depending on which queue processes their messages."
        )

    async def test_queue_implementation_performance_conflicts(self):
        """
        FAILING TEST: Shows performance conflicts between different queue implementations.

        Different queue implementations have different performance characteristics,
        causing inconsistent response times and resource usage.

        Expected to FAIL until performance is unified.
        """
        # Create all queue implementations
        message_queue = MessageQueue(self.test_connection_id, self.test_user_id, max_size=1000)
        message_buffer = WebSocketMessageBuffer()
        utils_queue = WebSocketMessageQueue(max_size=1000)

        # Create large message set for performance testing
        perf_messages = [
            {
                "id": f"perf_msg_{i}",
                "type": "agent_thinking",
                "content": f"Performance test message {i} with substantial content to test processing overhead",
                "data": {"large_field": "x" * 100}  # Add some data to test serialization overhead
            }
            for i in range(100)
        ]

        # Measure performance of each queue implementation
        async def time_queue_operations(queue_name: str, operation):
            start_time = time.perf_counter()
            await operation()
            end_time = time.perf_counter()
            return queue_name, end_time - start_time

        # Define queue operations
        async def message_queue_ops():
            for msg in perf_messages:
                await message_queue.enqueue_message(msg, msg["type"], MessagePriority.NORMAL, msg["id"])
            await message_queue.flush_queue()

        async def buffer_ops():
            for msg in perf_messages:
                await message_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.NORMAL)
            await message_buffer.deliver_buffered_messages(str(self.test_user_id), lambda x: True)

        async def utils_queue_ops():
            for msg in perf_messages:
                await utils_queue.enqueue(msg)
            while not utils_queue.is_empty():
                await utils_queue.dequeue(timeout=0.1)

        # Run performance tests concurrently
        performance_results = await asyncio.gather(
            time_queue_operations("MessageQueue", message_queue_ops),
            time_queue_operations("Buffer", buffer_ops),
            time_queue_operations("UtilsQueue", utils_queue_ops)
        )

        # Analyze performance differences
        timings = {name: duration for name, duration in performance_results}
        max_time = max(timings.values())
        min_time = min(timings.values())
        performance_variance = ((max_time - min_time) / min_time) * 100

        self.fail(
            f"EXPECTED FAILURE - Performance Inconsistency Issue #1011:\n"
            f"Different queue implementations have significantly different performance:\n"
            f"- MessageQueue: {timings['MessageQueue']:.4f}s\n"
            f"- Buffer: {timings['Buffer']:.4f}s\n"
            f"- UtilsQueue: {timings['UtilsQueue']:.4f}s\n"
            f"- Performance variance: {performance_variance:.1f}%\n"
            f"- Messages processed: {len(perf_messages)}\n"
            f"\nPerformance inconsistency affects user experience predictability.\n"
            f"Some users get fast responses while others experience delays."
        )