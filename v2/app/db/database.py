import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from ..config import settings
from .base import Base  # Import Base from the new central location.
from .postgres import get_db  # Continue to import the sync session generator.
from .clickhouse import get_clickhouse_client

# Setup logging
logger = logging.getLogger(__name__)

# This file sets up the ASYNCHRONOUS database connection.

# PostgreSQL async engine
try:
    async_engine = create_async_engine(
        settings.database_url,
        echo=True,
    )
    AsyncSessionLocal = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("PostgreSQL async engine created successfully.")
except Exception as e:
    logger.error(f"Failed to create PostgreSQL async engine: {e}")
    # Handle the error appropriately, maybe exit or use a fallback
    async_engine = None
    AsyncSessionLocal = None


async def get_async_db() -> AsyncSession:
    """
    Dependency to get an async database session.
    """
    if AsyncSessionLocal is None:
        logger.error("AsyncSessionLocal is not initialized.")
        raise RuntimeError("Database not configured")

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async DB session error: {e}")
            raise
        finally:
            await session.close()
