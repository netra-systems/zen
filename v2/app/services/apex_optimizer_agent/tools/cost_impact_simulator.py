from langchain_core.tools import tool

@tool
async def cost_impact_simulator(learned_policies: list, policy_simulator: any) -> str:
    """Simulates the impact of optimizations on costs."""
    total_predicted_cost = 0
    for policy in learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_cost += prediction.predicted_cost_usd
    
    return f"Simulated impact on costs. Total predicted cost: ${total_predicted_cost:.2f}"