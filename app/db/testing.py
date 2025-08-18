from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.config import settings
from app.db.base import Base

# Convert database URL to async format if needed
def _convert_postgresql_url(db_url: str) -> str:
    """Convert postgresql:// to postgresql+asyncpg://"""
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://")
    return db_url

def _convert_postgres_url(db_url: str) -> str:
    """Convert postgres:// to postgresql+asyncpg://"""
    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+asyncpg://")
    return db_url

def get_async_database_url() -> str:
    """Convert database URL to async format if needed"""
    db_url = settings.database_url
    db_url = _convert_postgresql_url(db_url)
    db_url = _convert_postgres_url(db_url)
    return db_url

engine = create_async_engine(get_async_database_url(), echo=False, future=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session
