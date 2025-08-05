
import asyncio
from app.services.deep_agent_v3.tools.cost_reduction_quality_preservation import CostReductionQualityPreservationTool

def test_cost_reduction_quality_preservation_tool():
    """Tests the CostReductionQualityPreservationTool."""
    tool = CostReductionQualityPreservationTool()
    result = asyncio.run(tool.run(feature_x_latency=500, feature_y_latency=200))
    
    assert "To reduce costs while maintaining quality" in result["message"]
