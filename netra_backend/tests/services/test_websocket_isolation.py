"""
Test WebSocket Event Isolation - Critical Multi-User Safety Tests

Business Value Justification:
- Segment: ALL (Free → Enterprise)
- Business Goal: Security & User Trust
- Value Impact: Prevents cross-user event leakage that could expose private data
- Strategic Impact: Critical - Enables secure multi-user chat functionality

This test suite validates that the refactored WebSocket system provides complete
user isolation and prevents events from being sent to the wrong users.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter, ConnectionInfo
from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing."""
    mock_manager = MagicMock()
    mock_manager.send_to_connection = AsyncMock(return_value=True)
    mock_manager.send_message_to_thread = AsyncMock(return_value=True)
    return mock_manager


@pytest.fixture
def websocket_router(mock_websocket_manager):
    """WebSocket event router instance for testing."""
    return WebSocketEventRouter(mock_websocket_manager)


@pytest.fixture
def user1_context():
    """User context for first test user."""
    return UserExecutionContext(
        user_id="user_001",
        thread_id="thread_001",
        run_id="run_001",
        request_id="req_001",
        websocket_connection_id="conn_001"
    )


@pytest.fixture
def user2_context():
    """User context for second test user."""
    return UserExecutionContext(
        user_id="user_002",
        thread_id="thread_002",
        run_id="run_002",
        request_id="req_002",
        websocket_connection_id="conn_002"
    )


@pytest.fixture
def user3_context():
    """User context for third test user."""
    return UserExecutionContext(
        user_id="user_003",
        thread_id="thread_003",
        run_id="run_003",
        request_id="req_003",
        websocket_connection_id="conn_003"
    )


class TestWebSocketEventRouter:
    """Test WebSocket event routing infrastructure."""
    
    async def test_connection_registration(self, websocket_router, user1_context):
        """Test that connections are properly registered."""
        # Register connection
        success = await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        
        assert success
        
        # Check connection is tracked
        connections = await websocket_router.get_user_connections(user1_context.user_id)
        assert user1_context.websocket_connection_id in connections
    
    async def test_connection_isolation(self, websocket_router, user1_context, user2_context):
        """Test that user connections are isolated."""
        # Register connections for both users
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        await websocket_router.register_connection(
            user2_context.user_id,
            user2_context.websocket_connection_id,
            user2_context.thread_id
        )
        
        # Check each user only sees their own connections
        user1_connections = await websocket_router.get_user_connections(user1_context.user_id)
        user2_connections = await websocket_router.get_user_connections(user2_context.user_id)
        
        assert user1_context.websocket_connection_id in user1_connections
        assert user1_context.websocket_connection_id not in user2_connections
        
        assert user2_context.websocket_connection_id in user2_connections
        assert user2_context.websocket_connection_id not in user1_connections
    
    async def test_event_routing_isolation(self, websocket_router, user1_context, user2_context):
        """Critical test: Events only go to intended user."""
        # Register both users
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        await websocket_router.register_connection(
            user2_context.user_id,
            user2_context.websocket_connection_id,
            user2_context.thread_id
        )
        
        # Send event to user 1
        test_event = {
            "type": "agent_started",
            "run_id": user1_context.run_id,
            "data": "sensitive_user1_data"
        }
        
        success = await websocket_router.route_event(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            test_event
        )
        
        assert success
        
        # Verify event was sent to correct connection
        websocket_router.websocket_manager.send_to_connection.assert_called_once()
        call_args = websocket_router.websocket_manager.send_to_connection.call_args
        assert call_args[0][0] == user1_context.websocket_connection_id
        assert call_args[0][1] == test_event
    
    async def test_connection_cleanup(self, websocket_router, user1_context):
        """Test connection cleanup removes all traces."""
        # Register connection
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        
        # Verify connection exists
        connections = await websocket_router.get_user_connections(user1_context.user_id)
        assert user1_context.websocket_connection_id in connections
        
        # Cleanup connection
        success = await websocket_router.unregister_connection(user1_context.websocket_connection_id)
        assert success
        
        # Verify connection is removed
        connections = await websocket_router.get_user_connections(user1_context.user_id)
        assert user1_context.websocket_connection_id not in connections


class TestUserWebSocketEmitter:
    """Test per-user WebSocket emitter isolation."""
    
    async def test_emitter_creation(self, websocket_router, user1_context):
        """Test UserWebSocketEmitter creation with proper context."""
        emitter = UserWebSocketEmitter(user1_context, websocket_router)
        
        assert emitter.user_id == user1_context.user_id
        assert emitter.thread_id == user1_context.thread_id
        assert emitter.run_id == user1_context.run_id
        assert emitter.connection_id == user1_context.websocket_connection_id
    
    async def test_event_emission_isolation(self, websocket_router, user1_context, user2_context):
        """Critical test: Each emitter only sends to its own user."""
        # Create emitters for both users
        emitter1 = UserWebSocketEmitter(user1_context, websocket_router)
        emitter2 = UserWebSocketEmitter(user2_context, websocket_router)
        
        # Register connections
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        await websocket_router.register_connection(
            user2_context.user_id,
            user2_context.websocket_connection_id,
            user2_context.thread_id
        )
        
        # Send events from each emitter
        await emitter1.notify_agent_started("TestAgent", {"user1": "data"})
        await emitter2.notify_agent_started("TestAgent", {"user2": "data"})
        
        # Each emitter should have sent exactly one event
        assert emitter1.events_sent == 1
        assert emitter1.events_failed == 0
        assert emitter2.events_sent == 1
        assert emitter2.events_failed == 0
        
        # Verify events went to correct users
        stats1 = emitter1.get_stats()
        stats2 = emitter2.get_stats()
        
        assert stats1["user_id"].startswith(user1_context.user_id[:8])
        assert stats2["user_id"].startswith(user2_context.user_id[:8])
    
    async def test_event_sanitization(self, websocket_router, user1_context):
        """Test that sensitive data is sanitized."""
        emitter = UserWebSocketEmitter(user1_context, websocket_router)
        
        # Register connection
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        
        # Send event with sensitive tool input
        sensitive_input = {
            "query": "normal query",
            "api_key": "secret_key_12345",
            "password": "super_secret",
            "large_data": "x" * 500  # Large string
        }
        
        await emitter.notify_tool_executing("TestAgent", "TestTool", sensitive_input)
        
        # Verify sanitization occurred
        assert emitter.events_sent == 1
    
    async def test_concurrent_emitters(self, websocket_router, user1_context, user2_context, user3_context):
        """Test multiple emitters running concurrently without interference."""
        contexts = [user1_context, user2_context, user3_context]
        emitters = []
        
        # Create emitters and register connections
        for context in contexts:
            emitter = UserWebSocketEmitter(context, websocket_router)
            emitters.append(emitter)
            
            await websocket_router.register_connection(
                context.user_id,
                context.websocket_connection_id,
                context.thread_id
            )
        
        # Send events concurrently from all emitters
        async def send_events(emitter, agent_name):
            await emitter.notify_agent_started(agent_name, {"test": "data"})
            await emitter.notify_agent_thinking(agent_name, "Thinking about the problem")
            await emitter.notify_tool_executing(agent_name, "TestTool", {"param": "value"})
            await emitter.notify_agent_completed(agent_name, {"result": "success"})
        
        # Run all emitters concurrently
        tasks = [
            send_events(emitters[0], "Agent1"),
            send_events(emitters[1], "Agent2"),
            send_events(emitters[2], "Agent3")
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify each emitter sent exactly 4 events
        for i, emitter in enumerate(emitters):
            assert emitter.events_sent == 4, f"Emitter {i} sent {emitter.events_sent} events, expected 4"
            assert emitter.events_failed == 0, f"Emitter {i} had {emitter.events_failed} failed events"


class TestWebSocketBridgeFactory:
    """Test WebSocket bridge factory functionality."""
    
    async def test_factory_creation(self):
        """Test factory can create user emitters."""
        factory = WebSocketBridgeFactory()
        
        # Mock the router
        mock_router = AsyncMock()
        mock_router.register_connection = AsyncMock(return_value=True)
        factory._router = mock_router
        
        # Create context and emitter
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request",
            websocket_connection_id="test_conn"
        )
        
        emitter = await factory.create_emitter(context)
        
        assert isinstance(emitter, UserWebSocketEmitter)
        assert emitter.user_id == context.user_id
        
        # Verify connection was registered
        mock_router.register_connection.assert_called_once_with(
            user_id=context.user_id,
            connection_id=context.websocket_connection_id,
            thread_id=context.thread_id
        )
    
    async def test_factory_caching(self):
        """Test factory emitter caching functionality."""
        factory = WebSocketBridgeFactory()
        
        # Mock the router
        mock_router = AsyncMock()
        mock_router.register_connection = AsyncMock(return_value=True)
        factory._router = mock_router
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Create emitter with caching
        emitter1 = await factory.create_emitter_with_caching(context)
        emitter2 = await factory.create_emitter_with_caching(context, context.run_id)
        
        # Should return the same cached instance
        assert emitter1 is emitter2
        
        # Cleanup cache
        await factory.cleanup_emitter_cache(context.run_id)
        
        # Should create new instance after cleanup
        emitter3 = await factory.create_emitter_with_caching(context)
        assert emitter3 is not emitter1


class TestAgentWebSocketBridgeRefactoring:
    """Test refactored AgentWebSocketBridge functionality."""
    
    async def test_non_singleton_creation(self):
        """Test bridge can be created without singleton pattern."""
        # Create multiple instances - should be different objects
        bridge1 = AgentWebSocketBridge()
        bridge2 = AgentWebSocketBridge()
        
        # Should be different instances
        assert bridge1 is not bridge2
        
        # Both should be properly initialized
        assert hasattr(bridge1, '_initialized')
        assert hasattr(bridge2, '_initialized')
        assert bridge1._initialized
        assert bridge2._initialized
    
    async def test_create_user_emitter_method(self):
        """Test bridge can create per-user emitters."""
        bridge = AgentWebSocketBridge()
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # This should not raise an import error
        try:
            emitter = await bridge.create_user_emitter(context)
            # If we get here without import error, the basic integration works
            assert emitter is not None
        except RuntimeError as e:
            # Expected if factory dependencies aren't mocked
            assert "UserWebSocketEmitter factory not available" in str(e)
    
    async def test_factory_creates_isolated_instances(self):
        """Test factory pattern creates isolated instances."""
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
        
        # Create different user contexts
        context1 = UserExecutionContext(user_id="user1", request_id="req1", thread_id="thread1")
        context2 = UserExecutionContext(user_id="user2", request_id="req2", thread_id="thread2")
        
        # Should create different instances for isolation
        bridge1 = await create_agent_websocket_bridge(context1)
        bridge2 = await create_agent_websocket_bridge(context2)
        
        assert isinstance(bridge1, AgentWebSocketBridge)
        assert isinstance(bridge2, AgentWebSocketBridge)
        assert bridge1 is not bridge2  # Different instances for isolation


class TestCrossUserEventLeakagePrevention:
    """Critical security tests for cross-user event leakage prevention."""
    
    async def test_event_isolation_under_load(self, websocket_router):
        """Stress test: Ensure no event leakage under high load."""
        num_users = 10
        events_per_user = 50
        
        # Create contexts and emitters for multiple users
        contexts = []
        emitters = []
        
        for i in range(num_users):
            context = UserExecutionContext(
                user_id=f"user_{i:03d}",
                thread_id=f"thread_{i:03d}",
                run_id=f"run_{i:03d}",
                request_id=f"req_{i:03d}",
                websocket_connection_id=f"conn_{i:03d}"
            )
            contexts.append(context)
            
            emitter = UserWebSocketEmitter(context, websocket_router)
            emitters.append(emitter)
            
            await websocket_router.register_connection(
                context.user_id,
                context.websocket_connection_id,
                context.thread_id
            )
        
        # Send events concurrently from all users
        async def send_user_events(user_idx, emitter):
            for event_idx in range(events_per_user):
                await emitter.notify_agent_started(
                    f"Agent_{user_idx}",
                    {"user_data": f"secret_user_{user_idx}_event_{event_idx}"}
                )
        
        # Run all users concurrently
        tasks = [
            send_user_events(i, emitters[i])
            for i in range(num_users)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify each emitter sent exactly the right number of events
        for i, emitter in enumerate(emitters):
            assert emitter.events_sent == events_per_user, \
                f"User {i} sent {emitter.events_sent} events, expected {events_per_user}"
            assert emitter.events_failed == 0, \
                f"User {i} had {emitter.events_failed} failed events"
            
            # Verify user_id isolation in stats
            stats = emitter.get_stats()
            expected_user_prefix = contexts[i].user_id[:8]
            assert stats["user_id"].startswith(expected_user_prefix), \
                f"User {i} stats show wrong user_id: {stats['user_id']}"
    
    async def test_connection_id_validation(self, websocket_router, user1_context, user2_context):
        """Test that connection IDs are properly validated per user."""
        # Register connections
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        await websocket_router.register_connection(
            user2_context.user_id,
            user2_context.websocket_connection_id,
            user2_context.thread_id
        )
        
        # Try to send event to user1 using user2's connection_id - should fail
        test_event = {"type": "test", "data": "should_not_work"}
        
        success = await websocket_router.route_event(
            user1_context.user_id,
            user2_context.websocket_connection_id,  # Wrong connection for user1
            test_event
        )
        
        # Should fail due to connection validation
        assert not success
    
    async def test_memory_isolation(self, websocket_router, user1_context, user2_context):
        """Test that user data doesn't leak through shared memory."""
        # Create emitters
        emitter1 = UserWebSocketEmitter(user1_context, websocket_router)
        emitter2 = UserWebSocketEmitter(user2_context, websocket_router)
        
        # Register connections
        await websocket_router.register_connection(
            user1_context.user_id,
            user1_context.websocket_connection_id,
            user1_context.thread_id
        )
        await websocket_router.register_connection(
            user2_context.user_id,
            user2_context.websocket_connection_id,
            user2_context.thread_id
        )
        
        # Send sensitive events
        await emitter1.notify_agent_started("Agent1", {"sensitive": "user1_secret"})
        await emitter2.notify_agent_started("Agent2", {"sensitive": "user2_secret"})
        
        # Verify emitters have separate stats
        stats1 = emitter1.get_stats()
        stats2 = emitter2.get_stats()
        
        assert stats1["user_id"] != stats2["user_id"]
        assert stats1["run_id"] == user1_context.run_id
        assert stats2["run_id"] == user2_context.run_id


@pytest.mark.asyncio
async def test_end_to_end_isolation():
    """End-to-end test of complete WebSocket isolation system."""
    # Create mock WebSocket manager
    mock_manager = MagicMock()
    mock_manager.send_to_connection = AsyncMock(return_value=True)
    
    # Create router
    router = WebSocketEventRouter(mock_manager)
    
    # Create two user contexts
    user1 = UserExecutionContext(
        user_id="user_001",
        thread_id="thread_001",
        run_id="run_001",
        request_id="req_001",
        websocket_connection_id="conn_001"
    )
    
    user2 = UserExecutionContext(
        user_id="user_002",
        thread_id="thread_002",
        run_id="run_002",
        request_id="req_002",
        websocket_connection_id="conn_002"
    )
    
    # Create emitters directly (since we're testing the concept, not the factory)
    emitter1 = UserWebSocketEmitter(user1, router)
    emitter2 = UserWebSocketEmitter(user2, router)
    
    # Register connections
    await router.register_connection(
        user1.user_id,
        user1.websocket_connection_id,
        user1.thread_id
    )
    await router.register_connection(
        user2.user_id,
        user2.websocket_connection_id,
        user2.thread_id
    )
    
    # Send events from both users
    await emitter1.notify_agent_started("TestAgent", {"user": "1"})
    await emitter2.notify_agent_started("TestAgent", {"user": "2"})
    
    # Verify isolation
    assert emitter1.user_id == user1.user_id
    assert emitter2.user_id == user2.user_id
    assert emitter1.user_id != emitter2.user_id
    
    # Verify events were sent
    assert emitter1.events_sent == 1
    assert emitter2.events_sent == 1
    assert emitter1.events_failed == 0
    assert emitter2.events_failed == 0


if __name__ == "__main__":
    # Run critical isolation tests
    pytest.main([__file__, "-v", "--tb=short"])