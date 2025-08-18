import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager

@pytest.mark.asyncio
@patch('app.agents.triage_sub_agent.agent.TriageSubAgent.execute')
@patch('app.agents.data_sub_agent.agent.DataSubAgent.execute') 
@patch('app.agents.optimizations_core_sub_agent.OptimizationsCoreSubAgent.execute')
@patch('app.agents.actions_to_meet_goals_sub_agent.ActionsToMeetGoalsSubAgent.execute')
@patch('app.agents.reporting_sub_agent.ReportingSubAgent.execute')
async def test_supervisor_flow(mock_reporting_execute, mock_actions_execute, 
                              mock_optimizations_execute, mock_data_execute, mock_triage_execute):
    # Mock LLMManager
    llm_manager = MagicMock(spec=LLMManager)
    llm_manager.ask_llm = AsyncMock()
    llm_manager.ask_structured_llm = AsyncMock()

    # Mock WebSocketManager
    websocket_manager = MagicMock()
    websocket_manager.send_to_client = AsyncMock()

    # Mock ToolDispatcher
    tool_dispatcher = MagicMock()

    # Mock db_session
    db_session = MagicMock()

    # Predefined LLM responses
    llm_responses = {
        'triage': '{"category": "Data Analysis"}',
        'data': '{"data": "Some data"}',
        'optimizations_core': '{"optimizations": ["Optimization 1"]}',
        'actions_to_meet_goals': '{"action_plan": ["Action 1"]}',
        'reporting': '{"report": "This is the final report."}'
    }

    async def regular_side_effect(prompt, llm_config_name):
        return llm_responses[llm_config_name]

    async def structured_side_effect(prompt, llm_config_name, schema, use_cache=False):
        # For structured calls, create the actual TriageResult object for triage calls
        if llm_config_name == 'triage':
            from app.agents.triage_sub_agent.models import TriageResult
            return TriageResult(category="Data Analysis", confidence_score=0.9)
        # For other agents, return the regular JSON response
        return llm_responses[llm_config_name]

    llm_manager.ask_llm.side_effect = regular_side_effect
    llm_manager.ask_structured_llm.side_effect = structured_side_effect
    
    # Mock the triage agent execute method to set the correct triage result
    async def mock_triage_execute_impl(state, run_id, stream_updates):
        from app.agents.triage_sub_agent.models import TriageResult
        state.triage_result = TriageResult(category="Data Analysis", confidence_score=0.9)
        state.step_count += 1
    
    mock_triage_execute.side_effect = mock_triage_execute_impl
    
    # Mock the data agent execute method
    async def mock_data_execute_impl(state, run_id, stream_updates):
        from app.agents.state import DataResult
        state.data_result = DataResult(data="Some data", confidence_score=0.8)
        state.step_count += 1
    
    mock_data_execute.side_effect = mock_data_execute_impl
    
    # Mock the optimizations agent execute method  
    async def mock_optimizations_execute_impl(state, run_id, stream_updates):
        from app.agents.state import OptimizationsResult
        state.optimizations_result = OptimizationsResult(
            optimization_type="performance",
            recommendations=["Optimization 1", "Optimization 2"],
            confidence_score=0.9
        )
        state.step_count += 1
    
    mock_optimizations_execute.side_effect = mock_optimizations_execute_impl
    
    # Mock the actions agent execute method
    async def mock_actions_execute_impl(state, run_id, stream_updates):
        from app.agents.state import ActionPlanResult
        state.action_plan_result = ActionPlanResult(
            action_plan=["Action 1", "Action 2"],
            confidence_score=0.85
        )
        state.step_count += 1
    
    mock_actions_execute.side_effect = mock_actions_execute_impl
    
    # Mock the reporting agent execute method
    async def mock_reporting_execute_impl(state, run_id, stream_updates):
        from app.agents.state import ReportResult
        state.report_result = ReportResult(
            report="This is the final report.",
            confidence_score=0.9
        )
        state.step_count += 1
    
    mock_reporting_execute.side_effect = mock_reporting_execute_impl

    # Create Supervisor
    supervisor = Supervisor(
        db_session=db_session,
        llm_manager=llm_manager,
        websocket_manager=websocket_manager,
        tool_dispatcher=tool_dispatcher
    )

    # Run the supervisor
    user_request = "Analyze my data and suggest optimizations."
    run_id = "test_run"
    thread_id = "test_thread"
    user_id = "test_user"
    initial_state = DeepAgentState(user_request=user_request)
    final_state = await supervisor.run(user_request, thread_id, user_id, run_id)

    # Assertions
    assert final_state.user_request == user_request
    
    # Verify triage_result is properly set with typed object
    assert final_state.triage_result is not None
    assert final_state.triage_result.category == "Data Analysis"
    assert final_state.triage_result.confidence_score == 0.9
    
    # Verify data_result is properly set with typed object
    assert final_state.data_result is not None
    assert final_state.data_result.data == "Some data"
    assert final_state.data_result.confidence_score == 0.8
    
    # Verify optimizations_result is properly set with typed object (this was the failing assertion)
    assert final_state.optimizations_result is not None  
    assert final_state.optimizations_result.optimization_type == "performance"
    assert final_state.optimizations_result.recommendations == ["Optimization 1", "Optimization 2"]
    assert final_state.optimizations_result.confidence_score == 0.9
    
    # Verify action_plan_result is properly set with typed object
    assert final_state.action_plan_result is not None
    assert final_state.action_plan_result.action_plan == ["Action 1", "Action 2"]
    assert final_state.action_plan_result.confidence_score == 0.85
    
    # Verify report_result is properly set with typed object
    assert final_state.report_result is not None
    assert final_state.report_result.report == "This is the final report."
    assert final_state.report_result.confidence_score == 0.9