
import json
from typing import Any

from app.services.deep_agent_v3.core import query_raw_logs
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.models import DataSource, TimeRange

async def fetch_raw_logs(state: AgentState, db_session: Any) -> str:
    """Fetches raw log data from the user's ClickHouse database."""
    state.raw_logs = await query_raw_logs(
        db_session=db_session,
        source_table=state.request.data_source.source_table,
        start_time=state.request.time_range.start_time,
        end_time=state.request.time_range.end_time,
        filters=state.request.data_source.filters,
    )
    return f"Fetched {len(state.raw_logs)} log entries."
