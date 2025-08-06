from langchain_core.tools import tool
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class DiscoveredPattern(BaseModel):
    pattern_id: str = Field(..., description="The ID of the pattern.")
    description: str = Field(..., description="A description of the pattern.")

@tool
async def optimization_proposer(discovered_patterns: List[DiscoveredPattern], span_map: Dict[str, Any], db_session: Any, llm_manager: Any, policy_proposer: any) -> str:
    """Proposes optimizations to reduce costs or latency."""
    policies, outcomes = await policy_proposer.propose_policies(discovered_patterns, span_map)
    return f"Proposed {len(policies)} optimizations."