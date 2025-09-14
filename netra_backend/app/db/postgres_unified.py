"""Unified PostgreSQL Async Configuration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database management across environments
- Value Impact: Single interface for all environments, reducing complexity
- Strategic Impact: Faster development and deployment cycles
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.config import get_config
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UnifiedPostgresDB:
    """DEPRECATED: Unified async PostgreSQL manager - Use DatabaseManager instead.
    
    This class has been DEPRECATED to eliminate SSOT violations.
    Use netra_backend.app.db.database_manager.DatabaseManager directly.
    """
    
    def __init__(self):
        import warnings
        warnings.warn(
            "UnifiedPostgresDB is deprecated. Use DatabaseManager from netra_backend.app.db.database_manager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to DatabaseManager
        from netra_backend.app.db.database_manager import DatabaseManager
        self._database_manager = DatabaseManager
        
        # Detect environment from unified config for compatibility
        config = get_config()
        from netra_backend.app.core.environment_constants import EnvironmentDetector
        self.is_cloud_run = EnvironmentDetector.is_cloud_run()
        self.is_staging = config.environment == "staging"
        self.is_production = config.environment == "production" 
        self.is_test = config.environment == "test"
        self._initialized = True  # Always initialized since DatabaseManager handles lazy init
        
        logger.info(f"DEPRECATED UnifiedPostgresDB - delegating to DatabaseManager")
    
    async def initialize(self):
        """DEPRECATED: DatabaseManager handles initialization automatically."""
        logger.info("UnifiedPostgresDB.initialize() is deprecated - DatabaseManager handles initialization")
        
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """DEPRECATED: Get database session via DatabaseManager."""
        session_factory = self._database_manager.get_application_session()
        async with session_factory() as session:
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
            except Exception:
                # Only rollback if session is in valid state with active transaction
                if (session_yielded and 
                    hasattr(session, 'is_active') and session.is_active and
                    hasattr(session, 'in_transaction') and session.in_transaction()):
                    try:
                        await session.rollback()
                    except Exception:
                        # If rollback fails, let context manager handle cleanup
                        pass
                raise
    
    async def test_connection(self) -> bool:
        """DEPRECATED: Test database connectivity via DatabaseManager."""
        try:
            engine = self._database_manager.create_application_engine()
            return await self._database_manager.test_connection_with_retry(engine)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def close(self):
        """DEPRECATED: DatabaseManager handles connection lifecycle."""
        logger.info("UnifiedPostgresDB.close() is deprecated - DatabaseManager handles lifecycle")
    
    def get_status(self) -> dict:
        """DEPRECATED: Get current database status via DatabaseManager."""
        return {
            "status": "deprecated_redirected_to_database_manager", 
            "environment": self._get_environment_name(),
            "manager_type": "database_manager_delegate",
            "is_cloud_sql": self._database_manager.is_cloud_sql_environment(),
            "is_local_dev": self._database_manager.is_local_development(),
        }
    
    def _get_environment_name(self) -> str:
        """Get human-readable environment name"""
        if self.is_production:
            return "production"
        elif self.is_staging:
            return "staging"
        elif self.is_cloud_run:
            return "cloud_run"
        elif self.is_test:
            return "test"
        else:
            return "development"


# Global unified instance
unified_db = UnifiedPostgresDB()


# DEPRECATED: Redirects to DatabaseManager-based single source of truth
@asynccontextmanager
async def get_db():
    """DEPRECATED: Use netra_backend.app.database.get_db() for SSOT compliance.
    
    This implementation has been DEPRECATED to eliminate SSOT violations.
    All new code should import from netra_backend.app.database directly.
    """
    import warnings
    warnings.warn(
        "postgres_unified.get_db() is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    from netra_backend.app.database import get_db as _get_db
    async with _get_db() as session:
        yield session

# DEPRECATED: Backward compatibility alias
def get_async_db():
    """DEPRECATED: Use netra_backend.app.database.get_db() for SSOT compliance."""
    import warnings
    warnings.warn(
        "postgres_unified.get_async_db() is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_db()


# Utility functions for lifecycle management
async def initialize_database():
    """Initialize the database connection"""
    await unified_db.initialize()
    return unified_db


async def close_database():
    """Close the database connection"""
    await unified_db.close()


async def check_database_health() -> dict:
    """Check database health and return status"""
    is_healthy = await unified_db.test_connection()
    status = unified_db.get_status()
    status["healthy"] = is_healthy
    return status


# FastAPI lifespan events integration
async def on_startup():
    """FastAPI startup event handler"""
    logger.info("Starting database initialization on app startup")
    await initialize_database()
    
    # Test connection
    health = await check_database_health()
    if health.get("healthy"):
        logger.info(f"Database healthy on startup: {health}")
    else:
        logger.error(f"Database unhealthy on startup: {health}")
        # Don't fail startup, allow app to run in degraded mode


async def on_shutdown():
    """FastAPI shutdown event handler"""
    logger.info("Closing database connections on app shutdown")
    await close_database()