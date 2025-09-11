"""
Database layer for Analytics Service - SSOT Implementation

Provides centralized database access through the ClickHouse Manager SSOT
and backward-compatible stub implementations for development.
"""

# Import SSOT ClickHouse Manager implementation
from .clickhouse_manager import (
    ClickHouseManager,
    ClickHouseConnectionError,
    ClickHouseQueryError,
    create_clickhouse_manager
)

# Import stub implementations from connection.py for backward compatibility
from .connection import (
    StubClickHouseManager,
    StubRedisManager,
    get_clickhouse_manager as get_clickhouse_manager_from_connection,
    get_redis_manager as get_redis_manager_from_connection,
)

# Keep Redis manager as stub (Redis not implemented in SSOT yet)
RedisManager = StubRedisManager


# Define Redis exception for compatibility
class RedisConnectionError(Exception):
    """Stub Redis connection error."""
    pass


# Provide stub functions for backward compatibility
def get_redis_manager():
    """Get Redis manager - delegates to connection.py"""
    return get_redis_manager_from_connection()


async def initialize_redis():
    """Stub initialize Redis function."""
    manager = get_redis_manager()
    await manager.initialize()


async def close_redis():
    """Stub close Redis function."""
    # No actual cleanup needed for stub implementation
    pass


__all__ = [
    # SSOT ClickHouse Manager (primary)
    'ClickHouseManager',
    'ClickHouseConnectionError', 
    'ClickHouseQueryError',
    'create_clickhouse_manager',
    # Redis (stub implementation)
    'RedisManager',
    'RedisConnectionError',
    'get_redis_manager',
    'initialize_redis',
    'close_redis',
    # Backward compatibility stubs
    'StubClickHouseManager',
    'StubRedisManager',
]