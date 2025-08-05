
from typing import Any, List, Dict, Optional
from datetime import datetime
import json
from app.db.models_clickhouse import UnifiedLogEntry
from app.services.security_service import security_service
from app.db.clickhouse import get_clickhouse_client
from app.config import settings

class LogFetcher:
    def __init__(self, db_session: Any):
        self.db_session = db_session

    async def fetch_logs(
        self, source_table: str, start_time: datetime, end_time: datetime, filters: dict = None
    ) -> (List[UnifiedLogEntry], List[str]):
        """Connects to ClickHouse to fetch raw log data."""
        from app.config import settings
        if settings.app_env == "development":
            from app.services.deep_agent_v3.dev_utils import get_or_create_dev_user
            dev_user = get_or_create_dev_user(self.db_session)
            user_id = dev_user.id
        else:
            user_id = self.db_session.info["user_id"]

        credentials = security_service.get_user_credentials(user_id=user_id, db_session=self.db_session)
        if not credentials:
            raise ValueError("ClickHouse credentials not found for user.")

        client = get_clickhouse_client(credentials)
        database, table = source_table.split('.', 1)
        query = f"SELECT * FROM {database}.{table} WHERE timestamp BETWEEN '{start_time}' AND '{end_time}'"

        if filters:
            for key, value in filters.items():
                query += f" AND {key} = '{value}'"

        query_result = client.execute(query, with_column_types=True)
        if not query_result or not query_result[0]:
            return [], []

        column_names = [col[0] for col in query_result[1]]
        data_rows = query_result[0]

        log_entries = []
        trace_ids = []
        for row in data_rows:
            try:
                row_dict = dict(zip(column_names, row))
                for key, value in row_dict.items():
                    if isinstance(value, str) and value.startswith('{'):
                        try:
                            row_dict[key] = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                log_entry = UnifiedLogEntry.model_validate(row_dict)
                log_entries.append(log_entry)
                trace_ids.append(log_entry.trace_context.trace_id)
            except Exception as e:
                print(f"Skipping a row due to parsing/validation error: {e}. Row data: {row}")
                continue
        return log_entries, trace_ids
