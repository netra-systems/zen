from unittest.mock import Mock, patch, MagicMock
import asyncio

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Tests for AgentClassRegistry: Infrastructure-only agent class registration.

# REMOVED_SYNTAX_ERROR: CRITICAL: These tests verify that the AgentClassRegistry meets all requirements:
    # REMOVED_SYNTAX_ERROR: 1. Stores only agent classes (not instances)
    # REMOVED_SYNTAX_ERROR: 2. Is immutable after startup
    # REMOVED_SYNTAX_ERROR: 3. Has no per-user state
    # REMOVED_SYNTAX_ERROR: 4. Is thread-safe for concurrent reads
    # REMOVED_SYNTAX_ERROR: 5. Provides methods to get agent classes by name
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import threading
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_class_registry import ( )
    # REMOVED_SYNTAX_ERROR: AgentClassRegistry,
    # REMOVED_SYNTAX_ERROR: AgentClassInfo,
    # REMOVED_SYNTAX_ERROR: get_agent_class_registry,
    # REMOVED_SYNTAX_ERROR: create_test_registry
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState


# REMOVED_SYNTAX_ERROR: class MockAgent(BaseAgent):
    # REMOVED_SYNTAX_ERROR: """Mock agent for testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self, name: str = "MockAgent"):
    # REMOVED_SYNTAX_ERROR: super().__init__(name=name)

# REMOVED_SYNTAX_ERROR: async def execute_core_logic(self, context) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: return {"status": "mock_completed"}


# REMOVED_SYNTAX_ERROR: class AnotherMockAgent(BaseAgent):
    # REMOVED_SYNTAX_ERROR: """Another mock agent for testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self, name: str = "AnotherMockAgent"):
    # REMOVED_SYNTAX_ERROR: super().__init__(name=name)

# REMOVED_SYNTAX_ERROR: async def execute_core_logic(self, context) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: return {"status": "another_mock_completed"}


# REMOVED_SYNTAX_ERROR: class NonAgentClass:
    # REMOVED_SYNTAX_ERROR: """Non-agent class for testing invalid registrations."""
    # REMOVED_SYNTAX_ERROR: pass


# REMOVED_SYNTAX_ERROR: class TestAgentClassRegistry:
    # REMOVED_SYNTAX_ERROR: """Test suite for AgentClassRegistry."""

# REMOVED_SYNTAX_ERROR: def test_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Test registry initialization."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # REMOVED_SYNTAX_ERROR: assert not registry.is_frozen()
    # REMOVED_SYNTAX_ERROR: assert len(registry) == 0
    # REMOVED_SYNTAX_ERROR: assert registry.list_agent_names() == []
    # REMOVED_SYNTAX_ERROR: assert registry.get_registry_stats()["total_agent_classes"] == 0

# REMOVED_SYNTAX_ERROR: def test_register_agent_class(self):
    # REMOVED_SYNTAX_ERROR: """Test registering an agent class."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Test successful registration
    # REMOVED_SYNTAX_ERROR: registry.register("test_agent", MockAgent, "Test agent description")

    # REMOVED_SYNTAX_ERROR: assert len(registry) == 1
    # REMOVED_SYNTAX_ERROR: assert "test_agent" in registry
    # REMOVED_SYNTAX_ERROR: assert registry.has_agent_class("test_agent")
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("test_agent") == MockAgent

    # Test agent info retrieval
    # REMOVED_SYNTAX_ERROR: agent_info = registry.get_agent_info("test_agent")
    # REMOVED_SYNTAX_ERROR: assert agent_info is not None
    # REMOVED_SYNTAX_ERROR: assert agent_info.name == "test_agent"
    # REMOVED_SYNTAX_ERROR: assert agent_info.agent_class == MockAgent
    # REMOVED_SYNTAX_ERROR: assert agent_info.description == "Test agent description"
    # REMOVED_SYNTAX_ERROR: assert agent_info.version == "1.0.0"  # Default version
    # REMOVED_SYNTAX_ERROR: assert agent_info.dependencies == tuple()  # Default empty dependencies

# REMOVED_SYNTAX_ERROR: def test_register_with_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Test registering agent with full metadata."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # REMOVED_SYNTAX_ERROR: metadata = {"category": "test", "priority": "high"}
    # REMOVED_SYNTAX_ERROR: dependencies = ["dep1", "dep2"]

    # REMOVED_SYNTAX_ERROR: registry.register( )
    # REMOVED_SYNTAX_ERROR: "full_agent",
    # REMOVED_SYNTAX_ERROR: MockAgent,
    # REMOVED_SYNTAX_ERROR: "Full agent description",
    # REMOVED_SYNTAX_ERROR: version="2.1.0",
    # REMOVED_SYNTAX_ERROR: dependencies=dependencies,
    # REMOVED_SYNTAX_ERROR: metadata=metadata
    

    # REMOVED_SYNTAX_ERROR: agent_info = registry.get_agent_info("full_agent")
    # REMOVED_SYNTAX_ERROR: assert agent_info.version == "2.1.0"
    # REMOVED_SYNTAX_ERROR: assert agent_info.dependencies == ("dep1", "dep2")
    # REMOVED_SYNTAX_ERROR: assert agent_info.metadata == metadata

# REMOVED_SYNTAX_ERROR: def test_register_invalid_agent_class(self):
    # REMOVED_SYNTAX_ERROR: """Test registering invalid agent classes."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Test non-agent class
    # REMOVED_SYNTAX_ERROR: with pytest.raises(TypeError, match="must inherit from BaseAgent"):
        # REMOVED_SYNTAX_ERROR: registry.register("invalid", NonAgentClass, "Invalid class")

        # Test empty name
        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="must be a non-empty string"):
            # REMOVED_SYNTAX_ERROR: registry.register("", MockAgent, "Empty name")

            # Test None name
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="must be a non-empty string"):
                # REMOVED_SYNTAX_ERROR: registry.register(None, MockAgent, "None name")

                # Test non-class type
                # REMOVED_SYNTAX_ERROR: with pytest.raises(TypeError, match="must be a class type"):
                    # REMOVED_SYNTAX_ERROR: registry.register("invalid", "not_a_class", "Not a class")

# REMOVED_SYNTAX_ERROR: def test_duplicate_registration(self):
    # REMOVED_SYNTAX_ERROR: """Test duplicate agent registration."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Register agent
    # REMOVED_SYNTAX_ERROR: registry.register("test_agent", MockAgent, "Test description")

    # Try to register same agent with same class (should warn and skip)
    # REMOVED_SYNTAX_ERROR: registry.register("test_agent", MockAgent, "Different description")
    # REMOVED_SYNTAX_ERROR: assert len(registry) == 1  # Should still be 1

    # Try to register same name with different class (should raise error)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="already registered with different class"):
        # REMOVED_SYNTAX_ERROR: registry.register("test_agent", AnotherMockAgent, "Different class")

# REMOVED_SYNTAX_ERROR: def test_freeze_functionality(self):
    # REMOVED_SYNTAX_ERROR: """Test registry freezing functionality."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Register some agents
    # REMOVED_SYNTAX_ERROR: registry.register("agent1", MockAgent, "Agent 1")
    # REMOVED_SYNTAX_ERROR: registry.register("agent2", AnotherMockAgent, "Agent 2")

    # REMOVED_SYNTAX_ERROR: assert not registry.is_frozen()

    # Freeze the registry
    # REMOVED_SYNTAX_ERROR: registry.freeze()

    # REMOVED_SYNTAX_ERROR: assert registry.is_frozen()
    # REMOVED_SYNTAX_ERROR: stats = registry.get_registry_stats()
    # REMOVED_SYNTAX_ERROR: assert stats["frozen"] is True
    # REMOVED_SYNTAX_ERROR: assert stats["freeze_time"] is not None

    # Try to register after freezing (should raise error)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
        # REMOVED_SYNTAX_ERROR: registry.register("agent3", MockAgent, "Agent 3")

# REMOVED_SYNTAX_ERROR: def test_freeze_idempotent(self):
    # REMOVED_SYNTAX_ERROR: """Test that freezing is idempotent."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()
    # REMOVED_SYNTAX_ERROR: registry.register("agent1", MockAgent, "Agent 1")

    # Freeze multiple times
    # REMOVED_SYNTAX_ERROR: registry.freeze()
    # REMOVED_SYNTAX_ERROR: registry.freeze()  # Should not raise error

    # REMOVED_SYNTAX_ERROR: assert registry.is_frozen()

# REMOVED_SYNTAX_ERROR: def test_agent_retrieval(self):
    # REMOVED_SYNTAX_ERROR: """Test various methods to retrieve agent information."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # REMOVED_SYNTAX_ERROR: registry.register("agent1", MockAgent, "Agent 1")
    # REMOVED_SYNTAX_ERROR: registry.register("agent2", AnotherMockAgent, "Agent 2")

    # Test get_agent_class
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("agent1") == MockAgent
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("agent2") == AnotherMockAgent
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("nonexistent") is None

    # Test list_agent_names
    # REMOVED_SYNTAX_ERROR: names = registry.list_agent_names()
    # REMOVED_SYNTAX_ERROR: assert names == ["agent1", "agent2"]  # Should be sorted

    # Test get_all_agent_classes
    # REMOVED_SYNTAX_ERROR: all_classes = registry.get_all_agent_classes()
    # REMOVED_SYNTAX_ERROR: expected = {"agent1": MockAgent, "agent2": AnotherMockAgent}
    # REMOVED_SYNTAX_ERROR: assert all_classes == expected

    # Test has_agent_class
    # REMOVED_SYNTAX_ERROR: assert registry.has_agent_class("agent1") is True
    # REMOVED_SYNTAX_ERROR: assert registry.has_agent_class("nonexistent") is False

    # Test __contains__ operator
    # REMOVED_SYNTAX_ERROR: assert "agent1" in registry
    # REMOVED_SYNTAX_ERROR: assert "nonexistent" not in registry

# REMOVED_SYNTAX_ERROR: def test_dependency_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test dependency validation functionality."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Register agents with dependencies
    # REMOVED_SYNTAX_ERROR: registry.register("base_agent", MockAgent, "Base agent", dependencies=[])
    # REMOVED_SYNTAX_ERROR: registry.register("dependent_agent", AnotherMockAgent, "Dependent agent",
    # REMOVED_SYNTAX_ERROR: dependencies=["base_agent", "missing_dep"])

    # Validate dependencies
    # REMOVED_SYNTAX_ERROR: missing_deps = registry.validate_dependencies()

    # REMOVED_SYNTAX_ERROR: assert "base_agent" not in missing_deps  # Has no missing dependencies
    # REMOVED_SYNTAX_ERROR: assert "dependent_agent" in missing_deps
    # REMOVED_SYNTAX_ERROR: assert missing_deps["dependent_agent"] == ["missing_dep"]

    # Test get_agents_by_dependency
    # REMOVED_SYNTAX_ERROR: dependents = registry.get_agents_by_dependency("base_agent")
    # REMOVED_SYNTAX_ERROR: assert dependents == ["dependent_agent"]

    # REMOVED_SYNTAX_ERROR: dependents = registry.get_agents_by_dependency("nonexistent")
    # REMOVED_SYNTAX_ERROR: assert dependents == []

# REMOVED_SYNTAX_ERROR: def test_registry_stats(self):
    # REMOVED_SYNTAX_ERROR: """Test registry statistics functionality."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Empty registry stats
    # REMOVED_SYNTAX_ERROR: stats = registry.get_registry_stats()
    # REMOVED_SYNTAX_ERROR: assert stats["total_agent_classes"] == 0
    # REMOVED_SYNTAX_ERROR: assert stats["frozen"] is False
    # REMOVED_SYNTAX_ERROR: assert stats["health_status"] == "unhealthy"

    # Add agents and freeze
    # REMOVED_SYNTAX_ERROR: registry.register("agent1", MockAgent, "Agent 1")
    # REMOVED_SYNTAX_ERROR: registry.register("agent2", AnotherMockAgent, "Agent 2")
    # REMOVED_SYNTAX_ERROR: registry.freeze()

    # REMOVED_SYNTAX_ERROR: stats = registry.get_registry_stats()
    # REMOVED_SYNTAX_ERROR: assert stats["total_agent_classes"] == 2
    # REMOVED_SYNTAX_ERROR: assert stats["frozen"] is True
    # REMOVED_SYNTAX_ERROR: assert stats["health_status"] == "healthy"
    # REMOVED_SYNTAX_ERROR: assert "agent1" in stats["agent_names"]
    # REMOVED_SYNTAX_ERROR: assert "agent2" in stats["agent_names"]

# REMOVED_SYNTAX_ERROR: def test_agent_class_info_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test AgentClassInfo validation."""
    # Valid agent class info
    # REMOVED_SYNTAX_ERROR: info = AgentClassInfo( )
    # REMOVED_SYNTAX_ERROR: name="test",
    # REMOVED_SYNTAX_ERROR: agent_class=MockAgent,
    # REMOVED_SYNTAX_ERROR: description="Test description",
    # REMOVED_SYNTAX_ERROR: version="1.0.0",
    # REMOVED_SYNTAX_ERROR: dependencies=["dep1", "dep2"],
    # REMOVED_SYNTAX_ERROR: metadata={"key": "value"}
    

    # REMOVED_SYNTAX_ERROR: assert info.name == "test"
    # REMOVED_SYNTAX_ERROR: assert info.agent_class == MockAgent
    # REMOVED_SYNTAX_ERROR: assert info.dependencies == ("dep1", "dep2")  # Should be converted to tuple

    # Invalid agent class
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="must inherit from BaseAgent"):
        # REMOVED_SYNTAX_ERROR: AgentClassInfo( )
        # REMOVED_SYNTAX_ERROR: name="test",
        # REMOVED_SYNTAX_ERROR: agent_class=NonAgentClass,
        # REMOVED_SYNTAX_ERROR: description="Test",
        # REMOVED_SYNTAX_ERROR: version="1.0.0",
        # REMOVED_SYNTAX_ERROR: dependencies=[],
        # REMOVED_SYNTAX_ERROR: metadata={}
        

        # Empty name
        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="cannot be empty"):
            # REMOVED_SYNTAX_ERROR: AgentClassInfo( )
            # REMOVED_SYNTAX_ERROR: name="",
            # REMOVED_SYNTAX_ERROR: agent_class=MockAgent,
            # REMOVED_SYNTAX_ERROR: description="Test",
            # REMOVED_SYNTAX_ERROR: version="1.0.0",
            # REMOVED_SYNTAX_ERROR: dependencies=[],
            # REMOVED_SYNTAX_ERROR: metadata={}
            


# REMOVED_SYNTAX_ERROR: class TestAgentClassRegistryThreadSafety:
    # REMOVED_SYNTAX_ERROR: """Test thread safety of AgentClassRegistry."""

# REMOVED_SYNTAX_ERROR: def test_concurrent_reads_after_freeze(self):
    # REMOVED_SYNTAX_ERROR: """Test that concurrent reads work safely after registry is frozen."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # Register agents and freeze
    # REMOVED_SYNTAX_ERROR: registry.register("agent1", MockAgent, "Agent 1")
    # REMOVED_SYNTAX_ERROR: registry.register("agent2", AnotherMockAgent, "Agent 2")
    # REMOVED_SYNTAX_ERROR: registry.freeze()

    # REMOVED_SYNTAX_ERROR: results = []
    # REMOVED_SYNTAX_ERROR: errors = []

# REMOVED_SYNTAX_ERROR: def read_operations():
    # REMOVED_SYNTAX_ERROR: """Perform multiple read operations."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: for _ in range(100):
            # Various read operations
            # REMOVED_SYNTAX_ERROR: agent_class = registry.get_agent_class("agent1")
            # REMOVED_SYNTAX_ERROR: agent_names = registry.list_agent_names()
            # REMOVED_SYNTAX_ERROR: has_agent = registry.has_agent_class("agent2")
            # REMOVED_SYNTAX_ERROR: stats = registry.get_registry_stats()

            # REMOVED_SYNTAX_ERROR: results.append({ ))
            # REMOVED_SYNTAX_ERROR: "agent_class": agent_class,
            # REMOVED_SYNTAX_ERROR: "agent_names": agent_names,
            # REMOVED_SYNTAX_ERROR: "has_agent": has_agent,
            # REMOVED_SYNTAX_ERROR: "stats": stats
            
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: errors.append(e)

                # Start multiple threads
                # REMOVED_SYNTAX_ERROR: threads = []
                # REMOVED_SYNTAX_ERROR: for _ in range(10):
                    # REMOVED_SYNTAX_ERROR: thread = threading.Thread(target=read_operations)
                    # REMOVED_SYNTAX_ERROR: threads.append(thread)
                    # REMOVED_SYNTAX_ERROR: thread.start()

                    # Wait for all threads to complete
                    # REMOVED_SYNTAX_ERROR: for thread in threads:
                        # REMOVED_SYNTAX_ERROR: thread.join()

                        # Verify no errors occurred
                        # REMOVED_SYNTAX_ERROR: assert len(errors) == 0, "formatted_string"

                        # Verify consistent results
                        # REMOVED_SYNTAX_ERROR: assert len(results) > 0
                        # REMOVED_SYNTAX_ERROR: first_result = results[0]
                        # REMOVED_SYNTAX_ERROR: for result in results:
                            # REMOVED_SYNTAX_ERROR: assert result["agent_class"] == first_result["agent_class"]
                            # REMOVED_SYNTAX_ERROR: assert result["agent_names"] == first_result["agent_names"]
                            # REMOVED_SYNTAX_ERROR: assert result["has_agent"] == first_result["has_agent"]

# REMOVED_SYNTAX_ERROR: def test_registration_thread_safety(self):
    # REMOVED_SYNTAX_ERROR: """Test that registration is thread-safe during startup phase."""
    # REMOVED_SYNTAX_ERROR: registry = AgentClassRegistry()

    # REMOVED_SYNTAX_ERROR: registration_results = []
    # REMOVED_SYNTAX_ERROR: errors = []

# REMOVED_SYNTAX_ERROR: def register_agents(start_id: int):
    # REMOVED_SYNTAX_ERROR: """Register agents with unique names."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: for i in range(5):
            # REMOVED_SYNTAX_ERROR: name = "formatted_string"
            # REMOVED_SYNTAX_ERROR: registry.register(name, MockAgent, "formatted_string")
            # REMOVED_SYNTAX_ERROR: registration_results.append(name)
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: errors.append(e)

                # Start multiple registration threads
                # REMOVED_SYNTAX_ERROR: threads = []
                # REMOVED_SYNTAX_ERROR: for thread_id in range(3):
                    # REMOVED_SYNTAX_ERROR: thread = threading.Thread(target=register_agents, args=(thread_id,))
                    # REMOVED_SYNTAX_ERROR: threads.append(thread)
                    # REMOVED_SYNTAX_ERROR: thread.start()

                    # Wait for all threads
                    # REMOVED_SYNTAX_ERROR: for thread in threads:
                        # REMOVED_SYNTAX_ERROR: thread.join()

                        # Verify no errors and all agents registered
                        # REMOVED_SYNTAX_ERROR: assert len(errors) == 0, "formatted_string"
                        # REMOVED_SYNTAX_ERROR: assert len(registry) == 15  # 3 threads * 5 agents each
                        # REMOVED_SYNTAX_ERROR: assert len(set(registration_results)) == 15  # All unique names


# REMOVED_SYNTAX_ERROR: class TestGlobalRegistry:
    # REMOVED_SYNTAX_ERROR: """Test global registry singleton functionality."""

# REMOVED_SYNTAX_ERROR: def test_singleton_behavior(self):
    # REMOVED_SYNTAX_ERROR: """Test that get_agent_class_registry returns the same instance."""
    # REMOVED_SYNTAX_ERROR: registry1 = get_agent_class_registry()
    # REMOVED_SYNTAX_ERROR: registry2 = get_agent_class_registry()

    # REMOVED_SYNTAX_ERROR: assert registry1 is registry2
    # REMOVED_SYNTAX_ERROR: assert isinstance(registry1, AgentClassRegistry)

# REMOVED_SYNTAX_ERROR: def test_create_test_registry(self):
    # REMOVED_SYNTAX_ERROR: """Test that create_test_registry returns a separate instance."""
    # REMOVED_SYNTAX_ERROR: global_registry = get_agent_class_registry()
    # REMOVED_SYNTAX_ERROR: test_registry = create_test_registry()

    # REMOVED_SYNTAX_ERROR: assert test_registry is not global_registry
    # REMOVED_SYNTAX_ERROR: assert isinstance(test_registry, AgentClassRegistry)

    # Verify they operate independently
    # REMOVED_SYNTAX_ERROR: test_registry.register("test_agent", MockAgent, "Test")

    # REMOVED_SYNTAX_ERROR: assert test_registry.has_agent_class("test_agent")
    # REMOVED_SYNTAX_ERROR: assert not global_registry.has_agent_class("test_agent")


# REMOVED_SYNTAX_ERROR: class TestAgentClassRegistryIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for AgentClassRegistry."""

# REMOVED_SYNTAX_ERROR: def test_full_lifecycle(self):
    # REMOVED_SYNTAX_ERROR: """Test the complete lifecycle of the registry."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Phase 1: Registration (startup)
    # REMOVED_SYNTAX_ERROR: registry.register("triage", MockAgent, "Triage agent",
    # REMOVED_SYNTAX_ERROR: dependencies=[], metadata={"priority": "high"])
    # REMOVED_SYNTAX_ERROR: registry.register("data", AnotherMockAgent, "Data agent",
    # REMOVED_SYNTAX_ERROR: dependencies=["triage"], metadata={"priority": "medium"])

    # REMOVED_SYNTAX_ERROR: assert not registry.is_frozen()
    # REMOVED_SYNTAX_ERROR: assert len(registry) == 2

    # Phase 2: Freeze (startup completion)
    # REMOVED_SYNTAX_ERROR: registry.freeze()

    # REMOVED_SYNTAX_ERROR: assert registry.is_frozen()

    # Phase 3: Runtime usage (concurrent, read-only)
    # REMOVED_SYNTAX_ERROR: triage_class = registry.get_agent_class("triage")
    # REMOVED_SYNTAX_ERROR: data_class = registry.get_agent_class("data")

    # REMOVED_SYNTAX_ERROR: assert triage_class == MockAgent
    # REMOVED_SYNTAX_ERROR: assert data_class == AnotherMockAgent

    # Instantiate agents (this is what happens at runtime)
    # REMOVED_SYNTAX_ERROR: triage_agent = triage_class("triage_instance")
    # REMOVED_SYNTAX_ERROR: data_agent = data_class("data_instance")

    # REMOVED_SYNTAX_ERROR: assert isinstance(triage_agent, MockAgent)
    # REMOVED_SYNTAX_ERROR: assert isinstance(data_agent, AnotherMockAgent)
    # REMOVED_SYNTAX_ERROR: assert triage_agent.name == "triage_instance"
    # REMOVED_SYNTAX_ERROR: assert data_agent.name == "data_instance"

    # Verify dependency validation
    # REMOVED_SYNTAX_ERROR: missing_deps = registry.validate_dependencies()
    # REMOVED_SYNTAX_ERROR: assert len(missing_deps) == 0  # All dependencies satisfied

    # Verify stats
    # REMOVED_SYNTAX_ERROR: stats = registry.get_registry_stats()
    # REMOVED_SYNTAX_ERROR: assert stats["health_status"] == "healthy"
    # REMOVED_SYNTAX_ERROR: assert stats["total_agent_classes"] == 2

# REMOVED_SYNTAX_ERROR: def test_error_scenarios(self):
    # REMOVED_SYNTAX_ERROR: """Test various error scenarios."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register valid agent
    # REMOVED_SYNTAX_ERROR: registry.register("valid", MockAgent, "Valid agent")

    # Freeze registry
    # REMOVED_SYNTAX_ERROR: registry.freeze()

    # Test operations on non-existent agents
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("nonexistent") is None
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_info("nonexistent") is None
    # REMOVED_SYNTAX_ERROR: assert not registry.has_agent_class("nonexistent")

    # Test post-freeze registration error
    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
        # REMOVED_SYNTAX_ERROR: registry.register("post_freeze", MockAgent, "Should fail")

        # Verify registry integrity after errors
        # REMOVED_SYNTAX_ERROR: assert len(registry) == 1
        # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("valid") == MockAgent


        # Performance and stress tests
# REMOVED_SYNTAX_ERROR: class TestAgentClassRegistryPerformance:
    # REMOVED_SYNTAX_ERROR: """Performance tests for AgentClassRegistry."""

# REMOVED_SYNTAX_ERROR: def test_large_registry_performance(self):
    # REMOVED_SYNTAX_ERROR: """Test performance with a large number of registered agents."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register many agents
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: for i in range(1000):
        # REMOVED_SYNTAX_ERROR: registry.register("formatted_string", MockAgent, "formatted_string")
        # REMOVED_SYNTAX_ERROR: registration_time = time.time() - start_time

        # REMOVED_SYNTAX_ERROR: registry.freeze()

        # Test retrieval performance
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: for i in range(1000):
            # REMOVED_SYNTAX_ERROR: agent_class = registry.get_agent_class("formatted_string")
            # REMOVED_SYNTAX_ERROR: assert agent_class == MockAgent
            # REMOVED_SYNTAX_ERROR: retrieval_time = time.time() - start_time

            # Performance should be reasonable
            # REMOVED_SYNTAX_ERROR: assert registration_time < 5.0  # 5 seconds max for 1000 registrations
            # REMOVED_SYNTAX_ERROR: assert retrieval_time < 1.0     # 1 second max for 1000 retrievals
            # REMOVED_SYNTAX_ERROR: assert len(registry) == 1000

# REMOVED_SYNTAX_ERROR: def test_concurrent_access_performance(self):
    # REMOVED_SYNTAX_ERROR: """Test performance under concurrent access."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register agents
    # REMOVED_SYNTAX_ERROR: for i in range(100):
        # REMOVED_SYNTAX_ERROR: registry.register("formatted_string", MockAgent, "formatted_string")

        # REMOVED_SYNTAX_ERROR: registry.freeze()

        # REMOVED_SYNTAX_ERROR: results = []

# REMOVED_SYNTAX_ERROR: def access_agents():
    # REMOVED_SYNTAX_ERROR: """Access agents concurrently."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: for i in range(100):
        # REMOVED_SYNTAX_ERROR: agent_class = registry.get_agent_class("formatted_string")
        # REMOVED_SYNTAX_ERROR: assert agent_class == MockAgent
        # REMOVED_SYNTAX_ERROR: end_time = time.time()
        # REMOVED_SYNTAX_ERROR: results.append(end_time - start_time)

        # Start multiple threads
        # REMOVED_SYNTAX_ERROR: threads = []
        # REMOVED_SYNTAX_ERROR: for _ in range(20):
            # REMOVED_SYNTAX_ERROR: thread = threading.Thread(target=access_agents)
            # REMOVED_SYNTAX_ERROR: threads.append(thread)
            # REMOVED_SYNTAX_ERROR: thread.start()

            # Wait for completion
            # REMOVED_SYNTAX_ERROR: for thread in threads:
                # REMOVED_SYNTAX_ERROR: thread.join()

                # All threads should complete quickly
                # REMOVED_SYNTAX_ERROR: assert len(results) == 20
                # REMOVED_SYNTAX_ERROR: assert all(result < 1.0 for result in results)  # Each thread under 1 second