import pytest
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

@pytest.mark.asyncio
async def test_cost_estimator():
    estimator = CostEstimator(llm_connector=None)
    result = await estimator.execute("test model", {})
    assert isinstance(result["estimated_cost_usd"], float)

@pytest.mark.asyncio
async def test_performance_predictor():
    predictor = PerformancePredictor(llm_connector=None)
    result = await predictor.execute("test model", {})
    assert isinstance(result["predicted_latency_ms"], int)