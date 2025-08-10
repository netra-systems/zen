from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import async_session_factory, get_async_db
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class SessionManager:
    """Centralized session management with connection pooling and monitoring."""
    _instance: Optional['SessionManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.active_sessions = 0
            self.total_sessions_created = 0
            self.initialized = True
    
    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """Get a database session with monitoring."""
        async with self._lock:
            self.active_sessions += 1
            self.total_sessions_created += 1
            session_id = self.total_sessions_created
        
        logger.debug(f"Opening session {session_id}, active: {self.active_sessions}")
        
        try:
            async with get_async_db() as session:
                yield session
        finally:
            async with self._lock:
                self.active_sessions -= 1
            logger.debug(f"Closed session {session_id}, active: {self.active_sessions}")
    
    def get_stats(self) -> dict:
        """Get session manager statistics."""
        return {
            "active_sessions": self.active_sessions,
            "total_sessions_created": self.total_sessions_created
        }

# Global session manager instance
session_manager = SessionManager()

@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around a series of operations.
    
    This function maintains backward compatibility while using the improved
    session management from postgres.py.
    """
    if async_session_factory is None:
        logger.error("async_session_factory is not initialized")
        raise RuntimeError("Database not configured")
    
    async with session_manager.get_session() as session:
        yield session