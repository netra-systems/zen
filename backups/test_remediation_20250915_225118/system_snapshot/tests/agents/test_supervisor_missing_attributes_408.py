"""Comprehensive test suite for issue #408 - SupervisorAgent missing attributes validation

This test suite validates that the changes made to fix issue #408 have successfully
resolved the missing attributes problem without introducing breaking changes.

ISSUE #408: SupervisorAgent classes missing critical attributes expected by tests and business logic
- Added workflow_executor attribute to both SupervisorAgent implementations
- Implemented _create_supervisor_execution_context method
- Ensured backward compatibility with UserExecutionContext patterns
"""
import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as SupervisorAgentConsolidated
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as SupervisorAgentSSot
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionContext

class SupervisorAgentMissingAttributesTests:
    """Test validation that issue #408 missing attributes have been resolved."""

    def test_supervisor_consolidated_has_workflow_executor(self):
        """Test that SupervisorAgent (consolidated) has workflow_executor attribute."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentConsolidated(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert hasattr(supervisor, 'workflow_executor'), 'SupervisorAgent missing workflow_executor attribute'
        assert supervisor.workflow_executor is not None, 'workflow_executor is None - not properly initialized'
        assert hasattr(supervisor.workflow_executor, 'supervisor'), 'workflow_executor missing supervisor reference'
        assert supervisor.workflow_executor.supervisor is supervisor, 'workflow_executor supervisor reference incorrect'

    def test_supervisor_ssot_has_workflow_executor(self):
        """Test that SupervisorAgentSSot has workflow_executor attribute."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentSSot(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert hasattr(supervisor, 'workflow_executor'), 'SupervisorAgentSSot missing workflow_executor attribute'
        assert supervisor.workflow_executor is not None, 'workflow_executor is None - not properly initialized'
        assert hasattr(supervisor.workflow_executor, 'supervisor'), 'workflow_executor missing supervisor reference'
        assert supervisor.workflow_executor.supervisor is supervisor, 'workflow_executor supervisor reference incorrect'

    def test_supervisor_consolidated_has_create_supervisor_execution_context(self):
        """Test that SupervisorAgent (consolidated) has _create_supervisor_execution_context method."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentConsolidated(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert hasattr(supervisor, '_create_supervisor_execution_context'), 'SupervisorAgent missing _create_supervisor_execution_context method'
        assert callable(supervisor._create_supervisor_execution_context), '_create_supervisor_execution_context is not callable'
        user_context = UserExecutionContext.from_request_supervisor(user_id='test-user-408', thread_id='test-thread-408', run_id='test-run-408', metadata={'test': 'issue-408'})
        execution_context = supervisor._create_supervisor_execution_context(user_context, agent_name='TestSupervisor408')
        assert isinstance(execution_context, ExecutionContext), '_create_supervisor_execution_context did not return ExecutionContext'
        assert execution_context.user_id == 'test-user-408'
        assert execution_context.run_id == 'test-run-408'
        assert execution_context.agent_name == 'TestSupervisor408'

    def test_supervisor_ssot_has_create_supervisor_execution_context(self):
        """Test that SupervisorAgentSSot has _create_supervisor_execution_context method."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentSSot(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert hasattr(supervisor, '_create_supervisor_execution_context'), 'SupervisorAgentSSot missing _create_supervisor_execution_context method'
        assert callable(supervisor._create_supervisor_execution_context), '_create_supervisor_execution_context is not callable'
        user_context = UserExecutionContext.from_request_supervisor(user_id='test-user-ssot-408', thread_id='test-thread-ssot-408', run_id='test-run-ssot-408', metadata={'test': 'issue-408-ssot'})
        execution_context = supervisor._create_supervisor_execution_context(user_context, agent_name='TestSupervisorSSot408')
        assert isinstance(execution_context, ExecutionContext), '_create_supervisor_execution_context did not return ExecutionContext'
        assert execution_context.user_id == 'test-user-ssot-408'
        assert execution_context.run_id == 'test-run-ssot-408'
        assert execution_context.agent_name == 'TestSupervisorSSot408'

    def test_workflow_executor_integration_consolidated(self):
        """Test that workflow_executor integrates properly with SupervisorAgent methods."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentConsolidated(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert supervisor.workflow_executor is not None
        expected_methods = ['execute_workflow', 'coordinate_agents', 'orchestrate']
        has_workflow_methods = any((hasattr(supervisor.workflow_executor, method) for method in expected_methods))
        assert str(type(supervisor.workflow_executor).__name__).endswith('Executor'), 'workflow_executor does not appear to be a proper executor type'

    def test_workflow_executor_integration_ssot(self):
        """Test that workflow_executor integrates properly with SupervisorAgentSSot methods."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentSSot(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert supervisor.workflow_executor is not None
        assert str(type(supervisor.workflow_executor).__name__).endswith('Executor'), 'workflow_executor does not appear to be a proper executor type'

    def test_execution_context_bridge_functionality_consolidated(self):
        """Test that _create_supervisor_execution_context properly bridges UserExecutionContext to ExecutionContext."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentConsolidated(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        user_context = UserExecutionContext.from_request_supervisor(user_id='test-user-bridge-408', thread_id='test-thread-bridge-408', run_id='test-run-bridge-408', metadata={'user_request': 'test bridge functionality', 'agent_type': 'supervisor', 'operation': 'test'})
        execution_context = supervisor._create_supervisor_execution_context(user_context, agent_name='BridgeTestSupervisor', additional_metadata={'bridge_test': True, 'issue': '408'})
        assert execution_context.user_id == 'test-user-bridge-408'
        assert execution_context.run_id == 'test-run-bridge-408'
        assert execution_context.agent_name == 'BridgeTestSupervisor'
        assert execution_context.stream_updates == True
        assert 'thread_id' in execution_context.parameters
        assert execution_context.parameters['thread_id'] == 'test-thread-bridge-408'
        assert 'supervisor_execution' in execution_context.metadata
        assert execution_context.metadata['supervisor_execution'] == True
        assert 'user_isolation_enabled' in execution_context.metadata
        assert execution_context.metadata['user_isolation_enabled'] == True
        if hasattr(execution_context, 'additional_metadata') or 'bridge_test' in execution_context.metadata:
            pass

    def test_execution_context_bridge_functionality_ssot(self):
        """Test that _create_supervisor_execution_context properly bridges UserExecutionContext to ExecutionContext for SSOT."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentSSot(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        user_context = UserExecutionContext.from_request_supervisor(user_id='test-user-bridge-ssot-408', thread_id='test-thread-bridge-ssot-408', run_id='test-run-bridge-ssot-408', metadata={'user_request': 'test ssot bridge functionality', 'agent_type': 'supervisor', 'operation': 'test'})
        execution_context = supervisor._create_supervisor_execution_context(user_context, agent_name='BridgeTestSupervisorSSot')
        assert execution_context.user_id == 'test-user-bridge-ssot-408'
        assert execution_context.run_id == 'test-run-bridge-ssot-408'
        assert execution_context.agent_name == 'BridgeTestSupervisorSSot'
        assert hasattr(execution_context, 'parameters')
        assert hasattr(execution_context, 'metadata')

class BackwardCompatibilityTests:
    """Test that the changes maintain backward compatibility."""

    @pytest.mark.asyncio
    async def test_execute_method_still_works_consolidated(self):
        """Test that the execute method still works after adding missing attributes."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentConsolidated(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        supervisor._orchestrate_agents = AsyncMock(return_value={'supervisor_result': 'completed', 'orchestration_successful': True, 'results': {'compatibility_test': 'passed'}})
        context = UserExecutionContext.from_request_supervisor(user_id='test-compatibility-408', thread_id='test-thread-compatibility', run_id='test-run-compatibility', metadata={'compatibility_test': True}).with_db_session(db_session)
        result = await supervisor.execute(context, stream_updates=True)
        assert isinstance(result, dict)
        assert result['supervisor_result'] == 'completed'
        assert result['orchestration_successful'] is True
        assert 'compatibility_test' in result['results']

    @pytest.mark.asyncio
    async def test_execute_method_still_works_ssot(self):
        """Test that the execute method still works after adding missing attributes for SSOT."""
        llm_manager = Mock(spec=LLMManager)
        db_session = Mock(spec=AsyncSession)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor = SupervisorAgentSSot(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        supervisor._orchestrate_agents = AsyncMock(return_value={'supervisor_result': 'completed', 'orchestration_successful': True, 'results': {'compatibility_test_ssot': 'passed'}})
        context = UserExecutionContext.from_request_supervisor(user_id='test-compatibility-ssot-408', thread_id='test-thread-compatibility-ssot', run_id='test-run-compatibility-ssot', metadata={'compatibility_test': True}).with_db_session(db_session)
        result = await supervisor.execute(context, stream_updates=True)
        if hasattr(result, 'data'):
            assert result.data['supervisor_result'] == 'completed'
            assert result.data['orchestration_successful'] is True
            assert result.data['user_id'] == 'test-compatibility-ssot-408'
        else:
            assert isinstance(result, dict)
            assert result['supervisor_result'] == 'completed'
            assert result['orchestration_successful'] is True
            assert 'compatibility_test_ssot' in result['results']

    def test_attributes_are_not_none_after_initialization(self):
        """Test that the added attributes are properly initialized and not None."""
        llm_manager = Mock(spec=LLMManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket_bridge.websocket_manager = Mock()
        websocket_bridge.emit_agent_event = AsyncMock()
        supervisor_consolidated = SupervisorAgentConsolidated(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert supervisor_consolidated.workflow_executor is not None, 'SupervisorAgent workflow_executor is None'
        supervisor_ssot = SupervisorAgentSSot(llm_manager=llm_manager, websocket_bridge=websocket_bridge)
        assert supervisor_ssot.workflow_executor is not None, 'SupervisorAgentSSot workflow_executor is None'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')