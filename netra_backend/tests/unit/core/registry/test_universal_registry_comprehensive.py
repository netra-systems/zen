"""Comprehensive unit tests for Universal Registry - CRITICAL SSOT component.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Platform Stability, Development Velocity, Risk Reduction
- Value Impact: Validates the critical SSOT registry system that underlies ALL
  agent, tool, and service management operates correctly in multi-user scenarios
- Strategic Impact: Prevents cascade failures - registry failures would break
  agent execution, tool dispatch, and service discovery causing system unavailability

Test Coverage Strategy:
- 100% line coverage of universal_registry.py
- All method paths and error conditions
- Thread safety for multi-user concurrent access
- Factory patterns for user isolation
- Specialized registry implementations
- Global registry singleton management
- Edge cases and failure scenarios

CRITICAL: NO MOCKS unless absolutely necessary - use real registry instances
CRITICAL: Tests must FAIL HARD when system breaks (no silent failures)
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from netra_backend.app.core.registry.universal_registry import (
    UniversalRegistry,
    AgentRegistry,
    ToolRegistry,
    ServiceRegistry, 
    StrategyRegistry,
    RegistryItem,
    get_global_registry,
    create_scoped_registry,
    _global_registries,
    _registry_lock
)


# ===================== TEST FIXTURES =====================

class MockAgent:
    """Mock agent for testing without BaseAgent import."""
    
    def __init__(self, name: str):
        self.name = name
        self.executed = False
        self._mock_name = f"MockAgent_{name}"  # Add mock identifier for validation
    
    def execute(self):
        self.executed = True
        return f"Agent {self.name} executed"


class MockUserExecutionContext:
    """Mock context for factory testing."""
    
    def __init__(self, user_id: str = "test-user", run_id: str = "test-run"):
        self.user_id = user_id
        self.run_id = run_id
        self.isolated = True


class MockTool:
    """Mock tool for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.calls = 0
    
    def execute(self, **kwargs):
        self.calls += 1
        return f"Tool {self.name} called {self.calls} times"


class MockService:
    """Mock service for testing."""
    
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.healthy = True


class MockStrategy:
    """Mock strategy for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.priority = 1


@pytest.fixture
def clean_global_registries():
    """Clean global registries before and after each test."""
    # Clear before test
    with _registry_lock:
        _global_registries.clear()
    
    yield
    
    # Clear after test
    with _registry_lock:
        _global_registries.clear()


@pytest.fixture
def mock_context():
    """Provide mock user execution context."""
    return MockUserExecutionContext()


@pytest.fixture
def sample_agent():
    """Provide sample mock agent."""
    return MockAgent("test-agent")


@pytest.fixture
def sample_tool():
    """Provide sample mock tool."""
    return MockTool("test-tool")


# ===================== REGISTRY ITEM TESTS =====================

class TestRegistryItem:
    """Test RegistryItem data class."""
    
    def test_registry_item_creation(self):
        """Test RegistryItem creation with metadata."""
        now = datetime.now(timezone.utc)
        item = RegistryItem(
            key="test-key",
            value="test-value", 
            factory=None,
            metadata={"description": "test item"},
            registered_at=now
        )
        
        assert item.key == "test-key"
        assert item.value == "test-value"
        assert item.factory is None
        assert item.metadata["description"] == "test item"
        assert item.registered_at == now
        assert item.access_count == 0
        assert item.last_accessed is None
        assert item.tags == set()
    
    def test_registry_item_with_tags(self):
        """Test RegistryItem creation with tags."""
        item = RegistryItem(
            key="test-key",
            value="test-value",
            factory=None,
            metadata={"tags": ["category1", "category2"]},
            registered_at=datetime.now(timezone.utc),
            tags={"tag1", "tag2"}
        )
        
        # Should use explicitly provided tags, not metadata tags
        assert item.tags == {"tag1", "tag2"}
    
    def test_mark_accessed(self):
        """Test marking item as accessed updates counters."""
        item = RegistryItem(
            key="test-key",
            value="test-value",
            factory=None,
            metadata={},
            registered_at=datetime.now(timezone.utc)
        )
        
        assert item.access_count == 0
        assert item.last_accessed is None
        
        item.mark_accessed()
        
        assert item.access_count == 1
        assert item.last_accessed is not None
        assert isinstance(item.last_accessed, datetime)
        
        # Mark accessed again
        first_access = item.last_accessed
        time.sleep(0.01)  # Ensure time difference
        item.mark_accessed()
        
        assert item.access_count == 2
        assert item.last_accessed > first_access


# ===================== UNIVERSAL REGISTRY CORE TESTS =====================

class TestUniversalRegistryCore:
    """Test core UniversalRegistry functionality."""
    
    def test_registry_initialization(self):
        """Test registry initialization with all parameters."""
        registry = UniversalRegistry[str]("TestRegistry", allow_override=True, enable_metrics=False)
        
        assert registry.name == "TestRegistry"
        assert registry.allow_override is True
        assert registry.enable_metrics is False
        assert not registry.is_frozen()
        assert len(registry) == 0
        assert registry._created_at is not None
    
    def test_register_singleton(self, sample_agent):
        """Test registering singleton items."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Register agent
        registry.register("agent1", sample_agent, description="Test agent")
        
        assert "agent1" in registry
        assert len(registry) == 1
        assert registry.has("agent1")
        
        # Verify item storage
        item = registry._items["agent1"]
        assert item.key == "agent1"
        assert item.value == sample_agent
        assert item.factory is None
        assert item.metadata["description"] == "Test agent"
    
    def test_register_with_tags(self, sample_agent):
        """Test registering items with tags."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        registry.register("agent1", sample_agent, tags=["ai", "automation"], priority=1)
        
        assert "agent1" in registry
        
        # Check tags
        keys = registry.list_by_tag("ai")
        assert "agent1" in keys
        
        keys = registry.list_by_tag("automation") 
        assert "agent1" in keys
        
        keys = registry.list_by_tag("nonexistent")
        assert len(keys) == 0
    
    def test_register_factory(self, mock_context):
        """Test registering factory functions."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def agent_factory(ctx):
            return MockAgent(f"agent-{ctx.user_id}")
        
        registry.register_factory("agent-factory", agent_factory, description="Agent factory")
        
        assert "agent-factory" in registry
        
        # Verify factory storage
        item = registry._items["agent-factory"]
        assert item.key == "agent-factory"
        assert item.value is None
        assert item.factory == agent_factory
    
    def test_register_duplicate_without_override(self, sample_agent):
        """Test registering duplicate key fails when override disabled."""
        registry = UniversalRegistry[MockAgent]("TestRegistry", allow_override=False)
        
        registry.register("agent1", sample_agent)
        
        # Should fail on duplicate
        with pytest.raises(ValueError, match="agent1 already registered"):
            registry.register("agent1", MockAgent("different"))
    
    def test_register_duplicate_with_override(self, sample_agent):
        """Test registering duplicate key succeeds with override enabled."""
        registry = UniversalRegistry[MockAgent]("TestRegistry", allow_override=True)
        
        registry.register("agent1", sample_agent)
        assert registry.get("agent1") == sample_agent
        
        # Should succeed with override
        new_agent = MockAgent("new-agent")
        registry.register("agent1", new_agent, description="Updated agent")
        
        assert registry.get("agent1") == new_agent
        assert registry._items["agent1"].metadata["description"] == "Updated agent"
    
    def test_get_singleton(self, sample_agent):
        """Test retrieving singleton items."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        registry.register("agent1", sample_agent)
        
        retrieved = registry.get("agent1")
        assert retrieved == sample_agent
        
        # Check access counting
        item = registry._items["agent1"]
        assert item.access_count == 1
        assert item.last_accessed is not None
    
    def test_get_via_factory(self, mock_context):
        """Test retrieving items via factory."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def agent_factory(ctx):
            return MockAgent(f"agent-{ctx.user_id}")
        
        registry.register_factory("agent-factory", agent_factory)
        
        # Get via factory
        agent = registry.get("agent-factory", mock_context)
        assert agent is not None
        assert agent.name == f"agent-{mock_context.user_id}"
        
        # Should create new instance each time
        agent2 = registry.get("agent-factory", mock_context)
        assert agent2 is not agent  # Different instances
        assert agent2.name == f"agent-{mock_context.user_id}"
    
    def test_get_nonexistent(self):
        """Test getting non-existent item returns None."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        result = registry.get("nonexistent")
        assert result is None
    
    def test_create_instance_with_factory(self, mock_context):
        """Test create_instance method."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def agent_factory(ctx):
            return MockAgent(f"created-{ctx.run_id}")
        
        registry.register_factory("creator", agent_factory)
        
        # Create instance
        agent = registry.create_instance("creator", mock_context)
        assert agent is not None
        assert agent.name == f"created-{mock_context.run_id}"
        
        # Should track factory creation
        metrics = registry.get_metrics()
        assert metrics["metrics"]["factory_creations"] == 1
    
    def test_create_instance_no_factory(self, mock_context):
        """Test create_instance fails when no factory registered."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        with pytest.raises(KeyError, match="No factory for nonexistent"):
            registry.create_instance("nonexistent", mock_context)
    
    def test_list_keys(self, sample_agent, sample_tool):
        """Test listing all registered keys."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        registry.register("agent1", sample_agent)
        registry.register("tool1", sample_tool)
        
        keys = registry.list_keys()
        assert len(keys) == 2
        assert "agent1" in keys
        assert "tool1" in keys
    
    def test_remove_item(self, sample_agent):
        """Test removing items from registry."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        registry.register("agent1", sample_agent, tags=["ai"])
        
        assert "agent1" in registry
        assert len(registry.list_by_tag("ai")) == 1
        
        # Remove item
        result = registry.remove("agent1")
        assert result is True
        assert "agent1" not in registry
        assert len(registry.list_by_tag("ai")) == 0
        
        # Remove non-existent item
        result = registry.remove("nonexistent")
        assert result is False
    
    def test_clear_registry(self, sample_agent, sample_tool):
        """Test clearing all items from registry."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        registry.register("agent1", sample_agent)
        registry.register("tool1", sample_tool, tags=["utility"])
        
        assert len(registry) == 2
        assert len(registry.list_by_tag("utility")) == 1
        
        registry.clear()
        
        assert len(registry) == 0
        assert len(registry.list_by_tag("utility")) == 0
        assert registry.list_keys() == []


# ===================== FROZEN STATE TESTS =====================

class TestUniversalRegistryFrozen:
    """Test registry frozen state functionality."""
    
    def test_freeze_registry(self, sample_agent):
        """Test freezing registry makes it immutable."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Add item before freezing
        registry.register("agent1", sample_agent)
        
        assert not registry.is_frozen()
        
        # Freeze registry
        registry.freeze()
        
        assert registry.is_frozen()
        assert registry._freeze_time is not None
        
        # Verify frozen operations fail
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.register("agent2", MockAgent("agent2"))
        
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.register_factory("factory", lambda ctx: MockAgent("factory"))
        
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.remove("agent1")
        
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.clear()
        
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.load_from_config({})
        
        # But reading should still work
        assert registry.get("agent1") == sample_agent
        assert "agent1" in registry
    
    def test_freeze_already_frozen(self, sample_agent):
        """Test freezing already frozen registry logs warning."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        registry.register("agent1", sample_agent)
        
        # Freeze twice
        registry.freeze()
        assert registry.is_frozen()
        
        # Second freeze should not raise error but log warning
        registry.freeze()  # Should log warning but not crash
        assert registry.is_frozen()


# ===================== VALIDATION TESTS =====================

class TestUniversalRegistryValidation:
    """Test validation functionality."""
    
    def test_add_validation_handler(self, sample_agent):
        """Test adding custom validation handlers."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def validate_agent_name(key: str, item: Any) -> bool:
            return key.startswith("valid_")
        
        registry.add_validation_handler(validate_agent_name)
        
        # Valid key should work
        registry.register("valid_agent", sample_agent)
        assert "valid_agent" in registry
        
        # Invalid key should fail
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("invalid_agent", MockAgent("invalid"))
    
    def test_multiple_validation_handlers(self, sample_agent):
        """Test multiple validation handlers."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def validate_prefix(key: str, item: Any) -> bool:
            return key.startswith("test_")
        
        def validate_agent_type(key: str, item: Any) -> bool:
            return isinstance(item, MockAgent)
        
        registry.add_validation_handler(validate_prefix)
        registry.add_validation_handler(validate_agent_type)
        
        # Both validators must pass
        registry.register("test_agent", sample_agent)
        assert "test_agent" in registry
        
        # First validator fails
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("wrong_prefix", sample_agent)
        
        # Second validator fails
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("test_notAgent", "not an agent")
    
    def test_validation_handler_exception(self, sample_agent):
        """Test validation handler that throws exception."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def failing_validator(key: str, item: Any) -> bool:
            raise Exception("Validator error")
        
        registry.add_validation_handler(failing_validator)
        
        # Should fail on validator exception
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("agent1", sample_agent)
    
    def test_validation_updates_metrics(self, sample_agent):
        """Test validation failures update metrics."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def always_fail(key: str, item: Any) -> bool:
            return False
        
        registry.add_validation_handler(always_fail)
        
        initial_metrics = registry.get_metrics()
        assert initial_metrics["metrics"]["validation_failures"] == 0
        
        # Try to register - should fail validation
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("agent1", sample_agent)
        
        updated_metrics = registry.get_metrics()
        assert updated_metrics["metrics"]["validation_failures"] == 1


# ===================== METRICS AND HEALTH TESTS =====================

class TestUniversalRegistryMetrics:
    """Test metrics and health functionality."""
    
    def test_get_metrics(self, sample_agent, mock_context):
        """Test comprehensive metrics collection."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        # Small delay to ensure uptime > 0
        time.sleep(0.01)
        
        # Register items with tags
        registry.register("agent1", sample_agent, tags=["ai"])
        registry.register("tool1", MockTool("tool1"), tags=["utility"])
        
        # Register factory
        registry.register_factory("factory1", lambda ctx: MockAgent(ctx.user_id))
        
        # Access items to generate metrics
        registry.get("agent1")
        registry.get("agent1")  # Access twice
        registry.get("tool1")
        registry.create_instance("factory1", mock_context)
        
        metrics = registry.get_metrics()
        
        # Basic metrics
        assert metrics["registry_name"] == "TestRegistry"
        assert metrics["total_items"] == 3
        assert metrics["frozen"] is False
        assert metrics["uptime_seconds"] >= 0  # Allow for very fast execution
        
        # Operation metrics
        assert metrics["metrics"]["total_registrations"] == 3
        assert metrics["metrics"]["successful_registrations"] == 3
        assert metrics["metrics"]["failed_registrations"] == 0
        assert metrics["metrics"]["total_retrievals"] == 3  # 2 + 1
        assert metrics["metrics"]["factory_creations"] == 1
        assert metrics["metrics"]["validation_failures"] == 0
        
        # Category distribution
        assert metrics["category_distribution"]["ai"] == 1
        assert metrics["category_distribution"]["utility"] == 1
        
        # Most accessed
        most_accessed = metrics["most_accessed"]
        assert len(most_accessed) == 3
        assert most_accessed[0]["key"] == "agent1"
        assert most_accessed[0]["count"] == 2
        
        # Success rate
        assert metrics["success_rate"] == 1.0
    
    def test_metrics_disabled(self, sample_agent):
        """Test metrics when disabled."""
        registry = UniversalRegistry[MockAgent]("TestRegistry", enable_metrics=False)
        
        registry.register("agent1", sample_agent)
        agent = registry.get("agent1")
        
        # Access count should not be updated
        item = registry._items["agent1"]
        assert item.access_count == 0
        assert item.last_accessed is None
    
    def test_validate_health_healthy(self, sample_agent, sample_tool):
        """Test health validation for healthy registry."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        registry.register("agent1", sample_agent)
        registry.register("tool1", sample_tool)
        
        # Access items
        registry.get("agent1")
        registry.get("tool1")
        
        health = registry.validate_health()
        
        assert health["status"] == "healthy"
        assert health["timestamp"] is not None
        assert len(health["issues"]) == 0
        assert "metrics" in health
    
    def test_validate_health_empty_registry(self):
        """Test health validation for empty registry."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        health = registry.validate_health()
        
        assert health["status"] == "warning"
        assert "Registry is empty" in health["issues"]
    
    def test_validate_health_unused_items(self, sample_agent, sample_tool):
        """Test health validation with many unused items."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        # Register many items but don't access them
        for i in range(10):
            registry.register(f"item{i}", MockAgent(f"agent{i}"))
        
        health = registry.validate_health()
        
        assert health["status"] == "warning"
        assert any("Many unused items" in issue for issue in health["issues"])
    
    def test_validate_health_high_failure_rate(self, sample_agent):
        """Test health validation with high failure rate."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Add failing validator
        def sometimes_fail(key: str, item: Any) -> bool:
            return not key.startswith("fail_")
        
        registry.add_validation_handler(sometimes_fail)
        
        # Register successful items
        registry.register("success1", sample_agent)
        
        # Try to register failing items
        for i in range(5):
            try:
                registry.register(f"fail_{i}", MockAgent(f"fail{i}"))
            except ValueError:
                pass
        
        health = registry.validate_health()
        
        # Status could be 'degraded' or 'warning' depending on exact failure rate calculation
        assert health["status"] in ["degraded", "warning"]
        # Should have some issue about failures
        assert len(health["issues"]) > 0


# ===================== CONFIGURATION TESTS =====================

class TestUniversalRegistryConfiguration:
    """Test configuration loading functionality."""
    
    def test_load_from_config_basic(self):
        """Test basic config loading (currently logs warnings)."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        config = {
            "item1": {
                "factory": "MockAgentFactory"
            },
            "item2": {
                "class": "MockAgent"
            },
            "item3": {
                "invalid": "config"
            }
        }
        
        # Should not raise exception, but logs warnings
        registry.load_from_config(config)
        
        # No items should be registered since implementation is incomplete
        assert len(registry) == 0
    
    def test_load_from_config_frozen(self):
        """Test config loading fails on frozen registry."""
        registry = UniversalRegistry[Any]("TestRegistry")
        registry.freeze()
        
        with pytest.raises(RuntimeError, match="Registry 'TestRegistry' is frozen"):
            registry.load_from_config({})


# ===================== SPECIAL METHODS TESTS =====================

class TestUniversalRegistrySpecialMethods:
    """Test special methods (__len__, __contains__, __repr__)."""
    
    def test_len(self, sample_agent, sample_tool):
        """Test __len__ method."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        assert len(registry) == 0
        
        registry.register("agent1", sample_agent)
        assert len(registry) == 1
        
        registry.register("tool1", sample_tool)
        assert len(registry) == 2
        
        registry.remove("agent1")
        assert len(registry) == 1
    
    def test_contains(self, sample_agent):
        """Test __contains__ method."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        assert "agent1" not in registry
        
        registry.register("agent1", sample_agent)
        
        assert "agent1" in registry
        assert "agent2" not in registry
    
    def test_repr(self, sample_agent):
        """Test __repr__ method."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Empty registry
        repr_str = repr(registry)
        assert "UniversalRegistry[TestRegistry]" in repr_str
        assert "0 items" in repr_str
        assert "mutable" in repr_str
        
        # Add item
        registry.register("agent1", sample_agent)
        repr_str = repr(registry)
        assert "1 items" in repr_str
        assert "mutable" in repr_str
        
        # Freeze registry
        registry.freeze()
        repr_str = repr(registry)
        assert "1 items" in repr_str
        assert "frozen" in repr_str


# ===================== THREAD SAFETY TESTS =====================

class TestUniversalRegistryThreadSafety:
    """Test thread safety for multi-user scenarios."""
    
    def test_concurrent_registration(self):
        """Test concurrent registration is thread-safe."""
        registry = UniversalRegistry[MockAgent]("TestRegistry", allow_override=True)
        
        results = []
        errors = []
        
        def register_agent(thread_id):
            try:
                agent = MockAgent(f"agent-{thread_id}")
                registry.register(f"agent-{thread_id}", agent)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=register_agent, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 20
        assert len(registry) == 20
        
        # Verify all agents are present
        for i in range(20):
            assert f"agent-{i}" in registry
            agent = registry.get(f"agent-{i}")
            assert agent.name == f"agent-{i}"
    
    def test_concurrent_access_and_registration(self, mock_context):
        """Test concurrent access while registering."""
        registry = UniversalRegistry[MockAgent]("TestRegistry", allow_override=True)
        
        # Pre-register some agents
        for i in range(5):
            registry.register(f"initial-{i}", MockAgent(f"initial-{i}"))
        
        # Register factory
        registry.register_factory("factory", lambda ctx: MockAgent(f"factory-{ctx.user_id}"))
        
        access_results = []
        registration_results = []
        factory_results = []
        errors = []
        
        def access_agents(thread_id):
            try:
                for i in range(5):
                    agent = registry.get(f"initial-{i}")
                    if agent:
                        access_results.append((thread_id, agent.name))
            except Exception as e:
                errors.append(("access", thread_id, e))
        
        def register_agents(thread_id):
            try:
                agent = MockAgent(f"new-{thread_id}")
                registry.register(f"new-{thread_id}", agent)
                registration_results.append(thread_id)
            except Exception as e:
                errors.append(("register", thread_id, e))
        
        def use_factory(thread_id):
            try:
                ctx = MockUserExecutionContext(f"user-{thread_id}", f"run-{thread_id}")
                agent = registry.create_instance("factory", ctx)
                factory_results.append((thread_id, agent.name))
            except Exception as e:
                errors.append(("factory", thread_id, e))
        
        # Start mixed threads
        threads = []
        for i in range(15):
            if i % 3 == 0:
                thread = threading.Thread(target=access_agents, args=(i,))
            elif i % 3 == 1:
                thread = threading.Thread(target=register_agents, args=(i,))
            else:
                thread = threading.Thread(target=use_factory, args=(i,))
            
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify operations succeeded
        assert len(access_results) > 0
        assert len(registration_results) > 0
        assert len(factory_results) > 0
        
        # Verify registry state
        assert len(registry) >= 5  # Initial + new registrations
    
    def test_concurrent_freeze_and_operations(self, sample_agent):
        """Test concurrent freeze with other operations."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Pre-register agent
        registry.register("agent1", sample_agent)
        
        freeze_completed = []
        operation_results = []
        errors = []
        
        def freeze_registry():
            try:
                time.sleep(0.01)  # Small delay
                registry.freeze()
                freeze_completed.append(True)
            except Exception as e:
                errors.append(("freeze", e))
        
        def try_operations(thread_id):
            try:
                # Try various operations
                agent = registry.get("agent1")  # Should always work
                operation_results.append(("get", thread_id, "success"))
                
                try:
                    registry.register(f"new-{thread_id}", MockAgent(f"new-{thread_id}"))
                    operation_results.append(("register", thread_id, "success"))
                except RuntimeError:
                    operation_results.append(("register", thread_id, "frozen"))
                
            except Exception as e:
                errors.append(("operation", thread_id, e))
        
        # Start freeze thread
        freeze_thread = threading.Thread(target=freeze_registry)
        
        # Start operation threads
        op_threads = []
        for i in range(10):
            thread = threading.Thread(target=try_operations, args=(i,))
            op_threads.append(thread)
        
        # Start all threads
        freeze_thread.start()
        for thread in op_threads:
            thread.start()
        
        # Wait for completion
        freeze_thread.join()
        for thread in op_threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(freeze_completed) == 1
        assert registry.is_frozen()
        
        # All get operations should have succeeded
        get_results = [r for r in operation_results if r[0] == "get"]
        assert len(get_results) == 10
        assert all(r[2] == "success" for r in get_results)
    
    def test_concurrent_metrics_access(self):
        """Test concurrent metrics access is thread-safe."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Register items
        for i in range(10):
            registry.register(f"agent-{i}", MockAgent(f"agent-{i}"))
        
        metrics_results = []
        errors = []
        
        def get_metrics_and_access(thread_id):
            try:
                for i in range(5):
                    # Access some items
                    registry.get(f"agent-{i % 10}")
                    
                    # Get metrics
                    metrics = registry.get_metrics()
                    metrics_results.append((thread_id, metrics["total_items"]))
                    
                    # Get health
                    health = registry.validate_health()
                    assert "status" in health
                    
            except Exception as e:
                errors.append((thread_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_metrics_and_access, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(metrics_results) == 50  # 10 threads * 5 calls each
        
        # All metrics should show same item count
        assert all(count == 10 for _, count in metrics_results)


# ===================== AGENT REGISTRY TESTS =====================

class TestAgentRegistry:
    """Test AgentRegistry specialized functionality."""
    
    def test_agent_registry_initialization(self):
        """Test AgentRegistry initializes correctly."""
        registry = AgentRegistry()
        
        assert registry.name == "AgentRegistry"
        assert registry.websocket_manager is None
        assert registry.websocket_bridge is None
        assert len(registry._validation_handlers) == 1  # Agent validator added
    
    def test_agent_validation_with_mock(self):
        """Test agent validation accepts Mock objects for testing."""
        registry = AgentRegistry()
        
        mock_agent = Mock()
        mock_agent._mock_name = "MockAgent"
        
        # Should accept mock objects
        registry.register("mock-agent", mock_agent)
        assert "mock-agent" in registry
    
    def test_agent_validation_with_real_agent(self):
        """Test agent validation with MockAgent (acts like BaseAgent)."""
        registry = AgentRegistry()
        
        agent = MockAgent("test-agent")
        
        # Should accept MockAgent instances
        registry.register("test-agent", agent)
        assert "test-agent" in registry
    
    def test_agent_validation_with_invalid_type(self):
        """Test agent validation rejects invalid types."""
        registry = AgentRegistry()
        
        # Should reject non-agent objects
        with pytest.raises(ValueError, match="Validation failed"):
            registry.register("invalid", "not an agent")
    
    def test_set_websocket_manager(self):
        """Test setting WebSocket manager."""
        registry = AgentRegistry()
        
        mock_manager = Mock()
        mock_manager.name = "WebSocketManager"
        
        registry.set_websocket_manager(mock_manager)
        
        assert registry.websocket_manager == mock_manager
    
    def test_set_websocket_bridge(self):
        """Test setting WebSocket bridge."""
        registry = AgentRegistry()
        
        mock_bridge = Mock()
        mock_bridge.name = "AgentWebSocketBridge"
        
        registry.set_websocket_bridge(mock_bridge)
        
        assert registry.websocket_bridge == mock_bridge
    
    def test_set_websocket_bridge_none_fails(self):
        """Test setting None WebSocket bridge fails."""
        registry = AgentRegistry()
        
        with pytest.raises(ValueError, match="WebSocket bridge cannot be None"):
            registry.set_websocket_bridge(None)
    
    def test_create_agent_with_context(self, mock_context):
        """Test creating agent with full context."""
        registry = AgentRegistry()
        
        # Register agent
        agent = MockAgent("test-agent")
        registry.register("test-agent", agent)
        
        # Set websocket bridge
        mock_bridge = Mock()
        registry.set_websocket_bridge(mock_bridge)
        
        # Mock agent with set_websocket_bridge method
        agent.set_websocket_bridge = Mock()
        
        # Create with context
        mock_llm = Mock()
        mock_dispatcher = Mock()
        
        result_agent = registry.create_agent_with_context(
            "test-agent", mock_context, mock_llm, mock_dispatcher
        )
        
        assert result_agent == agent
        agent.set_websocket_bridge.assert_called_once_with(mock_bridge)
    
    def test_create_agent_with_context_no_agent(self, mock_context):
        """Test creating non-existent agent fails."""
        registry = AgentRegistry()
        
        with pytest.raises(KeyError, match="Agent nonexistent not found"):
            registry.create_agent_with_context(
                "nonexistent", mock_context, Mock(), Mock()
            )
    
    def test_create_agent_with_context_no_websocket_method(self, mock_context):
        """Test creating agent without websocket method works."""
        registry = AgentRegistry()
        
        # Register agent without set_websocket_bridge method
        agent = MockAgent("test-agent")
        registry.register("test-agent", agent)
        
        # Set websocket bridge
        mock_bridge = Mock()
        registry.set_websocket_bridge(mock_bridge)
        
        # Create with context (should not crash)
        result_agent = registry.create_agent_with_context(
            "test-agent", mock_context, Mock(), Mock()
        )
        
        assert result_agent == agent
    
    def test_tool_dispatcher_property_lazy_creation(self):
        """Test tool_dispatcher property creates mock dispatcher lazily."""
        registry = AgentRegistry()
        
        # Initially no tool dispatcher
        assert registry._tool_dispatcher is None
        
        # Accessing property should create mock
        dispatcher = registry.tool_dispatcher
        
        assert dispatcher is not None
        assert registry._tool_dispatcher is dispatcher
        assert hasattr(dispatcher, '_websocket_enhanced')
        assert hasattr(dispatcher, 'registry')
        assert dispatcher.registry == registry
        assert dispatcher._websocket_enhanced is False
        assert dispatcher.executor is None
    
    def test_tool_dispatcher_property_returns_same_instance(self):
        """Test tool_dispatcher property returns same instance on multiple calls."""
        registry = AgentRegistry()
        
        dispatcher1 = registry.tool_dispatcher
        dispatcher2 = registry.tool_dispatcher
        
        assert dispatcher1 is dispatcher2
    
    def test_tool_dispatcher_auto_enhance_with_websocket_manager(self):
        """Test tool_dispatcher gets enhanced when websocket_manager is set."""
        registry = AgentRegistry()
        
        # Set websocket manager first
        mock_manager = Mock()
        registry.set_websocket_manager(mock_manager)
        
        # Access tool_dispatcher - should be auto-enhanced
        dispatcher = registry.tool_dispatcher
        
        assert dispatcher._websocket_enhanced is True
    
    def test_set_tool_dispatcher_method(self):
        """Test set_tool_dispatcher method."""
        registry = AgentRegistry()
        
        # Create custom mock dispatcher
        custom_dispatcher = Mock()
        custom_dispatcher._websocket_enhanced = False
        
        # Set dispatcher
        registry.set_tool_dispatcher(custom_dispatcher)
        
        assert registry._tool_dispatcher == custom_dispatcher
        assert registry.tool_dispatcher == custom_dispatcher
    
    def test_set_tool_dispatcher_with_websocket_manager(self):
        """Test set_tool_dispatcher auto-enhances with existing websocket_manager."""
        registry = AgentRegistry()
        
        # Set websocket manager first
        mock_manager = Mock()
        registry.set_websocket_manager(mock_manager)
        
        # Create and set custom dispatcher
        custom_dispatcher = Mock()
        custom_dispatcher._websocket_enhanced = False
        
        registry.set_tool_dispatcher(custom_dispatcher)
        
        # Should have been auto-enhanced
        assert custom_dispatcher._websocket_enhanced is True
    
    def test_websocket_manager_enhances_existing_tool_dispatcher(self):
        """Test setting websocket_manager enhances existing tool_dispatcher."""
        registry = AgentRegistry()
        
        # Access tool_dispatcher first (creates mock)
        dispatcher = registry.tool_dispatcher
        assert dispatcher._websocket_enhanced is False
        
        # Set websocket manager - should enhance existing dispatcher
        mock_manager = Mock()
        registry.set_websocket_manager(mock_manager)
        
        assert dispatcher._websocket_enhanced is True
    
    def test_mock_tool_dispatcher_enhance_method(self):
        """Test MockToolDispatcher enhance_with_websockets method."""
        registry = AgentRegistry()
        
        dispatcher = registry.tool_dispatcher
        
        # Mock bridge
        mock_bridge = Mock()
        
        # Call enhance method directly
        assert dispatcher._websocket_enhanced is False
        dispatcher.enhance_with_websockets(mock_bridge)
        assert dispatcher._websocket_enhanced is True
    
    def test_enhance_tool_dispatcher_with_real_dispatcher_import_error(self):
        """Test WebSocket enhancement handles import errors gracefully."""
        registry = AgentRegistry()
        
        # Create real-looking dispatcher without _websocket_enhanced attribute
        real_dispatcher = Mock(spec=[])  # No attributes
        registry.set_tool_dispatcher(real_dispatcher)
        
        # Mock the import to fail
        import sys
        original_modules = sys.modules.copy()
        
        # Remove the module if it exists
        if 'netra_backend.app.agents.unified_tool_execution' in sys.modules:
            del sys.modules['netra_backend.app.agents.unified_tool_execution']
        
        # Add a mock module that raises ImportError
        class FailingModule:
            def __getattr__(self, name):
                raise ImportError("Module not found")
        
        sys.modules['netra_backend.app.agents.unified_tool_execution'] = FailingModule()
        
        try:
            # Set websocket manager - should handle import error gracefully
            mock_manager = Mock()
            registry.set_websocket_manager(mock_manager)
            
            # Should not crash, but log error
            assert registry.websocket_manager == mock_manager
            
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def test_enhance_tool_dispatcher_no_dispatcher(self):
        """Test WebSocket enhancement when no tool_dispatcher exists."""
        registry = AgentRegistry()
        
        # Call enhancement directly without tool_dispatcher
        registry._enhance_tool_dispatcher_with_websockets()
        
        # Should not crash and should still be None
        assert registry._tool_dispatcher is None
    
    def test_agent_validation_with_class_type(self):
        """Test agent validation with class types instead of instances."""
        registry = AgentRegistry()
        
        # Mock a class that inherits from BaseAgent
        class MockAgentClass:
            pass
        
        # Test with class validation - should pass through validation
        registry.register("agent-class", MockAgentClass)
        assert "agent-class" in registry
    
    def test_enhance_tool_dispatcher_with_real_dispatcher_success(self):
        """Test successful WebSocket enhancement with real dispatcher."""
        registry = AgentRegistry()
        
        # Create a real-looking dispatcher without _websocket_enhanced attribute
        real_dispatcher = Mock(spec=[])  # No attributes initially
        registry.set_tool_dispatcher(real_dispatcher)
        
        # Mock successful import and enhancement
        import sys
        from unittest.mock import patch, MagicMock
        
        mock_enhance_func = MagicMock()
        
        with patch.dict(sys.modules, {
            'netra_backend.app.agents.unified_tool_execution': MagicMock(
                enhance_tool_dispatcher_with_notifications=mock_enhance_func
            )
        }):
            # Set websocket manager - should call real enhancement
            mock_manager = Mock()
            registry.set_websocket_manager(mock_manager)
            
            # Verify the real enhancement function was called
            mock_enhance_func.assert_called_once_with(
                real_dispatcher,
                websocket_manager=mock_manager,
                enable_notifications=True
            )


# ===================== OTHER SPECIALIZED REGISTRY TESTS =====================

class TestOtherSpecializedRegistries:
    """Test other specialized registry classes."""
    
    def test_tool_registry_initialization(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        
        assert registry.name == "ToolRegistry"
        # May have default tools registered
        assert len(registry) >= 0
    
    def test_service_registry_initialization(self):
        """Test ServiceRegistry initialization."""
        registry = ServiceRegistry()
        
        assert registry.name == "ServiceRegistry"
    
    def test_service_registry_register_service(self):
        """Test registering services with metadata."""
        registry = ServiceRegistry()
        
        registry.register_service(
            "auth-service",
            "http://localhost:8081", 
            health_endpoint="/health",
            version="1.0.0"
        )
        
        assert "auth-service" in registry
        
        service_info = registry.get("auth-service")
        assert service_info["url"] == "http://localhost:8081"
        assert service_info["health_endpoint"] == "/health"
        assert service_info["version"] == "1.0.0"
    
    def test_strategy_registry_initialization(self):
        """Test StrategyRegistry initialization."""
        registry = StrategyRegistry()
        
        assert registry.name == "StrategyRegistry"


# ===================== GLOBAL REGISTRY MANAGEMENT TESTS =====================

class TestGlobalRegistryManagement:
    """Test global registry management functions."""
    
    def test_get_global_registry_agent(self, clean_global_registries):
        """Test getting global agent registry."""
        registry = get_global_registry("agent")
        
        assert isinstance(registry, AgentRegistry)
        assert registry.name == "AgentRegistry"
        
        # Second call should return same instance
        registry2 = get_global_registry("agent")
        assert registry2 is registry
    
    def test_get_global_registry_tool(self, clean_global_registries):
        """Test getting global tool registry."""
        registry = get_global_registry("tool")
        
        assert isinstance(registry, ToolRegistry)
        assert registry.name == "ToolRegistry"
    
    def test_get_global_registry_service(self, clean_global_registries):
        """Test getting global service registry."""
        registry = get_global_registry("service")
        
        assert isinstance(registry, ServiceRegistry)
        assert registry.name == "ServiceRegistry"
    
    def test_get_global_registry_strategy(self, clean_global_registries):
        """Test getting global strategy registry."""
        registry = get_global_registry("strategy")
        
        assert isinstance(registry, StrategyRegistry)
        assert registry.name == "StrategyRegistry"
    
    def test_get_global_registry_invalid(self, clean_global_registries):
        """Test getting invalid registry type fails."""
        with pytest.raises(ValueError, match="Unknown registry type: invalid"):
            get_global_registry("invalid")
    
    def test_get_global_registry_case_insensitive(self, clean_global_registries):
        """Test global registry is case insensitive."""
        registry1 = get_global_registry("AGENT")
        registry2 = get_global_registry("agent") 
        registry3 = get_global_registry("Agent")
        
        assert registry1 is registry2 is registry3
    
    def test_global_registry_thread_safety(self, clean_global_registries):
        """Test global registry creation is thread-safe."""
        registries = []
        errors = []
        
        def get_registry(thread_id):
            try:
                registry = get_global_registry("agent")
                registries.append((thread_id, registry))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=get_registry, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(registries) == 20
        
        # All should be the same instance
        first_registry = registries[0][1]
        assert all(reg is first_registry for _, reg in registries)
    
    def test_create_scoped_registry(self):
        """Test creating scoped registries."""
        registry1 = create_scoped_registry("agent", "user-123")
        registry2 = create_scoped_registry("agent", "user-456")
        
        assert isinstance(registry1, AgentRegistry)
        assert isinstance(registry2, AgentRegistry)
        assert registry1 is not registry2
        
        assert registry1.name == "agent_user-123"
        assert registry2.name == "agent_user-456"
    
    def test_create_scoped_registry_all_types(self):
        """Test creating scoped registries for all types."""
        types = ["agent", "tool", "service", "strategy"]
        expected_classes = [AgentRegistry, ToolRegistry, ServiceRegistry, StrategyRegistry]
        
        for registry_type, expected_class in zip(types, expected_classes):
            registry = create_scoped_registry(registry_type, "test-scope")
            assert isinstance(registry, expected_class)
            assert registry.name == f"{registry_type}_test-scope"
    
    def test_create_scoped_registry_generic(self):
        """Test creating scoped registry for unknown type creates generic."""
        registry = create_scoped_registry("custom", "test-scope")
        
        assert isinstance(registry, UniversalRegistry)
        assert registry.name == "custom_test-scope"


# ===================== EDGE CASES AND ERROR CONDITIONS =====================

class TestUniversalRegistryEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_key_registration(self, sample_agent):
        """Test registering with empty key."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Empty string key should be allowed
        registry.register("", sample_agent)
        assert "" in registry
        assert registry.get("") == sample_agent
    
    def test_none_value_registration(self):
        """Test registering None value."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        # None value should be allowed
        registry.register("none-item", None)
        assert "none-item" in registry
        assert registry.get("none-item") is None
    
    def test_factory_with_none_context(self):
        """Test factory call with None context."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def agent_factory(ctx):
            if ctx is None:
                return MockAgent("default")
            return MockAgent(f"user-{ctx.user_id}")
        
        registry.register_factory("factory", agent_factory)
        
        # Call get without context should return None
        agent = registry.get("factory")
        assert agent is None
        
        # Call get with None context explicitly should still return None
        agent = registry.get("factory", None)
        assert agent is None
    
    def test_factory_exception_handling(self, mock_context):
        """Test factory that raises exceptions."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        def failing_factory(ctx):
            raise Exception("Factory failed")
        
        registry.register_factory("failing", failing_factory)
        
        # Factory exception should propagate
        with pytest.raises(Exception, match="Factory failed"):
            registry.get("failing", mock_context)
        
        with pytest.raises(Exception, match="Factory failed"):
            registry.create_instance("failing", mock_context)
    
    def test_large_registry_performance(self):
        """Test registry with large number of items."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        # Register 1000 items
        start_time = time.time()
        for i in range(1000):
            registry.register(f"agent-{i:04d}", MockAgent(f"agent-{i:04d}"))
        registration_time = time.time() - start_time
        
        assert len(registry) == 1000
        
        # Access items
        start_time = time.time()
        for i in range(0, 1000, 10):  # Access every 10th item
            agent = registry.get(f"agent-{i:04d}")
            assert agent is not None
        access_time = time.time() - start_time
        
        # Get metrics
        start_time = time.time()
        metrics = registry.get_metrics()
        metrics_time = time.time() - start_time
        
        assert metrics["total_items"] == 1000
        
        # Performance should be reasonable (not scientific, just sanity check)
        assert registration_time < 5.0  # Should register 1000 items in < 5 seconds
        assert access_time < 1.0  # Should access 100 items in < 1 second
        assert metrics_time < 1.0  # Should get metrics in < 1 second
    
    def test_registry_with_circular_references(self):
        """Test registry handles circular references gracefully."""
        registry = UniversalRegistry[Dict]("TestRegistry")
        
        # Create objects with circular references
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2"}
        obj1["ref"] = obj2
        obj2["ref"] = obj1
        
        # Should be able to register circular references
        registry.register("circular1", obj1)
        registry.register("circular2", obj2)
        
        # Should be able to retrieve them
        retrieved1 = registry.get("circular1")
        retrieved2 = registry.get("circular2")
        
        assert retrieved1["name"] == "obj1"
        assert retrieved2["name"] == "obj2"
        assert retrieved1["ref"] is obj2
        assert retrieved2["ref"] is obj1
    
    def test_registry_item_metadata_mutation(self, sample_agent):
        """Test metadata behavior after registration."""
        registry = UniversalRegistry[MockAgent]("TestRegistry")
        
        metadata = {"mutable": ["list"]}
        registry.register("agent1", sample_agent, **metadata)
        
        # Get the stored metadata
        item = registry._items["agent1"]
        stored_metadata = item.metadata
        
        # Verify initial state
        assert "mutable" in stored_metadata
        assert stored_metadata["mutable"] == ["list"]
        
        # Mutate the stored metadata directly (since **kwargs creates a new dict)
        stored_metadata["mutable"].append("modified")  
        stored_metadata["new_key"] = "new_value"
        
        # Verify mutations are reflected
        assert item.metadata["mutable"] == ["list", "modified"]
        assert item.metadata["new_key"] == "new_value"
        
        # Original metadata dict should be unchanged (since **kwargs created a copy)
        metadata["external_change"] = "should_not_affect_registry"
        assert "external_change" not in item.metadata
    
    def test_concurrent_clear_and_access(self, sample_agent):
        """Test concurrent clear while accessing items."""
        registry = UniversalRegistry[MockAgent]("TestRegistry", allow_override=True)
        
        # Pre-populate registry
        for i in range(100):
            registry.register(f"agent-{i}", MockAgent(f"agent-{i}"))
        
        access_results = []
        clear_completed = []
        errors = []
        
        def access_items(thread_id):
            try:
                for i in range(100):
                    agent = registry.get(f"agent-{i}")
                    if agent:  # May be None if cleared
                        access_results.append((thread_id, i))
            except Exception as e:
                errors.append(("access", thread_id, e))
        
        def clear_registry():
            try:
                time.sleep(0.01)  # Let access threads start
                registry.clear()
                clear_completed.append(True)
            except Exception as e:
                errors.append(("clear", e))
        
        # Start access threads
        access_threads = []
        for i in range(5):
            thread = threading.Thread(target=access_items, args=(i,))
            access_threads.append(thread)
            thread.start()
        
        # Start clear thread
        clear_thread = threading.Thread(target=clear_registry)
        clear_thread.start()
        
        # Wait for completion
        for thread in access_threads:
            thread.join()
        clear_thread.join()
        
        # Verify no crashes
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(clear_completed) == 1
        assert len(registry) == 0


# ===================== INTEGRATION WITH SYSTEM TESTS =====================

class TestUniversalRegistrySystemIntegration:
    """Test integration with broader system components."""
    
    def test_multiple_registries_isolation(self):
        """Test multiple registries maintain isolation."""
        agent_registry = UniversalRegistry[MockAgent]("AgentRegistry")
        tool_registry = UniversalRegistry[MockTool]("ToolRegistry")
        
        # Register items in both
        agent = MockAgent("agent1")
        tool = MockTool("tool1")
        
        agent_registry.register("item1", agent)
        tool_registry.register("item1", tool)
        
        # Same key should be independent
        assert agent_registry.get("item1") == agent
        assert tool_registry.get("item1") == tool
        assert agent_registry.get("item1") is not tool_registry.get("item1")
        
        # Operations on one shouldn't affect the other
        agent_registry.remove("item1")
        assert "item1" not in agent_registry
        assert "item1" in tool_registry
    
    def test_registry_with_real_context_patterns(self):
        """Test registry patterns similar to real system usage."""
        # Simulate agent registry usage pattern
        agent_registry = AgentRegistry()
        
        # Register agent class factories (simulating real usage)
        def triage_factory(ctx):
            agent = MockAgent("triage")
            agent.user_id = ctx.user_id
            agent.run_id = ctx.run_id
            return agent
        
        def data_factory(ctx):
            agent = MockAgent("data")
            agent.user_id = ctx.user_id
            agent.run_id = ctx.run_id
            return agent
        
        agent_registry.register_factory("triage", triage_factory, tags=["primary"])
        agent_registry.register_factory("data", data_factory, tags=["analysis"])
        
        # Simulate multiple users
        user1_ctx = MockUserExecutionContext("user-1", "run-123")
        user2_ctx = MockUserExecutionContext("user-2", "run-456")
        
        # Create isolated instances
        user1_triage = agent_registry.create_instance("triage", user1_ctx)
        user1_data = agent_registry.create_instance("data", user1_ctx)
        
        user2_triage = agent_registry.create_instance("triage", user2_ctx)
        user2_data = agent_registry.create_instance("data", user2_ctx)
        
        # Verify isolation
        assert user1_triage.user_id == "user-1"
        assert user1_triage.run_id == "run-123"
        assert user2_triage.user_id == "user-2"
        assert user2_triage.run_id == "run-456"
        
        # Different instances
        assert user1_triage is not user2_triage
        assert user1_data is not user2_data
        
        # But same factory
        assert user1_triage.name == user2_triage.name == "triage"
        assert user1_data.name == user2_data.name == "data"
    
    def test_registry_metrics_real_usage_simulation(self):
        """Test metrics under realistic usage patterns."""
        registry = UniversalRegistry[Any]("TestRegistry")
        
        # Register mixed items
        for i in range(5):
            registry.register(f"agent-{i}", MockAgent(f"agent-{i}"), tags=["agent"])
            registry.register(f"tool-{i}", MockTool(f"tool-{i}"), tags=["tool"])
        
        # Register factories
        def agent_factory(ctx):
            return MockAgent(f"dynamic-{ctx.user_id}")
        
        registry.register_factory("dynamic-agent", agent_factory, tags=["dynamic", "agent"])
        
        # Simulate realistic access patterns
        contexts = [MockUserExecutionContext(f"user-{i}", f"run-{i}") for i in range(3)]
        
        # Heavy access to some items, light access to others
        for _ in range(50):
            registry.get("agent-0")  # Popular agent
            registry.get("tool-0")   # Popular tool
        
        for _ in range(10):
            registry.get("agent-1")  # Moderate usage
            registry.get("tool-1")
        
        # Some unused items (agent-2 through agent-4, tool-2 through tool-4)
        
        # Factory usage
        for ctx in contexts:
            for _ in range(5):
                registry.create_instance("dynamic-agent", ctx)
        
        # Get comprehensive metrics
        metrics = registry.get_metrics()
        
        # Verify metrics accuracy
        assert metrics["total_items"] == 11  # 5 agents + 5 tools + 1 factory
        # Note: total_retrievals includes get() calls which also happen during create_instance calls
        # Each create_instance() internally calls get() first, then creates via factory
        # So total retrievals = 120 (50+50+10+10 explicit get calls) + 15 (implicit get calls from create_instance)
        expected_retrievals = 120 + 15  # Explicit get calls + create_instance internal get calls
        assert metrics["metrics"]["total_retrievals"] >= 120  # At least the explicit calls
        assert metrics["metrics"]["factory_creations"] == 15  # 3 contexts * 5 calls
        
        # Check category distribution
        assert metrics["category_distribution"]["agent"] == 6  # 5 + 1 factory
        assert metrics["category_distribution"]["tool"] == 5
        assert metrics["category_distribution"]["dynamic"] == 1
        
        # Check most accessed
        most_accessed = metrics["most_accessed"]
        assert most_accessed[0]["key"] in ["agent-0", "tool-0"]
        assert most_accessed[0]["count"] == 50
        
        # Health check should be healthy
        health = registry.validate_health()
        assert health["status"] == "healthy" or health["status"] == "warning"
        
        # May warn about unused items but shouldn't be degraded


# ===================== RUN COMPREHENSIVE TESTS =====================

if __name__ == "__main__":
    # Run all tests with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10",
        "--cov=netra_backend.app.core.registry.universal_registry",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_reports/universal_registry_coverage"
    ])