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
        await _execute_postgres_query()
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("postgres", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("postgres", str(e), response_time)

async def _execute_postgres_query() -> None:
    """Execute test query on PostgreSQL database."""
    from app.db.postgres import async_engine
    from sqlalchemy import text
    if async_engine is None:
        raise RuntimeError("Database engine not initialized")
    async with async_engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def check_clickhouse_health() -> HealthCheckResult:
    """Check ClickHouse database connectivity and health."""
    start_time = time.time()
    try:
        return await _process_clickhouse_health_check(start_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _handle_clickhouse_error(e, response_time)

async def _process_clickhouse_health_check(start_time: float) -> HealthCheckResult:
    """Process ClickHouse health check logic."""
    disabled_result = _check_clickhouse_disabled_status()
    if disabled_result:
        return disabled_result
    await _execute_clickhouse_query()
    response_time = (time.time() - start_time) * 1000
    return _create_success_result("clickhouse", response_time)

def _check_clickhouse_disabled_status() -> Optional[HealthCheckResult]:
    """Check if ClickHouse is disabled and return appropriate result."""
    if _is_development_mode() and _is_clickhouse_disabled():
        return _create_disabled_result("clickhouse", "ClickHouse disabled in development")
    return None

async def _execute_clickhouse_query() -> None:
    """Execute test query on ClickHouse database."""
    from app.db.clickhouse import get_clickhouse_client
    async with get_clickhouse_client() as client:
        await client.execute("SELECT 1")

def _handle_clickhouse_error(error: Exception, response_time: float) -> HealthCheckResult:
    """Handle ClickHouse connection errors based on environment."""
    error_msg = str(error)
    if _is_development_mode():
        return _create_disabled_result("clickhouse", f"ClickHouse unavailable in development: {error_msg}")
    return _create_failed_result("clickhouse", error_msg, response_time)


async def check_redis_health() -> HealthCheckResult:
    """Check Redis connectivity and health."""
    start_time = time.time()
    try:
        await _execute_redis_ping()
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("redis", response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("redis", str(e), response_time)

async def _execute_redis_ping() -> None:
    """Execute Redis ping operation."""
    client = await _get_redis_client_or_fail()
    await client.ping()

async def _get_redis_client_or_fail():
    """Get Redis client or raise appropriate exception."""
    from app.redis_manager import redis_manager
    if not redis_manager.enabled:
        raise RuntimeError("Redis disabled in development")
    client = await redis_manager.get_client()
    if client is None:
        raise RuntimeError("Redis client not available")
    return client


async def check_websocket_health() -> HealthCheckResult:
    """Check WebSocket connection manager health."""
    start_time = time.time()
    try:
        stats, health_score = _get_websocket_stats_and_score()
        response_time = (time.time() - start_time) * 1000
        return _create_websocket_health_result(stats, health_score, response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("websocket", str(e), response_time)

def _get_websocket_stats_and_score() -> tuple[Dict[str, Any], float]:
    """Get WebSocket connection stats and calculate health score."""
    from app.websocket.connection import connection_manager
    stats = connection_manager.get_stats()
    health_score = _calculate_websocket_health_score(stats)
    return stats, health_score


def check_system_resources() -> HealthCheckResult:
    """Check system resource usage (CPU, memory, disk)."""
    start_time = time.time()
    try:
        metrics, score = _get_system_metrics_and_score()
        response_time = (time.time() - start_time) * 1000
        return _create_system_health_result(metrics, score, response_time)
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("system_resources", str(e), response_time)

def _get_system_metrics_and_score() -> tuple[Dict[str, Any], float]:
    """Get system resource metrics and calculate overall health score."""
    resource_metrics = _gather_system_resource_metrics()
    overall_score = _calculate_overall_system_health(resource_metrics)
    return resource_metrics, overall_score

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
    details = _build_system_health_details(metrics, overall_score)
    return HealthCheckResult(
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_system_health_details(metrics: Dict[str, Any], overall_score: float) -> Dict[str, Any]:
    """Build details dictionary for system health result."""
    return {
        "component_name": "system_resources",
        "success": True,
        "health_score": overall_score,
        "metadata": _create_system_metadata(metrics)
    }

def _create_system_metadata(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Create metadata dictionary for system health check."""
    base_metrics = _extract_base_system_metrics(metrics)
    computed_metrics = _compute_system_metrics(metrics)
    return {**base_metrics, **computed_metrics}

def _extract_base_system_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Extract basic system metrics."""
    return {
        "cpu_percent": metrics["cpu_percent"],
        "memory_percent": metrics["memory"].percent,
        "disk_percent": metrics["disk"].percent
    }

def _compute_system_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compute derived system metrics."""
    return {
        "memory_available_gb": metrics["memory"].available / (1024**3),
        "disk_free_gb": metrics["disk"].free / (1024**3)
    }


def _create_success_result(component: str, response_time: float) -> HealthCheckResult:
    """Create a successful health check result."""
    details = _build_success_details(component)
    return HealthCheckResult(
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_success_details(component: str) -> Dict[str, Any]:
    """Build details dictionary for successful health check."""
    return {
        "component_name": component,
        "success": True,
        "health_score": 1.0
    }


def _create_failed_result(component: str, error: str, response_time: float = 0.0) -> HealthCheckResult:
    """Create a failed health check result."""
    details = _build_failure_details(component, error)
    return HealthCheckResult(
        status="unhealthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_failure_details(component: str, error: str) -> Dict[str, Any]:
    """Build details dictionary for failed health check."""
    return {
        "component_name": component,
        "success": False,
        "health_score": 0.0,
        "error_message": error
    }


def _create_disabled_result(component: str, reason: str) -> HealthCheckResult:
    """Create a disabled service health check result."""
    details = _build_disabled_details(component, reason)
    return HealthCheckResult(
        status="healthy",
        response_time=0.0,
        details=details
    )

def _build_disabled_details(component: str, reason: str) -> Dict[str, Any]:
    """Build details dictionary for disabled service health check."""
    return {
        "component_name": component,
        "success": True,
        "health_score": 1.0,
        "status": "disabled",
        "reason": reason
    }


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
    details = _build_websocket_health_details(stats, health_score)
    return HealthCheckResult(
        status="healthy",
        response_time=response_time / 1000,
        details=details
    )

def _build_websocket_health_details(stats: Dict[str, Any], health_score: float) -> Dict[str, Any]:
    """Build details dictionary for WebSocket health result."""
    return {
        "component_name": "websocket",
        "success": True,
        "health_score": health_score,
        "metadata": stats
    }


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