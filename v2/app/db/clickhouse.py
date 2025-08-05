import clickhouse_connect
from app.logging_config_custom.logger import app_logger as logger
from clickhouse_connect.driver.client import Client
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from app.logging_config_custom.logger import app_logger
from ..config import settings

class ClickHouseClient:
    """
    A client for interacting with a ClickHouse database.
    It handles connection, disconnection, and data operations.
    """
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.client: Client | None = None

    async def connect(self):
        """
        Establishes a connection to the ClickHouse server.
        """
        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                database=self.database,
                username=self.user,
                password=self.password
            )
            self.client.ping()
            logger.info(f"Successfully connected to ClickHouse at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}", exc_info=True)
            self.client = None
            raise ConnectionError("Could not connect to ClickHouse") from e

    async def disconnect(self):
        """Closes the connection to the ClickHouse server."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("ClickHouse connection closed.")

    async def is_connected(self) -> bool:
        """
        Checks if the client is initialized and can connect to the server.
        """
        if self.client is None:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False

    async def command(self, schema: str):
        """Executes a command."""
        if not await self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.command(schema)
            logger.info(f"Schema executed successfully.")
        except Exception as e:
            logger.error(f"Could not execute schema '{schema[:50]}...': {e}", exc_info=True)
            raise

    async def insert_data(self, table: str, data: List[List[Any]], column_names: List[str]):
        """Inserts a list of rows into the specified table."""
        if not await self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.insert(table, data, column_names=column_names)
            logger.info(f"Inserted {len(data)} rows into table '{table}'.")
        except Exception as e:
            logger.error(f"Failed to insert data into table '{table}': {e}", exc_info=True)
            raise

    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a read-only query and returns the result as a list of dicts."""
        if not await self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            result = self.client.query(query)
            return [dict(zip(result.column_names, row)) for row in result.result_rows]
        except Exception as e:
            logger.error(f"Failed to execute query '{query}': {e}", exc_info=True)
            raise

@asynccontextmanager
async def get_clickhouse_client():
    """
    Dependency provider for the ClickHouse client.
    Instantiates the client with settings and attempts to connect.
    This function will be called by FastAPI for routes that need a ClickHouse connection.
    """
    if settings.app_env == "development":
        config = settings.clickhouse_https_dev
    else:
        config = settings.clickhouse_https

    client = ClickHouseClient(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
    )
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()