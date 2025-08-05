from typing import Any
from app.services.apex_optimizer_agent.state import AgentState

class PolicySimulator:
    def __init__(self, policy_simulator: any):
        self.policy_simulator = policy_simulator

    async def run(self, state: AgentState) -> str:
        """Simulates the outcome of a single policy."""
        if not state.learned_policies:
            return "No policies to simulate."

        # For now, we only simulate the first policy
        # This can be extended to simulate multiple policies in the future
        policy = state.learned_policies[0]
        predicted_outcome = await self.policy_simulator.simulate(policy)

        state.predicted_outcomes = [predicted_outcome]

        return "Successfully simulated policy"