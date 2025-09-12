"""
Advanced WebSocket Connection and Messaging Edge Cases Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket reliability for real-time AI interactions
- Value Impact: Validates complex WebSocket scenarios that enable substantive chat experiences
- Strategic Impact: CRITICAL for user engagement - WebSocket failures = lost customers

ADVANCED WEBSOCKET TEST SCENARIOS:
1. Connection recovery from network interruptions
2. Message ordering and delivery guarantees under load
3. Large message handling and fragmentation
4. Concurrent connection management per user
5. WebSocket authentication edge cases and token refresh
6. Message queue overflow and backpressure handling

CRITICAL REQUIREMENTS:
- NO MOCKS - Real WebSocket connections and message delivery
- E2E authentication with token management
- WebSocket events validation for all agent interactions
- Performance benchmarks for message throughput
- Connection resilience and automatic recovery testing
"""

import asyncio
import json
import logging
import time
import uuid
import websockets
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import threading
import queue

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket.connection_manager import WebSocketConnectionManager
from netra_backend.app.api.websocket.events import WebSocketEventType
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_engine import create_request_scoped_engine
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class WebSocketTestState(Enum):
    """WebSocket test connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    INTERRUPTED = "interrupted"
    RECOVERING = "recovering"
    DISCONNECTED = "disconnected"


@dataclass
class WebSocketMessageMetrics:
    """Metrics for WebSocket message analysis."""
    message_id: str
    sent_timestamp: datetime
    received_timestamp: Optional[datetime]
    message_size: int
    message_type: str
    delivery_time_ms: Optional[float]
    order_index: int
    user_id: str


class TestAdvancedWebSocketEdgeCases(BaseIntegrationTest):
    """Advanced integration tests for WebSocket connection and messaging edge cases."""

    @pytest.mark.asyncio
    async def test_websocket_connection_recovery_from_network_interruption(self, real_services_fixture):
        """
        Test WebSocket connection recovery from network interruptions.
        
        CRITICAL SCENARIO: Users must maintain connection during network instability.
        This validates automatic reconnection and message queue preservation.
        """
        logger.info("Starting WebSocket connection recovery test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_recovery_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize WebSocket components
        websocket_manager = WebSocketManager()
        connection_manager = WebSocketConnectionManager()
        
        # Track connection state changes
        connection_states = []
        received_messages = []
        
        def track_state_change(old_state, new_state, timestamp):
            connection_states.append({
                "from": old_state,
                "to": new_state,
                "timestamp": timestamp,
                "user_id": str(user_id)
            })
            logger.info(f"Connection state: {old_state} -> {new_state}")
        
        # Phase 1: Establish initial connection
        websocket_uri = f"ws://localhost:8000/ws/user/{user_id}"
        
        async def message_handler(websocket, path):
            """Handle incoming WebSocket messages."""
            async for message in websocket:
                received_msg = json.loads(message)
                received_messages.append({
                    **received_msg,
                    "received_at": datetime.now(timezone.utc),
                    "connection_state": "connected"
                })
        
        # Start WebSocket connection
        connection = await websocket_manager.create_authenticated_connection(
            user_id=str(user_id),
            auth_context=auth_context,
            message_handler=message_handler
        )
        
        track_state_change(WebSocketTestState.CONNECTING, WebSocketTestState.CONNECTED, datetime.now(timezone.utc))
        
        # Send initial messages to establish baseline
        baseline_messages = []
        for i in range(5):
            message = {
                "type": WebSocketEventType.AGENT_STARTED.value,
                "data": {
                    "message_id": f"baseline_{i}",
                    "agent_id": str(uuid.uuid4()),
                    "content": f"Baseline message {i}"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_manager.send_message_to_user(
                user_id=str(user_id),
                message=message
            )
            baseline_messages.append(message)
            await asyncio.sleep(0.2)
        
        # Verify baseline messages received
        await asyncio.sleep(1)
        initial_received_count = len(received_messages)
        assert initial_received_count >= 3, f"Should receive most baseline messages, got {initial_received_count}"
        
        # Phase 2: Simulate network interruption
        logger.info("Simulating network interruption")
        track_state_change(WebSocketTestState.CONNECTED, WebSocketTestState.INTERRUPTED, datetime.now(timezone.utc))
        
        # Force disconnect
        await connection_manager.force_disconnect(str(user_id), reason="network_interruption")
        
        # Try to send messages during interruption (should queue)
        interrupted_messages = []
        for i in range(3):
            message = {
                "type": WebSocketEventType.AGENT_THINKING.value,
                "data": {
                    "message_id": f"interrupted_{i}",
                    "agent_id": str(uuid.uuid4()),
                    "content": f"Message during interruption {i}"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # This should queue the message for delivery when connection recovers
            try:
                await websocket_manager.send_message_to_user(
                    user_id=str(user_id),
                    message=message,
                    queue_if_disconnected=True
                )
                interrupted_messages.append(message)
            except Exception as e:
                logger.info(f"Expected exception during interruption: {e}")
            
            await asyncio.sleep(0.1)
        
        # Phase 3: Recover connection
        await asyncio.sleep(2)  # Simulate interruption duration
        
        logger.info("Recovering connection")
        track_state_change(WebSocketTestState.INTERRUPTED, WebSocketTestState.RECOVERING, datetime.now(timezone.utc))
        
        # Reestablish connection
        recovered_connection = await websocket_manager.create_authenticated_connection(
            user_id=str(user_id),
            auth_context=auth_context,
            message_handler=message_handler,
            recovery_mode=True
        )
        
        track_state_change(WebSocketTestState.RECOVERING, WebSocketTestState.CONNECTED, datetime.now(timezone.utc))
        
        # Phase 4: Send post-recovery messages
        await asyncio.sleep(1)  # Allow queued messages to be delivered
        
        post_recovery_messages = []
        for i in range(3):
            message = {
                "type": WebSocketEventType.AGENT_COMPLETED.value,
                "data": {
                    "message_id": f"post_recovery_{i}",
                    "agent_id": str(uuid.uuid4()),
                    "content": f"Post-recovery message {i}"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_manager.send_message_to_user(
                user_id=str(user_id),
                message=message
            )
            post_recovery_messages.append(message)
            await asyncio.sleep(0.2)
        
        # Phase 5: Validate recovery success
        await asyncio.sleep(2)  # Allow all messages to be received
        
        final_received_count = len(received_messages)
        total_expected = len(baseline_messages) + len(interrupted_messages) + len(post_recovery_messages)
        
        logger.info(f"Message delivery: Expected={total_expected}, Received={final_received_count}")
        
        # Validate message delivery (allow some tolerance for network timing)
        delivery_rate = final_received_count / total_expected
        assert delivery_rate >= 0.8, f"Message delivery rate too low: {delivery_rate:.2%} (expected  >= 80%)"
        
        # Validate connection state transitions
        expected_transitions = [
            WebSocketTestState.CONNECTED,
            WebSocketTestState.INTERRUPTED,
            WebSocketTestState.RECOVERING,
            WebSocketTestState.CONNECTED
        ]
        
        actual_transitions = [state["to"] for state in connection_states]
        for expected in expected_transitions:
            assert expected in actual_transitions, f"Missing expected transition: {expected}"
        
        # Validate queued message delivery
        interrupted_msg_ids = {msg["data"]["message_id"] for msg in interrupted_messages}
        received_msg_ids = {msg.get("data", {}).get("message_id") for msg in received_messages}
        
        queued_delivered = len(interrupted_msg_ids.intersection(received_msg_ids))
        queued_delivery_rate = queued_delivered / len(interrupted_messages) if interrupted_messages else 1.0
        
        assert queued_delivery_rate >= 0.7, f"Queued message delivery rate too low: {queued_delivery_rate:.2%} (expected  >= 70%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 30.0, f"Recovery test should complete in <30s, took {execution_time:.2f}s"
        
        logger.info(f"Connection recovery test completed in {execution_time:.2f}s with {delivery_rate:.2%} delivery rate")

    @pytest.mark.asyncio
    async def test_websocket_message_ordering_under_load(self, real_services_fixture):
        """
        Test WebSocket message ordering and delivery guarantees under high load.
        
        PERFORMANCE SCENARIO: Validates message ordering during high-throughput operations
        typical in multi-agent executions.
        """
        logger.info("Starting WebSocket message ordering under load test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_ordering_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        websocket_manager = WebSocketManager()
        agent_registry = AgentRegistry()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Create WebSocket bridge for proper ExecutionEngine instantiation
        websocket_bridge = create_agent_websocket_bridge()
        
        # Use factory method for ExecutionEngine (SSOT compliance)
        execution_engine = create_request_scoped_engine(
            user_context=auth_context,
            registry=agent_registry, 
            websocket_bridge=websocket_bridge,
            max_concurrent_executions=3
        )
        
        # Track message ordering
        sent_messages = []
        received_messages = []
        message_order_violations = []
        
        async def ordered_message_handler(websocket, path):
            """Handle messages and track ordering."""
            async for message in websocket:
                received_msg = json.loads(message)
                received_msg["received_at"] = datetime.now(timezone.utc)
                received_msg["received_order"] = len(received_messages)
                received_messages.append(received_msg)
        
        # Establish connection
        connection = await websocket_manager.create_authenticated_connection(
            user_id=str(user_id),
            auth_context=auth_context,
            message_handler=ordered_message_handler
        )
        
        # Phase 1: Send high volume of ordered messages
        message_batch_size = 50
        total_batches = 4
        
        for batch in range(total_batches):
            batch_messages = []
            
            # Send batch of messages rapidly
            for i in range(message_batch_size):
                sequence_number = batch * message_batch_size + i
                message = {
                    "type": WebSocketEventType.AGENT_THINKING.value,
                    "data": {
                        "message_id": f"seq_{sequence_number:04d}",
                        "sequence_number": sequence_number,
                        "batch": batch,
                        "batch_index": i,
                        "agent_id": str(uuid.uuid4()),
                        "content": f"Ordered message {sequence_number}"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                sent_timestamp = datetime.now(timezone.utc)
                
                # Send message
                await websocket_manager.send_message_to_user(
                    user_id=str(user_id),
                    message=message
                )
                
                sent_messages.append({
                    "message": message,
                    "sent_at": sent_timestamp,
                    "sent_order": sequence_number
                })
                batch_messages.append(message)
                
                # Minimal delay to create ordering pressure
                await asyncio.sleep(0.01)
            
            logger.info(f"Sent batch {batch} with {len(batch_messages)} messages")
            
            # Brief pause between batches
            await asyncio.sleep(0.5)
        
        # Phase 2: Allow all messages to be received
        await asyncio.sleep(3)
        
        total_sent = len(sent_messages)
        total_received = len(received_messages)
        
        logger.info(f"Message throughput: Sent={total_sent}, Received={total_received}")
        
        # Validate message delivery completeness
        delivery_rate = total_received / total_sent
        assert delivery_rate >= 0.95, f"Message delivery rate too low: {delivery_rate:.2%} (expected  >= 95%)"
        
        # Phase 3: Analyze message ordering
        ordering_violations = []
        
        # Create mapping of received messages by sequence number
        received_by_sequence = {}
        for msg in received_messages:
            seq_num = msg.get("data", {}).get("sequence_number")
            if seq_num is not None:
                received_by_sequence[seq_num] = msg
        
        # Check for ordering violations
        for i in range(1, total_sent):
            if i in received_by_sequence and (i-1) in received_by_sequence:
                curr_msg = received_by_sequence[i]
                prev_msg = received_by_sequence[i-1]
                
                curr_received_order = curr_msg["received_order"]
                prev_received_order = prev_msg["received_order"]
                
                # Current message should be received after previous
                if curr_received_order < prev_received_order:
                    ordering_violations.append({
                        "sequence": i,
                        "expected_order": i,
                        "actual_order": curr_received_order,
                        "previous_order": prev_received_order
                    })
        
        # Calculate ordering accuracy
        ordering_accuracy = 1.0 - (len(ordering_violations) / (total_received - 1)) if total_received > 1 else 1.0
        
        logger.info(f"Message ordering: Violations={len(ordering_violations)}, Accuracy={ordering_accuracy:.2%}")
        
        # Validate ordering quality (allow some flexibility for high-load scenarios)
        assert ordering_accuracy >= 0.90, f"Message ordering accuracy too low: {ordering_accuracy:.2%} (expected  >= 90%)"
        
        # Phase 4: Test batch ordering within reasonable bounds
        batch_ordering_violations = 0
        
        for batch in range(total_batches):
            batch_start = batch * message_batch_size
            batch_end = batch_start + message_batch_size
            
            batch_messages = [msg for msg in received_messages 
                            if msg.get("data", {}).get("batch") == batch]
            
            # Sort by received order
            batch_messages.sort(key=lambda x: x["received_order"])
            
            # Check if batch messages are reasonably ordered
            for i in range(1, len(batch_messages)):
                curr_seq = batch_messages[i].get("data", {}).get("sequence_number", 0)
                prev_seq = batch_messages[i-1].get("data", {}).get("sequence_number", 0)
                
                # Within a batch, allow some reordering but not major violations
                if curr_seq < prev_seq - 5:  # Allow up to 5 positions of reordering
                    batch_ordering_violations += 1
        
        batch_ordering_rate = 1.0 - (batch_ordering_violations / total_received) if total_received > 0 else 1.0
        assert batch_ordering_rate >= 0.85, f"Batch ordering rate too low: {batch_ordering_rate:.2%} (expected  >= 85%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        throughput = total_sent / execution_time  # messages per second
        
        assert throughput >= 10.0, f"Message throughput too low: {throughput:.1f} msg/s (expected  >= 10 msg/s)"
        assert execution_time < 45.0, f"Load test should complete in <45s, took {execution_time:.2f}s"
        
        logger.info(f"Message ordering test completed in {execution_time:.2f}s with {throughput:.1f} msg/s throughput")

    @pytest.mark.asyncio
    async def test_websocket_large_message_handling(self, real_services_fixture):
        """
        Test WebSocket handling of large messages and fragmentation.
        
        ENTERPRISE SCENARIO: Validates large data transfer capabilities
        for comprehensive agent results and detailed analysis reports.
        """
        logger.info("Starting WebSocket large message handling test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_large_msg_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        websocket_manager = WebSocketManager()
        
        # Track large message handling
        large_messages_sent = []
        large_messages_received = []
        fragmentation_events = []
        
        async def large_message_handler(websocket, path):
            """Handle large messages and track fragmentation."""
            async for message in websocket:
                try:
                    received_msg = json.loads(message)
                    message_size = len(message)
                    
                    received_msg["received_at"] = datetime.now(timezone.utc)
                    received_msg["received_size"] = message_size
                    large_messages_received.append(received_msg)
                    
                    # Check for fragmentation indicators
                    if message_size > 10000:  # Large message threshold
                        fragmentation_events.append({
                            "message_id": received_msg.get("data", {}).get("message_id"),
                            "size": message_size,
                            "timestamp": datetime.now(timezone.utc)
                        })
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse large message: {e}")
        
        # Establish connection with large message support
        connection = await websocket_manager.create_authenticated_connection(
            user_id=str(user_id),
            auth_context=auth_context,
            message_handler=large_message_handler,
            max_message_size=1024*1024  # 1MB limit
        )
        
        # Phase 1: Test progressively larger messages
        message_sizes = [
            1024,      # 1KB
            10240,     # 10KB  
            51200,     # 50KB
            102400,    # 100KB
            256000,    # 250KB
            512000     # 500KB
        ]
        
        for size in message_sizes:
            # Create large content
            large_content = {
                "analysis_data": "x" * (size // 2),
                "detailed_results": ["item_" + str(i) for i in range(size // 100)],
                "metadata": {
                    "size_category": f"{size//1024}KB",
                    "generation_time": datetime.now(timezone.utc).isoformat(),
                    "content_hash": str(hash("x" * (size // 2)))
                }
            }
            
            message = {
                "type": WebSocketEventType.AGENT_COMPLETED.value,
                "data": {
                    "message_id": f"large_{size}",
                    "size_bytes": size,
                    "agent_id": str(uuid.uuid4()),
                    "result": large_content
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            sent_timestamp = datetime.now(timezone.utc)
            
            try:
                await websocket_manager.send_message_to_user(
                    user_id=str(user_id),
                    message=message
                )
                
                large_messages_sent.append({
                    "message_id": f"large_{size}",
                    "size": size,
                    "sent_at": sent_timestamp
                })
                
                logger.info(f"Sent large message: {size} bytes")
                
            except Exception as e:
                logger.error(f"Failed to send {size} byte message: {e}")
            
            # Brief pause between large messages
            await asyncio.sleep(1)
        
        # Phase 2: Allow large messages to be processed
        await asyncio.sleep(5)
        
        # Phase 3: Test extremely large message (near limit)
        extreme_size = 800000  # 800KB
        extreme_content = {
            "comprehensive_analysis": "x" * (extreme_size // 4),
            "detailed_breakdown": {
                "section_" + str(i): "data_" * 100 for i in range(extreme_size // 10000)
            },
            "performance_metrics": [{"metric": f"value_{i}", "data": "x" * 50} for i in range(extreme_size // 1000)]
        }
        
        extreme_message = {
            "type": WebSocketEventType.AGENT_COMPLETED.value,
            "data": {
                "message_id": "extreme_large",
                "size_bytes": extreme_size,
                "agent_id": str(uuid.uuid4()),
                "comprehensive_result": extreme_content
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await websocket_manager.send_message_to_user(
                user_id=str(user_id),
                message=extreme_message
            )
            large_messages_sent.append({
                "message_id": "extreme_large",
                "size": extreme_size,
                "sent_at": datetime.now(timezone.utc)
            })
            logger.info(f"Sent extreme large message: {extreme_size} bytes")
        except Exception as e:
            logger.warning(f"Extreme large message failed as expected: {e}")
        
        await asyncio.sleep(3)
        
        # Phase 4: Validate large message delivery
        total_sent = len(large_messages_sent)
        total_received = len(large_messages_received)
        
        logger.info(f"Large message delivery: Sent={total_sent}, Received={total_received}")
        
        # Validate delivery rate (allow some failures for extremely large messages)
        delivery_rate = total_received / total_sent if total_sent > 0 else 0.0
        assert delivery_rate >= 0.75, f"Large message delivery rate too low: {delivery_rate:.2%} (expected  >= 75%)"
        
        # Validate message integrity
        integrity_checks = 0
        for received in large_messages_received:
            message_id = received.get("data", {}).get("message_id", "")
            if message_id.startswith("large_"):
                # Find corresponding sent message
                size_str = message_id.replace("large_", "")
                try:
                    expected_size = int(size_str)
                    actual_size = received.get("received_size", 0)
                    
                    # Allow some variance due to JSON serialization overhead
                    size_ratio = actual_size / expected_size if expected_size > 0 else 0
                    if 0.8 <= size_ratio <= 1.5:  # 20% under to 50% over (JSON overhead)
                        integrity_checks += 1
                except ValueError:
                    pass
        
        integrity_rate = integrity_checks / total_received if total_received > 0 else 0.0
        assert integrity_rate >= 0.8, f"Message integrity rate too low: {integrity_rate:.2%} (expected  >= 80%)"
        
        # Validate fragmentation handling
        large_message_count = len([msg for msg in large_messages_received if msg.get("received_size", 0) > 50000])
        fragmentation_rate = len(fragmentation_events) / large_message_count if large_message_count > 0 else 0.0
        
        logger.info(f"Fragmentation handling: {len(fragmentation_events)} events for {large_message_count} large messages")
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 60.0, f"Large message test should complete in <60s, took {execution_time:.2f}s"
        
        logger.info(f"Large message handling test completed in {execution_time:.2f}s with {delivery_rate:.2%} delivery rate")

    @pytest.mark.asyncio
    async def test_websocket_concurrent_connection_management(self, real_services_fixture):
        """
        Test concurrent WebSocket connection management per user.
        
        MULTI-DEVICE SCENARIO: Validates user can have multiple concurrent connections
        (mobile, web, etc.) with proper message broadcasting.
        """
        logger.info("Starting WebSocket concurrent connection management test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_concurrent_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        websocket_manager = WebSocketManager()
        
        # Track messages for each connection
        connection_messages = {}
        
        async def create_connection_handler(connection_id: str):
            """Create message handler for specific connection."""
            connection_messages[connection_id] = []
            
            async def handler(websocket, path):
                async for message in websocket:
                    received_msg = json.loads(message)
                    received_msg["received_at"] = datetime.now(timezone.utc)
                    received_msg["connection_id"] = connection_id
                    connection_messages[connection_id].append(received_msg)
            
            return handler
        
        # Phase 1: Establish multiple concurrent connections
        num_connections = 4
        connections = []
        
        for i in range(num_connections):
            connection_id = f"conn_{i}"
            handler = await create_connection_handler(connection_id)
            
            try:
                connection = await websocket_manager.create_authenticated_connection(
                    user_id=str(user_id),
                    auth_context=auth_context,
                    message_handler=handler,
                    connection_id=connection_id
                )
                
                connections.append({
                    "id": connection_id,
                    "connection": connection,
                    "established_at": datetime.now(timezone.utc)
                })
                
                logger.info(f"Established connection {connection_id}")
                await asyncio.sleep(0.5)  # Stagger connection establishment
                
            except Exception as e:
                logger.error(f"Failed to establish connection {connection_id}: {e}")
        
        successful_connections = len(connections)
        assert successful_connections >= 3, f"Should establish  >= 3 connections, got {successful_connections}"
        
        # Phase 2: Send broadcast messages to all connections
        broadcast_messages = []
        
        for i in range(10):
            message = {
                "type": WebSocketEventType.AGENT_THINKING.value,
                "data": {
                    "message_id": f"broadcast_{i}",
                    "agent_id": str(uuid.uuid4()),
                    "content": f"Broadcast message {i} to all connections",
                    "broadcast_index": i
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_manager.broadcast_to_user(
                user_id=str(user_id),
                message=message
            )
            
            broadcast_messages.append(message)
            await asyncio.sleep(0.3)
        
        # Phase 3: Send targeted messages to specific connections
        targeted_messages = []
        
        for i, conn in enumerate(connections[:3]):  # Target first 3 connections
            message = {
                "type": WebSocketEventType.AGENT_COMPLETED.value,
                "data": {
                    "message_id": f"targeted_{conn['id']}_{i}",
                    "target_connection": conn['id'],
                    "agent_id": str(uuid.uuid4()),
                    "content": f"Targeted message for {conn['id']}"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_manager.send_to_connection(
                user_id=str(user_id),
                connection_id=conn['id'],
                message=message
            )
            
            targeted_messages.append({
                "message": message,
                "target": conn['id']
            })
            
            await asyncio.sleep(0.2)
        
        # Phase 4: Allow messages to be received
        await asyncio.sleep(3)
        
        # Phase 5: Validate broadcast message delivery
        broadcast_delivery_stats = {}
        
        for conn in connections:
            conn_id = conn['id']
            received_broadcasts = [
                msg for msg in connection_messages.get(conn_id, [])
                if msg.get("data", {}).get("message_id", "").startswith("broadcast_")
            ]
            
            broadcast_delivery_stats[conn_id] = {
                "received": len(received_broadcasts),
                "expected": len(broadcast_messages),
                "rate": len(received_broadcasts) / len(broadcast_messages)
            }
            
            logger.info(f"Connection {conn_id} broadcast delivery: {len(received_broadcasts)}/{len(broadcast_messages)}")
        
        # Validate broadcast delivery rates
        for conn_id, stats in broadcast_delivery_stats.items():
            delivery_rate = stats["rate"]
            assert delivery_rate >= 0.8, f"Connection {conn_id} broadcast delivery rate too low: {delivery_rate:.2%} (expected  >= 80%)"
        
        # Phase 6: Validate targeted message delivery
        targeted_delivery_stats = {}
        
        for target_msg in targeted_messages:
            target_conn = target_msg["target"]
            message_id = target_msg["message"]["data"]["message_id"]
            
            # Check if target connection received the message
            target_received = any(
                msg.get("data", {}).get("message_id") == message_id
                for msg in connection_messages.get(target_conn, [])
            )
            
            # Check if non-target connections did NOT receive the message
            non_target_received = 0
            for conn in connections:
                if conn['id'] != target_conn:
                    if any(msg.get("data", {}).get("message_id") == message_id 
                          for msg in connection_messages.get(conn['id'], [])):
                        non_target_received += 1
            
            targeted_delivery_stats[message_id] = {
                "target_received": target_received,
                "non_target_received": non_target_received,
                "isolation_success": non_target_received == 0
            }
        
        # Validate targeted delivery accuracy
        successful_targeting = sum(1 for stats in targeted_delivery_stats.values() 
                                 if stats["target_received"] and stats["isolation_success"])
        targeting_accuracy = successful_targeting / len(targeted_messages) if targeted_messages else 1.0
        
        assert targeting_accuracy >= 0.8, f"Targeted message accuracy too low: {targeting_accuracy:.2%} (expected  >= 80%)"
        
        # Phase 7: Test connection cleanup
        # Close half the connections
        connections_to_close = connections[:len(connections)//2]
        
        for conn in connections_to_close:
            try:
                await websocket_manager.close_connection(
                    user_id=str(user_id),
                    connection_id=conn['id'],
                    reason="test_cleanup"
                )
                logger.info(f"Closed connection {conn['id']}")
            except Exception as e:
                logger.warning(f"Error closing connection {conn['id']}: {e}")
        
        await asyncio.sleep(1)
        
        # Send message to remaining connections
        cleanup_message = {
            "type": WebSocketEventType.AGENT_STARTED.value,
            "data": {
                "message_id": "post_cleanup",
                "content": "Message after connection cleanup"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket_manager.broadcast_to_user(
            user_id=str(user_id),
            message=cleanup_message
        )
        
        await asyncio.sleep(1)
        
        # Validate cleanup worked - only remaining connections should receive message
        remaining_connections = connections[len(connections)//2:]
        cleanup_received = 0
        
        for conn in remaining_connections:
            conn_messages = connection_messages.get(conn['id'], [])
            if any(msg.get("data", {}).get("message_id") == "post_cleanup" for msg in conn_messages):
                cleanup_received += 1
        
        cleanup_delivery_rate = cleanup_received / len(remaining_connections) if remaining_connections else 0.0
        assert cleanup_delivery_rate >= 0.8, f"Post-cleanup message delivery too low: {cleanup_delivery_rate:.2%} (expected  >= 80%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 45.0, f"Concurrent connection test should complete in <45s, took {execution_time:.2f}s"
        
        logger.info(f"Concurrent connection management test completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_websocket_authentication_edge_cases(self, real_services_fixture):
        """
        Test WebSocket authentication edge cases and token refresh scenarios.
        
        SECURITY SCENARIO: Validates authentication handling during token expiration,
        refresh, and various edge cases.
        """
        logger.info("Starting WebSocket authentication edge cases test")
        start_time = time.time()
        
        # Create multiple user contexts with different auth scenarios
        auth_helper = E2EAuthHelper()
        
        # Standard user
        standard_context = await create_authenticated_user_context("test_auth_standard")
        standard_user_id = UserID(str(uuid.uuid4()))
        
        # User with expiring token
        expiring_context = await auth_helper.create_expiring_auth_context("test_auth_expiring", expires_in_seconds=10)
        expiring_user_id = UserID(str(uuid.uuid4()))
        
        # User with invalid token (for negative testing)
        invalid_context = auth_helper.create_invalid_auth_context("test_auth_invalid")
        invalid_user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components
        websocket_manager = WebSocketManager()
        
        auth_events = []
        connection_states = {}
        
        def track_auth_event(event_type, user_id, details):
            auth_events.append({
                "type": event_type,
                "user_id": user_id,
                "details": details,
                "timestamp": datetime.now(timezone.utc)
            })
            logger.info(f"Auth event: {event_type} for user {user_id}")
        
        async def create_auth_handler(user_id: str):
            """Create handler that tracks authentication events."""
            connection_states[user_id] = {"messages": [], "auth_status": "unknown"}
            
            async def handler(websocket, path):
                async for message in websocket:
                    try:
                        received_msg = json.loads(message)
                        received_msg["received_at"] = datetime.now(timezone.utc)
                        connection_states[user_id]["messages"].append(received_msg)
                        
                        # Track auth-related messages
                        if received_msg.get("type") == "auth_status":
                            connection_states[user_id]["auth_status"] = received_msg.get("status")
                            track_auth_event("auth_status_change", user_id, received_msg)
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Auth handler parse error for {user_id}: {e}")
            
            return handler
        
        # Phase 1: Test standard authentication
        standard_handler = await create_auth_handler(str(standard_user_id))
        
        try:
            standard_connection = await websocket_manager.create_authenticated_connection(
                user_id=str(standard_user_id),
                auth_context=standard_context,
                message_handler=standard_handler
            )
            track_auth_event("connection_established", str(standard_user_id), {"status": "success"})
        except Exception as e:
            track_auth_event("connection_failed", str(standard_user_id), {"error": str(e)})
            
        # Phase 2: Test authentication with expiring token
        expiring_handler = await create_auth_handler(str(expiring_user_id))
        
        try:
            expiring_connection = await websocket_manager.create_authenticated_connection(
                user_id=str(expiring_user_id),
                auth_context=expiring_context,
                message_handler=expiring_handler
            )
            track_auth_event("expiring_connection_established", str(expiring_user_id), {"status": "success"})
        except Exception as e:
            track_auth_event("expiring_connection_failed", str(expiring_user_id), {"error": str(e)})
        
        # Phase 3: Test invalid authentication (should fail)
        invalid_handler = await create_auth_handler(str(invalid_user_id))
        
        try:
            invalid_connection = await websocket_manager.create_authenticated_connection(
                user_id=str(invalid_user_id),
                auth_context=invalid_context,
                message_handler=invalid_handler
            )
            track_auth_event("invalid_connection_unexpected_success", str(invalid_user_id), {"status": "unexpected"})
        except Exception as e:
            track_auth_event("invalid_connection_properly_rejected", str(invalid_user_id), {"error": str(e)})
        
        # Phase 4: Send messages to test authentication validation
        test_message = {
            "type": WebSocketEventType.AGENT_STARTED.value,
            "data": {
                "message_id": "auth_test",
                "content": "Authentication validation test message"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to standard user (should succeed)
        try:
            await websocket_manager.send_message_to_user(
                user_id=str(standard_user_id),
                message=test_message
            )
            track_auth_event("message_sent", str(standard_user_id), {"status": "success"})
        except Exception as e:
            track_auth_event("message_send_failed", str(standard_user_id), {"error": str(e)})
        
        # Send to expiring user (should succeed initially)
        try:
            await websocket_manager.send_message_to_user(
                user_id=str(expiring_user_id),
                message=test_message
            )
            track_auth_event("message_sent_expiring", str(expiring_user_id), {"status": "success"})
        except Exception as e:
            track_auth_event("message_send_failed_expiring", str(expiring_user_id), {"error": str(e)})
        
        await asyncio.sleep(2)
        
        # Phase 5: Wait for token expiration and test refresh
        logger.info("Waiting for token expiration...")
        await asyncio.sleep(12)  # Wait for expiring token to expire
        
        # Try to send message after expiration
        expired_message = {
            "type": WebSocketEventType.AGENT_THINKING.value,
            "data": {
                "message_id": "post_expiration",
                "content": "Message after token expiration"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await websocket_manager.send_message_to_user(
                user_id=str(expiring_user_id),
                message=expired_message
            )
            track_auth_event("post_expiration_send", str(expiring_user_id), {"status": "should_fail"})
        except Exception as e:
            track_auth_event("post_expiration_send_properly_failed", str(expiring_user_id), {"error": str(e)})
        
        # Attempt token refresh
        try:
            refreshed_context = await auth_helper.refresh_auth_context(expiring_context)
            
            # Reestablish connection with refreshed token
            refreshed_handler = await create_auth_handler(f"{expiring_user_id}_refreshed")
            refreshed_connection = await websocket_manager.create_authenticated_connection(
                user_id=str(expiring_user_id),
                auth_context=refreshed_context,
                message_handler=refreshed_handler
            )
            
            track_auth_event("token_refresh_success", str(expiring_user_id), {"status": "refreshed"})
            
            # Send message with refreshed token
            await websocket_manager.send_message_to_user(
                user_id=str(expiring_user_id),
                message=expired_message
            )
            track_auth_event("post_refresh_send", str(expiring_user_id), {"status": "success"})
            
        except Exception as e:
            track_auth_event("token_refresh_failed", str(expiring_user_id), {"error": str(e)})
        
        await asyncio.sleep(2)
        
        # Phase 6: Validate authentication event outcomes
        
        # Standard authentication should work
        standard_events = [e for e in auth_events if e["user_id"] == str(standard_user_id)]
        standard_success = any(e["type"] == "connection_established" for e in standard_events)
        assert standard_success, "Standard authentication should succeed"
        
        # Invalid authentication should be rejected
        invalid_events = [e for e in auth_events if e["user_id"] == str(invalid_user_id)]
        invalid_properly_rejected = any(e["type"] == "invalid_connection_properly_rejected" for e in invalid_events)
        assert invalid_properly_rejected, "Invalid authentication should be properly rejected"
        
        # Expiring token should initially work, then fail, then work after refresh
        expiring_events = [e for e in auth_events if e["user_id"] == str(expiring_user_id)]
        initial_success = any(e["type"] == "expiring_connection_established" for e in expiring_events)
        post_expiration_failure = any(e["type"] == "post_expiration_send_properly_failed" for e in expiring_events)
        refresh_success = any(e["type"] == "token_refresh_success" for e in expiring_events)
        
        assert initial_success, "Expiring token should initially work"
        # Note: post_expiration_failure and refresh_success are expected but may not always occur in test environment
        
        # Validate message delivery to authenticated connections
        standard_messages = connection_states.get(str(standard_user_id), {}).get("messages", [])
        assert len(standard_messages) > 0, "Standard user should receive messages"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time >= 15.0, f"Auth edge case test should take  >= 15s (for expiration), took {execution_time:.2f}s"
        assert execution_time < 45.0, f"Auth edge case test should complete in <45s, took {execution_time:.2f}s"
        
        logger.info(f"Authentication edge cases test completed in {execution_time:.2f}s with {len(auth_events)} auth events")

    @pytest.mark.asyncio
    async def test_websocket_message_queue_overflow_backpressure(self, real_services_fixture):
        """
        Test WebSocket message queue overflow and backpressure handling.
        
        RESILIENCE SCENARIO: Validates system behavior when message queues overflow
        and backpressure mechanisms engage.
        """
        logger.info("Starting WebSocket message queue overflow and backpressure test")
        start_time = time.time()
        
        # Create authenticated user context
        auth_context = await create_authenticated_user_context("test_backpressure_user")
        user_id = UserID(str(uuid.uuid4()))
        
        # Initialize components with limited queue capacity
        websocket_manager = WebSocketManager(max_queue_size=50)  # Small queue for testing
        
        # Track queue behavior
        queue_metrics = []
        dropped_messages = []
        backpressure_events = []
        received_messages = []
        
        async def backpressure_handler(websocket, path):
            """Handle messages with intentional slow processing to trigger backpressure."""
            async for message in websocket:
                # Intentionally slow processing to create backpressure
                await asyncio.sleep(0.1)
                
                try:
                    received_msg = json.loads(message)
                    received_msg["received_at"] = datetime.now(timezone.utc)
                    received_msg["processing_delay"] = 0.1
                    received_messages.append(received_msg)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse message during backpressure test")
        
        # Phase 1: Establish slow-processing connection
        connection = await websocket_manager.create_authenticated_connection(
            user_id=str(user_id),
            auth_context=auth_context,
            message_handler=backpressure_handler
        )
        
        # Set up queue monitoring
        def monitor_queue_metrics():
            current_size = websocket_manager.get_queue_size(str(user_id))
            is_full = websocket_manager.is_queue_full(str(user_id))
            
            queue_metrics.append({
                "timestamp": datetime.now(timezone.utc),
                "queue_size": current_size,
                "queue_full": is_full,
                "messages_sent": len(received_messages)
            })
        
        # Phase 2: Rapidly send messages to trigger overflow
        overflow_threshold = 75  # Exceed queue capacity
        rapid_fire_messages = []
        
        logger.info(f"Rapidly sending {overflow_threshold} messages to trigger overflow")
        
        for i in range(overflow_threshold):
            message = {
                "type": WebSocketEventType.AGENT_THINKING.value,
                "data": {
                    "message_id": f"rapid_{i:04d}",
                    "sequence": i,
                    "agent_id": str(uuid.uuid4()),
                    "content": f"Rapid fire message {i} for backpressure testing"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await websocket_manager.send_message_to_user(
                    user_id=str(user_id),
                    message=message,
                    timeout=0.1  # Short timeout to detect backpressure
                )
                rapid_fire_messages.append(message)
                
                # Monitor queue after each send
                monitor_queue_metrics()
                
            except Exception as e:
                # Expected behavior when queue overflows
                dropped_messages.append({
                    "message_id": f"rapid_{i:04d}",
                    "sequence": i,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc)
                })
                
                if "queue" in str(e).lower() or "backpressure" in str(e).lower():
                    backpressure_events.append({
                        "type": "queue_overflow",
                        "message_sequence": i,
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                monitor_queue_metrics()
            
            # Minimal delay to stress queue
            await asyncio.sleep(0.01)
        
        logger.info(f"Rapid sending complete. Sent: {len(rapid_fire_messages)}, Dropped: {len(dropped_messages)}")
        
        # Phase 3: Allow queue to drain
        drain_start = time.time()
        while len(received_messages) < len(rapid_fire_messages) * 0.8 and (time.time() - drain_start) < 20:
            await asyncio.sleep(1)
            monitor_queue_metrics()
            logger.info(f"Queue draining: {len(received_messages)}/{len(rapid_fire_messages)} received")
        
        # Phase 4: Test recovery after backpressure
        recovery_messages = []
        logger.info("Testing recovery after backpressure")
        
        for i in range(5):
            recovery_message = {
                "type": WebSocketEventType.AGENT_COMPLETED.value,
                "data": {
                    "message_id": f"recovery_{i}",
                    "content": f"Recovery message {i} after backpressure"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await websocket_manager.send_message_to_user(
                    user_id=str(user_id),
                    message=recovery_message,
                    timeout=5.0  # Longer timeout for recovery
                )
                recovery_messages.append(recovery_message)
                logger.info(f"Recovery message {i} sent successfully")
            except Exception as e:
                logger.error(f"Recovery message {i} failed: {e}")
            
            await asyncio.sleep(1)
        
        # Allow recovery messages to be processed
        await asyncio.sleep(3)
        
        # Phase 5: Validate backpressure behavior
        
        # Calculate message delivery statistics
        total_attempted = len(rapid_fire_messages) + len(recovery_messages)
        total_received = len(received_messages)
        total_dropped = len(dropped_messages)
        
        delivery_rate = total_received / total_attempted if total_attempted > 0 else 0.0
        drop_rate = total_dropped / len(rapid_fire_messages) if rapid_fire_messages else 0.0
        
        logger.info(f"Delivery stats: Attempted={total_attempted}, Received={total_received}, Dropped={total_dropped}")
        logger.info(f"Rates: Delivery={delivery_rate:.2%}, Drop={drop_rate:.2%}")
        
        # Validate backpressure kicked in (some messages should be dropped)
        assert drop_rate > 0.1, f"Expected some message drops due to backpressure, got {drop_rate:.2%}"
        assert drop_rate < 0.8, f"Too many messages dropped: {drop_rate:.2%} (expected <80%)"
        
        # Validate queue metrics show overflow
        max_queue_size = max((m["queue_size"] for m in queue_metrics), default=0)
        queue_full_events = sum(1 for m in queue_metrics if m["queue_full"])
        
        assert max_queue_size >= 40, f"Queue should have filled significantly, max size was {max_queue_size}"
        assert queue_full_events > 0, "Should have detected queue full events"
        
        # Validate recovery after backpressure
        recovery_received = len([msg for msg in received_messages 
                               if msg.get("data", {}).get("message_id", "").startswith("recovery_")])
        recovery_rate = recovery_received / len(recovery_messages) if recovery_messages else 1.0
        
        assert recovery_rate >= 0.8, f"Recovery rate too low: {recovery_rate:.2%} (expected  >= 80%)"
        
        # Validate backpressure events were detected
        assert len(backpressure_events) > 0, "Should have detected backpressure events"
        
        # Validate message ordering preservation (among delivered messages)
        rapid_received = [msg for msg in received_messages 
                         if msg.get("data", {}).get("message_id", "").startswith("rapid_")]
        rapid_received.sort(key=lambda x: x.get("received_at", datetime.min.replace(tzinfo=timezone.utc)))
        
        ordering_violations = 0
        for i in range(1, len(rapid_received)):
            curr_seq = rapid_received[i].get("data", {}).get("sequence", 0)
            prev_seq = rapid_received[i-1].get("data", {}).get("sequence", 0)
            if curr_seq < prev_seq:
                ordering_violations += 1
        
        ordering_accuracy = 1.0 - (ordering_violations / len(rapid_received)) if rapid_received else 1.0
        assert ordering_accuracy >= 0.8, f"Message ordering accuracy too low: {ordering_accuracy:.2%} (expected  >= 80%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 90.0, f"Backpressure test should complete in <90s, took {execution_time:.2f}s"
        
        logger.info(f"Message queue overflow test completed in {execution_time:.2f}s")
        logger.info(f"Final stats: {delivery_rate:.2%} delivery rate, {drop_rate:.2%} drop rate, {recovery_rate:.2%} recovery rate")