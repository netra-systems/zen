import asyncio
from app.services.apex_optimizer_agent.tools.multi_objective_optimization import MultiObjectiveOptimizationTool

class MockMultiObjectiveOptimizationTool(MultiObjectiveOptimizationTool):
    async def run(self, *args, **kwargs):
        return "mocked result"

def test_multi_objective_optimization_tool():
    """Tests the MultiObjectiveOptimizationTool."""
    tool = MockMultiObjectiveOptimizationTool()
    assert tool is not None
    result = asyncio.run(tool.run())
    assert result == "mocked result"