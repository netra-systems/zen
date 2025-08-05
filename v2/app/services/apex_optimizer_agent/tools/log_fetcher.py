from langchain_core.tools import tool
from typing import Any, Dict, List

@tool
async def log_fetcher(workloads: List[Dict[str, Any]], log_fetcher: any) -> str:
    """
    Fetches raw logs from the database for each workload.
    """
    all_logs = []
    all_trace_ids = []
    for workload in workloads:
        time_range = workload.get("time_range")
        data_source = workload.get("data_source")
        if not time_range or not data_source:
            return "Error: time_range and data_source are required for each workload."
        
        source_table = data_source.get("source_table")
        if not source_table:
            return "Error: source_table is required in the data_source for each workload."

        logs, trace_ids = log_fetcher.fetch_logs(time_range=time_range, source_table=source_table)
        all_logs.extend(logs)
        all_trace_ids.extend(trace_ids)
        
    return f"Fetched {len(all_logs)} logs for {len(workloads)} workloads."
