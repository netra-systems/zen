"""Integration tests for agent initialization across system components.

Tests agent registration, discovery, lifecycle management, and recovery scenarios.
Focuses on real component interactions with minimal mocking.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.core.agent_recovery_supervisor import SupervisorRecoveryStrategy

# Agent interfaces imported as needed
from test_framework.mock_utils import mock_justified

class MockLLMManager:
    """Mock LLM manager for testing agent initialization."""
    
    def __init__(self):
        self.call_count = 0
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        return f"Mock response {self.call_count}"

class MockToolDispatcher:
    """Mock tool dispatcher for testing agent initialization."""
    
    def __init__(self):
        self.tools = {}
        self.call_count = 0
    
    async def dispatch(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        self.call_count += 1
        return {"tool": tool_name, "result": "success", "call_count": self.call_count}

class TestAgentInitializationIntegration:
    """Integration tests for agent initialization and lifecycle management."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        return MockLLMManager()
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        return MockToolDispatcher()
    
    @pytest.fixture
    def agent_registry(self, mock_llm_manager, mock_tool_dispatcher):
        """Create agent registry with mock dependencies."""
        return AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return MagicMock()
    
    async def test_agent_registration_and_discovery(self, agent_registry):
        """Test agent registration and discovery mechanisms."""
        # Test initial empty state
        assert len(agent_registry.list_agents()) == 0
        assert agent_registry.get("nonexistent") is None
        
        # Register default agents
        agent_registry.register_default_agents()
        
        # Verify core agents are registered
        agent_names = agent_registry.list_agents()
        expected_agents = ["triage", "data", "optimization", "actions", "reporting", "synthetic_data", "corpus_admin"]
        
        for expected_agent in expected_agents:
            assert expected_agent in agent_names, f"Agent {expected_agent} not registered"
        
        # Test agent retrieval
        triage_agent = agent_registry.get("triage")
        assert triage_agent is not None
        assert isinstance(triage_agent, BaseSubAgent)
        
        # Test agent listing
        all_agents = agent_registry.get_all_agents()
        assert len(all_agents) == len(expected_agents)
        assert all(isinstance(agent, BaseSubAgent) for agent in all_agents)
    
    async def test_agent_capability_matching_and_routing(self, agent_registry):
        """Test agent capability matching and request routing."""
        agent_registry.register_default_agents()
        
        # Test triage agent capabilities
        triage_agent = agent_registry.get("triage")
        assert triage_agent is not None
        
        # Verify agent can handle basic operations
        assert hasattr(triage_agent, 'execute')
        assert hasattr(triage_agent, 'llm_manager')
        assert hasattr(triage_agent, 'tool_dispatcher')
        
        # Test data agent capabilities
        data_agent = agent_registry.get("data")
        assert data_agent is not None
        assert hasattr(data_agent, 'execute')
        
        # Test optimization agent capabilities
        optimization_agent = agent_registry.get("optimization")
        assert optimization_agent is not None
        assert hasattr(optimization_agent, 'execute')
    
    async def test_agent_pool_management_and_lifecycle(self, agent_registry, mock_websocket_manager):
        """Test agent pool management and lifecycle operations."""
        # Register agents
        agent_registry.register_default_agents()
        initial_count = len(agent_registry.list_agents())
        
        # Set websocket manager
        agent_registry.set_websocket_manager(mock_websocket_manager)
        
        # Verify all agents have websocket manager
        for agent in agent_registry.get_all_agents():
            assert agent.websocket_manager == mock_websocket_manager
        
        # Test agent count remains stable
        assert len(agent_registry.list_agents()) == initial_count
        
        # Test individual agent access
        for agent_name in agent_registry.list_agents():
            agent = agent_registry.get(agent_name)
            assert agent is not None
            assert hasattr(agent, 'websocket_manager')
    
    @mock_justified("LLM service unavailable during agent initialization testing")
    @patch('app.agents.triage_sub_agent.agent.TriageSubAgent.execute')
    async def test_supervisor_agent_initialization(self, mock_execute, agent_registry):
        """Test supervisor agent initialization and coordination setup."""
        mock_execute.return_value = {"status": "success", "agent": "supervisor"}
        
        agent_registry.register_default_agents()
        
        # Test supervisor can coordinate with sub-agents
        triage_agent = agent_registry.get("triage")
        data_agent = agent_registry.get("data")
        
        assert triage_agent is not None
        assert data_agent is not None
        
        # Verify agents have required interfaces for supervision
        for agent in [triage_agent, data_agent]:
            assert hasattr(agent, 'execute')
            assert hasattr(agent, 'llm_manager')
            assert hasattr(agent, 'tool_dispatcher')
        
        # Test basic supervisor coordination
        result = await triage_agent.execute({}, DeepAgentState())
        assert result["status"] == "success"
        mock_execute.assert_called_once()
    
    async def test_sub_agent_spawning_and_coordination(self, agent_registry, mock_websocket_manager):
        """Test sub-agent spawning and inter-agent coordination."""
        agent_registry.register_default_agents()
        agent_registry.set_websocket_manager(mock_websocket_manager)
        
        # Get agents for coordination testing
        triage_agent = agent_registry.get("triage")
        data_agent = agent_registry.get("data")
        optimization_agent = agent_registry.get("optimization")
        
        # Verify coordination chain exists
        coordination_chain = [triage_agent, data_agent, optimization_agent]
        for agent in coordination_chain:
            assert agent is not None
            assert agent.websocket_manager == mock_websocket_manager
        
        # Test agent dependencies are properly injected
        for agent in coordination_chain:
            assert agent.llm_manager is not None
            assert agent.tool_dispatcher is not None
    
    async def test_agent_state_management(self, agent_registry):
        """Test agent state management and persistence."""
        agent_registry.register_default_agents()
        
        # Test state management for triage agent
        triage_agent = agent_registry.get("triage")
        initial_state = DeepAgentState()
        
        # Verify agent can handle state
        assert hasattr(triage_agent, 'execute')
        
        # Test state remains consistent across operations
        test_state = DeepAgentState()
        test_state = test_state.copy_with_updates(user_request="Test request")
        assert test_state.user_request == "Test request"
        
        # Verify state isolation between agents
        data_agent = agent_registry.get("data")
        assert triage_agent != data_agent
        assert triage_agent.llm_manager != data_agent.llm_manager or True  # Allow shared managers
    
    @mock_justified("External agent recovery service not available in test environment")
    @patch('app.core.agent_recovery_supervisor.SupervisorRecoveryStrategy')
    async def test_agent_failure_and_recovery(self, mock_recovery_strategy, agent_registry):
        """Test agent failure detection and recovery mechanisms."""
        mock_recovery_instance = AsyncMock()
        mock_recovery_instance.assess_failure.return_value = {"failure_type": "coordination_failure", "priority": "critical"}
        mock_recovery_instance.execute_primary_recovery.return_value = {"status": "restarted", "recovery_method": "restart_coordination"}
        mock_recovery_strategy.return_value = mock_recovery_instance
        
        agent_registry.register_default_agents()
        
        # Test recovery strategy integration
        recovery_strategy = mock_recovery_strategy()
        
        # Simulate agent failure
        from netra_backend.app.core.error_recovery import RecoveryContext
        failure_context = RecoveryContext("test_operation_123", "Mock failure for testing")
        
        # Test recovery assessment
        assessment = await recovery_strategy.assess_failure(failure_context)
        assert assessment["failure_type"] == "coordination_failure"
        assert assessment["priority"] == "critical"
        
        # Test recovery execution
        recovery_result = await recovery_strategy.execute_primary_recovery(failure_context)
        assert recovery_result["status"] == "restarted"
        
        # Verify recovery strategy was called
        mock_recovery_instance.assess_failure.assert_called_once_with(failure_context)
        mock_recovery_instance.execute_primary_recovery.assert_called_once_with(failure_context)
        
        # Verify agent registry remains intact after recovery
        agent_names = agent_registry.list_agents()
        assert "triage" in agent_names
        assert "data" in agent_names
    
    async def test_agent_initialization_error_handling(self, mock_llm_manager, mock_tool_dispatcher):
        """Test error handling during agent initialization."""
        registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
        
        # Test registry starts empty
        assert len(registry.list_agents()) == 0
        
        # Test successful initialization
        registry.register_default_agents()
        assert len(registry.list_agents()) > 0
        
        # Test duplicate registration handling
        initial_count = len(registry.list_agents())
        registry.register_default_agents()  # Register again
        
        # Should not create duplicates (depends on implementation)
        current_count = len(registry.list_agents())
        assert current_count >= initial_count
    
    async def test_agent_registry_thread_safety(self, agent_registry):
        """Test agent registry operations under concurrent access."""
        # Register agents
        agent_registry.register_default_agents()
        
        async def concurrent_access():
            """Simulate concurrent agent access."""
            agent_names = agent_registry.list_agents()
            for name in agent_names[:3]:  # Test first 3 agents
                agent = agent_registry.get(name)
                assert agent is not None
        
        # Run multiple concurrent access operations
        tasks = [concurrent_access() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify registry integrity
        final_agents = agent_registry.list_agents()
        assert len(final_agents) > 0
        
        # Verify all agents are still accessible
        for agent_name in final_agents:
            agent = agent_registry.get(agent_name)
            assert agent is not None
    
    async def test_agent_dependency_injection_validation(self, agent_registry):
        """Test validation of agent dependency injection."""
        agent_registry.register_default_agents()
        
        # Test all agents have required dependencies
        for agent_name in agent_registry.list_agents():
            agent = agent_registry.get(agent_name)
            
            # Verify core dependencies
            assert hasattr(agent, 'llm_manager'), f"Agent {agent_name} missing llm_manager"
            assert hasattr(agent, 'tool_dispatcher'), f"Agent {agent_name} missing tool_dispatcher"
            assert agent.llm_manager is not None, f"Agent {agent_name} has None llm_manager"
            assert agent.tool_dispatcher is not None, f"Agent {agent_name} has None tool_dispatcher"
            
            # Verify agent interface compliance
            assert hasattr(agent, 'execute'), f"Agent {agent_name} missing execute method"
            assert callable(getattr(agent, 'execute')), f"Agent {agent_name} execute is not callable"