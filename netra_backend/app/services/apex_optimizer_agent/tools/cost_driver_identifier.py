from typing import Any, List

from langchain_core.tools import tool

from netra_backend.app.services.context import ToolContext


@tool
async def cost_driver_identifier(context: ToolContext) -> str:
    """Identifies the main drivers of cost in the system."""
    cost_drivers = {}
    for log in context.logs:
        cost_result = await context.cost_estimator.execute(log.request.prompt_text, log.model_dump())
        prompt_category = log.request.prompt_text.split(" ")[0] # Simple categorization by first word
        if prompt_category not in cost_drivers:
            cost_drivers[prompt_category] = 0
        cost_drivers[prompt_category] += cost_result["estimated_cost_usd"]
    
    sorted_cost_drivers = sorted(cost_drivers.items(), key=lambda item: item[1], reverse=True)
    
    return f"Identified cost drivers: {sorted_cost_drivers}"