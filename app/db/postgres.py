from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Generator, AsyncGenerator, Union, Dict, Any
from sqlalchemy import create_engine, pool, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import Pool, ConnectionPoolEntry, _ConnectionFairy
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool, AsyncAdaptedQueuePool
from sqlalchemy.exc import OperationalError, IntegrityError, DisconnectionError
from app.config import settings
from app.logging_config import central_logger
from app.core.enhanced_retry_strategies import RetryConfig
import asyncio
import time
from functools import wraps

logger = central_logger.get_logger(__name__)

class DatabaseConfig:
    """Database configuration with enhanced connection pooling settings."""
    # Production-optimized pool settings
    POOL_SIZE = 20  # Increased base pool size for production loads
    MAX_OVERFLOW = 30  # Allow more overflow connections under load
    POOL_TIMEOUT = 30  # Timeout waiting for connection from pool
    POOL_RECYCLE = 1800  # Recycle connections every 30 minutes
    POOL_PRE_PING = True  # Test connections before using
    ECHO = False
    ECHO_POOL = False
    
    # Connection limits for protection
    MAX_CONNECTIONS = 100  # Hard limit on total connections
    CONNECTION_TIMEOUT = 10  # Timeout for establishing new connections
    STATEMENT_TIMEOUT = 30000  # 30 seconds max statement execution time (ms)
    
    # Read/write splitting configuration
    ENABLE_READ_WRITE_SPLIT = False
    READ_db_url: Optional[str] = None
    write_db_url: Optional[str] = None
    
    # Query caching configuration
    ENABLE_QUERY_CACHE = True
    QUERY_CACHE_TTL = 300  # 5 minutes
    QUERY_CACHE_SIZE = 1000  # Max cached queries
    
    # Transaction retry configuration
    TRANSACTION_RETRY_ATTEMPTS = 3
    TRANSACTION_RETRY_DELAY = 0.1  # Base delay in seconds
    TRANSACTION_RETRY_BACKOFF = 2.0  # Exponential backoff multiplier

class Database:
    """Synchronous database connection manager with proper pooling."""
    
    def _get_pool_class(self, db_url: str):
        """Determine appropriate pool class for database type."""
        return NullPool if "sqlite" in db_url else QueuePool
    
    def _create_engine(self, db_url: str, pool_class):
        """Create database engine with optimized pooling configuration."""
        return create_engine(
            db_url, echo=DatabaseConfig.ECHO, echo_pool=DatabaseConfig.ECHO_POOL,
            poolclass=pool_class, pool_size=DatabaseConfig.POOL_SIZE if pool_class == QueuePool else 0,
            max_overflow=DatabaseConfig.MAX_OVERFLOW if pool_class == QueuePool else 0,
            pool_timeout=DatabaseConfig.POOL_TIMEOUT, pool_recycle=DatabaseConfig.POOL_RECYCLE,
            pool_pre_ping=DatabaseConfig.POOL_PRE_PING
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
        self._setup_connection_events()

    def _configure_connection_timeouts(self, dbapi_conn: Connection):
        """Configure statement and transaction timeouts for connection."""
        with dbapi_conn.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {DatabaseConfig.STATEMENT_TIMEOUT}")
            cursor.execute("SET idle_in_transaction_session_timeout = 60000")
            cursor.execute("SET lock_timeout = 10000")
    
    def _setup_connect_handler(self):
        """Setup connection establishment event handler."""
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
            connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None
            self._configure_connection_timeouts(dbapi_conn)
            if settings.log_async_checkout:
                logger.debug(f"Database connection established with safety limits: {connection_record.info.get('pid')}")
    
    def _check_pool_usage_warning(self, pool):
        """Check and warn if pool usage is high."""
        if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
            active = pool.size() - pool.checkedin() + pool.overflow()
            if active > (DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW) * 0.8:
                logger.warning(f"Connection pool usage high: {active}/{DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW}")
    
    def _setup_checkout_handler(self):
        """Setup connection checkout event handler."""
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
            self._check_pool_usage_warning(self.engine.pool)
            # Only log checkout events if explicitly enabled in config
            if settings.log_async_checkout:
                logger.debug(f"Connection checked out from pool: {connection_record.info.get('pid')}")
    
    def _setup_connection_events(self):
        """Setup database connection event listeners for monitoring and configuration."""
        self._setup_connect_handler()
        self._setup_checkout_handler()

    def _execute_connection_test(self):
        """Execute database connection test query."""
        with self.engine.connect() as conn:
            conn.execute("SELECT 1")
            logger.info("Database connection test successful")
    
    def connect(self):
        """Test database connectivity with proper error handling."""
        try:
            self._execute_connection_test()
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    def _handle_transaction_error(self, db: Session, e: Exception):
        """Handle database transaction error with rollback and logging."""
        db.rollback()
        logger.error(f"Database transaction rolled back: {e}")
        raise
    
    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            self._handle_transaction_error(db, e)
        finally:
            db.close()

    def close(self):
        """Close all database connections."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("Database connections closed")

# PostgreSQL async engine with proper configuration
async_engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker] = None

try:
    db_url = settings.database_url
    if db_url:
        # Convert sync database URL to async format
        if db_url.startswith("postgresql://"):
            async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            async_db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("sqlite://"):
            async_db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        else:
            async_db_url = db_url
        
        # Use AsyncAdaptedQueuePool for proper async connection pooling
        pool_class = AsyncAdaptedQueuePool if "sqlite" not in async_db_url else NullPool
        
        # Build engine arguments based on pool class
        engine_args = {
            "echo": DatabaseConfig.ECHO,
            "echo_pool": DatabaseConfig.ECHO_POOL,
            "poolclass": pool_class,
        }
        
        # Only add pool-specific arguments for non-NullPool
        if pool_class != NullPool:
            engine_args.update({
                "pool_size": DatabaseConfig.POOL_SIZE,
                "max_overflow": DatabaseConfig.MAX_OVERFLOW,
                "pool_timeout": DatabaseConfig.POOL_TIMEOUT,
                "pool_recycle": DatabaseConfig.POOL_RECYCLE,
                "pool_pre_ping": DatabaseConfig.POOL_PRE_PING,
            })
        
        async_engine = create_async_engine(async_db_url, **engine_args)
        async_session_factory = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        def _configure_async_connection_timeouts(dbapi_conn: Connection):
            """Configure timeouts for async database connection."""
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute(f"SET statement_timeout = {DatabaseConfig.STATEMENT_TIMEOUT}")
                cursor.execute("SET idle_in_transaction_session_timeout = 60000")
                cursor.execute("SET lock_timeout = 10000")
                dbapi_conn.commit()
            except Exception as e:
                dbapi_conn.rollback()
                logger.error(f"Failed to set connection parameters: {e}")
                raise
            finally:
                cursor.close()
        
        # Setup async connection events
        @event.listens_for(async_engine.sync_engine, "connect")
        def receive_async_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
            # Note: asyncpg connections don't have get_backend_pid() method
            # PID is None for async connections until they execute queries
            # This is expected behavior and not an issue
            connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None
            _configure_async_connection_timeouts(dbapi_conn)
            if settings.log_async_checkout:
                logger.debug(f"Async database connection established with safety limits: {connection_record.info.get('pid')}")
        

        def _monitor_async_pool_usage(pool):
            """Monitor async connection pool usage and warn if high."""
            if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
                active = pool.size() - pool.checkedin() + pool.overflow()
                threshold = (DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW) * 0.8
                if active > threshold:
                    logger.warning(f"Async connection pool usage high: {active}/{DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW}")
        
        @event.listens_for(async_engine.sync_engine, "checkout")
        def receive_async_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
            _monitor_async_pool_usage(async_engine.pool)
            # Only log checkout events if explicitly enabled in config
            if settings.log_async_checkout:
                pid = connection_record.info.get('pid', 'unknown')
                logger.debug(f"Async connection checked out from pool: PID={pid}")
        
        
        logger.info("PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling")
    else:
        logger.warning("Database URL not configured")
except Exception as e:
    logger.error(f"Failed to create PostgreSQL async engine: {e}")
    async_engine = None
    async_session_factory = None


def validate_session(session: any) -> bool:
    """Validate that a session is a proper AsyncSession instance."""
    return isinstance(session, AsyncSession)

def get_session_validation_error(session: any) -> str:
    """Get descriptive error for invalid session type."""
    if session is None:
        return "Session is None"
    actual_type = type(session).__name__
    return f"Expected AsyncSession, got {actual_type}"

def _validate_async_session_factory():
    """Validate that async session factory is initialized."""
    if async_session_factory is None:
        logger.error("async_session_factory is not initialized.")
        raise RuntimeError("Database not configured")

def _validate_async_session(session):
    """Validate async session type and raise error if invalid."""
    if not validate_session(session):
        error_msg = get_session_validation_error(session)
        logger.error(f"Invalid session type: {error_msg}")
        raise RuntimeError(f"Database session error: {error_msg}")

async def _handle_async_transaction_error(session: AsyncSession, e: Exception):
    """Handle async transaction error with rollback and logging."""
    await session.rollback()
    logger.error(f"Async DB session error: {e}", exc_info=True)
    raise

@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session with proper transaction handling."""
    _validate_async_session_factory()
    async with async_session_factory() as session:
        _validate_async_session(session)
        logger.debug(f"Created async session: {type(session).__name__}")
        try:
            yield session
            await session.commit()
        except Exception as e:
            await _handle_async_transaction_error(session, e)

async def close_async_db():
    """Close all async database connections."""
    global async_engine
    if async_engine:
        await async_engine.dispose()
        logger.info("Async database connections closed")
        async_engine = None


@asynccontextmanager
async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for get_async_db() for compatibility with existing code.
    Get a PostgreSQL async database session with proper transaction handling.
    """
    async with get_async_db() as session:
        yield session

def _get_enhanced_pool_status():
    """Get pool status from enhanced monitoring system."""
    from app.services.database.connection_monitor import connection_metrics
    return connection_metrics.get_pool_status()

def _extract_pool_metrics(pool):
    """Extract metrics from a connection pool."""
    return {
        "size": pool.size() if hasattr(pool, 'size') else None,
        "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
        "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
        "total": pool.size() + pool.overflow() if hasattr(pool, 'size') and hasattr(pool, 'overflow') else None
    }

def _get_sync_pool_status():
    """Get synchronous pool status if available."""
    # Currently we only use async engine, no sync instance
    return None

def _get_async_pool_status():
    """Get asynchronous pool status if available."""
    if async_engine:
        return _extract_pool_metrics(async_engine.pool)
    return None

def _get_fallback_pool_status():
    """Get basic pool status as fallback when monitoring unavailable."""
    return {
        "sync": _get_sync_pool_status(),
        "async": _get_async_pool_status()
    }

def get_pool_status() -> dict:
    """Get current connection pool status for monitoring."""
    try:
        return _get_enhanced_pool_status()
    except ImportError:
        return _get_fallback_pool_status()