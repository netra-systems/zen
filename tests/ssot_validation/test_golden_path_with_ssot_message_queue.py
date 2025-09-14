"""
Golden Path Integration Tests with SSOT Message Queue

PURPOSE: Validate golden path user flow with consolidated message queue
BUSINESS VALUE:
- Segment: Enterprise/Platform
- Goal: Revenue Protection & User Experience
- Impact: Protects $500K+ ARR Golden Path functionality
- Strategic Impact: Ensures critical user workflows remain operational during SSOT consolidation

MISSION CRITICAL: Issue #1011 - SSOT WebSocket Message Queue & Golden Path Integration
These tests validate the complete end-to-end user experience with unified message handling.

Golden Path User Flow:
1. User Login → Authentication
2. WebSocket Connection → Message Queue Initialization
3. Agent Interaction → Message Delivery via Queue
4. Real-time Updates → WebSocket Events via Queue
5. Session Management → Queue Cleanup

Expected Test State: FAILING initially (demonstrates current issues)
Expected Fix State: PASSING (after SSOT consolidation complete)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec

import pytest

from test_framework.ssot.base_test_case import SsotAsyncTestCase
from shared.types.core_types import UserID, ConnectionID
from netra_backend.app.logging_config import central_logger

# Golden Path imports - critical business functionality
try:
    from netra_backend.app.dependencies import get_user_execution_context
    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
    from netra_backend.app.agents.registry import AgentRegistry
except ImportError as e:
    logger = central_logger.get_logger(__name__)
    logger.warning(f"Golden Path import warning: {e}")

# Import current message queue implementations for testing
from netra_backend.app.services.websocket.message_queue import MessageQueue as RedisMessageQueue
from netra_backend.app.websocket_core.message_queue import MessageQueue as ConnectionStateMessageQueue
from netra_backend.app.websocket_core.message_buffer import WebSocketMessageBuffer

logger = central_logger.get_logger(__name__)


class TestGoldenPathWithSsotMessageQueue(SsotAsyncTestCase):
    """
    Test suite to validate Golden Path user flow with SSOT message queue integration.

    CRITICAL: These tests validate $500K+ ARR business functionality.
    Success criteria: Complete user workflow operates reliably with consolidated queue.
    """

    def setup_method(self, method):
        """Set up Golden Path test environment."""
        super().setup_method(method)

        # Golden Path user scenario
        self.user_id = UserID("golden_path_user_789")
        self.connection_id = ConnectionID("golden_conn_789")
        self.session_id = f"session_{uuid.uuid4()}"

        # Critical WebSocket events for Golden Path
        self.critical_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        # Mock implementations for testing
        self.mock_websocket_manager = None
        self.mock_agent = None
        self.mock_user_context = None

        # Message tracking
        self.delivered_messages = []
        self.websocket_events = []

    async def _setup_golden_path_mocks(self):
        """Set up mocks for Golden Path components."""
        # Mock user execution context
        self.mock_user_context = MagicMock()
        self.mock_user_context.user_id = str(self.user_id)
        self.mock_user_context.session_id = self.session_id
        self.mock_user_context.connection_id = str(self.connection_id)

        # Mock WebSocket manager with message delivery
        self.mock_websocket_manager = create_autospec(object, spec_set=True)
        self.mock_websocket_manager.send_to_user = AsyncMock(side_effect=self._mock_message_delivery)
        self.mock_websocket_manager.connection_id = str(self.connection_id)
        self.mock_websocket_manager.user_id = str(self.user_id)

        # Mock agent with message queue integration
        self.mock_agent = create_autospec(object, spec_set=True)
        self.mock_agent.execute = AsyncMock(side_effect=self._mock_agent_execution)
        self.mock_agent.user_id = str(self.user_id)

    async def _mock_message_delivery(self, message_data: Dict[str, Any]) -> bool:
        """Mock message delivery tracking for Golden Path validation."""
        delivery_record = {
            "message": message_data,
            "user_id": str(self.user_id),
            "connection_id": str(self.connection_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "delivery_method": "websocket"
        }
        self.delivered_messages.append(delivery_record)

        # Track critical WebSocket events
        message_type = message_data.get("type", "unknown")
        if message_type in self.critical_events:
            self.websocket_events.append({
                "event_type": message_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": str(self.user_id)
            })

        return True

    async def _mock_agent_execution(self, user_request: str) -> Dict[str, Any]:
        """Mock agent execution that generates WebSocket events."""
        # Simulate agent workflow with message queue integration
        agent_events = [
            {"type": "agent_started", "message": "Starting to process your request"},
            {"type": "agent_thinking", "message": "Analyzing your request..."},
            {"type": "tool_executing", "message": "Executing relevant tools"},
            {"type": "tool_completed", "message": "Tools executed successfully"},
            {"type": "agent_completed", "message": "Request processed successfully"}
        ]

        # Send events through message delivery
        for event in agent_events:
            await self._mock_message_delivery(event)

        return {
            "status": "success",
            "response": "Mock agent response",
            "events_generated": len(agent_events)
        }

    async def teardown_method(self, method):
        """Clean up Golden Path test environment."""
        await super().teardown_method(method)

    async def test_end_to_end_message_delivery_with_consolidated_queue(self):
        """
        Test complete end-to-end message delivery through consolidated queue.
        This validates the core Golden Path message flow.
        """
        await self._setup_golden_path_mocks()

        # Initialize message queues for testing current behavior
        redis_queue = RedisMessageQueue()
        connection_queue = ConnectionStateMessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=100
        )
        message_buffer = WebSocketMessageBuffer()
        await message_buffer.start()

        try:
            # Simulate Golden Path message flow
            golden_path_messages = [
                {"type": "user_login", "message": "User authenticated successfully"},
                {"type": "websocket_connect", "message": "WebSocket connection established"},
                {"type": "agent_request", "message": "User requested AI assistance"},
                {"type": "agent_started", "message": "AI agent started processing"},
                {"type": "agent_completed", "message": "AI processing completed"}
            ]

            # Test message delivery through each queue (demonstrating current fragmentation)
            delivery_results = []

            for i, message in enumerate(golden_path_messages):
                message["user_id"] = str(self.user_id)
                message["message_id"] = f"golden_{i}"
                message["timestamp"] = datetime.now(timezone.utc).isoformat()

                # Simulate delivery through different queues (current fragmented approach)
                if i % 3 == 0:  # Redis queue
                    from netra_backend.app.services.websocket.message_queue import QueuedMessage as RedisMsg
                    redis_msg = RedisMsg(
                        user_id=str(self.user_id),
                        type=message["type"],
                        payload=message
                    )
                    redis_result = await redis_queue.enqueue(redis_msg)
                    delivery_results.append(("redis", redis_result))

                elif i % 3 == 1:  # ConnectionState queue
                    conn_result = await connection_queue.enqueue_message(
                        message_data=message,
                        message_type=message["type"]
                    )
                    delivery_results.append(("connection_state", conn_result))

                else:  # Message buffer
                    buffer_result = await message_buffer.buffer_message(
                        user_id=str(self.user_id),
                        message=message
                    )
                    delivery_results.append(("buffer", buffer_result))

            # Analyze delivery results
            successful_deliveries = sum(1 for _, result in delivery_results if result)
            total_messages = len(golden_path_messages)

            self.record_custom_metric("golden_path_messages", total_messages)
            self.record_custom_metric("successful_deliveries", successful_deliveries)
            self.record_custom_metric("delivery_success_rate", successful_deliveries / total_messages)
            self.record_custom_metric("queue_fragmentation", len(set(queue_type for queue_type, _ in delivery_results)))

            logger.info(f"Golden Path delivery: {successful_deliveries}/{total_messages} messages delivered")
            logger.error(f"Queue fragmentation: Using {len(set(queue_type for queue_type, _ in delivery_results))} different queues")

            # This test should highlight the current fragmentation issue
            # In ideal SSOT implementation, all messages would go through single queue
            assert successful_deliveries == total_messages, \
                f"Golden Path message delivery incomplete: {successful_deliveries}/{total_messages}"

        finally:
            await message_buffer.stop()
            await redis_queue.stop_processing()
            await connection_queue.close()

    async def test_multi_user_message_isolation_single_queue(self):
        """
        Test that consolidated queue properly isolates messages between multiple users.
        This is critical for enterprise security and Golden Path scalability.
        """
        await self._setup_golden_path_mocks()

        # Set up multiple users for isolation testing
        users = [
            UserID("user_alpha"),
            UserID("user_beta"),
            UserID("user_gamma")
        ]

        connection_queues = {}
        message_buffers = {}

        try:
            # Initialize separate queues for each user (current approach)
            for user in users:
                conn_id = ConnectionID(f"conn_{user}")
                connection_queues[user] = ConnectionStateMessageQueue(
                    connection_id=conn_id,
                    user_id=user,
                    max_size=50
                )

                buffer = WebSocketMessageBuffer()
                await buffer.start()
                message_buffers[user] = buffer

            # Send user-specific messages
            user_messages = {}
            for user in users:
                user_messages[user] = []
                for i in range(3):
                    message = {
                        "type": "agent_thinking",
                        "content": f"Private message for {user} - {i}",
                        "user_id": str(user),
                        "sensitive_data": f"secret_info_{user}_{i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    user_messages[user].append(message)

                    # Send to user's queue
                    await connection_queues[user].enqueue_message(
                        message_data=message,
                        message_type=message["type"]
                    )

                    # Also send to user's buffer
                    await message_buffers[user].buffer_message(
                        user_id=str(user),
                        message=message
                    )

            # Verify message isolation
            isolation_violations = []
            cross_contamination_count = 0

            for user in users:
                # Check ConnectionState queue isolation
                conn_stats = connection_queues[user].get_queue_stats()
                expected_messages = len(user_messages[user])
                actual_messages = conn_stats.get("total_size", 0)

                if actual_messages != expected_messages:
                    isolation_violations.append(f"User {user} connection queue: expected {expected_messages}, got {actual_messages}")

                # Check buffer isolation
                buffer_stats = message_buffers[user].get_buffer_stats()
                buffer_messages = buffer_stats.get("total_buffered_messages", 0)

                if buffer_messages != expected_messages:
                    isolation_violations.append(f"User {user} buffer: expected {expected_messages}, got {buffer_messages}")

                # Check for cross-user contamination (simplified check)
                user_buffer_info = message_buffers[user].get_user_buffer_info(str(user))
                if user_buffer_info.get("buffer_size", 0) != expected_messages:
                    cross_contamination_count += 1

            self.record_custom_metric("total_users_tested", len(users))
            self.record_custom_metric("isolation_violations", len(isolation_violations))
            self.record_custom_metric("cross_contamination_count", cross_contamination_count)
            self.record_custom_metric("queue_types_per_user", 2)  # ConnectionState + Buffer

            logger.info(f"Multi-user isolation test: {len(isolation_violations)} violations found")

            # In proper SSOT implementation, there should be perfect isolation with single queue
            assert len(isolation_violations) == 0, \
                f"User message isolation violations found: {isolation_violations}"

        finally:
            # Clean up all queues
            for user in users:
                if user in connection_queues:
                    await connection_queues[user].close()
                if user in message_buffers:
                    await message_buffers[user].stop()

    async def test_agent_websocket_events_with_ssot_queue(self):
        """
        Test that agent WebSocket events are properly delivered through SSOT queue.
        This validates the core Golden Path AI interaction flow.
        """
        await self._setup_golden_path_mocks()

        # Test current agent event delivery (fragmented across queues)
        agent_event_queues = {
            "redis": RedisMessageQueue(),
            "connection_state": ConnectionStateMessageQueue(
                connection_id=self.connection_id,
                user_id=self.user_id,
                max_size=100
            ),
            "buffer": WebSocketMessageBuffer()
        }

        await agent_event_queues["buffer"].start()

        try:
            # Simulate agent execution generating critical events
            agent_events = []
            for event_type in self.critical_events:
                event = {
                    "type": event_type,
                    "message": f"Agent {event_type.replace('_', ' ')} event",
                    "user_id": str(self.user_id),
                    "agent_id": "supervisor_agent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "priority": "high" if event_type in ["agent_started", "agent_completed"] else "normal"
                }
                agent_events.append(event)

            # Distribute events across different queues (current fragmented approach)
            event_distribution = []

            for i, event in enumerate(agent_events):
                queue_type = list(agent_event_queues.keys())[i % len(agent_event_queues)]

                if queue_type == "redis":
                    from netra_backend.app.services.websocket.message_queue import QueuedMessage as RedisMsg
                    redis_msg = RedisMsg(
                        user_id=str(self.user_id),
                        type=event["type"],
                        payload=event
                    )
                    success = await agent_event_queues["redis"].enqueue(redis_msg)

                elif queue_type == "connection_state":
                    success = await agent_event_queues["connection_state"].enqueue_message(
                        message_data=event,
                        message_type=event["type"]
                    )

                else:  # buffer
                    success = await agent_event_queues["buffer"].buffer_message(
                        user_id=str(self.user_id),
                        message=event
                    )

                event_distribution.append((queue_type, success))

            # Analyze event distribution
            successful_events = sum(1 for _, success in event_distribution if success)
            queues_used = set(queue_type for queue_type, _ in event_distribution)
            critical_events_count = len([e for e in agent_events if e["type"] in self.critical_events])

            self.record_custom_metric("total_agent_events", len(agent_events))
            self.record_custom_metric("successful_agent_events", successful_events)
            self.record_custom_metric("critical_events_count", critical_events_count)
            self.record_custom_metric("queues_used_for_events", len(queues_used))
            self.record_custom_metric("event_distribution", dict(event_distribution))

            logger.info(f"Agent events: {successful_events}/{len(agent_events)} delivered across {len(queues_used)} queues")

            # Verify all critical events were handled
            assert successful_events == len(agent_events), \
                f"Agent event delivery incomplete: {successful_events}/{len(agent_events)}"

            # This should highlight queue fragmentation issue
            assert len(queues_used) == 1, \
                f"Agent events should use single queue, but used {len(queues_used)}: {list(queues_used)}"

        finally:
            await agent_event_queues["buffer"].stop()
            await agent_event_queues["redis"].stop_processing()
            await agent_event_queues["connection_state"].close()

    async def test_connection_lifecycle_with_consolidated_queue(self):
        """
        Test WebSocket connection lifecycle with consolidated message queue.
        This validates Golden Path connection management and cleanup.
        """
        await self._setup_golden_path_mocks()

        # Simulate connection lifecycle stages
        lifecycle_stages = [
            "connecting",
            "authenticating",
            "services_ready",
            "processing_ready",
            "active",
            "degraded",
            "disconnecting",
            "closed"
        ]

        # Track message handling at each lifecycle stage
        lifecycle_results = {}
        connection_queue = ConnectionStateMessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=100
        )

        try:
            for stage in lifecycle_stages:
                # Simulate different message handling behavior per stage
                test_message = {
                    "type": f"lifecycle_{stage}",
                    "content": f"Message during {stage} stage",
                    "user_id": str(self.user_id),
                    "connection_stage": stage,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                # Test message enqueue during this lifecycle stage
                enqueue_success = await connection_queue.enqueue_message(
                    message_data=test_message,
                    message_type=test_message["type"]
                )

                # Get queue state during this stage
                queue_stats = connection_queue.get_queue_stats()

                lifecycle_results[stage] = {
                    "enqueue_success": enqueue_success,
                    "queue_state": queue_stats.get("state"),
                    "queue_size": queue_stats.get("total_size", 0),
                    "message_handled": enqueue_success
                }

                # Simulate stage-appropriate queue behavior
                if stage == "processing_ready":
                    # Should trigger message flush
                    flush_result = await connection_queue.flush_queue()
                    lifecycle_results[stage]["flush_triggered"] = flush_result
                elif stage == "closed":
                    # Should clean up queue
                    cleared_count = await connection_queue.clear_queue()
                    lifecycle_results[stage]["cleanup_performed"] = cleared_count > 0

            # Analyze lifecycle handling
            successful_stages = sum(1 for stage_data in lifecycle_results.values() if stage_data["message_handled"])
            total_stages = len(lifecycle_stages)

            processing_ready_flush = lifecycle_results.get("processing_ready", {}).get("flush_triggered", False)
            closed_cleanup = lifecycle_results.get("closed", {}).get("cleanup_performed", False)

            self.record_custom_metric("lifecycle_stages_tested", total_stages)
            self.record_custom_metric("successful_stage_handling", successful_stages)
            self.record_custom_metric("processing_ready_flush", processing_ready_flush)
            self.record_custom_metric("closed_cleanup", closed_cleanup)
            self.record_custom_metric("lifecycle_results", lifecycle_results)

            logger.info(f"Connection lifecycle: {successful_stages}/{total_stages} stages handled successfully")

            # Verify proper lifecycle handling
            assert successful_stages == total_stages, \
                f"Connection lifecycle incomplete: {successful_stages}/{total_stages} stages"

            assert processing_ready_flush, "Queue should flush when connection becomes processing ready"
            assert closed_cleanup, "Queue should clean up when connection closes"

        finally:
            await connection_queue.close()

    async def test_golden_path_no_message_loss(self):
        """
        Test that Golden Path user flow has zero message loss with consolidated queue.
        This is the ultimate reliability test for $500K+ ARR protection.
        """
        await self._setup_golden_path_mocks()

        # Set up comprehensive message tracking
        sent_messages = []
        received_messages = []
        lost_messages = []

        # Initialize all queue types for loss comparison
        queues = {
            "redis": RedisMessageQueue(),
            "connection_state": ConnectionStateMessageQueue(
                connection_id=self.connection_id,
                user_id=self.user_id,
                max_size=50  # Smaller size to test overflow
            ),
            "buffer": WebSocketMessageBuffer()
        }

        await queues["buffer"].start()

        # Mock message delivery tracking
        async def track_message_delivery(message_data):
            received_messages.append({
                "message": message_data,
                "received_at": datetime.now(timezone.utc).isoformat()
            })
            return True

        queues["connection_state"].set_message_processor(
            lambda msg: track_message_delivery(msg.message_data)
        )

        try:
            # Generate Golden Path message sequence
            golden_path_sequence = [
                {"type": "user_login", "priority": "high", "critical": True},
                {"type": "websocket_connect", "priority": "high", "critical": True},
                {"type": "agent_request", "priority": "normal", "critical": False},
                {"type": "agent_started", "priority": "high", "critical": True},
                {"type": "agent_thinking", "priority": "normal", "critical": True},
                {"type": "tool_executing", "priority": "normal", "critical": True},
                {"type": "tool_completed", "priority": "normal", "critical": True},
                {"type": "agent_completed", "priority": "high", "critical": True},
                {"type": "user_response", "priority": "normal", "critical": False}
            ]

            # Send messages through different queues (stress test)
            for i, msg_template in enumerate(golden_path_sequence):
                message = {
                    **msg_template,
                    "id": f"golden_msg_{i}",
                    "user_id": str(self.user_id),
                    "content": f"Golden Path message {i}: {msg_template['type']}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sequence_number": i
                }
                sent_messages.append(message)

                # Round-robin through queues to test all paths
                queue_type = list(queues.keys())[i % len(queues)]

                try:
                    if queue_type == "redis":
                        from netra_backend.app.services.websocket.message_queue import QueuedMessage as RedisMsg
                        redis_msg = RedisMsg(
                            user_id=str(self.user_id),
                            type=message["type"],
                            payload=message
                        )
                        success = await queues["redis"].enqueue(redis_msg)

                    elif queue_type == "connection_state":
                        success = await queues["connection_state"].enqueue_message(
                            message_data=message,
                            message_type=message["type"]
                        )

                    else:  # buffer
                        from netra_backend.app.websocket_core.message_buffer import BufferPriority
                        priority_map = {"high": BufferPriority.HIGH, "normal": BufferPriority.NORMAL}
                        success = await queues["buffer"].buffer_message(
                            user_id=str(self.user_id),
                            message=message,
                            priority=priority_map.get(message["priority"], BufferPriority.NORMAL)
                        )

                    if not success:
                        lost_messages.append({
                            "message": message,
                            "queue_type": queue_type,
                            "reason": "enqueue_failed"
                        })

                except Exception as e:
                    lost_messages.append({
                        "message": message,
                        "queue_type": queue_type,
                        "reason": f"exception: {str(e)}"
                    })

            # Flush connection state queue to trigger deliveries
            await queues["connection_state"].flush_queue()

            # Attempt buffer delivery
            buffer_delivered = await queues["buffer"].deliver_buffered_messages(
                str(self.user_id),
                track_message_delivery
            )

            # Calculate message loss statistics
            total_sent = len(sent_messages)
            total_received = len(received_messages)
            total_lost = len(lost_messages)
            critical_sent = len([msg for msg in sent_messages if msg.get("critical", False)])
            critical_received = len([msg for msg in received_messages
                                   if isinstance(msg.get("message"), dict) and
                                   msg["message"].get("critical", False)])

            loss_rate = (total_lost / total_sent * 100) if total_sent > 0 else 0
            critical_loss_rate = ((critical_sent - critical_received) / critical_sent * 100) if critical_sent > 0 else 0

            self.record_custom_metric("total_messages_sent", total_sent)
            self.record_custom_metric("total_messages_received", total_received)
            self.record_custom_metric("total_messages_lost", total_lost)
            self.record_custom_metric("message_loss_rate_percent", loss_rate)
            self.record_custom_metric("critical_messages_sent", critical_sent)
            self.record_custom_metric("critical_messages_received", critical_received)
            self.record_custom_metric("critical_loss_rate_percent", critical_loss_rate)
            self.record_custom_metric("buffer_delivered_count", buffer_delivered)

            logger.info(f"Golden Path message loss test: {total_lost}/{total_sent} messages lost ({loss_rate:.1f}%)")
            logger.error(f"Critical message loss: {critical_sent - critical_received}/{critical_sent} lost ({critical_loss_rate:.1f}%)")

            # Zero message loss requirement for Golden Path
            assert total_lost == 0, f"Golden Path message loss detected: {total_lost} messages lost - {lost_messages}"
            assert critical_loss_rate == 0, f"Critical message loss: {critical_loss_rate:.1f}% - UNACCEPTABLE for Golden Path"

        finally:
            await queues["buffer"].stop()
            await queues["redis"].stop_processing()
            await queues["connection_state"].close()

    async def test_golden_path_proper_message_ordering(self):
        """
        Test that Golden Path messages maintain proper ordering through consolidated queue.
        This validates sequential message delivery for optimal user experience.
        """
        await self._setup_golden_path_mocks()

        # Set up ordered message tracking
        sent_sequence = []
        received_sequence = []

        connection_queue = ConnectionStateMessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=100
        )

        # Mock ordered delivery tracking
        async def track_ordered_delivery(message_data):
            if isinstance(message_data, dict) and "sequence" in message_data:
                received_sequence.append({
                    "sequence": message_data["sequence"],
                    "type": message_data["type"],
                    "received_at": datetime.now(timezone.utc).isoformat()
                })
            return True

        connection_queue.set_message_processor(
            lambda msg: track_ordered_delivery(msg.message_data)
        )

        try:
            # Create ordered Golden Path sequence
            ordered_messages = [
                {"type": "user_login", "sequence": 1},
                {"type": "websocket_connect", "sequence": 2},
                {"type": "agent_request", "sequence": 3},
                {"type": "agent_started", "sequence": 4},
                {"type": "agent_thinking", "sequence": 5},
                {"type": "tool_executing", "sequence": 6},
                {"type": "tool_completed", "sequence": 7},
                {"type": "agent_completed", "sequence": 8}
            ]

            # Send messages in order
            for msg_template in ordered_messages:
                message = {
                    **msg_template,
                    "user_id": str(self.user_id),
                    "content": f"Ordered message {msg_template['sequence']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                sent_sequence.append(message)

                success = await connection_queue.enqueue_message(
                    message_data=message,
                    message_type=message["type"]
                )
                assert success, f"Failed to enqueue message {msg_template['sequence']}"

                # Small delay to ensure ordering
                await asyncio.sleep(0.01)

            # Flush and process messages
            await connection_queue.flush_queue()

            # Verify message ordering
            expected_sequence = [msg["sequence"] for msg in sent_sequence]
            actual_sequence = [msg["sequence"] for msg in received_sequence]

            ordering_violations = []
            for i in range(1, len(actual_sequence)):
                if actual_sequence[i] <= actual_sequence[i-1]:
                    ordering_violations.append(f"Message {actual_sequence[i]} came before {actual_sequence[i-1]}")

            # Calculate ordering metrics
            correct_order = expected_sequence == actual_sequence
            total_messages = len(expected_sequence)
            received_count = len(actual_sequence)

            self.record_custom_metric("expected_sequence", expected_sequence)
            self.record_custom_metric("actual_sequence", actual_sequence)
            self.record_custom_metric("correct_order", correct_order)
            self.record_custom_metric("ordering_violations", len(ordering_violations))
            self.record_custom_metric("total_ordered_messages", total_messages)
            self.record_custom_metric("received_ordered_messages", received_count)

            logger.info(f"Message ordering test: {received_count}/{total_messages} messages, correct order: {correct_order}")

            if ordering_violations:
                logger.error(f"Ordering violations found: {ordering_violations}")

            # Verify perfect ordering for Golden Path
            assert correct_order, f"Golden Path message ordering violated. Expected: {expected_sequence}, Got: {actual_sequence}"
            assert len(ordering_violations) == 0, f"Message ordering violations: {ordering_violations}"
            assert received_count == total_messages, f"Message count mismatch: expected {total_messages}, received {received_count}"

        finally:
            await connection_queue.close()


if __name__ == "__main__":
    # Run Golden Path tests with detailed output
    pytest.main([__file__, "-v", "-s", "--tb=short"])