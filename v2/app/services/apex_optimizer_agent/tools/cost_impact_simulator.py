
class CostImpactSimulator:
    def __init__(self, policy_simulator: any):
        self.policy_simulator = policy_simulator

    async def run(self, learned_policies: list) -> str:
        """Simulates the impact of optimizations on costs."""
        total_predicted_cost = 0
        for policy in learned_policies:
            prediction = await self.policy_simulator.simulate(policy)
            total_predicted_cost += prediction.predicted_cost_usd
        
        return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"