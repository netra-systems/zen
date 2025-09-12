"""Database health monitoring with  <= 8 line functions.

Provides health checking for database connection pools with aggressive
function decomposition. All functions  <= 8 lines.
"""

from datetime import datetime
from typing import Any

from netra_backend.app.core.database_types import DatabaseType, PoolHealth, PoolMetrics
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# Import DatabaseHealthChecker from canonical location - CONSOLIDATED
from netra_backend.app.db.health_checks import (
    DatabaseHealthChecker as CoreDatabaseHealthChecker,
)


class PoolHealthChecker:
    """Health checker for database connections -  <= 8 lines per function."""
    
    def __init__(self, db_type: DatabaseType):
        """Initialize health checker."""
        self.db_type = db_type
        self.health_queries = self._create_health_queries()
    
    def _create_health_queries(self) -> dict:
        """Create health check queries by database type."""
        return {
            DatabaseType.POSTGRESQL: "SELECT 1",
            DatabaseType.CLICKHOUSE: "SELECT 1",
            DatabaseType.REDIS: "PING"
        }
    
    async def check_pool_health(self, pool: Any) -> PoolMetrics:
        """Check health of database connection pool."""
        start_time = datetime.now()
        try:
            return await self._execute_health_check(pool, start_time)
        except Exception as e:
            return self._create_error_metrics(pool, e)
    
    async def _execute_health_check(self, pool: Any, start_time: datetime) -> PoolMetrics:
        """Execute health check and calculate metrics."""
        metrics = self._get_pool_metrics(pool)
        await self._perform_health_query(pool)
        response_time = self._calculate_response_time(start_time)
        return self._finalize_metrics(metrics, response_time)
    
    async def _perform_health_query(self, pool: Any) -> None:
        """Perform the actual health check query."""
        query = self.health_queries.get(self.db_type, "SELECT 1")
        async with pool.acquire() as conn:
            if self.db_type == DatabaseType.REDIS:
                await conn.ping()
            else:
                await conn.fetchval(query)
    
    def _calculate_response_time(self, start_time: datetime) -> float:
        """Calculate response time in seconds."""
        return (datetime.now() - start_time).total_seconds()
    
    def _finalize_metrics(self, metrics: PoolMetrics, response_time: float) -> PoolMetrics:
        """Finalize metrics with response time and health status."""
        metrics.avg_response_time = response_time
        metrics.last_health_check = datetime.now()
        metrics.health_status = self._determine_health_status(metrics)
        return metrics
    
    def _create_error_metrics(self, pool: Any, error: Exception) -> PoolMetrics:
        """Create metrics for failed health check."""
        logger.error(f"Database health check failed: {error}")
        metrics = self._get_pool_metrics(pool)
        metrics.connection_errors += 1
        metrics.health_status = PoolHealth.UNHEALTHY
        metrics.last_health_check = datetime.now()
        return metrics
    
    def _get_pool_metrics(self, pool: Any) -> PoolMetrics:
        """Extract metrics from pool object."""
        pool_id = getattr(pool, '_pool_id', str(id(pool)))
        total_connections = self._get_total_connections(pool)
        active_connections = self._get_active_connections(pool)
        idle_connections = total_connections - active_connections
        return self._create_metrics_object(pool_id, total_connections, active_connections, idle_connections)
    
    def _get_total_connections(self, pool: Any) -> int:
        """Get total connection count from pool."""
        try:
            if hasattr(pool, 'size'):
                return pool.size
            elif hasattr(pool, '_pool'):
                return len(pool._pool)
            return 0
        except Exception:
            return 0
    
    def _get_active_connections(self, pool: Any) -> int:
        """Get active connection count from pool."""
        try:
            if hasattr(pool, '_used'):
                return len(pool._used)
            elif hasattr(pool, '_in_use'):
                return pool._in_use
            return 0
        except Exception:
            return 0
    
    def _create_metrics_object(self, pool_id: str, total: int, active: int, idle: int) -> PoolMetrics:
        """Create PoolMetrics object with connection counts."""
        return PoolMetrics(
            pool_id=pool_id, database_type=self.db_type,
            total_connections=total, active_connections=active,
            idle_connections=idle
        )
    
    def _determine_health_status(self, metrics: PoolMetrics) -> PoolHealth:
        """Determine health status from metrics."""
        if self._is_critical_status(metrics):
            return PoolHealth.CRITICAL
        elif self._is_unhealthy_status(metrics):
            return PoolHealth.UNHEALTHY
        elif self._is_degraded_status(metrics):
            return PoolHealth.DEGRADED
        return PoolHealth.HEALTHY
    
    def _is_critical_status(self, metrics: PoolMetrics) -> bool:
        """Check if metrics indicate critical status."""
        return metrics.total_connections == 0 or metrics.connection_errors > 10
    
    def _is_unhealthy_status(self, metrics: PoolMetrics) -> bool:
        """Check if metrics indicate unhealthy status."""
        return metrics.avg_response_time > 5.0 or metrics.failed_connections > 5
    
    def _is_degraded_status(self, metrics: PoolMetrics) -> bool:
        """Check if metrics indicate degraded status."""
        return metrics.avg_response_time > 2.0 or metrics.failed_connections > 2