"""Database module - Single Source of Truth (SSOT) for database operations.

This module provides the canonical database interface for the Netra backend application.
All database imports should come from this module to maintain SSOT compliance.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability & Development Velocity  
- Value Impact: Eliminates circular imports and provides consistent database interface
- Strategic Impact: Foundation for reliable database operations across all services
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Global database engine and sessionmaker
_engine = None
_sessionmaker = None

def get_database_url() -> str:
    """Get database URL from environment."""
    from netra_backend.app.core.backend_environment import get_backend_env
    
    # Use backend_environment which now uses DatabaseURLBuilder internally
    database_url = get_backend_env().get_database_url(sync=False)  # async for SQLAlchemy
    
    if not database_url:
        raise RuntimeError(
            "Database configuration not found. Please provide either: "
            "1) Individual POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD environment variables, or "
            "2) A complete DATABASE_URL environment variable (deprecated, use individual variables instead)"
        )
    
    return database_url

def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            poolclass=NullPool,  # Use NullPool for now to avoid connection issues
            echo=False,
            future=True
        )
    return _engine

def get_sessionmaker():
    """Get or create session maker."""
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine()
        _sessionmaker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
    return _sessionmaker

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.
    
    This is the canonical SSOT function for database sessions.
    All FastAPI routes should use this as a dependency.
    
    Yields:
        AsyncSession: Database session
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            logger.debug("Created new database session")
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Closed database session")

class DatabaseManager:
    """
    Database Manager class for backward compatibility.
    
    This class provides the DatabaseManager interface that other modules expect.
    """
    
    def __init__(self):
        self._engine = None
        self._sessionmaker = None
    
    @property
    def engine(self):
        """Get database engine."""
        return get_engine()
    
    @property
    def sessionmaker(self):
        """Get session maker."""
        return get_sessionmaker()
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        sessionmaker = get_sessionmaker()
        return sessionmaker()
    
    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database sessions."""
        async with get_db() as session:
            yield session

# Default instance for backward compatibility
database_manager = DatabaseManager()

# Import ClickHouse utilities from db module
from netra_backend.app.db.clickhouse import get_clickhouse_client

# Export main functions and classes
__all__ = [
    "get_db",
    "get_database_url", 
    "get_engine",
    "get_sessionmaker",
    "DatabaseManager",
    "database_manager",
    "get_clickhouse_client"
]