"""
SSOT Database session management module.
Consolidates session management functionality from postgres_session.py and database_manager.py.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.postgres_session import (
    validate_session,
    get_async_db,
    get_postgres_session
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_session() -> AsyncSession:
    """
    Get a database session from the SSOT database manager.
    
    Returns:
        AsyncSession: Database session for executing queries
    """
    db_manager = get_database_manager()
    return await db_manager.get_session()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session context manager.
    
    Yields:
        AsyncSession: Database session for executing queries
    """
    db_manager = get_database_manager()
    async with db_manager.get_session_context() as session:
        yield session


def get_session_from_factory(factory: Any) -> AsyncSession:
    """
    Get a session from a factory object (for testing and dependency injection).
    
    Args:
        factory: Factory object that provides database sessions
        
    Returns:
        AsyncSession: Database session from the factory
    """
    if hasattr(factory, 'get_db_session'):
        return factory.get_db_session()
    elif hasattr(factory, 'db_session'):
        return factory.db_session
    elif hasattr(factory, 'session'):
        return factory.session
    else:
        # Fallback to global database manager
        logger.warning(f"Factory {factory} does not have session method, using global manager")
        return get_database_manager().get_sync_session()


async def init_database(config: Optional[dict] = None) -> None:
    """
    Initialize the database connection and session factory.
    
    Args:
        config: Optional database configuration
    """
    db_manager = get_database_manager()
    await db_manager.initialize(config)


async def close_database() -> None:
    """
    Close the database connection and cleanup resources.
    """
    global _db_manager
    if _db_manager:
        await _db_manager.cleanup()
        _db_manager = None


# Re-export common functions from postgres_session for backward compatibility
__all__ = [
    'get_session',
    'get_async_session', 
    'get_session_from_factory',
    'init_database',
    'close_database',
    'validate_session',
    'safe_session_context',
    'handle_session_error'
]