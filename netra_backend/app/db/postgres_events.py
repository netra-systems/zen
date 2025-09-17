"""PostgreSQL connection event handling module.

Handles connection events, monitoring, and timeout configuration.
Focused module adhering to 25-line function limit and modular architecture.
"""

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import ConnectionPoolEntry, _ConnectionFairy

from netra_backend.app.logging_config import central_logger
from netra_backend.app.config import get_unified_config


# Import settings lazily to avoid circular dependency
def get_settings():
    """Get settings lazily to avoid circular import."""
    from netra_backend.app.config import get_config
    return get_config()

# Initialize settings at module level
settings = get_settings()
# Get unified config for database settings
config = get_unified_config()

logger = central_logger.get_logger(__name__)


def _execute_timeout_statements(cursor):
    """Execute timeout configuration statements."""
    cursor.execute(f"SET statement_timeout = {config.db_statement_timeout}")
    cursor.execute("SET idle_in_transaction_session_timeout = 300000")  # Issue #1278: 5 minutes for Cloud Run
    cursor.execute("SET lock_timeout = 60000")  # Issue #1278: 60 seconds for Cloud Run infrastructure


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
    _close_cursor_safely(cursor)

def _close_cursor_safely(cursor):
    """Safely close database cursor."""
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
        threshold = (config.db_pool_size + config.db_max_overflow) * 0.8
        if active > threshold:
            logger.warning(f"Async connection pool usage high: {active}/{config.db_pool_size + config.db_max_overflow}")


def _create_async_connect_handler(engine: AsyncEngine):
    """Create async connection event handler."""
    @event.listens_for(engine.sync_engine, "connect")
    def receive_async_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
        _set_connection_pid(dbapi_conn, connection_record)
        _configure_async_connection_timeouts(dbapi_conn)
        _log_async_connection_established(connection_record)

def _create_async_checkout_handler(engine: AsyncEngine):
    """Create async checkout event handler."""
    @event.listens_for(engine.sync_engine, "checkout")
    def receive_async_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
        _monitor_async_pool_usage(engine.pool)
        _log_async_checkout_if_enabled(connection_record)

def _log_async_checkout_if_enabled(connection_record: ConnectionPoolEntry):
    """Log async checkout if enabled in settings."""
    if settings.log_async_checkout:
        pid = connection_record.info.get('pid', 'unknown')
        logger.debug(f"Async connection checked out from pool: PID={pid}")

def setup_async_engine_events(engine: AsyncEngine):
    """Setup async engine connection events."""
    _create_async_connect_handler(engine)
    _create_async_checkout_handler(engine)


def _configure_sync_connection_timeouts(dbapi_conn: Connection):
    """Configure statement and transaction timeouts for sync connection."""
    with dbapi_conn.cursor() as cursor:
        cursor.execute(f"SET statement_timeout = {config.db_statement_timeout}")
        cursor.execute("SET idle_in_transaction_session_timeout = 300000")  # Issue #1278: 5 minutes for Cloud Run
        cursor.execute("SET lock_timeout = 60000")  # Issue #1278: 60 seconds for Cloud Run infrastructure

def _set_sync_connection_pid_and_configure(dbapi_conn: Connection, connection_record: ConnectionPoolEntry):
    """Set PID and configure timeouts for sync connection."""
    connection_record.info['pid'] = dbapi_conn.get_backend_pid() if hasattr(dbapi_conn, 'get_backend_pid') else None
    _configure_sync_connection_timeouts(dbapi_conn)

def _log_sync_connection_if_enabled(connection_record: ConnectionPoolEntry):
    """Log sync connection establishment if enabled."""
    if settings.log_async_checkout:
        logger.debug(f"Database connection established with safety limits: {connection_record.info.get('pid')}")

def _check_sync_pool_usage_warning(pool):
    """Check and warn if sync pool usage is high."""
    if hasattr(pool, 'size') and hasattr(pool, 'overflow'):
        active = pool.size() - pool.checkedin() + pool.overflow()
        if active > (config.db_pool_size + config.db_max_overflow) * 0.8:
            logger.warning(f"Connection pool usage high: {active}/{config.db_pool_size + config.db_max_overflow}")

def _log_sync_checkout_if_enabled(connection_record: ConnectionPoolEntry):
    """Log sync checkout if enabled in settings."""
    if settings.log_async_checkout:
        logger.debug(f"Connection checked out from pool: {connection_record.info.get('pid')}")

def _create_sync_connect_handler(engine):
    """Create sync connection event handler."""
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
        _set_sync_connection_pid_and_configure(dbapi_conn, connection_record)
        _log_sync_connection_if_enabled(connection_record)

def _create_sync_checkout_handler(engine):
    """Create sync checkout event handler."""
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
        _check_sync_pool_usage_warning(engine.pool)
        _log_sync_checkout_if_enabled(connection_record)

def setup_sync_engine_events(engine):
    """Setup synchronous engine connection events."""
    _create_sync_connect_handler(engine)
    _create_sync_checkout_handler(engine)