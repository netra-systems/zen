from shared.isolated_environment import get_env

"""PostgreSQL core connection and engine setup module.

Handles database engine creation, connection management, and initialization.
Focused module adhering to 25-line function limit and modular architecture.
"""

import asyncio
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, QueuePool

from netra_backend.app.db.postgres_events import (
    setup_async_engine_events,
    setup_sync_engine_events,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.configuration.base import get_unified_config


# Import settings lazily to avoid circular dependency
def get_settings():
    """Get settings lazily to avoid circular import."""
    return get_unified_config()

logger = central_logger.get_logger(__name__)


class Database:
    """Synchronous database connection manager with proper pooling."""
    
    def _get_pool_class(self, db_url: str):
        """Determine appropriate pool class for database type."""
        return NullPool if "sqlite" in db_url else QueuePool
    
    def _get_pool_size(self, pool_class) -> int:
        """Get pool size based on pool class with resilient defaults."""
        # Increase pool size for better resilience
        config = get_unified_config()
        base_size = config.db_pool_size if pool_class == QueuePool else 0
        return max(base_size, 10) if pool_class == QueuePool else 0

    def _get_max_overflow(self, pool_class) -> int:
        """Get max overflow based on pool class with resilient defaults."""
        # Increase overflow for better resilience
        config = get_unified_config()
        base_overflow = config.db_max_overflow if pool_class == QueuePool else 0
        return max(base_overflow, 20) if pool_class == QueuePool else 0

    def _create_engine(self, db_url: str, pool_class):
        """Create database engine with resilient pooling configuration."""
        config = get_unified_config()
        
        # Determine connect_args based on connection type
        # Cloud SQL connections may not support PostgreSQL options parameter
        connect_args = {}
        if "cloudsql" not in db_url.lower():
            connect_args = {"options": "-c default_transaction_isolation=read_committed"}
        
        return create_engine(
            db_url, echo=config.db_echo, echo_pool=config.db_echo_pool,
            poolclass=pool_class, pool_size=self._get_pool_size(pool_class),
            max_overflow=self._get_max_overflow(pool_class), 
            pool_timeout=max(config.db_pool_timeout, 60),  # Increased timeout for resilience
            pool_recycle=config.db_pool_recycle, 
            pool_pre_ping=True,  # Always enable pre-ping for resilience
            # Additional resilience settings
            pool_reset_on_return='rollback',  # Reset connections safely
            connect_args=connect_args
        )
    
    def _create_session_factory(self):
        """Create optimized session factory bound to engine."""
        return sessionmaker(
            autocommit=False, autoflush=False,
            bind=self.engine, expire_on_commit=False
        )
    
    def __init__(self, db_url: str):
        """Initialize database with optimized connection pooling."""
        pool_class = self._get_pool_class(db_url)
        self.engine = self._create_engine(db_url, pool_class)
        self.SessionLocal = self._create_session_factory()
        try:
            setup_sync_engine_events(self.engine)
        except Exception:
            # Skip event setup for mock engines in tests
            pass

    def _execute_connection_test(self):
        """Execute database connection test query."""
        with self.engine.connect() as conn:
            conn.execute("SELECT 1")
            logger.info("Database connection test successful")
    
    def connect(self):
        """Test database connectivity with resilient error handling."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self._execute_connection_test()
                if attempt > 0:
                    logger.info(f"Database connection successful on attempt {attempt + 1}")
                return
            except Exception as e:
                if attempt == max_attempts - 1:
                    logger.error(f"Database connection test failed after {max_attempts} attempts: {e}")
                    raise
                else:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}, retrying...")
                    import time
                    time.sleep(1 * (attempt + 1))  # Progressive delay

    def _handle_transaction_error(self, db: Session, e: Exception):
        """Handle database transaction error with rollback and logging."""
        db.rollback()
        logger.error(f"Database transaction rolled back: {e}")
        raise
    
    def _create_session(self) -> Session:
        """Create new database session."""
        return self.SessionLocal()

    def _commit_session(self, db: Session):
        """Commit database session."""
        db.commit()

    def _close_session(self, db: Session):
        """Close database session."""
        db.close()

    def _execute_db_transaction(self, db: Session):
        """Execute database transaction."""
        yield db
        self._commit_session(db)

    def _handle_db_session_error(self, db: Session, e: Exception):
        """Handle database session error."""
        self._handle_transaction_error(db, e)
        self._close_session(db)

    def _manage_db_session(self):
        """Manage database session lifecycle."""
        db = self._create_session()
        try:
            yield from self._execute_db_transaction(db)
        except Exception as e:
            self._handle_db_session_error(db, e)
        else: self._close_session(db)

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """DEPRECATED: Use netra_backend.app.database.get_db() for SSOT compliance.
        
        This method provides a transactional scope around a series of operations
        but violates the Single Source of Truth principle. New code should use
        the canonical implementation from netra_backend.app.database.
        """
        import warnings
        warnings.warn(
            "Database.get_db() is deprecated. Use 'from netra_backend.app.database import get_db' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        yield from self._manage_db_session()

    def close(self):
        """Close all database connections."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("Database connections closed")


# PostgreSQL async engine with proper configuration
async_engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker] = None


class AsyncDatabase:
    """Asynchronous database connection manager with proper pooling and resilience.
    
    Provides async database operations with connection pool management,
    retry logic, and graceful error handling for cold start scenarios.
    """
    
    def __init__(self, db_url: str = None):
        """Initialize AsyncDatabase with optional URL override.
        
        Args:
            db_url: Optional database URL override. If None, uses SSOT method.
        """
        from netra_backend.app.database import get_database_url
        self.db_url = db_url or get_database_url()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._connection_lock = asyncio.Lock()
        self._initialization_complete = False
        
        # Initialize engine immediately if URL is provided - needed for tests and immediate usage
        if db_url:
            # For tests, immediately call the initialization to trigger create_async_engine
            self._initialize_engine_sync()
        
    async def _ensure_initialized(self):
        """Ensure database is initialized with thread-safe lazy loading."""
        if self._initialization_complete and self._engine and self._session_factory:
            return
            
        async with self._connection_lock:
            # Double-check after acquiring lock
            if self._initialization_complete and self._engine and self._session_factory:
                return
                
            await self._initialize_engine()
            self._initialization_complete = True
    
    def _initialize_engine_sync(self):
        """Initialize async engine synchronously for constructor usage."""
        # Delegate to the main engine initialization logic to avoid duplication
        self._do_initialize_engine()
        self._initialization_complete = True
        logger.info("AsyncDatabase engine initialized with resilient configuration")
    
    def _do_initialize_engine(self):
        """Common engine initialization logic used by both sync and async methods."""
        pool_class = AsyncAdaptedQueuePool if "sqlite" not in self.db_url else NullPool
        
        # Validate URL for asyncpg compatibility
        if not self.db_url:
            raise RuntimeError(f"Database URL validation failed for asyncpg: {self.db_url}")
        
        engine_args = {
            "echo": False,  # Disable to reduce logging noise
            "echo_pool": False,  # Disable pool logging to reduce noise
            "poolclass": pool_class,
            "pool_pre_ping": True,  # Enable connection health checks
            "pool_reset_on_return": "rollback",  # Safe connection resets
        }
        
        # Add pool sizing for non-NullPool connections with environment-aware optimization
        if pool_class != NullPool:
            config = get_unified_config()
            
            # Get environment-aware database configuration
            from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config
            environment = get_env().get("ENVIRONMENT", "development")
            cloud_sql_config = get_cloud_sql_optimized_config(environment)
            
            # Use Cloud SQL optimized configuration if available
            pool_config = cloud_sql_config["pool_config"]
            engine_args.update({
                "pool_size": pool_config["pool_size"],
                "max_overflow": pool_config["max_overflow"],
                "pool_timeout": pool_config["pool_timeout"],
                "pool_recycle": pool_config["pool_recycle"],
                "pool_pre_ping": pool_config["pool_pre_ping"],
                "pool_reset_on_return": pool_config["pool_reset_on_return"],
            })
            
            # Use Cloud SQL optimized connection arguments
            engine_args["connect_args"] = cloud_sql_config["connect_args"]
        
        self._engine = create_async_engine(self.db_url, **engine_args)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        try:
            setup_async_engine_events(self._engine)
        except Exception:
            # Skip event setup for mock engines in tests
            pass

    async def _initialize_engine(self):
        """Initialize async engine with resilient pool configuration."""
        self._do_initialize_engine()
        logger.info("AsyncDatabase engine initialized with resilient configuration")
    
    async def test_connection_with_retry(self, max_retries: int = 5, base_delay: float = 1.0) -> bool:
        """Test database connection with exponential backoff retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        await self._ensure_initialized()
        
        for attempt in range(max_retries):
            try:
                # Use timeout to prevent hanging
                async with asyncio.wait_for(self._engine.begin(), timeout=15.0) as conn:
                    await conn.execute("SELECT 1")
                    logger.debug(f"Database connection test successful on attempt {attempt + 1}")
                    return True
                    
            except Exception as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {max_retries} connection attempts failed: {e}")
        
        return False
    
    async def get_session(self) -> AsyncSession:
        """Get async database session with connection validation.
        
        Returns:
            Configured AsyncSession instance
        """
        await self._ensure_initialized()
        return self._session_factory()
    
    async def execute_with_retry(self, query, params=None, max_retries: int = 3):
        """Execute query with retry logic for connection failures.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            max_retries: Maximum retry attempts
            
        Returns:
            Query result
        """
        for attempt in range(max_retries):
            try:
                async with self.get_session() as session:
                    if params:
                        result = await session.execute(query, params)
                    else:
                        result = await session.execute(query)
                    # Only commit if session is active and has a transaction
                    if hasattr(session, 'is_active') and session.is_active:
                        if hasattr(session, 'in_transaction') and session.in_transaction():
                            await session.commit()
                    return result
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"Query execution attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    # Force re-initialization on connection errors
                    if "connection" in str(e).lower() or "pool" in str(e).lower():
                        self._initialization_complete = False
                        await self._ensure_initialized()
                else:
                    logger.error(f"Query execution failed after {max_retries} attempts: {e}")
                    raise
    
    async def get_pool_status(self) -> dict:
        """Get connection pool status for monitoring.
        
        Returns:
            Dictionary with pool statistics
        """
        await self._ensure_initialized()
        
        if hasattr(self._engine.pool, 'size'):
            pool_stats = {
                "pool_size": self._engine.pool.size(),
                "checked_in": self._engine.pool.checkedin(),
                "checked_out": self._engine.pool.checkedout(),
                "overflow": self._engine.pool.overflow(),
                "engine_disposed": self._engine.pool._invalidate_time is not None,
            }
            
            # CRITICAL FIX: AsyncAdaptedQueuePool doesn't have invalid() or invalidated() methods
            # These methods only exist on synchronous pools
            pool_stats["pool_type"] = type(self._engine.pool).__name__
            
            return pool_stats
        return {"status": "Pool status unavailable"}
    
    async def close(self):
        """Close database connections gracefully."""
        if self._engine:
            await self._engine.dispose()
            logger.info("AsyncDatabase connections closed")
            self._engine = None
            self._session_factory = None
            self._initialization_complete = False




def _get_pool_class_for_async(async_db_url: str):
    """Get appropriate pool class for async database."""
    return AsyncAdaptedQueuePool if "sqlite" not in async_db_url else NullPool


def _get_base_engine_args(pool_class):
    """Get base engine arguments for all pool types."""
    config = get_unified_config()
    return {
        "echo": False,  # Disable to reduce logging noise in dev
        "echo_pool": False,  # Disable pool logging to reduce noise
        "poolclass": pool_class,
    }

def _get_pool_sizing_args():
    """Get pool sizing arguments with environment-aware Cloud SQL optimization."""
    from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config
    environment = get_env().get("ENVIRONMENT", "development")
    cloud_sql_config = get_cloud_sql_optimized_config(environment)
    
    pool_config = cloud_sql_config["pool_config"]
    return {
        "pool_size": pool_config["pool_size"],
        "max_overflow": pool_config["max_overflow"],
    }

def _get_pool_timing_args():
    """Get pool timing arguments with environment-aware Cloud SQL optimization."""
    from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config
    environment = get_env().get("ENVIRONMENT", "development")
    cloud_sql_config = get_cloud_sql_optimized_config(environment)
    
    pool_config = cloud_sql_config["pool_config"]
    return {
        "pool_timeout": pool_config["pool_timeout"],
        "pool_recycle": pool_config["pool_recycle"],
        "pool_pre_ping": pool_config["pool_pre_ping"],
        "pool_reset_on_return": pool_config["pool_reset_on_return"],
    }

def _get_pool_specific_args():
    """Get pool-specific arguments for non-NullPool."""
    args = _get_pool_sizing_args()
    args.update(_get_pool_timing_args())
    return args

def _build_engine_args(pool_class):
    """Build engine arguments based on pool class."""
    engine_args = _get_base_engine_args(pool_class)
    if pool_class != NullPool:
        engine_args.update(_get_pool_specific_args())
    return engine_args


def _create_async_session_factory(engine: AsyncEngine):
    """Create async session factory."""
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False,
        autocommit=False, autoflush=False
    )


def _validate_database_url():
    """Validate database URL configuration using SSOT method."""
    try:
        from netra_backend.app.database import get_database_url
        async_db_url = get_database_url()
        if not async_db_url:
            logger.warning("Database URL not configured")
            return None
        return async_db_url
    except Exception as e:
        logger.error(f"Failed to get database URL from SSOT: {e}")
        return None

def _create_engine_components(async_db_url: str):
    """Create engine components from async database URL."""
    pool_class = _get_pool_class_for_async(async_db_url)
    engine_args = _build_engine_args(pool_class)
    return engine_args

def _setup_global_engine_objects(engine):
    """Setup global engine and session factory objects."""
    global async_engine, async_session_factory
    async_engine = engine
    async_session_factory = _create_async_session_factory(async_engine)
    setup_async_engine_events(async_engine)

def _handle_engine_creation_error(e):
    """Handle engine creation error with resilient logging and graceful degradation."""
    logger.error(f"Failed to create PostgreSQL async engine: {e}")
    
    # Try to set up resilience manager in degraded state
    try:
        from netra_backend.app.db.postgres_resilience import postgres_resilience
        postgres_resilience.set_connection_health(False)
        logger.warning("PostgreSQL resilience manager set to degraded state")
    except ImportError:
        pass  # Resilience module not available
    
    raise RuntimeError(f"Database engine creation failed: {e}") from e

def _create_and_setup_engine(async_db_url: str, engine_args: dict):
    """Create engine and setup global objects with resilient configuration."""
    # CRITICAL: Validate URL conversion to prevent sslmode regression
    if not async_db_url:
        raise RuntimeError(f"CRITICAL: Database URL validation failed. "
                          f"URL may contain incompatible parameters for asyncpg. URL: {async_db_url}")
    
    # Use environment-aware connection arguments for Cloud SQL optimization
    from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config
    environment = get_env().get("ENVIRONMENT", "development")
    cloud_sql_config = get_cloud_sql_optimized_config(environment)
    
    # Override with Cloud SQL optimized connection arguments
    engine_args["connect_args"] = cloud_sql_config["connect_args"]
    
    engine = create_async_engine(async_db_url, **engine_args)
    _setup_global_engine_objects(engine)
    logger.info("PostgreSQL async engine created with resilient AsyncAdaptedQueuePool connection pooling")

def _initialize_engine_with_url(async_db_url: str):
    """Initialize engine with validated URL."""
    engine_args = _create_engine_components(async_db_url)
    _create_and_setup_engine(async_db_url, engine_args)

def _initialize_async_engine():
    """Initialize the async PostgreSQL engine."""
    logger.debug("_initialize_async_engine called")
    try:
        async_db_url = _validate_database_url()
        logger.debug(f"Database URL validated: {async_db_url is not None}")
        if async_db_url:
            logger.debug(f"Initializing engine with URL...")
            _initialize_engine_with_url(async_db_url)
            logger.debug("Engine initialization completed")
        else:
            logger.error("Database URL is None or empty")
    except Exception as e:
        logger.error(f"Exception in _initialize_async_engine: {e}")
        _handle_engine_creation_error(e)


# Initialize the async engine - moved to lazy initialization
# _initialize_async_engine() is now called via initialize_postgres()

def get_converted_async_db_url() -> str:
    """
    CRITICAL: Get properly converted async database URL with sslmode->ssl conversion.
    
    This function MUST be used by any component creating async engines to prevent
    the recurring 'sslmode' parameter error with asyncpg.
        
    Returns:
        Converted URL safe for use with asyncpg (sslmode converted to ssl)
    """
    from netra_backend.app.database import get_database_url
    return get_database_url()


def initialize_postgres():
    """Initialize PostgreSQL connection with robust database initialization."""
    import os
    global async_engine, async_session_factory
    
    # Skip initialization during test collection to prevent hanging
    if get_env().get('TEST_COLLECTION_MODE') == '1':
        logger.debug("Skipping PostgreSQL initialization during test collection")
        return None
        
    logger.debug(f"initialize_postgres called. Current async_engine: {async_engine is not None}, async_session_factory: {async_session_factory is not None}")
    
    # Check if both engine and session factory are properly initialized
    if async_engine is not None and async_session_factory is not None:
        logger.debug("Database already initialized, reusing existing connection")
        return async_session_factory
    
    # Reset both if either is None to ensure clean initialization
    if async_engine is None or async_session_factory is None:
        logger.debug("Database not fully initialized, performing clean initialization...")
        # Don't reassign to None here, as it creates local variables
        
        try:
            # Initialize the engine and session factory directly
            logger.info("Initializing async engine and session factory...")
            _initialize_async_engine()
            logger.debug(f"After _initialize_async_engine(), async_engine: {async_engine is not None}, async_session_factory: {async_session_factory is not None}")
            
            if async_engine is None or async_session_factory is None:
                raise RuntimeError("Engine or session factory is None after initialization")
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            # CRITICAL SECURITY FIX: Never return mock session factory in any environment
            # Mock session factories cause silent data loss by accepting operations without persistence
            # All database initialization failures MUST be raised to prevent data corruption
            raise RuntimeError(f"Failed to initialize PostgreSQL: {e}") from e
    
    logger.debug(f"initialize_postgres returning: {async_session_factory}")
    return async_session_factory




def create_async_database(db_url: str = None) -> AsyncDatabase:
    """Create AsyncDatabase instance with optional URL override.
    
    Args:
        db_url: Optional database URL override
        
    Returns:
        Configured AsyncDatabase instance
    """
    return AsyncDatabase(db_url)


# Compatibility alias for test imports
PostgresCore = Database


# Compatibility exports for existing code
__all__ = [
    "Database", "AsyncDatabase", "PostgresCore", "initialize_postgres", "create_async_database",
    "get_converted_async_db_url", "async_engine", "async_session_factory"
]