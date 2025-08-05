import asyncio
from app.services.deep_agent_v3.tools.cost_simulation_for_increased_usage import CostSimulationForIncreasedUsageTool

def test_cost_simulation_for_increased_usage_tool():
    """Tests the CostSimulationForIncreasedUsageTool."""
    tool = CostSimulationForIncreasedUsageTool()
    result = asyncio.run(tool.run(usage_increase_percentage=50))
    
    assert "increase in agent usage" in result["message"]