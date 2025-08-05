
class QualityImpactSimulator:
    def __init__(self, policy_simulator: any):
        self.policy_simulator = policy_simulator

    async def run(self, learned_policies: list) -> str:
        """Simulates the impact of optimizations on quality."""
        total_predicted_quality = 0
        for policy in learned_policies:
            prediction = await self.policy_simulator.simulate(policy)
            total_predicted_quality += prediction.predicted_quality_score
        
        average_predicted_quality = total_predicted_quality / len(learned_policies) if learned_policies else 0
        
        return f"Simulated impact on quality. Average predicted quality: {average_predicted_quality:.2f}"