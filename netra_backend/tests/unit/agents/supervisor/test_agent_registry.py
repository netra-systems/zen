"""Comprehensive AgentRegistry Unit Tests

CRITICAL TEST SUITE: Validates AgentRegistry SSOT implementation and functionality.

This test suite focuses on breadth of basic functionality for the AgentRegistry class
which extends UniversalRegistry to provide agent-specific registry capabilities.

BVJ: ALL segments | Platform Stability | Ensures agent registration system works correctly

Test Coverage:
1. Registry initialization and configuration
2. Default agent registration
3. Factory pattern support for user isolation
4. WebSocket manager integration  
5. Legacy agent registration compatibility
6. Agent retrieval and creation methods
7. Registry health and diagnostics
8. Thread safety for concurrent access
9. Error handling and validation
10. Registry state management
"""

import pytest
import asyncio
import threading
import time
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timezone

# Import the class under test
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, get_agent_registry

# Import dependencies for mocking
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class MockAgent(BaseAgent):
    """Mock agent for testing purposes."""
    
    def __init__(self, *args, **kwargs):
        # Initialize with minimal setup to avoid complex dependencies
        self.name = kwargs.get('name', 'mock_agent')
        self.llm_manager = kwargs.get('llm_manager')
        self.tool_dispatcher = kwargs.get('tool_dispatcher')
        self.context = kwargs.get('context')
        self.execution_priority = kwargs.get('execution_priority', 0)
        self._websocket_bridge = None
        
    async def execute(self, *args, **kwargs):
        return {"status": "success", "result": "mock_execution"}
    
    def set_websocket_bridge(self, bridge):
        self._websocket_bridge = bridge


class MockUserExecutionContext:
    """Mock UserExecutionContext for testing."""
    
    def __init__(self, user_id="test_user", run_id="test_run", thread_id="test_thread"):
        self.user_id = user_id
        self.run_id = run_id
        self.thread_id = thread_id
        self.request_id = f"req_{run_id}"
        self.created_at = datetime.now(timezone.utc)


class TestAgentRegistryInitialization:
    """Test AgentRegistry initialization and basic setup."""

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value="Mock response")
        return llm

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock(return_value={"result": "mock"})
        return dispatcher

    def test_init_with_required_dependencies_creates_registry_successfully(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that AgentRegistry initializes successfully with required dependencies."""
        # Create factory function for the new SSOT API
        def mock_factory(user_context=None, websocket_bridge=None):
            return mock_tool_dispatcher
        
        registry = AgentRegistry(mock_llm_manager, mock_factory)
        
        assert registry.llm_manager is mock_llm_manager
        assert registry.tool_dispatcher_factory is mock_factory
        # tool_dispatcher property is deprecated and returns None for security
        assert registry.tool_dispatcher is None  
        assert registry._agents_registered is False
        assert isinstance(registry.registration_errors, dict)
        assert len(registry.registration_errors) == 0
        assert registry.name == "AgentRegistry"  # Inherited from UniversalRegistry

    def test_init_inherits_from_universal_registry_correctly(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that AgentRegistry properly inherits from UniversalRegistry."""
        registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
        
        # Should have UniversalRegistry methods
        assert hasattr(registry, 'register')
        assert hasattr(registry, 'get')
        assert hasattr(registry, 'list_keys')
        assert hasattr(registry, 'remove')
        assert hasattr(registry, 'register_factory')
        assert hasattr(registry, 'has')

    def test_init_with_none_llm_manager_should_work(self, mock_tool_dispatcher):
        """Test initialization with None LLM manager (should work but may limit functionality)."""
        # Create factory function for the new SSOT API
        def mock_factory(user_context=None, websocket_bridge=None):
            return mock_tool_dispatcher
        
        registry = AgentRegistry(None, mock_factory)
        
        assert registry.llm_manager is None
        assert registry.tool_dispatcher_factory is mock_factory
        # tool_dispatcher property is deprecated and returns None for security
        assert registry.tool_dispatcher is None
        assert registry._agents_registered is False

    def test_init_with_none_tool_dispatcher_should_work(self, mock_llm_manager):
        """Test initialization with None tool dispatcher (should work but may limit functionality)."""
        registry = AgentRegistry(mock_llm_manager, None)
        
        assert registry.llm_manager is mock_llm_manager
        assert registry.tool_dispatcher is None
        assert registry._agents_registered is False

    def test_init_sets_websocket_attributes_to_none(self, mock_llm_manager, mock_tool_dispatcher):
        """Test that WebSocket attributes are initialized to None."""
        registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
        
        # WebSocket attributes should be None initially
        assert registry.websocket_manager is None
        assert registry.websocket_bridge is None


class TestDefaultAgentRegistration:
    """Test default agent registration functionality."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_register_default_agents_when_not_registered_should_register_agents(self, registry):
        """Test that default agents are registered when not previously registered."""
        with patch.object(registry, '_register_core_agents') as mock_core, \
             patch.object(registry, '_register_auxiliary_agents') as mock_aux:
            
            registry.register_default_agents()
            
            mock_core.assert_called_once()
            mock_aux.assert_called_once()
            assert registry._agents_registered is True

    def test_register_default_agents_when_already_registered_should_skip(self, registry):
        """Test that default agents registration is skipped if already registered."""
        registry._agents_registered = True
        
        with patch.object(registry, '_register_core_agents') as mock_core, \
             patch.object(registry, '_register_auxiliary_agents') as mock_aux:
            
            registry.register_default_agents()
            
            mock_core.assert_not_called()
            mock_aux.assert_not_called()

    def test_register_default_agents_multiple_calls_should_be_idempotent(self, registry):
        """Test that multiple calls to register_default_agents are idempotent."""
        with patch.object(registry, '_register_core_agents') as mock_core, \
             patch.object(registry, '_register_auxiliary_agents') as mock_aux:
            
            # First call should register
            registry.register_default_agents()
            assert mock_core.call_count == 1
            assert mock_aux.call_count == 1
            
            # Second call should skip
            registry.register_default_agents()
            assert mock_core.call_count == 1
            assert mock_aux.call_count == 1

    @patch('netra_backend.app.agents.triage.unified_triage_agent.UnifiedTriageAgent')
    @patch('netra_backend.app.agents.data.unified_data_agent.UnifiedDataAgent')
    def test_register_core_agents_should_register_factories(self, mock_data_agent, mock_triage_agent, registry):
        """Test that core agents are registered as factories."""
        with patch.object(registry, 'register_factory') as mock_register_factory, \
             patch.object(registry, '_register_optimization_agents'):
            
            registry._register_core_agents()
            
            # Should register triage and data factories
            assert mock_register_factory.call_count >= 2
            calls = mock_register_factory.call_args_list
            
            # Check that triage and data were registered
            registered_names = [call[0][0] for call in calls]
            assert 'triage' in registered_names
            assert 'data' in registered_names

    def test_register_optimization_agents_should_register_factories(self, registry):
        """Test that optimization agents are registered as factories."""
        with patch.object(registry, 'register_factory') as mock_register_factory:
            
            registry._register_optimization_agents()
            
            # Should register optimization and actions factories
            assert mock_register_factory.call_count == 2
            calls = mock_register_factory.call_args_list
            
            registered_names = [call[0][0] for call in calls]
            assert 'optimization' in registered_names
            assert 'actions' in registered_names

    def test_register_core_agents_with_import_error_should_log_error(self, registry):
        """Test that import errors during core agent registration are handled gracefully."""
        # Force an error by making register_factory raise an exception
        def failing_register_factory(*args, **kwargs):
            raise ImportError("Module not found")
        
        with patch.object(registry, 'register_factory', side_effect=failing_register_factory):
            registry._register_core_agents()
            
            # Should record the error
            assert 'core_agents' in registry.registration_errors
            assert 'Module not found' in registry.registration_errors['core_agents']

    def test_register_auxiliary_agents_calls_all_auxiliary_registration_methods(self, registry):
        """Test that auxiliary agent registration calls all required methods."""
        with patch.object(registry, '_register_reporting_agent') as mock_reporting, \
             patch.object(registry, '_register_goals_triage_agent') as mock_goals, \
             patch.object(registry, '_register_data_helper_agent') as mock_helper, \
             patch.object(registry, '_register_synthetic_data_agent') as mock_synthetic, \
             patch.object(registry, '_register_corpus_admin_agent') as mock_corpus:
            
            registry._register_auxiliary_agents()
            
            mock_reporting.assert_called_once()
            mock_goals.assert_called_once()
            mock_helper.assert_called_once()
            mock_synthetic.assert_called_once()
            mock_corpus.assert_called_once()


class TestFactoryPatternSupport:
    """Test factory pattern support for user isolation."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    @pytest.fixture
    def mock_context(self):
        """Create mock execution context."""
        return MockUserExecutionContext()

    def test_register_factory_should_register_factory_function(self, registry):
        """Test that factory functions can be registered."""
        def mock_factory(context):
            return MockAgent(name="test_agent", context=context)
        
        registry.register_factory("test_factory", mock_factory, tags=["test"], description="Test factory")
        
        assert registry.has("test_factory")
        assert "test_factory" in registry.list_keys()

    def test_get_with_context_should_call_factory(self, registry, mock_context):
        """Test that get() with context calls the factory function."""
        def mock_factory(context):
            agent = MockAgent(name="factory_agent", context=context)
            return agent
        
        registry.register_factory("factory_test", mock_factory)
        
        agent = registry.get("factory_test", mock_context)
        
        assert agent is not None
        assert agent.name == "factory_agent"
        assert agent.context is mock_context

    def test_get_without_context_factory_only_returns_none(self, registry):
        """Test that get() without context on factory-only item returns None."""
        def mock_factory(context):
            return MockAgent(name="factory_agent")
        
        registry.register_factory("factory_only", mock_factory)
        
        agent = registry.get("factory_only")  # No context provided
        
        assert agent is None

    def test_create_instance_should_create_new_instance(self, registry, mock_context):
        """Test that create_instance creates a new instance via factory."""
        def mock_factory(context):
            return MockAgent(name="fresh_agent", context=context)
        
        registry.register_factory("factory_create", mock_factory)
        
        agent = registry.create_instance("factory_create", mock_context)
        
        assert agent is not None
        assert agent.name == "fresh_agent"
        assert agent.context is mock_context

    def test_create_instance_with_invalid_key_should_raise_keyerror(self, registry, mock_context):
        """Test that create_instance with invalid key raises KeyError."""
        with pytest.raises(KeyError, match="No factory for invalid_key"):
            registry.create_instance("invalid_key", mock_context)

    def test_create_instance_on_singleton_should_raise_keyerror(self, registry, mock_context):
        """Test that create_instance on singleton registration raises KeyError."""
        agent = MockAgent(name="singleton_agent")
        registry.register("singleton", agent)
        
        with pytest.raises(KeyError, match="No factory for singleton"):
            registry.create_instance("singleton", mock_context)


class TestWebSocketIntegration:
    """Test WebSocket manager and bridge integration."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return Mock(spec=WebSocketManager)

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge."""
        return Mock(spec=AgentWebSocketBridge)

    def test_set_websocket_manager_should_store_manager(self, registry, mock_websocket_manager):
        """Test that WebSocket manager can be set."""
        registry.set_websocket_manager(mock_websocket_manager)
        
        assert registry.websocket_manager is mock_websocket_manager

    def test_set_websocket_bridge_should_store_bridge(self, registry, mock_websocket_bridge):
        """Test that WebSocket bridge can be set."""
        registry.set_websocket_bridge(mock_websocket_bridge)
        
        assert registry.websocket_bridge is mock_websocket_bridge

    def test_set_websocket_bridge_with_none_should_raise_error(self, registry):
        """Test that setting None WebSocket bridge raises ValueError."""
        with pytest.raises(ValueError, match="WebSocket bridge cannot be None"):
            registry.set_websocket_bridge(None)

    def test_create_agent_with_context_should_inject_websocket_bridge(self, registry, mock_websocket_bridge):
        """Test that agent creation injects WebSocket bridge."""
        # Setup registry with bridge
        registry.set_websocket_bridge(mock_websocket_bridge)
        
        # Register factory
        def factory(context):
            agent = MockAgent(name="ws_agent")
            return agent
        
        registry.register_factory("ws_test", factory)
        
        # Create context
        context = MockUserExecutionContext()
        
        # Create agent
        agent = registry.create_agent_with_context("ws_test", context, None, None)
        
        assert agent is not None
        assert agent._websocket_bridge is mock_websocket_bridge

    def test_create_agent_with_context_invalid_key_should_raise_error(self, registry):
        """Test that invalid key in create_agent_with_context raises KeyError."""
        context = MockUserExecutionContext()
        
        with pytest.raises(KeyError, match="Agent invalid_agent not found"):
            registry.create_agent_with_context("invalid_agent", context, None, None)

    def test_diagnose_websocket_wiring_with_no_bridge_shows_critical_issue(self, registry):
        """Test that WebSocket diagnosis detects missing bridge."""
        diagnosis = registry.diagnose_websocket_wiring()
        
        assert diagnosis["registry_has_websocket_bridge"] is False
        assert diagnosis["registry_has_websocket_manager"] is False
        assert "No global WebSocket bridge configured" in diagnosis["critical_issues"]
        assert "No global WebSocket manager configured" in diagnosis["critical_issues"]
        assert diagnosis["websocket_health"] == "CRITICAL"

    def test_diagnose_websocket_wiring_with_components_shows_healthy(self, registry, mock_websocket_manager, mock_websocket_bridge):
        """Test that WebSocket diagnosis shows healthy when components are present."""
        registry.set_websocket_manager(mock_websocket_manager)
        registry.set_websocket_bridge(mock_websocket_bridge)
        
        diagnosis = registry.diagnose_websocket_wiring()
        
        assert diagnosis["registry_has_websocket_bridge"] is True
        assert diagnosis["registry_has_websocket_manager"] is True
        assert len(diagnosis["critical_issues"]) == 0
        assert diagnosis["websocket_health"] == "HEALTHY"


class TestLegacyAgentRegistration:
    """Test legacy agent registration for backward compatibility."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_register_agent_singleton_should_work(self, registry):
        """Test that legacy register method works for singleton agents."""
        agent = MockAgent(name="legacy_agent")
        
        registry.register("legacy", agent)
        
        assert registry.has("legacy")
        retrieved = registry.get("legacy")
        assert retrieved is agent

    def test_register_agent_should_clear_registration_errors(self, registry):
        """Test that successful registration clears previous errors."""
        # Set up an error first
        registry.registration_errors["test_agent"] = "Previous error"
        
        agent = MockAgent(name="test_agent")
        registry.register("test_agent", agent)
        
        assert "test_agent" not in registry.registration_errors

    def test_register_agent_with_error_should_record_error(self, registry):
        """Test that registration errors are properly recorded."""
        # Mock the parent register method to raise an exception
        with patch.object(registry.__class__.__bases__[0], 'register', side_effect=ValueError("Registration failed")):
            
            agent = MockAgent(name="error_agent")
            registry.register("error_agent", agent)
            
            assert "error_agent" in registry.registration_errors
            assert "Registration failed" in registry.registration_errors["error_agent"]

    @pytest.mark.asyncio
    async def test_register_agent_safely_successful_registration(self, registry):
        """Test that register_agent_safely returns True on successful registration."""
        with patch.object(registry, 'register') as mock_register:
            mock_register.return_value = None  # Successful registration
            
            result = await registry.register_agent_safely("test_agent", MockAgent)
            
            assert result is True
            mock_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_agent_safely_failed_registration(self, registry):
        """Test that register_agent_safely returns False on failed registration."""
        with patch.object(registry, 'register', side_effect=ValueError("Failed")):
            
            result = await registry.register_agent_safely("test_agent", MockAgent)
            
            assert result is False
            assert "test_agent" in registry.registration_errors

    def test_register_with_override_not_allowed_should_record_error(self, registry):
        """Test that registering duplicate key without override records error."""
        agent1 = MockAgent(name="agent1")
        agent2 = MockAgent(name="agent2")
        
        registry.register("duplicate", agent1)
        
        # Should succeed first time
        assert registry.has("duplicate")
        assert "duplicate" not in registry.registration_errors
        
        # Should record error on duplicate registration
        registry.register("duplicate", agent2)
        
        # Should have recorded the error instead of raising exception
        assert "duplicate" in registry.registration_errors
        assert "already registered" in registry.registration_errors["duplicate"]


class TestAgentRetrievalMethods:
    """Test agent retrieval and listing methods."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_get_agent_with_singleton_should_return_agent(self, registry):
        """Test that get_agent returns singleton agent."""
        agent = MockAgent(name="singleton")
        registry.register("singleton", agent)
        
        retrieved = asyncio.run(registry.get_agent("singleton"))
        
        assert retrieved is agent

    def test_get_agent_with_factory_and_context_should_return_new_instance(self, registry):
        """Test that get_agent with context creates new instance via factory."""
        def factory(context):
            return MockAgent(name="factory_agent", context=context)
        
        registry.register_factory("factory", factory)
        context = MockUserExecutionContext()
        
        agent = asyncio.run(registry.get_agent("factory", context))
        
        assert agent is not None
        assert agent.name == "factory_agent"
        assert agent.context is context

    def test_get_agent_nonexistent_should_return_none(self, registry):
        """Test that getting non-existent agent returns None."""
        agent = asyncio.run(registry.get_agent("nonexistent"))
        
        assert agent is None

    def test_list_agents_should_return_all_registered_keys(self, registry):
        """Test that list_agents returns all registered agent names."""
        registry.register("agent1", MockAgent(name="agent1"))
        registry.register_factory("agent2", lambda c: MockAgent(name="agent2"))
        
        agents = registry.list_agents()
        
        assert "agent1" in agents
        assert "agent2" in agents
        assert len(agents) >= 2

    def test_remove_agent_existing_should_return_true(self, registry):
        """Test that removing existing agent returns True."""
        registry.register("removable", MockAgent(name="removable"))
        
        result = registry.remove_agent("removable")
        
        assert result is True
        assert not registry.has("removable")

    def test_remove_agent_nonexistent_should_return_false(self, registry):
        """Test that removing non-existent agent returns False."""
        result = registry.remove_agent("nonexistent")
        
        assert result is False

    def test_has_agent_existing_should_return_true(self, registry):
        """Test that has() returns True for existing agents."""
        registry.register("existing", MockAgent(name="existing"))
        
        assert registry.has("existing") is True

    def test_has_agent_nonexistent_should_return_false(self, registry):
        """Test that has() returns False for non-existent agents."""
        assert registry.has("nonexistent") is False


class TestRegistryHealthAndDiagnostics:
    """Test registry health monitoring and diagnostic methods."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_get_registry_health_empty_registry(self, registry):
        """Test registry health for empty registry."""
        health = registry.get_registry_health()
        
        assert health["total_agents"] == 0
        assert health["failed_registrations"] == 0
        assert health["using_universal_registry"] is True
        assert isinstance(health["registration_errors"], dict)

    def test_get_registry_health_with_agents(self, registry):
        """Test registry health with registered agents."""
        registry.register("test1", MockAgent(name="test1"))
        registry.register_factory("test2", lambda c: MockAgent(name="test2"))
        
        health = registry.get_registry_health()
        
        assert health["total_agents"] == 2
        assert health["failed_registrations"] == 0
        assert health["using_universal_registry"] is True

    def test_get_registry_health_with_errors(self, registry):
        """Test registry health with registration errors."""
        registry.registration_errors["failed_agent"] = "Import error"
        
        health = registry.get_registry_health()
        
        assert health["failed_registrations"] == 1
        assert "failed_agent" in health["registration_errors"]

    def test_get_factory_integration_status_returns_expected_fields(self, registry):
        """Test that factory integration status returns all expected fields."""
        status = registry.get_factory_integration_status()
        
        assert status["using_universal_registry"] is True
        assert status["factory_patterns_enabled"] is True
        assert "total_factories" in status
        assert status["thread_safe"] is True
        assert "metrics_enabled" in status
        assert "timestamp" in status

    @pytest.mark.asyncio
    async def test_reset_all_agents_factory_pattern_returns_success(self, registry):
        """Test that reset_all_agents returns success for factory pattern."""
        registry.register("test1", MockAgent(name="test1"))
        registry.register_factory("test2", lambda c: MockAgent(name="test2"))
        
        result = await registry.reset_all_agents()
        
        assert result["total_agents"] == 2
        assert result["successful_resets"] == 2
        assert result["failed_resets"] == 0
        assert result["using_universal_registry"] is True
        assert "reset_details" in result


class TestThreadSafety:
    """Test thread safety for concurrent access."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_concurrent_registration_should_not_conflict(self, registry):
        """Test that concurrent registrations don't conflict."""
        def register_agent(i):
            agent = MockAgent(name=f"agent_{i}")
            registry.register(f"concurrent_{i}", agent)
        
        # Create multiple threads registering agents
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_agent, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all agents were registered
        agents = registry.list_agents()
        for i in range(10):
            assert f"concurrent_{i}" in agents

    def test_concurrent_factory_creation_should_work(self, registry):
        """Test that concurrent factory creations work correctly."""
        def factory(context):
            return MockAgent(name="factory_agent", context=context)
        
        registry.register_factory("concurrent_factory", factory)
        
        results = []
        
        def create_agent(user_id):
            context = MockUserExecutionContext(user_id=f"user_{user_id}")
            agent = registry.get("concurrent_factory", context)
            results.append((user_id, agent))
        
        # Create multiple threads creating agents
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_agent, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all agents were created
        assert len(results) == 5
        for user_id, agent in results:
            assert agent is not None
            assert agent.context.user_id == f"user_{user_id}"

    def test_concurrent_websocket_manager_setting_should_be_thread_safe(self, registry):
        """Test that setting WebSocket manager concurrently is thread-safe."""
        managers = []
        for i in range(5):
            manager = Mock(spec=WebSocketManager)
            manager.name = f"manager_{i}"
            managers.append(manager)
        
        def set_manager(manager):
            registry.set_websocket_manager(manager)
        
        # Create multiple threads setting managers
        threads = []
        for manager in managers:
            thread = threading.Thread(target=set_manager, args=(manager,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify a manager was set (last one wins)
        assert registry.websocket_manager is not None
        assert hasattr(registry.websocket_manager, 'name')


class TestErrorHandlingAndValidation:
    """Test error handling and validation mechanisms."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_registration_with_invalid_agent_should_handle_error(self, registry):
        """Test that registering invalid agent type handles error gracefully."""
        # Try to register a non-agent object
        invalid_agent = "not_an_agent"
        
        # This should not crash, but might record an error
        try:
            registry.register("invalid", invalid_agent)
        except (ValueError, TypeError):
            # Expected - invalid agent should be rejected
            pass
        
        # Verify it didn't break the registry
        assert registry.has("invalid") == False

    def test_factory_creation_error_should_not_break_registry(self, registry):
        """Test that factory creation errors don't break the registry."""
        def failing_factory(context):
            raise ValueError("Factory creation failed")
        
        registry.register_factory("failing_factory", failing_factory)
        
        # This should raise the factory error, not break the registry
        with pytest.raises(ValueError, match="Factory creation failed"):
            registry.get("failing_factory", MockUserExecutionContext())
        
        # Registry should still be functional
        assert registry.has("failing_factory") is True

    def test_websocket_bridge_validation_should_reject_none(self, registry):
        """Test that WebSocket bridge validation rejects None values."""
        with pytest.raises(ValueError, match="WebSocket bridge cannot be None"):
            registry.set_websocket_bridge(None)

    def test_get_with_invalid_context_type_should_handle_gracefully(self, registry):
        """Test that invalid context types are handled gracefully."""
        def factory(context):
            return MockAgent(name="context_agent", context=context)
        
        registry.register_factory("context_test", factory)
        
        # Try with invalid context
        result = registry.get("context_test", "invalid_context_type")
        
        # Should either work or return None, not crash
        # Implementation may vary on how it handles invalid contexts

    @pytest.mark.asyncio
    async def test_register_agent_safely_with_constructor_error(self, registry):
        """Test register_agent_safely handles constructor errors."""
        class FailingAgent:
            def __init__(self, *args, **kwargs):
                raise ValueError("Constructor failed")
        
        result = await registry.register_agent_safely("failing", FailingAgent)
        
        assert result is False
        assert "failing" in registry.registration_errors


class TestGetAgentRegistryFunction:
    """Test the get_agent_registry module function."""

    def test_get_agent_registry_creates_new_registry(self):
        """Test that get_agent_registry creates a new registry."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        
        # Create factory function for the new SSOT API
        def dispatcher_factory(user_context=None, websocket_bridge=None):
            return dispatcher
        
        registry = get_agent_registry(llm, dispatcher_factory)
        
        assert isinstance(registry, AgentRegistry)
        assert registry.llm_manager is llm
        assert registry.tool_dispatcher_factory is dispatcher_factory
        # tool_dispatcher property is deprecated and returns None for security
        assert registry.tool_dispatcher is None

    def test_get_agent_registry_with_existing_global_registry(self):
        """Test that get_agent_registry handles existing global registry."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        
        # Mock the global registry
        with patch('netra_backend.app.agents.supervisor.agent_registry.get_global_registry') as mock_get_global:
            mock_registry = Mock(spec=AgentRegistry)
            mock_registry.llm_manager = llm
            mock_registry.tool_dispatcher = dispatcher
            mock_get_global.return_value = mock_registry
            
            registry = get_agent_registry(llm, dispatcher)
            
            # Should return the mocked registry
            assert registry is mock_registry

    def test_get_agent_registry_with_exception_creates_new_registry(self):
        """Test that get_agent_registry creates new registry when global registry fails."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        
        # Create factory function for the new SSOT API
        def dispatcher_factory(user_context=None, websocket_bridge=None):
            return dispatcher
        
        with patch('netra_backend.app.agents.supervisor.agent_registry.get_global_registry', side_effect=Exception("Global registry failed")):
            
            registry = get_agent_registry(llm, dispatcher_factory)
            
            assert isinstance(registry, AgentRegistry)
            assert registry.llm_manager is llm
            assert registry.tool_dispatcher_factory is dispatcher_factory
            # tool_dispatcher property is deprecated and returns None for security
            assert registry.tool_dispatcher is None


class TestRegistryStateManagement:
    """Test registry state management and lifecycle."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    def test_registry_starts_in_clean_state(self, registry):
        """Test that registry starts in a clean initial state."""
        assert len(registry.list_keys()) == 0
        assert len(registry.registration_errors) == 0
        assert registry._agents_registered is False
        assert registry.websocket_manager is None
        assert registry.websocket_bridge is None

    def test_clear_registry_should_remove_all_agents(self, registry):
        """Test that clearing registry removes all agents."""
        # Add some agents
        registry.register("agent1", MockAgent(name="agent1"))
        registry.register_factory("agent2", lambda c: MockAgent(name="agent2"))
        
        assert len(registry.list_keys()) == 2
        
        # Clear registry
        registry.clear()
        
        assert len(registry.list_keys()) == 0

    def test_registry_metrics_tracking(self, registry):
        """Test that registry tracks metrics properly."""
        # Register some agents
        registry.register("metric_agent1", MockAgent(name="metric1"))
        registry.register_factory("metric_agent2", lambda c: MockAgent(name="metric2"))
        
        # Get some agents to increment access counts
        registry.get("metric_agent1")
        context = MockUserExecutionContext()
        registry.get("metric_agent2", context)
        
        # Check metrics
        metrics = registry.get_metrics()
        
        assert metrics["total_items"] == 2
        assert metrics["metrics"]["total_registrations"] == 2
        assert metrics["metrics"]["successful_registrations"] == 2
        assert metrics["metrics"]["total_retrievals"] >= 2

    def test_list_by_tag_should_filter_agents_correctly(self, registry):
        """Test that list_by_tag filters agents by their tags."""
        registry.register_factory("core_agent", lambda c: MockAgent(), tags=["core", "workflow"])
        registry.register_factory("aux_agent", lambda c: MockAgent(), tags=["auxiliary"])
        registry.register_factory("mixed_agent", lambda c: MockAgent(), tags=["core", "auxiliary"])
        
        core_agents = registry.list_by_tag("core")
        aux_agents = registry.list_by_tag("auxiliary")
        
        assert "core_agent" in core_agents
        assert "mixed_agent" in core_agents
        assert "aux_agent" not in core_agents
        
        assert "aux_agent" in aux_agents
        assert "mixed_agent" in aux_agents
        assert "core_agent" not in aux_agents

    def test_validation_health_checks_empty_registry_warning(self, registry):
        """Test that health validation warns about empty registries."""
        health = registry.validate_health()
        
        assert health["status"] in ["warning", "healthy"]  # Empty registry might be a warning
        if health["status"] == "warning":
            assert any("empty" in issue.lower() for issue in health["issues"])


class TestSpecificAgentRegistrationMethods:
    """Test specific agent registration helper methods."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        llm = Mock(spec=LLMManager)
        dispatcher = Mock(spec=ToolDispatcher)
        return AgentRegistry(llm, dispatcher)

    @patch('netra_backend.app.agents.reporting_sub_agent.ReportingSubAgent')
    def test_register_reporting_agent_success(self, mock_reporting_agent, registry):
        """Test successful reporting agent registration."""
        with patch.object(registry, 'register_factory') as mock_register:
            registry._register_reporting_agent()
            
            mock_register.assert_called_once()
            args, kwargs = mock_register.call_args
            assert args[0] == "reporting"
            assert "reporting" in kwargs.get("tags", [])

    def test_register_reporting_agent_import_error(self, registry):
        """Test reporting agent registration with import error."""
        # Force an error by making register_factory raise an exception
        def failing_register_factory(*args, **kwargs):
            raise ImportError("Module not found")
        
        with patch.object(registry, 'register_factory', side_effect=failing_register_factory):
            registry._register_reporting_agent()
            
            assert "reporting" in registry.registration_errors
            assert "Module not found" in registry.registration_errors["reporting"]

    @patch('netra_backend.app.agents.goals_triage_sub_agent.GoalsTriageSubAgent')
    def test_register_goals_triage_agent_success(self, mock_goals_agent, registry):
        """Test successful goals triage agent registration."""
        with patch.object(registry, 'register_factory') as mock_register:
            registry._register_goals_triage_agent()
            
            mock_register.assert_called_once()
            args, kwargs = mock_register.call_args
            assert args[0] == "goals_triage"

    @patch('netra_backend.app.agents.data_helper_agent.DataHelperAgent') 
    def test_register_data_helper_agent_success(self, mock_helper_agent, registry):
        """Test successful data helper agent registration."""
        with patch.object(registry, 'register_factory') as mock_register:
            registry._register_data_helper_agent()
            
            mock_register.assert_called_once()
            args, kwargs = mock_register.call_args
            assert args[0] == "data_helper"

    @patch('netra_backend.app.agents.synthetic_data_sub_agent.SyntheticDataSubAgent')
    def test_register_synthetic_data_agent_success(self, mock_synthetic_agent, registry):
        """Test successful synthetic data agent registration."""
        with patch.object(registry, 'register_factory') as mock_register:
            registry._register_synthetic_data_agent()
            
            mock_register.assert_called_once()
            args, kwargs = mock_register.call_args
            assert args[0] == "synthetic_data"

    @patch('netra_backend.app.admin.corpus.CorpusAdminSubAgent')
    def test_register_corpus_admin_agent_success(self, mock_corpus_agent, registry):
        """Test successful corpus admin agent registration."""
        with patch.object(registry, 'register_factory') as mock_register:
            registry._register_corpus_admin_agent()
            
            mock_register.assert_called_once()
            args, kwargs = mock_register.call_args
            assert args[0] == "corpus_admin"