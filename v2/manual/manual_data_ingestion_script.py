# app/manual_data_ingestion_script.py

import json
import logging
from typing import Dict
from clickhouse_driver import Client

logger = logging.getLogger(__name__)

class DataIngestor:
    def __init__(self, clickhouse_creds: Dict, table_name: str, table_schema: Dict):
        self.clickhouse_creds = clickhouse_creds
        self.table_name = table_name
        self.table_schema = table_schema
        self.client = Client(**clickhouse_creds)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.disconnect()

    def create_table_if_not_exists(self):
        """Creates the table in ClickHouse if it doesn't exist."""
        logging.info(f"Creating table {self.table_name} if it does not exist.")
        create_table_query = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join([f'{k} {v}' for k, v in self.table_schema.items()])}) ENGINE = MergeTree() ORDER BY (timestamp_utc)"
        self.client.execute(create_table_query)

    def ingest_data(self, data_path: str):
        """Ingests data from a JSON file into the ClickHouse table."""
        logging.info(f"Ingesting data from {data_path} into {self.table_name}.")
        with open(data_path, 'r') as f:
            data = json.load(f)
        self.client.execute(f"INSERT INTO {self.table_name} VALUES", data)
        logging.info("Data ingestion completed successfully.")