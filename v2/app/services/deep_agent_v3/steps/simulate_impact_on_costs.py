from app.services.deep_agent_v3.state import AgentState

async def simulate_impact_on_costs(state: AgentState, policy_simulator: any) -> str:
    """Simulates the impact of optimizations on costs."""
    total_predicted_cost = 0
    for policy in state.learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_cost += prediction.predicted_cost_usd
    
    state.messages.append({"message": f"Total predicted cost after optimizations: ${total_predicted_cost:.2f}"})
    return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"