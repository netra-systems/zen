from typing import Any, Dict
from app.services.deep_agent_v3.state import AgentState

async def fetch_raw_logs(state: AgentState, log_fetcher: Any, request: Dict[str, Any]) -> str:
    """
    Fetches raw logs from the database.
    """
    time_range = request.get("time_range")
    source_table = request.get("source_table")
    if not time_range:
        return "Error: time_range is required."

    logs, trace_ids = log_fetcher.fetch_logs(time_range=time_range, source_table=source_table)
    state.raw_logs = logs
    state.trace_ids = trace_ids
    return "Raw logs fetched."
