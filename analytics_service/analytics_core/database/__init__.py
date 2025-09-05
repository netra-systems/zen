"""
Database layer for Analytics Service - Updated for stub implementations

IMPORTANT: The original ClickHouseManager and RedisManager were deleted.
This module now provides stub implementations and imports from connection.py
to maintain backward compatibility.
"""

# Import stub implementations from connection.py
from .connection import (
    StubClickHouseManager,
    StubRedisManager,
    get_clickhouse_manager as get_clickhouse_manager_from_connection,
    get_redis_manager as get_redis_manager_from_connection,
)

# Create aliases for backward compatibility
ClickHouseManager = StubClickHouseManager
RedisManager = StubRedisManager


# Define stub exception classes to maintain compatibility
class ClickHouseConnectionError(Exception):
    """Stub ClickHouse connection error."""
    pass


class ClickHouseQueryError(Exception):
    """Stub ClickHouse query error."""
    pass


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
    'ClickHouseManager',
    'ClickHouseConnectionError', 
    'ClickHouseQueryError',
    'RedisManager',
    'RedisConnectionError',
    'get_redis_manager',
    'initialize_redis',
    'close_redis',
    'StubClickHouseManager',
    'StubRedisManager',
]