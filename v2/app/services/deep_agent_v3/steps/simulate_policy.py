
from typing import Any
from app.services.deep_agent_v3.state import AgentState

async def simulate_policy(
    state: AgentState,
    policy_simulator: Any
) -> str:
    """Simulates the outcome of a single policy."""
    if not state.learned_policies:
        return "No policies to simulate."

    # For now, we only simulate the first policy
    # This can be extended to simulate multiple policies in the future
    policy = state.learned_policies[0]
    predicted_outcome = await policy_simulator.simulate(policy)

    state.predicted_outcomes = [predicted_outcome]

    return "Successfully simulated policy"
