"""
Main Database Sync Module
Handles syncing auth users to main application database
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class MainDatabaseSync:
    """Manages main database sync operations with Cloud Run compatibility"""
    
    def __init__(self):
        self._engine = None
        self._session_maker = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connection (public method)"""
        await self._initialize_engine()
    
    async def _ensure_initialized(self):
        """Lazy initialization for Cloud Run compatibility"""
        if not self._initialized:
            await self._initialize_engine()
    
    async def _initialize_engine(self):
        """Initialize engine with Cloud Run optimizations"""
        if self._initialized:
            return
            
        # Check multiple environment variables for database URL
        # Priority: MAIN_DATABASE_URL > DATABASE_URL > default
        main_db_url = (
            os.getenv("MAIN_DATABASE_URL") or 
            os.getenv("DATABASE_URL") or
            "postgresql+asyncpg://postgres:postgres@localhost:5432/apex_development"
        )
        
        # Convert postgres:// to postgresql+asyncpg:// if needed
        if main_db_url.startswith("postgres://"):
            main_db_url = main_db_url.replace("postgres://", "postgresql+asyncpg://")
            # Convert sslmode to ssl for asyncpg
            main_db_url = main_db_url.replace("sslmode=", "ssl=")
        elif main_db_url.startswith("postgresql://"):
            main_db_url = main_db_url.replace("postgresql://", "postgresql+asyncpg://")
            # Convert sslmode to ssl for asyncpg
            main_db_url = main_db_url.replace("sslmode=", "ssl=")
        
        logger.info(f"Initializing main DB sync with URL pattern: {main_db_url.split('@')[1] if '@' in main_db_url else 'local'}")
        
        # Use NullPool for serverless environments
        self._engine = create_async_engine(
            main_db_url, 
            echo=False,
            poolclass=NullPool  # Important for Cloud Run
        )
        self._session_maker = async_sessionmaker(
            self._engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        self._initialized = True
        logger.info("Main database sync engine initialized")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with proper cleanup"""
        await self._ensure_initialized()
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def sync_user(self, auth_user) -> Optional[str]:
        """
        DEPRECATED: Auth service must be independent - no main database sync.
        This method should not be used. Services communicate via APIs only.
        
        Returns: user_id (just auth_user.id for compatibility)
        """
        logger.warning(
            "sync_user called but auth service must be independent. "
            "Main app should call auth service APIs instead."
        )
        
        # Return the auth user ID for backward compatibility
        # The main app should use the auth service API to get user data
        return auth_user.id if auth_user else None
    
    async def close(self):
        """Close the engine connection"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Main database sync engine closed")

# Global instance
main_db_sync = MainDatabaseSync()