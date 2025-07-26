# v2/app/main_v2_5.py
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes import auth, supply, analysis
from app.db.clickhouse import ClickHouseClient
from app.db.models_clickhouse import SUPPLY_TABLE_SCHEMA, LOGS_TABLE_SCHEMA
from app.config import settings
from app.logging_config_custom.logger import logger
from app.logging_config_custom.clickhouse_logger import ClickHouseLogHandler

def setup_logging():
    """Initializes the application's logging configuration."""
    logger.setup_logging(level=settings.LOG_LEVEL, log_file_path=settings.LOG_FILE_PATH)
    logger.info("Logging configured.")

def initialize_databases(app: FastAPI):
    """Initializes and connects to PostgreSQL and ClickHouse."""
    # Initialize PostgreSQL
    # TBD

    # Initialize and connect to ClickHouse
    ch_client = ClickHouseClient(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        database=settings.CLICKHOUSE_DATABASE,
        user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD
    )
    logger.info(f"Connecting to ClickHouse at {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}")
    try:
        ch_client.connect()
        logger.info("ClickHouse connected.")
        # Create tables if they don't exist
        ch_client.create_table_if_not_exists(SUPPLY_TABLE_SCHEMA)
        ch_client.create_table_if_not_exists(LOGS_TABLE_SCHEMA)
        app.state.clickhouse_client = ch_client

        # Add the ClickHouse handler to the root logger for the application
        ch_handler = ClickHouseLogHandler(client=ch_client)
        logging.getLogger("netra-core").addHandler(ch_handler)
        logger.info("ClickHouse logging handler initialized.")

    except Exception as e:
        logger.error(f"Failed to connect or setup ClickHouse: {e}", exc_info=True)
        # Re-raise the exception to prevent the application from starting in a bad state
        raise

def shutdown_resources(app: FastAPI):
    """Gracefully disconnects from all databases."""
    logger.info("Shutting down resources...")
    if hasattr(app.state, 'clickhouse_client') and app.state.clickhouse_client.is_connected():
        app.state.clickhouse_client.disconnect()
        logger.info("ClickHouse disconnected.")
    Database.close()
    logger.info("Postgres connection closed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # Startup
    setup_logging()
    logger.info("Application startup...")

    if settings.app_env != "development":
        initialize_databases(app)
    
    yield
    
    # Shutdown
    logger.info("Application shutdown...")
    shutdown_resources(app)


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(supply.router, prefix="/supply", tags=["supply"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])


@app.get("/")
def read_root():
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API v2"}
