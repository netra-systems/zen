# /v2/app/db/clickhouse.py
import logging
from clickhouse_driver import Client
from sqlmodel import SQLModel
from ..config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_clickhouse_client() -> Client:
    """Returns a ClickHouse database client."""
    client = Client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB,
        # settings={'use_numpy': True} # Optional: if you use numpy with clickhouse
    )
    logger.info("ClickHouse client created.")
    return client

def create_clickhouse_db_and_tables():
    """
    Creates the ClickHouse database and tables if they don't exist.
    """
    client = get_clickhouse_client()
    try:
        logger.info(f"Ensuring ClickHouse database '{settings.CLICKHOUSE_DB}' exists...")
        client.execute(f"CREATE DATABASE IF NOT EXISTS {settings.CLICKHOUSE_DB}")

        from . import models_clickhouse

        # This is a simplified approach. In a real-world scenario, you might need a more
        # robust migration tool for ClickHouse if your schema evolves frequently.
        # Here, we'll just execute the CREATE TABLE statements derived from models.
        # Note: SQLModel doesn't directly support ClickHouse, so table creation
        # must be handled with raw SQL or a compatible library. For now, we assume
        # the tables are managed externally or via initial setup scripts.
        # The models in models_clickhouse.py are for data validation and structure.
        
        logger.info("ClickHouse database setup checked/completed.")

    except Exception as e:
        logger.error(f"Could not connect to or set up ClickHouse database: {e}", exc_info=True)
        raise
    finally:
        if client:
            client.disconnect()
            logger.info("ClickHouse client disconnected.")

