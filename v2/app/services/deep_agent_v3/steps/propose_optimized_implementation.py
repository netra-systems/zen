from app.services.deep_agent_v3.state import AgentState

async def propose_optimized_implementation(state: AgentState, function_name: str, llm_connector: any) -> str:
    """Proposes an optimized implementation for a function."""
    prompt = f"""
    Given the function '{function_name}', propose an optimized implementation.
    Provide the optimized code and an explanation of the changes.
    """
    
    response = await llm_connector.get_completion(prompt)
    
    state.messages.append({"message": f"Optimized implementation for {function_name}:\n{response}"})
    return f"Proposed optimized implementation for {function_name}."