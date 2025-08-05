from langchain_core.tools import tool

@tool
async def optimization_proposer(discovered_patterns: list, span_map: dict, policy_proposer: any) -> str:
    """Proposes optimizations to reduce costs or latency."""
    policies, outcomes = await policy_proposer.propose_policies(discovered_patterns, span_map)
    return f"Proposed {len(policies)} optimizations."