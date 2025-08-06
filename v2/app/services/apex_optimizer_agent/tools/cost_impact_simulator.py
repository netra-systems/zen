from langchain_core.tools import tool
from typing import List, Any
from pydantic import BaseModel, Field
from app.services.context import ToolContext

class LearnedPolicy(BaseModel):
    pattern_name: str = Field(..., description="The name of the pattern.")
    optimal_supply_option_name: str = Field(..., description="The name of the optimal supply option.")

@tool
async def cost_impact_simulator(context: ToolContext, learned_policies: List[LearnedPolicy]) -> str:
    """Simulates the impact of optimizations on costs."""
    total_predicted_cost = 0
    for policy in learned_policies:
        prediction = await context.policy_simulator.simulate(policy)
        total_predicted_cost += prediction.predicted_cost_usd
    
    return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"