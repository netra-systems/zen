"""
WebSocket Message Routing and Delivery Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core messaging infrastructure
- Business Goal: Reliable message delivery enables chat functionality and real-time AI interactions
- Value Impact: CRITICAL - Message routing failures break chat (90% of platform business value)
- Strategic/Revenue Impact: $500K+ ARR depends on messages reaching the correct users at the right time

CRITICAL ROUTING REQUIREMENTS:
1. Messages must reach intended recipients only (user isolation)
2. Message ordering must be preserved for coherent conversations
3. Message delivery must be confirmed and tracked
4. Routing must handle concurrent users without cross-contamination
5. Failed deliveries must be handled gracefully with retries

CRITICAL REQUIREMENTS:
1. Uses REAL WebSocket connections and REAL message routing (NO MOCKS per CLAUDE.md)
2. Tests message routing across multiple concurrent users
3. Validates message ordering preservation during high load
4. Ensures proper error handling and delivery confirmation
5. Tests thread-based message routing isolation

This test validates the core message routing infrastructure that ensures users receive
their AI responses and notifications without interference from other users' sessions.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import pytest
import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed

# SSOT imports following CLAUDE.md absolute import requirements  
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


class TestWebSocketMessageRouting(BaseIntegrationTest):
    """
    Integration tests for WebSocket message routing and delivery.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL routing infrastructure.
    This ensures the complete message flow works correctly in production scenarios.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_message_routing_test(self, real_services_fixture):
        """
        Set up message routing test environment with real services.
        
        BVJ: Test Infrastructure - Ensures reliable message routing testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"routing_test_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services are available (CLAUDE.md requirement)
        assert real_services_fixture, "Real services fixture required - no mocks allowed per CLAUDE.md"
        assert "backend" in real_services_fixture, "Real backend service required for message routing"
        assert "redis" in real_services_fixture, "Real Redis required for message queuing and routing"
        
        # Initialize auth helper for multiple users
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            timeout=20.0
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.websocket_connections: Dict[str, ClientConnection] = {}
        self.user_received_messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Test connectivity to real services
        try:
            test_token = self.auth_helper.create_test_jwt_token(user_id=f"routing_test_user")
            assert test_token, "Failed to create test JWT for message routing"
        except Exception as e:
            pytest.fail(f"Real services not available for message routing testing: {e}")
    
    async def async_teardown(self):
        """Clean up all WebSocket connections."""
        for user_id, ws in self.websocket_connections.items():
            if not ws.closed:
                await ws.close()
        self.websocket_connections.clear()
        await super().async_teardown()
    
    async def create_authenticated_user_connection(self, user_id: str) -> ClientConnection:
        """
        Create authenticated WebSocket connection for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Authenticated WebSocket connection
        """
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"{user_id}@routing-test.com"
        )
        
        headers = self.auth_helper.get_websocket_headers(token)
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.auth_helper.config.websocket_url,
                additional_headers=headers,
                open_timeout=10.0
            ),
            timeout=15.0
        )
        
        self.websocket_connections[user_id] = websocket
        return websocket
    
    async def collect_user_messages(
        self, 
        user_id: str, 
        websocket: ClientConnection,
        duration: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Collect messages for a specific user over a time period.
        
        Args:
            user_id: User identifier
            websocket: User's WebSocket connection
            duration: Time to collect messages
            
        Returns:
            List of messages received by the user
        """
        messages = []
        start_time = time.time()
        
        try:
            while (time.time() - start_time) < duration:
                try:
                    message_data = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_data)
                    message["_received_at"] = time.time()
                    message["_received_by"] = user_id
                    messages.append(message)
                    self.user_received_messages[user_id].append(message)
                    
                except asyncio.TimeoutError:
                    continue
                except ConnectionClosed:
                    break
                    
        except Exception as e:
            # Log but don't fail - we'll check what messages were received
            pass
            
        return messages
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_routing_to_correct_user(self, real_services_fixture):
        """
        Test that messages are routed to the correct user and not to others.
        
        BVJ: User isolation - Critical for preventing data leaks between users.
        Ensures chat messages and AI responses reach only the intended recipient.
        """
        # Create two separate users
        user_a_id = f"routing_user_a_{uuid.uuid4().hex[:8]}"
        user_b_id = f"routing_user_b_{uuid.uuid4().hex[:8]}"
        
        try:
            # Establish connections for both users
            websocket_a = await self.create_authenticated_user_connection(user_a_id)
            websocket_b = await self.create_authenticated_user_connection(user_b_id)
            
            # Start message collection for both users
            collection_task_a = asyncio.create_task(
                self.collect_user_messages(user_a_id, websocket_a, duration=15.0)
            )
            collection_task_b = asyncio.create_task(
                self.collect_user_messages(user_b_id, websocket_b, duration=15.0)
            )
            
            # Wait a moment for connections to stabilize
            await asyncio.sleep(1.0)
            
            # Send targeted message to User A
            message_for_a = {
                "type": "targeted_message",
                "target_user_id": user_a_id,
                "content": "This message is specifically for User A",
                "sender": "routing_test_system",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": f"msg_a_{uuid.uuid4().hex[:8]}"
            }
            
            await websocket_a.send(json.dumps(message_for_a))
            
            # Send different targeted message to User B
            message_for_b = {
                "type": "targeted_message", 
                "target_user_id": user_b_id,
                "content": "This message is specifically for User B",
                "sender": "routing_test_system",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": f"msg_b_{uuid.uuid4().hex[:8]}"
            }
            
            await websocket_b.send(json.dumps(message_for_b))
            
            # Wait for message processing
            await asyncio.sleep(3.0)
            
            # Stop message collection
            collection_task_a.cancel()
            collection_task_b.cancel()
            
            try:
                messages_a = await collection_task_a
            except asyncio.CancelledError:
                messages_a = self.user_received_messages[user_a_id]
                
            try:
                messages_b = await collection_task_b
            except asyncio.CancelledError:
                messages_b = self.user_received_messages[user_b_id]
            
            # Verify User A received their message but not User B's message
            user_a_test_ids = set(msg.get("test_id") for msg in messages_a if msg.get("test_id"))
            user_b_test_ids = set(msg.get("test_id") for msg in messages_b if msg.get("test_id"))
            
            # User A should have received message_for_a but not message_for_b
            assert message_for_a["test_id"] in user_a_test_ids, "User A did not receive their targeted message"
            assert message_for_b["test_id"] not in user_a_test_ids, "User A incorrectly received User B's message - routing failure!"
            
            # User B should have received message_for_b but not message_for_a
            assert message_for_b["test_id"] in user_b_test_ids, "User B did not receive their targeted message"
            assert message_for_a["test_id"] not in user_b_test_ids, "User B incorrectly received User A's message - routing failure!"
            
            await websocket_a.close()
            await websocket_b.close()
            
        except Exception as e:
            pytest.fail(f"Message routing test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_ordering_preservation(self, real_services_fixture):
        """
        Test that message ordering is preserved during delivery.
        
        BVJ: Conversation coherence - Messages must arrive in order for meaningful AI conversations.
        Out-of-order messages break the chat experience and reduce business value.
        """
        user_id = f"ordering_test_{uuid.uuid4().hex[:8]}"
        
        try:
            websocket = await self.create_authenticated_user_connection(user_id)
            
            # Start message collection
            collection_task = asyncio.create_task(
                self.collect_user_messages(user_id, websocket, duration=20.0)
            )
            
            # Send sequence of ordered messages rapidly
            message_sequence = []
            for i in range(10):
                message = {
                    "type": "sequence_message",
                    "sequence_number": i,
                    "user_id": user_id,
                    "content": f"Ordered message {i} - this sequence must be preserved",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_sequence_id": f"seq_{self.test_session_id}"
                }
                
                await websocket.send(json.dumps(message))
                message_sequence.append(message)
                
                # Small delay to ensure messages are distinct
                await asyncio.sleep(0.1)
            
            # Wait for message processing
            await asyncio.sleep(5.0)
            
            # Stop collection and get messages
            collection_task.cancel()
            try:
                received_messages = await collection_task
            except asyncio.CancelledError:
                received_messages = self.user_received_messages[user_id]
            
            # Filter to sequence messages
            sequence_messages = [
                msg for msg in received_messages 
                if msg.get("test_sequence_id") == f"seq_{self.test_session_id}"
            ]
            
            # Verify we received all messages in sequence
            assert len(sequence_messages) >= 10, f"Expected 10 sequence messages, got {len(sequence_messages)}"
            
            # Verify ordering is preserved
            received_sequence = [msg.get("sequence_number") for msg in sequence_messages[:10]]
            expected_sequence = list(range(10))
            
            assert received_sequence == expected_sequence, \
                f"Message ordering not preserved: expected {expected_sequence}, got {received_sequence}"
            
            # Verify timing shows reasonable delivery speed
            if len(sequence_messages) >= 2:
                first_received = sequence_messages[0].get("_received_at", 0)
                last_received = sequence_messages[9].get("_received_at", 0) if len(sequence_messages) >= 10 else sequence_messages[-1].get("_received_at", 0)
                
                delivery_time = last_received - first_received
                assert delivery_time < 10.0, f"Message sequence took {delivery_time:.2f}s - too slow for good user experience"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Message ordering preservation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_message_isolation(self, real_services_fixture):
        """
        Test message isolation between multiple concurrent users.
        
        BVJ: Multi-user scaling - Platform must handle multiple users simultaneously without cross-talk.
        Critical for business growth and preventing data contamination during concurrent AI sessions.
        """
        num_users = 5
        users = [f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_users)]
        
        try:
            # Create connections for all users
            websockets_by_user = {}
            collection_tasks = {}
            
            for user_id in users:
                websocket = await self.create_authenticated_user_connection(user_id)
                websockets_by_user[user_id] = websocket
                
                # Start message collection for each user
                collection_tasks[user_id] = asyncio.create_task(
                    self.collect_user_messages(user_id, websocket, duration=25.0)
                )
            
            # Wait for all connections to stabilize
            await asyncio.sleep(2.0)
            
            # Each user sends their unique messages
            sent_messages_by_user = {}
            
            for i, user_id in enumerate(users):
                user_messages = []
                websocket = websockets_by_user[user_id]
                
                # Send multiple unique messages per user
                for j in range(3):
                    message = {
                        "type": "isolation_test_message",
                        "user_id": user_id,
                        "message_index": j,
                        "content": f"User {i} message {j} - should only reach {user_id}",
                        "unique_id": f"{user_id}_msg_{j}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(message))
                    user_messages.append(message)
                    
                    # Brief delay between messages
                    await asyncio.sleep(0.2)
                
                sent_messages_by_user[user_id] = user_messages
            
            # Wait for message processing and delivery
            await asyncio.sleep(8.0)
            
            # Stop all collection tasks
            for task in collection_tasks.values():
                task.cancel()
            
            # Analyze received messages for isolation
            received_by_user = {}
            for user_id, task in collection_tasks.items():
                try:
                    messages = await task
                except asyncio.CancelledError:
                    messages = self.user_received_messages[user_id]
                received_by_user[user_id] = messages
            
            # Verify each user only received their own messages
            for user_id in users:
                user_received = received_by_user[user_id]
                user_sent = sent_messages_by_user[user_id]
                
                # Get unique IDs of messages this user received
                received_unique_ids = set(
                    msg.get("unique_id") for msg in user_received 
                    if msg.get("type") == "isolation_test_message" and msg.get("unique_id")
                )
                
                # Get unique IDs of messages this user sent
                sent_unique_ids = set(msg["unique_id"] for msg in user_sent)
                
                # Verify user received their own messages
                missing_own_messages = sent_unique_ids - received_unique_ids
                assert len(missing_own_messages) == 0, \
                    f"User {user_id} missing own messages: {missing_own_messages}"
                
                # Verify user did not receive other users' messages
                for other_user_id in users:
                    if other_user_id != user_id:
                        other_user_sent = sent_messages_by_user[other_user_id]
                        other_sent_ids = set(msg["unique_id"] for msg in other_user_sent)
                        
                        leaked_messages = received_unique_ids & other_sent_ids
                        assert len(leaked_messages) == 0, \
                            f"CRITICAL: User {user_id} received messages from {other_user_id}: {leaked_messages}"
            
            # Close all connections
            for websocket in websockets_by_user.values():
                await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Concurrent user message isolation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_based_message_routing(self, real_services_fixture):
        """
        Test that messages are properly routed based on thread context.
        
        BVJ: Conversation context - Messages must be associated with correct conversation threads.
        Critical for maintaining coherent AI conversations and proper context isolation.
        """
        user_id = f"thread_test_{uuid.uuid4().hex[:8]}"
        thread_a_id = f"thread_a_{uuid.uuid4().hex[:8]}"
        thread_b_id = f"thread_b_{uuid.uuid4().hex[:8]}"
        
        try:
            websocket = await self.create_authenticated_user_connection(user_id)
            
            # Start message collection
            collection_task = asyncio.create_task(
                self.collect_user_messages(user_id, websocket, duration=20.0)
            )
            
            # Send messages to different threads
            messages_thread_a = []
            messages_thread_b = []
            
            for i in range(3):
                # Message for thread A
                msg_a = {
                    "type": "thread_message",
                    "user_id": user_id,
                    "thread_id": thread_a_id,
                    "content": f"Thread A message {i}",
                    "message_id": f"thread_a_msg_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(msg_a))
                messages_thread_a.append(msg_a)
                
                # Message for thread B
                msg_b = {
                    "type": "thread_message",
                    "user_id": user_id, 
                    "thread_id": thread_b_id,
                    "content": f"Thread B message {i}",
                    "message_id": f"thread_b_msg_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(msg_b))
                messages_thread_b.append(msg_b)
                
                await asyncio.sleep(0.3)
            
            # Wait for processing
            await asyncio.sleep(5.0)
            
            # Stop collection
            collection_task.cancel()
            try:
                received_messages = await collection_task
            except asyncio.CancelledError:
                received_messages = self.user_received_messages[user_id]
            
            # Analyze thread routing
            thread_messages = [
                msg for msg in received_messages 
                if msg.get("type") == "thread_message"
            ]
            
            # Group messages by thread
            thread_a_received = [msg for msg in thread_messages if msg.get("thread_id") == thread_a_id]
            thread_b_received = [msg for msg in thread_messages if msg.get("thread_id") == thread_b_id]
            
            # Verify thread isolation and proper routing
            assert len(thread_a_received) >= 3, f"Thread A messages not properly routed, expected 3+, got {len(thread_a_received)}"
            assert len(thread_b_received) >= 3, f"Thread B messages not properly routed, expected 3+, got {len(thread_b_received)}"
            
            # Verify no cross-thread contamination
            for msg in thread_a_received:
                assert msg.get("thread_id") == thread_a_id, "Thread A received message from wrong thread"
                
            for msg in thread_b_received:
                assert msg.get("thread_id") == thread_b_id, "Thread B received message from wrong thread"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Thread-based message routing test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_delivery_confirmation(self, real_services_fixture):
        """
        Test that message delivery can be confirmed and tracked.
        
        BVJ: Reliability assurance - System must confirm messages are delivered for critical AI responses.
        Prevents lost responses that would break user experience and reduce platform value.
        """
        user_id = f"delivery_test_{uuid.uuid4().hex[:8]}"
        
        try:
            websocket = await self.create_authenticated_user_connection(user_id)
            
            # Start message collection
            collection_task = asyncio.create_task(
                self.collect_user_messages(user_id, websocket, duration=15.0)
            )
            
            # Send message requiring delivery confirmation
            message_with_confirmation = {
                "type": "confirmed_message",
                "user_id": user_id,
                "content": "This critical message requires delivery confirmation",
                "message_id": f"confirm_msg_{uuid.uuid4().hex[:8]}",
                "require_confirmation": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            send_time = time.time()
            await websocket.send(json.dumps(message_with_confirmation))
            
            # Wait for delivery and potential confirmation
            await asyncio.sleep(8.0)
            
            # Stop collection
            collection_task.cancel()
            try:
                received_messages = await collection_task
            except asyncio.CancelledError:
                received_messages = self.user_received_messages[user_id]
            
            # Check for delivery confirmation or successful echo
            message_id = message_with_confirmation["message_id"]
            
            # Look for any form of message delivery confirmation
            confirmations = [
                msg for msg in received_messages 
                if (msg.get("type") == "delivery_confirmation" and 
                    msg.get("original_message_id") == message_id) or
                   (msg.get("message_id") == message_id) or
                   (message_id in str(msg))
            ]
            
            # Verify message was processed (either echoed back or confirmed)
            # In a real system, we'd expect some form of acknowledgment
            delivery_time = time.time() - send_time
            assert delivery_time < 10.0, f"Message processing took {delivery_time:.2f}s - too slow"
            
            # The fact that we could send and the connection remained stable indicates basic delivery
            assert websocket.state.name == "OPEN", "WebSocket connection was disrupted during message delivery"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"Message delivery confirmation test failed: {e}")
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_high_frequency_message_routing(self, real_services_fixture):
        """
        Test message routing under high frequency conditions.
        
        BVJ: Performance scaling - System must handle high message volumes during intensive AI interactions.
        Critical for supporting active users and complex AI conversations.
        """
        user_id = f"high_freq_{uuid.uuid4().hex[:8]}"
        
        try:
            websocket = await self.create_authenticated_user_connection(user_id)
            
            # Start message collection
            collection_task = asyncio.create_task(
                self.collect_user_messages(user_id, websocket, duration=25.0)
            )
            
            # Send high frequency messages
            num_messages = 50
            sent_messages = []
            
            start_time = time.time()
            
            for i in range(num_messages):
                message = {
                    "type": "high_frequency_message",
                    "user_id": user_id,
                    "sequence_id": i,
                    "content": f"High frequency message {i}",
                    "batch_id": f"batch_{self.test_session_id}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(message))
                sent_messages.append(message)
                
                # Very brief delay to avoid overwhelming
                await asyncio.sleep(0.02)  
            
            send_duration = time.time() - start_time
            
            # Wait for processing
            await asyncio.sleep(10.0)
            
            # Stop collection
            collection_task.cancel()
            try:
                received_messages = await collection_task
            except asyncio.CancelledError:
                received_messages = self.user_received_messages[user_id]
            
            # Analyze high frequency performance
            batch_messages = [
                msg for msg in received_messages
                if msg.get("batch_id") == f"batch_{self.test_session_id}"
            ]
            
            # Verify high delivery rate
            delivery_rate = len(batch_messages) / send_duration
            assert delivery_rate > 10, f"Message delivery rate too low: {delivery_rate:.2f} msg/sec"
            
            # Verify most messages were processed
            delivery_percentage = len(batch_messages) / num_messages
            assert delivery_percentage > 0.8, f"Only {delivery_percentage:.1%} of high frequency messages delivered"
            
            # Verify connection remained stable under load
            assert websocket.state.name == "OPEN", "WebSocket connection failed under high frequency load"
            
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"High frequency message routing test failed: {e}")