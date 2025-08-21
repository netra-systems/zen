from langchain_core.tools import tool
from typing import Any
from netra_backend.app.services.context import ToolContext

@tool
async def evaluation_criteria_definer(context: ToolContext, criteria: dict) -> str:
    """Defines the evaluation criteria for new models."""
    return f"Defined evaluation criteria: {criteria}"