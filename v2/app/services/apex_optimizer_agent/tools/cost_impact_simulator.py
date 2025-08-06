from langchain_core.tools import tool
from typing import List, Any
from pydantic import BaseModel, Field

class LearnedPolicy(BaseModel):
    pattern_name: str = Field(..., description="The name of the pattern.")
    optimal_supply_option_name: str = Field(..., description="The name of the optimal supply option.")

@tool
async def cost_impact_simulator(learned_policies: List[LearnedPolicy], db_session: Any, llm_manager: Any, policy_simulator: any) -> str:
    """Simulates the impact of optimizations on costs."""
    total_predicted_cost = 0
    for policy in learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_cost += prediction.predicted_cost_usd
    
    return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"