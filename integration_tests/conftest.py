"""
Integration tests conftest.py

Imports necessary fixtures from app/tests/conftest.py to ensure database tables are created.
"""
import os
import sys

# Set test environment before any imports
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"

# Import the test engine fixture from app tests
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

# Import all models to ensure they are registered with Base
from app.db.base import Base
from app.db.models_user import User, Secret, ToolUsageLog
from app.db.models_postgres import *
from app.db.models_content import *
from app.db.models_agent_state import *

from app.config import settings

@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine and create all tables."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    """Create database session for testing."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session