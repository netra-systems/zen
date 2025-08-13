from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings
from app.db.base import Base

# Convert database URL to async format if needed
def get_async_database_url():
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        # Replace with asyncpg driver
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    elif db_url.startswith("postgres://"):
        # Handle older postgres:// format
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
    return db_url

engine = create_async_engine(get_async_database_url(), echo=False, future=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session
