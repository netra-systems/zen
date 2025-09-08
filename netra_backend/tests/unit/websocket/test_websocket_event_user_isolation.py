"""
Test WebSocket Event System User Isolation 

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure WebSocket events reach only the correct user
- Value Impact: Prevents cross-user event leakage and ensures real-time notifications work reliably
- Strategic Impact: CRITICAL - WebSocket events enable the core chat experience that delivers business value

This test suite validates that all 5 critical WebSocket events maintain complete user isolation:
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility (shows AI is working)  
3. tool_executing - Tool usage transparency (demonstrates problem-solving)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

Architecture Tested:
- WebSocketBridgeFactory creates isolated per-user event emitters
- UserWebSocketEmitter ensures events only reach intended user
- Event queues are completely separate per user
- No shared state between user WebSocket contexts
"""

import asyncio
import pytest
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, Mock, patch
from fastapi import WebSocket

from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketContext,
    UserWebSocketEmitter,
    WebSocketFactoryConfig,
    WebSocketEvent,
    ConnectionStatus,
    UserWebSocketConnection
)
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool, ConnectionInfo
from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockWebSocket(Mock):
    """Mock WebSocket for testing WebSocket event isolation that passes FastAPI WebSocket validation."""
    
    def __init__(self, user_id: str):
        # Initialize as a Mock with WebSocket spec to pass isinstance checks
        super().__init__(spec=WebSocket)
        self.user_id = user_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.closed = False
        self.connection_state = "CONNECTED"
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json method."""
        if self.closed:
            raise ConnectionError(f"WebSocket closed for user {self.user_id}")
        self.sent_messages.append(data)
        
    async def send_text(self, text: str):
        """Mock send_text method for ping."""
        if self.closed:
            raise ConnectionError(f"WebSocket closed for user {self.user_id}")
        # Empty text is used for ping
        if text == "":
            return  # Ping successful
            
    async def ping(self):
        """Mock ping method."""
        if self.closed:
            raise ConnectionError(f"WebSocket closed for user {self.user_id}")
        return True
        
    async def close(self):
        """Mock close method."""
        self.closed = True
        self.connection_state = "CLOSED"
        
    @property 
    def application_state(self):
        """Mock application state for FastAPI WebSocket compatibility."""
        from fastapi.websockets import WebSocketState
        return WebSocketState.CONNECTED if not self.closed else WebSocketState.DISCONNECTED


# Store original isinstance for restoration
original_isinstance = isinstance


class MockConnectionPool:
    """Mock WebSocket connection pool for testing."""
    
    def __init__(self):
        self.connections: Dict[str, MockWebSocket] = {}
        
    async def get_connection(self, connection_id: str, user_id: str) -> ConnectionInfo:
        """Get or create mock connection for user."""
        if connection_id not in self.connections:
            self.connections[connection_id] = MockWebSocket(user_id)
            
        mock_ws = self.connections[connection_id]
        return ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_ws,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc)
        )


class TestWebSocketEventUserIsolation(SSotBaseTestCase):
    """Test WebSocket event system maintains complete user isolation."""
    
    def setup_method(self):
        """Set up test environment with isolated WebSocket factory."""
        # Create test configuration
        self.config = WebSocketFactoryConfig(
            max_events_per_user=100,
            event_timeout_seconds=5.0,
            delivery_retries=2,
            delivery_timeout_seconds=2.0
        )
        
        # Create factory and mock infrastructure
        self.factory = WebSocketBridgeFactory(self.config)
        self.mock_connection_pool = MockConnectionPool()
        self.mock_agent_registry = Mock()
        self.mock_health_monitor = Mock()
        
        # Configure factory with mocks
        self.factory.configure(
            connection_pool=self.mock_connection_pool,
            agent_registry=self.mock_agent_registry,
            health_monitor=self.mock_health_monitor
        )
        
        # Track created emitters for cleanup
        self.created_emitters: List[UserWebSocketEmitter] = []
        
    def teardown_method(self):
        """Clean up test resources."""        
        async def cleanup():
            for emitter in self.created_emitters:
                try:
                    await emitter.cleanup()
                except Exception:
                    pass  # Ignore cleanup errors in tests
        
        # Run cleanup
        asyncio.run(cleanup())
        self.created_emitters.clear()

    @patch('netra_backend.app.services.websocket_connection_pool.ConnectionInfo.__post_init__')
    async def test_websocket_event_isolation_between_users(self, mock_post_init):
        """Test that WebSocket events are completely isolated between users."""
        # Skip validation in ConnectionInfo for testing
        mock_post_init.return_value = None
        
        # Create emitters for multiple users
        user_emitters = {}
        user_websockets = {}
        
        for i in range(3):
            user_id = f"isolated_user_{i}"
            thread_id = f"isolated_thread_{i}"
            connection_id = f"isolated_conn_{i}"
            
            # Create user emitter
            emitter = await self.factory.create_user_emitter(
                user_id=user_id,
                thread_id=thread_id,
                connection_id=connection_id
            )
            
            user_emitters[user_id] = emitter
            self.created_emitters.append(emitter)
            
            # Get the mock WebSocket for this user
            user_websockets[user_id] = self.mock_connection_pool.connections[connection_id]
            
            # Verify emitter is properly isolated
            assert emitter.user_context.user_id == user_id
            assert emitter.user_context.thread_id == thread_id
            assert emitter.user_context.connection_id == connection_id
        
        # Send all 5 critical WebSocket events to each user
        critical_events = [
            ("agent_started", "notify_agent_started"),
            ("agent_thinking", "notify_agent_thinking"), 
            ("tool_executing", "notify_tool_executing"),
            ("tool_completed", "notify_tool_completed"),
            ("agent_completed", "notify_agent_completed")
        ]
        
        # Send events to each user
        for user_id, emitter in user_emitters.items():
            for event_type, method_name in critical_events:
                method = getattr(emitter, method_name)
                
                if event_type == "agent_started":
                    await method(f"test_agent_{user_id}", f"run_{user_id}")
                elif event_type == "agent_thinking":
                    await method(f"test_agent_{user_id}", f"run_{user_id}", f"Thinking for {user_id}")
                elif event_type == "tool_executing":
                    await method(f"test_agent_{user_id}", f"run_{user_id}", "test_tool", {"param": f"value_{user_id}"})
                elif event_type == "tool_completed": 
                    await method(f"test_agent_{user_id}", f"run_{user_id}", "test_tool", {"result": f"output_{user_id}"})
                elif event_type == "agent_completed":
                    await method(f"test_agent_{user_id}", f"run_{user_id}", {"final": f"result_{user_id}"})
        
        # Wait for event processing
        await asyncio.sleep(0.5)
        
        # Verify complete event isolation
        for user_id, websocket in user_websockets.items():
            # Verify this user received exactly 5 events (all critical events)
            assert len(websocket.sent_messages) == 5, \
                f"User {user_id} should receive 5 events, got {len(websocket.sent_messages)}"
            
            # Verify all events are for this user only
            for message in websocket.sent_messages:
                assert message["data"]["run_id"] == f"run_{user_id}", \
                    f"User {user_id} received event for wrong run_id: {message['data']['run_id']}"
                    
                # Verify user-specific data content
                if "agent_name" in message["data"]:
                    assert message["data"]["agent_name"] == f"test_agent_{user_id}", \
                        f"User {user_id} received event for wrong agent"
            
            # Verify event types received
            received_event_types = {msg["event_type"] for msg in websocket.sent_messages}
            expected_event_types = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
            assert received_event_types == expected_event_types, \
                f"User {user_id} missing events: {expected_event_types - received_event_types}"
        
        # CRITICAL: Verify no cross-user event leakage
        for user_id_1, websocket_1 in user_websockets.items():
            for message in websocket_1.sent_messages:
                # Extract user identifier from message content
                run_id = message["data"]["run_id"]
                expected_run_id = f"run_{user_id_1}"
                
                assert run_id == expected_run_id, \
                    f"ISOLATION VIOLATION: User {user_id_1} received event for {run_id}, expected {expected_run_id}"
                
                # Verify no other user's data appears in messages
                for user_id_2 in user_websockets.keys():
                    if user_id_1 != user_id_2:
                        message_str = json.dumps(message)
                        assert f"run_{user_id_2}" not in message_str, \
                            f"ISOLATION VIOLATION: User {user_id_1} received message containing {user_id_2} data"

    async def test_websocket_event_queue_isolation(self):
        """Test that event queues are completely isolated between users."""
        
        # Create emitters for two users
        user1_emitter = await self.factory.create_user_emitter(
            user_id="queue_user_1",
            thread_id="queue_thread_1", 
            connection_id="queue_conn_1"
        )
        
        user2_emitter = await self.factory.create_user_emitter(
            user_id="queue_user_2",
            thread_id="queue_thread_2",
            connection_id="queue_conn_2"
        )
        
        self.created_emitters.extend([user1_emitter, user2_emitter])
        
        # Verify queues are separate objects
        queue1 = user1_emitter.user_context.event_queue
        queue2 = user2_emitter.user_context.event_queue
        
        assert id(queue1) != id(queue2), \
            "Event queues share object reference - ISOLATION VIOLATION"
        
        # Test queue isolation by filling user1's queue
        # Create events directly to fill queue quickly
        for i in range(10):
            event = WebSocketEvent(
                event_type="test_event",
                user_id="queue_user_1",
                thread_id="queue_thread_1",
                data={"test": f"data_{i}"}
            )
            await user1_emitter._queue_event(event)
        
        # Verify user1's queue has events
        assert not queue1.empty(), "User 1 queue should have events"
        
        # Verify user2's queue is still empty
        assert queue2.empty(), "User 2 queue should remain empty - ISOLATION VIOLATED if not empty"
        
        # Add event to user2's queue
        event2 = WebSocketEvent(
            event_type="user2_event",
            user_id="queue_user_2", 
            thread_id="queue_thread_2",
            data={"test": "user2_data"}
        )
        await user2_emitter._queue_event(event2)
        
        # Verify user2 has exactly 1 event
        assert queue2.qsize() == 1, "User 2 should have exactly 1 event"
        
        # Verify user1's queue size unchanged (still has its events)
        assert queue1.qsize() == 10, "User 1 queue should still have 10 events"

    async def test_websocket_event_delivery_isolation(self):
        """Test that event delivery mechanisms are isolated per user."""
        
        # Create emitters for two users
        user1_emitter = await self.factory.create_user_emitter(
            user_id="delivery_user_1",
            thread_id="delivery_thread_1",
            connection_id="delivery_conn_1"
        )
        
        user2_emitter = await self.factory.create_user_emitter(
            user_id="delivery_user_2", 
            thread_id="delivery_thread_2",
            connection_id="delivery_conn_2"
        )
        
        self.created_emitters.extend([user1_emitter, user2_emitter])
        
        # Get mock WebSockets for verification
        ws1 = self.mock_connection_pool.connections["delivery_conn_1"]
        ws2 = self.mock_connection_pool.connections["delivery_conn_2"]
        
        # Send events to both users
        await user1_emitter.notify_agent_started("agent1", "run1")
        await user2_emitter.notify_agent_started("agent2", "run2")
        
        # Wait for delivery
        await asyncio.sleep(0.3)
        
        # Verify each user received only their own events
        assert len(ws1.sent_messages) == 1, "User 1 should receive exactly 1 event"
        assert len(ws2.sent_messages) == 1, "User 2 should receive exactly 1 event"
        
        # Verify event content isolation
        user1_message = ws1.sent_messages[0]
        user2_message = ws2.sent_messages[0]
        
        assert user1_message["data"]["run_id"] == "run1"
        assert user1_message["data"]["agent_name"] == "agent1"
        
        assert user2_message["data"]["run_id"] == "run2" 
        assert user2_message["data"]["agent_name"] == "agent2"
        
        # CRITICAL: Verify no cross-contamination
        user1_str = json.dumps(user1_message)
        user2_str = json.dumps(user2_message)
        
        assert "run2" not in user1_str, "User 1 message contains User 2 data - ISOLATION VIOLATION"
        assert "agent2" not in user1_str, "User 1 message contains User 2 agent - ISOLATION VIOLATION"
        assert "run1" not in user2_str, "User 2 message contains User 1 data - ISOLATION VIOLATION"
        assert "agent1" not in user2_str, "User 2 message contains User 1 agent - ISOLATION VIOLATION"

    async def test_websocket_connection_isolation(self):
        """Test that WebSocket connections are isolated per user."""
        
        # Create emitters for multiple users
        connections = {}
        emitters = {}
        
        for i in range(3):
            user_id = f"conn_user_{i}"
            thread_id = f"conn_thread_{i}"
            connection_id = f"conn_{i}"
            
            emitter = await self.factory.create_user_emitter(
                user_id=user_id,
                thread_id=thread_id,
                connection_id=connection_id
            )
            
            emitters[user_id] = emitter
            connections[user_id] = emitter.connection
            self.created_emitters.append(emitter)
        
        # Verify connections are separate objects
        connection_ids = set()
        websocket_objects = set()
        
        for user_id, connection in connections.items():
            # Verify unique connection identifiers
            assert connection.connection_id not in connection_ids, \
                f"Connection ID {connection.connection_id} used by multiple users - ISOLATION VIOLATION"
            connection_ids.add(connection.connection_id)
            
            # Verify separate WebSocket objects
            ws_id = id(connection.websocket)
            assert ws_id not in websocket_objects, \
                f"WebSocket object shared between users - ISOLATION VIOLATION"
            websocket_objects.add(ws_id)
            
            # Verify user-specific connection properties
            assert connection.user_id == user_id
        
        # Test connection health isolation
        # Simulate connection failure for user_0
        user0_connection = connections["conn_user_0"]
        user0_ws = user0_connection.websocket
        user0_ws.closed = True
        
        # Test health check isolation
        health_results = {}
        for user_id, connection in connections.items():
            health_results[user_id] = await connection.ping()
        
        # Verify only user_0's connection is unhealthy
        assert health_results["conn_user_0"] is False, "User 0 connection should be unhealthy"
        assert health_results["conn_user_1"] is True, "User 1 connection should be healthy"
        assert health_results["conn_user_2"] is True, "User 2 connection should be healthy"

    async def test_websocket_event_sanitization_isolation(self):
        """Test that event sanitization doesn't leak data between users."""
        
        # Create emitter
        emitter = await self.factory.create_user_emitter(
            user_id="sanitize_user",
            thread_id="sanitize_thread",
            connection_id="sanitize_conn"
        )
        self.created_emitters.append(emitter)
        
        # Test tool input sanitization with sensitive data
        sensitive_input = {
            "api_key": "secret_key_12345",
            "password": "super_secret_password",
            "regular_param": "safe_value",
            "long_data": "x" * 500  # Long data to test truncation
        }
        
        await emitter.notify_tool_executing("test_agent", "test_run", "test_tool", sensitive_input)
        
        # Wait for event processing
        await asyncio.sleep(0.2)
        
        # Get the sent message
        websocket = self.mock_connection_pool.connections["sanitize_conn"]
        assert len(websocket.sent_messages) == 1
        
        message = websocket.sent_messages[0]
        tool_input = message["data"]["tool_input"]
        
        # Verify sensitive data is redacted
        assert tool_input["api_key"] == "[REDACTED]", "API key not properly redacted"
        assert tool_input["password"] == "[REDACTED]", "Password not properly redacted"
        
        # Verify safe data is preserved
        assert tool_input["regular_param"] == "safe_value", "Safe parameter should be preserved"
        
        # Verify long data is truncated
        assert len(tool_input["long_data"]) <= 203, "Long data should be truncated (200 chars + '...')"
        assert tool_input["long_data"].endswith("..."), "Long data should end with '...'"
        
        # CRITICAL: Verify original sensitive data is not in message at all
        message_str = json.dumps(message)
        assert "secret_key_12345" not in message_str, \
            "Original sensitive data leaked in message - SECURITY VIOLATION"
        assert "super_secret_password" not in message_str, \
            "Original password leaked in message - SECURITY VIOLATION"

    async def test_websocket_event_concurrent_user_isolation(self):
        """Test event isolation under concurrent multi-user load."""
        
        async def user_event_simulation(user_index: int, events_per_user: int):
            """Simulate events for a single user."""
            user_id = f"concurrent_user_{user_index}"
            thread_id = f"concurrent_thread_{user_index}" 
            connection_id = f"concurrent_conn_{user_index}"
            
            # Create emitter for this user
            emitter = await self.factory.create_user_emitter(
                user_id=user_id,
                thread_id=thread_id, 
                connection_id=connection_id
            )
            
            # Send multiple events rapidly
            for event_num in range(events_per_user):
                await emitter.notify_agent_thinking(
                    f"agent_{user_index}",
                    f"run_{user_index}_{event_num}",
                    f"User {user_index} thinking {event_num}"
                )
            
            await emitter.cleanup()
            return user_id
        
        # Run concurrent user simulations
        num_users = 5
        events_per_user = 10
        
        # Start all user simulations concurrently
        tasks = [
            user_event_simulation(i, events_per_user)
            for i in range(num_users)
        ]
        
        # Wait for all simulations to complete
        completed_users = await asyncio.gather(*tasks)
        
        # Verify all users completed
        assert len(completed_users) == num_users
        
        # Verify each user's WebSocket received exactly their events
        for user_index in range(num_users):
            connection_id = f"concurrent_conn_{user_index}"
            websocket = self.mock_connection_pool.connections[connection_id]
            
            # Verify this user received exactly the expected number of events
            assert len(websocket.sent_messages) == events_per_user, \
                f"User {user_index} should receive {events_per_user} events, got {len(websocket.sent_messages)}"
            
            # Verify all events belong to this user
            for message in websocket.sent_messages:
                run_id = message["data"]["run_id"]
                agent_name = message["data"]["agent_name"]
                thinking = message["data"]["thinking"]
                
                # Verify user-specific data
                assert f"run_{user_index}_" in run_id, \
                    f"User {user_index} received event with wrong run_id: {run_id}"
                assert agent_name == f"agent_{user_index}", \
                    f"User {user_index} received event for wrong agent: {agent_name}"
                assert f"User {user_index} thinking" in thinking, \
                    f"User {user_index} received thinking from wrong user: {thinking}"
                
                # CRITICAL: Verify no other user's data in message
                for other_user_index in range(num_users):
                    if other_user_index != user_index:
                        message_str = json.dumps(message)
                        assert f"agent_{other_user_index}" not in message_str, \
                            f"ISOLATION VIOLATION: User {user_index} message contains User {other_user_index} agent"
                        assert f"User {other_user_index} thinking" not in message_str, \
                            f"ISOLATION VIOLATION: User {user_index} message contains User {other_user_index} thinking"

    async def test_websocket_factory_metrics_isolation(self):
        """Test that factory metrics don't leak user-specific information."""
        
        # Create emitters for multiple users
        emitters = []
        for i in range(3):
            emitter = await self.factory.create_user_emitter(
                user_id=f"metrics_user_{i}",
                thread_id=f"metrics_thread_{i}",
                connection_id=f"metrics_conn_{i}"
            )
            emitters.append(emitter)
            self.created_emitters.append(emitter)
        
        # Send some events to generate metrics
        for i, emitter in enumerate(emitters):
            await emitter.notify_agent_started(f"agent_{i}", f"run_{i}")
        
        await asyncio.sleep(0.2)  # Wait for event processing
        
        # Get factory metrics
        metrics = self.factory.get_factory_metrics()
        
        # Verify metrics contain aggregate data only (no user-specific info)
        assert "emitters_created" in metrics
        assert "emitters_active" in metrics
        assert "events_sent_total" in metrics
        assert "active_contexts" in metrics
        
        # Verify no user-specific data in metrics
        metrics_str = json.dumps(metrics)
        for i in range(3):
            assert f"metrics_user_{i}" not in metrics_str, \
                f"Factory metrics leak user-specific data: metrics_user_{i}"
            assert f"metrics_conn_{i}" not in metrics_str, \
                f"Factory metrics leak connection-specific data: metrics_conn_{i}"
        
        # Verify metrics show expected aggregate values
        assert metrics["emitters_created"] == 3, "Should show 3 emitters created"
        assert metrics["emitters_active"] == 3, "Should show 3 active emitters"
        assert metrics["events_sent_total"] >= 3, "Should show at least 3 events sent"

    async def test_websocket_cleanup_isolation(self):
        """Test that cleanup operations are isolated per user and don't affect other users."""
        
        # Create emitters for multiple users
        emitters = []
        websockets = []
        
        for i in range(3):
            emitter = await self.factory.create_user_emitter(
                user_id=f"cleanup_user_{i}",
                thread_id=f"cleanup_thread_{i}",
                connection_id=f"cleanup_conn_{i}"
            )
            emitters.append(emitter)
            websockets.append(self.mock_connection_pool.connections[f"cleanup_conn_{i}"])
        
        # Send events to all users
        for i, emitter in enumerate(emitters):
            await emitter.notify_agent_started(f"agent_{i}", f"run_{i}")
        
        await asyncio.sleep(0.2)  # Wait for events to be sent
        
        # Verify all users received their events
        for ws in websockets:
            assert len(ws.sent_messages) == 1, "All users should have received 1 event"
        
        # Cleanup user 1 only
        await emitters[1].cleanup()
        
        # Verify user 1's WebSocket is affected
        # (Note: In our mock, cleanup doesn't close the websocket, but in real implementation it would)
        
        # Send more events to remaining active users
        await emitters[0].notify_agent_completed("agent_0", "run_0", {"result": "success"})
        await emitters[2].notify_agent_completed("agent_2", "run_2", {"result": "success"})
        
        # Attempt to send to cleaned up user (should not work)
        try:
            await emitters[1].notify_agent_completed("agent_1", "run_1", {"result": "should_fail"})
        except Exception:
            pass  # Expected - cleanup should prevent new events
        
        await asyncio.sleep(0.2)  # Wait for event processing
        
        # Verify isolation: other users unaffected by cleanup
        assert len(websockets[0].sent_messages) == 2, \
            "User 0 should have 2 events (unaffected by User 1 cleanup)"
        assert len(websockets[2].sent_messages) == 2, \
            "User 2 should have 2 events (unaffected by User 1 cleanup)"
        
        # User 1 should still have only 1 event (before cleanup)
        assert len(websockets[1].sent_messages) == 1, \
            "User 1 should still have only 1 event from before cleanup"
        
        # Verify event content is still isolated
        for i, ws in enumerate([websockets[0], websockets[2]]):  # Skip cleaned up user
            user_index = 0 if i == 0 else 2  # Map to actual user indices
            for message in ws.sent_messages:
                run_id = message["data"]["run_id"]
                assert f"run_{user_index}" in run_id, \
                    f"User {user_index} received event for wrong user after cleanup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])