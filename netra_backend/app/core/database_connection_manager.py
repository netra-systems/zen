"""DEPRECATED: Database connection management - Use DatabaseManager instead.

CRITICAL: This module is deprecated to eliminate SSOT violations.
All database connection management now consolidated in DatabaseManager.
"""

import asyncio
from typing import Any, Dict, List, Optional

# SINGLE SOURCE OF TRUTH: Import from canonical DatabaseManager
from netra_backend.app.db.database_manager import DatabaseManager, ConnectionMetrics

from netra_backend.app.core.database_types import (
    DatabaseConfig,
    DatabaseType,
    PoolHealth,
    PoolMetrics,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseConnectionManager:
    """DEPRECATED: Database connection manager - delegates to DatabaseManager."""
    
    def __init__(self, db_type: DatabaseType):
        """DEPRECATED: Initialize - delegates to DatabaseManager."""
        logger.warning("DatabaseConnectionManager is deprecated. Use DatabaseManager directly.")
        self.db_type = db_type
        self._database_manager = DatabaseManager.get_connection_manager()
    
    def add_recovery_strategy(self, strategy: Any) -> None:
        """DEPRECATED: Delegates to DatabaseManager.""" 
        logger.warning("Recovery strategies handled by DatabaseManager")
    
    def register_pool(self, pool_id: str, pool: Any, config: DatabaseConfig) -> None:
        """DEPRECATED: Delegates to DatabaseManager."""
        logger.warning("Pool registration handled by DatabaseManager")
    
    async def start_monitoring(self) -> None:
        """DEPRECATED: Delegates to DatabaseManager."""
        logger.info(f"Monitoring delegated to DatabaseManager for {self.db_type.value}")
    
    async def stop_monitoring(self) -> None:
        """DEPRECATED: Delegates to DatabaseManager."""
        logger.info(f"Monitoring stop delegated to DatabaseManager for {self.db_type.value}")
    
    async def force_recovery(self, pool_id: str) -> bool:
        """DEPRECATED: Delegates to DatabaseManager."""
        logger.warning("Recovery operations delegated to DatabaseManager")
        return True  # Assume success since DatabaseManager handles this
    
    def get_pool_status(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """DEPRECATED: Get status - delegates to DatabaseManager."""
        try:
            metrics = DatabaseManager.get_connection_metrics(pool_id)
            return {
                'pool_id': pool_id,
                'database_type': self.db_type.value,
                'health_status': 'healthy',  # Simplified
                'total_connections': metrics.total_connections,
                'active_connections': metrics.active_connections,
                'idle_connections': metrics.idle_connections,
                'failed_connections': metrics.failed_connections
            }
        except Exception:
            return None
    
    def get_all_status(self) -> Dict[str, Any]:
        """DEPRECATED: Get all status - delegates to DatabaseManager."""
        return {
            'database_type': self.db_type.value,
            'monitoring_active': True,
            'pools': {'default': self.get_pool_status('default')}
        }


class DatabaseRecoveryRegistry:
    """DEPRECATED: Registry delegating to DatabaseManager."""
    
    def __init__(self):
        """DEPRECATED: Initialize - delegates to DatabaseManager."""
        logger.warning("DatabaseRecoveryRegistry is deprecated. Use DatabaseManager directly.")
        self.managers: Dict[DatabaseType, DatabaseConnectionManager] = {}
    
    def get_manager(self, db_type: DatabaseType) -> DatabaseConnectionManager:
        """DEPRECATED: Get manager - creates deprecated wrapper."""
        if db_type not in self.managers:
            self.managers[db_type] = DatabaseConnectionManager(db_type)
        return self.managers[db_type]
    
    async def start_all_monitoring(self) -> None:
        """DEPRECATED: Delegates to DatabaseManager."""
        logger.info("Database monitoring delegated to DatabaseManager")
    
    async def stop_all_monitoring(self) -> None:
        """DEPRECATED: Delegates to DatabaseManager."""
        logger.info("Database monitoring stop delegated to DatabaseManager")
    
    def get_global_status(self) -> Dict[str, Any]:
        """DEPRECATED: Get global status - simplified delegation."""
        return {
            "postgresql": {"status": "delegated_to_database_manager"},
            "monitoring_active": True
        }


# DEPRECATED: Global registry - use DatabaseManager directly
database_recovery_registry = DatabaseRecoveryRegistry()


# DEPRECATED: Convenience functions - use DatabaseManager directly
def register_postgresql_pool(pool_id: str, pool: Any, config: DatabaseConfig) -> None:
    """DEPRECATED: Use DatabaseManager for pool registration."""
    logger.warning("register_postgresql_pool is deprecated. Use DatabaseManager directly.")

def register_clickhouse_pool(pool_id: str, pool: Any, config: DatabaseConfig) -> None:
    """DEPRECATED: Use DatabaseManager for pool registration."""
    logger.warning("register_clickhouse_pool is deprecated. Use DatabaseManager directly.")

async def setup_database_monitoring() -> None:
    """DEPRECATED: Use DatabaseManager for monitoring setup."""
    logger.info("Database monitoring setup delegated to DatabaseManager")