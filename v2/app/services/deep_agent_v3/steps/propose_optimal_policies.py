from typing import Any

from app.services.deep_agent_v3.core import propose_optimal_policies
from app.services.deep_agent_v3.state import AgentState

async def propose_optimal_policies(state: AgentState, db_session: Any, llm_connector: Any) -> str:
    """Simulates outcomes and proposes optimal routing policies."""
    if not state.patterns:
        raise ValueError("Cannot propose policies without discovered patterns.")

    span_map = {span.trace_context.span_id: span for span in state.raw_logs}
    state.policies = await propose_optimal_policies(
        db_session=db_session,
        patterns=state.patterns,
        span_map=span_map,
        llm_connector=llm_connector,
    )
    return f"Generated {len(state.policies)} optimal policies."