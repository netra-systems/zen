from langchain_core.tools import tool
from typing import List, Any
from pydantic import BaseModel, Field
from app.services.context import ToolContext

class Log(BaseModel):
    request: dict = Field(..., description="The request data for the log.")

@tool
async def latency_analyzer(context: ToolContext) -> str:
    """Analyzes the current latency of the system."""
    total_latency = 0
    for log in context.logs:
        latency_result = await context.performance_predictor.execute(log.request.prompt_text, log.model_dump())
        total_latency += latency_result["predicted_latency_ms"]
    
    average_latency = total_latency / len(context.logs) if context.logs else 0
    
    return f"Analyzed current latency. Average predicted latency: {average_latency:.2f}ms"