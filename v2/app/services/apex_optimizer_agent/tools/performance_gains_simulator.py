from langchain_core.tools import tool

@tool
async def performance_gains_simulator(learned_policies: list, policy_simulator: any) -> str:
    """Simulates the performance gains of an optimized function."""
    total_predicted_latency = 0
    for policy in learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_latency += prediction.predicted_latency_ms
    
    average_predicted_latency = total_predicted_latency / len(learned_policies) if learned_policies else 0
    
    return f"Simulated performance gains. Average predicted latency: {average_predicted_latency:.2f}ms"