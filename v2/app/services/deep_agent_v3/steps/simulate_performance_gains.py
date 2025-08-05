from app.services.deep_agent_v3.state import AgentState

async def simulate_performance_gains(state: AgentState, policy_simulator: any) -> str:
    """Simulates the performance gains of an optimized function."""
    total_predicted_latency = 0
    for policy in state.learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_latency += prediction.predicted_latency_ms
    
    average_predicted_latency = total_predicted_latency / len(state.learned_policies) if state.learned_policies else 0
    
    state.messages.append({"message": f"Average predicted latency after optimizations: {average_predicted_latency:.2f}ms"})
    return f"Simulated performance gains. Average predicted latency: {average_predicted_latency:.2f}ms"