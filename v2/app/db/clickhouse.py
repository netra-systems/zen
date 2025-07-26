import clickhouse_connect
from clickhouse_connect.driver.client import Client
from typing import List, Dict, Any

from app.logging_config_custom.logger import logger, Log
from ..config import settings, IS_SCHEMA_GENERATION

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
        In schema generation mode, this step is skipped to avoid errors.
        """
        # If running to generate OpenAPI schema, do not attempt to connect.
        if IS_SCHEMA_GENERATION:
            logger.info("Skipping ClickHouse connection in schema generation mode.")
            return

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
        """Checks if the client is connected and the connection is open."""
        return self.client is not None and self.client.is_open

    def create_table_if_not_exists(self, table_schema: str):
        """Executes a CREATE TABLE IF NOT EXISTS command."""
        if not self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.command(table_schema)
            logger.info(f"Table schema executed successfully.")
        except Exception as e:
            logger.error(f"Could not create table with schema '{table_schema[:50]}...': {e}", exc_info=True)
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

# Dependency function for FastAPI
def get_clickhouse_client():
    """
    Dependency provider for the ClickHouse client.
    Instantiates the client with settings and attempts to connect.
    This function will be called by FastAPI for routes that need a ClickHouse connection.
    """
    client = ClickHouseClient(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db,
    )
    # The connect call is now safe during schema generation.
    client.connect()
    try:
        yield client
    finally:
        client.disconnect()