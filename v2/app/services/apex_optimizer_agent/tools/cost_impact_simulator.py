from app.services.apex_optimizer_agent.state import AgentState

class CostImpactSimulator:
    def __init__(self, policy_simulator: any):
        self.policy_simulator = policy_simulator

    async def run(self, state: AgentState) -> str:
        """Simulates the impact of optimizations on costs."""
        total_predicted_cost = 0
        for policy in state.learned_policies:
            prediction = await self.policy_simulator.simulate(policy)
            total_predicted_cost += prediction.predicted_cost_usd
        
        state.messages.append({"message": f"Total predicted cost after optimizations: ${total_predicted_cost:.2f}"})
        return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"