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
import time
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text

from netra_backend.app.core.config import get_config
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

# Issue #374: Enhanced database exception handling
from netra_backend.app.db.transaction_errors import (
    DeadlockError, ConnectionError, TransactionError, TimeoutError,
    PermissionError, SchemaError, classify_error, is_retryable_error
)
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError

# Expose specific exception classes for external detection (Issue #374)
DatabaseConnectionError = ConnectionError
DatabaseTimeoutError = TimeoutError
DatabasePermissionError = PermissionError
DatabaseDeadlockError = DeadlockError
DatabaseSchemaError = SchemaError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection and session management."""

    def __init__(self):
        self.config = get_config()
        self._engines: Dict[str, AsyncEngine] = {}
        self._initialized = False
        self._url_builder: Optional[DatabaseURLBuilder] = None

        # Session tracking and pool management
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._session_lifecycle_callbacks: List[Callable] = []
        self._pool_stats = {
            'total_sessions_created': 0,
            'active_sessions_count': 0,
            'sessions_cleaned_up': 0,
            'pool_exhaustion_warnings': 0,
            'context_isolation_violations': 0
        }

    async def initialize(self):
        """Initialize database connections using DatabaseURLBuilder."""
        if self._initialized:
            logger.debug("DatabaseManager already initialized, skipping")
            return

        init_start_time = time.time()
        logger.info("[🔗] Starting DatabaseManager initialization...")

        try:
            # Get database URL using DatabaseURLBuilder as SSOT
            logger.debug("Constructing database URL using DatabaseURLBuilder SSOT")
            database_url = self._get_database_url()

            # Simple database configuration
            echo = getattr(self.config, 'database_echo', False)
            pool_size = getattr(self.config, 'database_pool_size', 25)
            max_overflow = getattr(self.config, 'database_max_overflow', 25)  # Reduced from 50 to 25
            pool_timeout = getattr(self.config, 'database_pool_timeout', 30)  # 30 second timeout

            logger.info(f"[🔧] Database configuration: echo={echo}, pool_size={pool_size}, max_overflow={max_overflow}, timeout={pool_timeout}s")

            # Use appropriate pool class for async engines
            pool_recycle = 1800  # Reduced from 3600 to 1800s for faster recycling
            application_name = "netra_backend_pool"

            engine_kwargs = {
                "echo": echo,
                "pool_pre_ping": True,
                "pool_recycle": pool_recycle,
                "pool_timeout": pool_timeout,  # Add timeout to prevent hanging
                "connect_args": {
                    "command_timeout": 30,  # 30 second query timeout
                    "server_settings": {
                        "application_name": application_name
                    }
                }
            }

            # Configure pooling for async engines
            if pool_size <= 0 or "sqlite" in database_url.lower():
                # Use NullPool for SQLite or disabled pooling
                engine_kwargs["poolclass"] = NullPool
                # Remove pool_timeout for SQLite as NullPool doesn't support it
                engine_kwargs.pop("pool_timeout", None)
                # Remove connect_args for SQLite as they're PostgreSQL-specific
                engine_kwargs["connect_args"] = {}
                logger.info("[🏊] Using NullPool for SQLite or disabled pooling")
            else:
                # Use AsyncAdaptedQueuePool for better concurrent handling with async engines
                engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
                engine_kwargs["pool_size"] = pool_size
                engine_kwargs["max_overflow"] = max_overflow
                logger.info(f"[🏊] Using AsyncAdaptedQueuePool: pool_size={pool_size}, max_overflow={max_overflow}")

            logger.debug("Creating async database engine...")
            primary_engine = create_async_engine(
                database_url,
                **engine_kwargs
            )

            # Test initial connection with retry logic
            connection_success = await self._test_connection_with_retry(primary_engine)
            if not connection_success:
                raise ConnectionError("Failed to establish database connection after all retry attempts")

            self._engines['primary'] = primary_engine
            self._initialized = True

            init_duration = time.time() - init_start_time
            logger.info(f"✅ DatabaseManager initialized successfully in {init_duration:.3f}s")

        except (ConnectionError, OperationalError) as e:
            # Issue #374: Database connection and operational errors during initialization
            init_duration = time.time() - init_start_time
            classified_error = classify_error(e)
            logger.critical(f"[💥] CRITICAL: Database connection failed during initialization after {init_duration:.3f}s")
            logger.error(f"Database connection error: {type(classified_error).__name__}: {str(classified_error)}")
            logger.error(f"Check database server availability, network connectivity, and credentials")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise classified_error
        except Exception as e:
            # Issue #374: Fallback for unexpected initialization errors
            init_duration = time.time() - init_start_time
            classified_error = classify_error(e)
            logger.critical(f"[💥] CRITICAL: Unexpected database initialization failure after {init_duration:.3f}s")
            logger.error(f"Database initialization error: {type(e).__name__}: {str(e)}")
            raise classified_error

    def get_engine(self, name: str = 'primary') -> AsyncEngine:
        """Get database engine by name with auto-initialization safety."""
        if not self._initialized:
            # Auto-initialize on first access
            logger.warning("DatabaseManager accessed before initialization - auto-initializing now")
            import asyncio
            try:
                # Try to initialize synchronously if possible
                asyncio.create_task(self.initialize())
                # Give the initialization task a moment to complete
                import time
                time.sleep(0.1)  # Brief pause for initialization

                if not self._initialized:
                    raise RuntimeError(
                        "DatabaseManager auto-initialization failed. "
                        "Ensure proper startup sequence calls await manager.initialize()"
                    )
            except Exception as init_error:
                logger.error(f"Auto-initialization failed: {init_error}")
                raise RuntimeError(
                    f"DatabaseManager not initialized and auto-initialization failed: {init_error}. "
                    "Fix: Call await manager.initialize() in startup sequence."
                ) from init_error

        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found")

        return self._engines[name]

    @asynccontextmanager
    async def get_session(self, engine_name: str = 'primary', user_context: Optional[Any] = None, operation_type: str = "unknown"):
        """Get async database session with enhanced exception handling and user isolation."""
        session_start_time = time.time()

        # Extract user information from context for proper isolation
        user_id = None
        context_valid = False
        if user_context:
            try:
                user_id = getattr(user_context, 'user_id', None)
                thread_id = getattr(user_context, 'thread_id', None)
                context_valid = bool(user_id and thread_id)

                if not context_valid:
                    logger.warning(f"Invalid user context for session: user_id={user_id}, thread_id={thread_id}")
                    self._pool_stats['context_isolation_violations'] += 1
            except Exception as e:
                logger.error(f"User context extraction error: {type(e).__name__}: {e}")
                self._pool_stats['context_isolation_violations'] += 1

        session_id = f"sess_{int(session_start_time * 1000)}_{hash(user_id or 'system') % 10000}"

        # Check for pool exhaustion before creating session
        current_active = self._pool_stats['active_sessions_count']
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 25)
        total_capacity = pool_size + max_overflow

        if current_active >= total_capacity * 0.9:  # Warn at 90% capacity
            logger.warning(f"🚨 Database pool near exhaustion: {current_active}/{total_capacity} sessions active")
            self._pool_stats['pool_exhaustion_warnings'] += 1

        logger.debug(f"🔄 Starting database session {session_id} for {operation_type} (user: {user_id or 'system'})")

        # Enhanced initialization safety
        if not self._initialized:
            logger.info(f"[🔧] Auto-initializing DatabaseManager for session access (operation: {operation_type})")
            await self.initialize()

        # Track active session for pool management
        session_metadata = {
            'session_id': session_id,
            'user_id': user_id,
            'user_context': user_context,
            'operation_type': operation_type,
            'start_time': session_start_time,
            'engine_name': engine_name,
            'context_valid': context_valid
        }

        self._active_sessions[session_id] = session_metadata
        self._pool_stats['total_sessions_created'] += 1
        self._pool_stats['active_sessions_count'] += 1

        engine = self.get_engine(engine_name)
        async with AsyncSession(engine) as session:
            original_exception = None
            transaction_start_time = time.time()
            logger.debug(f"[📝] Transaction started for session {session_id}")

            try:
                yield session

                # Log successful commit
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

                logger.critical(f"[💥] SPECIFIC TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")

                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f"🔄 Rollback completed for session {session_id} in {rollback_duration:.3f}s")
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[💥] ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")

                session_duration = time.time() - session_start_time
                logger.error(f"❌ Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
                raise original_exception

            except Exception as e:
                # Handle general exceptions with enhanced error classification
                original_exception = classify_error(e)
                rollback_start_time = time.time()

                logger.critical(f"[💥] TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")

                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f"🔄 Rollback completed for session {session_id} in {rollback_duration:.3f}s")
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[💥] ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")

                session_duration = time.time() - session_start_time
                logger.error(f"❌ Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
                raise original_exception

            finally:
                close_start_time = time.time()

                # Enhanced session cleanup and tracking
                try:
                    await session.close()
                    close_duration = time.time() - close_start_time
                    logger.debug(f"[🔒] Session {session_id} closed in {close_duration:.3f}s")
                except Exception as close_error:
                    close_duration = time.time() - close_start_time
                    logger.error(f"⚠️ Session close failed for {session_id} after {close_duration:.3f}s: {close_error}")

                # Remove session from active tracking and update stats
                try:
                    if session_id in self._active_sessions:
                        session_meta = self._active_sessions.pop(session_id)
                        self._pool_stats['active_sessions_count'] -= 1
                        self._pool_stats['sessions_cleaned_up'] += 1

                        # Call lifecycle callbacks for user context cleanup
                        for callback in self._session_lifecycle_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(session_meta)
                                else:
                                    callback(session_meta)
                            except Exception as callback_error:
                                logger.warning(f"Session lifecycle callback failed: {callback_error}")

                        total_session_time = time.time() - session_start_time
                        logger.debug(f"[🧹] Session {session_id} cleanup complete - Total time: {total_session_time:.3f}s, "
                                   f"User: {user_id or 'system'}, Active sessions: {self._pool_stats['active_sessions_count']}")

                except Exception as cleanup_error:
                    logger.error(f"Session tracking cleanup failed for {session_id}: {cleanup_error}")
                    # Ensure counter is decremented even if cleanup fails
                    self._pool_stats['active_sessions_count'] = max(0, self._pool_stats['active_sessions_count'] - 1)

    async def health_check(self, engine_name: str = 'primary') -> Dict[str, Any]:
        """Perform health check on database connection with comprehensive logging."""
        health_check_start = time.time()
        logger.debug(f"[🏥] Starting database health check for engine: {engine_name}")

        try:
            # Ensure initialization before health check
            if not self._initialized:
                logger.info(f"[🔧] Initializing DatabaseManager for health check (engine: {engine_name})")
                await self.initialize()

            engine = self.get_engine(engine_name)

            # Test connection with timeout
            query_start = time.time()
            async with AsyncSession(engine) as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                health_result = result.fetchone()

            query_duration = time.time() - query_start
            total_duration = time.time() - health_check_start

            logger.info(f"✅ Database health check PASSED for {engine_name} - "
                       f"Query: {query_duration:.3f}s, Total: {total_duration:.3f}s")

            return {
                "status": "healthy",
                "engine": engine_name,
                "connection": "ok",
                "query_duration_ms": round(query_duration * 1000, 2),
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }

        except Exception as e:
            total_duration = time.time() - health_check_start
            classified_error = classify_error(e)

            logger.critical(f"[💥] Database health check FAILED for {engine_name} after {total_duration:.3f}s")
            logger.error(f"Health check error details: {type(classified_error).__name__}: {str(classified_error)}")

            return {
                "status": "unhealthy",
                "engine": engine_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current database pool statistics."""
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 25)
        total_capacity = pool_size + max_overflow

        return {
            **self._pool_stats,
            'pool_configuration': {
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'total_capacity': total_capacity
            },
            'pool_utilization': {
                'utilization_percent': round((self._pool_stats['active_sessions_count'] / total_capacity) * 100, 2),
                'sessions_remaining': total_capacity - self._pool_stats['active_sessions_count']
            },
            'active_sessions_by_user': self._get_sessions_by_user()
        }

    def _get_sessions_by_user(self) -> Dict[str, int]:
        """Get count of active sessions per user."""
        user_counts = {}
        for metadata in self._active_sessions.values():
            user_id = metadata.get('user_id', 'unknown')
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts

    async def close_all(self):
        """Close all database engines with comprehensive logging."""
        if not self._engines:
            logger.debug("No database engines to close")
            return

        logger.info(f"[🔒] Closing {len(self._engines)} database engines...")

        for name, engine in self._engines.items():
            close_start = time.time()
            try:
                await engine.dispose()
                close_duration = time.time() - close_start
                logger.info(f"✅ Closed database engine '{name}' in {close_duration:.3f}s")
            except Exception as e:
                close_duration = time.time() - close_start
                logger.error(f"❌ Error closing engine '{name}' after {close_duration:.3f}s: {e}")

        engines_count = len(self._engines)
        self._engines.clear()
        self._initialized = False
        logger.info(f"[🔒] DatabaseManager shutdown complete - {engines_count} engines closed")

    def _get_database_url(self) -> str:
        """Get database URL using DatabaseURLBuilder as SSOT."""
        env = get_env()

        # Create DatabaseURLBuilder instance if not exists
        if not self._url_builder:
            self._url_builder = DatabaseURLBuilder(env.as_dict())

        # Get URL for current environment
        database_url = self._url_builder.get_url_for_environment(sync=False)

        if not database_url:
            # Let the config handle the fallback if needed
            database_url = self.config.database_url
            if not database_url:
                raise ValueError(
                    "DatabaseURLBuilder failed to construct URL and no config fallback available. "
                    "Ensure proper POSTGRES_* environment variables are set."
                )

        # Use DatabaseURLBuilder to format URL for asyncpg driver
        database_url = self._url_builder.format_url_for_driver(database_url, 'asyncpg')

        # Log safe connection info
        logger.info(self._url_builder.get_safe_log_message())

        return database_url

    async def _test_connection_with_retry(self, engine: AsyncEngine, max_retries: int = 3, timeout: float = 10.0) -> bool:
        """Test database connection with retry logic."""
        for attempt in range(max_retries):
            attempt_start = time.time()
            try:
                logger.info(f"Testing database connection (attempt {attempt + 1}/{max_retries})")

                # Test connection with timeout
                async with AsyncSession(engine) as test_session:
                    result = await asyncio.wait_for(
                        test_session.execute(text("SELECT 1")),
                        timeout=timeout
                    )
                    test_result = result.fetchone()

                    if test_result and test_result[0] == 1:
                        attempt_duration = time.time() - attempt_start
                        logger.info(f"✅ Database connection test successful in {attempt_duration:.3f}s (attempt {attempt + 1})")
                        return True

            except asyncio.TimeoutError:
                attempt_duration = time.time() - attempt_start
                logger.error(f"❌ Database connection timeout after {attempt_duration:.3f}s (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                attempt_duration = time.time() - attempt_start
                logger.error(f"❌ Database connection error after {attempt_duration:.3f}s (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Database connection failed after {max_retries} attempts")
        return False

    @classmethod
    @asynccontextmanager
    async def get_async_session(cls, name: str = 'primary', user_id: Optional[str] = None, operation_type: str = "legacy_access"):
        """Class method for backward compatibility with code expecting DatabaseManager.get_async_session()."""
        logger.debug(f"[📞] Legacy database session access: {operation_type} (user: {user_id or 'system'})")

        manager = get_database_manager()
        if not manager._initialized:
            logger.info(f"[🔧] Ensuring DatabaseManager initialization for class method access ({operation_type})")
            await manager.initialize()

        async with manager.get_session(name, user_context=user_id, operation_type=operation_type) as session:
            yield session

    @staticmethod
    def create_application_engine() -> AsyncEngine:
        """Create a new application engine for health checks."""
        config = get_config()
        env = get_env()
        builder = DatabaseURLBuilder(env.as_dict())

        # Get URL from builder
        database_url = builder.get_url_for_environment(sync=False)
        if not database_url:
            database_url = config.database_url

        # Use DatabaseURLBuilder to format URL for asyncpg driver
        database_url = builder.format_url_for_driver(database_url, 'asyncpg')

        return create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=True,
            pool_recycle=3600,
        )


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance with auto-initialization."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
        # Auto-initialize using async pattern
        try:
            import asyncio
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.debug("No event loop available for immediate DatabaseManager initialization")

            if loop is not None:
                try:
                    asyncio.create_task(_database_manager.initialize())
                    logger.debug("Scheduled DatabaseManager initialization as async task")
                except Exception as init_error:
                    logger.warning(f"Could not schedule immediate initialization: {init_error}")
        except Exception as e:
            logger.warning(f"Auto-initialization setup failed, will initialize on first use: {e}")

    return _database_manager


@asynccontextmanager
async def get_db_session(engine_name: str = 'primary'):
    """Helper to get database session."""
    manager = get_database_manager()
    async with manager.get_session(engine_name) as session:
        yield session