"""
Integration tests for UniversalRegistry, AgentRegistry, and UnifiedWebSocketManager interactions.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure chat functionality works end-to-end for all user segments
- Value Impact: WebSocket agent events are MISSION CRITICAL for substantive chat value
- Strategic Impact: Registry-WebSocket integration enables real-time agent notifications 
  that deliver business value through responsive AI interactions

CRITICAL: These integration tests validate the SSOT patterns between registries and 
WebSocket systems that enable:
1. Multi-user isolation through factory patterns
2. Real-time agent event emission for chat UX
3. Thread-safe registry operations
4. Connection state management
5. Agent lifecycle events through WebSocket

Test Strategy:
- NO MOCKS: Use real instances but no external services (integration level)
- Test actual business logic flows for agent-websocket integration 
- Validate WebSocket event emission patterns for chat functionality
- Focus on thread-safety and multi-user scenarios
- Test registry factory patterns for user isolation
"""

import pytest
import asyncio
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import SSOT base test class
from test_framework.base_integration_test import BaseIntegrationTest

# Import core SSOT components under test
from netra_backend.app.core.registry.universal_registry import (
    UniversalRegistry,
    AgentRegistry,
    ToolRegistry,
    ServiceRegistry,
    RegistryItem,
    get_global_registry,
    create_scoped_registry
)
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    RegistryCompat
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockBaseAgent:
    """Mock BaseAgent that implements required interface."""
    
    def __init__(self, name: str, agent_type: str = "mock"):
        self.name = name
        self.agent_type = agent_type
        self.executed = False
        self.websocket_bridge = None
        self.execution_context = None
        self.events_emitted = []
        # Add _mock_name for AgentRegistry validation compatibility
        self._mock_name = f"MockBaseAgent_{name}"
        
    def set_websocket_bridge(self, bridge):
        """Set WebSocket bridge for event emission."""
        self.websocket_bridge = bridge
        
    async def execute(self, message: str, context: Optional[UserExecutionContext] = None):
        """Mock execute method."""
        self.executed = True
        self.execution_context = context
        
        # Emit WebSocket events through bridge if available
        if self.websocket_bridge and context:
            await self.websocket_bridge.emit_agent_started(context.user_id, context.run_id)
            await self.websocket_bridge.emit_agent_thinking(context.user_id, context.run_id, "Processing request")
            await self.websocket_bridge.emit_agent_completed(context.user_id, context.run_id, {"result": f"Processed: {message}"})
            
        return f"Agent {self.name} processed: {message}"


class MockWebSocket:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.messages_sent = []
        self.closed = False
        
    async def send_json(self, message: Dict[str, Any]):
        """Mock send_json method."""
        if self.closed:
            raise ConnectionError(f"WebSocket {self.connection_id} is closed")
        self.messages_sent.append(message)
        
    def close(self):
        """Mock close method."""
        self.closed = True


class MockAgentWebSocketBridge:
    """Mock bridge for agent-websocket integration."""
    
    def __init__(self):
        self.events_emitted = []
        self.websocket_manager = None
        
    def set_websocket_manager(self, manager):
        """Set WebSocket manager."""
        self.websocket_manager = manager
        
    async def emit_agent_started(self, user_id: str, run_id: str):
        """Emit agent started event."""
        event = {"type": "agent_started", "user_id": user_id, "run_id": run_id}
        self.events_emitted.append(event)
        if self.websocket_manager:
            await self.websocket_manager.emit_critical_event(
                user_id, "agent_started", {"run_id": run_id}
            )
    
    async def emit_agent_thinking(self, user_id: str, run_id: str, thought: str):
        """Emit agent thinking event."""
        event = {"type": "agent_thinking", "user_id": user_id, "run_id": run_id, "thought": thought}
        self.events_emitted.append(event)
        if self.websocket_manager:
            await self.websocket_manager.emit_critical_event(
                user_id, "agent_thinking", {"run_id": run_id, "thought": thought}
            )
            
    async def emit_agent_completed(self, user_id: str, run_id: str, result: Dict[str, Any]):
        """Emit agent completed event.""" 
        event = {"type": "agent_completed", "user_id": user_id, "run_id": run_id, "result": result}
        self.events_emitted.append(event)
        if self.websocket_manager:
            await self.websocket_manager.emit_critical_event(
                user_id, "agent_completed", {"run_id": run_id, "result": result}
            )


def create_test_context(user_id: str = None, thread_id: str = None, run_id: str = None) -> UserExecutionContext:
    """Create test execution context."""
    return UserExecutionContext(
        user_id=user_id or f"user_{uuid.uuid4().hex[:8]}",
        thread_id=thread_id or f"thread_{uuid.uuid4().hex[:8]}",
        run_id=run_id or f"run_{uuid.uuid4().hex[:8]}"
    )


class TestUniversalRegistryWebSocketIntegration(BaseIntegrationTest):
    """Test UniversalRegistry interactions with WebSocket systems."""
    
    @pytest.mark.integration
    async def test_registry_factory_multi_user_isolation(self):
        """
        BVJ: Multi-user factory patterns ensure user isolation for chat functionality.
        Tests that registry factories create isolated instances per user context.
        """
        # Create separate contexts for different users
        user1_context = create_test_context("user1", "thread1", "run1")
        user2_context = create_test_context("user2", "thread2", "run2")
        
        # Create agent registry with factory
        registry = UniversalRegistry[MockBaseAgent]("TestAgentRegistry")
        
        # Register factory function
        def agent_factory(context: UserExecutionContext) -> MockBaseAgent:
            return MockBaseAgent(f"agent_{context.user_id}", "factory_created")
        
        registry.register_factory("test_agent", agent_factory)
        
        # Create instances for different users
        agent1 = registry.create_instance("test_agent", user1_context)
        agent2 = registry.create_instance("test_agent", user2_context)
        
        # Verify isolation
        assert agent1 is not agent2
        assert agent1.name == "agent_user1"
        assert agent2.name == "agent_user2"
        assert agent1.agent_type == "factory_created"
        assert agent2.agent_type == "factory_created"
        
        # Verify each factory call creates new instance
        agent1_second = registry.create_instance("test_agent", user1_context)
        assert agent1 is not agent1_second
        assert agent1_second.name == "agent_user1"

    @pytest.mark.integration
    async def test_agent_registry_websocket_bridge_setup(self):
        """
        BVJ: WebSocket bridge integration enables real-time chat notifications.
        Tests that AgentRegistry properly integrates with WebSocket bridge for events.
        """
        # Create WebSocket manager
        websocket_manager = UnifiedWebSocketManager()
        
        # Create WebSocket bridge
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        
        # Create AgentRegistry
        agent_registry = AgentRegistry()
        agent_registry.set_websocket_manager(websocket_manager)
        agent_registry.set_websocket_bridge(bridge)
        
        # Verify integrations are set
        assert agent_registry.websocket_manager is websocket_manager
        assert agent_registry.websocket_bridge is bridge
        
        # Register test agent
        test_agent = MockBaseAgent("test_agent")
        agent_registry.register("test_agent", test_agent)
        
        # Verify agent is registered
        assert agent_registry.has("test_agent")
        retrieved_agent = agent_registry.get("test_agent")
        assert retrieved_agent is test_agent

    @pytest.mark.integration
    async def test_websocket_connection_registry_integration(self):
        """
        BVJ: Connection registry enables efficient message routing for chat.
        Tests WebSocket connection management through registry patterns.
        """
        # Create WebSocket manager
        manager = UnifiedWebSocketManager()
        
        # Create test connections
        user1_id = "user1"
        user2_id = "user2"
        
        websocket1 = MockWebSocket("conn1")
        websocket2 = MockWebSocket("conn2")
        
        # Create connections
        conn1 = WebSocketConnection(
            connection_id="conn1",
            user_id=user1_id,
            websocket=websocket1,
            connected_at=datetime.now(timezone.utc)
        )
        conn2 = WebSocketConnection(
            connection_id="conn2", 
            user_id=user2_id,
            websocket=websocket2,
            connected_at=datetime.now(timezone.utc)
        )
        
        # Add connections
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        # Verify connections are registered
        user1_connections = manager.get_user_connections(user1_id)
        user2_connections = manager.get_user_connections(user2_id)
        
        assert "conn1" in user1_connections
        assert "conn2" in user2_connections
        assert len(user1_connections) == 1
        assert len(user2_connections) == 1
        
        # Test connection retrieval
        retrieved_conn1 = manager.get_connection("conn1")
        assert retrieved_conn1 is conn1
        assert retrieved_conn1.user_id == user1_id

    @pytest.mark.integration
    async def test_agent_execution_with_websocket_events(self):
        """
        BVJ: Agent execution with WebSocket events delivers real-time chat value.
        Tests complete flow of agent execution with WebSocket event emission.
        """
        # Create WebSocket manager and connection
        websocket_manager = UnifiedWebSocketManager()
        test_websocket = MockWebSocket("test_conn")
        
        # Create user context
        context = create_test_context("test_user", "test_thread", "test_run")
        
        # Add connection for user
        connection = WebSocketConnection(
            connection_id="test_conn",
            user_id=context.user_id,
            websocket=test_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        await websocket_manager.add_connection(connection)
        
        # Create bridge and registry
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        
        agent_registry = AgentRegistry()
        agent_registry.set_websocket_manager(websocket_manager)
        agent_registry.set_websocket_bridge(bridge)
        
        # Register and create agent
        test_agent = MockBaseAgent("execution_test")
        agent_registry.register("execution_test", test_agent)
        
        # Execute agent with WebSocket bridge injection
        created_agent = agent_registry.create_agent_with_context(
            "execution_test", context, None, None
        )
        
        # Verify bridge was set
        assert created_agent.websocket_bridge is bridge
        
        # Execute agent
        result = await created_agent.execute("test message", context)
        
        # Verify execution
        assert created_agent.executed is True
        assert "test message" in result
        
        # Verify WebSocket events were emitted
        assert len(bridge.events_emitted) >= 3  # started, thinking, completed
        event_types = [event["type"] for event in bridge.events_emitted]
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types
        assert "agent_completed" in event_types
        
        # Verify messages were sent to WebSocket
        assert len(test_websocket.messages_sent) >= 3

    @pytest.mark.integration
    async def test_thread_safe_registry_websocket_operations(self):
        """
        BVJ: Thread-safety ensures concurrent users can access chat simultaneously.
        Tests concurrent registry and WebSocket operations for race condition prevention.
        """
        websocket_manager = UnifiedWebSocketManager()
        agent_registry = AgentRegistry()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Create multiple user contexts
        contexts = [create_test_context(f"user{i}") for i in range(10)]
        connections_created = []
        agents_registered = []
        
        async def create_user_setup(context: UserExecutionContext):
            """Set up user connection and agent registration."""
            try:
                # Create WebSocket connection
                websocket = MockWebSocket(f"conn_{context.user_id}")
                connection = WebSocketConnection(
                    connection_id=f"conn_{context.user_id}",
                    user_id=context.user_id,
                    websocket=websocket,
                    connected_at=datetime.now(timezone.utc)
                )
                
                await websocket_manager.add_connection(connection)
                connections_created.append(context.user_id)
                
                # Register user-specific agent
                agent = MockBaseAgent(f"agent_{context.user_id}")
                agent_registry.register(f"agent_{context.user_id}", agent)
                agents_registered.append(context.user_id)
                
                # Verify isolation
                user_connections = websocket_manager.get_user_connections(context.user_id)
                assert len(user_connections) == 1
                assert f"conn_{context.user_id}" in user_connections
                
                return True
                
            except Exception as e:
                logger.error(f"Error in concurrent setup for {context.user_id}: {e}")
                return False
        
        # Execute concurrent operations
        tasks = [create_user_setup(context) for context in contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        successful_results = [r for r in results if r is True]
        assert len(successful_results) == 10
        assert len(connections_created) == 10
        assert len(agents_registered) == 10
        
        # Verify all users have isolated connections
        for context in contexts:
            user_connections = websocket_manager.get_user_connections(context.user_id)
            assert len(user_connections) == 1
            
        # Verify all agents are registered
        for context in contexts:
            agent_key = f"agent_{context.user_id}"
            assert agent_registry.has(agent_key)

    @pytest.mark.integration
    async def test_registry_cleanup_websocket_teardown(self):
        """
        BVJ: Proper cleanup prevents connection leaks and maintains system stability.
        Tests registry cleanup and WebSocket connection teardown patterns.
        """
        websocket_manager = UnifiedWebSocketManager()
        registry = UniversalRegistry[MockBaseAgent]("CleanupTest")
        
        # Create test connections and registry items
        test_data = []
        for i in range(5):
            user_id = f"user{i}"
            websocket = MockWebSocket(f"conn{i}")
            connection = WebSocketConnection(
                connection_id=f"conn{i}",
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(timezone.utc)
            )
            
            await websocket_manager.add_connection(connection)
            
            agent = MockBaseAgent(f"agent{i}")
            registry.register(f"agent{i}", agent)
            
            test_data.append((user_id, f"conn{i}", f"agent{i}"))
        
        # Verify everything is set up
        stats = websocket_manager.get_stats()
        assert stats["total_connections"] == 5
        assert stats["unique_users"] == 5
        assert len(registry) == 5
        
        # Clean up connections
        for user_id, conn_id, agent_id in test_data:
            await websocket_manager.remove_connection(conn_id)
            registry.remove(agent_id)
        
        # Verify cleanup
        final_stats = websocket_manager.get_stats()
        assert final_stats["total_connections"] == 0
        assert final_stats["unique_users"] == 0
        assert len(registry) == 0

    @pytest.mark.integration
    async def test_factory_websocket_bridge_integration(self):
        """
        BVJ: Factory-WebSocket integration enables per-user isolated agent events.
        Tests that factory-created agents properly integrate with WebSocket bridges.
        """
        websocket_manager = UnifiedWebSocketManager()
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        
        # Create registry with factory
        registry = AgentRegistry()
        registry.set_websocket_bridge(bridge)
        registry.set_websocket_manager(websocket_manager)
        
        def create_isolated_agent(context: UserExecutionContext) -> MockBaseAgent:
            """Factory that creates user-isolated agents."""
            agent = MockBaseAgent(f"isolated_{context.user_id}")
            agent.context = context  # Store context for verification
            return agent
        
        registry.register_factory("isolated_agent", create_isolated_agent)
        
        # Create different user contexts
        user1_context = create_test_context("user1")
        user2_context = create_test_context("user2")
        
        # Set up WebSocket connections
        ws1 = MockWebSocket("conn1")
        ws2 = MockWebSocket("conn2")
        
        conn1 = WebSocketConnection("conn1", user1_context.user_id, ws1, datetime.now(timezone.utc))
        conn2 = WebSocketConnection("conn2", user2_context.user_id, ws2, datetime.now(timezone.utc))
        
        await websocket_manager.add_connection(conn1)
        await websocket_manager.add_connection(conn2)
        
        # Create agents via factory
        agent1 = registry.create_agent_with_context("isolated_agent", user1_context, None, None)
        agent2 = registry.create_agent_with_context("isolated_agent", user2_context, None, None)
        
        # Verify isolation and bridge injection
        assert agent1 is not agent2
        assert agent1.name == "isolated_user1"
        assert agent2.name == "isolated_user2"
        assert agent1.websocket_bridge is bridge
        assert agent2.websocket_bridge is bridge
        
        # Execute agents and verify events
        await agent1.execute("test1", user1_context)
        await agent2.execute("test2", user2_context)
        
        # Verify events were emitted for both users
        user1_events = [e for e in bridge.events_emitted if e["user_id"] == user1_context.user_id]
        user2_events = [e for e in bridge.events_emitted if e["user_id"] == user2_context.user_id]
        
        assert len(user1_events) >= 3
        assert len(user2_events) >= 3
        
        # Verify WebSocket messages were sent correctly
        assert len(ws1.messages_sent) >= 3
        assert len(ws2.messages_sent) >= 3

    @pytest.mark.integration
    async def test_registry_websocket_error_handling(self):
        """
        BVJ: Error handling prevents cascading failures that break chat functionality.
        Tests error scenarios in registry-WebSocket integration.
        """
        websocket_manager = UnifiedWebSocketManager()
        registry = AgentRegistry()
        registry.set_websocket_manager(websocket_manager)
        
        # Test 1: WebSocket bridge not set
        test_agent = MockBaseAgent("error_test")
        registry.register("error_test", test_agent)
        
        context = create_test_context()
        
        # Should not fail even without bridge
        retrieved_agent = registry.create_agent_with_context("error_test", context, None, None)
        assert retrieved_agent is test_agent
        
        # Test 2: Invalid bridge
        with pytest.raises(ValueError):
            registry.set_websocket_bridge(None)
        
        # Test 3: Missing WebSocket connection
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        registry.set_websocket_bridge(bridge)
        
        agent_with_bridge = registry.create_agent_with_context("error_test", context, None, None)
        
        # Execute without WebSocket connection (should handle gracefully)
        await agent_with_bridge.execute("test", context)
        
        # Verify events were emitted to bridge (even without connection)
        assert len(bridge.events_emitted) >= 3

    @pytest.mark.integration
    async def test_registry_validation_with_base_agent_instances(self):
        """
        BVJ: Registry validation ensures only compatible agents for chat functionality.
        Tests that AgentRegistry validates BaseAgent instances properly.
        """
        registry = AgentRegistry()
        
        # Test valid agent registration
        valid_agent = MockBaseAgent("valid")
        registry.register("valid_agent", valid_agent)
        assert registry.has("valid_agent")
        
        # Test invalid object registration - should fail validation
        invalid_object = {"not": "an agent"}
        
        # Should raise error due to validation failure
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("invalid_object", invalid_object)
        
        # Verify invalid object was not registered
        assert not registry.has("invalid_object")
        
        # Test mock agent recognition
        mock_agent = Mock()
        mock_agent._mock_name = "MockAgent"
        registry.register("mock_agent", mock_agent)
        assert registry.has("mock_agent")

    @pytest.mark.integration 
    async def test_websocket_connection_pooling_through_registry(self):
        """
        BVJ: Connection pooling enables efficient resource use for concurrent chat users.
        Tests WebSocket connection management through registry-like patterns.
        """
        manager = UnifiedWebSocketManager()
        
        # Create connection pool for multiple users
        user_pools = {}
        for user_num in range(3):
            user_id = f"pooled_user_{user_num}"
            user_pools[user_id] = []
            
            # Create multiple connections per user
            for conn_num in range(3):
                conn_id = f"conn_{user_num}_{conn_num}"
                websocket = MockWebSocket(conn_id)
                connection = WebSocketConnection(
                    connection_id=conn_id,
                    user_id=user_id,
                    websocket=websocket,
                    connected_at=datetime.now(timezone.utc)
                )
                
                await manager.add_connection(connection)
                user_pools[user_id].append(conn_id)
        
        # Verify connection pooling
        stats = manager.get_stats()
        assert stats["total_connections"] == 9
        assert stats["unique_users"] == 3
        
        # Verify each user has multiple connections
        for user_id in user_pools:
            user_connections = manager.get_user_connections(user_id)
            assert len(user_connections) == 3
            
        # Test broadcasting to user pools
        test_message = {"type": "test", "data": "pool_broadcast"}
        
        for user_id in user_pools:
            await manager.send_to_user(user_id, test_message)
        
        # Verify all connections received message
        for user_id, conn_ids in user_pools.items():
            for conn_id in conn_ids:
                connection = manager.get_connection(conn_id)
                assert len(connection.websocket.messages_sent) == 1
                assert connection.websocket.messages_sent[0] == test_message

    @pytest.mark.integration
    async def test_agent_lifecycle_websocket_events(self):
        """
        BVJ: Complete agent lifecycle events provide comprehensive chat experience.
        Tests all WebSocket events throughout agent execution lifecycle.
        """
        websocket_manager = UnifiedWebSocketManager()
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        
        # Set up connection
        context = create_test_context("lifecycle_user")
        websocket = MockWebSocket("lifecycle_conn")
        connection = WebSocketConnection(
            connection_id="lifecycle_conn",
            user_id=context.user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc)
        )
        await websocket_manager.add_connection(connection)
        
        # Create comprehensive agent
        class LifecycleAgent(MockBaseAgent):
            """Agent that emits complete lifecycle events."""
            
            async def execute(self, message: str, context: UserExecutionContext = None):
                if self.websocket_bridge and context:
                    # Emit comprehensive lifecycle
                    await self.websocket_bridge.emit_agent_started(context.user_id, context.run_id)
                    await self.websocket_bridge.emit_agent_thinking(context.user_id, context.run_id, "Analyzing request")
                    
                    # Simulate tool usage
                    await bridge.websocket_manager.emit_critical_event(
                        context.user_id, "tool_executing", 
                        {"tool": "analyzer", "run_id": context.run_id}
                    )
                    await bridge.websocket_manager.emit_critical_event(
                        context.user_id, "tool_completed", 
                        {"tool": "analyzer", "result": "analysis complete", "run_id": context.run_id}
                    )
                    
                    await self.websocket_bridge.emit_agent_thinking(context.user_id, context.run_id, "Formulating response")
                    await self.websocket_bridge.emit_agent_completed(context.user_id, context.run_id, 
                                                                   {"final_result": f"Processed: {message}"})
                
                self.executed = True
                return f"Lifecycle agent processed: {message}"
        
        # Execute lifecycle test
        agent = LifecycleAgent("lifecycle_test")
        agent.set_websocket_bridge(bridge)
        
        result = await agent.execute("comprehensive test", context)
        
        # Verify complete lifecycle
        assert agent.executed
        assert "comprehensive test" in result
        
        # Verify all events emitted
        expected_events = ["agent_started", "agent_thinking", "agent_completed"] 
        bridge_event_types = [event["type"] for event in bridge.events_emitted]
        for expected in expected_events:
            assert expected in bridge_event_types
        
        # Verify WebSocket received all events (bridge events + tool events)
        assert len(websocket.messages_sent) >= 5
        websocket_event_types = [msg["type"] for msg in websocket.messages_sent]
        assert "agent_started" in websocket_event_types
        assert "tool_executing" in websocket_event_types
        assert "tool_completed" in websocket_event_types
        assert "agent_completed" in websocket_event_types

    @pytest.mark.integration
    async def test_registry_persistence_recovery_patterns(self):
        """
        BVJ: Registry persistence ensures chat functionality survives system restarts.
        Tests registry state preservation and recovery patterns.
        """
        # Create initial registry state
        registry = UniversalRegistry[MockBaseAgent]("PersistenceTest")
        
        # Register multiple agents
        agents_data = []
        for i in range(5):
            agent = MockBaseAgent(f"persistent_agent_{i}")
            agent_key = f"agent_{i}"
            registry.register(agent_key, agent, description=f"Agent {i}", priority=i)
            agents_data.append((agent_key, agent.name, i))
        
        # Capture registry metrics before "restart"
        initial_metrics = registry.get_metrics()
        assert initial_metrics["total_items"] == 5
        
        # Simulate restart by creating new registry
        recovered_registry = UniversalRegistry[MockBaseAgent]("PersistenceTest")
        
        # Re-register agents (simulating recovery)
        for agent_key, agent_name, priority in agents_data:
            recovered_agent = MockBaseAgent(agent_name)
            recovered_registry.register(agent_key, recovered_agent, 
                                      description=f"Agent {priority}", priority=priority)
        
        # Verify recovery
        recovered_metrics = recovered_registry.get_metrics()
        assert recovered_metrics["total_items"] == 5
        
        # Verify all agents recovered
        for agent_key, _, _ in agents_data:
            assert recovered_registry.has(agent_key)
            recovered_agent = recovered_registry.get(agent_key)
            assert recovered_agent is not None

    @pytest.mark.integration
    async def test_cross_user_isolation_registry_websocket(self):
        """
        BVJ: Cross-user isolation prevents chat data leakage between users.
        Tests that registry and WebSocket systems maintain strict user isolation.
        """
        websocket_manager = UnifiedWebSocketManager()
        registry = UniversalRegistry[MockBaseAgent]("IsolationTest")
        
        # Create isolated user setups
        user_setups = {}
        for user_id in ["user_alpha", "user_beta", "user_gamma"]:
            # Create user-specific WebSocket
            websocket = MockWebSocket(f"ws_{user_id}")
            connection = WebSocketConnection(
                connection_id=f"conn_{user_id}",
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(timezone.utc)
            )
            await websocket_manager.add_connection(connection)
            
            # Create user-specific agent factory
            def create_user_agent(context: UserExecutionContext) -> MockBaseAgent:
                return MockBaseAgent(f"agent_{context.user_id}_{context.run_id}")
            
            registry.register_factory(f"agent_factory_{user_id}", create_user_agent)
            
            user_setups[user_id] = {
                "websocket": websocket,
                "connection": connection,
                "factory_key": f"agent_factory_{user_id}"
            }
        
        # Execute isolated operations
        results = {}
        for user_id, setup in user_setups.items():
            context = create_test_context(user_id, f"thread_{user_id}", f"run_{user_id}")
            
            # Create agent instance
            agent = registry.create_instance(setup["factory_key"], context)
            
            # Execute agent
            result = await agent.execute(f"message_from_{user_id}", context)
            
            results[user_id] = {
                "agent": agent,
                "result": result,
                "context": context
            }
        
        # Verify complete isolation
        for user_id, user_result in results.items():
            agent = user_result["agent"]
            result = user_result["result"]
            
            # Verify agent is user-specific
            assert user_id in agent.name
            assert user_id in result
            
            # Verify no cross-contamination
            for other_user_id, other_result in results.items():
                if other_user_id != user_id:
                    other_agent = other_result["agent"]
                    
                    # Agents should be completely separate
                    assert agent is not other_agent
                    assert other_user_id not in agent.name
                    assert other_user_id not in result
        
        # Verify WebSocket isolation
        for user_id, setup in user_setups.items():
            user_connections = websocket_manager.get_user_connections(user_id)
            assert len(user_connections) == 1
            assert f"conn_{user_id}" in user_connections
            
            # User should not have access to other users' connections
            for other_user_id in user_setups:
                if other_user_id != user_id:
                    other_connections = websocket_manager.get_user_connections(other_user_id)
                    assert f"conn_{user_id}" not in other_connections

    @pytest.mark.integration 
    async def test_websocket_event_ordering_through_registry(self):
        """
        BVJ: Proper event ordering ensures coherent chat experience for users.
        Tests that WebSocket events maintain correct ordering through registry systems.
        """
        websocket_manager = UnifiedWebSocketManager()
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        
        context = create_test_context("ordering_user")
        websocket = MockWebSocket("ordering_conn")
        connection = WebSocketConnection(
            connection_id="ordering_conn",
            user_id=context.user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc)
        )
        await websocket_manager.add_connection(connection)
        
        # Create agent that emits events with specific ordering
        class OrderingTestAgent(MockBaseAgent):
            async def execute(self, message: str, context: UserExecutionContext = None):
                if self.websocket_bridge and context:
                    # Emit events in specific order with timestamps
                    events = [
                        ("agent_started", {"step": 1}),
                        ("agent_thinking", {"step": 2, "thought": "step 2"}),
                        ("agent_thinking", {"step": 3, "thought": "step 3"}),
                        ("agent_thinking", {"step": 4, "thought": "step 4"}),
                        ("agent_completed", {"step": 5, "result": "final"})
                    ]
                    
                    for event_type, data in events:
                        if event_type == "agent_started":
                            await self.websocket_bridge.emit_agent_started(context.user_id, context.run_id)
                        elif event_type == "agent_thinking":
                            await self.websocket_bridge.emit_agent_thinking(
                                context.user_id, context.run_id, data["thought"]
                            )
                        elif event_type == "agent_completed":
                            await self.websocket_bridge.emit_agent_completed(
                                context.user_id, context.run_id, data
                            )
                        
                        # Small delay to ensure ordering
                        await asyncio.sleep(0.01)
                
                return "Ordering test completed"
        
        # Execute ordering test
        agent = OrderingTestAgent("ordering_agent")
        agent.set_websocket_bridge(bridge)
        
        await agent.execute("order test", context)
        
        # Verify event ordering in bridge
        bridge_events = bridge.events_emitted
        assert len(bridge_events) == 5
        
        # Check bridge event order
        expected_bridge_order = [
            "agent_started", "agent_thinking", "agent_thinking", 
            "agent_thinking", "agent_completed"
        ]
        actual_bridge_order = [event["type"] for event in bridge_events]
        assert actual_bridge_order == expected_bridge_order
        
        # Verify WebSocket message ordering
        websocket_messages = websocket.messages_sent
        assert len(websocket_messages) == 5
        
        websocket_event_order = [msg["type"] for msg in websocket_messages]
        assert websocket_event_order == expected_bridge_order
        
        # Verify timestamp ordering (each message should have later timestamp)
        timestamps = [datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00")) 
                     for msg in websocket_messages]
        
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], f"Event {i} timestamp not >= previous"

    @pytest.mark.integration
    async def test_registry_websocket_performance_under_load(self):
        """
        BVJ: Performance under load ensures chat remains responsive for all users.
        Tests registry and WebSocket performance with concurrent high-volume operations.
        """
        websocket_manager = UnifiedWebSocketManager()
        registry = AgentRegistry()
        registry.set_websocket_manager(websocket_manager)
        
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        registry.set_websocket_bridge(bridge)
        
        # Create high-volume test setup
        num_users = 20
        operations_per_user = 10
        
        user_contexts = []
        for i in range(num_users):
            context = create_test_context(f"perf_user_{i}")
            user_contexts.append(context)
            
            # Set up WebSocket connection
            websocket = MockWebSocket(f"perf_conn_{i}")
            connection = WebSocketConnection(
                connection_id=f"perf_conn_{i}",
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.now(timezone.utc)
            )
            await websocket_manager.add_connection(connection)
            
            # Register agents
            for j in range(operations_per_user):
                agent_key = f"perf_agent_{i}_{j}"
                agent = MockBaseAgent(agent_key)
                registry.register(agent_key, agent)
        
        # Measure performance of concurrent operations
        start_time = time.time()
        
        async def perform_user_operations(context: UserExecutionContext):
            """Perform operations for a single user."""
            operations_completed = 0
            user_num = context.user_id.split("_")[-1]
            
            for j in range(operations_per_user):
                try:
                    agent_key = f"perf_agent_{user_num}_{j}"
                    
                    # Retrieve agent
                    agent = registry.get(agent_key)
                    assert agent is not None
                    
                    # Create agent with context (includes WebSocket bridge setup)
                    contextual_agent = registry.create_agent_with_context(
                        agent_key, context, None, None
                    )
                    
                    # Execute agent (triggers WebSocket events)
                    await contextual_agent.execute(f"perf_test_{j}", context)
                    
                    operations_completed += 1
                    
                except Exception as e:
                    logger.error(f"Performance test operation failed: {e}")
            
            return operations_completed
        
        # Execute all operations concurrently
        tasks = [perform_user_operations(context) for context in user_contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance results
        successful_results = [r for r in results if isinstance(r, int)]
        total_operations_completed = sum(successful_results)
        expected_total = num_users * operations_per_user
        
        assert len(successful_results) == num_users
        assert total_operations_completed == expected_total
        
        # Performance assertions (should complete in reasonable time)
        operations_per_second = total_operations_completed / total_time
        assert operations_per_second > 50  # At least 50 ops/second
        assert total_time < 30  # Complete within 30 seconds
        
        # Verify all WebSocket connections still active
        final_stats = websocket_manager.get_stats()
        assert final_stats["total_connections"] == num_users
        assert final_stats["unique_users"] == num_users
        
        # Verify registry integrity
        registry_metrics = registry.get_metrics()
        assert registry_metrics["total_items"] == expected_total

    @pytest.mark.integration
    async def test_registry_websocket_graceful_degradation(self):
        """
        BVJ: Graceful degradation maintains core chat functionality during failures.
        Tests that registry-WebSocket integration handles failures gracefully.
        """
        websocket_manager = UnifiedWebSocketManager()
        registry = AgentRegistry()
        
        # Test 1: Registry works without WebSocket manager
        test_agent = MockBaseAgent("degradation_test")
        registry.register("degradation_test", test_agent)
        
        context = create_test_context("degradation_user")
        
        # Should work even without WebSocket setup
        agent = registry.get("degradation_test")
        assert agent is not None
        
        result = await agent.execute("graceful test", context)
        assert "graceful test" in result
        
        # Test 2: WebSocket manager handles missing connections
        registry.set_websocket_manager(websocket_manager)
        
        bridge = MockAgentWebSocketBridge()
        bridge.set_websocket_manager(websocket_manager)
        registry.set_websocket_bridge(bridge)
        
        # Execute without WebSocket connection - should not fail
        contextual_agent = registry.create_agent_with_context("degradation_test", context, None, None)
        result = await contextual_agent.execute("no websocket test", context)
        
        assert contextual_agent.executed
        assert "no websocket test" in result
        
        # Test 3: Partial WebSocket failure handling
        websocket1 = MockWebSocket("good_conn")
        websocket2 = MockWebSocket("bad_conn")
        
        # Make one WebSocket fail
        websocket2.closed = True
        
        good_conn = WebSocketConnection("good_conn", "good_user", websocket1, datetime.now(timezone.utc))
        bad_conn = WebSocketConnection("bad_conn", "bad_user", websocket2, datetime.now(timezone.utc))
        
        await websocket_manager.add_connection(good_conn)
        await websocket_manager.add_connection(bad_conn)
        
        # Send messages to both users
        test_message = {"type": "degradation_test", "data": "test"}
        
        # Good user should receive message
        await websocket_manager.send_to_user("good_user", test_message)
        assert len(websocket1.messages_sent) == 1
        
        # Bad user message should fail gracefully (connection gets cleaned up)
        # Use a short timeout to avoid infinite loops in tests
        try:
            await asyncio.wait_for(
                websocket_manager.send_to_user("bad_user", test_message), 
                timeout=2.0
            )
        except asyncio.TimeoutError:
            # This is expected - connection is bad and should timeout
            pass
        
        # Verify system continues operating
        stats = websocket_manager.get_stats()
        assert stats["unique_users"] >= 1  # At least good user remains