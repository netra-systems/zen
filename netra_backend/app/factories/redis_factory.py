"""
Redis Factory: Factory Pattern for User-Isolated Redis Instances

This module implements the Factory pattern for creating user-scoped Redis clients,
ensuring complete isolation of connections, operations, and resources per user.
Each factory creates isolated Redis instances with proper connection pooling
and user-scoped operations to prevent data leakage and enable concurrent multi-user access.

Follows the Factory pattern architecture from USER_CONTEXT_ARCHITECTURE.md:
- Factory creates isolated Redis instances per user/request
- Each user gets their own Redis client with namespaced operations
- Thread-safe concurrent operations with proper locking
- Automatic resource cleanup and connection management
- Complete user isolation at the Redis client level

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Redis-level user isolation for enterprise security
- Value Impact: Zero risk of cross-user data contamination, enterprise compliance
- Revenue Impact: Enables Enterprise tier with proper data governance ($50K+ ARR)
"""

import asyncio
import logging
import weakref
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class UserRedisClient:
    """
    User-scoped Redis client with isolated operations and namespacing.
    
    Each instance is completely isolated per user with its own:
    - Redis connection manager and operations
    - User-scoped key namespacing for all operations
    - Connection health monitoring
    - Resource cleanup tracking
    
    Provides the same interface as the global Redis service but with
    complete user isolation to prevent data leakage.
    """
    
    def __init__(self, user_id: str, request_id: str, thread_id: str):
        """
        Initialize user-scoped Redis client.
        
        Args:
            user_id: User identifier for isolation
            request_id: Request identifier for audit trails
            thread_id: Thread identifier for concurrent tracking
        """
        self.user_id = user_id
        self.request_id = request_id
        self.thread_id = thread_id
        self.created_at = datetime.now(timezone.utc)
        
        # User-scoped resources
        self._manager: Optional[RedisManager] = None
        self._connection_lock = asyncio.Lock()
        self._initialized = False
        
        # Metrics and monitoring
        self._operation_count = 0
        self._error_count = 0
        self._last_activity = self.created_at
        
        logger.debug(f"[UserRedisClient] Created for user {user_id[:8]}... (request: {request_id})")
    
    async def initialize(self) -> None:
        """
        Initialize user-scoped Redis connection manager.
        
        Creates an isolated Redis manager for this user.
        Each user gets their own manager to prevent interference.
        
        Raises:
            ConnectionError: If Redis connection fails
        """
        async with self._connection_lock:
            if self._initialized:
                return
            
            try:
                # Create isolated Redis manager for this user
                self._manager = RedisManager(test_mode=False)
                
                # Initialize the connection
                await self._manager.connect()
                
                # Test connection health
                if not await self._manager.ping():
                    raise ConnectionError("Redis ping failed during initialization")
                
                self._initialized = True
                self._last_activity = datetime.now(timezone.utc)
                
                logger.info(f"[UserRedisClient] Initialized for user {self.user_id[:8]}... with isolated manager")
                
            except Exception as e:
                logger.error(f"[UserRedisClient] Failed to initialize for user {self.user_id}: {e}")
                raise ConnectionError(f"Failed to initialize user Redis client: {e}") from e
    
    def _ensure_user_namespacing(self, key: str) -> str:
        """
        Ensure key is properly namespaced for this user.
        
        Args:
            key: Original Redis key
            
        Returns:
            Namespaced key with user isolation
        """
        # Keys are automatically namespaced by the manager when user_id is provided
        return key
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value by key with user isolation.
        
        Args:
            key: Redis key to retrieve
            
        Returns:
            Value if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            # Use manager with user_id for automatic namespacing
            result = await self._manager.get(key, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Get failed for user {self.user_id}: {e}")
            raise
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set key-value pair with user isolation.
        
        Args:
            key: Redis key to set
            value: Value to store
            ex: Optional expiration in seconds
            
        Returns:
            True if successful
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            # Use manager with user_id for automatic namespacing
            result = await self._manager.set(key, value, ex=ex, user_id=self.user_id)
            return result is not None
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Set failed for user {self.user_id}: {e}")
            raise
    
    async def delete(self, *keys: str) -> int:
        """
        Delete keys with user isolation.
        
        Args:
            keys: Redis keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            # Use manager with user_id for automatic namespacing
            result = await self._manager.delete(*keys, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Delete failed for user {self.user_id}: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists with user isolation.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.exists(key, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Exists failed for user {self.user_id}: {e}")
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set key expiration with user isolation.
        
        Args:
            key: Redis key to expire
            seconds: Expiration time in seconds
            
        Returns:
            True if successful
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.expire(key, seconds, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Expire failed for user {self.user_id}: {e}")
            raise
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern with user isolation.
        
        Args:
            pattern: Pattern to match keys against
            
        Returns:
            List of matching keys (without namespace prefix)
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.keys(pattern, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Keys failed for user {self.user_id}: {e}")
            raise
    
    async def ttl(self, key: str) -> int:
        """
        Get time to live for key with user isolation.
        
        Args:
            key: Redis key to check
            
        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.ttl(key, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] TTL failed for user {self.user_id}: {e}")
            raise
    
    # Hash operations
    async def hset(self, key: str, field_or_mapping: Union[str, Dict[str, Any]], value: Optional[str] = None) -> int:
        """Set hash field(s) with user isolation."""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.hset(key, field_or_mapping, value, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Hset failed for user {self.user_id}: {e}")
            raise
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field value with user isolation."""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.hget(key, field, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Hget failed for user {self.user_id}: {e}")
            raise
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields and values with user isolation."""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.hgetall(key, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Hgetall failed for user {self.user_id}: {e}")
            raise
    
    # List operations
    async def lpush(self, key: str, *values) -> int:
        """Push items to left side of list with user isolation."""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.lpush(key, *values, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Lpush failed for user {self.user_id}: {e}")
            raise
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop item from right side of list with user isolation."""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.rpop(key, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Rpop failed for user {self.user_id}: {e}")
            raise
    
    async def llen(self, key: str) -> int:
        """Get length of list with user isolation."""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._operation_count += 1
            self._last_activity = datetime.now(timezone.utc)
            
            result = await self._manager.llen(key, user_id=self.user_id)
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserRedisClient] Llen failed for user {self.user_id}: {e}")
            raise
    
    # JSON convenience methods
    async def set_json(self, key: str, value: Dict[str, Any], ex: Optional[int] = None) -> bool:
        """Set JSON value with user isolation."""
        import json
        json_str = json.dumps(value)
        return await self.set(key, json_str, ex=ex)
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value with user isolation."""
        import json
        json_str = await self.get(key)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None
        return None
    
    async def ping(self) -> bool:
        """Test Redis connection health."""
        if not self._initialized:
            try:
                await self.initialize()
            except:
                return False
        
        try:
            return await self._manager.ping()
        except:
            return False
    
    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics for monitoring.
        
        Returns:
            Dictionary with client metrics
        """
        age_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        last_activity_seconds = (datetime.now(timezone.utc) - self._last_activity).total_seconds()
        
        return {
            "user_id": f"{self.user_id[:8]}...",
            "request_id": self.request_id,
            "thread_id": self.thread_id,
            "initialized": self._initialized,
            "age_seconds": age_seconds,
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "last_activity_seconds_ago": last_activity_seconds,
            "error_rate": (self._error_count / max(self._operation_count, 1)) * 100
        }
    
    async def cleanup(self) -> None:
        """
        Clean up user-scoped resources and connections.
        
        Closes the isolated connection manager and clears resources.
        """
        async with self._connection_lock:
            if not self._initialized:
                return
            
            try:
                # Close isolated connection manager
                if self._manager:
                    await self._manager.disconnect()
                    self._manager = None
                
                self._initialized = False
                
                logger.info(f"[UserRedisClient] Cleaned up resources for user {self.user_id[:8]}...")
                
            except Exception as e:
                logger.warning(f"[UserRedisClient] Error during cleanup for user {self.user_id}: {e}")


class RedisFactory:
    """
    Factory for creating user-isolated Redis client instances.
    
    Implements the Factory pattern from USER_CONTEXT_ARCHITECTURE.md to create
    completely isolated Redis clients per user. Each client has its own:
    - Redis connection manager
    - User-scoped key namespacing for all operations
    - Resource management and cleanup
    - Thread-safe concurrent access
    
    Key Features:
    - Complete user isolation at the Redis client level
    - Automatic resource cleanup and connection management
    - Per-user connection pooling and operations
    - Thread-safe factory operations
    - Comprehensive monitoring and metrics
    - Graceful resource limits and TTL management
    
    Usage:
        factory = get_redis_factory()
        async with factory.get_user_client(user_context) as client:
            await client.set("key", "value")
            value = await client.get("key")
    """
    
    def __init__(self, 
                 max_clients_per_user: int = 5,
                 client_ttl_seconds: int = 1800,  # 30 minutes
                 cleanup_interval_seconds: int = 300):  # 5 minutes
        """
        Initialize Redis factory with resource limits.
        
        Args:
            max_clients_per_user: Maximum Redis clients per user
            client_ttl_seconds: Client time-to-live in seconds
            cleanup_interval_seconds: Cleanup task interval in seconds
        """
        self.factory_name = "RedisFactory"
        self.max_clients_per_user = max_clients_per_user
        self.client_ttl = client_ttl_seconds
        self.cleanup_interval = cleanup_interval_seconds
        
        # Active client tracking
        self._active_clients: Dict[str, UserRedisClient] = {}
        self._user_client_counts: Dict[str, int] = {}
        self._client_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Factory-wide locking for thread safety
        self._factory_lock = asyncio.Lock()
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._cleanup_started = False
        
        # Factory metrics
        self._created_count = 0
        self._cleanup_count = 0
        self.created_at = datetime.now(timezone.utc)
        
        logger.info(f"[RedisFactory] Initialized with max_clients_per_user={max_clients_per_user}, ttl={client_ttl_seconds}s")
    
    async def create_user_client(self, user_context: UserExecutionContext) -> UserRedisClient:
        """
        Create or reuse a user-scoped Redis client.
        
        Implements the Factory pattern by creating isolated clients per user.
        Enforces resource limits to prevent client proliferation.
        
        Args:
            user_context: User execution context with validated fields
            
        Returns:
            User-scoped Redis client with isolated operations
            
        Raises:
            ValueError: If user_context is invalid or user exceeds client limit
            ConnectionError: If Redis connection fails
        """
        # Validate user context
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError(f"Expected UserExecutionContext, got {type(user_context)}")
        
        user_id = user_context.user_id
        
        async with self._factory_lock:
            # Start cleanup task if not already started
            self._start_cleanup_task()
            
            # Check per-user client limits
            current_count = self._user_client_counts.get(user_id, 0)
            if current_count >= self.max_clients_per_user:
                logger.warning(f"[RedisFactory] User {user_id} at client limit ({current_count}/{self.max_clients_per_user})")
                
                # Clean up expired clients for this user
                await self._cleanup_user_clients(user_id)
                
                # Check again after cleanup
                current_count = self._user_client_counts.get(user_id, 0)
                if current_count >= self.max_clients_per_user:
                    raise ValueError(f"User {user_id} exceeds maximum Redis clients ({self.max_clients_per_user})")
            
            # Create new client
            client_id = f"{user_id}_{user_context.request_id}_{uuid4().hex[:8]}"
            
            try:
                # Create user-isolated Redis client
                client = UserRedisClient(
                    user_context.user_id,
                    user_context.request_id,
                    user_context.thread_id
                )
                
                # Initialize the client
                await client.initialize()
                
                # Store client and metadata
                self._active_clients[client_id] = client
                self._client_metadata[client_id] = {
                    "user_id": user_id,
                    "request_id": user_context.request_id,
                    "thread_id": user_context.thread_id,
                    "run_id": user_context.run_id,
                    "created_at": datetime.now(timezone.utc),
                    "last_accessed": datetime.now(timezone.utc),
                    "access_count": 0
                }
                
                # Update user client count
                self._user_client_counts[user_id] = current_count + 1
                self._created_count += 1
                
                logger.debug(f"[RedisFactory] Created client {client_id} for user {user_id[:8]}...")
                return client
                
            except Exception as e:
                logger.error(f"[RedisFactory] Failed to create client for user {user_id}: {e}")
                raise
    
    @asynccontextmanager
    async def get_user_client(self, user_context: UserExecutionContext):
        """
        Context manager for user-scoped Redis operations.
        
        Usage:
            factory = get_redis_factory()
            async with factory.get_user_client(user_context) as client:
                await client.set("key", "value")
                value = await client.get("key")
        
        Args:
            user_context: User execution context
            
        Yields:
            UserRedisClient: User-scoped Redis client
        """
        client = await self.create_user_client(user_context)
        try:
            yield client
        finally:
            # Client cleanup is handled by factory TTL and cleanup tasks
            # Manual cleanup could be added here if needed
            pass
    
    async def cleanup_user_clients(self, user_id: str) -> int:
        """
        Clean up all clients for a specific user.
        
        Args:
            user_id: User ID to clean up clients for
            
        Returns:
            Number of clients cleaned up
        """
        return await self._cleanup_user_clients(user_id)
    
    async def _cleanup_user_clients(self, user_id: str) -> int:
        """Internal method to clean up user clients."""
        clients_to_remove = []
        
        for client_id, metadata in self._client_metadata.items():
            if metadata["user_id"] == user_id:
                clients_to_remove.append(client_id)
        
        cleanup_count = 0
        for client_id in clients_to_remove:
            try:
                client = self._active_clients.get(client_id)
                if client:
                    await client.cleanup()
                    cleanup_count += 1
                
                # Remove from tracking
                self._active_clients.pop(client_id, None)
                self._client_metadata.pop(client_id, None)
                
            except Exception as e:
                logger.warning(f"[RedisFactory] Error cleaning up client {client_id}: {e}")
        
        # Update user client count
        if user_id in self._user_client_counts:
            self._user_client_counts[user_id] = max(0, self._user_client_counts[user_id] - cleanup_count)
            if self._user_client_counts[user_id] == 0:
                del self._user_client_counts[user_id]
        
        if cleanup_count > 0:
            self._cleanup_count += cleanup_count
            logger.info(f"[RedisFactory] Cleaned up {cleanup_count} clients for user {user_id}")
        
        return cleanup_count
    
    def _start_cleanup_task(self):
        """Start background cleanup task if event loop is available."""
        if self._cleanup_started:
            return
            
        try:
            # Only start if we're in an async context
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                self._cleanup_started = True
                logger.debug("[RedisFactory] Started cleanup task")
        except RuntimeError:
            # No event loop running, cleanup task will be started later
            logger.debug("[RedisFactory] No event loop available, cleanup task will start on first use")
            pass
    
    async def _cleanup_loop(self):
        """Background cleanup loop for expired clients."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.cleanup_interval)
                break  # Shutdown requested
            except asyncio.TimeoutError:
                # Normal cleanup cycle
                await self._cleanup_expired_clients()
    
    async def _cleanup_expired_clients(self):
        """Clean up expired clients based on TTL."""
        now = datetime.now(timezone.utc)
        expired_clients = []
        
        for client_id, metadata in self._client_metadata.items():
            age = now - metadata["created_at"]
            if age.total_seconds() > self.client_ttl:
                expired_clients.append(client_id)
        
        if expired_clients:
            logger.debug(f"[RedisFactory] Cleaning up {len(expired_clients)} expired clients")
            
            for client_id in expired_clients:
                try:
                    metadata = self._client_metadata.get(client_id, {})
                    user_id = metadata.get("user_id")
                    
                    client = self._active_clients.get(client_id)
                    if client:
                        await client.cleanup()
                    
                    # Remove from tracking
                    self._active_clients.pop(client_id, None)
                    self._client_metadata.pop(client_id, None)
                    
                    # Update user count
                    if user_id and user_id in self._user_client_counts:
                        self._user_client_counts[user_id] = max(0, self._user_client_counts[user_id] - 1)
                        if self._user_client_counts[user_id] == 0:
                            del self._user_client_counts[user_id]
                    
                    self._cleanup_count += 1
                
                except Exception as e:
                    logger.warning(f"[RedisFactory] Error during cleanup of client {client_id}: {e}")
    
    async def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics for monitoring.
        
        Returns:
            Dictionary with factory metrics and health information
        """
        total_clients = len(self._active_clients)
        users_with_clients = len(self._user_client_counts)
        factory_age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        # Calculate age distribution
        now = datetime.now(timezone.utc)
        age_buckets = {"0-5min": 0, "5-30min": 0, "30min+": 0}
        
        for metadata in self._client_metadata.values():
            age = now - metadata["created_at"]
            if age < timedelta(minutes=5):
                age_buckets["0-5min"] += 1
            elif age < timedelta(minutes=30):
                age_buckets["5-30min"] += 1
            else:
                age_buckets["30min+"] += 1
        
        # Get client health stats
        healthy_clients = 0
        client_stats = []
        
        for client_id, client in self._active_clients.items():
            stats = client.get_client_stats()
            client_stats.append(stats)
            if await client.ping():
                healthy_clients += 1
        
        return {
            "factory_name": self.factory_name,
            "factory_age_seconds": factory_age,
            "total_clients": total_clients,
            "healthy_clients": healthy_clients,
            "users_with_clients": users_with_clients,
            "max_clients_per_user": self.max_clients_per_user,
            "client_ttl_seconds": self.client_ttl,
            "created_count": self._created_count,
            "cleanup_count": self._cleanup_count,
            "age_distribution": age_buckets,
            "user_client_counts": dict(self._user_client_counts),
            "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done(),
            "client_details": client_stats
        }
    
    async def shutdown(self):
        """
        Shutdown the factory and clean up all resources.
        
        This method should be called when the application is shutting down
        to ensure proper cleanup of all clients and background tasks.
        """
        logger.info("[RedisFactory] Shutting down factory...")
        
        # Signal cleanup task to stop
        self._shutdown_event.set()
        
        # Wait for cleanup task to finish
        if self._cleanup_task and not self._cleanup_task.done():
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("[RedisFactory] Cleanup task did not finish in time, cancelling")
                self._cleanup_task.cancel()
        
        # Clean up all remaining clients
        client_count = len(self._active_clients)
        if client_count > 0:
            logger.info(f"[RedisFactory] Cleaning up {client_count} remaining clients")
            
            cleanup_tasks = []
            for client_id, client in self._active_clients.items():
                cleanup_tasks.append(client.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear all tracking data
        self._active_clients.clear()
        self._client_metadata.clear()
        self._user_client_counts.clear()
        
        logger.info("[RedisFactory] Factory shutdown complete")


# Global factory instance following the Factory pattern
_redis_factory: Optional[RedisFactory] = None


def get_redis_factory() -> RedisFactory:
    """
    Get the global Redis factory instance.
    
    Returns:
        Global Redis factory instance
    """
    global _redis_factory
    if _redis_factory is None:
        _redis_factory = RedisFactory()
    return _redis_factory


# Convenience functions for common usage patterns
@asynccontextmanager
async def get_user_redis_client(user_context: UserExecutionContext):
    """
    Context manager for user-scoped Redis client operations.
    
    Usage:
        async with get_user_redis_client(user_context) as client:
            await client.set("key", "value")
            value = await client.get("key")
    
    Args:
        user_context: User execution context
        
    Yields:
        UserRedisClient: User-scoped Redis client
    """
    factory = get_redis_factory()
    async with factory.get_user_client(user_context) as client:
        yield client


async def cleanup_redis_factory():
    """Clean up the global Redis factory and all its resources."""
    global _redis_factory
    
    if _redis_factory:
        await _redis_factory.shutdown()
        _redis_factory = None
    
    logger.info("[RedisFactory] Global factory cleaned up")


__all__ = [
    "RedisFactory",
    "UserRedisClient",
    "get_redis_factory",
    "get_user_redis_client",
    "cleanup_redis_factory"
]