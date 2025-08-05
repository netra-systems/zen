
from typing import Any
from app.services.deep_agent_v3.state import AgentState

async def propose_optimal_policies(
    state: AgentState,
    policy_proposer: Any
) -> str:
    """Proposes optimal policies based on the discovered patterns."""
    if not state.discovered_patterns:
        return "No discovered patterns to propose policies for."

    span_map = {s.trace_context.span_id: s for s in state.raw_logs}
    policies, outcomes = await policy_proposer.propose_policies(state.discovered_patterns, span_map)

    state.learned_policies = policies
    state.predicted_outcomes = outcomes

    return f"Successfully proposed {len(policies)} optimal policies."
