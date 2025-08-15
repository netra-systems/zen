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
        
        if async_engine is None:
            return _create_failed_result("postgres", "Database engine not initialized")
        
        async with async_engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("postgres", response_time)
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("postgres", str(e), response_time)


async def check_clickhouse_health() -> HealthCheckResult:
    """Check ClickHouse database connectivity and health."""
    start_time = time.time()
    
    try:
        from app.db.clickhouse import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            await client.execute("SELECT 1")
        
        response_time = (time.time() - start_time) * 1000
        return _create_success_result("clickhouse", response_time)
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
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
        active_connections = stats.get("active_connections", 0)
        
        # Consider healthy if manager is responsive and connections reasonable
        health_score = min(1.0, max(0.7, 1.0 - (active_connections / 1000)))
        
        response_time = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component_name="websocket",
            success=True,
            health_score=health_score,
            response_time_ms=response_time,
            metadata=stats
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("websocket", str(e), response_time)


def check_system_resources() -> HealthCheckResult:
    """Check system resource usage (CPU, memory, disk)."""
    start_time = time.time()
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Calculate health score based on resource usage
        cpu_score = max(0.0, 1.0 - (cpu_percent / 100))
        memory_score = max(0.0, 1.0 - (memory.percent / 100))
        disk_score = max(0.0, 1.0 - (disk.percent / 100))
        
        overall_score = (cpu_score + memory_score + disk_score) / 3
        
        response_time = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component_name="system_resources",
            success=True,
            health_score=overall_score,
            response_time_ms=response_time,
            metadata={
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3)
            }
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return _create_failed_result("system_resources", str(e), response_time)


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