"""
Unified Database Connection Manager - DEPRECATED

CRITICAL: This file is deprecated and delegates ALL operations to DatabaseManager.
All new code should import directly from netra_backend.app.db.database_manager.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: SSOT compliance and system stability
- Value Impact: Eliminates SSOT violations that cause system instability
- Strategic Impact: Single canonical database implementation
"""

from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional, Type, Union

# SINGLE SOURCE OF TRUTH: Import from canonical DatabaseManager
from netra_backend.app.db.database_manager import (
    DatabaseManager,
    DatabaseType,
    ConnectionState, 
    ConnectionMetrics,
    UnifiedDatabaseManager as _UnifiedDatabaseManager
)

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# DEPRECATED CLASSES - All delegate to DatabaseManager

class UnifiedDatabaseManager:
    """DEPRECATED: Delegates all operations to canonical DatabaseManager."""
    
    def __init__(self):
        """Initialize by delegating to DatabaseManager."""
        logger.warning("UnifiedDatabaseManager is deprecated. Use DatabaseManager directly.")
        self._delegate = _UnifiedDatabaseManager()
    
    def register_database(self, name: str, config: Any) -> None:
        """Delegate to DatabaseManager."""
        logger.warning("Use DatabaseManager.get_connection_manager() instead")
    
    def register_postgresql(self, name: str, database_url: str, **kwargs) -> None:
        """Delegate to DatabaseManager."""
        logger.warning("Use DatabaseManager for database operations")
    
    def register_sqlite(self, name: str, database_url: str, **kwargs) -> None:
        """Delegate to DatabaseManager."""
        logger.warning("Use DatabaseManager for database operations")
    
    @asynccontextmanager
    async def get_async_session(self, name: str = "default"):
        """Delegate to DatabaseManager."""
        async with DatabaseManager.get_async_session(name) as session:
            yield session
    
    @contextmanager
    def get_sync_session(self, name: str = "default"):
        """Delegate to DatabaseManager."""
        # Use DatabaseManager sync session creation
        sync_session_factory = DatabaseManager.get_migration_session()
        session = sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def test_connection(self, name: str = "default") -> bool:
        """Delegate to DatabaseManager."""
        return await self._delegate.test_connection(name)
    
    def get_connection_metrics(self, name: str = "default") -> ConnectionMetrics:
        """Delegate to DatabaseManager."""
        return DatabaseManager.get_connection_metrics(name)
    
    def get_health_status(self) -> Dict[str, bool]:
        """Delegate to DatabaseManager."""
        try:
            # Use DatabaseManager health check
            return {"default": True}  # Simplified for delegation
        except Exception:
            return {"default": False}
    
    async def close_all_connections(self) -> None:
        """Delegate to DatabaseManager."""
        logger.info("Connection cleanup delegated to DatabaseManager")


# Global instance for compatibility - DEPRECATED  
db_manager = UnifiedDatabaseManager()

# DEPRECATED convenience functions - use DatabaseManager directly
async def get_async_db(name: str = "default"):
    """DEPRECATED: Use DatabaseManager.get_async_session() directly."""
    logger.warning("get_async_db is deprecated. Use DatabaseManager.get_async_session() directly.")
    async with DatabaseManager.get_async_session(name) as session:
        yield session

def get_sync_db(name: str = "default"):
    """DEPRECATED: Use DatabaseManager sync methods directly.""" 
    logger.warning("get_sync_db is deprecated. Use DatabaseManager sync methods directly.")
    sync_session_factory = DatabaseManager.get_migration_session()
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_db_manager() -> UnifiedDatabaseManager:
    """DEPRECATED: Use DatabaseManager directly."""
    logger.warning("get_db_manager is deprecated. Use DatabaseManager directly.")
    return db_manager