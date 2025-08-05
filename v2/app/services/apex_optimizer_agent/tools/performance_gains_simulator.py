from app.services.apex_optimizer_agent.state import AgentState

class PerformanceGainsSimulator:
    def __init__(self, policy_simulator: any):
        self.policy_simulator = policy_simulator

    async def run(self, state: AgentState) -> str:
        """Simulates the performance gains of an optimized function."""
        total_predicted_latency = 0
        for policy in state.learned_policies:
            prediction = await self.policy_simulator.simulate(policy)
            total_predicted_latency += prediction.predicted_latency_ms
        
        average_predicted_latency = total_predicted_latency / len(state.learned_policies) if state.learned_policies else 0
        
        state.messages.append({"message": f"Average predicted latency after optimizations: {average_predicted_latency:.2f}ms"})
        return f"Simulated performance gains. Average predicted latency: {average_predicted_latency:.2f}ms"