from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from ..config import settings
from app.logging_config_custom.logger import logger

class Database:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def connect(self):
        self.engine.connect()

    def get_db(self) -> Session:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def close():
        pass

# PostgreSQL async engine
try:
    async_engine = create_async_engine(
        settings.database_url,
        echo=True,
    )
    AsyncSessionLocal = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    print("PostgreSQL async engine created successfully.")
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

