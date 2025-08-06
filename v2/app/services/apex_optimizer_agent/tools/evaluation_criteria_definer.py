from langchain_core.tools import tool
from typing import Any

@tool
async def evaluation_criteria_definer(criteria: dict, db_session: Any, llm_manager: Any) -> str:
    """Defines the evaluation criteria for new models."""
    return f"Defined evaluation criteria: {criteria}"