from langchain_core.tools import tool
from typing import Any, List
from pydantic import BaseModel, Field

class LearnedPolicy(BaseModel):
    pattern_name: str = Field(..., description="The name of the pattern.")
    optimal_supply_option_name: str = Field(..., description="The name of the optimal supply option.")

@tool
async def policy_simulator(learned_policies: List[LearnedPolicy], db_session: Any, llm_manager: Any, policy_simulator: Any) -> str:
    """Simulates the outcome of a single policy."""
    if not learned_policies:
        return "No policies to simulate."

    # For now, we only simulate the first policy
    # This can be extended to simulate multiple policies in the future
    policy = learned_policies[0]
    predicted_outcome = await policy_simulator.simulate(policy)

    return "Successfully simulated policy"