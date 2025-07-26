from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from ..config import settings
from app.logging_config_custom.logger import logger

engine = create_engine(settings.database_url, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a synchronous DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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


from typing import AsyncGenerator

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
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

