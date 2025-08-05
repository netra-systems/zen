from langchain_core.tools import tool

@tool
async def evaluation_criteria_definer(criteria: dict) -> str:
    """Defines the evaluation criteria for new models."""
    return f"Defined evaluation criteria: {criteria}"