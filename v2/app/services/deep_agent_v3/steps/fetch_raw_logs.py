
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.tools.log_fetcher import LogFetcher

async def fetch_raw_logs(state: AgentState, tool: LogFetcher, request: dict) -> str:
    """Fetches raw logs from the specified data source."""
    workload = request.workloads[0]  # Assuming single workload
    state.raw_logs = await tool.execute(
        source_table=workload["data_source"]["source_table"],
        start_time=workload["time_range"]["start_time"],
        end_time=workload["time_range"]["end_time"],
    )
    return f"Fetched {len(state.raw_logs)} raw logs."
