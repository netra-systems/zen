from typing import Any, List, Dict, Optional
from datetime import datetime
import json
from app.db.models_clickhouse import UnifiedLogEntry
from app.services.security_service import security_service
from app.db.clickhouse import get_clickhouse_client
from app.config import settings
from app.services.deep_agent_v3.tools.base import BaseTool, ToolMetadata

class LogFetcher(BaseTool):
    metadata = ToolMetadata(
        name="log_fetcher",
        description="Fetches raw log data from ClickHouse.",
        version="1.0.0",
        status="production"
    )

    async def run(
        self, source_table: str, start_time: datetime, end_time: datetime, filters: dict = None
    ) -> (List[UnifiedLogEntry], List[str]):
        """Connects to ClickHouse to fetch raw log data."""
        if settings.app_env == "development":
            from app.services.deep_agent_v3.dev_utils import get_or_create_dev_user
            dev_user = await get_or_create_dev_user(self.db_session)
            user_id = dev_user.id
        else:
            user_id = self.db_session.info["user_id"]

        credentials = await security_service.get_user_credentials(user_id=user_id, db_session=self.db_session)
        if not credentials:
            raise ValueError("ClickHouse credentials not found for user.")

        async with get_clickhouse_client() as client:
            database, table = source_table.split('.', 1)
            query = f"SELECT * FROM {database}.{table} WHERE timestamp BETWEEN '{start_time}' AND '{end_time}'"

            if filters:
                for key, value in filters.items():
                    query += f" AND {key} = '{value}'"

            query_result = await client.execute_query(query)
            if not query_result:
                return [], []

            log_entries = []
            trace_ids = []
            for row in query_result:
                try:
                    for key, value in row.items():
                        if isinstance(value, str) and value.startswith('{'):
                            try:
                                row[key] = json.loads(value)
                            except json.JSONDecodeError:
                                pass
                    log_entry = UnifiedLogEntry.model_validate(row)
                    log_entries.append(log_entry)
                    if log_entry.trace_context and log_entry.trace_context.trace_id:
                        trace_ids.append(log_entry.trace_context.trace_id)
                except Exception as e:
                    print(f"Skipping a row due to parsing/validation error: {e}. Row data: {row}")
                    continue
            return log_entries, trace_ids