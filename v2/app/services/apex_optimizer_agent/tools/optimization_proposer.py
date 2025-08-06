from langchain_core.tools import tool
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.services.context import ToolContext

class DiscoveredPattern(BaseModel):
    pattern_id: str = Field(..., description="The ID of the pattern.")
    description: str = Field(..., description="A description of the pattern.")

@tool
async def optimization_proposer(context: ToolContext, discovered_patterns: List[DiscoveredPattern], span_map: Dict[str, Any]) -> str:
    """Proposes optimizations to reduce costs or latency."""
    policies, outcomes = await context.policy_proposer.propose_policies(discovered_patterns, span_map)
    return f"Proposed {len(policies)} optimizations."