from langchain_core.tools import tool
from typing import List, Any
from app.schemas.Policy import LearnedPolicy

@tool
async def quality_impact_simulator(learned_policies: List[LearnedPolicy], db_session: Any, llm_manager: Any, policy_simulator: any) -> str:
    """Simulates the impact of optimizations on quality."""
    total_predicted_quality = 0
    for policy in learned_policies:
        prediction = await policy_simulator.simulate(policy)
        total_predicted_quality += prediction.predicted_quality_score
    
    average_predicted_quality = total_predicted_quality / len(learned_policies) if learned_policies else 0
    
    return f"Simulated impact on quality. Average predicted quality: {average_predicted_quality:.2f}"