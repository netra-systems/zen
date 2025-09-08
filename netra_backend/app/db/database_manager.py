"""Database Manager - SSOT for Database Operations

Centralized database management with proper DatabaseURLBuilder integration.
This module uses DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH for URL construction.

CRITICAL: ALL URL manipulation MUST go through DatabaseURLBuilder methods:
- format_url_for_driver() for driver-specific formatting
- normalize_url() for URL normalization
- NO MANUAL STRING REPLACEMENT OPERATIONS ALLOWED

See Also:
- shared/database_url_builder.py - The ONLY source for URL construction
- SPEC/database_connectivity_architecture.xml - Database connection patterns
- docs/configuration_architecture.md - Configuration system overview

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database connection management
- Value Impact: Eliminates URL construction errors and ensures consistency
- Strategic Impact: Single source of truth for all database connection patterns
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool, StaticPool
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text

from netra_backend.app.core.config import get_config
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection and session management."""
    
    def __init__(self):
        self.config = get_config()
        self._engines: Dict[str, AsyncEngine] = {}
        self._initialized = False
        self._url_builder: Optional[DatabaseURLBuilder] = None
    
    async def initialize(self):
        """Initialize database connections using DatabaseURLBuilder."""
        if self._initialized:
            return
        
        try:
            # Get database URL using DatabaseURLBuilder as SSOT
            database_url = self._get_database_url()
            
            # Handle different config attribute names gracefully
            echo = getattr(self.config, 'database_echo', False)
            pool_size = getattr(self.config, 'database_pool_size', 5)
            max_overflow = getattr(self.config, 'database_max_overflow', 10)
            
            # Use appropriate pool class for async engines
            engine_kwargs = {
                "echo": echo,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
            
            # Configure pooling for async engines
            if pool_size <= 0 or "sqlite" in database_url.lower():
                # Use NullPool for SQLite or disabled pooling
                engine_kwargs["poolclass"] = NullPool
            else:
                # Use StaticPool for async engines - it doesn't support pool_size/max_overflow
                engine_kwargs["poolclass"] = StaticPool
            
            primary_engine = create_async_engine(
                database_url,
                **engine_kwargs
            )
            
            self._engines['primary'] = primary_engine
            self._initialized = True
            
            logger.info("DatabaseManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseManager: {e}")
            raise
    
    def get_engine(self, name: str = 'primary') -> AsyncEngine:
        """Get database engine by name."""
        if not self._initialized:
            raise RuntimeError("DatabaseManager not initialized")
        
        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found")
        
        return self._engines[name]
    
    @asynccontextmanager
    async def get_session(self, engine_name: str = 'primary'):
        """Get async database session with automatic cleanup."""
        if not self._initialized:
            await self.initialize()
        
        engine = self.get_engine(engine_name)
        async with AsyncSession(engine) as session:
            original_exception = None
            try:
                yield session
                await session.commit()
            except Exception as e:
                original_exception = e
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    # Continue with original exception
                logger.error(f"Database session error: {e}")
                raise original_exception
            finally:
                try:
                    await session.close()
                except Exception as close_error:
                    logger.error(f"Session close failed: {close_error}")
                    # Don't raise close errors - they shouldn't prevent completion
    
    async def health_check(self, engine_name: str = 'primary') -> Dict[str, Any]:
        """Perform health check on database connection."""
        try:
            engine = self.get_engine(engine_name)
            
            async with AsyncSession(engine) as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()  # fetchone() is not awaitable
            
            return {
                "status": "healthy",
                "engine": engine_name,
                "connection": "ok"
            }
            
        except Exception as e:
            logger.error(f"Database health check failed for {engine_name}: {e}")
            return {
                "status": "unhealthy",
                "engine": engine_name,
                "error": str(e)
            }
    
    async def close_all(self):
        """Close all database engines."""
        for name, engine in self._engines.items():
            try:
                await engine.dispose()
                logger.info(f"Closed database engine: {name}")
            except Exception as e:
                logger.error(f"Error closing engine {name}: {e}")
        
        self._engines.clear()
        self._initialized = False
    
    def _get_database_url(self) -> str:
        """Get database URL using DatabaseURLBuilder as SSOT.
        
        Returns:
            Properly formatted database URL from DatabaseURLBuilder
        """
        env = get_env()
        
        # Create DatabaseURLBuilder instance if not exists
        if not self._url_builder:
            self._url_builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL for current environment
        database_url = self._url_builder.get_url_for_environment(sync=False)
        
        if not database_url:
            # Let the config handle the fallback if needed
            database_url = self.config.database_url
            if not database_url:
                raise ValueError(
                    "DatabaseURLBuilder failed to construct URL and no config fallback available. "
                    "Ensure proper POSTGRES_* environment variables are set."
                )
        
        # CRITICAL: Use DatabaseURLBuilder to format URL for asyncpg driver
        # NEVER use string.replace() or manual manipulation - DatabaseURLBuilder is SSOT
        # This handles all driver-specific formatting including postgresql:// -> postgresql+asyncpg://
        database_url = self._url_builder.format_url_for_driver(database_url, 'asyncpg')
        
        # Log safe connection info
        logger.info(self._url_builder.get_safe_log_message())
        
        return database_url
    
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get database URL in sync format for Alembic migrations.
        
        Returns:
            Properly formatted sync database URL for migrations
        """
        env = get_env()
        url_builder = DatabaseURLBuilder(env.as_dict())
        
        # Get sync URL for migrations
        migration_url = url_builder.get_url_for_environment(sync=True)
        
        if not migration_url:
            raise ValueError("Could not determine migration database URL")
        
        # Ensure the URL is in sync format by removing async drivers
        if "postgresql+asyncpg://" in migration_url:
            migration_url = migration_url.replace("postgresql+asyncpg://", "postgresql://")
        
        return migration_url
    
    @classmethod
    @asynccontextmanager
    async def get_async_session(cls, name: str = 'primary'):
        """
        Class method for backward compatibility with code expecting DatabaseManager.get_async_session().
        
        This method provides the expected static/class method interface while using
        the instance method internally for proper session management.
        
        Args:
            name: Engine name (default: 'primary')
            
        Yields:
            AsyncSession: Database session with automatic cleanup
            
        Note:
            This is a compatibility shim. New code should use:
            - netra_backend.app.database.get_db() for dependency injection
            - instance.get_session() for direct usage
        """
        manager = get_database_manager()
        if not manager._initialized:
            await manager.initialize()
        
        async with manager.get_session(name) as session:
            yield session
    
    @staticmethod
    def create_application_engine() -> AsyncEngine:
        """Create a new application engine for health checks."""
        config = get_config()
        env = get_env()
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL from builder
        database_url = builder.get_url_for_environment(sync=False)
        if not database_url:
            database_url = config.database_url
        
        # Use DatabaseURLBuilder to format URL for asyncpg driver - NO MANUAL STRING MANIPULATION
        database_url = builder.format_url_for_driver(database_url, 'asyncpg')
        
        return create_async_engine(
            database_url,
            echo=False,  # Don't echo in health checks
            poolclass=NullPool,  # Use NullPool for health check connections
            pool_pre_ping=True,
            pool_recycle=3600,
        )


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


@asynccontextmanager
async def get_db_session(engine_name: str = 'primary'):
    """Helper to get database session."""
    manager = get_database_manager()
    async with manager.get_session(engine_name) as session:
        yield session