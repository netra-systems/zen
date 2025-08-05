from app.services.deep_agent_v3.state import AgentState

async def simulate_impact_on_rate_limits(state: AgentState, usage_increase_percent: float, llm_connector: any) -> str:
    """Simulates the impact of usage increase on rate limits."""
    prompt = f"
    Given a {usage_increase_percent}% increase in agent usage, how will this impact my costs and rate limits?
    Current usage is {len(state.logs)} requests.
    "
    
    response = await llm_connector.get_completion(prompt)
    
    state.messages.append({"message": f"Impact on rate limits:\n{response}"})
    return f"Simulated impact on rate limits."