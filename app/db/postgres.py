from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Generator, AsyncGenerator, Any
from sqlalchemy import create_engine, pool, event
from sqlalchemy.engine import Connection
from sqlalchemy.pool import Pool, ConnectionPoolEntry, _ConnectionFairy
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool, AsyncAdaptedQueuePool
from app.config import settings
from app.logging_config import central_logger

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

class Database:
    """Synchronous database connection manager with proper pooling."""
    def __init__(self, db_url: str):
        pool_class = NullPool if "sqlite" in db_url else QueuePool
        self.engine = create_engine(
            db_url,
            echo=DatabaseConfig.ECHO,
            echo_pool=DatabaseConfig.ECHO_POOL,
            poolclass=pool_class,
            pool_size=DatabaseConfig.POOL_SIZE if pool_class == QueuePool else 0,
            max_overflow=DatabaseConfig.MAX_OVERFLOW if pool_class == QueuePool else 0,
            pool_timeout=DatabaseConfig.POOL_TIMEOUT,
            pool_recycle=DatabaseConfig.POOL_RECYCLE,
            pool_pre_ping=DatabaseConfig.POOL_PRE_PING,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False
        )
        self._setup_connection_events()

    def _setup_connection_events(self):
        """Setup database connection event listeners for monitoring and configuration."""
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn: Any, connection_record: ConnectionPoolEntry) -> None:
            connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None
            
            # Set statement timeout for all connections
            with dbapi_conn.cursor() as cursor:
                cursor.execute(f"SET statement_timeout = {DatabaseConfig.STATEMENT_TIMEOUT}")
                cursor.execute("SET idle_in_transaction_session_timeout = 60000")  # 60 seconds
                cursor.execute("SET lock_timeout = 10000")  # 10 seconds
            
            logger.debug(f"Database connection established with safety limits: {connection_record.info.get('pid')}")

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn: Any, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
            # Track pool usage for monitoring
            pool = self.engine.pool
            if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
                active = pool.size() - pool.checkedin() + pool.overflow()
                if active > (DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW) * 0.8:
                    logger.warning(f"Connection pool usage high: {active}/{DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW}")
            
            logger.debug(f"Connection checked out from pool: {connection_record.info.get('pid')}")

    def connect(self):
        """Test database connectivity."""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
                logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database transaction rolled back: {e}")
            raise
        finally:
            db.close()

    def close(self):
        """Close all database connections."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("Database connections closed")

# PostgreSQL async engine with proper configuration
async_engine: Optional[any] = None
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
        
        # Setup async connection events
        @event.listens_for(async_engine.sync_engine, "connect")
        def receive_async_connect(dbapi_conn: Any, connection_record: ConnectionPoolEntry) -> None:
            connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None
            
            # Set statement timeout for all async connections
            # For asyncpg connections, we need to use the direct execute method
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute(f"SET statement_timeout = {DatabaseConfig.STATEMENT_TIMEOUT}")
                cursor.execute("SET idle_in_transaction_session_timeout = 60000")  # 60 seconds
                cursor.execute("SET lock_timeout = 10000")  # 10 seconds
                dbapi_conn.commit()  # Commit the SET commands
            except Exception as e:
                dbapi_conn.rollback()  # Rollback on error
                logger.error(f"Failed to set connection parameters: {e}")
                raise
            finally:
                cursor.close()
            
            logger.debug(f"Async database connection established with safety limits: {connection_record.info.get('pid')}")

        @event.listens_for(async_engine.sync_engine, "checkout")
        def receive_async_checkout(dbapi_conn: Any, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
            # Track async pool usage for monitoring
            pool = async_engine.pool
            if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
                active = pool.size() - pool.checkedin() + pool.overflow()
                if active > (DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW) * 0.8:
                    logger.warning(f"Async connection pool usage high: {active}/{DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW}")
            
            logger.debug(f"Async connection checked out from pool: {connection_record.info.get('pid')}")
        
        logger.info("PostgreSQL async engine created with AsyncAdaptedQueuePool connection pooling")
    else:
        logger.warning("Database URL not configured")
except Exception as e:
    logger.error(f"Failed to create PostgreSQL async engine: {e}")
    async_engine = None
    async_session_factory = None


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an async database session with proper transaction handling.
    """
    if async_session_factory is None:
        logger.error("async_session_factory is not initialized.")
        raise RuntimeError("Database not configured")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async DB session error: {e}", exc_info=True)
            raise
        finally:
            await session.close()

async def close_async_db():
    """Close all async database connections."""
    global async_engine
    if async_engine:
        await async_engine.dispose()
        logger.info("Async database connections closed")
        async_engine = None

def get_pool_status() -> dict:
    """Get current connection pool status for monitoring."""
    # This function is now deprecated in favor of the comprehensive monitoring system
    # Import and use the new monitoring system
    try:
        from app.services.database.connection_monitor import connection_metrics
        return connection_metrics.get_pool_status()
    except ImportError:
        # Fallback to basic status if monitoring not available
        status = {"sync": None, "async": None}
        
        if hasattr(Database, 'engine') and Database.engine:
            pool = Database.engine.pool
            status["sync"] = {
                "size": pool.size() if hasattr(pool, 'size') else None,
                "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
                "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
                "total": pool.size() + pool.overflow() if hasattr(pool, 'size') and hasattr(pool, 'overflow') else None
            }
        
        if async_engine:
            pool = async_engine.pool
            status["async"] = {
                "size": pool.size() if hasattr(pool, 'size') else None,
                "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
                "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
                "total": pool.size() + pool.overflow() if hasattr(pool, 'size') and hasattr(pool, 'overflow') else None
            }
        
        return status