from app.services.deep_agent_v3.state import AgentState

async def research_optimization_methods(state: AgentState, function_name: str, llm_connector: any) -> str:
    """Researches advanced optimization methods for a function."""
    prompt = f"""
    Research and suggest advanced optimization methods for the function '{function_name}'.
    """
    
    response = await llm_connector.get_completion(prompt)
    
    state.messages.append({"message": f"Optimization methods for {function_name}:\n{response}"})
    return f"Researched optimization methods for {function_name}."