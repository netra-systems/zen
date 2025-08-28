from typing import Any, Dict, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from netra_backend.app.schemas.pattern import DiscoveredPattern
from netra_backend.app.services.context import ToolContext


@tool
async def optimization_proposer(context: ToolContext, discovered_patterns: List[DiscoveredPattern], span_map: Dict[str, Any]) -> str:
    """Proposes optimizations to reduce costs or latency."""
    policies, outcomes = await context.policy_proposer.propose_policies(discovered_patterns, span_map)
    return f"Proposed {len(policies)} optimizations."