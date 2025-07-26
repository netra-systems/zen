import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes import auth, supply, analysis
from app.db.database import Database
from app.db.clickhouse import ClickHouseClient
from app.db.models_clickhouse import SUPPLY_TABLE_SCHEMA, LOGS_TABLE_SCHEMA
from app.config import settings
from app.logging.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.setup_logging(level=settings.LOG_LEVEL, log_file_path=settings.LOG_FILE_PATH)
    logger.info("Application startup...")

    # Initialize databases
    Database.initialize(settings.DATABASE_URL)
    logger.info("Postgres initialized.")

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
    except Exception as e:
        logger.error(f"Failed to connect or setup ClickHouse: {e}", exc_info=True)
        # Depending on the application's requirements, you might want to exit here
        # raise

    yield

    # Shutdown
    logger.info("Application shutdown...")
    if hasattr(app.state, 'clickhouse_client') and app.state.clickhouse_client.is_connected():
        app.state.clickhouse_client.disconnect()
        logger.info("ClickHouse disconnected.")
    Database.close()
    logger.info("Postgres connection closed.")


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(supply.router, prefix="/supply", tags=["supply"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])


@app.get("/")
def read_root():
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API v2"}
