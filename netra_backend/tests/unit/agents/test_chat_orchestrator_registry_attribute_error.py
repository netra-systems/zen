"""
Unit Tests for Issue #956: ChatOrchestrator Registry AttributeError

Tests that reproduce the AttributeError where ChatOrchestrator expects self.registry
but SupervisorAgent provides self.agent_factory.

Date Created: 2025-09-14
Issue: #956 ChatOrchestrator Registry AttributeError - SupervisorAgent object has no attribute 'registry'
"""

import pytest
from unittest.mock import Mock, AsyncMock
import asyncio

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.chat_orchestrator.pipeline_executor import PipelineExecutor


class TestChatOrchestratorRegistryAttributeError(SSotAsyncTestCase):
    """Test cases for Issue #956: ChatOrchestrator Registry AttributeError."""

    def setup_method(self, method):
        """Set up test fixtures with SSOT mock factory."""
        super().setup_method(method)

        # Create SSOT-compliant mocks for ChatOrchestrator dependencies
        self.mock_db_session = SSotMockFactory.create_database_session_mock()
        self.mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
        self.mock_websocket_manager = SSotMockFactory.create_websocket_manager_mock()

        # Create simple tool dispatcher mock (not available in SSOT factory yet)
        self.mock_tool_dispatcher = AsyncMock()
        self.mock_tool_dispatcher.execute = AsyncMock()
        self.mock_tool_dispatcher.get_available_tools = AsyncMock(return_value=[])

        self.mock_cache_manager = Mock()

    async def test_chat_orchestrator_initialization_fails_with_registry_access(self):
        """Test that ChatOrchestrator initialization fails due to missing registry attribute.

        This test should FAIL before the fix is applied, demonstrating the AttributeError
        at line 97 in chat_orchestrator_main.py when accessing self.registry.
        """
        with pytest.raises(AttributeError) as exc_info:
            # Attempt to initialize ChatOrchestrator - should fail at line 97
            orchestrator = ChatOrchestrator(
                db_session=self.mock_db_session,
                llm_manager=self.mock_llm_manager,
                websocket_manager=self.mock_websocket_manager,
                tool_dispatcher=self.mock_tool_dispatcher,
                cache_manager=self.mock_cache_manager,
                semantic_cache_enabled=True
            )

        # Verify the specific AttributeError from registry access during ChatOrchestrator initialization
        error_msg = str(exc_info.value)
        assert "object has no attribute 'registry'" in error_msg
        assert "registry" in error_msg

    def test_supervisor_agent_has_agent_factory_not_registry(self):
        """Test that SupervisorAgent provides agent_factory, not registry."""
        # Initialize SupervisorAgent with minimal dependencies
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_manager
        )

        # Verify SupervisorAgent has agent_factory
        assert hasattr(supervisor, 'agent_factory'), "SupervisorAgent should have agent_factory attribute"
        assert supervisor.agent_factory is not None, "agent_factory should be initialized"

        # Verify SupervisorAgent does NOT have registry
        assert not hasattr(supervisor, 'registry'), "SupervisorAgent should NOT have registry attribute"

    def test_pipeline_executor_expects_agent_registry(self):
        """Test that PipelineExecutor requires agent_registry attribute from orchestrator."""
        # Create a mock orchestrator without agent_registry
        mock_orchestrator_no_registry = Mock()
        mock_orchestrator_no_registry.agent_registry = None

        # Initialize PipelineExecutor with orchestrator lacking agent_registry
        pipeline_executor = PipelineExecutor(mock_orchestrator_no_registry)

        # The PipelineExecutor should be created but will fail when trying to access agent_registry
        assert hasattr(pipeline_executor, 'orchestrator'), "PipelineExecutor should store orchestrator"

        # Verify that accessing agent_registry through orchestrator works (when it exists)
        mock_orchestrator_with_registry = Mock()
        mock_orchestrator_with_registry.agent_registry = Mock()

        pipeline_executor_with_registry = PipelineExecutor(mock_orchestrator_with_registry)
        assert pipeline_executor_with_registry.orchestrator.agent_registry is not None

    def test_chat_orchestrator_agent_factory_compatibility(self):
        """Test that agent_factory can be used as agent_registry for PipelineExecutor.

        This test verifies that the fix (agent_registry = agent_factory) would work.
        """
        # Create a ChatOrchestrator-like object with the proposed fix
        class MockChatOrchestrator:
            def __init__(self):
                # Simulate SupervisorAgent's agent_factory
                self.agent_factory = Mock()
                # Apply the proposed fix: use agent_factory as agent_registry
                self.agent_registry = self.agent_factory
                # Add attributes that PipelineExecutor expects
                self.execution_engine = Mock()
                self.trace_logger = Mock()

        # Create mock orchestrator with the fix applied
        fixed_orchestrator = MockChatOrchestrator()

        # Verify that PipelineExecutor can use agent_factory through agent_registry alias
        pipeline_executor = PipelineExecutor(fixed_orchestrator)

        # Both should reference the same object
        assert pipeline_executor.orchestrator.agent_registry is fixed_orchestrator.agent_factory
        assert pipeline_executor.orchestrator.agent_registry is not None

        # Verify that agent_registry can be used for agent operations
        fixed_orchestrator.agent_registry.create_agent = Mock(return_value="mock_agent")
        result = fixed_orchestrator.agent_registry.create_agent("test_agent")
        assert result == "mock_agent"

    async def test_supervisor_agent_factory_initialization(self):
        """Test that SupervisorAgent properly initializes agent_factory."""
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_manager
        )

        # Verify agent_factory is properly initialized with expected methods
        assert hasattr(supervisor.agent_factory, 'configure'), "agent_factory should have configure method"

        # Test that agent_factory can be configured (as done in SupervisorAgent._create_user_execution_engine)
        supervisor.agent_factory.configure(
            websocket_bridge=self.mock_websocket_manager,
            llm_manager=self.mock_llm_manager
        )

        # Verify configuration doesn't raise exceptions
        assert supervisor.agent_factory is not None

    async def test_chat_orchestrator_pipeline_executor_dependency(self):
        """Test the specific dependency between ChatOrchestrator and PipelineExecutor.

        This test reproduces the exact scenario from line 99 in chat_orchestrator_main.py
        where PipelineExecutor is initialized with 'self' (the ChatOrchestrator instance).
        """
        # Mock the dependencies that would be initialized before line 97
        with pytest.raises(AttributeError):
            # This should fail when _init_helper_modules is called
            orchestrator = ChatOrchestrator(
                db_session=self.mock_db_session,
                llm_manager=self.mock_llm_manager,
                websocket_manager=self.mock_websocket_manager,
                tool_dispatcher=self.mock_tool_dispatcher,
                cache_manager=self.mock_cache_manager,
                semantic_cache_enabled=True
            )

            # If initialization somehow succeeded, this would be the next failure point
            # where PipelineExecutor tries to access orchestrator.agent_registry
            pipeline_executor = PipelineExecutor(orchestrator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])