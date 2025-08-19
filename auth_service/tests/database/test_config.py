"""
Test Database Configuration
Handles database setup, isolation, and cleanup for auth service tests.
Each test gets isolated database state with proper cleanup.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager

from auth_core.database.models import Base

logger = logging.getLogger(__name__)


class TestDatabaseConfig:
    """Test database configuration and management"""
    
    def __init__(self, db_url: str = "sqlite+aiosqlite:///:memory:"):
        self.db_url = db_url
        self.engine = None
        self.session_factory = None
    
    async def setup_engine(self):
        """Setup async database engine for tests"""
        self.engine = create_async_engine(
            self.db_url,
            echo=False,  # Set to True for SQL debugging
            future=True,
            pool_pre_ping=True
        )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        await self._create_tables()
        
        logger.info(f"Test database engine setup complete: {self.db_url}")
    
    async def _create_tables(self):
        """Create all database tables"""
        if not self.engine:
            raise RuntimeError("Engine not setup. Call setup_engine first.")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.debug("Database tables created successfully")
    
    async def cleanup(self):
        """Cleanup database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.debug("Database engine disposed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get isolated database session with transaction rollback"""
        if not self.session_factory:
            await self.setup_engine()
        
        async with self.session_factory() as session:
            # Start transaction for rollback isolation
            transaction = await session.begin()
            try:
                yield session
            except Exception:
                await transaction.rollback()
                raise
            else:
                # Always rollback to maintain isolation
                await transaction.rollback()
    
    async def reset_tables(self):
        """Reset all tables - use with caution"""
        if not self.engine:
            return
        
        async with self.engine.begin() as conn:
            # Drop all tables
            await conn.run_sync(Base.metadata.drop_all)
            # Recreate all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.debug("Database tables reset")


class PostgresTestConfig(TestDatabaseConfig):
    """PostgreSQL-specific test configuration"""
    
    def __init__(self, test_db_name: str = "test_auth_service"):
        self.test_db_name = test_db_name
        # Use environment variables for connection
        import os
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{test_db_name}"
        super().__init__(db_url)
    
    async def create_test_database(self):
        """Create test database"""
        # Connect to postgres database to create test database
        import os
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        admin_db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/postgres"
        admin_engine = create_async_engine(admin_db_url, isolation_level="AUTOCOMMIT")
        
        async with admin_engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": self.test_db_name}
            )
            
            if not result.fetchone():
                # Create test database
                await conn.execute(text(f'CREATE DATABASE "{self.test_db_name}"'))
                logger.info(f"Created test database: {self.test_db_name}")
        
        await admin_engine.dispose()
    
    async def drop_test_database(self):
        """Drop test database"""
        import os
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        admin_db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/postgres"
        admin_engine = create_async_engine(admin_db_url, isolation_level="AUTOCOMMIT")
        
        async with admin_engine.connect() as conn:
            # Drop database if exists
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{self.test_db_name}"'))
            logger.info(f"Dropped test database: {self.test_db_name}")
        
        await admin_engine.dispose()


def get_test_db_config(use_postgres: bool = False) -> TestDatabaseConfig:
    """Get test database configuration"""
    if use_postgres:
        return PostgresTestConfig()
    return TestDatabaseConfig()


async def setup_test_database(config: Optional[TestDatabaseConfig] = None) -> TestDatabaseConfig:
    """Setup test database with proper configuration"""
    if config is None:
        config = get_test_db_config()
    
    await config.setup_engine()
    return config