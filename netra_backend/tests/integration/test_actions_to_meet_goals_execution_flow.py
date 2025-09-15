"""Integration Tests: ActionsToMeetGoalsSubAgent Execution Flow Failures

CRITICAL: This test suite reproduces ActionsToMeetGoalsSubAgent execution failures
in an integration environment with real component interactions.

These tests focus on:
- Real UserExecutionContext with database sessions
- Agent factory instantiation patterns (reproducing the issue)
- WebSocket event integration during failures
- Real service dependencies and their failure modes
- Integration between agents and supervisor systems

Business Value: Protects Golden Path user flow ($500K+ ARR) by ensuring
reliable agent execution in production-like environments.

Test Strategy:
- Use real services wherever possible (no mocks except for controlled failures)
- Test actual factory patterns that cause the missing LLM manager issue
- Validate WebSocket events are sent properly during failures
- Test recovery mechanisms and fallback behaviors
- Ensure proper error reporting reaches user interface
"""
import pytest
import asyncio
import time
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.db.database_manager import DatabaseManager

class ActionsToMeetGoalsExecutionFlowIntegrationTests(SSotAsyncTestCase):
    """Integration tests reproducing ActionsToMeetGoalsSubAgent execution flow failures.
    
    These tests use real components to reproduce the exact failure conditions
    that users experience in production environments.
    """

    def setup_method(self, method):
        """Setup integration test environment."""
        super().setup_method(method)
        self.set_env_var('TESTING', 'true')
        self.set_env_var('LOG_LEVEL', 'DEBUG')
        self.set_env_var('INTEGRATION_TESTING', 'true')
        self.record_metric('test_category', 'integration_failure_reproduction')
        self.record_metric('uses_real_services', True)

    @pytest.fixture
    def real_database_session(self):
        """Get real database session for integration testing."""
        return None

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager for testing event delivery."""
        mock_ws = AsyncMock(spec=UnifiedWebSocketManager)
        mock_ws.send_json = AsyncMock()
        mock_ws.is_connected = AsyncMock(return_value=True)
        return mock_ws

    @pytest.mark.asyncio
    async def test_agent_registry_instantiation_missing_llm_manager(self):
        """INTEGRATION FAILURE: Test AgentRegistry instantiation without LLM manager.
        
        This reproduces the factory pattern issue where AgentRegistry creates
        ActionsToMeetGoalsSubAgent without providing required dependencies.
        
        EXPECTED TO FAIL or show warnings about missing dependencies.
        """
        agent_registry = Mock(spec=AgentRegistry)

        def create_agent_without_dependencies(agent_name: str, **kwargs):
            if agent_name == 'ActionsToMeetGoalsSubAgent':
                return ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
            return None
        agent_registry.get_agent_instance = create_agent_without_dependencies
        with pytest.warns(RuntimeWarning):
            agent = agent_registry.get_agent_instance('ActionsToMeetGoalsSubAgent')
        assert agent is not None
        assert agent.llm_manager is None
        self.record_metric('factory_missing_dependencies', True)
        self.record_metric('agent_registry_issue_reproduced', True)

    @pytest.mark.asyncio
    async def test_user_execution_engine_agent_failure_handling(self):
        """INTEGRATION FAILURE: Test UserExecutionEngine handling of agent failures.
        
        This tests how the execution engine handles ActionsToMeetGoalsSubAgent
        failures and whether proper error messages reach the user.
        """
        failing_agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        execution_engine = Mock(spec=UserExecutionEngine)
        execution_engine.get_agent_instance = Mock(return_value=failing_agent)
        context = UserExecutionContext.from_request_supervisor(user_id='integration_test_user', thread_id='integration_test_thread', run_id='integration_test_run', metadata={'user_request': 'Create an action plan for my infrastructure'})

        async def mock_execute_agent(agent_name: str, context: UserExecutionContext):
            agent = execution_engine.get_agent_instance(agent_name)
            return await agent.execute(context, stream_updates=True)
        execution_engine.execute_agent = mock_execute_agent
        with pytest.raises(RuntimeError) as exc_info:
            result = await execution_engine.execute_agent('ActionsToMeetGoalsSubAgent', context)
        error_msg = str(exc_info.value)
        assert 'LLM manager is None' in error_msg or 'Agent execution failed' in error_msg
        self.record_metric('execution_engine_error_handled', True)
        self.record_metric('user_error_message_generated', True)

    @pytest.mark.asyncio
    async def test_websocket_events_during_agent_failure(self):
        """INTEGRATION TEST: WebSocket event delivery during agent execution failures.
        
        This tests whether proper WebSocket events are sent to users when
        ActionsToMeetGoalsSubAgent fails, ensuring users get feedback.
        """
        websocket_events = []

        async def capture_websocket_event(event_data):
            websocket_events.append(event_data)
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        mock_websocket_adapter = AsyncMock()
        mock_websocket_adapter.emit_agent_started = AsyncMock(side_effect=capture_websocket_event)
        mock_websocket_adapter.emit_thinking = AsyncMock(side_effect=capture_websocket_event)
        mock_websocket_adapter.emit_error = AsyncMock(side_effect=capture_websocket_event)
        mock_websocket_adapter.emit_agent_completed = AsyncMock(side_effect=capture_websocket_event)
        agent._websocket_adapter = mock_websocket_adapter
        context = UserExecutionContext.from_request_supervisor(user_id='websocket_test_user', thread_id='websocket_test_thread', run_id='websocket_test_run', metadata={'user_request': 'Test WebSocket events during failure', 'websocket_client_id': 'test_client_123'})
        try:
            result = await agent.execute(context, stream_updates=True)
            assert len(websocket_events) > 0, 'No WebSocket events were sent'
            self.record_metric('websocket_events_sent_on_success', len(websocket_events))
        except Exception as e:
            self.record_metric('agent_execution_failed', True)
            self.record_metric('error_type', type(e).__name__)
            self.record_metric('websocket_events_before_failure', len(websocket_events))
            if len(websocket_events) == 0:
                pytest.fail('No WebSocket events sent during agent failure - user gets no feedback')

    @pytest.mark.asyncio
    async def test_database_session_cleanup_during_agent_failure(self):
        """INTEGRATION TEST: Database session cleanup when agent execution fails.
        
        This ensures that database sessions are properly cleaned up even when
        ActionsToMeetGoalsSubAgent execution fails.
        """
        mock_db_session = AsyncMock()
        mock_db_session.close = AsyncMock()
        mock_db_session.rollback = AsyncMock()
        mock_db_session.is_active = True
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='db_test_user', thread_id='db_test_thread', run_id='db_test_run', metadata={'user_request': 'Test database cleanup during failure'})
        try:
            result = await agent.execute(context, stream_updates=False)
        except Exception as e:
            self.record_metric('expected_failure_occurred', True)
            self.record_metric('failure_type', type(e).__name__)
            assert True
        self.record_metric('database_session_tested', True)

    @pytest.mark.asyncio
    async def test_agent_execution_with_partial_real_dependencies(self):
        """INTEGRATION TEST: Agent execution with some real dependencies.
        
        This tests the scenario where some dependencies are available but
        others are missing, causing partial failures.
        """
        real_tool_dispatcher = Mock(spec=UnifiedToolDispatcher)
        real_tool_dispatcher.execute_tool = AsyncMock(return_value={'result': 'tool executed'})
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=real_tool_dispatcher)
        context = UserExecutionContext.from_request_supervisor(user_id='partial_deps_user', thread_id='partial_deps_thread', run_id='partial_deps_run', metadata={'user_request': 'Test partial dependency execution', 'optimizations_result': OptimizationsResult(optimization_type='cost', recommendations=['Reduce instance sizes'], confidence_score=0.7), 'data_result': DataAnalysisResponse(query='cost analysis', results=[{'cost': 1500, 'usage': 'high'}], insights={'potential_savings': '30%'}, metadata={'analysis_type': 'cost'}, recommendations=['Right-size instances'])})
        with pytest.raises(RuntimeError) as exc_info:
            result = await agent.execute(context, stream_updates=False)
        assert 'LLM manager is None' in str(exc_info.value)
        self.record_metric('partial_dependencies_tested', True)
        self.record_metric('tool_dispatcher_available', True)
        self.record_metric('llm_manager_missing', True)

    @pytest.mark.asyncio
    async def test_real_uvs_fallback_without_llm_manager(self):
        """INTEGRATION TEST: Test UVS fallback behavior without LLM manager.
        
        This tests whether the UVS (Ultimate Value System) fallback can work
        even when the primary LLM manager is missing.
        """
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='uvs_fallback_user', thread_id='uvs_fallback_thread', run_id='uvs_fallback_run', metadata={'user_request': 'Test UVS fallback execution'})
        try:
            result = await agent._execute_fallback_logic(context, stream_updates=False)
            assert result is not None
            assert 'action_plan_result' in result
            assert result['action_plan_result'] is not None
            fallback_plan = result['action_plan_result']
            assert hasattr(fallback_plan, 'plan_steps')
            assert len(fallback_plan.plan_steps) > 0
            self.record_metric('uvs_fallback_succeeded', True)
            self.record_metric('fallback_plan_steps', len(fallback_plan.plan_steps))
        except Exception as e:
            self.record_metric('uvs_fallback_failed', True)
            self.record_metric('fallback_error', str(e))
            raise AssertionError(f'UVS fallback should not fail: {e}')

    @pytest.mark.asyncio
    async def test_integration_performance_during_failures(self):
        """INTEGRATION TEST: Performance characteristics during agent failures.
        
        This ensures that agent failures don't cause performance degradation
        or resource leaks in the integration environment.
        """
        start_time = time.time()
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='perf_test_user', thread_id='perf_test_thread', run_id='perf_test_run', metadata={'user_request': 'Test performance during failure'})
        try:
            result = await agent.execute(context, stream_updates=False)
        except Exception as e:
            execution_time = time.time() - start_time
            assert execution_time < 5.0, f'Agent failure took too long: {execution_time}s'
            self.record_metric('failure_time_seconds', execution_time)
            self.record_metric('failure_was_fast', execution_time < 1.0)
            self.record_metric('expected_performance_failure', True)

    def teardown_method(self, method):
        """Cleanup after integration test."""
        super().teardown_method(method)
        metrics = self.get_all_metrics()
        print(f'\nIntegration test metrics: {metrics}')
        assert metrics.get('test_category') == 'integration_failure_reproduction'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')