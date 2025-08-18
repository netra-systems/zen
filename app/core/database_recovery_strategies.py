"""Database connection recovery and pool management strategies.

Provides comprehensive database connection recovery, pool health monitoring,
and failover mechanisms for PostgreSQL and ClickHouse databases.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from app.logging_config import central_logger

# Import consolidated types
from .database_types import DatabaseType, PoolHealth, DatabaseConfig, PoolMetrics
from .database_health_monitoring import DatabaseHealthChecker

logger = central_logger.get_logger(__name__)


# Types imported from database_types.py


# DatabaseHealthChecker imported from database_health_monitoring.py


class DatabaseRecoveryStrategy(ABC):
    """Abstract base for database recovery strategies."""
    
    @abstractmethod
    async def can_recover(self, metrics: PoolMetrics) -> bool:
        """Check if strategy can recover the pool."""
        pass
    
    @abstractmethod
    async def execute_recovery(self, pool: Any, config: DatabaseConfig) -> bool:
        """Execute recovery strategy."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get strategy priority (lower = higher priority)."""
        pass


class ConnectionPoolRefreshStrategy(DatabaseRecoveryStrategy):
    """Strategy to refresh stale connections in pool."""
    
    async def can_recover(self, metrics: PoolMetrics) -> bool:
        """Check if pool refresh can help."""
        return metrics.health_status in [
            PoolHealth.DEGRADED,
            PoolHealth.UNHEALTHY
        ]
    
    async def execute_recovery(self, pool: Any, config: DatabaseConfig) -> bool:
        """Refresh connections in pool."""
        try:
            logger.info(f"Refreshing connection pool: {config.database}")
            await self._close_idle_connections(pool)
            return await self._test_connection_refresh(pool, config)
        except Exception as e:
            return self._handle_refresh_error(e)
    
    def _handle_refresh_error(self, error: Exception) -> bool:
        """Handle pool refresh errors."""
        logger.error(f"Pool refresh failed: {error}")
        return False
    
    async def _close_idle_connections(self, pool: Any) -> None:
        """Close idle connections in the pool."""
        if hasattr(pool, 'expire'):
            await pool.expire()
        elif hasattr(pool, '_cleanup'):
            await pool._cleanup()
    
    async def _test_connection_refresh(self, pool: Any, config: DatabaseConfig) -> bool:
        """Test connection refresh by creating new connections."""
        test_connections = []
        try:
            await self._acquire_test_connections(pool, config, test_connections)
            await self._release_test_connections(pool, test_connections)
            return self._log_refresh_success()
        except Exception as e:
            return await self._handle_test_error(e, pool, test_connections)
    
    def _log_refresh_success(self) -> bool:
        """Log successful refresh and return True."""
        logger.info("Connection pool refresh successful")
        return True
    
    async def _handle_test_error(self, error: Exception, pool: Any, test_connections: list) -> bool:
        """Handle test connection errors."""
        logger.error(f"Failed to refresh connections: {error}")
        await self._release_test_connections(pool, test_connections)
        return False
    
    async def _acquire_test_connections(self, pool: Any, config: DatabaseConfig, test_connections: list) -> None:
        """Acquire test connections for validation."""
        for _ in range(min(3, config.pool_size)):
            conn = await pool.acquire()
            test_connections.append(conn)
    
    async def _release_test_connections(self, pool: Any, test_connections: list) -> None:
        """Release all test connections safely."""
        for conn in test_connections:
            try:
                await pool.release(conn)
            except Exception:
                pass
    
    def get_priority(self) -> int:
        """Pool refresh has high priority."""
        return 1


class ConnectionPoolRecreateStrategy(DatabaseRecoveryStrategy):
    """Strategy to recreate the entire connection pool."""
    
    async def can_recover(self, metrics: PoolMetrics) -> bool:
        """Check if pool recreation is needed."""
        return metrics.health_status in [
            PoolHealth.UNHEALTHY,
            PoolHealth.CRITICAL
        ]
    
    async def execute_recovery(self, pool: Any, config: DatabaseConfig) -> bool:
        """Recreate the connection pool."""
        try:
            self._log_recreation_attempt(config)
            await self._close_all_connections(pool)
            await self._wait_before_reconnection()
            return await self._attempt_pool_reconnection(pool)
        except Exception as e:
            return self._handle_recreation_error(e)
    
    def _log_recreation_attempt(self, config: DatabaseConfig) -> None:
        """Log pool recreation attempt."""
        logger.warning(f"Recreating connection pool: {config.database}")
    
    async def _wait_before_reconnection(self) -> None:
        """Wait before attempting reconnection."""
        await asyncio.sleep(1.0)
    
    def _handle_recreation_error(self, error: Exception) -> bool:
        """Handle pool recreation errors."""
        logger.error(f"Pool recreation failed: {error}")
        return False
    
    async def _close_all_connections(self, pool: Any) -> None:
        """Close all connections in the pool."""
        if hasattr(pool, 'close'):
            await pool.close()
        elif hasattr(pool, 'terminate'):
            await pool.terminate()
    
    async def _attempt_pool_reconnection(self, pool: Any) -> bool:
        """Attempt to reconnect the pool."""
        if hasattr(pool, 'reconnect'):
            await pool.reconnect()
            return True
        logger.warning("Pool recreation requires manual intervention")
        return False
    
    def get_priority(self) -> int:
        """Pool recreation has lower priority."""
        return 3


class DatabaseFailoverStrategy(DatabaseRecoveryStrategy):
    """Strategy to failover to backup database."""
    
    def __init__(self, backup_configs: List[DatabaseConfig]):
        """Initialize with backup database configurations."""
        self.backup_configs = backup_configs
        self.current_backup_index = 0
    
    async def can_recover(self, metrics: PoolMetrics) -> bool:
        """Check if failover is possible."""
        return (
            metrics.health_status == PoolHealth.CRITICAL and
            len(self.backup_configs) > 0
        )
    
    async def execute_recovery(self, pool: Any, config: DatabaseConfig) -> bool:
        """Execute failover to backup database."""
        if not self._validate_backup_configs():
            return False
        try:
            backup_config = self._get_next_backup_config()
            self._log_failover_attempt(backup_config)
            return await self._perform_failover(backup_config)
        except Exception as e:
            return self._handle_failover_error(e)
    
    def _validate_backup_configs(self) -> bool:
        """Validate that backup configurations exist."""
        return bool(self.backup_configs)
    
    def _handle_failover_error(self, error: Exception) -> bool:
        """Handle failover execution errors."""
        logger.error(f"Database failover failed: {error}")
        return False
    
    def _get_next_backup_config(self) -> DatabaseConfig:
        """Get the next backup configuration in rotation."""
        backup_config = self.backup_configs[self.current_backup_index]
        self.current_backup_index = (
            (self.current_backup_index + 1) % len(self.backup_configs)
        )
        return backup_config
    
    def _log_failover_attempt(self, backup_config: DatabaseConfig) -> None:
        """Log the failover attempt."""
        logger.critical(
            f"Failing over to backup database: "
            f"{backup_config.host}:{backup_config.port}"
        )
    
    async def _perform_failover(self, backup_config: DatabaseConfig) -> bool:
        """Perform the actual failover operation."""
        try:
            from app.db.postgres import update_connection_config
            await update_connection_config(backup_config)
            return self._log_failover_success()
        except Exception as failover_error:
            return self._log_failover_failure(failover_error)
    
    def _log_failover_success(self) -> bool:
        """Log successful failover and return True."""
        logger.info(f"Successfully failed over to backup database")
        return True
    
    def _log_failover_failure(self, error: Exception) -> bool:
        """Log failover failure and return False."""
        logger.error(f"Failed to update connection config: {error}")
        return False
    
    def get_priority(self) -> int:
        """Failover has lowest priority."""
        return 4


class DatabaseConnectionManager:
    """Manages database connections with recovery capabilities."""
    
    def __init__(self, db_type: DatabaseType):
        """Initialize database connection manager."""
        self.db_type = db_type
        self._initialize_data_structures()
        self._initialize_recovery_components()
        self._initialize_monitoring_settings()
        self._setup_default_strategies()
    
    def _initialize_data_structures(self) -> None:
        """Initialize core data structures."""
        self.pools: Dict[str, Any] = {}
        self.configs: Dict[str, DatabaseConfig] = {}
        self.metrics_history: Dict[str, List[PoolMetrics]] = {}
    
    def _initialize_recovery_components(self) -> None:
        """Initialize recovery and health checking components."""
        self.health_checker = DatabaseHealthChecker(self.db_type)
        self.recovery_strategies: List[DatabaseRecoveryStrategy] = []
    
    def _initialize_monitoring_settings(self) -> None:
        """Initialize monitoring configuration."""
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_interval = 60  # seconds
    
    def _setup_default_strategies(self) -> None:
        """Setup default recovery strategies."""
        self.recovery_strategies = [
            ConnectionPoolRefreshStrategy(),
            ConnectionPoolRecreateStrategy()
        ]
        self._sort_strategies_by_priority()
    
    def _sort_strategies_by_priority(self) -> None:
        """Sort recovery strategies by priority."""
        self.recovery_strategies.sort(key=lambda s: s.get_priority())
    
    def add_recovery_strategy(self, strategy: DatabaseRecoveryStrategy) -> None:
        """Add custom recovery strategy."""
        self.recovery_strategies.append(strategy)
        self.recovery_strategies.sort(key=lambda s: s.get_priority())
    
    def register_pool(
        self,
        pool_id: str,
        pool: Any,
        config: DatabaseConfig
    ) -> None:
        """Register database pool for monitoring."""
        self._store_pool_data(pool_id, pool, config)
        self._set_pool_identification(pool, pool_id)
        self._log_pool_registration(pool_id)
    
    def _log_pool_registration(self, pool_id: str) -> None:
        """Log successful pool registration."""
        logger.info(f"Registered database pool: {pool_id}")
    
    def _store_pool_data(self, pool_id: str, pool: Any, config: DatabaseConfig) -> None:
        """Store pool data in internal structures."""
        self.pools[pool_id] = pool
        self.configs[pool_id] = config
        self.metrics_history[pool_id] = []
    
    def _set_pool_identification(self, pool: Any, pool_id: str) -> None:
        """Set pool identification if supported."""
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
            await self._cancel_monitor_task()
        self._log_monitoring_stopped()
    
    async def _cancel_monitor_task(self) -> None:
        """Cancel the monitoring task safely."""
        self.monitor_task.cancel()
        try:
            await self.monitor_task
        except asyncio.CancelledError:
            pass
    
    def _log_monitoring_stopped(self) -> None:
        """Log that monitoring has been stopped."""
        logger.info(f"Stopped database monitoring for {self.db_type.value}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_pools()
                await self._sleep_before_next_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_monitoring_error(e)
    
    async def _sleep_before_next_check(self) -> None:
        """Sleep before the next health check cycle."""
        await asyncio.sleep(self.health_check_interval)
    
    async def _handle_monitoring_error(self, error: Exception) -> None:
        """Handle monitoring loop errors."""
        logger.error(f"Database monitoring error: {error}")
        await asyncio.sleep(self.health_check_interval)
    
    async def _check_all_pools(self) -> None:
        """Check health of all registered pools."""
        for pool_id, pool in self.pools.items():
            try:
                metrics = await self.health_checker.check_pool_health(pool)
                self._store_and_trim_metrics(pool_id, metrics)
                await self._trigger_recovery_if_needed(pool_id, pool, metrics)
            except Exception as e:
                self._log_health_check_error(pool_id, e)
    
    def _store_and_trim_metrics(self, pool_id: str, metrics: PoolMetrics) -> None:
        """Store metrics and trim history to recent entries."""
        self.metrics_history[pool_id].append(metrics)
        if len(self.metrics_history[pool_id]) > 100:
            self.metrics_history[pool_id] = self.metrics_history[pool_id][-50:]
    
    async def _trigger_recovery_if_needed(self, pool_id: str, pool: Any, metrics: PoolMetrics) -> None:
        """Trigger recovery if pool health is critical."""
        if metrics.health_status in [PoolHealth.UNHEALTHY, PoolHealth.CRITICAL]:
            await self._attempt_recovery(pool_id, pool, metrics)
    
    def _log_health_check_error(self, pool_id: str, error: Exception) -> None:
        """Log health check errors for a pool."""
        logger.error(f"Pool health check failed {pool_id}: {error}")
    
    async def _attempt_recovery(
        self,
        pool_id: str,
        pool: Any,
        metrics: PoolMetrics
    ) -> bool:
        """Attempt to recover unhealthy pool."""
        config = self.configs[pool_id]
        self._log_recovery_attempt(pool_id, metrics)
        return await self._execute_recovery_strategies(pool_id, pool, config, metrics)
    
    def _log_recovery_attempt(self, pool_id: str, metrics: PoolMetrics) -> None:
        """Log recovery attempt for unhealthy pool."""
        logger.warning(
            f"Attempting recovery for unhealthy pool: {pool_id} "
            f"(status: {metrics.health_status.value})"
        )
    
    async def _execute_recovery_strategies(
        self, pool_id: str, pool: Any, config: DatabaseConfig, metrics: PoolMetrics
    ) -> bool:
        """Execute recovery strategies until one succeeds."""
        for strategy in self.recovery_strategies:
            if await self._try_recovery_strategy(strategy, pool_id, pool, config, metrics):
                return True
        return self._log_all_strategies_failed(pool_id)
    
    async def _try_recovery_strategy(
        self, strategy: DatabaseRecoveryStrategy, pool_id: str, 
        pool: Any, config: DatabaseConfig, metrics: PoolMetrics
    ) -> bool:
        """Try a single recovery strategy."""
        try:
            if await strategy.can_recover(metrics):
                return await self._execute_strategy_with_logging(strategy, pool_id, pool, config)
        except Exception as e:
            self._log_strategy_failure(strategy, e)
        return False
    
    async def _execute_strategy_with_logging(
        self, strategy: DatabaseRecoveryStrategy, pool_id: str, pool: Any, config: DatabaseConfig
    ) -> bool:
        """Execute strategy and log success if applicable."""
        success = await strategy.execute_recovery(pool, config)
        if success:
            self._log_strategy_success(strategy, pool_id)
        return success
    
    def _log_strategy_success(self, strategy: DatabaseRecoveryStrategy, pool_id: str) -> None:
        """Log successful recovery strategy."""
        logger.info(f"Recovery successful using {type(strategy).__name__}: {pool_id}")
    
    def _log_strategy_failure(self, strategy: DatabaseRecoveryStrategy, error: Exception) -> None:
        """Log failed recovery strategy."""
        logger.error(f"Recovery strategy failed {type(strategy).__name__}: {error}")
    
    def _log_all_strategies_failed(self, pool_id: str) -> bool:
        """Log that all recovery strategies failed."""
        logger.error(f"All recovery strategies failed for pool: {pool_id}")
        return False
    
    async def force_recovery(self, pool_id: str) -> bool:
        """Force recovery attempt for specific pool."""
        if not self._validate_pool_exists(pool_id):
            return False
        pool = self.pools[pool_id]
        metrics = await self.health_checker.check_pool_health(pool)
        return await self._attempt_recovery(pool_id, pool, metrics)
    
    def _validate_pool_exists(self, pool_id: str) -> bool:
        """Validate that pool exists in registry."""
        return pool_id in self.pools
    
    def get_pool_status(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific pool."""
        latest_metrics = self._get_latest_metrics(pool_id)
        if not latest_metrics:
            return None
        return self._build_pool_status_dict(pool_id, latest_metrics)
    
    def _get_latest_metrics(self, pool_id: str) -> Optional[PoolMetrics]:
        """Get latest metrics for pool or None."""
        if pool_id not in self.metrics_history:
            return None
        history = self.metrics_history[pool_id]
        return history[-1] if history else None
    
    def _build_pool_status_dict(self, pool_id: str, metrics: Any) -> Dict[str, Any]:
        """Build pool status dictionary from metrics."""
        basic_info = self._build_basic_pool_info(pool_id, metrics)
        connection_info = self._build_connection_info(metrics)
        timing_info = self._build_timing_info(metrics)
        return {**basic_info, **connection_info, **timing_info}
    
    def _build_basic_pool_info(self, pool_id: str, metrics: Any) -> Dict[str, Any]:
        """Build basic pool information."""
        return {
            'pool_id': pool_id,
            'database_type': self.db_type.value,
            'health_status': metrics.health_status.value
        }
    
    def _build_connection_info(self, metrics: Any) -> Dict[str, Any]:
        """Build connection-related information."""
        return {
            'total_connections': metrics.total_connections,
            'active_connections': metrics.active_connections,
            'idle_connections': metrics.idle_connections,
            'failed_connections': metrics.failed_connections
        }
    
    def _build_timing_info(self, metrics: Any) -> Dict[str, Any]:
        """Build timing-related information."""
        return {
            'avg_response_time': metrics.avg_response_time,
            'last_health_check': metrics.last_health_check.isoformat() if metrics.last_health_check else None
        }
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all pools."""
        return {
            'database_type': self.db_type.value,
            'monitoring_active': self.monitoring_active,
            'pools': self._collect_all_pool_statuses()
        }
    
    def _collect_all_pool_statuses(self) -> Dict[str, Any]:
        """Collect status for all registered pools."""
        return {
            pool_id: self.get_pool_status(pool_id)
            for pool_id in self.pools.keys()
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


# Convenience functions
def register_postgresql_pool(
    pool_id: str,
    pool: Any,
    config: DatabaseConfig
) -> None:
    """Register PostgreSQL pool for monitoring."""
    manager = database_recovery_registry.get_manager(DatabaseType.POSTGRESQL)
    manager.register_pool(pool_id, pool, config)


def register_clickhouse_pool(
    pool_id: str,
    pool: Any,
    config: DatabaseConfig
) -> None:
    """Register ClickHouse pool for monitoring."""
    manager = database_recovery_registry.get_manager(DatabaseType.CLICKHOUSE)
    manager.register_pool(pool_id, pool, config)


async def setup_database_monitoring() -> None:
    """Setup database monitoring for all types."""
    await database_recovery_registry.start_all_monitoring()