from app.services.deep_agent_v3.state import AgentState

async def simulate_impact_on_quality(state: AgentState, policy_simulator: any) -> str:
    """Simulates the impact of optimizations on quality."""
    total_predicted_quality = 0
    for policy in state.learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_quality += prediction.predicted_quality_score
    
    average_predicted_quality = total_predicted_quality / len(state.learned_policies) if state.learned_policies else 0
    
    state.messages.append({"message": f"Average predicted quality after optimizations: {average_predicted_quality:.2f}"})
    return f"Simulated impact on quality. Average predicted quality: {average_predicted_quality:.2f}"