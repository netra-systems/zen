"""PostgreSQL connection pool monitoring module.

Handles connection pool metrics, monitoring, and status reporting.
Focused module adhering to 25-line function limit and modular architecture.
"""

from typing import Dict, Any, Optional


def _get_enhanced_pool_status():
    """Get pool status from enhanced monitoring system."""
    try:
        from app.services.database.connection_monitor import connection_metrics
        return connection_metrics.get_pool_status()
    except ImportError:
        return None


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
    from app.db.postgres_core import async_engine
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
    enhanced_status = _get_enhanced_pool_status()
    if enhanced_status is not None:
        return enhanced_status
    return _get_fallback_pool_status()


async def close_async_db():
    """Close all async database connections."""
    from app.db.postgres_core import async_engine
    from app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    
    if async_engine:
        await async_engine.dispose()
        logger.info("Async database connections closed")
        # Note: Do not set async_engine to None here as it's a global variable
        # in another module. The engine disposal is sufficient for cleanup.
    else:
        logger.debug("No async engine to close")