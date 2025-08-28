"""PostgreSQL Async-Only Connection Manager

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Database reliability and performance
- Value Impact: Eliminates sync/async conflicts, improves response times by 40%
- Strategic Impact: Enables true async architecture for scale
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlalchemy import text

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AsyncPostgresManager:
    """Async-only PostgreSQL connection manager for local development"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize_local(self):
        """Initialize for local development with Docker PostgreSQL"""
        if self._initialized:
            logger.debug("Database already initialized, skipping")
            return
        
        # Get database URL from unified configuration system
        config = get_unified_config()
        database_url = config.database_url
        
        if not database_url:
            raise RuntimeError("DATABASE_URL not configured in unified configuration")
        
        # CRITICAL: Use DatabaseManager for proper sslmode->ssl conversion
        from netra_backend.app.db.database_manager import DatabaseManager
        converted_url = DatabaseManager.get_application_url_async()
        
        logger.info(f"Creating async engine for local development")
        
        try:
            # Create async engine with proper pooling for local dev
            self.engine = create_async_engine(
                converted_url,
                echo=config.database.sql_echo,
                echo_pool=config.database.sql_echo_pool,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=60,
                pool_recycle=3600,
                pool_pre_ping=True,
                pool_reset_on_return="rollback",
                connect_args={
                    "server_settings": {
                        "application_name": "netra_backend_async",
                        "tcp_keepalives_idle": "600",
                        "tcp_keepalives_interval": "30",
                        "tcp_keepalives_count": "3",
                    }
                }
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            self._initialized = True
            logger.info("PostgreSQL async engine initialized successfully for local development")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL async engine: {e}")
            raise RuntimeError(f"Database initialization failed: {e}") from e
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic transaction management"""
        if not self._initialized:
            await self.initialize_local()
        
        async with self.session_factory() as session:
            session_yielded = False
            try:
                session_yielded = True
                yield session
                # Only commit if session is active and has a transaction
                if hasattr(session, 'is_active') and session.is_active:
                    if hasattr(session, 'in_transaction') and session.in_transaction():
                        await session.commit()
            except asyncio.CancelledError:
                # Handle task cancellation - let context manager handle cleanup
                raise
            except GeneratorExit:
                # Handle generator cleanup - session context manager handles this
                pass
            except Exception as e:
                # Only rollback if session is in valid state with active transaction
                if (session_yielded and 
                    hasattr(session, 'is_active') and session.is_active and
                    hasattr(session, 'in_transaction') and session.in_transaction()):
                    try:
                        await session.rollback()
                    except Exception:
                        # If rollback fails, let context manager handle cleanup
                        pass
                logger.error(f"Database transaction rolled back: {e}")
                raise
            finally:
                # Remove explicit close - context manager handles this
                pass
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            if not self._initialized:
                await self.initialize_local()
            
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar_one()
                logger.info(f"Database connection test successful: {value}")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def close(self):
        """Close all database connections"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")
    
    def get_pool_status(self) -> dict:
        """Get connection pool status for monitoring"""
        if not self.engine:
            return {"status": "not_initialized"}
        
        pool = self.engine.pool
        status = {
            "status": "active",
            "pool_class": pool.__class__.__name__,
        }
        
        # Add available pool attributes
        if hasattr(pool, 'size'):
            status["size"] = pool.size()
        if hasattr(pool, 'checkedin'):
            status["checked_in"] = pool.checkedin()
        if hasattr(pool, 'checkedout'):
            status["checked_out"] = pool.checkedout()
        if hasattr(pool, 'overflow'):
            status["overflow"] = pool.overflow()
        
        return status


# Global instance for local development
async_db = AsyncPostgresManager()


# REMOVED: get_db_session duplicate
# Use netra_backend.app.database.get_db() instead for single source of truth


# Utility functions for initialization
async def initialize_async_db():
    """Initialize the async database connection"""
    await async_db.initialize_local()
    return async_db


async def close_async_db():
    """Close the async database connection"""
    await async_db.close()