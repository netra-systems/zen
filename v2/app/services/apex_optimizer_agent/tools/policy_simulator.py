from typing import Any

class PolicySimulator:
    def __init__(self, policy_simulator: any):
        self.policy_simulator = policy_simulator

    async def run(self, learned_policies: list) -> str:
        """Simulates the outcome of a single policy."""
        if not learned_policies:
            return "No policies to simulate."

        # For now, we only simulate the first policy
        # This can be extended to simulate multiple policies in the future
        policy = learned_policies[0]
        predicted_outcome = await self.policy_simulator.simulate(policy)

        return "Successfully simulated policy"