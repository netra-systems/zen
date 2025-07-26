# /v2/app/database.py
import logging
from .postgres import create_postgres_db_and_tables, get_db_session
from .clickhouse import create_clickhouse_db_and_tables, get_clickhouse_client

def init_databases():
    """
    Initializes both PostgreSQL and ClickHouse databases and tables.
    """
    logging.info("Initializing all databases...")
    create_postgres_db_and_tables()
    # ClickHouse table creation is handled differently, but we check the connection.
    create_clickhouse_db_and_tables()
    logging.info("All databases initialized.")

# Expose the session getter for FastAPI dependency injection
get_db = get_db_session
get_ch_client = get_clickhouse_client
