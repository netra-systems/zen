"""Database Manager

Centralized database management with connection pooling, health checks, and error recovery.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text

from netra_backend.app.core.config import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection and session management."""
    
    def __init__(self):
        self.config = get_config()
        self._engines: Dict[str, AsyncEngine] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections."""
        if self._initialized:
            return
        
        try:
            # Create primary database engine
            primary_engine = create_async_engine(
                self.config.database_url,
                echo=self.config.database_echo,
                poolclass=QueuePool if self.config.database_pool_size > 0 else NullPool,
                pool_size=self.config.database_pool_size,
                max_overflow=self.config.database_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
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
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def health_check(self, engine_name: str = 'primary') -> Dict[str, Any]:
        """Perform health check on database connection."""
        try:
            engine = self.get_engine(engine_name)
            
            async with AsyncSession(engine) as session:
                result = await session.execute(text("SELECT 1"))
                await result.fetchone()
            
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


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


async def get_db_session(engine_name: str = 'primary'):
    """Helper to get database session."""
    manager = get_database_manager()
    async with manager.get_session(engine_name) as session:
        yield session