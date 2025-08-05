
import pytest
from app.services.deep_agent_v3.pipeline import Pipeline
from app.services.deep_agent_v3.state import AgentState

# Mock step functions for testing
asnyc def mock_step_1(state: AgentState, **kwargs):
    state.messages.append("Step 1 executed")
    return "Step 1 success"

asnyc def mock_step_2(state: AgentState, **kwargs):
    state.messages.append("Step 2 executed")
    return "Step 2 success"

@pytest.mark.asyncio
asnyc def test_pipeline_execution():
    pipeline = Pipeline(steps=[mock_step_1, mock_step_2])
    state = AgentState(messages=[])
    tools = {}
    request = {}

    result = await pipeline.run_next_step(state, tools, request)
    assert result["status"] == "success"
    assert result["completed_step"] == "mock_step_1"
    assert state.messages == ["Step 1 executed"]

    result = await pipeline.run_next_step(state, tools, request)
    assert result["status"] == "success"
    assert result["completed_step"] == "mock_step_2"
    assert state.messages == ["Step 1 executed", "Step 2 executed"]

    assert pipeline.is_complete()
