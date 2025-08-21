"""Health check utilities for route handlers."""

from datetime import UTC, datetime
from typing import Any, Dict

import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres import async_engine, get_pool_status
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def test_database_connectivity(db: AsyncSession) -> bool:
    """Test database connectivity."""
    result = await db.execute(text("SELECT 1"))
    return result.scalar() == 1


def _get_db_query_fields() -> str:
    """Get database query field selection."""
    return "count(*) as active_connections, max(state_change) as last_activity"

def _get_db_query_filter() -> str:
    """Get database query filter condition."""
    return "WHERE datname = current_database()"

def _build_db_stats_query() -> str:
    """Build database statistics query."""
    fields = _get_db_query_fields()
    filter_clause = _get_db_query_filter()
    return f"SELECT {fields} FROM pg_stat_activity {filter_clause}"


def _process_db_stats_result(row) -> Dict[str, Any]:
    """Process database statistics result."""
    return {
        "active_connections": row.active_connections,
        "last_activity": row.last_activity.isoformat() if row.last_activity else None
    }


async def _execute_db_stats_query(db: AsyncSession):
    """Execute database statistics query."""
    result = await db.execute(text(_build_db_stats_query()))
    return result.first()

async def _fetch_db_stats_with_error_handling(db: AsyncSession) -> Dict[str, Any]:
    """Fetch database statistics with error handling."""
    try:
        row = await _execute_db_stats_query(db)
        return _process_db_stats_result(row) if row else {}
    except Exception as e:
        logger.warning(f"Could not fetch database statistics: {e}")
        return {}

async def get_database_statistics(db: AsyncSession) -> Dict[str, Any]:
    """Get database statistics."""
    if not async_engine:
        return {}
    return await _fetch_db_stats_with_error_handling(db)


def _get_database_status(db_connected: bool) -> str:
    """Get database status string."""
    return "healthy" if db_connected else "unhealthy"


def _build_db_response_fields(db_connected: bool, pool_status: Dict, stats: Dict) -> Dict[str, Any]:
    """Build database response fields."""
    return {
        "status": _get_database_status(db_connected),
        "connected": db_connected,
        "pool_status": pool_status,
        "database_stats": stats
    }


def build_database_health_response(
    db_connected: bool, pool_status: Dict, stats: Dict
) -> Dict[str, Any]:
    """Build database health response."""
    response = _build_db_response_fields(db_connected, pool_status, stats)
    response["timestamp"] = datetime.now(UTC).isoformat()
    return response


def _get_memory_metrics() -> Dict[str, Any]:
    """Get memory metrics."""
    memory = psutil.virtual_memory()
    return {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent
    }


def _get_disk_metrics() -> Dict[str, Any]:
    """Get disk metrics."""
    disk = psutil.disk_usage('/')
    return {
        "total": disk.total,
        "free": disk.free,
        "percent": disk.percent
    }


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    return {
        "cpu_percent": cpu_percent,
        "memory": _get_memory_metrics(),
        "disk": _get_disk_metrics()
    }


def _get_process_memory_metrics(process) -> Dict[str, Any]:
    """Get process memory metrics."""
    memory = process.memory_info()
    return {
        "memory_rss": memory.rss,
        "memory_vms": memory.vms
    }


def _get_process_performance_metrics(process) -> Dict[str, Any]:
    """Get process performance metrics."""
    return {
        "cpu_percent": process.cpu_percent(),
        "num_threads": process.num_threads(),
        "connections": len(process.connections(kind='inet'))
    }


def get_process_metrics() -> Dict[str, Any]:
    """Get process-specific metrics."""
    process = psutil.Process()
    memory_metrics = _get_process_memory_metrics(process)
    performance_metrics = _get_process_performance_metrics(process)
    return {**memory_metrics, **performance_metrics}


def build_system_health_response(system_metrics: Dict, process_metrics: Dict) -> Dict[str, Any]:
    """Build system health response."""
    return {
        "status": "healthy",
        "system": system_metrics,
        "process": process_metrics,
        "timestamp": datetime.now(UTC).isoformat()
    }


def build_system_error_response(error: str) -> Dict[str, Any]:
    """Build system error response."""
    return {
        "status": "error",
        "error": error,
        "timestamp": datetime.now(UTC).isoformat()
    }


def _get_pool_basic_config() -> Dict[str, Any]:
    """Get basic pool configuration."""
    return {"pool_size": 20, "max_overflow": 30, "pool_timeout": 30}

def _get_pool_extended_config() -> Dict[str, Any]:
    """Get extended pool configuration."""
    return {"pool_recycle": 1800, "max_connections": 100}

def _get_pool_config_data() -> Dict[str, Any]:
    """Get pool configuration dictionary."""
    basic = _get_pool_basic_config()
    extended = _get_pool_extended_config()
    return {**basic, **extended}

def get_pool_configuration() -> Dict[str, Any]:
    """Get pool configuration data."""
    return _get_pool_config_data()


def _calculate_active_connections(async_pool: Dict) -> int:
    """Calculate active connections."""
    return async_pool["size"] - async_pool["checked_in"]


def _calculate_total_capacity(async_pool: Dict) -> int:
    """Calculate total pool capacity."""
    return async_pool["size"] + async_pool.get("overflow", 0)


def _build_utilization_metrics(active: int, total_capacity: int) -> Dict[str, Any]:
    """Build utilization metrics dict."""
    return {
        "active_connections": active,
        "utilization_percent": (active / total_capacity) * 100 if total_capacity else 0
    }


def _validate_pool_data(async_pool: Dict) -> bool:
    """Validate pool has required data."""
    return async_pool.get("size") is not None and async_pool.get("checked_in") is not None


def _process_async_pool(async_pool: Dict) -> Dict[str, Any]:
    """Process async pool data for utilization."""
    active = _calculate_active_connections(async_pool)
    total_capacity = _calculate_total_capacity(async_pool)
    return _build_utilization_metrics(active, total_capacity)


def calculate_pool_utilization(pool_status: Dict) -> Dict[str, Any]:
    """Calculate pool utilization metrics."""
    utilization = {}
    if pool_status.get("async"):
        async_pool = pool_status["async"]
        if _validate_pool_data(async_pool):
            utilization = _process_async_pool(async_pool)
    return utilization