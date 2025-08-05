from langchain_core.tools import tool
from typing import Any, Dict

@tool
async def log_fetcher(request: Dict[str, Any], log_fetcher: any) -> str:
    """
    Fetches raw logs from the database.
    """
    time_range = request.get("time_range")
    source_table = request.get("source_table")
    if not time_range:
        return "Error: time_range is required."

    logs, trace_ids = log_fetcher.fetch_logs(time_range=time_range, source_table=source_table)
    return "Raw logs fetched."
