# app/data/data_copier.py
import logging
from typing import Dict, Tuple, Optional, Any
from clickhouse_driver import Client
from ..config import settings
# For using remote() copy between clickhouse the driver is better then connect it seems.
from sqlmodel import Session
from ..db.models_postgres import SupplyOption
from ..db.models_clickhouse import SUPPLY_TABLE_NAME

# TBD if this should use clickhouse driver or connect


class DataCopier:
    """
    Handles the connection to source/destination ClickHouse instances and manages data transfer.
    """
    def __init__(self, customer_id: str) -> None:
        self.source_creds = settings.clickhouse_native.model_dump()
        self.dest_creds = settings.clickhouse_native.model_dump()
        self.customer_id = customer_id
        # Use a context manager for connections if possible, or ensure disconnection.
        self.source_client = Client(**self.source_creds)
        self.dest_client = Client(**self.dest_creds)
        logging.info("DataCopier initialized and clients connected.")

    def __enter__(self) -> 'DataCopier':
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.source_client.disconnect()
        self.dest_client.disconnect()
        logging.info("DataCopier clients disconnected.")

    def _execute_schema_query(self, table_name: str) -> list:
        """Execute schema query and return results."""
        query = f"SHOW CREATE TABLE `{self.source_creds['database']}`.`{table_name}`"
        schema_query_result = self.source_client.execute(query)
        if not schema_query_result or not schema_query_result[0]:
            raise RuntimeError(f"Could not retrieve schema for table {table_name}.")
        return schema_query_result

    def _handle_schema_retrieval_error(self, e: Exception, table_name: str) -> None:
        """Handle schema retrieval errors with logging."""
        logging.error(f"Failed to get table schema: {e}", exc_info=True)
        raise

    def _get_table_schema(self, table_name: str) -> str:
        """Retrieves the CREATE TABLE statement for a given table."""
        logging.info(f"Fetching schema for source table: {table_name}")
        try:
            schema_query_result = self._execute_schema_query(table_name)
            return schema_query_result[0][0]
        except Exception as e:
            self._handle_schema_retrieval_error(e, table_name)

    def _setup_destination_names(self, source_table_name: str) -> Tuple[str, str]:
        """Setup destination database and table names."""
        dest_db = f"customer_{self.customer_id.replace('-', '_')}" # Sanitize user ID for DB name
        dest_table = f"{source_table_name}_copy"
        return dest_db, dest_table

    def _create_destination_database(self, dest_db: str) -> None:
        """Create destination database if it doesn't exist."""
        logging.info(f"Creating isolated database (if not exists): {dest_db}")
        self.dest_client.execute(f"CREATE DATABASE IF NOT EXISTS {dest_db}")

    def _modify_schema_for_destination(self, source_schema: str, source_table_name: str, dest_db: str, dest_table: str) -> str:
        """Modify schema to point to destination database and table."""
        return source_schema.replace(
            f"TABLE `{self.source_creds['database']}`.`{source_table_name}`", 
            f"TABLE `{dest_db}`.`{dest_table}`"
        )

    def _create_destination_table(self, dest_db: str, dest_table: str, modified_schema: str) -> None:
        """Drop existing table and create new destination table."""
        logging.info(f"Dropping destination table if it exists: `{dest_db}`.`{dest_table}`")
        self.dest_client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{dest_table}`")
        logging.info(f"Creating destination table: `{dest_db}`.`{dest_table}`")
        self.dest_client.execute(modified_schema)

    def _create_isolated_environment(self, source_schema: str, source_table_name: str) -> Tuple[str, str]:
        """Creates a new, isolated database and table for the customer in the destination."""
        dest_db, dest_table = self._setup_destination_names(source_table_name)
        self._create_destination_database(dest_db)
        modified_schema = self._modify_schema_for_destination(source_schema, source_table_name, dest_db, dest_table)
        self._create_destination_table(dest_db, dest_table, modified_schema)
        return dest_db, dest_table

    def _get_remote_connection_params(self, source_table_name: str) -> tuple:
        """Get remote connection parameters for query building."""
        host_port = f"{self.source_creds['host']}:{self.source_creds['port']}"
        database_table = f"`{self.source_creds['database']}`.`{source_table_name}`"
        user = self.source_creds['user']
        password = self.source_creds.get('password', '')
        return host_port, database_table, user, password

    def _build_remote_insert_query(self, source_table_name: str, dest_db: str, dest_table: str) -> str:
        """Build remote insert query for data transfer."""
        host_port, database_table, user, password = self._get_remote_connection_params(source_table_name)
        return f"""
        INSERT INTO `{dest_db}`.`{dest_table}`
        SELECT * FROM remote(
            '{host_port}', 
            {database_table}, 
            '{user}', 
            '{password}'
        )
        """

    def _execute_data_transfer(self, insert_query: str) -> None:
        """Execute data transfer with error handling."""
        try:
            self.dest_client.execute(insert_query)
            logging.info("Data transfer via remote() completed successfully.")
        except Exception as e:
            logging.error(f"Error during remote() data transfer: {e}", exc_info=True)
            raise

    def copy_data(self, source_table_name: str) -> Tuple[str, str]:
        """Copies data from the source table to a new destination table using the remote() function."""
        source_schema = self._get_table_schema(source_table_name)
        dest_db, dest_table = self._create_isolated_environment(source_schema, source_table_name)
        logging.info("Starting data transfer using remote() function...")
        insert_query = self._build_remote_insert_query(source_table_name, dest_db, dest_table)
        self._execute_data_transfer(insert_query)
        return dest_db, dest_table
