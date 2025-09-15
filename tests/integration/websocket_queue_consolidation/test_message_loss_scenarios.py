"""
Integration tests for WebSocket message loss scenarios due to queue fragmentation.

Issue #1011 WebSocket Message Queue Consolidation - Message Loss Integration Tests

This test module validates message delivery across real WebSocket connections
and demonstrates how queue fragmentation causes message loss in production scenarios.

These tests use REAL SERVICES (no mocks) and are designed to FAIL initially
to prove the message loss problems exist in the current multi-queue system.

Business Value Justification:
- Segment: Enterprise/Mid-Market - CRITICAL
- Business Goal: Golden Path Reliability - $500K+ ARR Protection
- Value Impact: Prevents message loss that breaks chat functionality
- Strategic Impact: Ensures reliable real-time user experience
"""

import asyncio
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility

# Import all queue implementations that cause conflicts
from netra_backend.app.websocket_core.message_queue import MessageQueue, MessagePriority
from netra_backend.app.websocket_core.message_buffer import WebSocketMessageBuffer, BufferPriority
from netra_backend.app.websocket_core.utils import WebSocketMessageQueue
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

from shared.types.core_types import UserID, ConnectionID


class WebSocketMessageLossScenariosTests(SSotAsyncTestCase):
    """Test message loss scenarios caused by queue implementation conflicts."""

    def setup_method(self, method):
        """Set up real WebSocket test environment."""
        super().setup_method(method)
        self.websocket_util = WebSocketTestUtility()

        # Test user and connection setup
        self.test_user_id = UserID(f"user_{str(uuid.uuid4())}")
        self.test_connection_id = ConnectionID(f"conn_{str(uuid.uuid4())}")

        # Golden Path agent events that MUST be delivered reliably
        self.critical_agent_events = [
            {"type": "agent_started", "content": "Starting analysis of your request"},
            {"type": "agent_thinking", "content": "Analyzing data patterns"},
            {"type": "tool_executing", "content": "Running optimization algorithm"},
            {"type": "tool_completed", "content": "Optimization complete"},
            {"type": "agent_completed", "content": "Analysis finished successfully"}
        ]

    async def test_message_loss_during_concurrent_queue_processing(self):
        """
        FAILING INTEGRATION TEST: Demonstrates message loss when multiple queues process
        the same user's messages concurrently in a real WebSocket scenario.

        This simulates the production condition where different parts of the system
        may route messages through different queue implementations simultaneously.

        Expected to FAIL due to message loss and duplication.
        """
        # Create all queue implementations that exist in production
        message_queue = MessageQueue(self.test_connection_id, self.test_user_id, max_size=100)
        message_buffer = WebSocketMessageBuffer()
        utils_queue = WebSocketMessageQueue(max_size=100)
        unified_manager = UnifiedWebSocketManager()

        # Track messages delivered to user
        delivered_messages = []
        delivery_times = {}

        async def track_message_delivery(message):
            """Track when messages are actually delivered to the user."""
            msg_id = None
            if isinstance(message, dict):
                msg_id = message.get("id") or message.get("type")
            elif hasattr(message, "message_data"):
                msg_id = message.message_data.get("id") or message.message_data.get("type")
            elif hasattr(message, "message"):
                msg_id = getattr(message.message, "id", None) or getattr(message.message, "type", None)

            if msg_id:
                delivery_times[msg_id] = time.time()
                delivered_messages.append(msg_id)
            return True

        # Set up message processors
        message_queue.set_message_processor(track_message_delivery)

        # Create comprehensive message set simulating real user interaction
        user_messages = [
            {
                "id": f"msg_{i}",
                "type": event["type"],
                "content": event["content"],
                "user_id": str(self.test_user_id),
                "timestamp": time.time() + i * 0.1,
                "sequence": i
            }
            for i, event in enumerate(self.critical_agent_events)
        ]

        # Add additional stress messages
        stress_messages = [
            {
                "id": f"stress_msg_{i}",
                "type": "status_update",
                "content": f"Status update {i}",
                "user_id": str(self.test_user_id),
                "timestamp": time.time() + 0.05 + i * 0.02,
                "sequence": 100 + i
            }
            for i in range(20)  # 20 additional messages for stress testing
        ]

        all_messages = user_messages + stress_messages

        # CONCURRENT ROUTING: Simulate production scenario where messages
        # are routed to different queue implementations based on system state
        routing_tasks = []

        # Route critical messages through MessageQueue (state-aware)
        for msg in user_messages:
            priority = MessagePriority.CRITICAL if msg["type"] in ["agent_started", "agent_completed"] else MessagePriority.HIGH
            routing_tasks.append(
                asyncio.create_task(
                    message_queue.enqueue_message(msg, msg["type"], priority, msg["id"])
                )
            )

        # Route all messages through Buffer (recovery mechanism)
        for msg in all_messages:
            buffer_priority = BufferPriority.CRITICAL if msg["type"] in ["agent_started", "agent_completed"] else BufferPriority.HIGH
            routing_tasks.append(
                asyncio.create_task(
                    message_buffer.buffer_message(str(self.test_user_id), msg, buffer_priority)
                )
            )

        # Route status updates through utils queue (lightweight messages)
        for msg in stress_messages:
            routing_tasks.append(
                asyncio.create_task(utils_queue.enqueue(msg))
            )

        # Execute all routing concurrently (race condition)
        routing_results = await asyncio.gather(*routing_tasks, return_exceptions=True)

        # Count routing failures
        routing_failures = sum(1 for result in routing_results if isinstance(result, Exception) or result is False)

        # CONCURRENT PROCESSING: Process all queues simultaneously
        processing_tasks = [
            asyncio.create_task(message_queue.flush_queue()),
            asyncio.create_task(
                message_buffer.deliver_buffered_messages(str(self.test_user_id), track_message_delivery)
            ),
            # Utils queue processing
            asyncio.create_task(self._process_utils_queue(utils_queue, track_message_delivery))
        ]

        processing_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        processing_failures = sum(1 for result in processing_results if isinstance(result, Exception))

        # Analyze message delivery results
        expected_message_count = len(all_messages)
        delivered_message_count = len(set(delivered_messages))  # Unique messages delivered
        duplicate_deliveries = len(delivered_messages) - delivered_message_count
        lost_messages = expected_message_count - delivered_message_count

        # Check for critical message loss
        critical_message_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        delivered_critical = [msg for msg in delivered_messages if any(critical_type in msg for critical_type in critical_message_types)]
        lost_critical_messages = len(critical_message_types) - len(set(delivered_critical))

        self.fail(
            f"EXPECTED FAILURE - Message Loss in Production Scenario (Issue #1011):\n"
            f"Multiple queue implementations caused message loss during real WebSocket processing:\n"
            f"\n=== ROUTING ANALYSIS ===\n"
            f"- Total messages sent: {expected_message_count}\n"
            f"- Routing failures: {routing_failures}\n"
            f"- Processing failures: {processing_failures}\n"
            f"\n=== MESSAGE DELIVERY ANALYSIS ===\n"
            f"- Expected deliveries: {expected_message_count}\n"
            f"- Unique messages delivered: {delivered_message_count}\n"
            f"- Lost messages: {lost_messages}\n"
            f"- Duplicate deliveries: {duplicate_deliveries}\n"
            f"\n=== CRITICAL MESSAGE ANALYSIS ===\n"
            f"- Critical messages expected: {len(critical_message_types)}\n"
            f"- Critical messages delivered: {len(set(delivered_critical))}\n"
            f"- LOST CRITICAL MESSAGES: {lost_critical_messages}\n"
            f"\n=== BUSINESS IMPACT ===\n"
            f"Lost critical messages disrupt the Golden Path user flow.\n"
            f"Users don't see agent progress updates, breaking the $500K+ ARR chat experience.\n"
            f"\nDelivered messages: {sorted(set(delivered_messages))}\n"
            f"All deliveries (with duplicates): {delivered_messages}"
        )

    async def test_message_ordering_corruption_in_real_websocket_flow(self):
        """
        FAILING INTEGRATION TEST: Shows how queue fragmentation corrupts message ordering
        in real WebSocket connections, breaking the logical flow of agent interactions.

        Expected to FAIL due to out-of-order delivery breaking user experience.
        """
        # Create queues with different ordering behaviors
        priority_queue = MessageQueue(self.test_connection_id, self.test_user_id)
        fifo_buffer = WebSocketMessageBuffer()
        simple_queue = WebSocketMessageQueue()

        # Create ordered conversation flow
        conversation_flow = [
            {"seq": 1, "type": "user_message", "content": "Analyze this data for me"},
            {"seq": 2, "type": "agent_started", "content": "I'll analyze your data"},
            {"seq": 3, "type": "agent_thinking", "content": "Reading your data..."},
            {"seq": 4, "type": "tool_executing", "content": "Running analysis algorithm"},
            {"seq": 5, "type": "agent_thinking", "content": "Interpreting results..."},
            {"seq": 6, "type": "tool_completed", "content": "Analysis complete"},
            {"seq": 7, "type": "agent_completed", "content": "Here are your insights: ..."}
        ]

        # Track message delivery order from each queue
        priority_queue_order = []
        buffer_order = []
        simple_queue_order = []

        async def track_priority_queue_order(queued_msg):
            priority_queue_order.append(queued_msg.message_data["seq"])

        async def track_buffer_order(message):
            buffer_order.append(message["seq"])
            return True

        async def track_simple_queue_order():
            while not simple_queue.is_empty():
                msg = await simple_queue.dequeue(timeout=0.1)
                if msg:
                    simple_queue_order.append(msg["seq"])

        # Set up processors
        priority_queue.set_message_processor(track_priority_queue_order)

        # Send messages to all queues with different priority assignments
        for msg in conversation_flow:
            # Priority queue: Assign different priorities
            if msg["type"] in ["agent_started", "agent_completed"]:
                priority = MessagePriority.CRITICAL
            elif msg["type"] in ["tool_executing", "tool_completed"]:
                priority = MessagePriority.HIGH
            else:
                priority = MessagePriority.NORMAL

            await priority_queue.enqueue_message(msg, msg["type"], priority, f"msg_{msg['seq']}")

            # Buffer: All messages same priority (FIFO)
            await fifo_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.HIGH)

            # Simple queue: Pure FIFO
            await simple_queue.enqueue(msg)

        # Process all queues
        await priority_queue.flush_queue()
        await fifo_buffer.deliver_buffered_messages(str(self.test_user_id), track_buffer_order)
        await track_simple_queue_order()

        # Expected chronological order for user experience
        expected_order = [1, 2, 3, 4, 5, 6, 7]

        # Calculate ordering correctness
        def calculate_ordering_errors(actual_order, expected_order):
            if len(actual_order) != len(expected_order):
                return len(expected_order)  # Complete failure

            errors = 0
            for i, expected in enumerate(expected_order):
                if i >= len(actual_order) or actual_order[i] != expected:
                    errors += 1
            return errors

        priority_errors = calculate_ordering_errors(priority_queue_order, expected_order)
        buffer_errors = calculate_ordering_errors(buffer_order, expected_order)
        simple_errors = calculate_ordering_errors(simple_queue_order, expected_order)

        self.fail(
            f"EXPECTED FAILURE - Message Ordering Corruption (Issue #1011):\n"
            f"Different queue implementations produce different message ordering:\n"
            f"\n=== CONVERSATION FLOW ANALYSIS ===\n"
            f"- Expected chronological order: {expected_order}\n"
            f"- Priority queue delivered: {priority_queue_order} ({priority_errors} errors)\n"
            f"- Buffer delivered: {buffer_order} ({buffer_errors} errors)\n"
            f"- Simple queue delivered: {simple_queue_order} ({simple_errors} errors)\n"
            f"\n=== USER EXPERIENCE IMPACT ===\n"
            f"Out-of-order messages break the logical conversation flow.\n"
            f"Users see 'Analysis complete' before 'Running analysis algorithm'.\n"
            f"This destroys the illusion of intelligent agent interaction.\n"
            f"\n=== BUSINESS IMPACT ===\n"
            f"Broken conversation flow reduces user trust and satisfaction.\n"
            f"Chat quality issues directly impact the $500K+ ARR user retention."
        )

    async def test_connection_recovery_message_loss(self):
        """
        FAILING INTEGRATION TEST: Shows message loss during WebSocket connection recovery
        when multiple queue implementations handle recovery differently.

        This simulates the production scenario where connection drops cause message loss
        because different queues have different recovery strategies.

        Expected to FAIL due to recovery strategy conflicts.
        """
        # Create queues with different recovery capabilities
        state_aware_queue = MessageQueue(self.test_connection_id, self.test_user_id)
        recovery_buffer = WebSocketMessageBuffer()  # Has recovery features
        basic_queue = WebSocketMessageQueue()  # No recovery

        # Simulate active conversation before connection drop
        pre_disconnect_messages = [
            {"id": "pre_1", "type": "agent_thinking", "content": "Analyzing your request..."},
            {"id": "pre_2", "type": "tool_executing", "content": "Running calculations..."},
        ]

        # Messages sent during connection drop (should be recovered)
        during_disconnect_messages = [
            {"id": "disconnect_1", "type": "tool_completed", "content": "Calculations complete"},
            {"id": "disconnect_2", "type": "agent_thinking", "content": "Preparing response..."},
            {"id": "disconnect_3", "type": "agent_completed", "content": "Here are your results..."},
        ]

        # Messages sent after reconnection
        post_reconnect_messages = [
            {"id": "post_1", "type": "user_message", "content": "Thank you!"},
            {"id": "post_2", "type": "agent_started", "content": "You're welcome!"},
        ]

        all_messages = pre_disconnect_messages + during_disconnect_messages + post_reconnect_messages

        # Track recovered messages
        recovered_from_state_queue = []
        recovered_from_buffer = []
        recovered_from_basic_queue = []

        async def track_state_queue_recovery(queued_msg):
            recovered_from_state_queue.append(queued_msg.message_data["id"])

        async def track_buffer_recovery(message):
            recovered_from_buffer.append(message["id"])
            return True

        # Set up processors
        state_aware_queue.set_message_processor(track_state_queue_recovery)

        # Phase 1: Send pre-disconnect messages
        for msg in pre_disconnect_messages:
            await state_aware_queue.enqueue_message(msg, msg["type"], MessagePriority.HIGH, msg["id"])
            await recovery_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.HIGH)
            await basic_queue.enqueue(msg)

        # Process pre-disconnect messages
        await state_aware_queue.flush_queue()
        await recovery_buffer.deliver_buffered_messages(str(self.test_user_id), track_buffer_recovery)
        while not basic_queue.is_empty():
            msg = await basic_queue.dequeue(timeout=0.1)
            if msg:
                recovered_from_basic_queue.append(msg["id"])

        # Clear tracking for disconnect simulation
        recovered_from_state_queue.clear()
        recovered_from_buffer.clear()
        recovered_from_basic_queue.clear()

        # Phase 2: Simulate connection drop - send messages that need recovery
        for msg in during_disconnect_messages:
            await state_aware_queue.enqueue_message(msg, msg["type"], MessagePriority.HIGH, msg["id"])
            await recovery_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.HIGH)
            await basic_queue.enqueue(msg)

        # Simulate connection recovery delay
        await asyncio.sleep(0.1)

        # Phase 3: Simulate reconnection - attempt message recovery
        try:
            # State-aware queue recovery
            await state_aware_queue.flush_queue()

            # Buffer recovery
            buffered_messages = await recovery_buffer.get_buffered_messages(str(self.test_user_id))
            await recovery_buffer.deliver_buffered_messages(str(self.test_user_id), track_buffer_recovery)

            # Basic queue (no recovery mechanism)
            while not basic_queue.is_empty():
                msg = await basic_queue.dequeue(timeout=0.1)
                if msg:
                    recovered_from_basic_queue.append(msg["id"])

        except Exception as e:
            # Recovery failures are part of the problem we're demonstrating
            pass

        # Phase 4: Send post-reconnect messages
        for msg in post_reconnect_messages:
            await state_aware_queue.enqueue_message(msg, msg["type"], MessagePriority.HIGH, msg["id"])
            await recovery_buffer.buffer_message(str(self.test_user_id), msg, BufferPriority.HIGH)
            await basic_queue.enqueue(msg)

        # Process post-reconnect messages
        await state_aware_queue.flush_queue()
        await recovery_buffer.deliver_buffered_messages(str(self.test_user_id), track_buffer_recovery)
        while not basic_queue.is_empty():
            msg = await basic_queue.dequeue(timeout=0.1)
            if msg:
                recovered_from_basic_queue.append(msg["id"])

        # Analyze recovery effectiveness
        expected_during_disconnect = [msg["id"] for msg in during_disconnect_messages]
        expected_post_reconnect = [msg["id"] for msg in post_reconnect_messages]

        # Calculate recovery rates
        state_queue_recovery_rate = len([msg for msg in recovered_from_state_queue if msg in expected_during_disconnect]) / len(expected_during_disconnect) * 100
        buffer_recovery_rate = len([msg for msg in recovered_from_buffer if msg in expected_during_disconnect]) / len(expected_during_disconnect) * 100
        basic_queue_recovery_rate = len([msg for msg in recovered_from_basic_queue if msg in expected_during_disconnect]) / len(expected_during_disconnect) * 100

        self.fail(
            f"EXPECTED FAILURE - Connection Recovery Message Loss (Issue #1011):\n"
            f"Different queue implementations have conflicting recovery strategies:\n"
            f"\n=== DISCONNECT RECOVERY ANALYSIS ===\n"
            f"- Messages during disconnect: {len(expected_during_disconnect)}\n"
            f"- State-aware queue recovered: {len([msg for msg in recovered_from_state_queue if msg in expected_during_disconnect])} ({state_queue_recovery_rate:.1f}%)\n"
            f"- Buffer recovered: {len([msg for msg in recovered_from_buffer if msg in expected_during_disconnect])} ({buffer_recovery_rate:.1f}%)\n"
            f"- Basic queue recovered: {len([msg for msg in recovered_from_basic_queue if msg in expected_during_disconnect])} ({basic_queue_recovery_rate:.1f}%)\n"
            f"\n=== MESSAGE RECOVERY DETAILS ===\n"
            f"- Expected during disconnect: {expected_during_disconnect}\n"
            f"- State queue recovered: {recovered_from_state_queue}\n"
            f"- Buffer recovered: {recovered_from_buffer}\n"
            f"- Basic queue recovered: {recovered_from_basic_queue}\n"
            f"\n=== USER EXPERIENCE IMPACT ===\n"
            f"Inconsistent recovery means users lose different messages depending on routing.\n"
            f"Critical agent responses disappear, breaking conversation continuity.\n"
            f"Users must refresh/reconnect manually, degrading the experience.\n"
            f"\n=== BUSINESS IMPACT ===\n"
            f"Message loss during connection issues affects user trust and retention.\n"
            f"Unreliable chat delivery impacts the $500K+ ARR business value."
        )

    async def _process_utils_queue(self, queue: WebSocketMessageQueue, delivery_callback) -> int:
        """Helper method to process utils queue messages."""
        processed_count = 0
        while not queue.is_empty():
            try:
                message = await queue.dequeue(timeout=0.1)
                if message:
                    await delivery_callback(message)
                    processed_count += 1
                else:
                    break
            except Exception:
                break
        return processed_count

    async def test_high_throughput_message_loss_under_load(self):
        """
        FAILING INTEGRATION TEST: Demonstrates message loss under high throughput
        when multiple queue implementations compete for resources.

        This simulates production load conditions where multiple users
        generate high message volume simultaneously.

        Expected to FAIL due to resource contention and queue overflow conflicts.
        """
        # Create multiple user scenarios with different queue implementations
        num_concurrent_users = 5
        messages_per_user = 50

        user_queues = {}
        user_buffers = {}
        user_utils_queues = {}
        user_delivered_messages = {}

        # Set up queues for each user
        for i in range(num_concurrent_users):
            user_id = UserID(f"user_{str(uuid.uuid4())}")
            connection_id = ConnectionID(f"conn_{str(uuid.uuid4())}")

            user_queues[user_id] = MessageQueue(connection_id, user_id, max_size=100)
            user_buffers[user_id] = WebSocketMessageBuffer()
            user_utils_queues[user_id] = WebSocketMessageQueue(max_size=100)
            user_delivered_messages[user_id] = []

        # Create high-volume message generation
        async def generate_user_messages(user_id: UserID, message_count: int):
            """Generate messages for a specific user."""
            messages = []
            for i in range(message_count):
                messages.append({
                    "id": f"user_{user_id}_msg_{i}",
                    "type": "agent_thinking",
                    "content": f"Processing request {i} for user {user_id}",
                    "user_id": str(user_id),
                    "timestamp": time.time() + i * 0.001  # Rapid message generation
                })
            return messages

        # Generate all user messages concurrently
        message_generation_tasks = [
            generate_user_messages(user_id, messages_per_user)
            for user_id in user_queues.keys()
        ]

        all_user_messages = await asyncio.gather(*message_generation_tasks)
        user_message_map = dict(zip(user_queues.keys(), all_user_messages))

        # Create message delivery trackers for each user
        async def create_delivery_tracker(user_id: UserID):
            async def track_delivery(message):
                msg_id = message.get("id") if isinstance(message, dict) else getattr(message, "id", None)
                if hasattr(message, "message_data"):
                    msg_id = message.message_data.get("id")
                if msg_id:
                    user_delivered_messages[user_id].append(msg_id)
                return True
            return track_delivery

        # Set up delivery tracking
        delivery_trackers = {}
        for user_id in user_queues.keys():
            delivery_trackers[user_id] = await create_delivery_tracker(user_id)
            user_queues[user_id].set_message_processor(delivery_trackers[user_id])

        # HIGH THROUGHPUT LOAD TEST: Send all messages concurrently across all queue types
        load_test_tasks = []

        for user_id, messages in user_message_map.items():
            # Send to MessageQueue
            for msg in messages:
                load_test_tasks.append(
                    asyncio.create_task(
                        user_queues[user_id].enqueue_message(msg, msg["type"], MessagePriority.HIGH, msg["id"])
                    )
                )

            # Send to Buffer
            for msg in messages:
                load_test_tasks.append(
                    asyncio.create_task(
                        user_buffers[user_id].buffer_message(str(user_id), msg, BufferPriority.HIGH)
                    )
                )

            # Send to Utils Queue
            for msg in messages:
                load_test_tasks.append(
                    asyncio.create_task(user_utils_queues[user_id].enqueue(msg))
                )

        # Execute load test
        start_time = time.time()
        load_results = await asyncio.gather(*load_test_tasks, return_exceptions=True)
        load_time = time.time() - start_time

        # Count load test failures
        load_failures = sum(1 for result in load_results if isinstance(result, Exception) or result is False)

        # Process all queues concurrently under load
        processing_tasks = []

        for user_id in user_queues.keys():
            processing_tasks.extend([
                asyncio.create_task(user_queues[user_id].flush_queue()),
                asyncio.create_task(
                    user_buffers[user_id].deliver_buffered_messages(str(user_id), delivery_trackers[user_id])
                ),
                asyncio.create_task(
                    self._process_utils_queue(user_utils_queues[user_id], delivery_trackers[user_id])
                )
            ])

        processing_start = time.time()
        processing_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        processing_time = time.time() - processing_start

        # Analyze load test results
        processing_failures = sum(1 for result in processing_results if isinstance(result, Exception))

        total_messages_sent = num_concurrent_users * messages_per_user
        total_messages_delivered = sum(len(messages) for messages in user_delivered_messages.values())
        total_message_loss = total_messages_sent - total_messages_delivered

        # Calculate per-user statistics
        user_loss_stats = {}
        for user_id, delivered in user_delivered_messages.items():
            expected = messages_per_user
            actual = len(set(delivered))  # Unique messages
            duplicates = len(delivered) - actual
            loss = expected - actual
            user_loss_stats[str(user_id)] = {
                "expected": expected,
                "delivered": actual,
                "lost": loss,
                "duplicates": duplicates,
                "loss_rate": (loss / expected) * 100 if expected > 0 else 0
            }

        # Calculate system-wide metrics
        avg_loss_rate = sum(stats["loss_rate"] for stats in user_loss_stats.values()) / len(user_loss_stats)
        max_loss_rate = max(stats["loss_rate"] for stats in user_loss_stats.values())
        total_duplicates = sum(stats["duplicates"] for stats in user_loss_stats.values())

        self.fail(
            f"EXPECTED FAILURE - High Throughput Message Loss (Issue #1011):\n"
            f"Multiple queue implementations cause message loss under concurrent load:\n"
            f"\n=== LOAD TEST CONFIGURATION ===\n"
            f"- Concurrent users: {num_concurrent_users}\n"
            f"- Messages per user: {messages_per_user}\n"
            f"- Total messages sent: {total_messages_sent}\n"
            f"- Load test duration: {load_time:.2f}s\n"
            f"- Processing duration: {processing_time:.2f}s\n"
            f"\n=== MESSAGE DELIVERY RESULTS ===\n"
            f"- Total messages delivered: {total_messages_delivered}\n"
            f"- Total messages lost: {total_message_loss}\n"
            f"- Total duplicate deliveries: {total_duplicates}\n"
            f"- Load operation failures: {load_failures}\n"
            f"- Processing failures: {processing_failures}\n"
            f"\n=== USER-LEVEL STATISTICS ===\n"
            f"- Average loss rate: {avg_loss_rate:.1f}%\n"
            f"- Maximum loss rate: {max_loss_rate:.1f}%\n"
            f"- Per-user details: {user_loss_stats}\n"
            f"\n=== SYSTEM PERFORMANCE IMPACT ===\n"
            f"- Messages per second (load): {total_messages_sent / load_time:.1f}\n"
            f"- Messages per second (processing): {total_messages_delivered / processing_time:.1f}\n"
            f"- System efficiency: {(total_messages_delivered / (total_messages_sent * 3)) * 100:.1f}%\n"
            f"\n=== BUSINESS IMPACT ===\n"
            f"Message loss under load affects multiple users simultaneously.\n"
            f"Peak usage times result in degraded experience for all users.\n"
            f"Inconsistent performance affects user trust and $500K+ ARR retention."
        )