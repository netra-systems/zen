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


# Import settings lazily to avoid circular dependency
def get_settings():
    """Get settings lazily to avoid circular import.
    
    Auth service can run standalone or with backend, so we need to handle both cases.
    """
    try:
        # First try auth service config
        from auth_service.auth_core.config import AuthConfig
        # Create a settings-like object with required attributes
        class AuthSettings:
            def __init__(self):
                self.log_async_checkout = AuthConfig.LOG_ASYNC_CHECKOUT if hasattr(AuthConfig, 'LOG_ASYNC_CHECKOUT') else False
                self.environment = AuthConfig.ENVIRONMENT if hasattr(AuthConfig, 'ENVIRONMENT') else 'development'
        return AuthSettings()
    except ImportError:
        try:
            # Fallback to netra_backend config if available (integrated mode)
            from netra_backend.app.config import get_config
            return get_config()
        except ImportError:
            # Handle case where neither is available (isolated testing)
            logger.debug("No config available, using defaults")
            return None

# Initialize settings at module level
settings = get_settings()


# Auth service specific database configuration
class AuthDatabaseConfig:
    """Auth service database configuration constants.
    
    Uses auth-specific values that are more conservative than the main backend
    since auth service handles lighter workloads but requires reliability.
    """
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
    # Use unified settings for logging control if available, otherwise default to debug
    try:
        should_log = getattr(settings, 'log_async_checkout', False) if settings else False
    except Exception:
        should_log = False
    
    if should_log or logger.isEnabledFor(logging.DEBUG):
        pid = connection_record.info.get('pid', 'unknown')
        logger.debug(f"Auth service: Database connection established with timeouts, PID={pid}")


def _monitor_auth_pool_usage(pool):
    """Monitor auth service connection pool usage and warn if high."""
    if not pool:
        return
    
    try:
        # Check for pool monitoring methods
        if hasattr(pool, 'size') and hasattr(pool, 'checkedin') and hasattr(pool, 'overflow'):
            total_size = pool.size()
            checked_in = pool.checkedin()
            overflow_count = pool.overflow()
            active = total_size - checked_in + overflow_count
            max_connections = AuthDatabaseConfig.POOL_SIZE + AuthDatabaseConfig.MAX_OVERFLOW
            threshold = max_connections * AuthDatabaseConfig.POOL_WARNING_THRESHOLD
            
            if active > threshold:
                logger.warning(
                    f"Auth service: Connection pool usage high: {active}/{max_connections} "
                    f"(size={total_size}, checkedin={checked_in}, overflow={overflow_count})"
                )
                
                # Log additional pool health metrics if available
                if hasattr(pool, 'total'):
                    logger.warning(f"Auth service: Total connections created: {pool.total()}")
    except Exception as e:
        logger.debug(f"Auth service: Could not monitor pool usage: {e}")


def _create_auth_async_connect_handler(engine: AsyncEngine):
    """Create async connection event handler for auth service."""
    @event.listens_for(engine.sync_engine, "connect")
    def receive_auth_async_connect(dbapi_conn: Connection, connection_record: ConnectionPoolEntry) -> None:
        _set_auth_connection_pid(dbapi_conn, connection_record)
        
        # Skip timeout config for SQLite (used in tests)
        if not str(engine.url).startswith('sqlite'):
            _configure_auth_connection_timeouts(dbapi_conn)
        
        _log_auth_connection_established(connection_record)
        
        # Monitor initial pool state
        if hasattr(engine, 'pool'):
            _monitor_auth_pool_usage(engine.pool)


def _create_auth_async_checkout_handler(engine: AsyncEngine):
    """Create async checkout event handler for auth service."""
    @event.listens_for(engine.sync_engine, "checkout")
    def receive_auth_async_checkout(dbapi_conn: Connection, connection_record: ConnectionPoolEntry, connection_proxy: _ConnectionFairy) -> None:
        # Monitor pool usage on checkout to catch high usage scenarios
        if hasattr(engine, 'pool'):
            _monitor_auth_pool_usage(engine.pool)
        _log_auth_checkout_if_enabled(connection_record)


def _log_auth_checkout_if_enabled(connection_record: ConnectionPoolEntry):
    """Log auth service checkout if debug logging enabled."""
    # Use unified settings for logging control if available, otherwise fall back to debug level
    try:
        should_log = getattr(settings, 'log_async_checkout', False) if settings else False
    except Exception:
        should_log = False
    
    if should_log or logger.isEnabledFor(logging.DEBUG):
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
        
        # Setup additional pool events if available
        if hasattr(engine.sync_engine, "pool") and hasattr(event, "listens_for"):
            _setup_pool_overflow_events(engine)
        
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


def _setup_pool_overflow_events(engine: AsyncEngine):
    """Setup pool overflow event monitoring."""
    try:
        @event.listens_for(engine.sync_engine, "invalidate")
        def receive_invalidate(dbapi_conn, connection_record, exception):
            """Log when connections are invalidated."""
            if exception:
                logger.warning(
                    f"Auth service: Connection invalidated due to error: {exception}"
                )

        @event.listens_for(engine.sync_engine, "reset")
        def receive_reset(dbapi_conn, connection_record):
            """Log when connections are reset."""
            logger.debug("Auth service: Connection reset to pool")
            
        @event.listens_for(engine.sync_engine, "close")
        def receive_close(dbapi_conn, connection_record):
            """Log when connections are closed."""
            logger.debug("Auth service: Connection closed")
    except Exception as e:
        logger.debug(f"Auth service: Could not setup overflow events: {e}")

# Export main setup function
__all__ = ["setup_auth_async_engine_events", "AuthDatabaseConfig", "get_settings", "_monitor_auth_pool_usage"]