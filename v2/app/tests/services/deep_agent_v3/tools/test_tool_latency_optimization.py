
import asyncio
from app.services.deep_agent_v3.tools.tool_latency_optimization import ToolLatencyOptimizationTool

def test_tool_latency_optimization_tool():
    """Tests the ToolLatencyOptimizationTool."""
    tool = ToolLatencyOptimizationTool()
    result = asyncio.run(tool.run(latency_reduction_factor=3, budget_constraint=0))
    
    assert "To achieve a 3x latency reduction" in result["message"]
