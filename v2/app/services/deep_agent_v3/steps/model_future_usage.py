from app.services.deep_agent_v3.state import AgentState

async def model_future_usage(state: AgentState, usage_increase_percent: float) -> str:
    """Models the future usage of the system."""
    current_usage = len(state.logs)
    future_usage = current_usage * (1 + usage_increase_percent / 100)
    
    state.messages.append({"message": f"Future usage modeled: {future_usage:.2f} requests"})
    return f"Modeled future usage: {future_usage:.2f} requests"