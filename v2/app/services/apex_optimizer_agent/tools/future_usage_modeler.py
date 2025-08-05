from langchain_core.tools import tool

@tool
async def future_usage_modeler(logs: list, usage_increase_percent: float) -> str:
    """Models the future usage of the system."""
    current_usage = len(logs)
    future_usage = current_usage * (1 + usage_increase_percent / 100)
    
    return f"Modeled future usage: {future_usage:.2f} requests"