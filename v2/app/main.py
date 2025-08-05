# v2/app/main.py
import logging
logging.getLogger("faker").setLevel(logging.WARNING)

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth, supply, v3, generation, google_auth, deep_agent
from app.db.postgres import Database
from app.db.clickhouse import ClickHouseClient
from app.db.models_clickhouse import SUPPLY_TABLE_SCHEMA, LOGS_TABLE_SCHEMA
from app.config import settings
from app.logging_config_custom.logger import logger, Formatter
from app.logging_config_custom.clickhouse_logger import ClickHouseLogHandler
from app.llm.llm_manager import LLMManager

def setup_logging():
    """Initializes the application's logging configuration."""
    logger.remove()
    logger.add(sys.stdout, level=settings.log_level, format=Formatter().format)
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

    # Initialize LLMManager
    app.state.llm_manager = LLMManager(settings.llm_configs)

    # Initialize and connect to ClickHouse
    ch_client = ClickHouseClient(
        host=settings.clickhouse_https.host,
        port=settings.clickhouse_https.port,
        database=settings.clickhouse_https.database,
        user=settings.clickhouse_https.user,
        password=settings.clickhouse_https.password
    )
    logger.info(f"Connecting to ClickHouse at {settings.clickhouse_https.host}:{settings.clickhouse_https.port}")
    try:
        ch_client.connect()
        logger.info("ClickHouse connected.")
        # Create tables if they don't exist
        ch_client.command(SUPPLY_TABLE_SCHEMA)
        ch_client.command(LOGS_TABLE_SCHEMA)
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


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(supply.router, prefix="/api/v3/supply", tags=["supply"])
app.include_router(v3.router, prefix="/api/v3", tags=["v3"])
app.include_router(generation.router, prefix="/api/v3/generation", tags=["generation"])
app.include_router(google_auth.router, tags=["google_auth"])
app.include_router(deep_agent.router, prefix="/api/v3", tags=["deep_agent"])



@app.get("/")
def read_root():
    logger.info("Root endpoint was hit.")
    return {"message": "Welcome to Netra API v2"}
