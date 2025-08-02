# v2/app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.routes import auth, supply, analysis, v3, generation
from app.db.postgres import Database
from app.db.clickhouse import ClickHouseClient
from app.db.models_clickhouse import SUPPLY_TABLE_SCHEMA, LOGS_TABLE_SCHEMA
from app.config import settings
from app.logging_config_custom.logger import logger
from app.logging_config_custom.clickhouse_logger import ClickHouseLogHandler

def setup_logging():
    """Initializes the application's logging configuration."""
    logger.configure(level=settings.log_level)
    logger.info("Logging configured.")

from app.services.key_manager import KeyManager
from app.services.security_service import SecurityService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # Startup
    setup_logging()
    logger.info("Application startup...")

    key_manager = KeyManager.load_from_settings(settings)
    app.state.key_manager = key_manager
    app.state.security_service = SecurityService(key_manager)

    if settings.app_env != "development":
        # Initialize PostgreSQL
        try:
            db = Database(settings.DATABASE_URL)
            db.connect()
            app.state.db = db
            logger.info("PostgreSQL connected.")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}", exc_info=True)
            raise

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
    
    yield
    
    # Shutdown
    logger.info("Application shutdown...")
    if hasattr(app.state, 'clickhouse_client') and app.state.clickhouse_client.is_connected():
        app.state.clickhouse_client.disconnect()
        logger.info("ClickHouse disconnected.")
    if hasattr(app.state, 'db'):
        Database.close()
        logger.info("Postgres connection closed.")


app = FastAPI(lifespan=lifespan)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(supply.router, prefix="/supply", tags=["supply"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(v3.router, prefix="/v3", tags=["v3"])
app.include_router(generation.router, prefix="/generation", tags=["generation"])


@app.get("/")
def read_root():
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API v2"}
