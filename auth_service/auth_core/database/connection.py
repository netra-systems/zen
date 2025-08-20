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
        """Initialize database connection with fast test mode support"""
        if self._initialized:
            return
        
        # Check for fast test mode
        fast_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if fast_test_mode or env == "test":
            # Use in-memory SQLite for fast testing
            logger.info("Using in-memory SQLite for fast test mode")
            database_url = "sqlite+aiosqlite:///:memory:"
        else:
            # Get database URL from config
            from auth_core.config import AuthConfig
            database_url = AuthConfig.get_database_url()
            
            if not database_url:
                logger.warning("No database URL configured, using in-memory SQLite")
                database_url = "sqlite+aiosqlite:///:memory:"
            elif database_url.startswith("postgresql://"):
                # Convert to async PostgreSQL URL
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
                # Convert sslmode to ssl for asyncpg (unless it's a Unix socket connection)
                if "sslmode=" in database_url and "/cloudsql/" not in database_url:
                    database_url = database_url.replace("sslmode=", "ssl=")
            elif database_url.startswith("postgres://"):
                # Handle Heroku-style URLs
                database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
                # Convert sslmode to ssl for asyncpg (unless it's a Unix socket connection)
                if "sslmode=" in database_url and "/cloudsql/" not in database_url:
                    database_url = database_url.replace("sslmode=", "ssl=")
        
        # Create async engine with optimizations
        connect_args = {}
        if database_url.startswith("sqlite"):
            # SQLite optimizations for testing
            connect_args = {"check_same_thread": False}
        
        logger.info(f"Creating async engine with URL pattern: {database_url.split('@')[0]}@...")
        
        try:
            self.engine = create_async_engine(
                database_url,
                poolclass=NullPool,  # Disable pooling for serverless
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
                connect_args=connect_args
            )
        except Exception as e:
            logger.error(f"Failed to create async engine: {e}")
            raise
        
        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables if needed (skip for in-memory in some cases)
        if not (fast_test_mode and database_url == "sqlite+aiosqlite:///:memory:"):
            await self.create_tables()
        
        self._initialized = True
        logger.info(f"Auth database initialized successfully ({'fast test' if fast_test_mode else 'normal'} mode)")
    
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
    
    async def is_ready(self):
        """Check if database is ready to accept connections"""
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                logger.warning(f"Database initialization failed during readiness check: {e}")
                return False
        
        if not self.engine:
            return False
        
        try:
            # Try to execute a simple query
            from sqlalchemy import text
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Database readiness check failed: {e}")
            return False
    
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