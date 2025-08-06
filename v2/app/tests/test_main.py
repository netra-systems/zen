
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.logging_config import central_logger

@pytest.mark.asyncio
async def test_app_startup(client: AsyncClient):
    """
    Tests that the application starts up successfully.
    """
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Netra API v2"}

@pytest.mark.asyncio
async def test_postgres_connection(db_session: AsyncSession):
    """
    Tests the connection to the Postgres database.
    """
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1

@pytest.mark.asyncio
async def test_clickhouse_connection():
    """
    Tests the connection to the ClickHouse database.
    """
    clickhouse_client = central_logger.clickhouse_db
    assert clickhouse_client.ping()
