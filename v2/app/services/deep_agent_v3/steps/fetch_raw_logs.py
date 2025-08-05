from typing import Any, Dict
from app.services.deep_agent_v3.state import AgentState

async def fetch_raw_logs(
    state: AgentState,
    log_fetcher: Any,
    request: Dict[str, Any]
) -> str:
    """Fetches raw logs from the specified data source."""
    start_time = request.get("start_time")
    end_time = request.get("end_time")
    source_table = request.get("source_table")

    logs, trace_ids = await log_fetcher.fetch_logs(
        start_time=start_time,
        end_time=end_time,
        source_table=source_table
    )

    state.raw_logs = logs
    state.trace_ids = trace_ids

    return f"Successfully fetched {len(logs)} raw logs."