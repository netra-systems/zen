import clickhouse_connect
from clickhouse_connect.driver.client import Client
from typing import List, Dict, Any

from app.logging.logger import logger, Log


class ClickHouseClient:
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.client: Client | None = None

    def connect(self):
        """Establishes a connection to the ClickHouse server."""
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

    def disconnect(self):
        """Closes the connection to the ClickHouse server."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("ClickHouse connection closed.")

    def is_connected(self) -> bool:
        """Checks if the client is connected."""
        return self.client is not None and self.client.is_open

    def create_table_if_not_exists(self, table_schema: str):
        """Executes a CREATE TABLE IF NOT EXISTS command."""
        if not self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            self.client.command(table_schema)
            # We can't easily get the table name from the schema string here, so logging is generic.
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

    def insert_log(self, log_entry: Log):
        """Inserts a single log entry into the logs table."""
        if not self.is_connected():
            # Use standard logger here to avoid recursive logging issues
            import logging
            logging.getLogger().error("CRITICAL: Cannot write log to ClickHouse, client not connected.")
            return

        from .models_clickhouse import LOGS_TABLE_NAME
        try:
            log_dict = log_entry.to_dict()
            # The extra field needs to be a map of strings
            log_dict['extra'] = {k: str(v) for k, v in log_dict.get('extra', {}).items()}

            column_names = [
                'request_id', 'timestamp', 'level', 'message', 'module',
                'function', 'line_no', 'process_name', 'thread_name', 'extra'
            ]
            
            row = [log_dict.get(name) for name in column_names]
            self.client.insert(LOGS_TABLE_NAME, [row], column_names=column_names)

        except Exception as e:
            # Use the standard logger here to avoid recursive logging issues
            import logging
            logging.getLogger().error(f"CRITICAL: Could not write log to ClickHouse: {e}", exc_info=True)

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a read-only query and returns the result."""
        if not self.is_connected():
            raise ConnectionError("Not connected to ClickHouse.")
        try:
            result = self.client.query(query)
            return [dict(zip(result.column_names, row)) for row in result.result_rows]
        except Exception as e:
            logger.error(f"Failed to execute query '{query}': {e}", exc_info=True)
            raise
