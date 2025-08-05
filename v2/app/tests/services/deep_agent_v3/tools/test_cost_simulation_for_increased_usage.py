from app.services.deep_agent_v3.tools.cost_simulation_for_increased_usage import CostSimulationForIncreasedUsageTool

def test_cost_simulation_for_increased_usage_tool():
    """Tests the CostSimulationForIncreasedUsageTool."""
    tool = CostSimulationForIncreasedUsageTool()
    result = tool.run(usage_increase_percent=50)
    
    assert "increase in agent usage" in result["message"]