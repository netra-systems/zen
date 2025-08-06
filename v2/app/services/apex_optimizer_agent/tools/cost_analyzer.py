from langchain_core.tools import tool
from typing import List
from pydantic import BaseModel, Field

class Log(BaseModel):
    request: dict = Field(..., description="The request data for the log.")

@tool
async def cost_analyzer(logs: List[Log], db_session: any, llm_manager: any, cost_estimator: any) -> str:
    """Analyzes the current costs of the system."""
    total_cost = 0
    for log in logs:
        cost_result = await cost_estimator.execute(log.request.prompt_text, log.model_dump())
        total_cost += cost_result["estimated_cost_usd"]
    
    return f"Analyzed current costs. Total estimated cost: ${total_cost:.2f}"