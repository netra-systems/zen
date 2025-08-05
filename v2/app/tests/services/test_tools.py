import pytest
from app.llm.llm_manager import LLMManager
from unittest.mock import MagicMock, AsyncMock
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

@pytest.mark.asyncio
async def test_cost_estimator():
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_llm_manager.get_llm.return_value.ainvoke = AsyncMock(return_value=MagicMock(content="0.01"))
    estimator = CostEstimator(llm_manager=mock_llm_manager)
    result = await estimator.execute("test model", {})
    assert isinstance(result["estimated_cost_usd"], float)

@pytest.mark.asyncio
async def test_performance_predictor():
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_llm_manager.get_llm.return_value.ainvoke = AsyncMock(return_value=MagicMock(content="100"))
    predictor = PerformancePredictor(llm_manager=mock_llm_manager)
    result = await predictor.execute("test model", {})
    assert isinstance(result["predicted_latency_ms"], int)