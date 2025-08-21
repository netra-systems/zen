from langchain_core.tools import tool
from typing import List, Any
from app.services.context import ToolContext

@tool
async def latency_bottleneck_identifier(context: ToolContext) -> str:
    """Identifies the main latency bottlenecks in the system."""
    latency_bottlenecks = {}
    for log in context.logs:
        latency_result = await context.performance_predictor.execute(log.request.prompt_text, log.model_dump())
        prompt_category = log.request.prompt_text.split(" ")[0] # Simple categorization by first word
        if prompt_category not in latency_bottlenecks:
            latency_bottlenecks[prompt_category] = []
        latency_bottlenecks[prompt_category].append(latency_result["predicted_latency_ms"])
    
    avg_latency_bottlenecks = {k: sum(v) / len(v) for k, v in latency_bottlenecks.items()}
    sorted_latency_bottlenecks = sorted(avg_latency_bottlenecks.items(), key=lambda item: item[1], reverse=True)
    
    return f"Identified latency bottlenecks: {sorted_latency_bottlenecks}"