
import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.supervisor import Supervisor
from app.schemas import SubAgentLifecycle, WebSocketMessage

@pytest.fixture
def mock_llm_manager():
    llm_manager = MagicMock()
    
    async def mock_ask_llm(prompt: str, llm_config_name: str):
        if llm_config_name == 'triage':
            return json.dumps({"category": "Data Analysis"})
        if llm_config_name == 'data':
            return json.dumps({"data": "some data"})
        if llm_config_name == 'optimizations_core':
            return json.dumps({"optimizations": ["optimization 1"]})
        if llm_config_name == 'actions_to_meet_goals':
            return json.dumps({"action_plan": ["action 1"]})
        if llm_config_name == 'reporting':
            return json.dumps({"report": "This is the final report."})
        return "{}"

    llm_manager.ask_llm = AsyncMock(side_effect=mock_ask_llm)
    return llm_manager

@pytest.fixture
def mock_websocket_manager():
    websocket_manager = MagicMock()
    websocket_manager.send_to_client = AsyncMock()
    return websocket_manager

@pytest.fixture
def mock_tool_dispatcher():
    return MagicMock()

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.mark.asyncio
async def test_agent_flow(mock_db_session, mock_llm_manager, mock_websocket_manager, mock_tool_dispatcher):
    # Arrange
    supervisor = Supervisor(
        db_session=mock_db_session,
        llm_manager=mock_llm_manager,
        websocket_manager=mock_websocket_manager,
        tool_dispatcher=mock_tool_dispatcher,
    )
    input_data = {"query": "test query"}
    run_id = "test_run_id"

    # Act
    result = await supervisor.run(input_data, run_id, stream_updates=True)

    # Assert
    # Check the final result
    assert "report_result" in result
    assert result["report_result"]["report"] == "This is the final report."

    # Check WebSocket calls
    assert mock_websocket_manager.send_to_client.call_count > 0
    
    # Check agent_started message
    start_call = mock_websocket_manager.send_to_client.call_args_list[0]
    start_message: WebSocketMessage = start_call.args[1]
    assert start_message.type == "agent_started"

    # Check sub_agent_update messages
    update_calls = [call for call in mock_websocket_manager.send_to_client.call_args_list if call.args[1].type == "sub_agent_update"]
    
    agent_names = [
        "TriageSubAgent",
        "DataSubAgent",
        "OptimizationsCoreSubAgent",
        "ActionsToMeetGoalsSubAgent",
        "ReportingSubAgent",
    ]
    
    # 2 calls per agent (RUNNING, COMPLETED)
    assert len(update_calls) == len(agent_names) * 2

    for i, agent_name in enumerate(agent_names):
        running_call = update_calls[i*2]
        running_message: WebSocketMessage = running_call.args[1]
        assert running_message.payload.sub_agent_name == agent_name
        assert running_message.payload.state == SubAgentLifecycle.RUNNING

        completed_call = update_calls[i*2 + 1]
        completed_message: WebSocketMessage = completed_call.args[1]
        assert completed_message.payload.sub_agent_name == agent_name
        assert completed_message.payload.state == SubAgentLifecycle.COMPLETED

    # Check agent_completed message
    end_call = mock_websocket_manager.send_to_client.call_args_list[-1]
    end_message: WebSocketMessage = end_call.args[1]
    assert end_message.type == "agent_completed"
    assert end_message.payload.result == result
