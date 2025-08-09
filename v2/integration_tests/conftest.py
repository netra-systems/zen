import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base
from app.config import settings

@pytest.fixture(scope="session", autouse=True)
async def create_test_tables():
    if settings.environment == "testing":
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    else:
        yield # Do nothing if not in testing environment