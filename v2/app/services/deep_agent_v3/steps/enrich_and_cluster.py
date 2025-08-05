from typing import Any

from app.services.deep_agent_v3.core import enrich_and_cluster_logs
from app.services.deep_agent_v3.state import AgentState

async def enrich_and_cluster(state: AgentState, llm_connector: Any) -> str:
    """Enriches logs and clusters them to find usage patterns."""
    if not state.raw_logs:
        raise ValueError("Cannot perform clustering without raw logs.")

    state.patterns = await enrich_and_cluster_logs(
        spans=state.raw_logs,
        llm_connector=llm_connector,
    )
    return f"Discovered {len(state.patterns)} usage patterns."