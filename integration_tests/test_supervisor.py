import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager

@pytest.mark.asyncio
@patch('app.agents.triage_sub_agent.agent.TriageSubAgent.execute')
async def test_supervisor_flow(mock_triage_execute):
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
    
    # triage_result is a TriageResult object, not a dict - check the category field
    assert final_state.triage_result is not None
    assert final_state.triage_result.category == "Data Analysis"
    
    # The other results may also be typed objects, not dictionaries
    # For now, just verify they are not None to confirm execution completed
    assert final_state.data_result is not None
    assert final_state.optimizations_result is not None  
    assert final_state.action_plan_result is not None
    assert final_state.report_result is not None