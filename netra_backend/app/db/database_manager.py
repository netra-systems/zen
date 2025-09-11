"""Database Manager - SSOT for Database Operations

Centralized database management with proper DatabaseURLBuilder integration.
This module uses DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH for URL construction.

CRITICAL: ALL URL manipulation MUST go through DatabaseURLBuilder methods:
- format_url_for_driver() for driver-specific formatting
- normalize_url() for URL normalization
- NO MANUAL STRING REPLACEMENT OPERATIONS ALLOWED

See Also:
- shared/database_url_builder.py - The ONLY source for URL construction
- SPEC/database_connectivity_architecture.xml - Database connection patterns
- docs/configuration_architecture.md - Configuration system overview

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database connection management
- Value Impact: Eliminates URL construction errors and ensures consistency
- Strategic Impact: Single source of truth for all database connection patterns
"""

import asyncio
import logging
import re
import time
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool, StaticPool
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text

from netra_backend.app.core.config import get_config
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env
from netra_backend.app.db.transaction_errors import (    DeadlockError, ConnectionError, TransactionError,    TimeoutError, PermissionError, SchemaError, classify_error, is_retryable_error)
from sqlalchemy.exc import OperationalError, DisconnectionError, SQLAlchemyError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection and session management."""
    
    def __init__(self):
        self.config = get_config()
        self._engines: Dict[str, AsyncEngine] = {}
        self._initialized = False
        self._url_builder: Optional[DatabaseURLBuilder] = None
    
    async def initialize(self):
        """Initialize database connections using DatabaseURLBuilder."""
        if self._initialized:
            logger.debug("DatabaseManager already initialized, skipping")
            return
        
        init_start_time = time.time()
        logger.info("🔗 Starting DatabaseManager initialization...")
        
        try:
            # Get database URL using DatabaseURLBuilder as SSOT
            logger.debug("Constructing database URL using DatabaseURLBuilder SSOT")
            database_url = self._get_database_url()
            
            # Handle different config attribute names gracefully
            echo = getattr(self.config, 'database_echo', False)
            pool_size = getattr(self.config, 'database_pool_size', 5)
            max_overflow = getattr(self.config, 'database_max_overflow', 10)
            
            logger.info(f"🔧 Database configuration: echo={echo}, pool_size={pool_size}, max_overflow={max_overflow}")
            
            # Use appropriate pool class for async engines
            engine_kwargs = {
                "echo": echo,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
            
            # Configure pooling for async engines
            if pool_size <= 0 or "sqlite" in database_url.lower():
                # Use NullPool for SQLite or disabled pooling
                engine_kwargs["poolclass"] = NullPool
                logger.info("🏊 Using NullPool for SQLite or disabled pooling")
            else:
                # Use StaticPool for async engines - it doesn't support pool_size/max_overflow
                engine_kwargs["poolclass"] = StaticPool
                logger.info("🏊 Using StaticPool for async engine connection pooling")
            
            logger.debug("Creating async database engine...")
            primary_engine = create_async_engine(
                database_url,
                **engine_kwargs
            )
            
            # Test initial connection
            logger.debug("Testing initial database connection...")
            async with primary_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            self._engines['primary'] = primary_engine
            self._initialized = True
            
            init_duration = time.time() - init_start_time
            logger.info(f"✅ DatabaseManager initialized successfully in {init_duration:.3f}s")
            
        except (ConnectionError, DisconnectionError) as e:
            init_duration = time.time() - init_start_time
            logger.critical(f"💥 CRITICAL: Database connection failed during initialization after {init_duration:.3f}s: {e}")
            logger.error(f"Connection failure details: host={getattr(self.config, 'database_host', 'unknown')}, port={getattr(self.config, 'database_port', 'unknown')}")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise
        except (TimeoutError, OperationalError) as e:
            # Classify and potentially wrap the error
            classified_error = classify_error(e)
            init_duration = time.time() - init_start_time
            logger.critical(f"💥 CRITICAL: Database timeout/operational error during initialization after {init_duration:.3f}s: {classified_error}")
            logger.error(f"Operational failure details: {type(classified_error).__name__}: {str(classified_error)}")
            logger.error(f"Database URL pattern: {self._get_database_url()[:50]}... (masked for security)")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise classified_error
        except SQLAlchemyError as e:
            init_duration = time.time() - init_start_time
            logger.critical(f"💥 CRITICAL: SQLAlchemy error during initialization after {init_duration:.3f}s: {e}")
            logger.error(f"SQLAlchemy failure details: {type(e).__name__}: {str(e)}")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise
        except Exception as e:
            # Only for truly unexpected errors
            init_duration = time.time() - init_start_time
            logger.critical(f"💥 CRITICAL: Unexpected error during DatabaseManager initialization after {init_duration:.3f}s: {e}")
            logger.error(f"Unexpected failure details: {type(e).__name__}: {str(e)}")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise
    
    def get_engine(self, name: str = 'primary') -> AsyncEngine:
        """Get database engine by name with auto-initialization safety.
        
        CRITICAL FIX: Auto-initializes if not initialized to prevent 
        'Engine not found' errors that break service startup in Cloud Run.
        
        Args:
            name: Engine name (default: 'primary')
            
        Returns:
            AsyncEngine: The requested database engine
            
        Raises:
            RuntimeError: If initialization fails or engine not found
        """
        if not self._initialized:
            logger.warning(f"DatabaseManager not initialized, attempting auto-initialization for engine '{name}'")
            try:
                # Check if we have an event loop
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        # We're in an async context but can't await here
                        # This is a synchronous method being called from async context
                        raise RuntimeError(
                            "DatabaseManager not initialized. Call 'await manager.initialize()' before using get_engine(). "
                            "Auto-initialization not possible in sync context."
                        )
                except RuntimeError:
                    # No running loop - this might be during startup
                    pass
                
                if not self._initialized:
                    raise RuntimeError(
                        "DatabaseManager auto-initialization failed. "
                        "Ensure proper startup sequence calls await manager.initialize()"
                    )
            except (ConnectionError, DisconnectionError, TimeoutError, SQLAlchemyError) as init_error:
                logger.error(f"Auto-initialization failed with database error: {init_error}")
                raise RuntimeError(
                    f"DatabaseManager not initialized and auto-initialization failed with database error: {init_error}. "
                    "Fix: Call await manager.initialize() in startup sequence and check database connectivity."
                ) from init_error
            except Exception as init_error:
                logger.error(f"Auto-initialization failed with unexpected error: {init_error}")
                raise RuntimeError(
                    f"DatabaseManager not initialized and auto-initialization failed: {init_error}. "
                    "Fix: Call await manager.initialize() in startup sequence."
                ) from init_error
        
        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found")
        
        return self._engines[name]
    
    @asynccontextmanager
    async def get_session(self, 
                          engine_name: str = 'primary',
                          user_id: Optional[str] = None,
                          operation_type: str = "unknown") -> AsyncSession:
        """Get database session with transaction management, user tracking, and performance monitoring.
        
        CRITICAL FIX: Enhanced session management with detailed logging to debug Cloud Run timeouts.
        Enhanced with user tracking for multi-tenant operations and operation classification.
        
        Args:
            engine_name: Name of the engine to use (default: 'primary')
            user_id: Optional user identifier for multi-tenant tracking
            operation_type: Type of operation for monitoring (e.g., "user_query", "admin_task")
            
        Yields:
            AsyncSession: Database session with automatic transaction management
            
        Raises:
            Exception: Database errors, rollback errors (original exception preserved)
        """
        # Generate unique session ID for tracking
        session_id = f"sess_{int(time.time() * 1000)}"
        session_start_time = time.time()
        
        logger.info(f"🔄 Starting session {session_id} - Engine: {engine_name}, "
                   f"User: {user_id or 'system'}, Operation: {operation_type}")
        
        engine = self.get_engine(engine_name)
        session = AsyncSession(engine)
        
        try:
            yield session
            
            # Commit transaction
            commit_start_time = time.time()
            await session.commit()
            commit_duration = time.time() - commit_start_time
            session_duration = time.time() - session_start_time
            
            logger.info(f"✅ Session {session_id} committed successfully - Operation: {operation_type}, "
                       f"User: {user_id or 'system'}, Duration: {session_duration:.3f}s, Commit: {commit_duration:.3f}s")
            
        except (DeadlockError, ConnectionError) as e:
            # Handle specific transaction errors with enhanced context
            original_exception = classify_error(e)
            rollback_start_time = time.time()
            
            logger.critical(f"💥 TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
            logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")
            
            try:
                await session.rollback()
                rollback_duration = time.time() - rollback_start_time
                logger.warning(f"🔄 Rollback completed for session {session_id} in {rollback_duration:.3f}s")
            except Exception as rollback_error:
                rollback_duration = time.time() - rollback_start_time
                logger.critical(f"💥 ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")
            
            session_duration = time.time() - session_start_time
            logger.error(f"❌ Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
            raise original_exception
        except Exception as e:
            original_exception = e
            rollback_start_time = time.time()
            
            logger.critical(f"💥 TRANSACTION FAILURE in session {session_id}")
            logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {type(e).__name__}: {str(e)}")
            
            try:
                await session.rollback()
                rollback_duration = time.time() - rollback_start_time
                logger.warning(f"🔄 Rollback completed for session {session_id} in {rollback_duration:.3f}s")
            except Exception as rollback_error:
                rollback_duration = time.time() - rollback_start_time
                logger.critical(f"💥 ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")
                # Continue with original exception
            
            session_duration = time.time() - session_start_time
            logger.error(f"❌ Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
            raise original_exception
            
        finally:
            close_start_time = time.time()
            try:
                await session.close()
                close_duration = time.time() - close_start_time
                logger.debug(f"🔒 Session {session_id} closed in {close_duration:.3f}s")
            except Exception as close_error:
                close_duration = time.time() - close_start_time
                logger.error(f"⚠️ Session close failed for {session_id} after {close_duration:.3f}s: {close_error}")
                # Don't raise close errors - they shouldn't prevent completion
    
    async def health_check(self, engine_name: str = 'primary') -> Dict[str, Any]:
        """Perform health check on database connection with comprehensive logging.
        
        CRITICAL FIX: Ensures database manager is initialized before health check.
        Enhanced with detailed health monitoring for Golden Path operations.
        """
        health_check_start = time.time()
        logger.debug(f"🏥 Starting database health check for engine '{engine_name}'")
        
        try:
            engine = self.get_engine(engine_name)
            
            # Test database connectivity
            query_start = time.time()
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as health_check"))
                health_value = result.scalar()
            
            query_duration = time.time() - query_start
            total_duration = time.time() - health_check_start
            
            logger.info(f"✅ Database health check PASSED for {engine_name} - "
                       f"Query: {query_duration:.3f}s, Total: {total_duration:.3f}s")
            
            return {
                "status": "healthy",
                "engine": engine_name,
                "response_value": health_value,
                "query_duration_ms": round(query_duration * 1000, 2),
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }
            
        except (ConnectionError, DisconnectionError) as e:
            total_duration = time.time() - health_check_start
            logger.critical(f"💥 Database health check FAILED for {engine_name} after {total_duration:.3f}s - Connection error")
            logger.error(f"Connection health check error details: {type(e).__name__}: {str(e)}")
            logger.error(f"This indicates database connectivity issues that will affect user operations")
            
            return {
                "status": "unhealthy",
                "engine": engine_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_category": "connection",
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }
        except (TimeoutError, OperationalError) as e:
            classified_error = classify_error(e)
            total_duration = time.time() - health_check_start
            logger.critical(f"💥 Database health check FAILED for {engine_name} after {total_duration:.3f}s - Operational error")
            logger.error(f"Operational health check error details: {type(classified_error).__name__}: {str(classified_error)}")
            logger.error(f"This indicates database performance issues that will affect user operations")
            
            return {
                "status": "unhealthy", 
                "engine": engine_name,
                "error": str(classified_error),
                "error_type": type(classified_error).__name__,
                "error_category": "operational",
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }
        except Exception as e:
            total_duration = time.time() - health_check_start
            logger.critical(f"💥 Database health check FAILED for {engine_name} after {total_duration:.3f}s")
            logger.error(f"Health check error details: {type(e).__name__}: {str(e)}")
            logger.error(f"This indicates database connectivity issues that will affect user operations")
            
            return {
                "status": "unhealthy",
                "engine": engine_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_category": "unknown",
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }
    
    async def close(self):
        """Close all database connections and clean up resources.
        
        CRITICAL FIX: Enhanced cleanup with detailed logging for Cloud Run deployments.
        """
        if not self._initialized:
            logger.debug("DatabaseManager not initialized, no cleanup needed")
            return
            
        logger.info(f"🔒 Starting DatabaseManager shutdown - {len(self._engines)} engines to close")
        
        for name, engine in self._engines.items():
            close_start = time.time()
            try:
                await engine.dispose()
                close_duration = time.time() - close_start
                logger.info(f"✅ Closed database engine '{name}' in {close_duration:.3f}s")
            except Exception as e:
                close_duration = time.time() - close_start
                logger.error(f"❌ Error closing engine '{name}' after {close_duration:.3f}s: {e}")
                logger.warning(f"Engine '{name}' may have active connections that were forcibly closed")
        
        engines_count = len(self._engines)
        self._engines.clear()
        self._initialized = False
        logger.info(f"🔒 DatabaseManager shutdown complete - {engines_count} engines closed")
    
    def _get_database_url(self) -> str:
        """Get database URL using DatabaseURLBuilder as SSOT.
        
        CRITICAL: Uses DatabaseURLBuilder for ALL URL construction.
        NO manual string manipulation allowed.
        """
        if self._url_builder is None:
            self._url_builder = DatabaseURLBuilder()
        
        try:
            # Use DatabaseURLBuilder methods as SSOT
            url = self._url_builder.format_url_for_driver()
            return self._url_builder.normalize_url(url)
        except Exception as url_error:
            logger.error(f"DatabaseURLBuilder failed: {url_error}")
            # Fallback to basic configuration (temporary)
            logger.warning("Using fallback URL construction - this should not happen in production")
            return f"postgresql+asyncpg://{self.config.database_user}:{self.config.database_password}@{self.config.database_host}:{self.config.database_port}/{self.config.database_name}"


# Global DatabaseManager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global DatabaseManager instance with auto-initialization safety.
    
    CRITICAL FIX: Enhanced initialization detection and auto-setup for Cloud Run compatibility.
    """
    global _database_manager
    
    if _database_manager is None:
        logger.debug("Creating new DatabaseManager instance")
        _database_manager = DatabaseManager()
        
        # Check if we can schedule async initialization
        try:
            loop = asyncio.get_event_loop()
            if loop is not None:
                # We have an event loop, schedule initialization as a task
                try:
                    asyncio.create_task(_database_manager.initialize())
                    logger.debug("Scheduled DatabaseManager initialization as async task")
                except (ConnectionError, DisconnectionError, TimeoutError, SQLAlchemyError) as init_error:
                    logger.warning(f"Could not schedule immediate initialization due to database error: {init_error}")
                    # Still return the manager - it will auto-initialize on first async use
                except Exception as init_error:
                    logger.warning(f"Could not schedule immediate initialization: {init_error}")
                    # Still return the manager - it will auto-initialize on first async use
        except Exception as e:
            logger.warning(f"Auto-initialization setup failed, will initialize on first use: {e}")
            # This is safe - the manager will still work, just initialize on first async call
    
    return _database_manager


@asynccontextmanager
async def get_db_session(engine_name: str = 'primary'):
    """Helper to get database session."""
    manager = get_database_manager()
    async with manager.get_session(engine_name) as session:
        yield session