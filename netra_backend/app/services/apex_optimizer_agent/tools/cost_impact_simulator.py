from typing import Any, List

from langchain_core.tools import tool

from netra_backend.app.schemas.Policy import LearnedPolicy
from netra_backend.app.services.context import ToolContext


@tool
async def cost_impact_simulator(context: ToolContext, learned_policies: List[LearnedPolicy]) -> str:
    """Simulates the impact of optimizations on costs."""
    total_predicted_cost = 0
    for policy in learned_policies:
        prediction = await context.policy_simulator.simulate(policy)
        total_predicted_cost += prediction.predicted_cost_usd
    
    return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"