"""
Auth Service Database Connection
Database connection and session management for auth service
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

class AuthDatabase:
    """Database connection manager for auth service"""
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection"""
        if self._initialized:
            return
        
        # Get database URL from environment
        database_url = os.getenv("AUTH_DATABASE_URL", os.getenv("DATABASE_URL"))
        
        if not database_url:
            logger.warning("No database URL configured, using in-memory SQLite")
            database_url = "sqlite+aiosqlite:///:memory:"
        elif database_url.startswith("postgresql://"):
            # Convert to async PostgreSQL URL
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        elif database_url.startswith("postgres://"):
            # Handle Heroku-style URLs
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            poolclass=NullPool,  # Disable pooling for serverless
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
        
        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables if needed
        await self.create_tables()
        
        self._initialized = True
        logger.info("Auth database initialized successfully")
    
    async def create_tables(self):
        """Create database tables if they don't exist"""
        from .models import Base
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager"""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False

# Global database instance
auth_db = AuthDatabase()

async def get_db_session():
    """Dependency for FastAPI routes"""
    async with auth_db.get_session() as session:
        yield session