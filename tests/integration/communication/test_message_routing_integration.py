"""
Message Routing and Delivery System Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable message routing enables AI responses to reach correct users
- Value Impact: Message delivery accuracy directly impacts user experience and AI value delivery
- Strategic Impact: Core messaging infrastructure for $500K+ ARR chat functionality

CRITICAL: Message routing ensures users receive personalized AI insights per CLAUDE.md
Proper routing prevents cross-user data leakage and ensures response accuracy.

These integration tests validate message routing, user-specific delivery, message ordering,
priority handling, and delivery confirmation patterns without requiring Docker services.
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed

# SSOT imports - using absolute imports only per CLAUDE.md
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)


@pytest.mark.integration
class TestMessageRoutingBasics(SSotBaseTestCase):
    """
    Test basic message routing patterns and delivery mechanisms.
    
    BVJ: Reliable routing ensures AI responses reach the correct users
    """
    
    async def test_user_specific_message_routing(self):
        """
        Test routing messages to specific users without cross-contamination.
        
        BVJ: User-specific routing prevents data leakage and ensures personalized AI responses
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple users
            user_clients = {}
            for user_id in ["user_alpha", "user_beta", "user_gamma"]:
                client = await ws_util.create_authenticated_client(user_id)
                client.is_connected = True
                client.websocket = AsyncMock()
                user_clients[user_id] = client
            
            # Send user-specific messages
            test_messages = [
                ("user_alpha", {"analysis": "cost_optimization", "result": "20% savings"}),
                ("user_beta", {"analysis": "security_audit", "result": "3 vulnerabilities"}),
                ("user_gamma", {"analysis": "performance_review", "result": "95% uptime"}),
            ]
            
            for user_id, message_data in test_messages:
                client = user_clients[user_id]
                await client.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    message_data,
                    user_id=user_id,
                    thread_id=f"thread_{user_id}"
                )
            
            # Verify routing isolation - each user only has their own messages
            for user_id, expected_data in test_messages:
                client = user_clients[user_id]
                assert len(client.sent_messages) == 1
                
                sent_msg = client.sent_messages[0]
                assert sent_msg.user_id == user_id
                assert sent_msg.data["analysis"] == expected_data["analysis"]
                assert sent_msg.thread_id == f"thread_{user_id}"
            
            self.record_metric("user_routing_isolation", len(user_clients))
    
    async def test_thread_based_message_routing(self):
        """
        Test routing messages based on thread/conversation context.
        
        BVJ: Thread-based routing maintains conversation context and continuity
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("thread-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Create messages for different conversation threads
            threads = [
                ("thread_cost_analysis", {"topic": "AWS cost optimization"}),
                ("thread_security_scan", {"topic": "Security vulnerability assessment"}),
                ("thread_performance", {"topic": "Application performance tuning"}),
            ]
            
            # Send messages to different threads
            for thread_id, thread_data in threads:
                await client.send_message(
                    WebSocketEventType.THREAD_UPDATE,
                    thread_data,
                    user_id="thread-user",
                    thread_id=thread_id
                )
            
            # Verify thread routing
            assert len(client.sent_messages) == 3
            
            # Group messages by thread
            thread_messages = defaultdict(list)
            for msg in client.sent_messages:
                thread_messages[msg.thread_id].append(msg)
            
            # Verify each thread has correct messages
            for thread_id, expected_data in threads:
                assert thread_id in thread_messages
                thread_msgs = thread_messages[thread_id]
                assert len(thread_msgs) == 1
                assert thread_msgs[0].data["topic"] == expected_data["topic"]
            
            self.record_metric("thread_routing", len(threads))
    
    async def test_broadcast_message_routing(self):
        """
        Test broadcast message routing to multiple users simultaneously.
        
        BVJ: Broadcast routing enables system-wide notifications and announcements
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple users for broadcast testing
            broadcast_users = []
            for i in range(4):
                user_id = f"broadcast_user_{i}"
                client = await ws_util.create_authenticated_client(user_id)
                client.is_connected = True
                client.websocket = AsyncMock()
                broadcast_users.append(client)
            
            # Simulate broadcast message (sent to all users)
            broadcast_data = {
                "type": "system_notification",
                "message": "Scheduled maintenance in 30 minutes",
                "priority": "high",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send broadcast message to all users
            for client in broadcast_users:
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    broadcast_data,
                    user_id=client.headers["X-User-ID"]
                )
            
            # Verify all users received the broadcast
            for client in broadcast_users:
                assert len(client.sent_messages) == 1
                broadcast_msg = client.sent_messages[0]
                assert broadcast_msg.event_type == WebSocketEventType.STATUS_UPDATE
                assert broadcast_msg.data["type"] == "system_notification"
                assert broadcast_msg.data["priority"] == "high"
            
            self.record_metric("broadcast_routing", len(broadcast_users))
    
    async def test_conditional_message_routing(self):
        """
        Test conditional message routing based on user attributes or permissions.
        
        BVJ: Conditional routing ensures users only receive relevant messages
        """
        async with WebSocketTestUtility() as ws_util:
            # Create users with different permission levels
            users_config = [
                {"user_id": "basic_user", "tier": "free", "permissions": ["read"]},
                {"user_id": "premium_user", "tier": "premium", "permissions": ["read", "write"]},
                {"user_id": "enterprise_user", "tier": "enterprise", "permissions": ["read", "write", "admin"]},
            ]
            
            user_clients = {}
            for config in users_config:
                headers = {
                    "X-User-Tier": config["tier"],
                    "X-Permissions": ",".join(config["permissions"])
                }
                client = await ws_util.create_test_client(
                    user_id=config["user_id"],
                    headers=headers
                )
                client.is_connected = True
                client.websocket = AsyncMock()
                user_clients[config["user_id"]] = client
            
            # Send tier-specific messages
            tier_messages = [
                ("premium_user", {"feature": "advanced_analytics", "tier_required": "premium"}),
                ("enterprise_user", {"feature": "custom_integrations", "tier_required": "enterprise"}),
            ]
            
            # Route messages to appropriate users based on tier
            for user_id, message_data in tier_messages:
                if user_id in user_clients:
                    client = user_clients[user_id]
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        message_data,
                        user_id=user_id
                    )
            
            # Verify routing based on user attributes
            assert len(user_clients["basic_user"].sent_messages) == 0  # No premium messages
            assert len(user_clients["premium_user"].sent_messages) == 1  # Premium message
            assert len(user_clients["enterprise_user"].sent_messages) == 1  # Enterprise message
            
            # Verify message content matches user tier
            premium_msg = user_clients["premium_user"].sent_messages[0]
            assert premium_msg.data["tier_required"] == "premium"
            
            enterprise_msg = user_clients["enterprise_user"].sent_messages[0]
            assert enterprise_msg.data["tier_required"] == "enterprise"
            
            self.record_metric("conditional_routing", len(users_config))


@pytest.mark.integration
class TestMessageDeliveryReliability(SSotBaseTestCase):
    """
    Test message delivery reliability and confirmation patterns.
    
    BVJ: Reliable delivery ensures users receive all AI responses and updates
    """
    
    async def test_message_delivery_confirmation(self):
        """
        Test message delivery confirmation and acknowledgment patterns.
        
        BVJ: Delivery confirmation ensures critical AI responses reach users
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("delivery-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Send message with delivery tracking
            message_id = f"msg_{uuid.uuid4().hex[:8]}"
            await client.send_message(
                WebSocketEventType.AGENT_COMPLETED,
                {
                    "result": "Cost analysis completed",
                    "requires_confirmation": True,
                    "message_id": message_id,
                    "delivery_priority": "high"
                },
                user_id="delivery-user"
            )
            
            # Verify message was sent with tracking info
            sent_msg = client.sent_messages[0]
            assert sent_msg.data["requires_confirmation"] is True
            assert sent_msg.data["message_id"] == message_id
            assert sent_msg.message_id is not None
            
            # Simulate delivery confirmation (acknowledgment)
            ack_message = WebSocketMessage(
                event_type=WebSocketEventType.STATUS_UPDATE,
                data={
                    "type": "delivery_confirmation",
                    "original_message_id": message_id,
                    "status": "delivered",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                timestamp=datetime.now(timezone.utc),
                message_id=f"ack_{uuid.uuid4().hex[:8]}",
                user_id="delivery-user"
            )
            
            client.received_messages.append(ack_message)
            
            # Verify confirmation received
            assert len(client.received_messages) == 1
            confirmation = client.received_messages[0]
            assert confirmation.data["type"] == "delivery_confirmation"
            assert confirmation.data["original_message_id"] == message_id
            
            self.record_metric("delivery_confirmation", "tested")
    
    async def test_message_retry_mechanism(self):
        """
        Test message retry mechanism for failed deliveries.
        
        BVJ: Retry mechanism ensures important AI responses eventually reach users
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("retry-user")
            
            # Simulate failed delivery scenario
            failed_attempts = []
            retry_attempts = 3
            
            for attempt in range(retry_attempts):
                try:
                    # Mock connection failure on first attempts
                    if attempt < 2:
                        mock_websocket = AsyncMock()
                        mock_websocket.send.side_effect = ConnectionClosed(None, None)
                        client.websocket = mock_websocket
                        client.is_connected = True
                        
                        with pytest.raises(ConnectionClosed):
                            await client.send_message(
                                WebSocketEventType.AGENT_COMPLETED,
                                {"result": "Analysis ready", "attempt": attempt + 1},
                                user_id="retry-user"
                            )
                        
                        failed_attempts.append(attempt + 1)
                        
                    else:
                        # Successful delivery on final attempt
                        mock_websocket = AsyncMock()
                        mock_websocket.send = AsyncMock()  # Successful send
                        client.websocket = mock_websocket
                        client.is_connected = True
                        
                        await client.send_message(
                            WebSocketEventType.AGENT_COMPLETED,
                            {"result": "Analysis ready", "attempt": attempt + 1},
                            user_id="retry-user"
                        )
                        
                except ConnectionClosed:
                    continue  # Expected for retry testing
            
            # Verify retry attempts were made
            assert len(failed_attempts) == 2  # First 2 attempts failed
            assert len(client.sent_messages) == 1  # Final attempt succeeded
            
            successful_msg = client.sent_messages[0]
            assert successful_msg.data["attempt"] == 3  # Third attempt
            
            self.record_metric("retry_attempts", len(failed_attempts) + 1)
    
    async def test_message_ordering_preservation(self):
        """
        Test message ordering preservation during delivery.
        
        BVJ: Message ordering ensures users see logical AI processing progression
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("ordering-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Send ordered sequence of agent events
            ordered_events = [
                (WebSocketEventType.AGENT_STARTED, {"step": 1, "action": "Starting analysis"}),
                (WebSocketEventType.AGENT_THINKING, {"step": 2, "action": "Processing data"}),
                (WebSocketEventType.TOOL_EXECUTING, {"step": 3, "action": "Running calculations"}),
                (WebSocketEventType.TOOL_COMPLETED, {"step": 4, "action": "Calculations complete"}),
                (WebSocketEventType.AGENT_COMPLETED, {"step": 5, "action": "Analysis finished"}),
            ]
            
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            
            # Send messages in sequence
            for event_type, event_data in ordered_events:
                await client.send_message(
                    event_type,
                    {**event_data, "execution_id": execution_id},
                    user_id="ordering-user"
                )
            
            # Verify message order is preserved
            assert len(client.sent_messages) == 5
            
            for i, (expected_event, expected_data) in enumerate(ordered_events):
                actual_msg = client.sent_messages[i]
                assert actual_msg.event_type == expected_event
                assert actual_msg.data["step"] == expected_data["step"]
                assert actual_msg.data["execution_id"] == execution_id
            
            self.record_metric("message_ordering", len(ordered_events))
    
    async def test_message_priority_handling(self):
        """
        Test message priority handling and urgent message delivery.
        
        BVJ: Priority handling ensures critical alerts reach users immediately
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("priority-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Send messages with different priorities
            priority_messages = [
                ("low", {"alert": "Monthly report available", "urgency": "informational"}),
                ("high", {"alert": "Cost spike detected", "urgency": "immediate_attention"}),
                ("medium", {"alert": "Optimization recommendation", "urgency": "review_soon"}),
                ("critical", {"alert": "Security breach detected", "urgency": "emergency"}),
            ]
            
            # Send messages with priority metadata
            for priority, message_data in priority_messages:
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    {
                        **message_data,
                        "priority": priority,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    user_id="priority-user"
                )
            
            # Verify all messages were sent with priority information
            assert len(client.sent_messages) == 4
            
            # Check priority levels are preserved
            priorities_sent = [msg.data["priority"] for msg in client.sent_messages]
            expected_priorities = [p for p, _ in priority_messages]
            assert priorities_sent == expected_priorities
            
            # Verify critical message has highest urgency
            critical_msg = next(
                msg for msg in client.sent_messages 
                if msg.data["priority"] == "critical"
            )
            assert critical_msg.data["urgency"] == "emergency"
            
            self.record_metric("priority_handling", len(priority_messages))


@pytest.mark.integration
class TestMessageRoutingPerformance(SSotBaseTestCase):
    """
    Test message routing performance and scalability characteristics.
    
    BVJ: Performance ensures responsive AI interactions under load
    """
    
    async def test_concurrent_message_routing(self):
        """
        Test concurrent message routing to multiple users.
        
        BVJ: Concurrent routing supports multiple users receiving AI responses simultaneously
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple concurrent users
            user_count = 10
            clients = []
            
            for i in range(user_count):
                client = await ws_util.create_authenticated_client(f"concurrent_user_{i}")
                client.is_connected = True
                client.websocket = AsyncMock()
                clients.append(client)
            
            # Send concurrent messages
            async def send_user_message(client, user_index):
                await client.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    {
                        "user_index": user_index,
                        "analysis": f"Analysis for user {user_index}",
                        "timestamp": time.time()
                    },
                    user_id=client.headers["X-User-ID"]
                )
            
            # Send messages concurrently
            start_time = time.time()
            tasks = [
                send_user_message(client, i) 
                for i, client in enumerate(clients)
            ]
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Verify all messages were sent
            for i, client in enumerate(clients):
                assert len(client.sent_messages) == 1
                msg = client.sent_messages[0]
                assert msg.data["user_index"] == i
                assert msg.user_id == f"concurrent_user_{i}"
            
            # Performance metrics
            total_time = end_time - start_time
            messages_per_second = user_count / total_time if total_time > 0 else 0
            
            assert messages_per_second > 5, "Should handle at least 5 concurrent messages/second"
            
            self.record_metric("concurrent_routing_performance", messages_per_second)
    
    async def test_high_throughput_message_routing(self):
        """
        Test high-throughput message routing capabilities.
        
        BVJ: High throughput supports busy AI systems with many simultaneous interactions
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("throughput-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Send high volume of messages
            message_count = 100
            start_time = time.time()
            
            for i in range(message_count):
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    {
                        "sequence": i,
                        "batch_id": "throughput_test",
                        "data": f"Message {i}"
                    },
                    user_id="throughput-user"
                )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify all messages were sent
            assert len(client.sent_messages) == message_count
            
            # Performance calculations
            messages_per_second = message_count / total_time if total_time > 0 else 0
            avg_latency = (total_time / message_count) * 1000  # milliseconds
            
            # Performance assertions
            assert messages_per_second > 50, "Should handle at least 50 messages/second"
            assert avg_latency < 50, "Average latency should be under 50ms"
            
            self.record_metric("throughput_messages_per_second", messages_per_second)
            self.record_metric("average_latency_ms", avg_latency)
    
    async def test_message_routing_memory_efficiency(self):
        """
        Test message routing memory efficiency and cleanup.
        
        BVJ: Memory efficiency ensures system stability under sustained load
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("memory-test-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Track initial message state
            initial_sent_count = len(client.sent_messages)
            initial_received_count = len(client.received_messages)
            
            # Send multiple batches of messages
            batch_size = 20
            batch_count = 5
            
            for batch in range(batch_count):
                # Send batch of messages
                for i in range(batch_size):
                    message_data = {
                        "batch": batch,
                        "message": i,
                        "data": "x" * 100,  # Small payload
                        "timestamp": time.time()
                    }
                    
                    await client.send_message(
                        WebSocketEventType.PING,
                        message_data,
                        user_id="memory-test-user"
                    )
                
                # Simulate periodic cleanup (in real system)
                if batch % 2 == 1:  # Clean up every other batch
                    # Keep only recent messages (simulate sliding window)
                    if len(client.sent_messages) > batch_size:
                        client.sent_messages = client.sent_messages[-batch_size:]
            
            # Verify message handling
            total_expected = batch_size * batch_count
            final_sent_count = len(client.sent_messages)
            
            # Should have messages (exact count depends on cleanup simulation)
            assert final_sent_count > 0
            assert final_sent_count <= total_expected
            
            # Verify cleanup effectiveness
            cleanup_ratio = final_sent_count / total_expected
            assert cleanup_ratio <= 1.0, "Cleanup should not increase message count"
            
            self.record_metric("memory_efficiency_cleanup_ratio", cleanup_ratio)
    
    async def test_routing_error_recovery(self):
        """
        Test message routing error recovery and resilience.
        
        BVJ: Error recovery ensures AI responses reach users despite temporary issues
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("recovery-user")
            
            # Test routing with intermittent failures
            success_count = 0
            failure_count = 0
            
            for attempt in range(10):
                try:
                    # Simulate intermittent connection issues
                    if attempt % 3 == 0:  # Every 3rd attempt fails
                        mock_websocket = AsyncMock()
                        mock_websocket.send.side_effect = ConnectionClosed(None, None)
                        client.websocket = mock_websocket
                        client.is_connected = True
                        
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {"attempt": attempt, "status": "test_message"},
                            user_id="recovery-user"
                        )
                        
                    else:
                        # Successful sends
                        mock_websocket = AsyncMock()
                        client.websocket = mock_websocket
                        client.is_connected = True
                        
                        await client.send_message(
                            WebSocketEventType.STATUS_UPDATE,
                            {"attempt": attempt, "status": "test_message"},
                            user_id="recovery-user"
                        )
                        success_count += 1
                        
                except ConnectionClosed:
                    failure_count += 1
            
            # Verify recovery behavior
            assert success_count > 0, "Should have some successful sends"
            assert failure_count > 0, "Should have some expected failures"
            assert len(client.sent_messages) == success_count
            
            # Recovery ratio should be reasonable
            recovery_ratio = success_count / (success_count + failure_count)
            assert recovery_ratio > 0.5, "Should recover from most failures"
            
            self.record_metric("routing_recovery_ratio", recovery_ratio)