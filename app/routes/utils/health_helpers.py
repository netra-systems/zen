"""Health check utilities for route handlers."""

import psutil
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, UTC
from app.db.postgres import get_pool_status, async_engine
from app.logging_config import central_logger


logger = central_logger.get_logger(__name__)


async def test_database_connectivity(db: AsyncSession) -> bool:
    """Test database connectivity."""
    result = await db.execute(text("SELECT 1"))
    return result.scalar() == 1


async def get_database_statistics(db: AsyncSession) -> Dict[str, Any]:
    """Get database statistics."""
    stats = {}
    if async_engine:
        try:
            result = await db.execute(text("""
                SELECT 
                    count(*) as active_connections,
                    max(state_change) as last_activity
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """))
            row = result.first()
            if row:
                stats = {
                    "active_connections": row.active_connections,
                    "last_activity": row.last_activity.isoformat() if row.last_activity else None
                }
        except Exception as e:
            logger.warning(f"Could not fetch database statistics: {e}")
    return stats


def build_database_health_response(
    db_connected: bool, pool_status: Dict, stats: Dict
) -> Dict[str, Any]:
    """Build database health response."""
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "connected": db_connected,
        "pool_status": pool_status,
        "database_stats": stats,
        "timestamp": datetime.now(UTC).isoformat()
    }


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu_percent": cpu_percent,
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "free": disk.free,
            "percent": disk.percent
        }
    }


def get_process_metrics() -> Dict[str, Any]:
    """Get process-specific metrics."""
    process = psutil.Process()
    process_memory = process.memory_info()
    return {
        "memory_rss": process_memory.rss,
        "memory_vms": process_memory.vms,
        "cpu_percent": process.cpu_percent(),
        "num_threads": process.num_threads(),
        "connections": len(process.connections(kind='inet'))
    }


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


def get_pool_configuration() -> Dict[str, Any]:
    """Get pool configuration data."""
    return {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "max_connections": 100
    }


def calculate_pool_utilization(pool_status: Dict) -> Dict[str, Any]:
    """Calculate pool utilization metrics."""
    utilization = {}
    if pool_status.get("async"):
        async_pool = pool_status["async"]
        if async_pool.get("size") is not None and async_pool.get("checked_in") is not None:
            active = async_pool["size"] - async_pool["checked_in"]
            total_capacity = async_pool["size"] + async_pool.get("overflow", 0)
            utilization = {
                "active_connections": active,
                "utilization_percent": (active / total_capacity) * 100 if total_capacity else 0
            }
    return utilization