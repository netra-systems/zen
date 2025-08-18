"""PostgreSQL connection event handling module.

Handles connection events, monitoring, and timeout configuration.
Focused module adhering to 8-line function limit and modular architecture.
"""

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.pool import ConnectionPoolEntry, _ConnectionFairy
from sqlalchemy.ext.asyncio import AsyncEngine
from app.config import settings
from app.logging_config import central_logger
from .postgres_config import DatabaseConfig

logger = central_logger.get_logger(__name__)


def _execute_timeout_statements(cursor):
    """Execute timeout configuration statements."""
    cursor.execute(f"SET statement_timeout = {DatabaseConfig.STATEMENT_TIMEOUT}")
    cursor.execute("SET idle_in_transaction_session_timeout = 60000")
    cursor.execute("SET lock_timeout = 10000")


def _handle_timeout_config_error(dbapi_conn: Connection, e: Exception):
    """Handle timeout configuration errors with rollback."""
    dbapi_conn.rollback()
    logger.error(f"Failed to set connection parameters: {e}")
    raise


def _configure_async_connection_timeouts(dbapi_conn: Connection):
    """Configure timeouts for async database connection."""
    cursor = dbapi_conn.cursor()
    try:
        _execute_and_commit_timeout_config(dbapi_conn, cursor)
    except Exception as e:
        _handle_timeout_config_error(dbapi_conn, e)
    finally:
        cursor.close()

def _execute_and_commit_timeout_config(dbapi_conn: Connection, cursor):
    """Execute timeout statements and commit transaction."""
    _execute_timeout_statements(cursor)
    dbapi_conn.commit()


def _set_connection_pid(dbapi_conn: Connection, connection_record: ConnectionPoolEntry):
    """Set connection PID for async connections."""
    # Note: asyncpg connections don't have get_backend_pid() method
    # PID is None for async connections until they execute queries
    # This is expected behavior and not an issue
    connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None


def _log_async_connection_established(connection_record: ConnectionPoolEntry):
    """Log async connection establishment if enabled."""
    if settings.log_async_checkout:
        logger.debug(f"Async database connection established with safety limits: {connection_record.info.get('pid')}")


def _monitor_async_pool_usage(pool):
    """Monitor async connection pool usage and warn if high."""
    if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
        active = pool.size() - pool.checkedin() + pool.overflow()
        threshold = (DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW) * 0.8
        if active > threshold:
            logger.warning(f"Async connection pool usage high: {active}/{DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW}")


def setup_async_engine_events(engine: AsyncEngine):
    """Setup async engine connection events."""
    @event.listens_for(engine.sync_engine, "connect")
    def receive_async_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
        _set_connection_pid(dbapi_conn, connection_record)
        _configure_async_connection_timeouts(dbapi_conn)
        _log_async_connection_established(connection_record)

    @event.listens_for(engine.sync_engine, "checkout")
    def receive_async_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
        _monitor_async_pool_usage(engine.pool)
        # Only log checkout events if explicitly enabled in config
        if settings.log_async_checkout:
            pid = connection_record.info.get('pid', 'unknown')
            logger.debug(f"Async connection checked out from pool: PID={pid}")


def setup_sync_engine_events(engine):
    """Setup synchronous engine connection events."""
    def _configure_connection_timeouts(dbapi_conn: Connection):
        """Configure statement and transaction timeouts for connection."""
        with dbapi_conn.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {DatabaseConfig.STATEMENT_TIMEOUT}")
            cursor.execute("SET idle_in_transaction_session_timeout = 60000")
            cursor.execute("SET lock_timeout = 10000")
    
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
        connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None
        _configure_connection_timeouts(dbapi_conn)
        if settings.log_async_checkout:
            logger.debug(f"Database connection established with safety limits: {connection_record.info.get('pid')}")
    
    def _check_pool_usage_warning(pool):
        """Check and warn if pool usage is high."""
        if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
            active = pool.size() - pool.checkedin() + pool.overflow()
            if active > (DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW) * 0.8:
                logger.warning(f"Connection pool usage high: {active}/{DatabaseConfig.POOL_SIZE + DatabaseConfig.MAX_OVERFLOW}")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
        _check_pool_usage_warning(engine.pool)
        # Only log checkout events if explicitly enabled in config
        if settings.log_async_checkout:
            logger.debug(f"Connection checked out from pool: {connection_record.info.get('pid')}")