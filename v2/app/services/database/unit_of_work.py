"""Unit of Work Pattern Implementation

Manages database transactions and repositories in a single context.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from app.logging_config import central_logger
from app.db.postgres import async_session_factory
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.run_repository import RunRepository
from app.services.database.reference_repository import ReferenceRepository

logger = central_logger.get_logger(__name__)

class UnitOfWork:
    """Unit of Work pattern for managing database transactions"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session
        self._external_session = session is not None
        self.threads: Optional[ThreadRepository] = None
        self.messages: Optional[MessageRepository] = None
        self.runs: Optional[RunRepository] = None
        self.references: Optional[ReferenceRepository] = None
    
    async def __aenter__(self):
        """Enter async context"""
        if not self._external_session:
            self._session = async_session_factory()
        
        self.threads = ThreadRepository()
        self.messages = MessageRepository()
        self.runs = RunRepository()
        self.references = ReferenceRepository()
        
        logger.debug("UnitOfWork context entered")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        if exc_type:
            await self.rollback()
            logger.error(f"UnitOfWork rolled back due to exception: {exc_val}")
        else:
            await self.commit()
            logger.debug("UnitOfWork committed successfully")
        
        if not self._external_session and self._session:
            await self._session.close()
    
    async def commit(self):
        """Commit the transaction"""
        if self._session and not self._external_session:
            try:
                await self._session.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                logger.error(f"Error committing transaction: {e}")
                await self.rollback()
                raise
    
    async def rollback(self):
        """Rollback the transaction"""
        if self._session and not self._external_session:
            try:
                await self._session.rollback()
                logger.debug("Transaction rolled back")
            except Exception as e:
                logger.error(f"Error rolling back transaction: {e}")
    
    @property
    def session(self) -> AsyncSession:
        """Get the current session"""
        if not self._session:
            raise RuntimeError("UnitOfWork must be used within async context")
        return self._session
    
    async def execute_in_transaction(self, func, *args, **kwargs):
        """Execute a function within a transaction"""
        try:
            result = await func(self, *args, **kwargs)
            await self.commit()
            return result
        except Exception as e:
            await self.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

@asynccontextmanager
async def get_unit_of_work(session: Optional[AsyncSession] = None):
    """Factory for creating UnitOfWork instances"""
    uow = UnitOfWork(session)
    async with uow:
        yield uow