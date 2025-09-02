"""
Tests for AgentClassRegistry: Infrastructure-only agent class registration.

CRITICAL: These tests verify that the AgentClassRegistry meets all requirements:
1. Stores only agent classes (not instances)
2. Is immutable after startup
3. Has no per-user state 
4. Is thread-safe for concurrent reads
5. Provides methods to get agent classes by name
"""

import pytest
import threading
import time
from typing import Dict, Any
from unittest.mock import Mock, patch

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_class_registry import (
    AgentClassRegistry,
    AgentClassInfo,
    get_agent_class_registry,
    create_test_registry
)
from netra_backend.app.agents.state import DeepAgentState


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, name: str = "MockAgent"):
        super().__init__(name=name)
    
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        return {"status": "mock_completed"}


class AnotherMockAgent(BaseAgent):
    """Another mock agent for testing."""
    
    def __init__(self, name: str = "AnotherMockAgent"):
        super().__init__(name=name)
    
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        return {"status": "another_mock_completed"}


class NonAgentClass:
    """Non-agent class for testing invalid registrations."""
    pass


class TestAgentClassRegistry:
    """Test suite for AgentClassRegistry."""
    
    def test_initialization(self):
        """Test registry initialization."""
        registry = AgentClassRegistry()
        
        assert not registry.is_frozen()
        assert len(registry) == 0
        assert registry.list_agent_names() == []
        assert registry.get_registry_stats()["total_agent_classes"] == 0
    
    def test_register_agent_class(self):
        """Test registering an agent class."""
        registry = AgentClassRegistry()
        
        # Test successful registration
        registry.register("test_agent", MockAgent, "Test agent description")
        
        assert len(registry) == 1
        assert "test_agent" in registry
        assert registry.has_agent_class("test_agent")
        assert registry.get_agent_class("test_agent") == MockAgent
        
        # Test agent info retrieval
        agent_info = registry.get_agent_info("test_agent")
        assert agent_info is not None
        assert agent_info.name == "test_agent"
        assert agent_info.agent_class == MockAgent
        assert agent_info.description == "Test agent description"
        assert agent_info.version == "1.0.0"  # Default version
        assert agent_info.dependencies == tuple()  # Default empty dependencies
    
    def test_register_with_metadata(self):
        """Test registering agent with full metadata."""
        registry = AgentClassRegistry()
        
        metadata = {"category": "test", "priority": "high"}
        dependencies = ["dep1", "dep2"]
        
        registry.register(
            "full_agent",
            MockAgent,
            "Full agent description",
            version="2.1.0",
            dependencies=dependencies,
            metadata=metadata
        )
        
        agent_info = registry.get_agent_info("full_agent")
        assert agent_info.version == "2.1.0"
        assert agent_info.dependencies == ("dep1", "dep2")
        assert agent_info.metadata == metadata
    
    def test_register_invalid_agent_class(self):
        """Test registering invalid agent classes."""
        registry = AgentClassRegistry()
        
        # Test non-agent class
        with pytest.raises(TypeError, match="must inherit from BaseAgent"):
            registry.register("invalid", NonAgentClass, "Invalid class")
        
        # Test empty name
        with pytest.raises(ValueError, match="must be a non-empty string"):
            registry.register("", MockAgent, "Empty name")
        
        # Test None name
        with pytest.raises(ValueError, match="must be a non-empty string"):
            registry.register(None, MockAgent, "None name")
        
        # Test non-class type
        with pytest.raises(TypeError, match="must be a class type"):
            registry.register("invalid", "not_a_class", "Not a class")
    
    def test_duplicate_registration(self):
        """Test duplicate agent registration."""
        registry = AgentClassRegistry()
        
        # Register agent
        registry.register("test_agent", MockAgent, "Test description")
        
        # Try to register same agent with same class (should warn and skip)
        registry.register("test_agent", MockAgent, "Different description")
        assert len(registry) == 1  # Should still be 1
        
        # Try to register same name with different class (should raise error)
        with pytest.raises(ValueError, match="already registered with different class"):
            registry.register("test_agent", AnotherMockAgent, "Different class")
    
    def test_freeze_functionality(self):
        """Test registry freezing functionality."""
        registry = AgentClassRegistry()
        
        # Register some agents
        registry.register("agent1", MockAgent, "Agent 1")
        registry.register("agent2", AnotherMockAgent, "Agent 2")
        
        assert not registry.is_frozen()
        
        # Freeze the registry
        registry.freeze()
        
        assert registry.is_frozen()
        stats = registry.get_registry_stats()
        assert stats["frozen"] is True
        assert stats["freeze_time"] is not None
        
        # Try to register after freezing (should raise error)
        with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
            registry.register("agent3", MockAgent, "Agent 3")
    
    def test_freeze_idempotent(self):
        """Test that freezing is idempotent."""
        registry = AgentClassRegistry()
        registry.register("agent1", MockAgent, "Agent 1")
        
        # Freeze multiple times
        registry.freeze()
        registry.freeze()  # Should not raise error
        
        assert registry.is_frozen()
    
    def test_agent_retrieval(self):
        """Test various methods to retrieve agent information."""
        registry = AgentClassRegistry()
        
        registry.register("agent1", MockAgent, "Agent 1")
        registry.register("agent2", AnotherMockAgent, "Agent 2")
        
        # Test get_agent_class
        assert registry.get_agent_class("agent1") == MockAgent
        assert registry.get_agent_class("agent2") == AnotherMockAgent
        assert registry.get_agent_class("nonexistent") is None
        
        # Test list_agent_names
        names = registry.list_agent_names()
        assert names == ["agent1", "agent2"]  # Should be sorted
        
        # Test get_all_agent_classes
        all_classes = registry.get_all_agent_classes()
        expected = {"agent1": MockAgent, "agent2": AnotherMockAgent}
        assert all_classes == expected
        
        # Test has_agent_class
        assert registry.has_agent_class("agent1") is True
        assert registry.has_agent_class("nonexistent") is False
        
        # Test __contains__ operator
        assert "agent1" in registry
        assert "nonexistent" not in registry
    
    def test_dependency_validation(self):
        """Test dependency validation functionality."""
        registry = AgentClassRegistry()
        
        # Register agents with dependencies
        registry.register("base_agent", MockAgent, "Base agent", dependencies=[])
        registry.register("dependent_agent", AnotherMockAgent, "Dependent agent", 
                         dependencies=["base_agent", "missing_dep"])
        
        # Validate dependencies
        missing_deps = registry.validate_dependencies()
        
        assert "base_agent" not in missing_deps  # Has no missing dependencies
        assert "dependent_agent" in missing_deps
        assert missing_deps["dependent_agent"] == ["missing_dep"]
        
        # Test get_agents_by_dependency
        dependents = registry.get_agents_by_dependency("base_agent")
        assert dependents == ["dependent_agent"]
        
        dependents = registry.get_agents_by_dependency("nonexistent")
        assert dependents == []
    
    def test_registry_stats(self):
        """Test registry statistics functionality."""
        registry = AgentClassRegistry()
        
        # Empty registry stats
        stats = registry.get_registry_stats()
        assert stats["total_agent_classes"] == 0
        assert stats["frozen"] is False
        assert stats["health_status"] == "unhealthy"
        
        # Add agents and freeze
        registry.register("agent1", MockAgent, "Agent 1")
        registry.register("agent2", AnotherMockAgent, "Agent 2")
        registry.freeze()
        
        stats = registry.get_registry_stats()
        assert stats["total_agent_classes"] == 2
        assert stats["frozen"] is True
        assert stats["health_status"] == "healthy"
        assert "agent1" in stats["agent_names"]
        assert "agent2" in stats["agent_names"]
    
    def test_agent_class_info_validation(self):
        """Test AgentClassInfo validation."""
        # Valid agent class info
        info = AgentClassInfo(
            name="test",
            agent_class=MockAgent,
            description="Test description",
            version="1.0.0",
            dependencies=["dep1", "dep2"],
            metadata={"key": "value"}
        )
        
        assert info.name == "test"
        assert info.agent_class == MockAgent
        assert info.dependencies == ("dep1", "dep2")  # Should be converted to tuple
        
        # Invalid agent class
        with pytest.raises(ValueError, match="must inherit from BaseAgent"):
            AgentClassInfo(
                name="test",
                agent_class=NonAgentClass,
                description="Test",
                version="1.0.0",
                dependencies=[],
                metadata={}
            )
        
        # Empty name
        with pytest.raises(ValueError, match="cannot be empty"):
            AgentClassInfo(
                name="",
                agent_class=MockAgent,
                description="Test",
                version="1.0.0", 
                dependencies=[],
                metadata={}
            )


class TestAgentClassRegistryThreadSafety:
    """Test thread safety of AgentClassRegistry."""
    
    def test_concurrent_reads_after_freeze(self):
        """Test that concurrent reads work safely after registry is frozen."""
        registry = AgentClassRegistry()
        
        # Register agents and freeze
        registry.register("agent1", MockAgent, "Agent 1")
        registry.register("agent2", AnotherMockAgent, "Agent 2")
        registry.freeze()
        
        results = []
        errors = []
        
        def read_operations():
            """Perform multiple read operations."""
            try:
                for _ in range(100):
                    # Various read operations
                    agent_class = registry.get_agent_class("agent1")
                    agent_names = registry.list_agent_names()
                    has_agent = registry.has_agent_class("agent2")
                    stats = registry.get_registry_stats()
                    
                    results.append({
                        "agent_class": agent_class,
                        "agent_names": agent_names,
                        "has_agent": has_agent,
                        "stats": stats
                    })
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=read_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread errors: {errors}"
        
        # Verify consistent results
        assert len(results) > 0
        first_result = results[0]
        for result in results:
            assert result["agent_class"] == first_result["agent_class"]
            assert result["agent_names"] == first_result["agent_names"]
            assert result["has_agent"] == first_result["has_agent"]
    
    def test_registration_thread_safety(self):
        """Test that registration is thread-safe during startup phase."""
        registry = AgentClassRegistry()
        
        registration_results = []
        errors = []
        
        def register_agents(start_id: int):
            """Register agents with unique names."""
            try:
                for i in range(5):
                    name = f"agent_{start_id}_{i}"
                    registry.register(name, MockAgent, f"Agent {name}")
                    registration_results.append(name)
            except Exception as e:
                errors.append(e)
        
        # Start multiple registration threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(target=register_agents, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors and all agents registered
        assert len(errors) == 0, f"Registration errors: {errors}"
        assert len(registry) == 15  # 3 threads * 5 agents each
        assert len(set(registration_results)) == 15  # All unique names


class TestGlobalRegistry:
    """Test global registry singleton functionality."""
    
    def test_singleton_behavior(self):
        """Test that get_agent_class_registry returns the same instance."""
        registry1 = get_agent_class_registry()
        registry2 = get_agent_class_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, AgentClassRegistry)
    
    def test_create_test_registry(self):
        """Test that create_test_registry returns a separate instance."""
        global_registry = get_agent_class_registry()
        test_registry = create_test_registry()
        
        assert test_registry is not global_registry
        assert isinstance(test_registry, AgentClassRegistry)
        
        # Verify they operate independently
        test_registry.register("test_agent", MockAgent, "Test")
        
        assert test_registry.has_agent_class("test_agent")
        assert not global_registry.has_agent_class("test_agent")


class TestAgentClassRegistryIntegration:
    """Integration tests for AgentClassRegistry."""
    
    def test_full_lifecycle(self):
        """Test the complete lifecycle of the registry."""
        registry = create_test_registry()
        
        # Phase 1: Registration (startup)
        registry.register("triage", MockAgent, "Triage agent", 
                         dependencies=[], metadata={"priority": "high"})
        registry.register("data", AnotherMockAgent, "Data agent",
                         dependencies=["triage"], metadata={"priority": "medium"})
        
        assert not registry.is_frozen()
        assert len(registry) == 2
        
        # Phase 2: Freeze (startup completion)
        registry.freeze()
        
        assert registry.is_frozen()
        
        # Phase 3: Runtime usage (concurrent, read-only)
        triage_class = registry.get_agent_class("triage")
        data_class = registry.get_agent_class("data")
        
        assert triage_class == MockAgent
        assert data_class == AnotherMockAgent
        
        # Instantiate agents (this is what happens at runtime)
        triage_agent = triage_class("triage_instance")
        data_agent = data_class("data_instance")
        
        assert isinstance(triage_agent, MockAgent)
        assert isinstance(data_agent, AnotherMockAgent)
        assert triage_agent.name == "triage_instance"
        assert data_agent.name == "data_instance"
        
        # Verify dependency validation
        missing_deps = registry.validate_dependencies()
        assert len(missing_deps) == 0  # All dependencies satisfied
        
        # Verify stats
        stats = registry.get_registry_stats()
        assert stats["health_status"] == "healthy"
        assert stats["total_agent_classes"] == 2
    
    def test_error_scenarios(self):
        """Test various error scenarios."""
        registry = create_test_registry()
        
        # Register valid agent
        registry.register("valid", MockAgent, "Valid agent")
        
        # Freeze registry
        registry.freeze()
        
        # Test operations on non-existent agents
        assert registry.get_agent_class("nonexistent") is None
        assert registry.get_agent_info("nonexistent") is None
        assert not registry.has_agent_class("nonexistent")
        
        # Test post-freeze registration error
        with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
            registry.register("post_freeze", MockAgent, "Should fail")
        
        # Verify registry integrity after errors
        assert len(registry) == 1
        assert registry.get_agent_class("valid") == MockAgent


# Performance and stress tests
class TestAgentClassRegistryPerformance:
    """Performance tests for AgentClassRegistry."""
    
    def test_large_registry_performance(self):
        """Test performance with a large number of registered agents."""
        registry = create_test_registry()
        
        # Register many agents
        start_time = time.time()
        for i in range(1000):
            registry.register(f"agent_{i}", MockAgent, f"Agent {i}")
        registration_time = time.time() - start_time
        
        registry.freeze()
        
        # Test retrieval performance
        start_time = time.time()
        for i in range(1000):
            agent_class = registry.get_agent_class(f"agent_{i}")
            assert agent_class == MockAgent
        retrieval_time = time.time() - start_time
        
        # Performance should be reasonable
        assert registration_time < 5.0  # 5 seconds max for 1000 registrations
        assert retrieval_time < 1.0     # 1 second max for 1000 retrievals
        assert len(registry) == 1000
    
    def test_concurrent_access_performance(self):
        """Test performance under concurrent access."""
        registry = create_test_registry()
        
        # Register agents
        for i in range(100):
            registry.register(f"agent_{i}", MockAgent, f"Agent {i}")
        
        registry.freeze()
        
        results = []
        
        def access_agents():
            """Access agents concurrently."""
            start_time = time.time()
            for i in range(100):
                agent_class = registry.get_agent_class(f"agent_{i}")
                assert agent_class == MockAgent
            end_time = time.time()
            results.append(end_time - start_time)
        
        # Start multiple threads
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=access_agents)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All threads should complete quickly
        assert len(results) == 20
        assert all(result < 1.0 for result in results)  # Each thread under 1 second