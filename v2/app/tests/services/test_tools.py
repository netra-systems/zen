
import pytest
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

@pytest.mark.asyncio
async def test_cost_estimator():
    estimator = CostEstimator(llm_connector=None)
    result = await estimator.execute("test prompt", {})
    assert "estimated_cost_usd" in result

@pytest.mark.asyncio
async def test_performance_predictor():
    predictor = PerformancePredictor(llm_connector=None)
    result = await predictor.execute("test prompt", {})
    assert "predicted_latency_ms" in result
