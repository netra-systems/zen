from typing import Any, Dict
from app.services.deep_agent_v3.state import AgentState

async def fetch_raw_logs(state: AgentState, log_fetcher: Any, request: Dict[str, Any]) -> str:
    """
    Fetches raw logs from the database.
    """
    time_range = request.get("time_range")
    if not time_range:
        return "Error: time_range is required."

    logs = log_fetcher.fetch_logs(time_range)
    state.raw_logs = logs
    return "Raw logs fetched."
