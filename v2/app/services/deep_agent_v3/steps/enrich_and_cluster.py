
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.tools.log_pattern_identifier import LogPatternIdentifier

async def enrich_and_cluster(state: AgentState, tool: LogPatternIdentifier) -> str:
    """Enriches logs with additional metrics and clusters them to find patterns."""
    state.patterns = await tool.execute(state.raw_logs, n_patterns=5) # Assuming n_patterns=5 for now
    state.span_map = {span.trace_context.span_id: span for span in state.raw_logs}
    return f"Identified {len(state.patterns)} patterns."
