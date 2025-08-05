from app.services.deep_agent_v3.state import AgentState

async def analyze_current_latency(state: AgentState, performance_predictor: any) -> str:
    """Analyzes the current latency of the system."""
    total_latency = 0
    for log in state.logs:
        latency_result = await performance_predictor.execute(log.request.prompt_text, log.model_dump())
        total_latency += latency_result["predicted_latency_ms"]
    
    average_latency = total_latency / len(state.logs) if state.logs else 0
    
    state.messages.append({"message": f"Average predicted latency: {average_latency:.2f}ms"})
    return f"Analyzed current latency. Average predicted latency: {average_latency:.2f}ms"