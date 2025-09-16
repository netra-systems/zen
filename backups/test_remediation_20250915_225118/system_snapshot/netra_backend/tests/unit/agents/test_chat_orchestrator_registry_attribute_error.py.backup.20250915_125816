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
        self.mock_db_session = SSotMockFactory.create_database_session_mock()
        self.mock_llm_manager = SSotMockFactory.create_mock_llm_manager()
        self.mock_websocket_manager = SSotMockFactory.create_websocket_manager_mock()
        self.mock_tool_dispatcher = AsyncMock()
        self.mock_tool_dispatcher.execute = AsyncMock()
        self.mock_tool_dispatcher.get_available_tools = AsyncMock(return_value=[])
        self.mock_cache_manager = Mock()

    async def test_chat_orchestrator_initialization_succeeds_with_fixed_agent_factory(self):
        """Test that ChatOrchestrator initialization succeeds after the fix.

        After the fix, ChatOrchestrator should initialize successfully using agent_factory
        instead of the non-existent registry attribute.
        """
        orchestrator = ChatOrchestrator(db_session=self.mock_db_session, llm_manager=self.mock_llm_manager, websocket_manager=self.mock_websocket_manager, tool_dispatcher=self.mock_tool_dispatcher, cache_manager=self.mock_cache_manager, semantic_cache_enabled=True)
        assert hasattr(orchestrator, 'agent_registry'), 'ChatOrchestrator should have agent_registry after fix'
        assert hasattr(orchestrator, 'agent_factory'), 'ChatOrchestrator should have agent_factory from SupervisorAgent'
        assert orchestrator.agent_registry is orchestrator.agent_factory, 'agent_registry should reference agent_factory'

    def test_supervisor_agent_has_agent_factory_not_registry(self):
        """Test that SupervisorAgent provides agent_factory, not registry."""
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager, websocket_bridge=self.mock_websocket_manager)
        assert hasattr(supervisor, 'agent_factory'), 'SupervisorAgent should have agent_factory attribute'
        assert supervisor.agent_factory is not None, 'agent_factory should be initialized'
        assert not hasattr(supervisor, 'registry'), 'SupervisorAgent should NOT have registry attribute'

    def test_pipeline_executor_expects_agent_registry(self):
        """Test that PipelineExecutor requires agent_registry attribute from orchestrator."""
        mock_orchestrator_no_registry = Mock()
        mock_orchestrator_no_registry.agent_registry = None
        pipeline_executor = PipelineExecutor(mock_orchestrator_no_registry)
        assert hasattr(pipeline_executor, 'orchestrator'), 'PipelineExecutor should store orchestrator'
        mock_orchestrator_with_registry = Mock()
        mock_orchestrator_with_registry.agent_registry = Mock()
        pipeline_executor_with_registry = PipelineExecutor(mock_orchestrator_with_registry)
        assert pipeline_executor_with_registry.orchestrator.agent_registry is not None

    def test_chat_orchestrator_agent_factory_compatibility(self):
        """Test that agent_factory can be used as agent_registry for PipelineExecutor.

        This test verifies that the fix (agent_registry = agent_factory) would work.
        """

        class MockChatOrchestrator:

            def __init__(self):
                self.agent_factory = Mock()
                self.agent_registry = self.agent_factory
                self.execution_engine = Mock()
                self.trace_logger = Mock()
        fixed_orchestrator = MockChatOrchestrator()
        pipeline_executor = PipelineExecutor(fixed_orchestrator)
        assert pipeline_executor.orchestrator.agent_registry is fixed_orchestrator.agent_factory
        assert pipeline_executor.orchestrator.agent_registry is not None
        fixed_orchestrator.agent_registry.create_agent = Mock(return_value='mock_agent')
        result = fixed_orchestrator.agent_registry.create_agent('test_agent')
        assert result == 'mock_agent'

    async def test_supervisor_agent_factory_initialization(self):
        """Test that SupervisorAgent properly initializes agent_factory."""
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager, websocket_bridge=self.mock_websocket_manager)
        assert hasattr(supervisor.agent_factory, 'configure'), 'agent_factory should have configure method'
        supervisor.agent_factory.configure(websocket_bridge=self.mock_websocket_manager, llm_manager=self.mock_llm_manager)
        assert supervisor.agent_factory is not None

    async def test_chat_orchestrator_pipeline_executor_dependency_after_fix(self):
        """Test the specific dependency between ChatOrchestrator and PipelineExecutor after fix.

        This test verifies the scenario from line 99 in chat_orchestrator_main.py
        where PipelineExecutor is initialized with 'self' (the ChatOrchestrator instance).
        """
        orchestrator = ChatOrchestrator(db_session=self.mock_db_session, llm_manager=self.mock_llm_manager, websocket_manager=self.mock_websocket_manager, tool_dispatcher=self.mock_tool_dispatcher, cache_manager=self.mock_cache_manager, semantic_cache_enabled=True)
        assert hasattr(orchestrator, 'agent_registry'), 'ChatOrchestrator should have agent_registry for PipelineExecutor'
        assert hasattr(orchestrator, 'pipeline_executor'), 'ChatOrchestrator should have initialized PipelineExecutor'
        pipeline_executor = orchestrator.pipeline_executor
        assert pipeline_executor is not None, 'PipelineExecutor should be created'
        assert pipeline_executor.orchestrator is orchestrator, 'PipelineExecutor should reference orchestrator'
        assert pipeline_executor.agent_registry is orchestrator.agent_registry, "PipelineExecutor should use orchestrator's agent_registry"
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')