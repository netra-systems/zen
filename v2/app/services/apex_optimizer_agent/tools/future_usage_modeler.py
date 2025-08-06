from langchain_core.tools import tool
from typing import List, Any
from pydantic import BaseModel, Field
from app.services.context import ToolContext

class Log(BaseModel):
    pass

@tool
async def future_usage_modeler(context: ToolContext, usage_increase_percent: float) -> str:
    """Models the future usage of the system."""
    current_usage = len(context.logs)
    future_usage = current_usage * (1 + usage_increase_percent / 100)
    
    return f"Modeled future usage: {future_usage:.2f} requests"