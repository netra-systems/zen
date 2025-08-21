"""Database recovery strategies with ≤8 line functions.

Provides recovery strategies for database pools with aggressive function
decomposition. All functions ≤8 lines.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.database_types import DatabaseConfig, PoolHealth, PoolMetrics

logger = central_logger.get_logger(__name__)


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
        return metrics.health_status in [PoolHealth.DEGRADED, PoolHealth.UNHEALTHY]
    
    async def execute_recovery(self, pool: Any, config: DatabaseConfig) -> bool:
        """Refresh connections in pool."""
        try:
            logger.info(f"Refreshing connection pool: {getattr(pool, '_pool_id', 'unknown')}")
            await self._cleanup_idle_connections(pool)
            return await self._test_new_connections(pool, config)
        except Exception as e:
            logger.error(f"Pool refresh failed: {e}")
            return False
    
    async def _cleanup_idle_connections(self, pool: Any) -> None:
        """Clean up idle connections in the pool."""
        if hasattr(pool, 'expire'):
            await pool.expire()
        elif hasattr(pool, '_cleanup'):
            await pool._cleanup()
    
    async def _test_new_connections(self, pool: Any, config: DatabaseConfig) -> bool:
        """Test creation of new connections."""
        test_connections = []
        try:
            success = await self._acquire_test_connections(pool, config, test_connections)
            await self._release_test_connections(pool, test_connections)
            return success
        except Exception as e:
            logger.error(f"Failed to refresh connections: {e}")
            await self._force_release_connections(pool, test_connections)
            return False
    
    async def _acquire_test_connections(self, pool: Any, config: DatabaseConfig, test_connections: List) -> bool:
        """Acquire test connections to verify pool health."""
        connection_count = min(3, config.pool_size)
        for _ in range(connection_count):
            conn = await pool.acquire()
            test_connections.append(conn)
        logger.info("Connection pool refresh successful")
        return True
    
    async def _release_test_connections(self, pool: Any, test_connections: List) -> None:
        """Release all test connections back to pool."""
        for conn in test_connections:
            await pool.release(conn)
    
    async def _force_release_connections(self, pool: Any, test_connections: List) -> None:
        """Force release connections even on errors."""
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
        return metrics.health_status in [PoolHealth.UNHEALTHY, PoolHealth.CRITICAL]
    
    async def execute_recovery(self, pool: Any, config: DatabaseConfig) -> bool:
        """Recreate the connection pool."""
        try:
            logger.warning(f"Recreating connection pool: {getattr(pool, '_pool_id', 'unknown')}")
            await self._close_existing_pool(pool)
            await asyncio.sleep(1.0)
            return await self._recreate_pool(pool)
        except Exception as e:
            logger.error(f"Pool recreation failed: {e}")
            return False
    
    async def _close_existing_pool(self, pool: Any) -> None:
        """Close all connections in existing pool."""
        if hasattr(pool, 'close'):
            await pool.close()
        elif hasattr(pool, 'terminate'):
            await pool.terminate()
    
    async def _recreate_pool(self, pool: Any) -> bool:
        """Recreate the pool if possible."""
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
        if not self.backup_configs:
            return False
        try:
            backup_config = self._get_next_backup_config()
            return await self._perform_failover(backup_config)
        except Exception as e:
            logger.error(f"Database failover failed: {e}")
            return False
    
    def _get_next_backup_config(self) -> DatabaseConfig:
        """Get next backup configuration in rotation."""
        backup_config = self.backup_configs[self.current_backup_index]
        self.current_backup_index = (
            (self.current_backup_index + 1) % len(self.backup_configs)
        )
        return backup_config
    
    async def _perform_failover(self, backup_config: DatabaseConfig) -> bool:
        """Perform actual failover to backup database."""
        logger.critical(
            f"Failing over to backup database: "
            f"{backup_config.host}:{backup_config.port}"
        )
        try:
            from netra_backend.app.db.postgres import update_connection_config
            await update_connection_config(backup_config)
            logger.info(f"Successfully failed over to backup database")
            return True
        except Exception as failover_error:
            logger.error(f"Failed to update connection config: {failover_error}")
            return False
    
    def get_priority(self) -> int:
        """Failover has lowest priority."""
        return 4