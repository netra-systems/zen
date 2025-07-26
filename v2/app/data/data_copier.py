# /v2/app/data/data_copier.py
import logging
from typing import Dict, Tuple
from clickhouse_driver import Client

class DataCopier:
    """
    Handles the connection to source/destination ClickHouse instances and manages data transfer.
    """
    def __init__(self, source_creds: Dict, dest_creds: Dict, customer_id: str):
        self.source_creds = source_creds
        self.dest_creds = dest_creds
        self.customer_id = customer_id
        # Use a context manager for connections if possible, or ensure disconnection.
        self.source_client = Client(**source_creds)
        self.dest_client = Client(**dest_creds)
        logging.info("DataCopier initialized and clients connected.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.source_client.disconnect()
        self.dest_client.disconnect()
        logging.info("DataCopier clients disconnected.")

    def _get_table_schema(self, table_name: str) -> str:
        """Retrieves the CREATE TABLE statement for a given table."""
        logging.info(f"Fetching schema for source table: {table_name}")
        try:
            query = f"SHOW CREATE TABLE `{self.source_creds['database']}`.`{table_name}`"
            schema_query_result = self.source_client.execute(query)
            if not schema_query_result or not schema_query_result[0]:
                raise RuntimeError(f"Could not retrieve schema for table {table_name}.")
            return schema_query_result[0][0]
        except Exception as e:
            logging.error(f"Failed to get table schema: {e}", exc_info=True)
            raise

    def _create_isolated_environment(self, source_schema: str, source_table_name: str) -> Tuple[str, str]:
        """Creates a new, isolated database and table for the customer in the destination."""
        dest_db = f"customer_{self.customer_id.replace('-', '_')}" # Sanitize user ID for DB name
        dest_table = f"{source_table_name}_copy"

        logging.info(f"Creating isolated database (if not exists): {dest_db}")
        self.dest_client.execute(f"CREATE DATABASE IF NOT EXISTS {dest_db}")

        # Modify the schema to point to the new database and table
        modified_schema = source_schema.replace(f"TABLE `{self.source_creds['database']}`.`{source_table_name}`", f"TABLE `{dest_db}`.`{dest_table}`")
        
        logging.info(f"Dropping destination table if it exists: `{dest_db}`.`{dest_table}`")
        self.dest_client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{dest_table}`")

        logging.info(f"Creating destination table: `{dest_db}`.`{dest_table}`")
        self.dest_client.execute(modified_schema)
        
        return dest_db, dest_table

    def copy_data(self, source_table_name: str) -> Tuple[str, str]:
        """
        Copies data from the source table to a new destination table using the remote() function.
        """
        source_schema = self._get_table_schema(source_table_name)
        dest_db, dest_table = self._create_isolated_environment(source_schema, source_table_name)

        logging.info("Starting data transfer using remote() function...")
        
        insert_query = f"""
        INSERT INTO `{dest_db}`.`{dest_table}`
        SELECT * FROM remote(
            '{self.source_creds['host']}:{self.source_creds['port']}', 
            `{self.source_creds['database']}`.`{source_table_name}`, 
            '{self.source_creds['user']}', 
            '{self.source_creds.get('password', '')}'
        )
        """
        try:
            self.dest_client.execute(insert_query)
            logging.info("Data transfer via remote() completed successfully.")
        except Exception as e:
            logging.error(f"Error during remote() data transfer: {e}", exc_info=True)
            raise

        return dest_db, dest_table
