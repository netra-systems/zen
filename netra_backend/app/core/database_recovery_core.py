"""Database recovery strategies with  <= 8 line functions.

Provides recovery strategies for database pools with aggressive function
decomposition. All functions  <= 8 lines.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, List

from netra_backend.app.core.database_types import (
    DatabaseConfig,
    PoolHealth,
    PoolMetrics,
)
from netra_backend.app.logging_config import central_logger

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
            # Add validation for pool state before attempting recovery
            if not await self._validate_pool_state(pool):
                logger.warning("Pool is not in a valid state for recovery")
                return False
                
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
    
    async def _validate_pool_state(self, pool: Any) -> bool:
        """Validate pool state before attempting recovery."""
        # Check if pool has required methods
        if not hasattr(pool, 'acquire') or not hasattr(pool, 'release'):
            logger.warning("Pool missing required methods for recovery")
            return False
            
        # Check if pool is disposed or closed
        if hasattr(pool, '_disposed') and pool._disposed:
            logger.warning("Pool is disposed and cannot be recovered")
            return False
            
        return True
    
    async def _acquire_test_connections(self, pool: Any, config: DatabaseConfig, test_connections: List) -> bool:
        """Acquire test connections to verify pool health."""
        connection_count = min(3, config.pool_size)
        for i in range(connection_count):
            try:
                # Add timeout to prevent hanging
                conn = await asyncio.wait_for(pool.acquire(), timeout=5.0)
                test_connections.append(conn)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout acquiring test connection {i+1}/{connection_count}")
                return False
            except Exception as e:
                logger.error(f"Failed to acquire test connection {i+1}/{connection_count}: {e}")
                return False
        logger.info("Connection pool refresh successful")
        return True
    
    async def _release_test_connections(self, pool: Any, test_connections: List) -> None:
        """Release all test connections back to pool."""
        for i, conn in enumerate(test_connections):
            try:
                # Add timeout to prevent hanging during release
                await asyncio.wait_for(pool.release(conn), timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout releasing test connection {i+1}")
            except Exception as e:
                logger.warning(f"Failed to release test connection {i+1}: {e}")
    
    async def _force_release_connections(self, pool: Any, test_connections: List) -> None:
        """Force release connections even on errors."""
        for i, conn in enumerate(test_connections):
            try:
                # Use shorter timeout for force release
                await asyncio.wait_for(pool.release(conn), timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                # Silently ignore errors in force release
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


class DatabaseRecoveryCore:
    """Core database recovery manager for test compatibility."""
    
    def __init__(self, backup_configs=None):
        """Initialize the database recovery core."""
        self.strategies = [
            ConnectionPoolRefreshStrategy(),
            ConnectionPoolRecreateStrategy(),
            DatabaseFailoverStrategy(backup_configs or []),
        ]
    
    async def recover(self, error_context: dict = None) -> bool:
        """Execute recovery strategies in priority order."""
        logger.info("Starting database recovery process")
        
        for strategy in sorted(self.strategies, key=lambda s: s.get_priority()):
            try:
                if await strategy.recover():
                    logger.info(f"Recovery successful using {strategy.__class__.__name__}")
                    return True
            except Exception as e:
                logger.error(f"Recovery strategy {strategy.__class__.__name__} failed: {e}")
                continue
        
        logger.error("All recovery strategies failed")
        return False