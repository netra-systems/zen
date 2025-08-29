"""Integration tests for agent service singleton behavior.

Tests to ensure proper dependency injection and prevent service duplication.
See: SPEC/learnings/agent_registration_idempotency.xml
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.agent_service_factory import (
    _create_supervisor_agent,
    get_agent_service,
)


class TestAgentServiceSingleton:
    """Test suite for agent service singleton behavior."""

    @pytest.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        manager = MagicMock(spec=LLMManager)
        return manager

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock websocket manager."""
        return MagicMock()

    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher."""
        return MagicMock()

    def test_create_supervisor_agent_creates_new_instance(
        self, mock_db_session, mock_llm_manager
    ):
        """Test that _create_supervisor_agent creates new instances."""
        with patch('netra_backend.app.services.agent_service_factory.ToolDispatcher'):
            with patch('netra_backend.app.services.agent_service_factory.manager'):
                # Create two supervisors
                supervisor1 = _create_supervisor_agent(mock_db_session, mock_llm_manager)
                supervisor2 = _create_supervisor_agent(mock_db_session, mock_llm_manager)
                
                # They should be different instances
                assert supervisor1 is not supervisor2
                assert isinstance(supervisor1, SupervisorAgent)
                assert isinstance(supervisor2, SupervisorAgent)

    def test_get_agent_service_returns_new_service(
        self, mock_db_session, mock_llm_manager
    ):
        """Test that get_agent_service returns new service instances."""
        with patch('netra_backend.app.services.agent_service_factory.ToolDispatcher'):
            with patch('netra_backend.app.services.agent_service_factory.manager'):
                # Get two services
                service1 = get_agent_service(mock_db_session, mock_llm_manager)
                service2 = get_agent_service(mock_db_session, mock_llm_manager)
                
                # They should be different instances
                assert service1 is not service2
                assert isinstance(service1, AgentService)
                assert isinstance(service2, AgentService)

    @patch('netra_backend.app.agents.supervisor.agent_registry.logger')
    def test_supervisor_agent_registers_agents_once(
        self, mock_logger, mock_db_session, mock_llm_manager, 
        mock_websocket_manager, mock_tool_dispatcher
    ):
        """Test that SupervisorAgent only registers agents once."""
        # Create supervisor
        supervisor = SupervisorAgent(
            mock_db_session,
            mock_llm_manager,
            mock_websocket_manager,
            mock_tool_dispatcher
        )
        
        # Verify agents were registered
        assert len(supervisor.agent_registry.agents) == 7
        assert supervisor.agent_registry._agents_registered is True
        
        # Try to register again manually
        supervisor.agent_registry.register_default_agents()
        
        # Should log that agents are already registered
        mock_logger.debug.assert_called_with(
            "Agents already registered, skipping re-registration"
        )

    def test_agent_registry_shared_within_supervisor(
        self, mock_db_session, mock_llm_manager,
        mock_websocket_manager, mock_tool_dispatcher
    ):
        """Test that agent registry is properly initialized within supervisor."""
        supervisor = SupervisorAgent(
            mock_db_session,
            mock_llm_manager,
            mock_websocket_manager,
            mock_tool_dispatcher
        )
        
        # Verify registry is initialized
        assert supervisor.agent_registry is not None
        assert len(supervisor.agent_registry.agents) == 7
        
        # Verify components share the same registry
        assert supervisor.execution_engine.agent_registry is supervisor.agent_registry
        assert supervisor.workflow_orchestrator.agent_registry is supervisor.agent_registry

    @pytest.mark.asyncio
    async def test_concurrent_service_creation(
        self, mock_db_session, mock_llm_manager
    ):
        """Test that concurrent service creation doesn't cause issues."""
        with patch('netra_backend.app.services.agent_service_factory.ToolDispatcher'):
            with patch('netra_backend.app.services.agent_service_factory.manager'):
                async def create_service():
                    return get_agent_service(mock_db_session, mock_llm_manager)
                
                # Create multiple services concurrently
                services = await asyncio.gather(*[create_service() for _ in range(5)])
                
                # All should be valid services
                for service in services:
                    assert isinstance(service, AgentService)
                    assert service.supervisor is not None

    def test_dependency_injection_simulation(
        self, mock_db_session, mock_llm_manager
    ):
        """Simulate FastAPI dependency injection behavior."""
        # This simulates how FastAPI would cache dependencies within a request
        dependency_cache = {}
        
        def get_service_with_cache():
            if 'agent_service' not in dependency_cache:
                with patch('netra_backend.app.services.agent_service_factory.ToolDispatcher'):
                    with patch('netra_backend.app.services.agent_service_factory.manager'):
                        dependency_cache['agent_service'] = get_agent_service(
                            mock_db_session, mock_llm_manager
                        )
            return dependency_cache['agent_service']
        
        # Multiple calls within same "request" return same instance
        service1 = get_service_with_cache()
        service2 = get_service_with_cache()
        assert service1 is service2
        
        # New "request" gets new instance
        dependency_cache.clear()
        service3 = get_service_with_cache()
        assert service3 is not service1

    @patch('netra_backend.app.agents.supervisor.agent_registry.AgentRegistry.register')
    def test_agent_registration_count(
        self, mock_register, mock_db_session, mock_llm_manager,
        mock_websocket_manager, mock_tool_dispatcher
    ):
        """Test that each agent is registered exactly once."""
        # Create supervisor
        supervisor = SupervisorAgent(
            mock_db_session,
            mock_llm_manager,
            mock_websocket_manager,
            mock_tool_dispatcher
        )
        
        # Count registrations for each agent
        registration_counts = {}
        for call in mock_register.call_args_list:
            agent_name = call[0][0]  # First positional argument
            registration_counts[agent_name] = registration_counts.get(agent_name, 0) + 1
        
        # Each agent should be registered exactly once
        expected_agents = ['triage', 'data', 'optimization', 'actions', 
                          'reporting', 'synthetic_data', 'corpus_admin']
        for agent_name in expected_agents:
            assert registration_counts.get(agent_name, 0) == 1

    def test_websocket_manager_propagation(
        self, mock_db_session, mock_llm_manager,
        mock_websocket_manager, mock_tool_dispatcher
    ):
        """Test that websocket manager is properly propagated to all agents."""
        supervisor = SupervisorAgent(
            mock_db_session,
            mock_llm_manager,
            mock_websocket_manager,
            mock_tool_dispatcher
        )
        
        # Verify websocket manager is set on registry
        assert supervisor.agent_registry.websocket_manager == mock_websocket_manager
        
        # Verify all agents have websocket manager
        for agent in supervisor.agent_registry.agents.values():
            assert hasattr(agent, 'websocket_manager')
            assert agent.websocket_manager == mock_websocket_manager