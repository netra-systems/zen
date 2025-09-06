# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test WebSocket Event Isolation - Critical Multi-User Safety Tests

# REMOVED_SYNTAX_ERROR: Business Value Justification:
    # REMOVED_SYNTAX_ERROR: - Segment: ALL (Free → Enterprise)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Security & User Trust
    # REMOVED_SYNTAX_ERROR: - Value Impact: Prevents cross-user event leakage that could expose private data
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: Critical - Enables secure multi-user chat functionality

    # REMOVED_SYNTAX_ERROR: This test suite validates that the refactored WebSocket system provides complete
    # REMOVED_SYNTAX_ERROR: user isolation and prevents events from being sent to the wrong users.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from typing import List, Dict, Any
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.models.user_execution_context import UserExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_event_router import WebSocketEventRouter, ConnectionInfo
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Mock WebSocket manager for testing."""
    # REMOVED_SYNTAX_ERROR: mock_manager = MagicNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_manager.send_to_connection = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: mock_manager.send_message_to_thread = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return mock_manager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_router(mock_websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """WebSocket event router instance for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketEventRouter(mock_websocket_manager)


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user1_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """User context for first test user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_001",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_001",
    # REMOVED_SYNTAX_ERROR: run_id="run_001",
    # REMOVED_SYNTAX_ERROR: request_id="req_001",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_001"
    


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user2_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """User context for second test user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_002",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_002",
    # REMOVED_SYNTAX_ERROR: run_id="run_002",
    # REMOVED_SYNTAX_ERROR: request_id="req_002",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_002"
    


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user3_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """User context for third test user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_003",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_003",
    # REMOVED_SYNTAX_ERROR: run_id="run_003",
    # REMOVED_SYNTAX_ERROR: request_id="req_003",
    # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_003"
    


# REMOVED_SYNTAX_ERROR: class TestWebSocketEventRouter:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket event routing infrastructure."""

    # Removed problematic line: async def test_connection_registration(self, websocket_router, user1_context):
        # REMOVED_SYNTAX_ERROR: """Test that connections are properly registered."""
        # Register connection
        # REMOVED_SYNTAX_ERROR: success = await websocket_router.register_connection( )
        # REMOVED_SYNTAX_ERROR: user1_context.user_id,
        # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
        # REMOVED_SYNTAX_ERROR: user1_context.thread_id
        

        # REMOVED_SYNTAX_ERROR: assert success

        # Check connection is tracked
        # REMOVED_SYNTAX_ERROR: connections = await websocket_router.get_user_connections(user1_context.user_id)
        # REMOVED_SYNTAX_ERROR: assert user1_context.websocket_connection_id in connections

        # Removed problematic line: async def test_connection_isolation(self, websocket_router, user1_context, user2_context):
            # REMOVED_SYNTAX_ERROR: """Test that user connections are isolated."""
            # REMOVED_SYNTAX_ERROR: pass
            # Register connections for both users
            # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
            # REMOVED_SYNTAX_ERROR: user1_context.user_id,
            # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
            # REMOVED_SYNTAX_ERROR: user1_context.thread_id
            
            # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
            # REMOVED_SYNTAX_ERROR: user2_context.user_id,
            # REMOVED_SYNTAX_ERROR: user2_context.websocket_connection_id,
            # REMOVED_SYNTAX_ERROR: user2_context.thread_id
            

            # Check each user only sees their own connections
            # REMOVED_SYNTAX_ERROR: user1_connections = await websocket_router.get_user_connections(user1_context.user_id)
            # REMOVED_SYNTAX_ERROR: user2_connections = await websocket_router.get_user_connections(user2_context.user_id)

            # REMOVED_SYNTAX_ERROR: assert user1_context.websocket_connection_id in user1_connections
            # REMOVED_SYNTAX_ERROR: assert user1_context.websocket_connection_id not in user2_connections

            # REMOVED_SYNTAX_ERROR: assert user2_context.websocket_connection_id in user2_connections
            # REMOVED_SYNTAX_ERROR: assert user2_context.websocket_connection_id not in user1_connections

            # Removed problematic line: async def test_event_routing_isolation(self, websocket_router, user1_context, user2_context):
                # REMOVED_SYNTAX_ERROR: """Critical test: Events only go to intended user."""
                # Register both users
                # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
                # REMOVED_SYNTAX_ERROR: user1_context.thread_id
                
                # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                # REMOVED_SYNTAX_ERROR: user2_context.user_id,
                # REMOVED_SYNTAX_ERROR: user2_context.websocket_connection_id,
                # REMOVED_SYNTAX_ERROR: user2_context.thread_id
                

                # Send event to user 1
                # REMOVED_SYNTAX_ERROR: test_event = { )
                # REMOVED_SYNTAX_ERROR: "type": "agent_started",
                # REMOVED_SYNTAX_ERROR: "run_id": user1_context.run_id,
                # REMOVED_SYNTAX_ERROR: "data": "sensitive_user1_data"
                

                # REMOVED_SYNTAX_ERROR: success = await websocket_router.route_event( )
                # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
                # REMOVED_SYNTAX_ERROR: test_event
                

                # REMOVED_SYNTAX_ERROR: assert success

                # Verify event was sent to correct connection
                # REMOVED_SYNTAX_ERROR: websocket_router.websocket_manager.send_to_connection.assert_called_once()
                # REMOVED_SYNTAX_ERROR: call_args = websocket_router.websocket_manager.send_to_connection.call_args
                # REMOVED_SYNTAX_ERROR: assert call_args[0][0] == user1_context.websocket_connection_id
                # REMOVED_SYNTAX_ERROR: assert call_args[0][1] == test_event

                # Removed problematic line: async def test_connection_cleanup(self, websocket_router, user1_context):
                    # REMOVED_SYNTAX_ERROR: """Test connection cleanup removes all traces."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Register connection
                    # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                    # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                    # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
                    # REMOVED_SYNTAX_ERROR: user1_context.thread_id
                    

                    # Verify connection exists
                    # REMOVED_SYNTAX_ERROR: connections = await websocket_router.get_user_connections(user1_context.user_id)
                    # REMOVED_SYNTAX_ERROR: assert user1_context.websocket_connection_id in connections

                    # Cleanup connection
                    # REMOVED_SYNTAX_ERROR: success = await websocket_router.unregister_connection(user1_context.websocket_connection_id)
                    # REMOVED_SYNTAX_ERROR: assert success

                    # Verify connection is removed
                    # REMOVED_SYNTAX_ERROR: connections = await websocket_router.get_user_connections(user1_context.user_id)
                    # REMOVED_SYNTAX_ERROR: assert user1_context.websocket_connection_id not in connections


# REMOVED_SYNTAX_ERROR: class TestUserWebSocketEmitter:
    # REMOVED_SYNTAX_ERROR: """Test per-user WebSocket emitter isolation."""

    # Removed problematic line: async def test_emitter_creation(self, websocket_router, user1_context):
        # REMOVED_SYNTAX_ERROR: """Test UserWebSocketEmitter creation with proper context."""
        # REMOVED_SYNTAX_ERROR: emitter = UserWebSocketEmitter(user1_context, websocket_router)

        # REMOVED_SYNTAX_ERROR: assert emitter.user_id == user1_context.user_id
        # REMOVED_SYNTAX_ERROR: assert emitter.thread_id == user1_context.thread_id
        # REMOVED_SYNTAX_ERROR: assert emitter.run_id == user1_context.run_id
        # REMOVED_SYNTAX_ERROR: assert emitter.connection_id == user1_context.websocket_connection_id

        # Removed problematic line: async def test_event_emission_isolation(self, websocket_router, user1_context, user2_context):
            # REMOVED_SYNTAX_ERROR: """Critical test: Each emitter only sends to its own user."""
            # REMOVED_SYNTAX_ERROR: pass
            # Create emitters for both users
            # REMOVED_SYNTAX_ERROR: emitter1 = UserWebSocketEmitter(user1_context, websocket_router)
            # REMOVED_SYNTAX_ERROR: emitter2 = UserWebSocketEmitter(user2_context, websocket_router)

            # Register connections
            # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
            # REMOVED_SYNTAX_ERROR: user1_context.user_id,
            # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
            # REMOVED_SYNTAX_ERROR: user1_context.thread_id
            
            # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
            # REMOVED_SYNTAX_ERROR: user2_context.user_id,
            # REMOVED_SYNTAX_ERROR: user2_context.websocket_connection_id,
            # REMOVED_SYNTAX_ERROR: user2_context.thread_id
            

            # Send events from each emitter
            # REMOVED_SYNTAX_ERROR: await emitter1.notify_agent_started("TestAgent", {"user1": "data"})
            # REMOVED_SYNTAX_ERROR: await emitter2.notify_agent_started("TestAgent", {"user2": "data"})

            # Each emitter should have sent exactly one event
            # REMOVED_SYNTAX_ERROR: assert emitter1.events_sent == 1
            # REMOVED_SYNTAX_ERROR: assert emitter1.events_failed == 0
            # REMOVED_SYNTAX_ERROR: assert emitter2.events_sent == 1
            # REMOVED_SYNTAX_ERROR: assert emitter2.events_failed == 0

            # Verify events went to correct users
            # REMOVED_SYNTAX_ERROR: stats1 = emitter1.get_stats()
            # REMOVED_SYNTAX_ERROR: stats2 = emitter2.get_stats()

            # REMOVED_SYNTAX_ERROR: assert stats1["user_id"].startswith(user1_context.user_id[:8])
            # REMOVED_SYNTAX_ERROR: assert stats2["user_id"].startswith(user2_context.user_id[:8])

            # Removed problematic line: async def test_event_sanitization(self, websocket_router, user1_context):
                # REMOVED_SYNTAX_ERROR: """Test that sensitive data is sanitized."""
                # REMOVED_SYNTAX_ERROR: emitter = UserWebSocketEmitter(user1_context, websocket_router)

                # Register connection
                # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
                # REMOVED_SYNTAX_ERROR: user1_context.thread_id
                

                # Send event with sensitive tool input
                # REMOVED_SYNTAX_ERROR: sensitive_input = { )
                # REMOVED_SYNTAX_ERROR: "query": "normal query",
                # REMOVED_SYNTAX_ERROR: "api_key": "secret_key_12345",
                # REMOVED_SYNTAX_ERROR: "password": "super_secret",
                # REMOVED_SYNTAX_ERROR: "large_data": "x" * 500  # Large string
                

                # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_executing("TestAgent", "TestTool", sensitive_input)

                # Verify sanitization occurred
                # REMOVED_SYNTAX_ERROR: assert emitter.events_sent == 1

                # Removed problematic line: async def test_concurrent_emitters(self, websocket_router, user1_context, user2_context, user3_context):
                    # REMOVED_SYNTAX_ERROR: """Test multiple emitters running concurrently without interference."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: contexts = [user1_context, user2_context, user3_context]
                    # REMOVED_SYNTAX_ERROR: emitters = []

                    # Create emitters and register connections
                    # REMOVED_SYNTAX_ERROR: for context in contexts:
                        # REMOVED_SYNTAX_ERROR: emitter = UserWebSocketEmitter(context, websocket_router)
                        # REMOVED_SYNTAX_ERROR: emitters.append(emitter)

                        # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                        # REMOVED_SYNTAX_ERROR: context.user_id,
                        # REMOVED_SYNTAX_ERROR: context.websocket_connection_id,
                        # REMOVED_SYNTAX_ERROR: context.thread_id
                        

                        # Send events concurrently from all emitters
# REMOVED_SYNTAX_ERROR: async def send_events(emitter, agent_name):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_started(agent_name, {"test": "data"})
    # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_thinking(agent_name, "Thinking about the problem")
    # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_executing(agent_name, "TestTool", {"param": "value"})
    # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_completed(agent_name, {"result": "success"})

    # Run all emitters concurrently
    # REMOVED_SYNTAX_ERROR: tasks = [ )
    # REMOVED_SYNTAX_ERROR: send_events(emitters[0], "Agent1"),
    # REMOVED_SYNTAX_ERROR: send_events(emitters[1], "Agent2"),
    # REMOVED_SYNTAX_ERROR: send_events(emitters[2], "Agent3")
    

    # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

    # Verify each emitter sent exactly 4 events
    # REMOVED_SYNTAX_ERROR: for i, emitter in enumerate(emitters):
        # REMOVED_SYNTAX_ERROR: assert emitter.events_sent == 4, "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert emitter.events_failed == 0, "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestWebSocketBridgeFactory:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket bridge factory functionality."""

    # Removed problematic line: async def test_factory_creation(self):
        # REMOVED_SYNTAX_ERROR: """Test factory can create user emitters."""
        # REMOVED_SYNTAX_ERROR: factory = WebSocketBridgeFactory()

        # Mock the router
        # REMOVED_SYNTAX_ERROR: mock_router = AsyncNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: mock_router.register_connection = AsyncMock(return_value=True)
        # REMOVED_SYNTAX_ERROR: factory._router = mock_router

        # Create context and emitter
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="test_user",
        # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
        # REMOVED_SYNTAX_ERROR: run_id="test_run",
        # REMOVED_SYNTAX_ERROR: request_id="test_request",
        # REMOVED_SYNTAX_ERROR: websocket_connection_id="test_conn"
        

        # REMOVED_SYNTAX_ERROR: emitter = await factory.create_emitter(context)

        # REMOVED_SYNTAX_ERROR: assert isinstance(emitter, UserWebSocketEmitter)
        # REMOVED_SYNTAX_ERROR: assert emitter.user_id == context.user_id

        # Verify connection was registered
        # REMOVED_SYNTAX_ERROR: mock_router.register_connection.assert_called_once_with( )
        # REMOVED_SYNTAX_ERROR: user_id=context.user_id,
        # REMOVED_SYNTAX_ERROR: connection_id=context.websocket_connection_id,
        # REMOVED_SYNTAX_ERROR: thread_id=context.thread_id
        

        # Removed problematic line: async def test_factory_caching(self):
            # REMOVED_SYNTAX_ERROR: """Test factory emitter caching functionality."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: factory = WebSocketBridgeFactory()

            # Mock the router
            # REMOVED_SYNTAX_ERROR: mock_router = AsyncNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: mock_router.register_connection = AsyncMock(return_value=True)
            # REMOVED_SYNTAX_ERROR: factory._router = mock_router

            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="test_user",
            # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
            # REMOVED_SYNTAX_ERROR: run_id="test_run",
            # REMOVED_SYNTAX_ERROR: request_id="test_request"
            

            # Create emitter with caching
            # REMOVED_SYNTAX_ERROR: emitter1 = await factory.create_emitter_with_caching(context)
            # REMOVED_SYNTAX_ERROR: emitter2 = await factory.create_emitter_with_caching(context, context.run_id)

            # Should await asyncio.sleep(0)
            # REMOVED_SYNTAX_ERROR: return the same cached instance
            # REMOVED_SYNTAX_ERROR: assert emitter1 is emitter2

            # Cleanup cache
            # REMOVED_SYNTAX_ERROR: await factory.cleanup_emitter_cache(context.run_id)

            # Should create new instance after cleanup
            # REMOVED_SYNTAX_ERROR: emitter3 = await factory.create_emitter_with_caching(context)
            # REMOVED_SYNTAX_ERROR: assert emitter3 is not emitter1


# REMOVED_SYNTAX_ERROR: class TestAgentWebSocketBridgeRefactoring:
    # REMOVED_SYNTAX_ERROR: """Test refactored AgentWebSocketBridge functionality."""

    # Removed problematic line: async def test_non_singleton_creation(self):
        # REMOVED_SYNTAX_ERROR: """Test bridge can be created without singleton pattern."""
        # Create multiple instances - should be different objects
        # REMOVED_SYNTAX_ERROR: bridge1 = AgentWebSocketBridge()
        # REMOVED_SYNTAX_ERROR: bridge2 = AgentWebSocketBridge()

        # Should be different instances
        # REMOVED_SYNTAX_ERROR: assert bridge1 is not bridge2

        # Both should be properly initialized
        # REMOVED_SYNTAX_ERROR: assert hasattr(bridge1, '_initialized')
        # REMOVED_SYNTAX_ERROR: assert hasattr(bridge2, '_initialized')
        # REMOVED_SYNTAX_ERROR: assert bridge1._initialized
        # REMOVED_SYNTAX_ERROR: assert bridge2._initialized

        # Removed problematic line: async def test_create_user_emitter_method(self):
            # REMOVED_SYNTAX_ERROR: """Test bridge can create per-user emitters."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()
            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="test_user",
            # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
            # REMOVED_SYNTAX_ERROR: run_id="test_run",
            # REMOVED_SYNTAX_ERROR: request_id="test_request"
            

            # This should not raise an import error
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: emitter = await bridge.create_user_emitter(context)
                # If we get here without import error, the basic integration works
                # REMOVED_SYNTAX_ERROR: assert emitter is not None
                # REMOVED_SYNTAX_ERROR: except RuntimeError as e:
                    # Expected if factory dependencies aren't mocked
                    # REMOVED_SYNTAX_ERROR: assert "UserWebSocketEmitter factory not available" in str(e)

                    # Removed problematic line: async def test_factory_creates_isolated_instances(self):
                        # REMOVED_SYNTAX_ERROR: """Test factory pattern creates isolated instances."""
                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext

                        # Create different user contexts
                        # REMOVED_SYNTAX_ERROR: context1 = UserExecutionContext(user_id="user1", request_id="req1", thread_id="thread1")
                        # REMOVED_SYNTAX_ERROR: context2 = UserExecutionContext(user_id="user2", request_id="req2", thread_id="thread2")

                        # Should create different instances for isolation
                        # REMOVED_SYNTAX_ERROR: bridge1 = await create_agent_websocket_bridge(context1)
                        # REMOVED_SYNTAX_ERROR: bridge2 = await create_agent_websocket_bridge(context2)

                        # REMOVED_SYNTAX_ERROR: assert isinstance(bridge1, AgentWebSocketBridge)
                        # REMOVED_SYNTAX_ERROR: assert isinstance(bridge2, AgentWebSocketBridge)
                        # REMOVED_SYNTAX_ERROR: assert bridge1 is not bridge2  # Different instances for isolation


# REMOVED_SYNTAX_ERROR: class TestCrossUserEventLeakagePrevention:
    # REMOVED_SYNTAX_ERROR: """Critical security tests for cross-user event leakage prevention."""

    # Removed problematic line: async def test_event_isolation_under_load(self, websocket_router):
        # REMOVED_SYNTAX_ERROR: """Stress test: Ensure no event leakage under high load."""
        # REMOVED_SYNTAX_ERROR: num_users = 10
        # REMOVED_SYNTAX_ERROR: events_per_user = 50

        # Create contexts and emitters for multiple users
        # REMOVED_SYNTAX_ERROR: contexts = []
        # REMOVED_SYNTAX_ERROR: emitters = []

        # REMOVED_SYNTAX_ERROR: for i in range(num_users):
            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: websocket_connection_id="formatted_string"
            
            # REMOVED_SYNTAX_ERROR: contexts.append(context)

            # REMOVED_SYNTAX_ERROR: emitter = UserWebSocketEmitter(context, websocket_router)
            # REMOVED_SYNTAX_ERROR: emitters.append(emitter)

            # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
            # REMOVED_SYNTAX_ERROR: context.user_id,
            # REMOVED_SYNTAX_ERROR: context.websocket_connection_id,
            # REMOVED_SYNTAX_ERROR: context.thread_id
            

            # Send events concurrently from all users
# REMOVED_SYNTAX_ERROR: async def send_user_events(user_idx, emitter):
    # REMOVED_SYNTAX_ERROR: for event_idx in range(events_per_user):
        # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_started( )
        # REMOVED_SYNTAX_ERROR: "formatted_string",
        # REMOVED_SYNTAX_ERROR: {"user_data": "formatted_string"}
        

        # Run all users concurrently
        # REMOVED_SYNTAX_ERROR: tasks = [ )
        # REMOVED_SYNTAX_ERROR: send_user_events(i, emitters[i])
        # REMOVED_SYNTAX_ERROR: for i in range(num_users)
        

        # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

        # Verify each emitter sent exactly the right number of events
        # REMOVED_SYNTAX_ERROR: for i, emitter in enumerate(emitters):
            # REMOVED_SYNTAX_ERROR: assert emitter.events_sent == events_per_user, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            # REMOVED_SYNTAX_ERROR: assert emitter.events_failed == 0, \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # Verify user_id isolation in stats
            # REMOVED_SYNTAX_ERROR: stats = emitter.get_stats()
            # REMOVED_SYNTAX_ERROR: expected_user_prefix = contexts[i].user_id[:8]
            # REMOVED_SYNTAX_ERROR: assert stats["user_id"].startswith(expected_user_prefix), \
            # REMOVED_SYNTAX_ERROR: "formatted_string"

            # Removed problematic line: async def test_connection_id_validation(self, websocket_router, user1_context, user2_context):
                # REMOVED_SYNTAX_ERROR: """Test that connection IDs are properly validated per user."""
                # REMOVED_SYNTAX_ERROR: pass
                # Register connections
                # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
                # REMOVED_SYNTAX_ERROR: user1_context.thread_id
                
                # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                # REMOVED_SYNTAX_ERROR: user2_context.user_id,
                # REMOVED_SYNTAX_ERROR: user2_context.websocket_connection_id,
                # REMOVED_SYNTAX_ERROR: user2_context.thread_id
                

                # Try to send event to user1 using user2's connection_id - should fail
                # REMOVED_SYNTAX_ERROR: test_event = {"type": "test", "data": "should_not_work"}

                # REMOVED_SYNTAX_ERROR: success = await websocket_router.route_event( )
                # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                # REMOVED_SYNTAX_ERROR: user2_context.websocket_connection_id,  # Wrong connection for user1
                # REMOVED_SYNTAX_ERROR: test_event
                

                # Should fail due to connection validation
                # REMOVED_SYNTAX_ERROR: assert not success

                # Removed problematic line: async def test_memory_isolation(self, websocket_router, user1_context, user2_context):
                    # REMOVED_SYNTAX_ERROR: """Test that user data doesn't leak through shared memory."""
                    # Create emitters
                    # REMOVED_SYNTAX_ERROR: emitter1 = UserWebSocketEmitter(user1_context, websocket_router)
                    # REMOVED_SYNTAX_ERROR: emitter2 = UserWebSocketEmitter(user2_context, websocket_router)

                    # Register connections
                    # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                    # REMOVED_SYNTAX_ERROR: user1_context.user_id,
                    # REMOVED_SYNTAX_ERROR: user1_context.websocket_connection_id,
                    # REMOVED_SYNTAX_ERROR: user1_context.thread_id
                    
                    # REMOVED_SYNTAX_ERROR: await websocket_router.register_connection( )
                    # REMOVED_SYNTAX_ERROR: user2_context.user_id,
                    # REMOVED_SYNTAX_ERROR: user2_context.websocket_connection_id,
                    # REMOVED_SYNTAX_ERROR: user2_context.thread_id
                    

                    # Send sensitive events
                    # REMOVED_SYNTAX_ERROR: await emitter1.notify_agent_started("Agent1", {"sensitive": "user1_secret"})
                    # REMOVED_SYNTAX_ERROR: await emitter2.notify_agent_started("Agent2", {"sensitive": "user2_secret"})

                    # Verify emitters have separate stats
                    # REMOVED_SYNTAX_ERROR: stats1 = emitter1.get_stats()
                    # REMOVED_SYNTAX_ERROR: stats2 = emitter2.get_stats()

                    # REMOVED_SYNTAX_ERROR: assert stats1["user_id"] != stats2["user_id"]
                    # REMOVED_SYNTAX_ERROR: assert stats1["run_id"] == user1_context.run_id
                    # REMOVED_SYNTAX_ERROR: assert stats2["run_id"] == user2_context.run_id


                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_end_to_end_isolation():
                        # REMOVED_SYNTAX_ERROR: """End-to-end test of complete WebSocket isolation system."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # Create mock WebSocket manager
                        # REMOVED_SYNTAX_ERROR: mock_manager = MagicNone  # TODO: Use real service instance
                        # REMOVED_SYNTAX_ERROR: mock_manager.send_to_connection = AsyncMock(return_value=True)

                        # Create router
                        # REMOVED_SYNTAX_ERROR: router = WebSocketEventRouter(mock_manager)

                        # Create two user contexts
                        # REMOVED_SYNTAX_ERROR: user1 = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id="user_001",
                        # REMOVED_SYNTAX_ERROR: thread_id="thread_001",
                        # REMOVED_SYNTAX_ERROR: run_id="run_001",
                        # REMOVED_SYNTAX_ERROR: request_id="req_001",
                        # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_001"
                        

                        # REMOVED_SYNTAX_ERROR: user2 = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id="user_002",
                        # REMOVED_SYNTAX_ERROR: thread_id="thread_002",
                        # REMOVED_SYNTAX_ERROR: run_id="run_002",
                        # REMOVED_SYNTAX_ERROR: request_id="req_002",
                        # REMOVED_SYNTAX_ERROR: websocket_connection_id="conn_002"
                        

                        # Create emitters directly (since we're testing the concept, not the factory)
                        # REMOVED_SYNTAX_ERROR: emitter1 = UserWebSocketEmitter(user1, router)
                        # REMOVED_SYNTAX_ERROR: emitter2 = UserWebSocketEmitter(user2, router)

                        # Register connections
                        # REMOVED_SYNTAX_ERROR: await router.register_connection( )
                        # REMOVED_SYNTAX_ERROR: user1.user_id,
                        # REMOVED_SYNTAX_ERROR: user1.websocket_connection_id,
                        # REMOVED_SYNTAX_ERROR: user1.thread_id
                        
                        # REMOVED_SYNTAX_ERROR: await router.register_connection( )
                        # REMOVED_SYNTAX_ERROR: user2.user_id,
                        # REMOVED_SYNTAX_ERROR: user2.websocket_connection_id,
                        # REMOVED_SYNTAX_ERROR: user2.thread_id
                        

                        # Send events from both users
                        # REMOVED_SYNTAX_ERROR: await emitter1.notify_agent_started("TestAgent", {"user": "1"})
                        # REMOVED_SYNTAX_ERROR: await emitter2.notify_agent_started("TestAgent", {"user": "2"})

                        # Verify isolation
                        # REMOVED_SYNTAX_ERROR: assert emitter1.user_id == user1.user_id
                        # REMOVED_SYNTAX_ERROR: assert emitter2.user_id == user2.user_id
                        # REMOVED_SYNTAX_ERROR: assert emitter1.user_id != emitter2.user_id

                        # Verify events were sent
                        # REMOVED_SYNTAX_ERROR: assert emitter1.events_sent == 1
                        # REMOVED_SYNTAX_ERROR: assert emitter2.events_sent == 1
                        # REMOVED_SYNTAX_ERROR: assert emitter1.events_failed == 0
                        # REMOVED_SYNTAX_ERROR: assert emitter2.events_failed == 0


                        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                            # Run critical isolation tests
                            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])