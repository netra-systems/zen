"""Auth Service PostgreSQL Connection Events Module

Handles connection events, monitoring, and timeout configuration for auth service.
Focused module adhering to 25-line function limit and modular architecture.
"""

import logging
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import ConnectionPoolEntry, _ConnectionFairy

logger = logging.getLogger(__name__)


# Auth service specific configuration
class AuthDatabaseConfig:
    """Auth service database configuration constants."""
    STATEMENT_TIMEOUT = 15000  # 15 seconds (shorter than backend)
    POOL_SIZE = 5  # Smaller pool for auth service
    MAX_OVERFLOW = 10  # Conservative overflow
    POOL_WARNING_THRESHOLD = 0.8  # Warn at 80% capacity


def _execute_auth_timeout_statements(cursor):
    """Execute timeout configuration statements for auth service."""
    cursor.execute(f"SET statement_timeout = {AuthDatabaseConfig.STATEMENT_TIMEOUT}")
    cursor.execute("SET idle_in_transaction_session_timeout = 30000")  # 30s
    cursor.execute("SET lock_timeout = 5000")  # 5s (shorter than backend)


def _handle_auth_timeout_config_error(dbapi_conn: Connection, e: Exception):
    """Handle timeout configuration errors with rollback."""
    try:
        dbapi_conn.rollback()
    except Exception as rollback_error:
        logger.error(f"Failed to rollback after timeout config error: {rollback_error}")
    logger.error(f"Auth service: Failed to set connection parameters: {e}")
    raise


def _configure_auth_connection_timeouts(dbapi_conn: Connection):
    """Configure timeouts for auth service database connection."""
    cursor = dbapi_conn.cursor()
    try:
        _execute_and_commit_auth_timeout_config(dbapi_conn, cursor)
    except Exception as e:
        _handle_auth_timeout_config_error(dbapi_conn, e)
    finally:
        _close_cursor_safely(cursor)


def _close_cursor_safely(cursor):
    """Safely close database cursor."""
    try:
        cursor.close()
    except Exception as e:
        logger.warning(f"Auth service: Error closing cursor: {e}")


def _execute_and_commit_auth_timeout_config(dbapi_conn: Connection, cursor):
    """Execute timeout statements and commit transaction."""
    _execute_auth_timeout_statements(cursor)
    dbapi_conn.commit()


def _set_auth_connection_pid(dbapi_conn: Connection, connection_record: ConnectionPoolEntry):
    """Set connection PID for auth service connections."""
    try:
        # Handle both sync and async connection types
        if hasattr(dbapi_conn, 'get_backend_pid'):
            connection_record.info['pid'] = dbapi_conn.get_backend_pid()
        else:
            # For asyncpg connections, PID might not be immediately available
            connection_record.info['pid'] = None
    except Exception as e:
        logger.warning(f"Auth service: Could not get connection PID: {e}")
        connection_record.info['pid'] = None


def _log_auth_connection_established(connection_record: ConnectionPoolEntry):
    """Log auth service connection establishment."""
    pid = connection_record.info.get('pid', 'unknown')
    logger.debug(f"Auth service: Database connection established with timeouts, PID={pid}")


def _monitor_auth_pool_usage(pool):
    """Monitor auth service connection pool usage and warn if high."""
    if not (hasattr(pool, 'size') and hasattr(pool, 'overflow')):
        return
    
    try:
        active = pool.size() - pool.checkedin() + pool.overflow()
        max_connections = AuthDatabaseConfig.POOL_SIZE + AuthDatabaseConfig.MAX_OVERFLOW
        threshold = max_connections * AuthDatabaseConfig.POOL_WARNING_THRESHOLD
        
        if active > threshold:
            logger.warning(f"Auth service: Connection pool usage high: {active}/{max_connections}")
    except Exception as e:
        logger.warning(f"Auth service: Error monitoring pool usage: {e}")


def _create_auth_async_connect_handler(engine: AsyncEngine):
    """Create async connection event handler for auth service."""
    @event.listens_for(engine.sync_engine, "connect")
    def receive_auth_async_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
        _set_auth_connection_pid(dbapi_conn, connection_record)
        
        # Skip timeout config for SQLite (used in tests)
        if not str(engine.url).startswith('sqlite'):
            _configure_auth_connection_timeouts(dbapi_conn)
        
        _log_auth_connection_established(connection_record)


def _create_auth_async_checkout_handler(engine: AsyncEngine):
    """Create async checkout event handler for auth service."""
    @event.listens_for(engine.sync_engine, "checkout")
    def receive_auth_async_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
        _monitor_auth_pool_usage(engine.pool)
        _log_auth_checkout_if_enabled(connection_record)


def _log_auth_checkout_if_enabled(connection_record: ConnectionPoolEntry):
    """Log auth service checkout if debug logging enabled."""
    if logger.isEnabledFor(logging.DEBUG):
        pid = connection_record.info.get('pid', 'unknown')
        logger.debug(f"Auth service: Connection checked out from pool, PID={pid}")


def setup_auth_async_engine_events(engine: AsyncEngine):
    """Setup async engine connection events for auth service."""
    if not engine:
        logger.warning("Auth service: Cannot setup events on None engine")
        return
    
    try:
        _create_auth_async_connect_handler(engine)
        _create_auth_async_checkout_handler(engine)
        logger.debug("Auth service: Async engine events configured successfully")
    except Exception as e:
        logger.error(f"Auth service: Failed to setup engine events: {e}")
        # Don't raise - connection events are not critical for functionality


def _log_auth_connection_info(dbapi_conn: Connection):
    """Log auth service connection information for debugging."""
    try:
        # Get basic connection info without failing
        conn_info = {
            'server_version': getattr(dbapi_conn, 'server_version', 'unknown'),
            'autocommit': getattr(dbapi_conn, 'autocommit', 'unknown'),
        }
        logger.debug(f"Auth service connection info: {conn_info}")
    except Exception as e:
        logger.debug(f"Auth service: Could not get connection info: {e}")


# Export main setup function
__all__ = ["setup_auth_async_engine_events", "AuthDatabaseConfig"]