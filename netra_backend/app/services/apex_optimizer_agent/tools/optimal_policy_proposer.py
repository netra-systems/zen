from langchain_core.tools import tool
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from netra_backend.app.services.context import ToolContext

class Pattern(BaseModel):
    pattern_id: str = Field(..., description="The ID of the pattern.")
    description: str = Field(..., description="A description of the pattern.")

@tool
async def optimal_policy_proposer(context: ToolContext, patterns: List[Pattern]) -> str:
    """
    Proposes optimal policies based on the clustered logs.
    """
    if not patterns:
        return "Error: patterns is not available."

    policies = await context.policy_proposer.propose_policies(patterns)
    return "Optimal policies proposed."