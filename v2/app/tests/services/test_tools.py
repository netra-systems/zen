
import pytest
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

@pytest.mark.asyncio
async def test_cost_estimator():
    estimator = CostEstimator(llm_connector=None)
    result = await estimator.estimate_cost("test model", {})
    assert isinstance(result, float)

@pytest.mark.asyncio
async def test_performance_predictor():
    predictor = PerformancePredictor(llm_connector=None)
    result = await predictor.predict_performance("test model", {})
    assert isinstance(result, float)
