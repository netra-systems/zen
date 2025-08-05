from app.services.deep_agent_v3.state import AgentState

async def analyze_current_costs(state: AgentState, cost_estimator: any) -> str:
    """Analyzes the current costs of the system."""
    total_cost = 0
    for log in state.logs:
        cost_result = await cost_estimator.execute(log.request.prompt_text, log.model_dump())
        total_cost += cost_result["estimated_cost_usd"]
    
    state.messages.append({"message": f"Total estimated cost: ${total_cost:.2f}"})
    return f"Analyzed current costs. Total estimated cost: ${total_cost:.2f}"