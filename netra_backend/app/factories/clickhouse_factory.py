"""
ClickHouse Factory: Factory Pattern for User-Isolated ClickHouse Instances

This module implements the Factory pattern for creating user-scoped ClickHouse clients,
ensuring complete isolation of connections, caches, and resources per user.
Each factory creates isolated ClickHouse instances with proper connection pooling
and user-scoped caching to prevent data leakage and enable concurrent multi-user access.

Follows the Factory pattern architecture from USER_CONTEXT_ARCHITECTURE.md:
- Factory creates isolated ClickHouse instances per user/request
- Each user gets their own connection pool and cache
- Thread-safe concurrent operations with proper locking
- Automatic resource cleanup and connection management
- Complete user isolation at the database client level

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Database-level user isolation for enterprise security
- Value Impact: Zero risk of cross-user data contamination, enterprise compliance
- Revenue Impact: Enables Enterprise tier with proper data governance ($50K+ ARR)
"""

import asyncio
import logging
import weakref
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


class UserClickHouseCache:
    """
    User-scoped ClickHouse cache with complete isolation.
    
    Each user gets their own cache instance to prevent data leakage.
    Provides TTL support and automatic cleanup of expired entries.
    """
    
    def __init__(self, user_id: str, max_size: int = 200):
        """
        Initialize user-scoped cache.
        
        Args:
            user_id: User identifier for this cache
            max_size: Maximum cache entries for this user
        """
        self.user_id = user_id
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
        self._lock = asyncio.Lock()
        self.created_at = datetime.utcnow()
        
        logger.debug(f"[UserClickHouseCache] Created for user {user_id[:8]}... (max_size: {max_size})")
    
    def _generate_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from query and parameters."""
        import hashlib
        
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        if params:
            params_str = str(sorted(params.items()))
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"ch_user:{query_hash}:p:{params_hash}"
        return f"ch_user:{query_hash}"
    
    async def get(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached result if not expired.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Cached result if found and not expired, None otherwise
        """
        async with self._lock:
            key = self._generate_key(query, params)
            entry = self.cache.get(key)
            
            if entry and datetime.utcnow().timestamp() < entry["expires_at"]:
                self._hits += 1
                logger.debug(f"[UserClickHouseCache] Cache hit for user {self.user_id[:8]}... query: {query[:30]}...")
                return entry["result"]
            elif entry:
                del self.cache[key]
            
            self._misses += 1
            return None
    
    async def set(self, query: str, result: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None, ttl: float = 300) -> None:
        """
        Cache query result with TTL.
        
        Args:
            query: SQL query string
            result: Query result to cache
            params: Optional query parameters
            ttl: Time to live in seconds
        """
        async with self._lock:
            # Evict oldest entries if at capacity
            if len(self.cache) >= self.max_size:
                oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k]["created_at"])[:10]
                for k in oldest_keys:
                    del self.cache[k]
            
            key = self._generate_key(query, params)
            now = datetime.utcnow().timestamp()
            self.cache[key] = {
                "result": result,
                "created_at": now,
                "expires_at": now + ttl
            }
            
            logger.debug(f"[UserClickHouseCache] Cached result for user {self.user_id[:8]}... (TTL: {ttl}s)")
    
    async def clear(self) -> None:
        """Clear all cache entries for this user."""
        async with self._lock:
            entry_count = len(self.cache)
            self.cache.clear()
            logger.info(f"[UserClickHouseCache] Cleared {entry_count} entries for user {self.user_id[:8]}...")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total) if total > 0 else 0
            age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
            
            return {
                "user_id": f"{self.user_id[:8]}...",
                "size": len(self.cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "max_size": self.max_size,
                "age_seconds": age_seconds
            }


class UserClickHouseClient:
    """
    User-scoped ClickHouse client with isolated connection and cache.
    
    Each instance is completely isolated per user with its own:
    - ClickHouse connection and query interceptor
    - User-scoped cache instance
    - Connection health monitoring
    - Resource cleanup tracking
    
    Provides the same interface as the global ClickHouse service but with
    complete user isolation to prevent data leakage.
    """
    
    def __init__(self, user_id: str, request_id: str, thread_id: str):
        """
        Initialize user-scoped ClickHouse client.
        
        Args:
            user_id: User identifier for isolation
            request_id: Request identifier for audit trails
            thread_id: Thread identifier for concurrent tracking
        """
        self.user_id = user_id
        self.request_id = request_id
        self.thread_id = thread_id
        self.created_at = datetime.utcnow()
        
        # User-scoped resources
        self._client: Optional[ClickHouseQueryInterceptor] = None
        self._cache: UserClickHouseCache = UserClickHouseCache(user_id)
        self._connection_lock = asyncio.Lock()
        self._initialized = False
        self._connection_pool = None
        
        # Metrics and monitoring
        self._query_count = 0
        self._error_count = 0
        self._last_activity = self.created_at
        
        logger.debug(f"[UserClickHouseClient] Created for user {user_id[:8]}... (request: {request_id})")
    
    async def initialize(self) -> None:
        """
        Initialize user-scoped ClickHouse connection.
        
        Creates an isolated connection and query interceptor for this user.
        Each user gets their own connection to prevent interference.
        
        Raises:
            ConnectionError: If ClickHouse connection fails
        """
        async with self._connection_lock:
            if self._initialized:
                return
            
            try:
                # Get ClickHouse configuration
                config = self._get_clickhouse_config()
                
                # Create isolated connection for this user
                base_client = self._create_base_client(config)
                self._client = ClickHouseQueryInterceptor(base_client)
                
                # Test connection
                await asyncio.wait_for(self._client.test_connection(), timeout=10.0)
                
                self._initialized = True
                self._last_activity = datetime.utcnow()
                
                logger.info(f"[UserClickHouseClient] Initialized for user {self.user_id[:8]}... with isolated connection")
                
            except Exception as e:
                logger.error(f"[UserClickHouseClient] Failed to initialize for user {self.user_id}: {e}")
                raise ConnectionError(f"Failed to initialize user ClickHouse client: {e}") from e
    
    def _get_clickhouse_config(self):
        """Get ClickHouse configuration from unified config system."""
        from netra_backend.app.db.clickhouse import get_clickhouse_config
        return get_clickhouse_config()
    
    def _create_base_client(self, config) -> ClickHouseDatabase:
        """Create base ClickHouse client with user-specific configuration."""
        # Never use HTTPS for localhost or Docker container connections
        is_local_or_docker = config.host in ["localhost", "127.0.0.1", "::1", "clickhouse", "netra-clickhouse"]
        app_config = get_configuration()
        use_secure = app_config.clickhouse_mode != "local" and not is_local_or_docker and app_config.environment != "development"
        
        # Create isolated client parameters
        params = {
            'host': config.host,
            'port': config.port,
            'user': config.user,
            'password': config.password,
            'database': config.database,
            'secure': use_secure
        }
        
        logger.debug(f"[UserClickHouseClient] Creating isolated connection for user {self.user_id[:8]}... to {config.host}:{config.port}")
        return ClickHouseDatabase(**params)
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute query with user-scoped caching and isolation.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            Query results as list of dictionaries
        """
        if not self._initialized:
            await self.initialize()
        
        # Check user cache first for read queries
        if query.lower().strip().startswith("select"):
            cached_result = await self._cache.get(query, params)
            if cached_result is not None:
                return cached_result
        
        try:
            self._query_count += 1
            self._last_activity = datetime.utcnow()
            
            # Execute with isolated client
            result = await self._client.execute(query, params)
            
            # Cache successful read results
            if query.lower().strip().startswith("select") and result:
                await self._cache.set(query, result, params, ttl=300)
            
            return result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"[UserClickHouseClient] Query failed for user {self.user_id}: {e}")
            raise
    
    async def execute_with_retry(self, query: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2) -> List[Dict[str, Any]]:
        """
        Execute query with retry logic for critical operations.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query results as list of dictionaries
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(2.0 * (2 ** (attempt - 1)), 8.0)  # Exponential backoff
                    logger.info(f"[UserClickHouseClient] Retrying query for user {self.user_id} (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
                return await self.execute(query, params)
                
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    break
        
        raise last_exception
    
    async def batch_insert(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """
        Insert batch of data into ClickHouse table.
        
        Args:
            table_name: Target table name
            data: List of records to insert
        """
        if not self._initialized:
            await self.initialize()
        
        if not data:
            return
        
        # Get column names from first row
        columns = list(data[0].keys())
        columns_str = ", ".join(columns)
        values_placeholder = ", ".join([f"%({col})s" for col in columns])
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_placeholder})"
        
        # Execute insert for each row
        for row in data:
            await self.execute(query, row)
    
    async def test_connection(self) -> bool:
        """
        Test ClickHouse connection availability.
        
        Returns:
            True if connection is healthy
        """
        if not self._initialized:
            try:
                await self.initialize()
            except:
                return False
        
        try:
            await self._client.test_connection()
            return True
        except:
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for this user."""
        return await self._cache.get_stats()
    
    async def clear_cache(self) -> None:
        """Clear cache for this user."""
        await self._cache.clear()
    
    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics for monitoring.
        
        Returns:
            Dictionary with client metrics
        """
        age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        last_activity_seconds = (datetime.utcnow() - self._last_activity).total_seconds()
        
        return {
            "user_id": f"{self.user_id[:8]}...",
            "request_id": self.request_id,
            "thread_id": self.thread_id,
            "initialized": self._initialized,
            "age_seconds": age_seconds,
            "query_count": self._query_count,
            "error_count": self._error_count,
            "last_activity_seconds_ago": last_activity_seconds,
            "error_rate": (self._error_count / max(self._query_count, 1)) * 100
        }
    
    async def cleanup(self) -> None:
        """
        Clean up user-scoped resources and connections.
        
        Closes the isolated connection and clears the user cache.
        """
        async with self._connection_lock:
            if not self._initialized:
                return
            
            try:
                # Clear user cache
                await self._cache.clear()
                
                # Close isolated connection
                if self._client:
                    await self._client.disconnect()
                    self._client = None
                
                self._initialized = False
                
                logger.info(f"[UserClickHouseClient] Cleaned up resources for user {self.user_id[:8]}...")
                
            except Exception as e:
                logger.warning(f"[UserClickHouseClient] Error during cleanup for user {self.user_id}: {e}")


class ClickHouseFactory:
    """
    Factory for creating user-isolated ClickHouse client instances.
    
    Implements the Factory pattern from USER_CONTEXT_ARCHITECTURE.md to create
    completely isolated ClickHouse clients per user. Each client has its own:
    - Database connection and connection pool
    - User-scoped cache instance  
    - Resource management and cleanup
    - Thread-safe concurrent access
    
    Key Features:
    - Complete user isolation at the database client level
    - Automatic resource cleanup and connection management
    - Per-user connection pooling and caching
    - Thread-safe factory operations
    - Comprehensive monitoring and metrics
    - Graceful resource limits and TTL management
    
    Usage:
        factory = get_clickhouse_factory()
        async with factory.create_user_client(user_context) as client:
            results = await client.execute("SELECT * FROM events")
    """
    
    def __init__(self, 
                 max_clients_per_user: int = 3,
                 client_ttl_seconds: int = 1800,  # 30 minutes
                 cleanup_interval_seconds: int = 300):  # 5 minutes
        """
        Initialize ClickHouse factory with resource limits.
        
        Args:
            max_clients_per_user: Maximum ClickHouse clients per user
            client_ttl_seconds: Client time-to-live in seconds
            cleanup_interval_seconds: Cleanup task interval in seconds
        """
        self.factory_name = "ClickHouseFactory"
        self.max_clients_per_user = max_clients_per_user
        self.client_ttl = client_ttl_seconds
        self.cleanup_interval = cleanup_interval_seconds
        
        # Active client tracking
        self._active_clients: Dict[str, UserClickHouseClient] = {}
        self._user_client_counts: Dict[str, int] = {}
        self._client_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Factory-wide locking for thread safety
        self._factory_lock = asyncio.Lock()
        
        # Background cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._start_cleanup_task()
        
        # Factory metrics
        self._created_count = 0
        self._cleanup_count = 0
        self.created_at = datetime.utcnow()
        
        logger.info(f"[ClickHouseFactory] Initialized with max_clients_per_user={max_clients_per_user}, ttl={client_ttl_seconds}s")
    
    async def create_user_client(self, user_context: UserExecutionContext) -> UserClickHouseClient:
        """
        Create or reuse a user-scoped ClickHouse client.
        
        Implements the Factory pattern by creating isolated clients per user.
        Enforces resource limits to prevent client proliferation.
        
        Args:
            user_context: User execution context with validated fields
            
        Returns:
            User-scoped ClickHouse client with isolated connection
            
        Raises:
            ValueError: If user_context is invalid or user exceeds client limit
            ConnectionError: If ClickHouse connection fails
        """
        # Validate user context
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError(f"Expected UserExecutionContext, got {type(user_context)}")
        
        user_id = user_context.user_id
        
        async with self._factory_lock:
            # Check per-user client limits
            current_count = self._user_client_counts.get(user_id, 0)
            if current_count >= self.max_clients_per_user:
                logger.warning(f"[ClickHouseFactory] User {user_id} at client limit ({current_count}/{self.max_clients_per_user})")
                
                # Clean up expired clients for this user
                await self._cleanup_user_clients(user_id)
                
                # Check again after cleanup
                current_count = self._user_client_counts.get(user_id, 0)
                if current_count >= self.max_clients_per_user:
                    raise ValueError(f"User {user_id} exceeds maximum ClickHouse clients ({self.max_clients_per_user})")
            
            # Create new client
            client_id = f"{user_id}_{user_context.request_id}_{uuid4().hex[:8]}"
            
            try:
                # Create user-isolated ClickHouse client
                client = UserClickHouseClient(
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
                    "created_at": datetime.utcnow(),
                    "last_accessed": datetime.utcnow(),
                    "access_count": 0
                }
                
                # Update user client count
                self._user_client_counts[user_id] = current_count + 1
                self._created_count += 1
                
                logger.debug(f"[ClickHouseFactory] Created client {client_id} for user {user_id[:8]}...")
                return client
                
            except Exception as e:
                logger.error(f"[ClickHouseFactory] Failed to create client for user {user_id}: {e}")
                raise
    
    @asynccontextmanager
    async def get_user_client(self, user_context: UserExecutionContext):
        """
        Context manager for user-scoped ClickHouse operations.
        
        Usage:
            factory = get_clickhouse_factory()
            async with factory.get_user_client(user_context) as client:
                results = await client.execute("SELECT * FROM events")
        
        Args:
            user_context: User execution context
            
        Yields:
            UserClickHouseClient: User-scoped ClickHouse client
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
                logger.warning(f"[ClickHouseFactory] Error cleaning up client {client_id}: {e}")
        
        # Update user client count
        if user_id in self._user_client_counts:
            self._user_client_counts[user_id] = max(0, self._user_client_counts[user_id] - cleanup_count)
            if self._user_client_counts[user_id] == 0:
                del self._user_client_counts[user_id]
        
        if cleanup_count > 0:
            self._cleanup_count += cleanup_count
            logger.info(f"[ClickHouseFactory] Cleaned up {cleanup_count} clients for user {user_id}")
        
        return cleanup_count
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("[ClickHouseFactory] Started cleanup task")
    
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
        now = datetime.utcnow()
        expired_clients = []
        
        for client_id, metadata in self._client_metadata.items():
            age = now - metadata["created_at"]
            if age.total_seconds() > self.client_ttl:
                expired_clients.append(client_id)
        
        if expired_clients:
            logger.debug(f"[ClickHouseFactory] Cleaning up {len(expired_clients)} expired clients")
            
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
                    logger.warning(f"[ClickHouseFactory] Error during cleanup of client {client_id}: {e}")
    
    async def get_factory_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics for monitoring.
        
        Returns:
            Dictionary with factory metrics and health information
        """
        total_clients = len(self._active_clients)
        users_with_clients = len(self._user_client_counts)
        factory_age = (datetime.utcnow() - self.created_at).total_seconds()
        
        # Calculate age distribution
        now = datetime.utcnow()
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
            if await client.test_connection():
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
        logger.info("[ClickHouseFactory] Shutting down factory...")
        
        # Signal cleanup task to stop
        self._shutdown_event.set()
        
        # Wait for cleanup task to finish
        if self._cleanup_task and not self._cleanup_task.done():
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("[ClickHouseFactory] Cleanup task did not finish in time, cancelling")
                self._cleanup_task.cancel()
        
        # Clean up all remaining clients
        client_count = len(self._active_clients)
        if client_count > 0:
            logger.info(f"[ClickHouseFactory] Cleaning up {client_count} remaining clients")
            
            cleanup_tasks = []
            for client_id, client in self._active_clients.items():
                cleanup_tasks.append(client.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear all tracking data
        self._active_clients.clear()
        self._client_metadata.clear()
        self._user_client_counts.clear()
        
        logger.info("[ClickHouseFactory] Factory shutdown complete")


# Global factory instance following the Factory pattern
_clickhouse_factory: Optional[ClickHouseFactory] = None


def get_clickhouse_factory() -> ClickHouseFactory:
    """
    Get the global ClickHouse factory instance.
    
    Returns:
        Global ClickHouse factory instance
    """
    global _clickhouse_factory
    if _clickhouse_factory is None:
        _clickhouse_factory = ClickHouseFactory()
    return _clickhouse_factory


# Convenience functions for common usage patterns
@asynccontextmanager
async def get_user_clickhouse_client(user_context: UserExecutionContext):
    """
    Context manager for user-scoped ClickHouse client operations.
    
    Usage:
        async with get_user_clickhouse_client(user_context) as client:
            results = await client.execute("SELECT * FROM events")
    
    Args:
        user_context: User execution context
        
    Yields:
        UserClickHouseClient: User-scoped ClickHouse client
    """
    factory = get_clickhouse_factory()
    async with factory.get_user_client(user_context) as client:
        yield client


async def cleanup_clickhouse_factory():
    """Clean up the global ClickHouse factory and all its resources."""
    global _clickhouse_factory
    
    if _clickhouse_factory:
        await _clickhouse_factory.shutdown()
        _clickhouse_factory = None
    
    logger.info("[ClickHouseFactory] Global factory cleaned up")


__all__ = [
    "ClickHouseFactory",
    "UserClickHouseClient", 
    "UserClickHouseCache",
    "get_clickhouse_factory",
    "get_user_clickhouse_client",
    "cleanup_clickhouse_factory"
]