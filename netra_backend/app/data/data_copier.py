# app/data/data_copier.py
import logging
from typing import Any, Dict, Optional, Tuple

from netra_backend.app.db.clickhouse import get_clickhouse_client

# For using remote() copy between clickhouse the driver is better then connect it seems.
from sqlmodel import Session

from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.db.models_clickhouse import SUPPLY_TABLE_NAME
from netra_backend.app.db.models_postgres import SupplyOption

# TBD if this should use clickhouse driver or connect


class DataCopier:
    """
    Handles the connection to source/destination ClickHouse instances and manages data transfer.
    """
    def __init__(self, customer_id: str) -> None:
        self._setup_credentials(customer_id)
        self._initialize_clients()
        logging.info("DataCopier initialized and clients connected.")

    def _setup_credentials(self, customer_id: str) -> None:
        """Setup credentials and customer ID."""
        self.source_creds = settings.clickhouse_native.model_dump()
        self.dest_creds = settings.clickhouse_native.model_dump()
        self.customer_id = customer_id

    def _initialize_clients(self) -> None:
        """Initialize ClickHouse clients."""
        # Use a context manager for connections if possible, or ensure disconnection.
        self.source_client = Client(**self.source_creds)
        self.dest_client = Client(**self.dest_creds)

    def __enter__(self) -> 'DataCopier':
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self._disconnect_clients()
        logging.info("DataCopier clients disconnected.")

    def _disconnect_clients(self) -> None:
        """Disconnect all ClickHouse clients."""
        self.source_client.disconnect()
        self.dest_client.disconnect()

    def _execute_schema_query(self, table_name: str) -> list:
        """Execute schema query and return results."""
        query = self._build_schema_query(table_name)
        schema_query_result = self.source_client.execute(query)
        self._validate_schema_result(schema_query_result, table_name)
        return schema_query_result

    def _build_schema_query(self, table_name: str) -> str:
        """Build schema query string."""
        return f"SHOW CREATE TABLE `{self.source_creds['database']}`.`{table_name}`"

    def _validate_schema_result(self, result: list, table_name: str) -> None:
        """Validate schema query result."""
        if not result or not result[0]:
            raise RuntimeError(f"Could not retrieve schema for table {table_name}.")

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
            raise

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
        old_table_ref = f"TABLE `{self.source_creds['database']}`.`{source_table_name}`"
        new_table_ref = f"TABLE `{dest_db}`.`{dest_table}`"
        return source_schema.replace(old_table_ref, new_table_ref)

    def _create_destination_table(self, dest_db: str, dest_table: str, modified_schema: str) -> None:
        """Drop existing table and create new destination table."""
        self._drop_existing_table(dest_db, dest_table)
        self._create_new_table(dest_db, dest_table, modified_schema)

    def _drop_existing_table(self, dest_db: str, dest_table: str) -> None:
        """Drop existing destination table if it exists."""
        logging.info(f"Dropping destination table if it exists: `{dest_db}`.`{dest_table}`")
        self.dest_client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{dest_table}`")

    def _create_new_table(self, dest_db: str, dest_table: str, schema: str) -> None:
        """Create new destination table with schema."""
        logging.info(f"Creating destination table: `{dest_db}`.`{dest_table}`")
        self.dest_client.execute(schema)

    def _create_isolated_environment(self, source_schema: str, source_table_name: str) -> Tuple[str, str]:
        """Creates a new, isolated database and table for the customer in the destination."""
        dest_db, dest_table = self._setup_destination_names(source_table_name)
        self._create_destination_database(dest_db)
        modified_schema = self._modify_schema_for_destination(source_schema, source_table_name, dest_db, dest_table)
        self._create_destination_table(dest_db, dest_table, modified_schema)
        return dest_db, dest_table

    def _get_remote_connection_params(self, source_table_name: str) -> tuple:
        """Get remote connection parameters for query building."""
        host_port = self._build_host_port()
        database_table = self._build_database_table(source_table_name)
        user = self.source_creds['user']
        password = self.source_creds.get('password', '')
        return host_port, database_table, user, password

    def _build_host_port(self) -> str:
        """Build host:port string."""
        return f"{self.source_creds['host']}:{self.source_creds['port']}"

    def _build_database_table(self, table_name: str) -> str:
        """Build database.table reference."""
        return f"`{self.source_creds['database']}`.`{table_name}`"

    def _build_remote_insert_query(self, source_table_name: str, dest_db: str, dest_table: str) -> str:
        """Build remote insert query for data transfer."""
        connection_params = self._get_remote_connection_params(source_table_name)
        remote_clause = self._build_remote_clause(*connection_params)
        return self._create_insert_statement(dest_db, dest_table, remote_clause)
        
    def _build_remote_clause(self, host_port: str, database_table: str, user: str, password: str) -> str:
        """Build remote clause for query."""
        return f"remote('{host_port}', {database_table}, '{user}', '{password}')"
        
    def _create_insert_statement(self, dest_db: str, dest_table: str, remote_clause: str) -> str:
        """Create INSERT statement with remote source."""
        return f"INSERT INTO `{dest_db}`.`{dest_table}` SELECT * FROM {remote_clause}"

    def _execute_data_transfer(self, insert_query: str) -> None:
        """Execute data transfer with error handling."""
        try:
            self.dest_client.execute(insert_query)
            logging.info("Data transfer via remote() completed successfully.")
        except Exception as e:
            self._handle_transfer_error(e)

    def _handle_transfer_error(self, e: Exception) -> None:
        """Handle data transfer errors."""
        logging.error(f"Error during remote() data transfer: {e}", exc_info=True)
        raise

    def copy_data(self, source_table_name: str) -> Tuple[str, str]:
        """Copies data from the source table to a new destination table using the remote() function."""
        source_schema = self._get_table_schema(source_table_name)
        dest_db, dest_table = self._create_isolated_environment(source_schema, source_table_name)
        self._execute_copy_workflow(source_table_name, dest_db, dest_table)
        return dest_db, dest_table

    def _execute_copy_workflow(self, source_table_name: str, dest_db: str, dest_table: str) -> None:
        """Execute the data copy workflow."""
        logging.info("Starting data transfer using remote() function...")
        insert_query = self._build_remote_insert_query(source_table_name, dest_db, dest_table)
        self._execute_data_transfer(insert_query)
