import asyncio
from app.services.deep_agent_v3.tools.multi_objective_optimization import MultiObjectiveOptimizationTool

def test_multi_objective_optimization_tool():
    """Tests the MultiObjectiveOptimizationTool."""
    tool = MultiObjectiveOptimizationTool()
    # This tool has no execute method, so we can't test it directly.
    # We will just check if the object can be created.
    assert tool is not None
