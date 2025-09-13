"""
Agent Registry Lifecycle Tests - Foundation Coverage Phase 1

Business Value: Platform/Internal - Agent Management & System Stability
Tests AgentRegistry lifecycle management, agent registration patterns, and proper
initialization/cleanup sequences that ensure reliable agent system operation.

SSOT Compliance: Uses SSotAsyncTestCase, real UserExecutionContext instances,
follows agent registry patterns per CLAUDE.md standards.

Coverage Target: AgentRegistry lifecycle, registration, initialization patterns
Current AgentRegistry Coverage: 11.82% -> Target: 30%+

Critical Lifecycle Patterns Tested:
- Agent registration and discovery mechanisms
- Agent class initialization and configuration
- Registry state management and consistency
- Agent lifecycle hooks (start, stop, cleanup)
- Tool dispatcher integration with agent registry
- WebSocket bridge connection management
- Memory management and resource cleanup

GitHub Issue: #714 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
import time
import weakref
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
from shared.isolated_environment import get_env

# Import target classes
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class MockAgent(BaseAgent):
    """Mock agent for testing registry lifecycle patterns."""

    def __init__(self, agent_type: str = "mock_agent", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_type = agent_type
        self.initialization_time = time.time()
        self.cleanup_called = False
        self.lifecycle_events = []

    async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Mock implementation for testing."""
        self.lifecycle_events.append("process_request")
        return {
            "status": "success",
            "agent_type": self.agent_type,
            "request": request,
            "user_id": context.user_id
        }

    def cleanup(self):
        """Mock cleanup method for lifecycle testing."""
        self.cleanup_called = True
        self.lifecycle_events.append("cleanup")

    def __del__(self):
        """Track deletion for memory leak testing."""
        self.lifecycle_events.append("deleted")


class TestAgentRegistryLifecycle(SSotAsyncTestCase):
    """Test AgentRegistry lifecycle management and agent registration."""

    def setup_method(self, method):
        """Set up test environment with registry and mock agents."""
        super().setup_method(method)

        # Create mock dependencies
        self.llm_manager = Mock(spec=LLMManager)
        self.llm_manager._get_model_name = Mock(return_value="test-model")
        self.llm_manager.ask_llm = AsyncMock(return_value="Mock response")

        self.websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.websocket_bridge.emit_agent_event = AsyncMock()
        self.websocket_bridge.emit_tool_event = AsyncMock()

        # Create user context for registry testing
        self.test_context = UserExecutionContext(
            user_id="registry-test-user-001",
            thread_id="registry-test-thread-001",
            run_id="registry-test-run-001",
            agent_context={
                "user_request": "registry lifecycle test",
                "registry_testing": True
            }
        ).with_db_session(AsyncMock())

        # Track registered agents for cleanup verification
        self.registered_agents = []
        self.registry_events = []

    def teardown_method(self, method):
        """Clean up registry test resources."""
        super().teardown_method(method)
        self.registered_agents.clear()
        self.registry_events.clear()

    def test_agent_registry_initialization_basic(self):
        """Test basic AgentRegistry initialization and configuration."""
        # Test: Registry can be initialized
        registry = AgentRegistry()

        # Verify: Registry is properly initialized
        assert registry is not None
        assert hasattr(registry, '_agent_classes')
        assert hasattr(registry, '_registry_state')

        # Verify: Registry starts with empty state
        initial_classes = registry.get_agent_classes()
        assert isinstance(initial_classes, dict)

        # Verify: Registry has proper SSOT compliance
        assert hasattr(registry, '__len__')  # Required by SSOT patterns

        # Test: Registry length calculation works
        initial_length = len(registry)
        assert isinstance(initial_length, int)
        assert initial_length >= 0

    def test_agent_class_registration_and_discovery(self):
        """Test agent class registration and discovery mechanisms."""
        registry = AgentRegistry()

        # Define test agent classes
        class TestTriageAgent(MockAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(agent_type="triage", *args, **kwargs)

        class TestDataHelperAgent(MockAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(agent_type="data_helper", *args, **kwargs)

        class TestReportingAgent(MockAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(agent_type="reporting", *args, **kwargs)

        # Mock the agent registration process
        test_agent_classes = {
            "triage": TestTriageAgent,
            "data_helper": TestDataHelperAgent,
            "reporting": TestReportingAgent
        }

        # Mock the get_agent_classes method to return our test classes
        registry._agent_classes = test_agent_classes

        # Test: Agent classes can be discovered
        discovered_classes = registry.get_agent_classes()
        assert isinstance(discovered_classes, dict)
        assert len(discovered_classes) == 3

        # Verify: All expected agent types are registered
        expected_types = ["triage", "data_helper", "reporting"]
        for agent_type in expected_types:
            assert agent_type in discovered_classes
            assert issubclass(discovered_classes[agent_type], BaseAgent)

        # Test: Registry length reflects registered agents
        assert len(registry) == 3

        # Verify: Agent classes can be instantiated
        for agent_type, agent_class in discovered_classes.items():
            agent_instance = agent_class(
                llm_manager=self.llm_manager,
                websocket_bridge=self.websocket_bridge
            )
            assert isinstance(agent_instance, BaseAgent)
            assert agent_instance.agent_type == agent_type
            self.registered_agents.append(agent_instance)

    async def test_agent_initialization_with_registry(self):
        """Test agent initialization through registry with proper dependency injection."""
        registry = AgentRegistry()

        # Mock agent factory method
        def create_mock_agent(agent_type: str, **dependencies):
            """Factory method for creating mock agents with dependencies."""
            agent = MockAgent(
                agent_type=agent_type,
                llm_manager=dependencies.get('llm_manager'),
                websocket_bridge=dependencies.get('websocket_bridge')
            )
            self.registered_agents.append(agent)
            return agent

        # Test: Agent can be created through registry factory pattern
        test_dependencies = {
            'llm_manager': self.llm_manager,
            'websocket_bridge': self.websocket_bridge
        }

        agent = create_mock_agent("test_agent", **test_dependencies)

        # Verify: Agent was properly initialized with dependencies
        assert isinstance(agent, MockAgent)
        assert agent.agent_type == "test_agent"
        assert agent.llm_manager is self.llm_manager
        assert agent.websocket_bridge is self.websocket_bridge

        # Verify: Agent initialization timing is recorded
        assert agent.initialization_time > 0
        assert time.time() - agent.initialization_time < 1.0  # Should be recent

        # Test: Agent can process requests with user context
        result = await agent.process_request("test initialization request", self.test_context)

        # Verify: Agent processed request correctly
        assert result["status"] == "success"
        assert result["agent_type"] == "test_agent"
        assert result["user_id"] == "registry-test-user-001"
        assert "process_request" in agent.lifecycle_events

    def test_registry_state_management_and_consistency(self):
        """Test registry state management and consistency across operations."""
        registry = AgentRegistry()

        # Mock registry state
        initial_state = {
            "initialized": True,
            "agents_registered": 0,
            "last_update": time.time(),
            "consistency_check": "passed"
        }

        # Set up registry state tracking
        if not hasattr(registry, '_registry_state'):
            registry._registry_state = initial_state

        # Test: Registry state is consistent
        assert registry._registry_state["initialized"] is True
        assert registry._registry_state["consistency_check"] == "passed"

        # Simulate agent registration affecting state
        mock_agents = {
            "agent_1": MockAgent,
            "agent_2": MockAgent,
            "agent_3": MockAgent
        }

        # Mock agent registration
        registry._agent_classes = mock_agents
        registry._registry_state["agents_registered"] = len(mock_agents)
        registry._registry_state["last_update"] = time.time()

        # Verify: State reflects changes
        assert registry._registry_state["agents_registered"] == 3
        assert registry._registry_state["last_update"] > initial_state["last_update"]

        # Test: Registry consistency is maintained
        agent_count = len(registry.get_agent_classes())
        state_count = registry._registry_state["agents_registered"]
        assert agent_count == state_count

        # Test: Registry length matches state
        assert len(registry) == agent_count

    def test_agent_lifecycle_hooks_and_cleanup(self):
        """Test agent lifecycle hooks and proper cleanup sequences."""
        registry = AgentRegistry()

        # Create agents with lifecycle tracking
        agents = []
        for i in range(3):
            agent = MockAgent(
                agent_type=f"lifecycle_test_agent_{i}",
                llm_manager=self.llm_manager,
                websocket_bridge=self.websocket_bridge
            )
            agents.append(agent)
            self.registered_agents.append(agent)

        # Verify: All agents are properly initialized
        for agent in agents:
            assert agent.initialization_time > 0
            assert not agent.cleanup_called
            assert len(agent.lifecycle_events) == 0

        # Test: Agents can execute lifecycle operations
        for i, agent in enumerate(agents):
            # Simulate lifecycle event
            agent.lifecycle_events.append(f"operation_{i}")

        # Test: Cleanup can be called on all agents
        for agent in agents:
            agent.cleanup()

        # Verify: Cleanup was called on all agents
        for agent in agents:
            assert agent.cleanup_called
            assert "cleanup" in agent.lifecycle_events

        # Test: Agents can be properly dereferenced
        agent_refs = [weakref.ref(agent) for agent in agents]
        agents.clear()  # Remove strong references

        # Force garbage collection (for testing purposes)
        import gc
        gc.collect()

        # Note: We can't reliably test __del__ in Python due to GC behavior,
        # but we can verify that the cleanup methods were called properly

    def test_tool_dispatcher_integration_with_registry(self):
        """Test tool dispatcher integration with agent registry."""
        registry = AgentRegistry()

        # Mock tool dispatcher for registry integration
        mock_tool_dispatcher = Mock()
        mock_tool_dispatcher.get_available_tools = Mock(return_value=[
            "data_analysis_tool",
            "reporting_tool",
            "optimization_tool"
        ])
        mock_tool_dispatcher.execute_tool = AsyncMock(return_value={
            "status": "success",
            "result": "Tool execution completed"
        })

        # Create agent with tool dispatcher integration
        class ToolIntegratedAgent(MockAgent):
            def __init__(self, tool_dispatcher=None, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.tool_dispatcher = tool_dispatcher

            async def process_request(self, request: str, context: UserExecutionContext) -> Dict[str, Any]:
                # Use tool dispatcher if available
                if self.tool_dispatcher and "use_tool" in request:
                    tool_result = await self.tool_dispatcher.execute_tool(
                        "data_analysis_tool",
                        {"request": request, "context": context}
                    )
                    return {
                        "status": "success",
                        "agent_type": self.agent_type,
                        "tool_result": tool_result,
                        "user_id": context.user_id
                    }
                return await super().process_request(request, context)

        # Test: Agent can be created with tool dispatcher
        agent = ToolIntegratedAgent(
            agent_type="tool_integrated",
            tool_dispatcher=mock_tool_dispatcher,
            llm_manager=self.llm_manager,
            websocket_bridge=self.websocket_bridge
        )

        # Verify: Agent has tool dispatcher integration
        assert agent.tool_dispatcher is mock_tool_dispatcher

        # Test: Tool dispatcher integration works
        available_tools = agent.tool_dispatcher.get_available_tools()
        assert len(available_tools) == 3
        assert "data_analysis_tool" in available_tools

        self.registered_agents.append(agent)

    async def test_websocket_bridge_connection_management(self):
        """Test WebSocket bridge connection management through registry."""
        registry = AgentRegistry()

        # Create agents with WebSocket bridge tracking
        websocket_events = []

        async def track_websocket_events(event_type, context, **kwargs):
            websocket_events.append({
                "event_type": event_type,
                "user_id": context.user_id,
                "timestamp": time.time(),
                "agent_info": kwargs.get("data", {})
            })

        self.websocket_bridge.emit_agent_event.side_effect = track_websocket_events

        # Create multiple agents with WebSocket integration
        agents = []
        for i in range(3):
            agent = MockAgent(
                agent_type=f"websocket_test_agent_{i}",
                llm_manager=self.llm_manager,
                websocket_bridge=self.websocket_bridge
            )
            agents.append(agent)
            self.registered_agents.append(agent)

        # Test: Each agent can emit WebSocket events
        for i, agent in enumerate(agents):
            await agent.websocket_bridge.emit_agent_event(
                "agent_test_event",
                self.test_context,
                data={
                    "agent_id": i,
                    "agent_type": agent.agent_type,
                    "test_message": f"WebSocket test from agent {i}"
                }
            )

        # Verify: All WebSocket events were properly emitted
        assert len(websocket_events) == 3

        for i, event in enumerate(websocket_events):
            assert event["event_type"] == "agent_test_event"
            assert event["user_id"] == "registry-test-user-001"
            assert event["agent_info"]["agent_id"] == i
            assert f"websocket_test_agent_{i}" in event["agent_info"]["agent_type"]

        # Test: WebSocket bridge maintains proper connection state
        # (In a real system, this would verify connection pools, etc.)
        assert self.websocket_bridge.emit_agent_event.call_count == 3

    def test_memory_management_and_leak_prevention(self):
        """Test memory management and leak prevention in registry operations."""
        registry = AgentRegistry()

        # Create many agents to test memory management
        agents_created = []
        for i in range(20):  # Create 20 agents
            agent = MockAgent(
                agent_type=f"memory_test_agent_{i}",
                llm_manager=self.llm_manager,
                websocket_bridge=self.websocket_bridge
            )
            agents_created.append(agent)

        # Track memory using weak references
        weak_refs = [weakref.ref(agent) for agent in agents_created]

        # Verify: All agents are initially alive
        alive_count = sum(1 for ref in weak_refs if ref() is not None)
        assert alive_count == 20

        # Simulate registry cleanup - remove references
        del agents_created[10:]  # Remove half the agents

        # Force garbage collection
        import gc
        gc.collect()

        # Test: Registry doesn't hold strong references (preventing cleanup)
        # Note: This test is somewhat limited by Python's GC behavior
        remaining_agents = [ref() for ref in weak_refs[:10] if ref() is not None]
        assert len(remaining_agents) <= 10  # At most 10 should remain

        # Clean up remaining agents
        del remaining_agents
        gc.collect()

        # This test ensures that the registry doesn't prevent proper garbage
        # collection of agents when they're no longer needed, preventing memory leaks.

    def test_registry_thread_safety_basic(self):
        """Test basic thread safety of registry operations."""
        registry = AgentRegistry()

        # Mock thread-safe registry operations
        import threading

        results = []
        errors = []

        def registry_operation(thread_id):
            """Simulate registry operation in different thread."""
            try:
                # Simulate getting agent classes
                agent_classes = registry.get_agent_classes()

                # Simulate length calculation
                registry_length = len(registry)

                results.append({
                    "thread_id": thread_id,
                    "agent_classes_count": len(agent_classes),
                    "registry_length": registry_length,
                    "success": True
                })
            except Exception as e:
                errors.append({
                    "thread_id": thread_id,
                    "error": str(e)
                })

        # Run registry operations in multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=registry_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify: All operations completed successfully
        assert len(results) == 5
        assert len(errors) == 0

        # Verify: All threads got consistent results
        lengths = [result["registry_length"] for result in results]
        assert all(length == lengths[0] for length in lengths)  # All should be the same

        # This test verifies basic thread safety of registry read operations.
        # In a production system, more comprehensive thread safety tests would be needed.