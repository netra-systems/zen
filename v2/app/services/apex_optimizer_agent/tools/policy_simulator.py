from langchain_core.tools import tool
from typing import Any

@tool
async def policy_simulator(learned_policies: list, policy_simulator: any) -> str:
    """Simulates the outcome of a single policy."""
    if not learned_policies:
        return "No policies to simulate."

    # For now, we only simulate the first policy
    # This can be extended to simulate multiple policies in the future
    policy = learned_policies[0]
    predicted_outcome = await policy_simulator.simulate(policy)

    return "Successfully simulated policy"
