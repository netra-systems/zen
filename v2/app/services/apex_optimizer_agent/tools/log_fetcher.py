from typing import Any, Dict
from app.services.apex_optimizer_agent.state import AgentState

class LogFetcher:
    def __init__(self, log_fetcher: any):
        self.log_fetcher = log_fetcher

    async def run(self, state: AgentState, request: Dict[str, Any]) -> str:
        """
        Fetches raw logs from the database.
        """
        time_range = request.get("time_range")
        source_table = request.get("source_table")
        if not time_range:
            return "Error: time_range is required."

        logs, trace_ids = self.log_fetcher.fetch_logs(time_range=time_range, source_table=source_table)
        state.raw_logs = logs
        state.trace_ids = trace_ids
        return "Raw logs fetched."