import clickhouse_connect
from clickhouse_connect.driver.client import Client
from typing import List, Dict, Any

from app.logging_config_custom.logger import logger, Log
from ..config import settings

# TBD better difference between "Connect" and "Driver"

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

    def connect(self):
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
            # Raise a specific error to be handled by the application startup logic.
            raise ConnectionError("Could not connect to ClickHouse") from e

    def disconnect(self):
        """Closes the connection to the ClickHouse server."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("ClickHouse connection closed.")

    def is_connected(self) -> bool:
        """
        Checks if the client is initialized and can connect to the server.
        """
        if self.client is None:
            return False
        try:
            # The ping() method returns True on success or raises an exception on failure.
            return self.client.ping()
        except Exception:
            return False

    def command(self, schema: str):
        """Executes a command."""
        if not self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.command(schema)
            logger.info(f"Schema executed successfully.")
        except Exception as e:
            logger.error(f"Could not execute schema '{schema[:50]}...': {e}", exc_info=True)
            raise

    def insert_data(self, table: str, data: List[List[Any]], column_names: List[str]):
        """Inserts a list of rows into the specified table."""
        if not self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.insert(table, data, column_names=column_names)
            logger.info(f"Inserted {len(data)} rows into table '{table}'.")
        except Exception as e:
            logger.error(f"Failed to insert data into table '{table}': {e}", exc_info=True)
            raise

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a read-only query and returns the result as a list of dicts."""
        if not self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            result = self.client.query(query)
            # Return results as a list of dictionaries for easier use.
            return [dict(zip(result.column_names, row)) for row in result.result_rows]
        except Exception as e:
            logger.error(f"Failed to execute query '{query}': {e}", exc_info=True)
            raise

from contextlib import contextmanager

@contextmanager
def get_clickhouse_client():
    """
    Dependency provider for the ClickHouse client.
    Instantiates the client with settings and attempts to connect.
    This function will be called by FastAPI for routes that need a ClickHouse connection.
    """
    client = ClickHouseClient(
        host=settings.clickhouse_https.host,
        port=settings.clickhouse_https.port,
        user=settings.clickhouse_https.user,
        password=settings.clickhouse_https.password,
        database=settings.clickhouse_https.database,
    )
    client.connect()
    try:
        yield client
    finally:
        client.disconnect()