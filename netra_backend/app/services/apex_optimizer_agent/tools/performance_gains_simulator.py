from langchain_core.tools import tool
from typing import List, Any
from netra_backend.app.schemas.Policy import LearnedPolicy

@tool
async def performance_gains_simulator(learned_policies: List[LearnedPolicy], db_session: Any, llm_manager: Any, policy_simulator: any) -> str:
    """Simulates the performance gains of an optimized function."""
    total_predicted_latency = 0
    for policy in learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_latency += prediction.predicted_latency_ms
    
    average_predicted_latency = total_predicted_latency / len(learned_policies) if learned_policies else 0
    
    return f"Simulated performance gains. Average predicted latency: {average_predicted_latency:.2f}ms"