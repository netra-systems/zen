import asyncio
from unittest.mock import Mock, patch, MagicMock

"""Core tests for SupervisorAgent - initialization, registration, and properties."""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead


import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

class TestSupervisorAgentInitialization:
    """Test initialization and setup methods."""
    
    def test_init_base(self):
        """Test _init_base method."""
        # Mock LLM manager
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        
        # Create supervisor instance
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify base initialization
        assert supervisor.name == "Supervisor"
        assert supervisor.description == "The supervisor agent that orchestrates sub-agents"
        assert supervisor.llm_manager == llm_manager
    
    def test_init_services(self):
        """Test _init_services method."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify services initialization
        assert supervisor.db_session == db_session
        assert supervisor.websocket_manager == websocket_manager
        assert supervisor.tool_dispatcher == tool_dispatcher
        assert supervisor.state_persistence is not None
    
    def test_init_components(self):
        """Test _init_components method."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify components initialization
        assert supervisor.registry is not None
        assert supervisor.engine is not None
        assert supervisor.pipeline_executor is not None
        assert supervisor.state_manager is not None
        assert supervisor.pipeline_builder is not None
    
    def test_init_hooks(self):
        """Test _init_hooks method."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Verify hooks initialization
        expected_hooks = ["before_agent", "after_agent", "on_error", "on_retry", "on_complete"]
        assert all(hook in supervisor.hooks for hook in expected_hooks)
        assert all(isinstance(supervisor.hooks[hook], list) for hook in expected_hooks)
    
    def test_initialization_with_none_values(self):
        """Test initialization handles None values gracefully."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
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
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock agent
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent = Mock(spec = BaseAgent)
        mock_agent.name = "test_agent"
        
        # Register agent
        supervisor.register_agent("test_agent", mock_agent)
        
        # Verify registration
        assert "test_agent" in supervisor.agents
        assert supervisor.agents["test_agent"] == mock_agent
    
    def test_register_hook(self):
        """Test register_hook method."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock handler
        # Mock: Generic component isolation for controlled unit testing
        mock_handler = mock_handler_instance  # Initialize appropriate service
        
        # Register hook
        supervisor.register_hook("before_agent", mock_handler)
        
        # Verify hook registration
        assert mock_handler in supervisor.hooks["before_agent"]
    
    def test_register_hook_invalid_event(self):
        """Test register_hook with invalid event."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock: Generic component isolation for controlled unit testing
        mock_handler = mock_handler_instance  # Initialize appropriate service
        
        # Register invalid hook - should not crash
        supervisor.register_hook("invalid_event", mock_handler)
        
        # Verify invalid event not added
        assert "invalid_event" not in supervisor.hooks

class TestSupervisorAgentProperties:
    """Test property methods."""
    
    def test_agents_property(self):
        """Test agents property getter."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Test property returns registry agents
        agents = supervisor.agents
        assert agents == supervisor.registry.agents
    
    def test_sub_agents_property_getter(self):
        """Test sub_agents property getter (backward compatibility)."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Mock registry method
        # Mock: Agent service isolation for testing without LLM agent execution
        supervisor.registry.get_all_agents = Mock(return_value = ["agent1", "agent2"])
        
        # Test property
        sub_agents = supervisor.sub_agents
        assert sub_agents == ["agent1", "agent2"]
    
    def test_sub_agents_property_setter(self):
        """Test sub_agents property setter (backward compatibility)."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec = LLMManager)
        # Mock: Database session isolation for transaction testing without real database dependency
        db_session = Mock(spec = AsyncSession)
        # Mock: WebSocket connection isolation for testing without network overhead
        websocket_manager = UnifiedWebSocketManager()
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        tool_dispatcher = Mock(spec = ToolDispatcher)
        
        supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Create mock agents
        # Mock: Agent service isolation for testing without LLM agent execution
        agent1 = Mock(spec = BaseAgent)
        # Mock: Agent service isolation for testing without LLM agent execution
        agent2 = Mock(spec = BaseAgent)
        agents_list = [agent1, agent2]
        
        # Set sub_agents
        supervisor.sub_agents = agents_list
        
        # Verify agents were registered
        assert "agent_0" in supervisor.registry.agents
        assert "agent_1" in supervisor.registry.agents
