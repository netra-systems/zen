
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.supervisor import Supervisor
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher

@pytest.mark.asyncio
async def test_supervisor_e2e():
    # Mocks
    db_session = AsyncMock()
    llm_manager = MagicMock(spec=LLMManager)
    websocket_manager = AsyncMock()
    tool_dispatcher = MagicMock(spec=ToolDispatcher)

    # Mock LLM responses for each sub-agent
    llm_manager.ask_llm.side_effect = [
        '{"category": "Data Analysis"}',  # Triage
        '{"data": "Some enriched data"}',   # Data
        '{"optimizations": ["Optimization 1"]}',  # Optimizations
        '{"action_plan": ["Action 1"]}',  # Actions
        '{"report": "This is the final report."}'  # Reporting
    ]

    # Instantiate the Supervisor
    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)

    # Input for the supervisor
    input_data = {"query": "Analyze my data"}
    run_id = "test_run_123"

    # Run the supervisor
    result = await supervisor.run(input_data, run_id, stream_updates=False)

    # Assertions
    assert "triage_result" in result
    assert result["triage_result"]["category"] == "Data Analysis"

    assert "data_result" in result
    assert result["data_result"]["data"] == "Some enriched data"

    assert "optimizations_result" in result
    assert result["optimizations_result"]["optimizations"] == ["Optimization 1"]

    assert "action_plan_result" in result
    assert result["action_plan_result"]["action_plan"] == ["Action 1"]

    assert "report_result" in result
    assert result["report_result"]["report"] == "This is the final report."

    # Verify that the LLM was called 5 times (once for each sub-agent)
    assert llm_manager.ask_llm.call_count == 5
