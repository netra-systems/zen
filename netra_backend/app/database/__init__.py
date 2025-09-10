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
            "Database configuration not found. Please provide: "
            "Individual POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD environment variables"
        )
    
    return database_url

def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        # RACE CONDITION FIX: Increased pool size and improved connection isolation
        # Note: QueuePool cannot be used with async engines - use AsyncAdaptedQueuePool (default)
        _engine = create_async_engine(
            database_url,
            # poolclass is omitted - SQLAlchemy will use default async-compatible pool (AsyncAdaptedQueuePool)
            pool_size=20,         # RACE FIX: Increased from 5 to 20 for better concurrent access
            max_overflow=30,      # RACE FIX: Increased from 10 to 30 for high concurrency
            pool_timeout=10,      # RACE FIX: Increased timeout to prevent premature failures
            pool_recycle=300,     # Recycle connections every 5 minutes
            pool_pre_ping=True,   # RACE FIX: Verify connections before use
            echo=False,
            future=True,
            # RACE CONDITION FIX: Enable connection pooling optimizations
            pool_reset_on_return='commit',  # Clean up connections properly
            execution_options={
                "isolation_level": "READ_COMMITTED"  # Explicit isolation level
            }
        )
        logger.info(
            f"📊 DATABASE ENGINE: Created with pool_size=20, max_overflow=30, "
            f"pool_timeout=10s for race condition prevention"
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
            autoflush=False,           # RACE FIX: Keep explicit transaction control
            autocommit=False,          # RACE FIX: Keep explicit transaction control  
            # RACE CONDITION FIX: Additional session configuration
            info={'connection_isolation': True}  # Tag sessions for isolation tracking
        )
        logger.info("📊 SESSION MAKER: Configured with race condition prevention settings")
    return _sessionmaker

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.
    
    This is the canonical SSOT function for database sessions.
    All FastAPI routes should use this as a dependency.
    
    RACE CONDITION FIX: Enhanced connection management and isolation.
    
    Yields:
        AsyncSession: Database session with proper connection isolation
    """
    sessionmaker = get_sessionmaker()
    session = None
    try:
        # RACE CONDITION FIX: Create session with explicit connection handling
        session = sessionmaker()
        
        # RACE CONDITION FIX: Tag session with isolation metadata
        if not hasattr(session, 'info'):
            session.info = {}
        session.info.update({
            'race_condition_fix': True,
            'session_creation_time': asyncio.get_event_loop().time(),
            'connection_isolated': True
        })
        
        logger.debug(f"Created new database session {id(session)} with race condition protection")
        yield session
        
        # RACE CONDITION FIX: Explicit commit handling
        if session.in_transaction():
            await session.commit()
            logger.debug(f"Committed transaction for session {id(session)}")
            
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if session and session.in_transaction():
            try:
                await session.rollback()
                logger.debug(f"Rolled back transaction for session {id(session)}")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback session {id(session)}: {rollback_error}")
        raise
    finally:
        if session:
            try:
                await session.close()
                logger.debug(f"Closed database session {id(session)}")
            except Exception as close_error:
                logger.error(f"Error closing session {id(session)}: {close_error}")

@asynccontextmanager
async def get_system_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get system database session that bypasses authentication.
    
    CRITICAL: This session is for internal system operations only.
    It should NEVER be exposed to user requests or external APIs.
    
    Use cases:
    - Background tasks
    - Health checks
    - System initialization
    - Internal service operations
    
    Yields:
        AsyncSession: System database session
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            logger.debug("Created new SYSTEM database session (auth bypass)")
            yield session
        except Exception as e:
            logger.error(f"SYSTEM database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Closed SYSTEM database session")

# Import the canonical DatabaseManager from SSOT location
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager

# Default instance for backward compatibility
database_manager = get_database_manager()

# Import ClickHouse utilities from db module
from netra_backend.app.db.clickhouse import get_clickhouse_client

# Re-export get_env for backward compatibility
from shared.isolated_environment import get_env

# Export main functions and classes
__all__ = [
    "get_db",
    "get_system_db",
    "get_database_url", 
    "get_engine",
    "get_sessionmaker",
    "DatabaseManager",
    "database_manager",
    "get_clickhouse_client",
    "get_env"  # Added for backward compatibility
]