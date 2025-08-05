import asyncio
import logging
import pytest
from typing import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app, lifespan
from app.config import settings
from app.db.base import Base
from app.db.models_postgres import DeepAgentRun
from app.db.postgres import get_async_db
from app.llm.llm_manager import LLMManager

# Set the log level for sqlalchemy.engine to WARNING
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

@pytest.fixture(scope="function")
def event_loop(request) -> Generator:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Creates a test database engine that is reused across the test session.
    Creates all tables before running tests, and drops them after.
    """
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a transactional session for each test function.
    It starts a transaction and rolls it back after the test, ensuring isolation.
    """
    async_session_factory = sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        async with session.begin():
            yield session

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient with the database dependency overridden
    to use the test database session.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = _override_get_db
    async with lifespan(app):
        yield TestClient(app)
    del app.dependency_overrides[get_async_db]