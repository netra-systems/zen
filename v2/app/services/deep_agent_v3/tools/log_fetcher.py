
from app.services.deep_agent_v3.core import query_raw_logs

class LogFetcher:
    def __init__(self, db_session):
        self.db_session = db_session

    async def execute(self, source_table: str, start_time: str, end_time: str):
        return await query_raw_logs(self.db_session, source_table, start_time, end_time)
