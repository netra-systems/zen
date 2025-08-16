"""Database recovery strategies - main module with imports from focused modules.

Imports from split modules to maintain backward compatibility while enforcing
300-line limit and 8-line function limit. All functions ≤8 lines.
"""

# Import types
from .database_types import DatabaseType, PoolHealth, DatabaseConfig, PoolMetrics

# Import health monitoring
from .database_health_monitoring import DatabaseHealthChecker

# Import recovery strategies  
from .database_recovery_core import (
    DatabaseRecoveryStrategy, ConnectionPoolRefreshStrategy,
    ConnectionPoolRecreateStrategy, DatabaseFailoverStrategy
)

# Import connection management
from .database_connection_manager import (
    DatabaseConnectionManager, DatabaseRecoveryRegistry,
    database_recovery_registry, register_postgresql_pool,
    register_clickhouse_pool, setup_database_monitoring
)

# Export all for backward compatibility
__all__ = [
    'DatabaseType', 'PoolHealth', 'DatabaseConfig', 'PoolMetrics',
    'DatabaseHealthChecker', 'DatabaseRecoveryStrategy',
    'ConnectionPoolRefreshStrategy', 'ConnectionPoolRecreateStrategy',
    'DatabaseFailoverStrategy', 'DatabaseConnectionManager',
    'DatabaseRecoveryRegistry', 'database_recovery_registry',
    'register_postgresql_pool', 'register_clickhouse_pool',
    'setup_database_monitoring'
]


def get_database_manager(db_type: DatabaseType) -> DatabaseConnectionManager:
    """Get database connection manager for type."""
    return database_recovery_registry.get_manager(db_type)


def get_postgresql_manager() -> DatabaseConnectionManager:
    """Get PostgreSQL connection manager."""
    return get_database_manager(DatabaseType.POSTGRESQL)


def get_clickhouse_manager() -> DatabaseConnectionManager:
    """Get ClickHouse connection manager."""
    return get_database_manager(DatabaseType.CLICKHOUSE)


def get_redis_manager() -> DatabaseConnectionManager:
    """Get Redis connection manager."""
    return get_database_manager(DatabaseType.REDIS)