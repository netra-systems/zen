"""Database connection management with ≤8 line functions.

Manages database connections with recovery capabilities using aggressive
function decomposition. All functions ≤8 lines.
"""

import asyncio
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.database_types import DatabaseType, DatabaseConfig, PoolMetrics, PoolHealth
from netra_backend.app.core.database_health_monitoring import CoreDatabaseHealthChecker as DatabaseHealthChecker
from netra_backend.app.core.database_recovery_core import (
    DatabaseRecoveryStrategy, ConnectionPoolRefreshStrategy, 
    ConnectionPoolRecreateStrategy
)

logger = central_logger.get_logger(__name__)


class DatabaseConnectionManager:
    """Manages database connections with recovery capabilities."""
    
    def __init__(self, db_type: DatabaseType):
        """Initialize database connection manager."""
        self.db_type = db_type
        self.pools: Dict[str, Any] = {}
        self.configs: Dict[str, DatabaseConfig] = {}
        self.metrics_history: Dict[str, List[PoolMetrics]] = {}
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize health checker and recovery components."""
        self.health_checker = DatabaseHealthChecker(self.db_type)
        self.recovery_strategies: List[DatabaseRecoveryStrategy] = []
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_interval = 60
        self._setup_default_strategies()
    
    def _setup_default_strategies(self) -> None:
        """Setup default recovery strategies."""
        self.recovery_strategies = [
            ConnectionPoolRefreshStrategy(),
            ConnectionPoolRecreateStrategy()
        ]
        self.recovery_strategies.sort(key=lambda s: s.get_priority())
    
    def add_recovery_strategy(self, strategy: DatabaseRecoveryStrategy) -> None:
        """Add custom recovery strategy."""
        self.recovery_strategies.append(strategy)
        self.recovery_strategies.sort(key=lambda s: s.get_priority())
    
    def register_pool(self, pool_id: str, pool: Any, config: DatabaseConfig) -> None:
        """Register database pool for monitoring."""
        self.pools[pool_id] = pool
        self.configs[pool_id] = config
        self.metrics_history[pool_id] = []
        self._set_pool_id(pool, pool_id)
        logger.info(f"Registered database pool: {pool_id}")
    
    def _set_pool_id(self, pool: Any, pool_id: str) -> None:
        """Set pool ID for identification."""
        if hasattr(pool, '_pool_id'):
            pool._pool_id = pool_id
    
    async def start_monitoring(self) -> None:
        """Start database health monitoring."""
        if self.monitoring_active:
            return
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started database monitoring for {self.db_type.value}")
    
    async def stop_monitoring(self) -> None:
        """Stop database health monitoring."""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            await self._wait_for_task_completion()
        logger.info(f"Stopped database monitoring for {self.db_type.value}")
    
    async def _wait_for_task_completion(self) -> None:
        """Wait for monitoring task to complete."""
        try:
            await self.monitor_task
        except asyncio.CancelledError:
            pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_pools()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Database monitoring error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _check_all_pools(self) -> None:
        """Check health of all registered pools."""
        for pool_id, pool in self.pools.items():
            try:
                await self._check_individual_pool(pool_id, pool)
            except Exception as e:
                logger.error(f"Pool health check failed {pool_id}: {e}")
    
    async def _check_individual_pool(self, pool_id: str, pool: Any) -> None:
        """Check health of individual pool."""
        metrics = await self.health_checker.check_pool_health(pool)
        self._store_metrics(pool_id, metrics)
        if self._requires_recovery(metrics):
            await self._attempt_recovery(pool_id, pool, metrics)
    
    def _store_metrics(self, pool_id: str, metrics: PoolMetrics) -> None:
        """Store metrics and maintain history limit."""
        self.metrics_history[pool_id].append(metrics)
        if len(self.metrics_history[pool_id]) > 100:
            self.metrics_history[pool_id] = self.metrics_history[pool_id][-50:]
    
    def _requires_recovery(self, metrics: PoolMetrics) -> bool:
        """Check if metrics indicate recovery is needed."""
        return metrics.health_status in [PoolHealth.UNHEALTHY, PoolHealth.CRITICAL]
    
    async def _attempt_recovery(self, pool_id: str, pool: Any, metrics: PoolMetrics) -> bool:
        """Attempt to recover unhealthy pool."""
        config = self.configs[pool_id]
        logger.warning(
            f"Attempting recovery for unhealthy pool: {pool_id} "
            f"(status: {metrics.health_status.value})"
        )
        return await self._execute_recovery_strategies(pool_id, pool, config, metrics)
    
    async def _execute_recovery_strategies(self, pool_id: str, pool: Any, 
                                         config: DatabaseConfig, metrics: PoolMetrics) -> bool:
        """Execute recovery strategies in priority order."""
        for strategy in self.recovery_strategies:
            try:
                if await self._try_recovery_strategy(strategy, pool_id, pool, config, metrics):
                    return True
            except Exception as e:
                logger.error(f"Recovery strategy failed {type(strategy).__name__}: {e}")
        logger.error(f"All recovery strategies failed for pool: {pool_id}")
        return False
    
    async def _try_recovery_strategy(self, strategy: DatabaseRecoveryStrategy, pool_id: str,
                                   pool: Any, config: DatabaseConfig, metrics: PoolMetrics) -> bool:
        """Try individual recovery strategy."""
        if await strategy.can_recover(metrics):
            success = await strategy.execute_recovery(pool, config)
            if success:
                logger.info(f"Recovery successful using {type(strategy).__name__}: {pool_id}")
                return True
        return False
    
    async def force_recovery(self, pool_id: str) -> bool:
        """Force recovery attempt for specific pool."""
        if pool_id not in self.pools:
            return False
        pool = self.pools[pool_id]
        metrics = await self.health_checker.check_pool_health(pool)
        return await self._attempt_recovery(pool_id, pool, metrics)
    
    def get_pool_status(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific pool."""
        if pool_id not in self.metrics_history or not self.metrics_history[pool_id]:
            return None
        return self._build_pool_status(pool_id, self.metrics_history[pool_id][-1])
    
    def _build_pool_status(self, pool_id: str, metrics: PoolMetrics) -> Dict[str, Any]:
        """Build pool status dictionary."""
        return {
            'pool_id': pool_id, 'database_type': self.db_type.value,
            'health_status': metrics.health_status.value,
            'total_connections': metrics.total_connections,
            'active_connections': metrics.active_connections,
            'idle_connections': metrics.idle_connections,
            'failed_connections': metrics.failed_connections,
            'avg_response_time': metrics.avg_response_time,
            'last_health_check': metrics.last_health_check.isoformat() if metrics.last_health_check else None
        }
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all pools."""
        return {
            'database_type': self.db_type.value,
            'monitoring_active': self.monitoring_active,
            'pools': {
                pool_id: self.get_pool_status(pool_id)
                for pool_id in self.pools.keys()
            }
        }


class DatabaseRecoveryRegistry:
    """Registry for database connection managers."""
    
    def __init__(self):
        """Initialize registry."""
        self.managers: Dict[DatabaseType, DatabaseConnectionManager] = {}
    
    def get_manager(self, db_type: DatabaseType) -> DatabaseConnectionManager:
        """Get or create database manager for type."""
        if db_type not in self.managers:
            self.managers[db_type] = DatabaseConnectionManager(db_type)
        return self.managers[db_type]
    
    async def start_all_monitoring(self) -> None:
        """Start monitoring for all database types."""
        for manager in self.managers.values():
            await manager.start_monitoring()
    
    async def stop_all_monitoring(self) -> None:
        """Stop monitoring for all database types."""
        for manager in self.managers.values():
            await manager.stop_monitoring()
    
    def get_global_status(self) -> Dict[str, Any]:
        """Get status of all database managers."""
        return {
            db_type.value: manager.get_all_status()
            for db_type, manager in self.managers.items()
        }


# Global database recovery registry
database_recovery_registry = DatabaseRecoveryRegistry()


# Convenience functions with ≤8 lines each
def register_postgresql_pool(pool_id: str, pool: Any, config: DatabaseConfig) -> None:
    """Register PostgreSQL pool for monitoring."""
    manager = database_recovery_registry.get_manager(DatabaseType.POSTGRESQL)
    manager.register_pool(pool_id, pool, config)


def register_clickhouse_pool(pool_id: str, pool: Any, config: DatabaseConfig) -> None:
    """Register ClickHouse pool for monitoring."""
    manager = database_recovery_registry.get_manager(DatabaseType.CLICKHOUSE)
    manager.register_pool(pool_id, pool, config)


async def setup_database_monitoring() -> None:
    """Setup database monitoring for all types."""
    await database_recovery_registry.start_all_monitoring()