"""
Auth Service Database Connection - Async-Only Implementation
Unified async database connection management for auth service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Auth service reliability and performance
- Value Impact: Consistent async patterns, improved auth response times
- Strategic Impact: Enables scalable authentication for enterprise
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AuthDatabase:
    """Async-only database connection manager for auth service"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker] = None
        self._initialized = False
        self.is_cloud_run = os.getenv("K_SERVICE") is not None
        self.is_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
    
    async def initialize(self):
        """Initialize async database connection for all environments"""
        if self._initialized:
            return
        
        # Determine database URL and configuration based on environment
        if self.is_test_mode or self.environment == "test":
            # Use in-memory SQLite for testing
            logger.info("Using in-memory SQLite for test mode")
            database_url = "sqlite+aiosqlite:///:memory:"
            pool_class = NullPool
            connect_args = {"check_same_thread": False}
        elif self.is_cloud_run:
            # Cloud Run with Cloud SQL
            database_url = await self._get_cloud_sql_url()
            pool_class = NullPool  # Serverless requires NullPool
            connect_args = self._get_cloud_sql_connect_args()
        else:
            # Local development with PostgreSQL
            database_url = await self._get_local_postgres_url()
            pool_class = AsyncAdaptedQueuePool
            connect_args = self._get_local_connect_args()
        
        logger.info(f"Creating async engine for environment: {self.environment}")
        
        try:
            # Create engine with environment-specific configuration
            engine_kwargs = {
                "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
                "poolclass": pool_class,
                "connect_args": connect_args,
            }
            
            # Add pool configuration for non-NullPool
            if pool_class == AsyncAdaptedQueuePool:
                engine_kwargs.update({
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                    "pool_pre_ping": True,
                    "pool_reset_on_return": "rollback",
                })
            
            self.engine = create_async_engine(database_url, **engine_kwargs)
            
            # Create session factory
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            # Create tables if needed
            if not (self.is_test_mode and "memory" in database_url):
                await self.create_tables()
            
            self._initialized = True
            logger.info(f"Auth database initialized successfully for {self.environment}")
            
        except Exception as e:
            logger.error(f"Failed to initialize auth database: {e}")
            raise RuntimeError(f"Auth database initialization failed: {e}") from e
    
    async def _get_cloud_sql_url(self) -> str:
        """Get Cloud SQL connection URL for Cloud Run"""
        try:
            # Try Cloud SQL connector first
            from google.cloud.sql.connector import Connector
            
            # This would be handled differently with connector
            # For now, fall back to direct URL
            return await self._get_direct_cloud_sql_url()
        except ImportError:
            # Fallback to direct connection
            return await self._get_direct_cloud_sql_url()
    
    async def _get_direct_cloud_sql_url(self) -> str:
        """Get direct Cloud SQL connection URL"""
        from auth_service.auth_core.config import AuthConfig
        database_url = AuthConfig.get_database_url()
        
        if not database_url:
            raise ValueError("No database URL configured for Cloud Run")
        
        # Convert to async format
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
        
        # Handle SSL for asyncpg
        if "sslmode=" in database_url:
            if "/cloudsql/" in database_url:
                import re
                database_url = re.sub(r'[&?]sslmode=[^&]*', '', database_url)
            else:
                database_url = database_url.replace("sslmode=", "ssl=")
        
        return database_url
    
    async def _get_local_postgres_url(self) -> str:
        """Get local PostgreSQL connection URL"""
        from auth_service.auth_core.config import AuthConfig
        database_url = AuthConfig.get_database_url()
        
        if not database_url:
            # Default local PostgreSQL
            database_url = "postgresql+asyncpg://postgres:password@localhost:5432/auth"
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
        
        # Handle SSL for asyncpg
        if "sslmode=" in database_url:
            database_url = database_url.replace("sslmode=", "ssl=")
        
        return database_url
    
    def _get_cloud_sql_connect_args(self) -> dict:
        """Get connection arguments for Cloud SQL"""
        return {
            "server_settings": {
                "application_name": "auth_service_cloud",
                "tcp_keepalives_idle": "120",
                "tcp_keepalives_interval": "10",
                "tcp_keepalives_count": "3",
            },
            "command_timeout": 60,
        }
    
    def _get_local_connect_args(self) -> dict:
        """Get connection arguments for local PostgreSQL"""
        return {
            "server_settings": {
                "application_name": "auth_service_local",
                "tcp_keepalives_idle": "600",
                "tcp_keepalives_interval": "30",
                "tcp_keepalives_count": "3",
            }
        }
    
    async def create_tables(self):
        """Create database tables if they don't exist"""
        from .models import Base
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic transaction management"""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Auth database transaction rolled back: {e}")
                raise
            finally:
                await session.close()
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            if not self._initialized:
                await self.initialize()
            
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar_one()
                logger.info(f"Auth database connection test successful: {value}")
                return True
        except Exception as e:
            logger.error(f"Auth database connection test failed: {e}")
            return False
    
    async def is_ready(self) -> bool:
        """Check if database is ready to accept connections"""
        return await self.test_connection()
    
    async def close(self):
        """Close all database connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Auth database connections closed")
    
    def get_status(self) -> dict:
        """Get current database status for monitoring"""
        return {
            "status": "active" if self._initialized else "not_initialized",
            "environment": self.environment,
            "is_cloud_run": self.is_cloud_run,
            "is_test_mode": self.is_test_mode,
            "pool_type": "NullPool" if (self.is_cloud_run or self.is_test_mode) else "AsyncAdaptedQueuePool",
        }

# Global database instance
auth_db = AuthDatabase()

async def get_db_session():
    """Dependency for FastAPI routes"""
    async with auth_db.get_session() as session:
        yield session