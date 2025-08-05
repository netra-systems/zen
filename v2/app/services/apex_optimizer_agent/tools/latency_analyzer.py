from langchain_core.tools import tool
from typing import List
from pydantic import BaseModel, Field

class Log(BaseModel):
    request: dict = Field(..., description="The request data for the log.")

@tool
async def latency_analyzer(logs: List[Log], performance_predictor: any) -> str:
    """Analyzes the current latency of the system."""
    total_latency = 0
    for log in logs:
        latency_result = await performance_predictor.execute(log.request.prompt_text, log.model_dump())
        total_latency += latency_result["predicted_latency_ms"]
    
    average_latency = total_latency / len(logs) if logs else 0
    
    return f"Analyzed current latency. Average predicted latency: {average_latency:.2f}ms"