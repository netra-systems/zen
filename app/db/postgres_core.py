"""PostgreSQL core connection and engine setup module.

Handles database engine creation, connection management, and initialization.
Focused module adhering to 8-line function limit and modular architecture.
"""

from contextlib import contextmanager
from typing import Optional, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool, AsyncAdaptedQueuePool
from app.config import settings
from app.logging_config import central_logger
from .postgres_config import DatabaseConfig
from .postgres_events import setup_async_engine_events, setup_sync_engine_events

logger = central_logger.get_logger(__name__)


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
        setup_sync_engine_events(self.engine)

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


def _get_async_db_url(db_url: str) -> str:
    """Convert sync database URL to async format."""
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("sqlite://"):
        return db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return db_url


def _get_pool_class_for_async(async_db_url: str):
    """Get appropriate pool class for async database."""
    return AsyncAdaptedQueuePool if "sqlite" not in async_db_url else NullPool


def _get_base_engine_args(pool_class):
    """Get base engine arguments for all pool types."""
    return {
        "echo": DatabaseConfig.ECHO,
        "echo_pool": DatabaseConfig.ECHO_POOL,
        "poolclass": pool_class,
    }

def _get_pool_specific_args():
    """Get pool-specific arguments for non-NullPool."""
    return {
        "pool_size": DatabaseConfig.POOL_SIZE,
        "max_overflow": DatabaseConfig.MAX_OVERFLOW,
        "pool_timeout": DatabaseConfig.POOL_TIMEOUT,
        "pool_recycle": DatabaseConfig.POOL_RECYCLE,
        "pool_pre_ping": DatabaseConfig.POOL_PRE_PING,
    }

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
    """Validate database URL configuration."""
    db_url = settings.database_url
    if not db_url:
        logger.warning("Database URL not configured")
        return None
    return db_url

def _create_engine_components(db_url):
    """Create engine components from database URL."""
    async_db_url = _get_async_db_url(db_url)
    pool_class = _get_pool_class_for_async(async_db_url)
    engine_args = _build_engine_args(pool_class)
    return async_db_url, engine_args

def _setup_global_engine_objects(engine):
    """Setup global engine and session factory objects."""
    global async_engine, async_session_factory
    async_engine = engine
    async_session_factory = _create_async_session_factory(async_engine)
    setup_async_engine_events(async_engine)

def _handle_engine_creation_error(e):
    """Handle engine creation error and reset globals."""
    global async_engine, async_session_factory
    logger.error(f"Failed to create PostgreSQL async engine: {e}")
    async_engine = None
    async_session_factory = None

def _initialize_async_engine():
    """Initialize the async PostgreSQL engine."""
    try:
        db_url = _validate_database_url()
        if not db_url:
            return
        async_db_url, engine_args = _create_engine_components(db_url)
        engine = create_async_engine(async_db_url, **engine_args)
        _setup_global_engine_objects(engine)
        logger.info("PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling")
    except Exception as e:
        _handle_engine_creation_error(e)


# Initialize the async engine
_initialize_async_engine()