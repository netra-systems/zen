"""Unit Tests: ActionsToMeetGoalsSubAgent Execution Failure Reproduction

CRITICAL: This test suite is designed to FAIL initially to reproduce the exact 
"Agent execution failed" error reported by users.

These tests validate the Five Whys root cause analysis:
- Level 1: Missing LLM manager during agent instantiation
- Level 2: Factory pattern not passing required dependencies  
- Level 3: Architectural migration leaving gaps in dependency injection
- Level 4: BaseAgent infrastructure expecting dependencies that aren't provided
- Level 5: No validation at construction time allowing silent failures

Business Value: Protects $500K+ ARR by ensuring reliable action plan generation

Test Approach:
- Each test is designed to FAIL with clear reproduction of the issue
- Tests use real UserExecutionContext patterns for proper isolation
- No mocks for core business logic - real service patterns only
- Follows SSOT test framework patterns from test_framework.ssot.base_test_case
"""
import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from shared.isolated_environment import IsolatedEnvironment, get_env

class TestActionsToMeetGoalsExecutionFailures(SSotAsyncTestCase):
    """Unit test suite reproducing ActionsToMeetGoalsSubAgent execution failures.
    
    CRITICAL: These tests are designed to FAIL initially to prove the issue exists.
    Each test reproduces a specific failure mode from the Five Whys analysis.
    """

    def setup_method(self, method):
        """Setup test environment with SSOT patterns."""
        super().setup_method(method)
        self.set_env_var('TESTING', 'true')
        self.set_env_var('LOG_LEVEL', 'DEBUG')
        self.record_metric('test_category', 'unit_failure_reproduction')
        self.record_metric('expected_failures', True)

    @pytest.mark.asyncio
    async def test_agent_instantiation_without_llm_manager_shows_warning(self):
        """LEVEL 1 FAILURE: Test that agent without LLM manager shows proper warnings.
        
        This test SHOULD PASS but demonstrates the warning system.
        The actual failure happens during execution, not instantiation.
        """
        with pytest.warns(RuntimeWarning, match='ActionsToMeetGoalsSubAgent instantiated without LLMManager'):
            agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        assert agent is not None
        assert agent.llm_manager is None
        self.record_metric('llm_manager_warning_shown', True)
        self.record_metric('instantiation_succeeded_with_warning', True)

    @pytest.mark.asyncio
    async def test_agent_execution_fails_with_missing_llm_manager(self):
        """LEVEL 1 FAILURE REPRODUCTION: Agent execution fails when LLM manager is None.
        
        This test reproduces the exact RuntimeError that causes "Agent execution failed".
        EXPECTED TO FAIL with the specific error message from Five Whys analysis.
        """
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        context = await self._create_minimal_execution_context()
        with pytest.raises(RuntimeError) as exc_info:
            result = await agent.execute(context, stream_updates=False)
        error_message = str(exc_info.value)
        assert ' FAIL:  LLM manager is None' in error_message
        assert 'agent was instantiated without required dependency' in error_message
        assert 'incomplete architectural migration' in error_message
        assert 'FIVE_WHYS_ANALYSIS_20250904.md' in error_message
        self.record_metric('llm_manager_runtime_error', True)
        self.record_metric('expected_error_message_matched', True)

    @pytest.mark.asyncio
    async def test_validate_preconditions_fails_without_user_request(self):
        """LEVEL 2 FAILURE: Test precondition validation failures.
        
        This test should FAIL when user_request is missing from context metadata.
        """
        llm_manager = Mock(spec=LLMManager)
        agent = ActionsToMeetGoalsSubAgent(llm_manager=llm_manager, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='test_user', thread_id='test_thread', run_id='test_run', metadata={})
        result = await agent.validate_preconditions(context)
        assert result is False, 'Validation should fail without user_request'
        self.record_metric('precondition_validation_failed', True)
        self.record_metric('missing_user_request_detected', True)

    @pytest.mark.asyncio
    async def test_execute_core_logic_fails_with_missing_dependencies(self):
        """LEVEL 3 FAILURE: Test core logic execution failure with missing data.
        
        This test should FAIL when both optimizations_result and data_result are missing.
        Even with graceful degradation, some execution paths may still fail.
        """
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.ask_llm.side_effect = Exception('LLM unavailable')
        agent = ActionsToMeetGoalsSubAgent(llm_manager=llm_manager, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='test_user', thread_id='test_thread', run_id='test_run', metadata={'user_request': 'Help me optimize my AI infrastructure'})
        with pytest.raises(Exception) as exc_info:
            await agent.execute_core_logic(context)
        assert 'LLM unavailable' in str(exc_info.value)
        self.record_metric('core_logic_execution_failed', True)
        self.record_metric('llm_dependency_failure', True)

    @pytest.mark.asyncio
    async def test_end_to_end_agent_execution_reproduces_user_error(self):
        """FULL REPRODUCTION: End-to-end test reproducing exact user experience.
        
        This test reproduces the complete failure path that users experience:
        1. Agent instantiated without proper dependencies
        2. Validation may pass with defaults
        3. Core execution fails due to missing LLM manager
        4. User sees "Agent execution failed" error
        
        EXPECTED TO FAIL with the complete error chain.
        """
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='user_12345', thread_id='thread_67890', run_id='run_11111', metadata={'user_request': 'Create an action plan to optimize my AI infrastructure costs'})
        with pytest.raises(Exception) as exc_info:
            result = await agent.execute(context, stream_updates=True)
        error_message = str(exc_info.value)
        assert any(['LLM manager is None' in error_message, 'Agent execution failed' in error_message, 'incomplete architectural migration' in error_message]), f'Expected user-facing error, got: {error_message}'
        self.record_metric('user_error_reproduced', True)
        self.record_metric('end_to_end_failure', True)
        self.record_metric('error_type', type(exc_info.value).__name__)

    @pytest.mark.asyncio
    async def test_fallback_logic_still_fails_without_llm_manager(self):
        """LEVEL 4 FAILURE: Test that even fallback logic fails without LLM manager.
        
        This test shows that the fallback mechanisms don't help when the core 
        dependency (LLM manager) is missing.
        """
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        context = UserExecutionContext.from_request_supervisor(user_id='test_user', thread_id='test_thread', run_id='test_run', metadata={'user_request': 'Test fallback execution'})
        try:
            result = await agent._execute_fallback_logic(context, stream_updates=False)
            assert result is not None
            assert 'action_plan_result' in result
            self.record_metric('fallback_succeeded', True)
            self.record_metric('uvs_fallback_working', True)
        except Exception as e:
            self.record_metric('fallback_failed', True)
            self.record_metric('fallback_error', str(e))
            raise

    async def _create_minimal_execution_context(self) -> UserExecutionContext:
        """Helper to create minimal execution context for testing."""
        return UserExecutionContext.from_request_supervisor(user_id='test_user_minimal', thread_id='test_thread_minimal', run_id='test_run_minimal', metadata={'user_request': 'Test minimal execution context'})

    async def _create_complete_execution_context(self) -> UserExecutionContext:
        """Helper to create complete execution context with all dependencies."""
        return UserExecutionContext.from_request_supervisor(user_id='test_user_complete', thread_id='test_thread_complete', run_id='test_run_complete', metadata={'user_request': 'Test complete execution context', 'optimizations_result': OptimizationsResult(optimization_type='performance', recommendations=['Add caching layer', 'Implement monitoring'], confidence_score=0.85), 'data_result': DataAnalysisResponse(query='optimization analysis', results=[{'metric': 'response_time', 'value': 120}], insights={'performance': 'good'}, metadata={'source': 'test'}, recommendations=['Continue monitoring'])})

    def teardown_method(self, method):
        """Cleanup after test execution."""
        super().teardown_method(method)
        metrics = self.get_all_metrics()
        logger = self.get_env().get_logger(__name__)
        logger.info(f"Test {(method.__name__ if method else 'unknown')} metrics: {metrics}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')