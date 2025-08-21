"""Database Manager - Compatibility Module

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Ensure backward compatibility for database operations
- Value Impact: Prevents import errors and maintains test compatibility
- Strategic Impact: Smooth system evolution without breaking existing code

This module provides compatibility for database manager imports.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from netra_backend.app.db.postgres_core import PostgresCore
from netra_backend.app.db.session import SessionLocal, get_db

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for compatibility with legacy imports."""
    
    def __init__(self):
        """Initialize database manager."""
        self._postgres_core = None
        self._session_factory = SessionLocal
        
    @property
    def postgres_core(self) -> PostgresCore:
        """Get postgres core instance."""
        if self._postgres_core is None:
            self._postgres_core = PostgresCore()
        return self._postgres_core
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager."""
        session = self._session_factory()
        try:
            yield session
        finally:
            await session.close()
    
    async def get_database_session(self):
        """Get database session for compatibility."""
        return get_db()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        try:
            session = await get_db()
            result = await session.execute("SELECT 1")
            await session.close()
            
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": current_timestamp
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": current_timestamp
            }


def get_database_manager() -> DatabaseManager:
    """Get database manager instance."""
    return DatabaseManager()


def get_database_session():
    """Get database session for compatibility."""
    return get_db()


__all__ = [
    'DatabaseManager',
    'get_database_manager',
    'get_database_session'
]