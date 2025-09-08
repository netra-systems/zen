"""Database Service - Transaction Management

Provides database transaction management services.
"""

import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseTransactionManager:
    """Manages database transactions and sessions."""
    
    def __init__(self):
        self.session_factory = AsyncSessionLocal
    
    @asynccontextmanager
    async def transaction(self):
        """Provide a transactional context manager."""
        session = None
        try:
            session = self.session_factory()
            yield session
            await session.commit()
        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            if session:
                await session.close()
    
    async def create_session(self) -> AsyncSession:
        """Create a new database session."""
        return self.session_factory()
    
    async def execute_transaction(self, func, *args, **kwargs):
        """Execute a function within a transaction."""
        async with self.transaction() as session:
            return await func(session, *args, **kwargs)