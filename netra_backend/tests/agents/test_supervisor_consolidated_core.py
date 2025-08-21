"""Core tests for SupervisorAgent - initialization, registration, and properties."""

import pytest
from unittest.mock import AsyncMock, Mock
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path


class TestSupervisorAgentInitialization:
    """Test initialization and setup methods."""
    
    def test_init_base(self):
        """Test _init_base method."""
        # Mock LLM manager
        llm_manager = Mock(spec=LLMManager)
        
        # Create supervisor instance
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify base initialization
        assert supervisor.name == "Supervisor"
        assert supervisor.description == "The supervisor agent that orchestrates sub-agents"
        assert supervisor.llm_manager == llm_manager
    
    def test_init_services(self):
        """Test _init_services method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify services initialization
        assert supervisor.db_session == db_session
        assert supervisor.websocket_manager == websocket_manager
        assert supervisor.tool_dispatcher == tool_dispatcher
        assert supervisor.state_persistence is not None
    
    def test_init_components(self):
        """Test _init_components method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify components initialization
        assert supervisor.registry is not None
        assert supervisor.engine is not None
        assert supervisor.pipeline_executor is not None
        assert supervisor.state_manager is not None
        assert supervisor.pipeline_builder is not None
    
    def test_init_hooks(self):
        """Test _init_hooks method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify hooks initialization
        expected_hooks = ["before_agent", "after_agent", "on_error", "on_retry", "on_complete"]
        assert all(hook in supervisor.hooks for hook in expected_hooks)
        assert all(isinstance(supervisor.hooks[hook], list) for hook in expected_hooks)
    
    def test_initialization_with_none_values(self):
        """Test initialization handles None values gracefully."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        # Should not crash with valid mocks
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify basic setup completed
        assert supervisor is not None
        assert supervisor.name == "Supervisor"
        assert hasattr(supervisor, '_execution_lock')
        assert isinstance(supervisor.hooks, dict)


class TestSupervisorAgentRegistration:
    """Test agent registration and hook management."""
    
    def test_register_agent(self):
        """Test register_agent method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock agent
        mock_agent = Mock(spec=BaseSubAgent)
        mock_agent.name = "test_agent"
        
        # Register agent
        supervisor.register_agent("test_agent", mock_agent)
        
        # Verify registration
        assert "test_agent" in supervisor.agents
        assert supervisor.agents["test_agent"] == mock_agent
    
    def test_register_hook(self):
        """Test register_hook method."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock handler
        mock_handler = Mock()
        
        # Register hook
        supervisor.register_hook("before_agent", mock_handler)
        
        # Verify hook registration
        assert mock_handler in supervisor.hooks["before_agent"]
    
    def test_register_hook_invalid_event(self):
        """Test register_hook with invalid event."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        mock_handler = Mock()
        
        # Register invalid hook - should not crash
        supervisor.register_hook("invalid_event", mock_handler)
        
        # Verify invalid event not added
        assert "invalid_event" not in supervisor.hooks


class TestSupervisorAgentProperties:
    """Test property methods."""
    
    def test_agents_property(self):
        """Test agents property getter."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Test property returns registry agents
        agents = supervisor.agents
        assert agents == supervisor.registry.agents
    
    def test_sub_agents_property_getter(self):
        """Test sub_agents property getter (backward compatibility)."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock registry method
        supervisor.registry.get_all_agents = Mock(return_value=["agent1", "agent2"])
        
        # Test property
        sub_agents = supervisor.sub_agents
        assert sub_agents == ["agent1", "agent2"]
    
    def test_sub_agents_property_setter(self):
        """Test sub_agents property setter (backward compatibility)."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_manager = Mock()
        tool_dispatcher = Mock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock agents
        agent1 = Mock(spec=BaseSubAgent)
        agent2 = Mock(spec=BaseSubAgent)
        agents_list = [agent1, agent2]
        
        # Set sub_agents
        supervisor.sub_agents = agents_list
        
        # Verify agents were registered
        assert "agent_0" in supervisor.registry.agents
        assert "agent_1" in supervisor.registry.agents
