"""
Redis Manager Module - DEPRECATED Compatibility Layer

⚠️  DEPRECATED: Use netra_backend.app.redis_manager.redis_manager directly

This module provides a compatibility layer for integration tests that expect
a Redis manager implementation. This is a minimal implementation for test compatibility.

ISSUE #849 CRITICAL FIX: This compatibility layer caused WebSocket 1011 errors
by creating competing Redis managers that conflicted with the primary SSOT implementation.

MIGRATION PATH:
- Replace imports: from netra_backend.app.core.redis_manager import RedisManager
- With: from netra_backend.app.redis_manager import redis_manager

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Test Infrastructure Stability + WebSocket Reliability
- Value Impact: Eliminates WebSocket 1011 errors caused by Redis manager conflicts
- Strategic Impact: Maintains test coverage while preventing $500K+ ARR chat functionality failures
"""

from typing import Any, Dict, List, Optional, Union
import warnings

# ISSUE #849 FIX: Import SSOT Redis Manager instead of competing implementation
try:
    from netra_backend.app.redis_manager import (
        RedisManager as SSotRedisManager,
        redis_manager as ssot_redis_manager
    )
    SSOT_AVAILABLE = True
except ImportError:
    SSOT_AVAILABLE = False
    SSotRedisManager = None
    ssot_redis_manager = None

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Issue deprecation warning
warnings.warn(
    "netra_backend.app.core.redis_manager is deprecated. "
    "Use netra_backend.app.redis_manager.redis_manager directly to avoid WebSocket 1011 errors.",
    DeprecationWarning,
    stacklevel=2
)

# ISSUE #849 LEGACY CONFIG: Keep RedisConfig for backward compatibility
from dataclasses import dataclass

@dataclass  
class RedisConfig:
    """Redis configuration (DEPRECATED - use SSOT RedisManager)."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    timeout: float = 30.0


class RedisManager:
    """
    DEPRECATED: Redis manager compatibility wrapper.
    
    ISSUE #849 FIX: Redirects to SSOT Redis Manager to prevent WebSocket 1011 errors.
    This eliminates competing Redis managers that caused startup race conditions.
    """

    def __init__(self, config: RedisConfig = None):
        """Initialize Redis manager (redirects to SSOT)."""
        self.config = config or RedisConfig()
        
        # ISSUE #849 FIX: Use SSOT Redis Manager if available
        if SSOT_AVAILABLE:
            self._ssot_manager = ssot_redis_manager
            logger.info("Redis manager compatibility layer - redirecting to SSOT manager")
        else:
            # Fallback for isolated environments (auth service)
            self._ssot_manager = None
            self.connected = False
            self.data_store: Dict[str, str] = {}  # In-memory simulation
            self.expiry_store: Dict[str, float] = {}  # Key expiry times
            logger.info("Redis manager initialized (fallback compatibility mode)")

    async def connect(self):
        """Connect to Redis (redirected to SSOT or simulated)."""
        if self._ssot_manager:
            # ISSUE #849 FIX: Redirect to SSOT manager to prevent race conditions
            if hasattr(self._ssot_manager, 'initialize'):
                await self._ssot_manager.initialize()
            self.connected = self._ssot_manager.is_connected
            return
        
        # Fallback simulation for isolated environments
        await asyncio.sleep(0.1)
        self.connected = True
        logger.info(f"Connected to Redis at {self.config.host}:{self.config.port} (simulated)")

    async def disconnect(self):
        """Disconnect from Redis (redirected to SSOT or simulated)."""
        if self._ssot_manager:
            # ISSUE #849 FIX: Redirect to SSOT manager  
            await self._ssot_manager.shutdown()
            self.connected = False
            return
        
        # Fallback simulation
        self.connected = False
        self.data_store.clear()
        self.expiry_store.clear()
        logger.info("Disconnected from Redis (simulated)")

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a key-value pair (redirected to SSOT or simulated)."""
        if self._ssot_manager:
            # ISSUE #849 FIX: Redirect to SSOT manager to prevent conflicts
            return await self._ssot_manager.set(key, value, ex=ex)
        
        # Fallback simulation
        self._check_connection()
        self.data_store[key] = value

        if ex:
            self.expiry_store[key] = time.time() + ex

        logger.debug(f"Set key: {key} (expires in {ex}s)" if ex else f"Set key: {key}")
        return True

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key (redirected to SSOT or simulated)."""
        if self._ssot_manager:
            # ISSUE #849 FIX: Redirect to SSOT manager to prevent conflicts
            return await self._ssot_manager.get(key)
        
        # Fallback simulation
        self._check_connection()

        # Check if key has expired
        if key in self.expiry_store:
            if time.time() > self.expiry_store[key]:
                self.data_store.pop(key, None)
                self.expiry_store.pop(key, None)
                return None

        return self.data_store.get(key)

    async def delete(self, key: str) -> int:
        """Delete a key (redirected to SSOT or simulated)."""
        if self._ssot_manager:
            # ISSUE #849 FIX: Redirect to SSOT manager to prevent conflicts
            result = await self._ssot_manager.delete(key)
            return 1 if result else 0
        
        # Fallback simulation
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
        """Check if connected (redirected to SSOT or simulated)."""
        if self._ssot_manager:
            # ISSUE #849 FIX: Check SSOT manager connection
            if not self._ssot_manager.is_connected:
                raise ConnectionError("Not connected to Redis (SSOT)")
            return
        
        # Fallback simulation
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


# ISSUE #849 FIX: Global instance redirects to SSOT to prevent WebSocket 1011 errors
if SSOT_AVAILABLE:
    # Use SSOT Redis manager instance directly
    redis_manager = ssot_redis_manager
    logger.info("Using SSOT Redis manager for global compatibility instance")
else:
    # SSOT pattern: Import from canonical location
    from netra_backend.app.redis_manager import redis_manager as canonical_redis_manager
    redis_manager = canonical_redis_manager
    logger.warning("SSOT Redis manager not available - using canonical import")

__all__ = [
    "RedisManager",
    "RedisConfig", 
    "redis_manager"
]