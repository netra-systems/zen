
from app.services.deep_agent_v3.tools.tool_latency_optimization import ToolLatencyOptimizationTool

def test_tool_latency_optimization_tool():
    """Tests the ToolLatencyOptimizationTool."""
    tool = ToolLatencyOptimizationTool()
    result = tool.run(target_latency_reduction=3)
    
    assert "To achieve a 3x latency reduction" in result["message"]
