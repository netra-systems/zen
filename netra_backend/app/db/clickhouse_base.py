import asyncio
import json
from typing import Any, Dict, Iterable, List

import clickhouse_connect
from clickhouse_connect.driver.client import Client
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ClickHouseDatabase:
    """
    A client for interacting with a ClickHouse database.
    It handles connection, disconnection, and data operations.
    """
    def _validate_connection_parameters(self, host: str, port: int, database: str, user: str, password: str):
        """Validate ClickHouse connection parameters for control characters and format."""
        # Check for control characters in string parameters
        string_params = {"host": host, "database": database, "user": user, "password": password}
        
        for param_name, param_value in string_params.items():
            if not isinstance(param_value, str):
                continue
                
            # Check for control characters (ASCII 0-31 and 127)
            for i, char in enumerate(param_value):
                if ord(char) < 32 or ord(char) == 127:
                    char_name = {
                        '\n': 'newline',
                        '\r': 'carriage return', 
                        '\t': 'tab'
                    }.get(char, f'control character (ASCII {ord(char)})')
                    raise ValueError(f"ClickHouse {param_name} contains {char_name} at position {i}: {repr(param_value)}")
        
        # Validate port range
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"ClickHouse port must be integer between 1-65535, got: {port}")
        
        # Validate host format
        if not host or not host.strip():
            raise ValueError("ClickHouse host cannot be empty")
    
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
        # Validate parameters first
        self._validate_connection_parameters(host, port, database, user, password)
        self._set_connection_details(host, port, database, user, password, secure)
        self._initialize_client_state()
    
    def _create_client_connection(self):
        """Create ClickHouse client connection with environment-aware timeouts."""
        from shared.isolated_environment import get_env
        
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        # CRITICAL FIX: Increase timeouts for staging to prevent connection failures
        if environment == "staging":
            connect_timeout = 15   # Increased from 3 to 15 seconds for staging
            receive_timeout = 30   # Increased from 5 to 30 seconds for staging
        elif environment == "production":
            connect_timeout = 20   # Increased timeout for production
            receive_timeout = 45   # Increased timeout for production
        else:
            connect_timeout = 3    # Fast timeout for development
            receive_timeout = 5    # Fast timeout for development
        
        return clickhouse_connect.get_client(
            host=self.host, port=self.port, database=self.database,
            username=self.user, password=self.password, secure=self.secure,
            connect_timeout=connect_timeout, send_receive_timeout=receive_timeout
        )
    
    def _establish_connection(self):
        """Establish and test ClickHouse connection with timeout protection."""
        import time
        from shared.isolated_environment import get_env
        
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        try:
            # CRITICAL FIX: Track connection time for better error reporting
            start_time = time.time()
            self.client = self._create_client_connection()
            
            # Test connection with ping
            self.client.ping()
            
            connection_time = time.time() - start_time
            if connection_time > 5.0:  # Log slow connections
                from netra_backend.app.logging_config import central_logger
                logger = central_logger.get_logger(__name__)
                logger.warning(f"[ClickHouse] Slow connection established in {connection_time:.2f}s")
                
        except Exception as e:
            self.client = None
            
            # CRITICAL FIX: Enhanced error message with environment context
            error_msg = f"Could not connect to ClickHouse in {environment} environment: {e}"
            
            # Check for specific timeout/connection errors
            if any(keyword in str(e).lower() for keyword in ['timeout', 'refused', 'unreachable', 'network']):
                if environment in ["staging", "development"]:
                    error_msg += " (ClickHouse infrastructure may not be available in this environment)"
            
            raise ConnectionError(error_msg) from e
    
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
        """Test if the ClickHouse connection is working with environment-aware timeout."""
        import asyncio
        from shared.isolated_environment import get_env
        
        try:
            if not self.client:
                return False
                
            # CRITICAL FIX: Environment-aware test timeout
            environment = get_env().get("ENVIRONMENT", "development").lower()
            if environment == "staging":
                timeout = 10.0  # Longer timeout for staging
            elif environment == "production":
                timeout = 15.0  # Longest timeout for production
            else:
                timeout = 5.0   # Standard timeout for development
                
            return await asyncio.wait_for(self._execute_connection_test_query(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"ClickHouse connection test timeout after {timeout}s")
            return False
        except Exception as e:
            logger.warning(f"ClickHouse connection test failed: {e}")
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
