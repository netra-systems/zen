import logging

# --- PostgreSQL Imports ---
# Import and alias from the postgres module to avoid name conflicts.
# This makes database.py the single, consistent source for DB components.
from .postgres import (
    engine as postgres_engine,
    Base as PostgresBase,
    SessionLocal as PostgresSessionLocal,
    create_postgres_db_and_tables,
)

# --- ClickHouse Imports ---
# Import and alias from the clickhouse module.
from .clickhouse import (
    engine as clickhouse_engine,
    Base as ClickHouseBase,
    SessionLocal as ClickHouseSessionLocal,
    create_clickhouse_db_and_tables,
)

# --- Exports for Application-wide Use ---
# Re-export the main components so other parts of the application (like main.py)
# can import them from this central module.
engine = postgres_engine
Base = PostgresBase
# clickhouse_engine and ClickHouseBase are already correctly named from the import.

# --- Dependency Providers for FastAPI ---

def get_db():
    """
    FastAPI dependency that provides a PostgreSQL database session.
    It ensures the session is properly closed after the request is handled.
    """
    if PostgresSessionLocal is None:
        logging.error("PostgreSQL session is not available. Connection may have failed at startup.")
        # The calling endpoint will receive an error.
        return

    db = PostgresSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_clickhouse_db():
    """
    FastAPI dependency that provides a ClickHouse database session.
    It ensures the session is properly closed after the request is handled.
    """
    if ClickHouseSessionLocal is None:
        logging.error("ClickHouse session is not available. Connection may have failed at startup.")
        return

    db = ClickHouseSessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Utility Functions ---

def create_all_tables():
    """
    A utility function to create all tables in both databases.
    This is useful for initial application setup or for testing.
    """
    logging.info("Attempting to create tables for all configured databases...")
    create_postgres_db_and_tables()
    create_clickhouse_db_and_tables()
