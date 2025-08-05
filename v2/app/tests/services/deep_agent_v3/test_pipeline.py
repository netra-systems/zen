import pytest
from unittest.mock import AsyncMock

from app.services.deep_agent_v3.pipeline import Pipeline
from app.services.deep_agent_v3.state import AgentState

@pytest.mark.asyncio
async def test_pipeline_executes_steps_in_order():
    """Tests that the pipeline executes a series of steps in the correct order."""
    # Arrange
    step1 = AsyncMock(return_value="Step 1 complete")
    step2 = AsyncMock(return_value="Step 2 complete")
    pipeline = Pipeline(steps=[step1, step2])
    state = AgentState(messages=[])
    tools = {}
    request = {}

    # Act & Assert - Step 1
    result1 = await pipeline.run_next_step(state, tools, request)
    assert result1["status"] == "success"
    assert result1["completed_step"] == step1.__name__
    assert pipeline.current_step_index == 1
    assert not pipeline.is_complete()

    # Act & Assert - Step 2
    result2 = await pipeline.run_next_step(state, tools, request)
    assert result2["status"] == "success"
    assert result2["completed_step"] == step2.__name__
    assert pipeline.current_step_index == 2
    assert pipeline.is_complete()

@pytest.mark.asyncio
async def test_pipeline_handles_step_failure():
    """Tests that the pipeline correctly handles a step that raises an exception."""
    # Arrange
    step1 = AsyncMock(side_effect=Exception("Something went wrong"))
    step2 = AsyncMock()
    pipeline = Pipeline(steps=[step1, step2])
    state = AgentState(messages=[])
    tools = {}
    request = {}

    # Act
    result = await pipeline.run_next_step(state, tools, request)

    # Assert
    assert result["status"] == "failed"
    assert result["step"] == step1.__name__
    assert result["error"] == "Something went wrong"
    assert not pipeline.is_complete()
    step2.assert_not_called()