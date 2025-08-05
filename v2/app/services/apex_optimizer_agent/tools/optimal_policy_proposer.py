from langchain_core.tools import tool
from typing import Any, Dict, List
from pydantic import BaseModel, Field

class Pattern(BaseModel):
    pattern_id: str = Field(..., description="The ID of the pattern.")
    description: str = Field(..., description="A description of the pattern.")

@tool
async def optimal_policy_proposer(patterns: List[Pattern], policy_proposer: any) -> str:
    """
    Proposes optimal policies based on the clustered logs.
    """
    if not patterns:
        return "Error: patterns is not available."

    policies = await policy_proposer.propose_policies(patterns)
    return "Optimal policies proposed."