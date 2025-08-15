import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager

@pytest.mark.asyncio
async def test_supervisor_flow():
    # Mock LLMManager
    llm_manager = MagicMock(spec=LLMManager)
    llm_manager.ask_llm = AsyncMock()

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

    async def side_effect(prompt, llm_config_name):
        return llm_responses[llm_config_name]

    llm_manager.ask_llm.side_effect = side_effect

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
    assert final_state.triage_result == {"category": "Data Analysis"}
    assert final_state.data_result == {"data": "Some data"}
    assert final_state.optimizations_result == {"optimizations": ["Optimization 1"]}
    assert final_state.action_plan_result == {"action_plan": ["Action 1"]}
    assert final_state.report_result == {"report": "This is the final report."}