from langchain_core.tools import tool

@tool
async def cost_analyzer(logs: list, cost_estimator: any) -> str:
    """Analyzes the current costs of the system."""
    total_cost = 0
    for log in logs:
        cost_result = await cost_estimator.execute(log.request.prompt_text, log.model_dump())
        total_cost += cost_result["estimated_cost_usd"]
    
    return f"Analyzed current costs. Total estimated cost: ${total_cost:.2f}"