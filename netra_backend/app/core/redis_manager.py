"""
Redis Manager Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a Redis manager implementation. This is a minimal implementation for test compatibility.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Provides minimal implementation for test collection compatibility
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union
import asyncio
import time
import json
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    timeout: float = 30.0


class RedisManager:
    """
    Simple Redis manager for test compatibility.

    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self, config: RedisConfig = None):
        """Initialize Redis manager."""
        self.config = config or RedisConfig()
        self.connected = False
        self.data_store: Dict[str, str] = {}  # In-memory simulation
        self.expiry_store: Dict[str, float] = {}  # Key expiry times

        logger.info("Redis manager initialized (test compatibility mode)")

    async def connect(self):
        """Connect to Redis (simulated)."""
        # Simulate connection
        await asyncio.sleep(0.1)
        self.connected = True
        logger.info(f"Connected to Redis at {self.config.host}:{self.config.port} (simulated)")

    async def disconnect(self):
        """Disconnect from Redis (simulated)."""
        self.connected = False
        self.data_store.clear()
        self.expiry_store.clear()
        logger.info("Disconnected from Redis (simulated)")

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a key-value pair."""
        self._check_connection()
        self.data_store[key] = value

        if ex:
            self.expiry_store[key] = time.time() + ex

        logger.debug(f"Set key: {key} (expires in {ex}s)" if ex else f"Set key: {key}")
        return True

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        self._check_connection()

        # Check if key has expired
        if key in self.expiry_store:
            if time.time() > self.expiry_store[key]:
                self.data_store.pop(key, None)
                self.expiry_store.pop(key, None)
                return None

        return self.data_store.get(key)

    async def delete(self, key: str) -> int:
        """Delete a key."""
        self._check_connection()

        if key in self.data_store:
            self.data_store.pop(key)
            self.expiry_store.pop(key, None)
            logger.debug(f"Deleted key: {key}")
            return 1
        return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        self._check_connection()

        # Check if key has expired
        if key in self.expiry_store:
            if time.time() > self.expiry_store[key]:
                self.data_store.pop(key, None)
                self.expiry_store.pop(key, None)
                return False

        return key in self.data_store

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry for a key."""
        self._check_connection()

        if key not in self.data_store:
            return False

        self.expiry_store[key] = time.time() + seconds
        return True

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        self._check_connection()

        # Simple pattern matching (just * for all)
        if pattern == "*":
            # Filter out expired keys
            current_time = time.time()
            valid_keys = []

            for key in list(self.data_store.keys()):
                if key in self.expiry_store and current_time > self.expiry_store[key]:
                    self.data_store.pop(key, None)
                    self.expiry_store.pop(key, None)
                else:
                    valid_keys.append(key)

            return valid_keys
        else:
            # Basic pattern matching
            import fnmatch
            all_keys = await self.keys("*")
            return [key for key in all_keys if fnmatch.fnmatch(key, pattern)]

    async def flushdb(self):
        """Clear all data."""
        self._check_connection()
        self.data_store.clear()
        self.expiry_store.clear()
        logger.info("Cleared all Redis data (simulated)")

    async def info(self) -> Dict[str, str]:
        """Get Redis info."""
        self._check_connection()
        return {
            "redis_version": "6.2.0-simulated",
            "connected_clients": "1",
            "used_memory": str(len(str(self.data_store))),
            "keyspace": f"db{self.config.db}:keys={len(self.data_store)}"
        }

    async def ping(self) -> bool:
        """Ping Redis."""
        return self.connected

    def _check_connection(self):
        """Check if connected."""
        if not self.connected:
            raise ConnectionError("Not connected to Redis")

    # JSON operations
    async def json_set(self, key: str, path: str, value: Any) -> bool:
        """Set JSON value."""
        json_str = json.dumps(value)
        return await self.set(key, json_str)

    async def json_get(self, key: str, path: str = ".") -> Any:
        """Get JSON value."""
        json_str = await self.get(key)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
        return None

    # Hash operations (simplified)
    async def hset(self, key: str, field: str, value: str) -> int:
        """Set hash field."""
        hash_key = f"{key}:{field}"
        await self.set(hash_key, value)
        return 1

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field."""
        hash_key = f"{key}:{field}"
        return await self.get(hash_key)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        pattern = f"{key}:*"
        keys = await self.keys(pattern)
        result = {}

        for full_key in keys:
            field = full_key[len(key) + 1:]  # Remove key prefix and ':'
            value = await self.get(full_key)
            if value:
                result[field] = value

        return result


# Global instance for compatibility
redis_manager = RedisManager()

__all__ = [
    "RedisManager",
    "RedisConfig",
    "redis_manager"
]