"""Extended health check endpoints with detailed monitoring."""
import asyncio
from datetime import UTC, datetime
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.postgres import async_engine, get_pool_status
from netra_backend.app.dependencies import get_db_dependency
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.error_handlers import handle_database_error
from netra_backend.app.routes.utils.health_helpers import (
    build_database_health_response,
    build_system_error_response,
    build_system_health_response,
    calculate_pool_utilization,
    get_database_statistics,
    get_pool_configuration,
    get_process_metrics,
    get_system_metrics,
    test_database_connectivity,
)

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

async def _check_database_health(db: AsyncSession) -> Dict[str, Any]:
    """Check database health components."""
    db_connected = await test_database_connectivity(db)
    pool_status = get_pool_status()
    stats = await get_database_statistics(db)
    return build_database_health_response(db_connected, pool_status, stats)

@router.get("/database")
async def health_database(db: AsyncSession = Depends(get_db_dependency)) -> Dict[str, Any]:
    """Check database health and connection pool status."""
    try:
        return await _check_database_health(db)
    except Exception as e:
        handle_database_error(e)

def _gather_system_health_data() -> Dict[str, Any]:
    """Gather system health data."""
    system_metrics = get_system_metrics()
    process_metrics = get_process_metrics()
    return build_system_health_response(system_metrics, process_metrics)

@router.get("/system")
async def health_system() -> Dict[str, Any]:
    """Check system resource usage."""
    try:
        return _gather_system_health_data()
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return build_system_error_response(str(e))

def _build_base_pool_metrics(pool_status: Dict) -> Dict[str, Any]:
    """Build base pool metrics."""
    return {
        "pool_configuration": get_pool_configuration(),
        "current_status": pool_status,
        "timestamp": datetime.now(UTC).isoformat()
    }

def _build_pool_metrics() -> Dict[str, Any]:
    """Build pool metrics response."""
    pool_status = get_pool_status()
    metrics = _build_base_pool_metrics(pool_status)
    utilization = calculate_pool_utilization(pool_status)
    if utilization:
        metrics["utilization"] = utilization
    return metrics

@router.get("/pool-metrics")
async def pool_metrics() -> Dict[str, Any]:
    """Get detailed connection pool metrics for monitoring."""
    return _build_pool_metrics()