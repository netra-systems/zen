"""Unit of Work Pattern Implementation

Manages database transactions and repositories in a single context.
"""

from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres import (
    async_session_factory,
    get_session_validation_error,
    validate_session,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.reference_repository import ReferenceRepository
from netra_backend.app.services.database.run_repository import RunRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository

logger = central_logger.get_logger(__name__)

class UnitOfWork:
    """Unit of Work pattern for managing database transactions"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session
        self._session_context = None
        self._external_session = session is not None
        self.threads: Optional[ThreadRepository] = None
        self.messages: Optional[MessageRepository] = None
        self.runs: Optional[RunRepository] = None
        self.references: Optional[ReferenceRepository] = None
    
    async def __aenter__(self):
        """Enter async context"""
        if not self._external_session:
            if async_session_factory is None:
                raise RuntimeError("Database not configured - async_session_factory is None")
            # Properly create a session using the async session factory
            self._session_context = async_session_factory()
            self._session = await self._session_context.__aenter__()
            if not validate_session(self._session):
                error_msg = get_session_validation_error(self._session)
                raise RuntimeError(f"UnitOfWork session error: {error_msg}")
            
        self._init_repositories()
        logger.debug("UnitOfWork context entered")
        return self
    
    def _init_repositories(self):
        """Initialize repositories and inject session."""
        self.threads = ThreadRepository()
        self.messages = MessageRepository()
        self.runs = RunRepository()
        self.references = ReferenceRepository()
        
        # Inject session into repositories
        self.threads._session = self._session
        self.messages._session = self._session
        self.runs._session = self._session
        self.references._session = self._session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        if exc_type:
            await self.rollback()
            logger.error(f"UnitOfWork rolled back due to exception: {exc_val}")
        else:
            await self.commit()
            logger.debug("UnitOfWork committed successfully")
        
        if not self._external_session:
            if self._session:
                await self._session.close()
            if hasattr(self, '_session_context'):
                await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
    
    async def commit(self):
        """Commit the transaction"""
        if self._session:
            if not validate_session(self._session):
                error_msg = get_session_validation_error(self._session)
                logger.error(f"Invalid session type for commit: {error_msg}")
                raise RuntimeError(f"Cannot commit - {error_msg}")
            try:
                await self._session.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                logger.error(f"Error committing transaction: {e}")
                await self.rollback()
                raise
    
    async def rollback(self):
        """Rollback the transaction"""
        if self._session:
            if not validate_session(self._session):
                error_msg = get_session_validation_error(self._session)
                logger.error(f"Invalid session type for rollback: {error_msg}")
                return  # Can't rollback if not a valid session
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
    
    async def initialize(self):
        """Initialize the UnitOfWork - for backward compatibility with tests"""
        if not self._external_session:
            if async_session_factory is None:
                raise RuntimeError("Database not configured - async_session_factory is None")
            # Properly create a session using the async session factory
            self._session_context = async_session_factory()
            self._session = await self._session_context.__aenter__()
            if not validate_session(self._session):
                error_msg = get_session_validation_error(self._session)
                raise RuntimeError(f"UnitOfWork session error: {error_msg}")
        
        self._init_repositories()
        logger.debug("UnitOfWork initialized")
    
    async def close(self):
        """Close the UnitOfWork - for backward compatibility with tests"""
        if not self._external_session and hasattr(self, '_session_context'):
            await self._session_context.__aexit__(None, None, None)
            logger.debug("UnitOfWork closed")
    
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