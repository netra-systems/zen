from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from netra_backend.app.config import settings
from netra_backend.app.db.base import Base

# Convert database URL to async format if needed
def _convert_postgresql_url(db_url: str) -> str:
    """Convert postgresql:// to postgresql+asyncpg://"""
    if db_url.startswith("postgresql://"):
        url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        # Convert sslmode to ssl for asyncpg
        return url.replace("sslmode=", "ssl=")
    return db_url

def _convert_postgres_url(db_url: str) -> str:
    """Convert postgres:// to postgresql+asyncpg://"""
    if db_url.startswith("postgres://"):
        url = db_url.replace("postgres://", "postgresql+asyncpg://")
        # Convert sslmode to ssl for asyncpg
        return url.replace("sslmode=", "ssl=")
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
