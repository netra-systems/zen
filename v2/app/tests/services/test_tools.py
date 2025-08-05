import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

@pytest.mark.asyncio
async def test_cost_estimator():
    mock_llm_connector = MagicMock()
    mock_llm_connector.get_completion = AsyncMock(return_value="0.01")
    estimator = CostEstimator(llm_connector=mock_llm_connector)
    result = await estimator.execute("test model", {})
    assert isinstance(result["estimated_cost_usd"], float)

@pytest.mark.asyncio
async def test_performance_predictor():
    mock_llm_connector = MagicMock()
    mock_llm_connector.get_completion = AsyncMock(return_value="100")
    predictor = PerformancePredictor(llm_connector=mock_llm_connector)
    result = await predictor.execute("test model", {})
    assert isinstance(result["predicted_latency_ms"], int)