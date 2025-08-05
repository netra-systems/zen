
from app.services.deep_agent_v3.tools.multi_objective_optimization import MultiObjectiveOptimizationTool

def test_multi_objective_optimization_tool():
    """Tests the MultiObjectiveOptimizationTool."""
    tool = MultiObjectiveOptimizationTool()
    result = tool.run(cost_reduction_percent=20, latency_improvement_factor=2, usage_increase_percent=30)
    
    assert "To achieve a 20% cost reduction" in result["message"]
