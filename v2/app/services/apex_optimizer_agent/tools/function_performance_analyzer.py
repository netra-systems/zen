from langchain_core.tools import tool
from typing import List
from pydantic import BaseModel, Field

class Log(BaseModel):
    request: dict = Field(..., description="The request data for the log.")

@tool
async def function_performance_analyzer(logs: List[Log], function_name: str, performance_predictor: any) -> str:
    """Analyzes the performance of a specific function."""
    total_latency = 0
    function_logs = [log for log in logs if function_name in log.request.prompt_text]
    
    if not function_logs:
        return f"No logs found for function: {function_name}"
    
    for log in function_logs:
        latency_result = await performance_predictor.execute(log.request.prompt_text, log.model_dump())
        total_latency += latency_result["predicted_latency_ms"]
    
    average_latency = total_latency / len(function_logs)
    
    return f"Analyzed function performance for {function_name}. Average predicted latency: {average_latency:.2f}ms"