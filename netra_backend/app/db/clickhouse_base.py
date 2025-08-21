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
    def _set_connection_details(self, host: str, port: int, database: str, user: str, password: str, secure: bool):
        """Set basic connection details."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.secure = secure
    
    def _initialize_client_state(self):
        """Initialize client state."""
        self.client: Client | None = None
    
    def _initialize_connection_params(self, host: str, port: int, database: str, user: str, password: str, secure: bool):
        """Initialize ClickHouse connection parameters."""
        self._set_connection_details(host, port, database, user, password, secure)
        self._initialize_client_state()
    
    def _create_client_connection(self):
        """Create ClickHouse client connection with timeouts."""
        return clickhouse_connect.get_client(
            host=self.host, port=self.port, database=self.database,
            user=self.user, password=self.password, secure=self.secure,
            connect_timeout=10, send_receive_timeout=30
        )
    
    def _establish_connection(self):
        """Establish and test ClickHouse connection."""
        try:
            self.client = self._create_client_connection()
            self.client.ping()
        except Exception as e:
            self.client = None
            raise ConnectionError(f"Could not connect to ClickHouse: {e}") from e
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str, secure: bool = False):
        self._initialize_connection_params(host, port, database, user, password, secure)
        self._establish_connection()

    def ping(self):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.ping()
            return True
        except Exception as e:
            return False

    async def _execute_connection_test_query(self) -> bool:
        """Execute connection test query."""
        await self.execute_query("SELECT 1")
        return True

    async def test_connection(self) -> bool:
        """Test if the ClickHouse connection is working."""
        try:
            if not self.client:
                return False
            return await self._execute_connection_test_query()
        except Exception:
            return False

    async def command(self, cmd: str, parameters: Dict[str, Any] | None = None, settings: Dict[str, Any] | None = None):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        return await asyncio.to_thread(self.client.command, cmd, parameters=parameters, settings=settings)

    def _execute_sync_query(self, query: str, parameters: Dict[str, Any] | None, settings: Dict[str, Any] | None):
        """Execute synchronous query and return named results."""
        result = self.client.query(query, parameters=parameters, settings=settings)
        return list(result.named_results())
    
    async def execute_query(self, query: str, parameters: Dict[str, Any] | None = None, settings: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        return await asyncio.to_thread(self._execute_sync_query, query, parameters, settings)
    
    async def execute(self, query: str, parameters: Dict[str, Any] | None = None, settings: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Alias for execute_query to maintain compatibility with different interfaces."""
        return await self.execute_query(query, parameters, settings)

    async def insert_data(self, table: str, data: List[List[Any]], column_names: Iterable[str] = '*'):
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        return await asyncio.to_thread(self.client.insert, table, data, column_names=column_names)

    def _prepare_log_data(self, log_entry):
        """Prepare log entry data for ClickHouse insertion."""
        data_value = (json.dumps(log_entry.data) 
                     if isinstance(log_entry.data, dict) 
                     else str(log_entry.data))
        return [[log_entry.trace_id, log_entry.span_id, log_entry.event,
                data_value, log_entry.source, log_entry.user_id]]
    
    def _get_log_column_names(self):
        """Get column names for log table insertion."""
        return ['trace_id', 'span_id', 'event', 'data', 'source', 'user_id']
    
    async def _execute_log_insertion(self, table_name: str, data, column_names):
        """Execute the actual log insertion."""
        await self.insert_data(table_name, data, column_names=column_names)
    
    async def insert_log(self, log_entry, table_name: str):
        """Insert a log entry into ClickHouse."""
        if not self.client:
            raise ConnectionError("Not connected to ClickHouse.")
        data = self._prepare_log_data(log_entry)
        column_names = self._get_log_column_names()
        await self._execute_log_insertion(table_name, data, column_names)

    async def disconnect(self):
        if self.client:
            await asyncio.to_thread(self.client.close)
            self.client = None
