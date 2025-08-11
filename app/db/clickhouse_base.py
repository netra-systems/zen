import asyncio
import json
import clickhouse_connect
from clickhouse_connect.driver.client import Client
from typing import List, Dict, Any, Iterable

class ClickHouseDatabase:
    """
    A client for interacting with a ClickHouse database.
    It handles connection, disconnection, and data operations.
    """
    def __init__(self, host: str, port: int, database: str, user: str, password: str, secure: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.secure = secure
        self.client: Client | None = None

        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                secure=self.secure
            )
            self.client.ping()
        except Exception as e:
            self.client = None
            raise ConnectionError(f"Could not connect to ClickHouse: {e}") from e

    def ping(self):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.ping()
            return True
        except Exception as e:
            return False

    async def test_connection(self) -> bool:
        """Test if the ClickHouse connection is working."""
        try:
            if not self.client:
                return False
            # Run a simple query to test the connection
            await self.execute_query("SELECT 1")
            return True
        except Exception:
            return False

    async def command(self, cmd: str, parameters: Dict[str, Any] | None = None, settings: Dict[str, Any] | None = None):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        return await asyncio.to_thread(self.client.command, cmd, parameters=parameters, settings=settings)

    async def execute_query(self, query: str, parameters: Dict[str, Any] | None = None, settings: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        
        def _query():
            result = self.client.query(query, parameters=parameters, settings=settings)
            return list(result.named_results())

        return await asyncio.to_thread(_query)

    async def insert_data(self, table: str, data: List[List[Any]], column_names: Iterable[str] = '*'):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        return await asyncio.to_thread(self.client.insert, table, data, column_names=column_names)

    async def insert_log(self, log_entry, table_name: str):
        """Insert a log entry into ClickHouse."""
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        
        # Convert log entry to appropriate format for insertion
        data = [[
            log_entry.trace_id,
            log_entry.span_id,
            log_entry.event,
            json.dumps(log_entry.data) if isinstance(log_entry.data, dict) else str(log_entry.data),
            log_entry.source,
            log_entry.user_id
        ]]
        
        column_names = ['trace_id', 'span_id', 'event', 'data', 'source', 'user_id']
        
        await self.insert_data(table_name, data, column_names=column_names)

    async def disconnect(self):
        if self.client:
            await asyncio.to_thread(self.client.close)
            self.client = None
