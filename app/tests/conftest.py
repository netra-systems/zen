import os
import sys

# Set test environment variables BEFORE importing any app modules
# Use isolated values if TEST_ISOLATION is enabled
if os.environ.get("TEST_ISOLATION") == "1":
    # When using test isolation, environment is already configured
    # Just ensure critical test flags are set
    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("LOG_LEVEL", "ERROR")
    os.environ.setdefault("DEV_MODE_DISABLE_CLICKHOUSE", "true")
    os.environ.setdefault("CLICKHOUSE_ENABLED", "false")
else:
    # Standard test environment setup
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_USERNAME"] = ""
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["TEST_DISABLE_REDIS"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
    os.environ["FERNET_KEY"] = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["LOG_LEVEL"] = "ERROR"
    # Disable ClickHouse for tests
    os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
    os.environ["CLICKHOUSE_ENABLED"] = "false"
    
    # Handle real LLM testing configuration
    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
        # When real LLM testing is enabled, use actual API keys
        # These should be passed from the test runner
        # Ensure GOOGLE_API_KEY mirrors GEMINI_API_KEY for compatibility
        if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    else:
        # Use mock keys for regular testing
        os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
        os.environ.setdefault("GOOGLE_API_KEY", "test-gemini-api-key")  # Same as GEMINI
        os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
        os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-api-key")

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from app.db.session import get_db_session
from app.config import settings

# Temporarily disabled to fix test hanging issue
# @pytest.fixture(scope="function")
# def event_loop():
#     import asyncio
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()

@pytest.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    async_session = sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db_session]