"""
ClickHouse Connection Manager for Analytics Service

Provides connection pooling, health checks, retry logic, and query execution methods
for ClickHouse integration. Complete isolation from other services.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
import json
from datetime import datetime, timedelta

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError, NetworkError, ServerException


logger = logging.getLogger(__name__)


class ClickHouseConnectionError(Exception):
    """Raised when ClickHouse connection fails"""
    pass


class ClickHouseQueryError(Exception):
    """Raised when ClickHouse query execution fails"""
    pass


class ClickHouseManager:
    """
    ClickHouse connection manager with connection pooling, health checks,
    and retry logic for the analytics service.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9000,
        database: str = "analytics",
        user: str = "default",
        password: str = "",
        max_connections: int = 10,
        connection_timeout: int = 10,
        query_timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        health_check_interval: int = 60
    ):
        """
        Initialize ClickHouse connection manager.
        
        Args:
            host: ClickHouse server host
            port: ClickHouse server port
            database: Database name
            user: Username for authentication
            password: Password for authentication
            max_connections: Maximum number of connections in pool
            connection_timeout: Connection timeout in seconds
            query_timeout: Query timeout in seconds
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Base delay between retries in seconds
            health_check_interval: Health check interval in seconds
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_check_interval = health_check_interval
        
        self._connection_pool: List[Client] = []
        self._pool_lock = asyncio.Lock()
        self._is_initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._last_health_check = 0
        self._is_healthy = False
        
        # Connection settings
        self._connection_settings = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'connect_timeout': self.connection_timeout,
            'send_receive_timeout': self.query_timeout,
            'secure': False,  # Set to True for HTTPS connections
            'compression': True,
            'settings': {
                'max_execution_time': self.query_timeout,
                'max_memory_usage': '2GB',
                'readonly': 0,
            }
        }
    
    async def initialize(self) -> None:
        """Initialize the connection manager and create initial connections."""
        if self._is_initialized:
            return
            
        logger.info(f"Initializing ClickHouse connection manager for {self.host}:{self.port}")
        
        try:
            # Test connection
            await self._test_connection()
            
            # Initialize connection pool
            await self._initialize_pool()
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._is_initialized = True
            self._is_healthy = True
            
            logger.info("ClickHouse connection manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse connection manager: {e}")
            raise ClickHouseConnectionError(f"Failed to initialize ClickHouse: {e}") from e
    
    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        logger.info("Closing ClickHouse connection manager")
        
        # Stop health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._pool_lock:
            while self._connection_pool:
                client = self._connection_pool.pop()
                try:
                    client.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing ClickHouse connection: {e}")
        
        self._is_initialized = False
        self._is_healthy = False
        
        logger.info("ClickHouse connection manager closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a connection from the pool.
        
        Yields:
            Client: ClickHouse client connection
            
        Raises:
            ClickHouseConnectionError: If no healthy connection available
        """
        if not self._is_initialized:
            await self.initialize()
            
        if not self._is_healthy:
            raise ClickHouseConnectionError("ClickHouse connection manager is not healthy")
        
        client = None
        
        try:
            async with self._pool_lock:
                if self._connection_pool:
                    client = self._connection_pool.pop()
                else:
                    client = self._create_client()
            
            # Test connection before yielding
            await self._test_client(client)
            
            yield client
            
        except Exception as e:
            # If there was an error, don't return the client to the pool
            if client:
                try:
                    client.disconnect()
                except:
                    pass
            raise
            
        finally:
            # Return client to pool if it's still healthy
            if client:
                try:
                    async with self._pool_lock:
                        if len(self._connection_pool) < self.max_connections:
                            self._connection_pool.append(client)
                        else:
                            client.disconnect()
                except Exception as e:
                    logger.warning(f"Error returning client to pool: {e}")
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        with_column_types: bool = False
    ) -> List[Any]:
        """
        Execute a SELECT query with retry logic.
        
        Args:
            query: SQL query string
            parameters: Query parameters
            with_column_types: Whether to return column type information
            
        Returns:
            List of query results
            
        Raises:
            ClickHouseQueryError: If query execution fails after retries
        """
        return await self._execute_with_retry(
            self._execute_select,
            query=query,
            parameters=parameters,
            with_column_types=with_column_types
        )
    
    async def execute_command(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Execute a non-SELECT command (INSERT, CREATE, etc.) with retry logic.
        
        Args:
            query: SQL command string
            parameters: Query parameters
            
        Returns:
            Number of affected rows
            
        Raises:
            ClickHouseQueryError: If command execution fails after retries
        """
        return await self._execute_with_retry(
            self._execute_command,
            query=query,
            parameters=parameters
        )
    
    async def insert_data(
        self,
        table: str,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None
    ) -> int:
        """
        Insert data into a table with optimized batch insertion.
        
        Args:
            table: Table name
            data: List of dictionaries with data to insert
            columns: Optional list of column names (inferred from data if not provided)
            
        Returns:
            Number of rows inserted
            
        Raises:
            ClickHouseQueryError: If insertion fails after retries
        """
        if not data:
            return 0
        
        # Infer columns from first record if not provided
        if columns is None:
            columns = list(data[0].keys())
        
        # Prepare data as tuples in column order
        rows = []
        for record in data:
            row = tuple(record.get(col) for col in columns)
            rows.append(row)
        
        return await self._execute_with_retry(
            self._insert_rows,
            table=table,
            columns=columns,
            rows=rows
        )
    
    async def create_table_if_not_exists(self, create_sql: str) -> None:
        """
        Create a table if it doesn't exist.
        
        Args:
            create_sql: CREATE TABLE SQL statement
            
        Raises:
            ClickHouseQueryError: If table creation fails
        """
        await self.execute_command(create_sql)
        logger.info("Table creation command executed successfully")
    
    async def get_table_info(self, table: str) -> Dict[str, Any]:
        """
        Get information about a table.
        
        Args:
            table: Table name
            
        Returns:
            Dictionary with table information
        """
        query = """
        SELECT 
            name,
            type,
            default_type,
            default_expression,
            comment
        FROM system.columns 
        WHERE database = %(database)s AND table = %(table)s
        ORDER BY position
        """
        
        result = await self.execute_query(
            query, 
            parameters={'database': self.database, 'table': table}
        )
        
        return {
            'columns': [
                {
                    'name': row[0],
                    'type': row[1],
                    'default_type': row[2],
                    'default_expression': row[3],
                    'comment': row[4]
                }
                for row in result
            ],
            'total_columns': len(result)
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the connection manager.
        
        Returns:
            Dictionary with health information
        """
        return {
            'is_healthy': self._is_healthy,
            'is_initialized': self._is_initialized,
            'last_health_check': self._last_health_check,
            'pool_size': len(self._connection_pool),
            'max_connections': self.max_connections,
            'host': self.host,
            'port': self.port,
            'database': self.database
        }
    
    # Private methods
    
    def _create_client(self) -> Client:
        """Create a new ClickHouse client connection."""
        try:
            client = Client(**self._connection_settings)
            return client
        except Exception as e:
            logger.error(f"Failed to create ClickHouse client: {e}")
            raise ClickHouseConnectionError(f"Failed to create client: {e}") from e
    
    async def _test_connection(self) -> None:
        """Test connection to ClickHouse server."""
        client = None
        try:
            client = self._create_client()
            await self._test_client(client)
            logger.info("ClickHouse connection test successful")
        finally:
            if client:
                try:
                    client.disconnect()
                except:
                    pass
    
    async def _test_client(self, client: Client) -> None:
        """Test a specific client connection."""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: client.execute("SELECT 1")
            )
            if result != [(1,)]:
                raise ClickHouseError("Unexpected test query result")
        except Exception as e:
            logger.error(f"ClickHouse client test failed: {e}")
            raise ClickHouseConnectionError(f"Client test failed: {e}") from e
    
    async def _initialize_pool(self) -> None:
        """Initialize the connection pool with initial connections."""
        async with self._pool_lock:
            initial_size = min(2, self.max_connections)  # Start with 2 connections
            for _ in range(initial_size):
                try:
                    client = self._create_client()
                    await self._test_client(client)
                    self._connection_pool.append(client)
                except Exception as e:
                    logger.warning(f"Failed to create initial connection: {e}")
        
        logger.info(f"Initialized connection pool with {len(self._connection_pool)} connections")
    
    async def _execute_select(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        with_column_types: bool = False
    ) -> List[Any]:
        """Execute a SELECT query."""
        async with self.get_connection() as client:
            try:
                loop = asyncio.get_event_loop()
                
                if parameters:
                    result = await loop.run_in_executor(
                        None,
                        lambda: client.execute(
                            query, 
                            parameters, 
                            with_column_types=with_column_types
                        )
                    )
                else:
                    result = await loop.run_in_executor(
                        None,
                        lambda: client.execute(query, with_column_types=with_column_types)
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise ClickHouseQueryError(f"Query failed: {e}") from e
    
    async def _execute_command(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute a non-SELECT command."""
        async with self.get_connection() as client:
            try:
                loop = asyncio.get_event_loop()
                
                if parameters:
                    result = await loop.run_in_executor(
                        None,
                        lambda: client.execute(query, parameters)
                    )
                else:
                    result = await loop.run_in_executor(
                        None,
                        lambda: client.execute(query)
                    )
                
                # For most commands, result is empty, return 1 for success
                return 1 if result == [] else len(result)
                
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise ClickHouseQueryError(f"Command failed: {e}") from e
    
    async def _insert_rows(
        self,
        table: str,
        columns: List[str],
        rows: List[tuple]
    ) -> int:
        """Insert rows into a table."""
        async with self.get_connection() as client:
            try:
                loop = asyncio.get_event_loop()
                
                result = await loop.run_in_executor(
                    None,
                    lambda: client.execute(
                        f"INSERT INTO {table} ({', '.join(columns)}) VALUES",
                        rows
                    )
                )
                
                return len(rows)
                
            except Exception as e:
                logger.error(f"Insert failed: {e}")
                raise ClickHouseQueryError(f"Insert failed: {e}") from e
    
    async def _execute_with_retry(self, func, **kwargs) -> Any:
        """Execute a function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(**kwargs)
                
            except (NetworkError, ServerException, ClickHouseConnectionError) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries + 1} attempts: {e}")
                    break
            
            except Exception as e:
                # For non-retryable errors, fail immediately
                logger.error(f"Non-retryable error: {e}")
                raise ClickHouseQueryError(f"Operation failed: {e}") from e
        
        # If we get here, all retries failed
        raise ClickHouseQueryError(f"Operation failed after retries: {last_exception}") from last_exception
    
    async def _health_check_loop(self) -> None:
        """Continuous health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                self._is_healthy = False
    
    async def _perform_health_check(self) -> None:
        """Perform a health check."""
        try:
            start_time = time.time()
            
            # Test connection with simple query
            result = await self.execute_query("SELECT 1")
            
            if result == [(1,)]:
                self._is_healthy = True
                self._last_health_check = start_time
                
                response_time = (time.time() - start_time) * 1000  # ms
                logger.debug(f"ClickHouse health check passed in {response_time:.2f}ms")
            else:
                raise ClickHouseError("Unexpected health check result")
                
        except Exception as e:
            self._is_healthy = False
            logger.warning(f"ClickHouse health check failed: {e}")