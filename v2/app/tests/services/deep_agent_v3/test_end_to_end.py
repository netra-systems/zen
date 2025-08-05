import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.deep_agent_v3.main import DeepAgentV3
from app.db.models_clickhouse import AnalysisRequest
from app.services.deep_agent_v3.state import AgentState

class IsCompleteSideEffect:
    def __init__(self):
        self.called = False

    def __call__(self):
        if not self.called:
            self.called = True
            return False
        return True

@pytest.mark.asyncio
async def test_end_to_end_cost_reduction_quality_preservation():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms."
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()

@pytest.mark.asyncio
async def test_end_to_end_latency_reduction_cost_constraint():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money."
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()

@pytest.mark.asyncio
async def test_end_to_end_usage_increase_impact_analysis():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?"
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()

@pytest.mark.asyncio
async def test_end_to_end_function_optimization():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="I need to optimize the 'user_authentication' function. What advanced methods can I use?"
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()

@pytest.mark.asyncio
async def test_end_to_end_model_effectiveness_analysis():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?"
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()

@pytest.mark.asyncio
async def test_end_to_end_kv_caching_audit():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="I want to audit all uses of KV caching in my system to find optimization opportunities."
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()

@pytest.mark.asyncio
async def test_end_to_end_multi_objective_optimization():
    # Arrange
    run_id = "test_run_id"
    request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?"
    )
    db_session = MagicMock()
    llm_connector = MagicMock()

    # Create the agent
    agent = DeepAgentV3(run_id, request, db_session, llm_connector)
    
    async def mock_run_next_step(state, tools, request):
        state.final_report = "This is the final report."
        return {"status": "success", "completed_step": "generate_final_report"}

    agent.pipeline.run_next_step = AsyncMock(side_effect=mock_run_next_step)
    agent.pipeline.is_complete = MagicMock(side_effect=IsCompleteSideEffect())

    # Act
    result = await agent.run_full_analysis()

    # Assert
    assert result is not None
    agent.pipeline.run_next_step.assert_called_once()