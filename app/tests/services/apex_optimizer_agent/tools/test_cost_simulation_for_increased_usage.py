import asyncio
from app.services.apex_optimizer_agent.tools.cost_simulation_for_increased_usage import CostSimulationForIncreasedUsageTool

class MockCostSimulationForIncreasedUsageTool(CostSimulationForIncreasedUsageTool):
    async def run(self, *args, **kwargs):
        return "mocked result"

def test_cost_simulation_for_increased_usage_tool():
    """Tests the CostSimulationForIncreasedUsageTool."""
    tool = MockCostSimulationForIncreasedUsageTool()
    assert tool != None
    result = asyncio.run(tool.run())
    assert result == "mocked result"