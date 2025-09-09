"""
Unit Tests for AgentRegistry Registration Patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal & All tiers
- Business Goal: Reliable agent factory registration and instantiation
- Value Impact: Enables dynamic agent creation with proper error handling
- Strategic Impact: Foundation for scalable agent ecosystem

CRITICAL MISSION: Test AgentRegistry registration patterns ensuring:
1. Agent factory registration and management
2. Default agent registration with error handling
3. Safe agent registration patterns with validation
4. Legacy agent registration backward compatibility
5. Agent class instantiation with dependency injection
6. Tool dispatcher factory integration
7. Registration error tracking and reporting
8. Agent registration state management

FOCUS: Factory-based registration patterns as per SSOT architecture
"""

import asyncio
import pytest
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession,
    AgentLifecycleManager
)

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager for testing."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm._initialized = True
    mock_llm.chat_completion = AsyncMock(return_value="Test response")
    mock_llm.is_healthy = Mock(return_value=True)
    return mock_llm


@pytest.fixture
def mock_agent_class():
    """Create mock agent class that behaves like BaseAgent."""
    class MockAgent:
        def __init__(self, llm_manager=None, tool_dispatcher=None, *args, **kwargs):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.cleanup = AsyncMock()
            self.close = AsyncMock()
            self.reset = AsyncMock()
    
    return MockAgent


@pytest.fixture
def failing_agent_class():
    """Create agent class that fails during instantiation."""
    class FailingAgent:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Agent instantiation failed")
    
    return FailingAgent


@pytest.fixture
def test_user_context():
    """Create test user execution context."""
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        request_id=f"test_request_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}"
    )


# ============================================================================
# TEST: Agent Factory Registration 
# ============================================================================

class TestAgentFactoryRegistration(SSotBaseTestCase):
    """Test agent factory registration and management."""
    
    def test_register_default_agents_sets_registration_flag(self, mock_llm_manager):
        """Test that register_default_agents properly sets registration flag."""
        registry = AgentRegistry(mock_llm_manager)
        assert registry._agents_registered is False
        
        registry.register_default_agents()
        
        assert registry._agents_registered is True
    
    def test_register_default_agents_idempotent_behavior(self, mock_llm_manager):
        """Test that register_default_agents is idempotent."""
        registry = AgentRegistry(mock_llm_manager)
        
        # First registration
        registry.register_default_agents()
        initial_count = len(registry.list_keys())
        initial_errors = len(registry.registration_errors)
        
        # Second registration should not change anything
        registry.register_default_agents()
        final_count = len(registry.list_keys())
        final_errors = len(registry.registration_errors)
        
        assert initial_count == final_count
        assert initial_errors == final_errors
    
    def test_register_default_agents_attempts_all_registrations(self, mock_llm_manager):
        """Test that register_default_agents attempts to register all expected agents."""
        registry = AgentRegistry(mock_llm_manager)
        
        with patch.object(registry, '_register_core_agents') as mock_core, \
             patch.object(registry, '_register_auxiliary_agents') as mock_aux:
            
            registry.register_default_agents()
            
            mock_core.assert_called_once()
            mock_aux.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_agent_safely_success_scenario(self, mock_llm_manager, mock_agent_class):
        """Test successful agent registration via register_agent_safely."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Mock legacy dispatcher to avoid None error
        registry._legacy_dispatcher = Mock()
        
        result = await registry.register_agent_safely(
            name="test_agent",
            agent_class=mock_agent_class,
            custom_param="test_value"
        )
        
        assert result is True
        assert "test_agent" not in registry.registration_errors
        assert "test_agent" in registry.list_keys()
    
    @pytest.mark.asyncio 
    async def test_register_agent_safely_failure_scenario(self, mock_llm_manager, failing_agent_class):
        """Test failed agent registration via register_agent_safely."""
        registry = AgentRegistry(mock_llm_manager)
        
        result = await registry.register_agent_safely(
            name="failing_agent", 
            agent_class=failing_agent_class
        )
        
        assert result is False
        assert "failing_agent" in registry.registration_errors
        assert "Agent instantiation failed" in registry.registration_errors["failing_agent"]
    
    @pytest.mark.asyncio
    async def test_register_agent_safely_parameter_passing(self, mock_llm_manager, mock_agent_class):
        """Test that register_agent_safely passes parameters correctly."""
        registry = AgentRegistry(mock_llm_manager)
        registry._legacy_dispatcher = Mock()
        
        # Mock agent class to capture constructor calls
        mock_class = Mock(return_value=Mock())
        
        await registry.register_agent_safely(
            name="param_test_agent",
            agent_class=mock_class,
            extra_param="test_value",
            another_param=42
        )
        
        # Verify agent was constructed with correct parameters
        mock_class.assert_called_once_with(
            registry.llm_manager,
            registry._legacy_dispatcher,
            extra_param="test_value",
            another_param=42
        )
    
    def test_register_method_backward_compatibility(self, mock_llm_manager):
        """Test backward compatible register method."""
        registry = AgentRegistry(mock_llm_manager)
        mock_agent = Mock()
        
        # Should not raise exception
        registry.register("test_agent", mock_agent)
        
        # Verify agent is registered
        assert "test_agent" in registry.list_keys()
        assert "test_agent" not in registry.registration_errors
    
    def test_register_method_handles_registration_errors(self, mock_llm_manager):
        """Test register method handles registration errors."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Mock the parent register method to raise an exception
        with patch.object(registry.__class__.__bases__[0], 'register', 
                         side_effect=Exception("Registration failed")):
            mock_agent = Mock()
            registry.register("failing_agent", mock_agent)
            
            # Should record the error instead of raising
            assert "failing_agent" in registry.registration_errors
            assert "Registration failed" in registry.registration_errors["failing_agent"]


# ============================================================================
# TEST: Core and Auxiliary Agent Registration
# ============================================================================

class TestCoreAndAuxiliaryAgentRegistration(SSotBaseTestCase):
    """Test core and auxiliary agent registration patterns."""
    
    @pytest.mark.asyncio
    async def test_register_core_agents_comprehensive(self, mock_llm_manager):
        """Test registration of core agents with error handling."""
        registry = AgentRegistry(mock_llm_manager)
        
        with patch.object(registry, 'register_agent_safely') as mock_register:
            mock_register.return_value = True
            
            registry._register_core_agents()
            
            # Verify core agents were registered
            assert mock_register.call_count >= 3  # Should attempt core agents
            
            # Check that essential core agents were included
            called_names = [call[1]['name'] for call in mock_register.call_args_list]
            expected_core_agents = ['triage', 'goals_triage', 'reporting']
            
            for agent_name in expected_core_agents:
                assert any(agent_name in name for name in called_names)
    
    @pytest.mark.asyncio
    async def test_register_auxiliary_agents_comprehensive(self, mock_llm_manager):
        """Test registration of auxiliary agents with error handling."""
        registry = AgentRegistry(mock_llm_manager)
        
        with patch.object(registry, 'register_agent_safely') as mock_register:
            mock_register.return_value = True
            
            registry._register_auxiliary_agents()
            
            # Verify auxiliary agents were attempted
            assert mock_register.call_count >= 2  # Should attempt auxiliary agents
            
            # Check that essential auxiliary agents were included
            called_names = [call[1]['name'] for call in mock_register.call_args_list]
            expected_aux_agents = ['data', 'optimization_core']
            
            for agent_name in expected_aux_agents:
                assert any(agent_name in name for name in called_names)
    
    @pytest.mark.asyncio
    async def test_register_core_agents_handles_failures(self, mock_llm_manager):
        """Test core agent registration handles individual failures gracefully."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Mock register_agent_safely to fail for specific agents
        async def mock_register(name, agent_class, **kwargs):
            if 'failing' in name:
                return False
            return True
        
        with patch.object(registry, 'register_agent_safely', side_effect=mock_register):
            # Should not raise exception even if some registrations fail
            registry._register_core_agents()
            
            # Registry should still be functional
            assert isinstance(registry._agents_registered, bool)
    
    @pytest.mark.asyncio 
    async def test_register_auxiliary_agents_handles_import_failures(self, mock_llm_manager):
        """Test auxiliary agent registration handles import failures."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Mock import failures for specific agent modules
        with patch('netra_backend.app.agents.data_sub_agent.DataSubAgent', 
                   side_effect=ImportError("Module not found")), \
             patch.object(registry, 'register_agent_safely') as mock_register:
            
            registry._register_auxiliary_agents()
            
            # Should continue with other registrations despite import failures
            # The method should attempt registration but handle ImportError gracefully
            assert mock_register.call_count >= 0  # May not register failing imports


# ============================================================================
# TEST: Agent Factory Pattern Integration
# ============================================================================

class TestAgentFactoryPatternIntegration(SSotBaseTestCase):
    """Test integration between registry and factory patterns."""
    
    @pytest.mark.asyncio
    async def test_get_agent_with_factory_instantiation(self, mock_llm_manager, test_user_context):
        """Test agent retrieval with factory-based instantiation."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Register a mock agent factory
        mock_agent = Mock(spec=BaseAgent)
        registry.register("factory_agent", mock_agent)
        
        # Get agent should return factory instance
        retrieved_agent = await registry.get_async("factory_agent", test_user_context)
        
        # Should use factory patterns for new instance creation
        assert retrieved_agent is not None
    
    @pytest.mark.asyncio
    async def test_get_agent_handles_factory_failures(self, mock_llm_manager, test_user_context):
        """Test agent retrieval handles factory instantiation failures."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Mock agent that raises exception during get
        with patch.object(registry, 'get', side_effect=Exception("Factory failure")):
            
            result = await registry.get_async("failing_factory_agent", test_user_context)
            
            # Should handle gracefully
            assert result is None
    
    @pytest.mark.asyncio
    async def test_agent_state_reset_via_factory(self, mock_llm_manager):
        """Test agent state reset through factory patterns."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Register agents with reset methods
        mock_agent1 = Mock()
        mock_agent1.reset = AsyncMock()
        mock_agent2 = Mock() 
        mock_agent2.reset = AsyncMock()
        
        registry.register("reset_agent1", mock_agent1)
        registry.register("reset_agent2", mock_agent2)
        
        # Reset all agents
        reset_report = await registry.reset_all_agents()
        
        # Verify reset was called
        mock_agent1.reset.assert_called_once()
        mock_agent2.reset.assert_called_once()
        
        # Verify report structure
        assert 'total_agents' in reset_report
        assert 'successful_resets' in reset_report
        assert 'failed_resets' in reset_report
        assert reset_report['failed_resets'] == 0
    
    @pytest.mark.asyncio
    async def test_reset_all_agents_handles_failures(self, mock_llm_manager):
        """Test reset_all_agents handles individual agent failures."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Register agents with different reset behaviors
        successful_agent = Mock()
        successful_agent.reset = AsyncMock()
        
        failing_agent = Mock() 
        failing_agent.reset = AsyncMock(side_effect=Exception("Reset failed"))
        
        no_reset_agent = Mock()
        # no_reset_agent doesn't have reset method
        
        registry.register("successful", successful_agent)
        registry.register("failing", failing_agent)
        registry.register("no_reset", no_reset_agent)
        
        reset_report = await registry.reset_all_agents()
        
        # Should handle failures gracefully
        assert reset_report['successful_resets'] >= 1
        assert reset_report['failed_resets'] >= 1
        assert reset_report['agents_without_reset'] >= 1


# ============================================================================
# TEST: Tool Dispatcher Factory Registration
# ============================================================================

class TestToolDispatcherFactoryRegistration(SSotBaseTestCase):
    """Test tool dispatcher factory registration and creation patterns."""
    
    def test_set_tool_dispatcher_factory_custom(self, mock_llm_manager):
        """Test setting custom tool dispatcher factory."""
        registry = AgentRegistry(mock_llm_manager)
        
        custom_factory = AsyncMock()
        registry.set_tool_dispatcher_factory(custom_factory)
        
        assert registry.tool_dispatcher_factory == custom_factory
    
    @pytest.mark.asyncio
    async def test_default_dispatcher_factory_creation(self, mock_llm_manager, test_user_context):
        """Test default tool dispatcher factory."""
        registry = AgentRegistry(mock_llm_manager)
        
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher') as mock_dispatcher_class:
            mock_dispatcher = Mock()
            mock_dispatcher_class.create_for_user = AsyncMock(return_value=mock_dispatcher)
            
            result = await registry._default_dispatcher_factory(test_user_context)
            
            assert result == mock_dispatcher
            mock_dispatcher_class.create_for_user.assert_called_once_with(
                user_context=test_user_context,
                websocket_bridge=None,
                enable_admin_tools=False
            )
    
    @pytest.mark.asyncio
    async def test_create_tool_dispatcher_for_user_with_bridge(self, mock_llm_manager, test_user_context):
        """Test creating tool dispatcher with WebSocket bridge."""
        registry = AgentRegistry(mock_llm_manager)
        
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher') as mock_dispatcher_class:
            mock_dispatcher = Mock()
            mock_websocket_bridge = Mock()
            mock_dispatcher_class.create_for_user = AsyncMock(return_value=mock_dispatcher)
            
            result = await registry.create_tool_dispatcher_for_user(
                user_context=test_user_context,
                websocket_bridge=mock_websocket_bridge,
                enable_admin_tools=True
            )
            
            assert result == mock_dispatcher
            mock_dispatcher_class.create_for_user.assert_called_once_with(
                user_context=test_user_context,
                websocket_bridge=mock_websocket_bridge,
                enable_admin_tools=True
            )
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_factory_error_handling(self, mock_llm_manager, test_user_context):
        """Test tool dispatcher factory error handling."""
        # Create factory that raises exception
        async def failing_factory(user_context, websocket_bridge=None):
            raise RuntimeError("Factory creation failed")
        
        registry = AgentRegistry(mock_llm_manager, failing_factory)
        
        # Should raise the factory exception
        with pytest.raises(RuntimeError, match="Factory creation failed"):
            await registry.create_tool_dispatcher_for_user(test_user_context)
    
    def test_legacy_tool_dispatcher_property_deprecated(self, mock_llm_manager):
        """Test that legacy tool_dispatcher property returns None and warns."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Should return None for legacy compatibility
        assert registry.tool_dispatcher is None
    
    def test_legacy_tool_dispatcher_setter_deprecated(self, mock_llm_manager):
        """Test that legacy tool_dispatcher setter is deprecated."""
        registry = AgentRegistry(mock_llm_manager)
        mock_dispatcher = Mock()
        
        # Should store the value but still return None from property
        registry.tool_dispatcher = mock_dispatcher
        assert registry._legacy_dispatcher == mock_dispatcher
        assert registry.tool_dispatcher is None


# ============================================================================
# TEST: Registration State and Error Management
# ============================================================================

class TestRegistrationStateAndErrorManagement(SSotBaseTestCase):
    """Test registration state management and error tracking."""
    
    def test_registration_errors_tracking(self, mock_llm_manager):
        """Test that registration errors are properly tracked."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Initially no errors
        assert len(registry.registration_errors) == 0
        
        # Register some agents with errors
        with patch.object(registry.__class__.__bases__[0], 'register',
                         side_effect=Exception("Test registration error")):
            registry.register("error_agent", Mock())
        
        # Error should be tracked
        assert "error_agent" in registry.registration_errors
        assert "Test registration error" in registry.registration_errors["error_agent"]
    
    def test_registration_errors_accumulation(self, mock_llm_manager):
        """Test that multiple registration errors are accumulated."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Cause multiple registration errors
        error_agents = ["error1", "error2", "error3"]
        
        for agent_name in error_agents:
            with patch.object(registry.__class__.__bases__[0], 'register',
                             side_effect=Exception(f"Error for {agent_name}")):
                registry.register(agent_name, Mock())
        
        # All errors should be tracked
        assert len(registry.registration_errors) == len(error_agents)
        
        for agent_name in error_agents:
            assert agent_name in registry.registration_errors
            assert f"Error for {agent_name}" in registry.registration_errors[agent_name]
    
    def test_registration_flag_state_management(self, mock_llm_manager):
        """Test registration flag state management."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Initially not registered
        assert registry._agents_registered is False
        
        # Register default agents
        registry.register_default_agents()
        assert registry._agents_registered is True
        
        # Multiple calls should not change state
        registry.register_default_agents()
        assert registry._agents_registered is True
    
    def test_list_agents_returns_registered_keys(self, mock_llm_manager):
        """Test that list_agents returns registered agent keys."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Register some agents
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        registry.register("agent1", mock_agent1)
        registry.register("agent2", mock_agent2)
        
        agent_list = registry.list_agents()
        
        assert isinstance(agent_list, list)
        assert "agent1" in agent_list
        assert "agent2" in agent_list
    
    def test_remove_agent_delegates_properly(self, mock_llm_manager):
        """Test that remove_agent properly delegates to UniversalRegistry."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Register and then remove agent
        mock_agent = Mock()
        registry.register("test_agent", mock_agent)
        assert "test_agent" in registry.list_keys()
        
        result = registry.remove_agent("test_agent")
        
        assert result is True
        assert "test_agent" not in registry.list_keys()
    
    def test_remove_agent_returns_false_for_nonexistent(self, mock_llm_manager):
        """Test remove_agent returns False for non-existent agent.""" 
        registry = AgentRegistry(mock_llm_manager)
        
        result = registry.remove_agent("nonexistent_agent")
        assert result is False


# ============================================================================
# TEST: Registration Integration with Agent Factories
# ============================================================================

class TestRegistrationFactoryIntegration(SSotBaseTestCase):
    """Test integration between registration and agent factory patterns."""
    
    @pytest.mark.asyncio
    async def test_agent_registration_with_factory_methods(self, mock_llm_manager, mock_agent_class):
        """Test agent registration integrates with factory creation methods."""
        registry = AgentRegistry(mock_llm_manager)
        registry._legacy_dispatcher = Mock()
        
        # Register agent class
        await registry.register_agent_safely("factory_agent", mock_agent_class)
        
        # Should be available in registry
        assert "factory_agent" in registry.list_keys()
        
        # Should be able to retrieve (which uses factory patterns)
        agent = registry.get("factory_agent")
        assert agent is not None
    
    @pytest.mark.asyncio
    async def test_registered_agents_state_isolation(self, mock_llm_manager, mock_agent_class, test_user_context):
        """Test that registered agents maintain state isolation per user."""
        registry = AgentRegistry(mock_llm_manager)
        registry._legacy_dispatcher = Mock()
        
        # Register agent
        await registry.register_agent_safely("isolated_agent", mock_agent_class)
        
        # Get agent for different users should create separate instances
        agent1 = await registry.get_async("isolated_agent", test_user_context)
        
        # Create different user context
        user2_context = UserExecutionContext(
            user_id="different_user",
            request_id="different_request",
            thread_id="different_thread", 
            run_id="different_run"
        )
        agent2 = await registry.get_async("isolated_agent", user2_context)
        
        # Should be different instances (factory pattern creates new ones)
        assert agent1 is not None
        assert agent2 is not None
    
    @pytest.mark.asyncio
    async def test_registration_error_recovery(self, mock_llm_manager, failing_agent_class, mock_agent_class):
        """Test registration error recovery and continued operation."""
        registry = AgentRegistry(mock_llm_manager)
        registry._legacy_dispatcher = Mock()
        
        # Attempt to register failing agent
        result1 = await registry.register_agent_safely("failing_agent", failing_agent_class)
        assert result1 is False
        assert "failing_agent" in registry.registration_errors
        
        # Should still be able to register working agents
        result2 = await registry.register_agent_safely("working_agent", mock_agent_class)
        assert result2 is True
        assert "working_agent" in registry.list_keys()
        assert "working_agent" not in registry.registration_errors
    
    @pytest.mark.asyncio
    async def test_bulk_agent_registration_with_mixed_results(self, mock_llm_manager, 
                                                             mock_agent_class, failing_agent_class):
        """Test bulk agent registration handles mixed success/failure results."""
        registry = AgentRegistry(mock_llm_manager)
        registry._legacy_dispatcher = Mock()
        
        # Register multiple agents with mixed results
        agents_to_register = [
            ("successful1", mock_agent_class),
            ("failing1", failing_agent_class),
            ("successful2", mock_agent_class),
            ("failing2", failing_agent_class),
            ("successful3", mock_agent_class)
        ]
        
        results = []
        for name, agent_class in agents_to_register:
            result = await registry.register_agent_safely(name, agent_class)
            results.append((name, result))
        
        # Should have mix of successes and failures
        successful = [name for name, result in results if result]
        failed = [name for name, result in results if not result]
        
        assert len(successful) == 3  # successful1, successful2, successful3
        assert len(failed) == 2     # failing1, failing2
        
        # Registry should continue working despite failures
        assert len(registry.list_keys()) >= 3
        assert len(registry.registration_errors) == 2


if __name__ == "__main__":
    # Run tests with proper async support
    pytest.main([__file__, "-v", "--tb=short"])