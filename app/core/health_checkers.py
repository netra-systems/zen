"""Database and service health checkers.

Individual health check implementations for system components.
"""

import asyncio
import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime

from app.logging_config import central_logger
from .health_types import HealthCheckResult

logger = central_logger.get_logger(__name__)


async def check_postgres_health() -> HealthCheckResult:
    """Check PostgreSQL database connectivity and health."""
    start_time = time.time()
    
    try:
        from app.db.postgres import async_engine
        from sqlalchemy import text
        
        if async_engine is None:
            return _create_failed_result("postgres", "Database engine not initialized")
        
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("postgres", response_time)
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("postgres", str(e), response_time)


async def check_clickhouse_health() -> HealthCheckResult:
    """Check ClickHouse database connectivity and health."""
    start_time = time.time()
    
    try:
        # Check if ClickHouse is disabled in development
        import os
        if _is_development_mode() and _is_clickhouse_disabled():
            return _create_disabled_result("clickhouse", "ClickHouse disabled in development")
        
        from app.db.clickhouse import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            await client.execute("SELECT 1")
        
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("clickhouse", response_time)
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        # In development mode, treat ClickHouse as optional
        if _is_development_mode():
            return _create_disabled_result("clickhouse", f"ClickHouse unavailable in development: {str(e)}")
        return _create_failed_result("clickhouse", str(e), response_time)


async def check_redis_health() -> HealthCheckResult:
    """Check Redis connectivity and health."""
    start_time = time.time()
    
    try:
        from app.redis_manager import redis_manager
        
        if not redis_manager.enabled:
            return _create_disabled_result("redis", "Redis disabled in development")
        
        client = await redis_manager.get_client()
        if client is None:
            return _create_failed_result("redis", "Redis client not available")
        
        await client.ping()
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("redis", response_time)
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("redis", str(e), response_time)


async def check_websocket_health() -> HealthCheckResult:
    """Check WebSocket connection manager health."""
    start_time = time.time()
    try:
        from app.websocket.connection import connection_manager
        stats = connection_manager.get_stats()
        health_score = _calculate_websocket_health_score(stats)
        response_time = (time.time() - start_time) * 1000
        return _create_websocket_health_result(stats, health_score, response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("websocket", str(e), response_time)


def check_system_resources() -> HealthCheckResult:
    """Check system resource usage (CPU, memory, disk)."""
    start_time = time.time()
    try:
        resource_metrics = _gather_system_resource_metrics()
        overall_score = _calculate_overall_system_health(resource_metrics)
        response_time = (time.time() - start_time) * 1000
        return _create_system_health_result(resource_metrics, overall_score, response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("system_resources", str(e), response_time)

def _gather_system_resource_metrics() -> Dict[str, Any]:
    """Gather CPU, memory, and disk metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {"cpu_percent": cpu_percent, "memory": memory, "disk": disk}

def _calculate_resource_health_scores(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Calculate health scores for each resource type."""
    cpu_score = max(0.0, 1.0 - (metrics["cpu_percent"] / 100))
    memory_score = max(0.0, 1.0 - (metrics["memory"].percent / 100))
    disk_score = max(0.0, 1.0 - (metrics["disk"].percent / 100))
    return {"cpu": cpu_score, "memory": memory_score, "disk": disk_score}

def _calculate_overall_health_score(health_scores: Dict[str, float]) -> float:
    """Calculate overall health score from individual scores."""
    return sum(health_scores.values()) / len(health_scores)

def _create_system_health_result(metrics: Dict[str, Any], overall_score: float, response_time: float) -> HealthCheckResult:
    """Create HealthCheckResult for system resources."""
    return HealthCheckResult(
        component_name="system_resources",
        success=True,
        health_score=overall_score,
        response_time_ms=response_time,
        metadata=_create_system_metadata(metrics)
    )

def _create_system_metadata(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata dictionary for system health check."""
    return {
        "cpu_percent": metrics["cpu_percent"],
        "memory_percent": metrics["memory"].percent,
        "disk_percent": metrics["disk"].percent,
        "memory_available_gb": metrics["memory"].available / (1024**3),
        "disk_free_gb": metrics["disk"].free / (1024**3)
    }


def _create_success_result(component: str, response_time: float) -> HealthCheckResult:
    """Create a successful health check result."""
    return HealthCheckResult(
        component_name=component,
        success=True,
        health_score=1.0,
        response_time_ms=response_time
    )


def _create_failed_result(component: str, error: str, response_time: float = 0.0) -> HealthCheckResult:
    """Create a failed health check result."""
    return HealthCheckResult(
        component_name=component,
        success=False,
        health_score=0.0,
        response_time_ms=response_time,
        error_message=error
    )


def _create_disabled_result(component: str, reason: str) -> HealthCheckResult:
    """Create a disabled service health check result."""
    return HealthCheckResult(
        component_name=component,
        success=True,
        health_score=1.0,
        response_time_ms=0.0,
        metadata={"status": "disabled", "reason": reason}
    )


def _calculate_overall_system_health(resource_metrics: Dict[str, Any]) -> float:
    """Calculate overall system health score from resource metrics."""
    health_scores = _calculate_resource_health_scores(resource_metrics)
    return _calculate_overall_health_score(health_scores)


def _calculate_websocket_health_score(stats: Dict[str, Any]) -> float:
    """Calculate WebSocket health score from connection stats."""
    active_connections = stats.get("active_connections", 0)
    return min(1.0, max(0.7, 1.0 - (active_connections / 1000)))


def _create_websocket_health_result(stats: Dict[str, Any], health_score: float, response_time: float) -> HealthCheckResult:
    """Create HealthCheckResult for WebSocket health check."""
    return HealthCheckResult(
        component_name="websocket",
        success=True,
        health_score=health_score,
        response_time_ms=response_time,
        metadata=stats
    )


def _is_development_mode() -> bool:
    """Check if running in development mode."""
    import os
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    return environment == "development"


def _is_clickhouse_disabled() -> bool:
    """Check if ClickHouse is disabled in environment."""
    import os
    clickhouse_mode = os.environ.get("CLICKHOUSE_MODE", "shared").lower()
    skip_clickhouse = os.environ.get("SKIP_CLICKHOUSE_INIT", "false").lower()
    return clickhouse_mode == "disabled" or skip_clickhouse == "true"