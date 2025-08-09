from contextlib import asynccontextmanager
from app.db.clickhouse_base import ClickHouseDatabase
from ..config import settings

@asynccontextmanager
async def get_clickhouse_client():
    """
    Dependency provider for the ClickHouse client.
    Instantiates the client with settings and attempts to connect.
    This function will be called by FastAPI for routes that need a ClickHouse connection.
    """
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
            client.disconnect()