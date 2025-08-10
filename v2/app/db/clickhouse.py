from contextlib import asynccontextmanager
from app.db.clickhouse_base import ClickHouseDatabase
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class MockClickHouseDatabase:
    """Mock ClickHouse client for when ClickHouse is disabled in dev mode."""
    
    async def execute(self, query, params=None):
        logger.debug(f"ClickHouse disabled - Mock execute: {query}")
        return []
    
    async def disconnect(self):
        pass
    
    async def test_connection(self):
        return True

@asynccontextmanager
async def get_clickhouse_client():
    """
    Dependency provider for the ClickHouse client.
    Instantiates the client with settings and attempts to connect.
    This function will be called by FastAPI for routes that need a ClickHouse connection.
    """
    # Check if ClickHouse is disabled in development mode
    if settings.environment == "development" and not settings.dev_mode_clickhouse_enabled:
        logger.info("ClickHouse is disabled in development mode - using mock client")
        client = MockClickHouseDatabase()
        try:
            yield client
        finally:
            await client.disconnect()
        return
    
    client = None
    try:
        if settings.environment == "development":
            config = settings.clickhouse_https_dev
        else:
            config = settings.clickhouse_https

        client = ClickHouseDatabase(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            secure=True
        )
        yield client
    finally:
        if client:
            await client.disconnect()