"""Unit tests for agent registry idempotency.

Tests to prevent regression of agent registration loop issue.
See: SPEC/learnings/agent_registration_idempotency.xml
"""

import asyncio
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.core.registry.universal_registry import AgentRegistry


class TestAgentRegistryIdempotency:
    """Test suite for agent registry idempotency."""

    @pytest.fixture
    def real_llm_manager(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create mock LLM manager."""
        return None  # TODO: Use real service instance

    @pytest.fixture
    def real_tool_dispatcher(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create mock tool dispatcher."""
        return None  # TODO: Use real service instance

    @pytest.fixture
    def agent_registry(self, mock_llm_manager, mock_tool_dispatcher):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create agent registry instance."""
        return AgentRegistry()

    def test_register_default_agents_idempotency(self, agent_registry):
        """Test that register_default_agents is idempotent."""
        # First registration
        agent_registry.register_default_agents()
        initial_agents = list(agent_registry.agents.keys())
        
        # Verify agents were registered
        assert len(initial_agents) == 8
        assert "triage" in initial_agents
        assert "data" in initial_agents
        assert "optimization" in initial_agents
        assert "actions" in initial_agents
        assert "reporting" in initial_agents
        assert "data_helper" in initial_agents
        assert "synthetic_data" in initial_agents
        assert "corpus_admin" in initial_agents
        
        # Second registration (should be skipped)
        agent_registry.register_default_agents()
        second_agents = list(agent_registry.agents.keys())
        
        # Verify no new agents were added
        assert initial_agents == second_agents
        assert len(agent_registry.agents) == 8

    def test_register_method_prevents_duplicates(self, agent_registry):
        """Test that register method prevents duplicate agent registration."""
        mock_agent = None  # TODO: Use real service instance
        
        # First registration
        agent_registry.register("test_agent", mock_agent)
        assert "test_agent" in agent_registry.agents
        assert agent_registry.agents["test_agent"] == mock_agent
        
        # Second registration with different instance (should be skipped)
        mock_agent_2 = None  # TODO: Use real service instance
        agent_registry.register("test_agent", mock_agent_2)
        
        # Verify original agent is still registered
        assert agent_registry.agents["test_agent"] == mock_agent
        assert agent_registry.agents["test_agent"] != mock_agent_2

    def test_agents_registered_flag(self, agent_registry):
        """Test that _agents_registered flag is properly set."""
        assert agent_registry._agents_registered is False
        
        agent_registry.register_default_agents()
        assert agent_registry._agents_registered is True
        
        # Flag should remain True after second call
        agent_registry.register_default_agents()
        assert agent_registry._agents_registered is True

    def test_concurrent_registration_safety(self, agent_registry):
        """Test thread safety of agent registration."""
        import threading
        
        registration_count = 0
        
        def register_agents():
            nonlocal registration_count
            agent_registry.register_default_agents()
            if len(agent_registry.agents) == 8:
                registration_count += 1
        
        # Create multiple threads trying to register simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=register_agents)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify only 8 agents registered despite multiple attempts
        assert len(agent_registry.agents) == 8
        assert agent_registry._agents_registered is True

    @pytest.mark.asyncio
    async def test_async_concurrent_registration(self, agent_registry):
        """Test async concurrent registration safety."""
        async def register_agents():
            agent_registry.register_default_agents()
        
        # Run multiple concurrent registrations
        await asyncio.gather(*[register_agents() for _ in range(10)])
        
        # Verify only 8 agents registered
        assert len(agent_registry.agents) == 8
        assert agent_registry._agents_registered is True

    def test_websocket_manager_assignment(self, agent_registry):
        """Test that websocket manager is properly assigned to agents."""
        mock_websocket_manager = None  # TODO: Use real service instance
        agent_registry.set_websocket_manager(mock_websocket_manager)
        
        agent_registry.register_default_agents()
        
        # Verify all agents have websocket manager
        for agent in agent_registry.agents.values():
            assert agent.websocket_manager == mock_websocket_manager

    def test_get_and_list_methods(self, agent_registry):
        """Test agent retrieval methods."""
        agent_registry.register_default_agents()
        
        # Test get method
        triage_agent = agent_registry.get("triage")
        assert triage_agent is not None
        assert triage_agent == agent_registry.agents["triage"]
        
        # Test list_agents method
        agent_names = agent_registry.list_agents()
        assert len(agent_names) == 8
        assert "triage" in agent_names
        
        # Test get_all_agents method
        all_agents = agent_registry.get_all_agents()
        assert len(all_agents) == 8

    def test_logging_behavior(self, mock_logger, agent_registry):
        """Test that appropriate logging occurs during registration."""
        # First registration - should log debug for each agent and info for summary
        agent_registry.register_default_agents()
        assert mock_logger.debug.call_count == 8  # One for each agent
        assert mock_logger.info.call_count == 1  # Summary message
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Second registration - should log debug
        agent_registry.register_default_agents()
        mock_logger.debug.assert_called_once_with(
            "Agents already registered, skipping re-registration"
        )
        assert mock_logger.info.call_count == 0

    def test_individual_agent_registration_after_default(self, agent_registry):
        """Test that individual agents can still be registered after defaults."""
        agent_registry.register_default_agents()
        
        # Should be able to register new agent
        mock_custom_agent = None  # TODO: Use real service instance
        agent_registry.register("custom_agent", mock_custom_agent)
        
        assert len(agent_registry.agents) == 9
        assert "custom_agent" in agent_registry.agents
        
        # But not duplicate of existing
        mock_duplicate = None  # TODO: Use real service instance
        agent_registry.register("triage", mock_duplicate)
        
        # Should still have 9 agents, not 10
        assert len(agent_registry.agents) == 9