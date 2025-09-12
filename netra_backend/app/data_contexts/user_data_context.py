"""
UserDataContext: User-Scoped Data Operations with Complete Isolation

This module provides user-scoped data contexts that ensure complete isolation
of data operations between different users. Each context wraps ClickHouse and
Redis operations with automatic user_id inclusion and proper audit trails.

Implements the three-tier architecture's data isolation requirements:
- All operations include user_id for proper isolation
- Cache keys are namespaced by user to prevent contamination
- Audit trails track all data access by user and request
- Thread-safe concurrent operations with proper resource management

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)  
- Business Goal: Complete data isolation for multi-tenant security
- Value Impact: Zero risk of cross-user data leakage, enterprise compliance
- Revenue Impact: Critical for Enterprise revenue, prevents security incidents
"""

import asyncio
import logging
import json
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class UserDataContext(ABC):
    """
    Abstract base class for user-scoped data contexts.
    
    Provides common functionality for user isolation, audit trails,
    and resource management across different data stores.
    
    Key Features:
    - Automatic user_id inclusion in all operations
    - Request-level tracking and audit trails
    - Resource cleanup and connection management
    - Thread-safe concurrent operations
    - Comprehensive error handling and logging
    
    Attributes:
        user_id (str): User identifier for all operations
        request_id (str): Request identifier for audit trails
        thread_id (str): Thread identifier for concurrent tracking
        created_at (datetime): Context creation timestamp
        operation_count (int): Number of operations performed
        last_activity (datetime): Timestamp of last operation
    """
    
    def __init__(self, user_id: str, request_id: str, thread_id: str):
        """
        Initialize user data context with required identifiers.
        
        Args:
            user_id: User identifier (must not be None, empty, or "None")
            request_id: Request identifier (must not be None or empty)  
            thread_id: Thread identifier (must not be None or empty)
            
        Raises:
            ValueError: If any identifier is invalid
        """
        # Validate required identifiers
        if not user_id or user_id in ["None", ""]:
            raise ValueError("UserDataContext requires valid user_id for data isolation")
        if not request_id or request_id == "":
            raise ValueError("UserDataContext requires valid request_id for audit trails")
        if not thread_id or thread_id == "":
            raise ValueError("UserDataContext requires valid thread_id for concurrent tracking")
        
        self.user_id = user_id
        self.request_id = request_id
        self.thread_id = thread_id
        self.created_at = datetime.utcnow()
        self.operation_count = 0
        self.last_activity = self.created_at
        self._initialized = False
        self._lock = asyncio.Lock()
        
        logger.debug(f"[UserDataContext] Created for user {self.user_id[:8]}... (request: {self.request_id})")
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the data context and establish connections.
        
        Must be called before using the context for operations.
        Concrete implementations should establish connections to their data stores.
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources and close connections.
        
        Should be called when the context is no longer needed.
        Concrete implementations should clean up connections and resources.
        """
        pass
    
    def _update_activity(self) -> None:
        """Update activity tracking for this context."""
        self.operation_count += 1
        self.last_activity = datetime.utcnow()
    
    def _create_audit_context(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Create audit context for logging data operations.
        
        Args:
            operation: Name of the operation being performed
            **kwargs: Additional context for the operation
            
        Returns:
            Dictionary with audit context information
        """
        return {
            "user_id": self.user_id,
            "request_id": self.request_id,
            "thread_id": self.thread_id,
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
            "context_age_seconds": (datetime.utcnow() - self.created_at).total_seconds(),
            "operation_count": self.operation_count + 1,
            **kwargs
        }
    
    def get_context_info(self) -> Dict[str, Any]:
        """
        Get context information for debugging and monitoring.
        
        Returns:
            Dictionary with context metadata
        """
        age_seconds = (datetime.utcnow() - self.created_at).total_seconds()
        last_activity_seconds = (datetime.utcnow() - self.last_activity).total_seconds()
        
        return {
            "user_id": f"{self.user_id[:8]}...",  # Truncated for security
            "request_id": self.request_id,
            "thread_id": self.thread_id, 
            "created_at": self.created_at.isoformat(),
            "age_seconds": age_seconds,
            "operation_count": self.operation_count,
            "last_activity": self.last_activity.isoformat(),
            "last_activity_seconds_ago": last_activity_seconds,
            "initialized": self._initialized
        }


class UserClickHouseContext(UserDataContext):
    """
    User-scoped ClickHouse context with complete data isolation.
    
    Wraps all ClickHouse operations with automatic user_id inclusion and
    user-scoped caching. Ensures that:
    - All queries automatically include user context
    - Cache keys are namespaced by user to prevent contamination  
    - Audit trails track all ClickHouse access by user
    - Connection pooling is managed per context
    
    Usage:
        context = UserClickHouseContext(user_id, request_id, thread_id)
        await context.initialize()
        results = await context.execute("SELECT * FROM events")
        await context.cleanup()
    """
    
    def __init__(self, user_id: str, request_id: str, thread_id: str):
        """Initialize ClickHouse context with user isolation."""
        super().__init__(user_id, request_id, thread_id)
        self._clickhouse_service = None
        self._connection_pool = None
        
    async def initialize(self) -> None:
        """
        Initialize ClickHouse connection with user context.
        
        Raises:
            ConnectionError: If ClickHouse service is unavailable
        """
        async with self._lock:
            if self._initialized:
                return
                
            try:
                # Import here to avoid circular imports
                from netra_backend.app.db.clickhouse import get_clickhouse_service
                
                # Get ClickHouse service (handles real vs mock automatically)
                self._clickhouse_service = get_clickhouse_service()
                
                # Initialize the service if needed
                if hasattr(self._clickhouse_service, 'initialize') and not self._clickhouse_service._client:
                    await self._clickhouse_service.initialize()
                
                self._initialized = True
                self._update_activity()
                
                logger.debug(f"[UserClickHouseContext] Initialized for user {self.user_id[:8]}...")
                
            except Exception as e:
                logger.error(f"[UserClickHouseContext] Failed to initialize for user {self.user_id}: {e}")
                raise ConnectionError(f"Failed to initialize ClickHouse context: {e}") from e
    
    async def execute(self, 
                     query: str, 
                     params: Optional[Dict[str, Any]] = None,
                     max_retries: int = 2) -> List[Dict[str, Any]]:
        """
        Execute ClickHouse query with user context and isolation.
        
        Automatically includes user_id in cache keys and provides user-isolated results.
        All operations are logged with full audit context.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters (user_id will be automatically added)
            max_retries: Maximum retry attempts for transient failures
            
        Returns:
            Query results as list of dictionaries
            
        Raises:
            ValueError: If context not initialized
            ConnectionError: If ClickHouse is unavailable
        """
        if not self._initialized:
            raise ValueError("UserClickHouseContext must be initialized before use")
        
        # Prepare parameters with user context
        effective_params = params or {}
        
        # Add user_id to params for queries that need it
        if "user_id" not in effective_params:
            effective_params["user_id"] = self.user_id
        
        # Create audit context
        audit_ctx = self._create_audit_context(
            operation="clickhouse_query",
            query_hash=hash(query),
            has_params=bool(effective_params),
            max_retries=max_retries
        )
        
        try:
            # Execute with user-scoped caching (user_id passed for cache isolation)
            result = await self._clickhouse_service.execute_with_retry(
                query=query,
                params=effective_params, 
                max_retries=max_retries,
                user_id=self.user_id  # Critical: Pass user_id for cache isolation
            )
            
            self._update_activity()
            
            # Log successful operation
            audit_ctx.update({
                "status": "success",
                "result_count": len(result) if result else 0
            })
            logger.debug(f"[UserClickHouseContext] Query executed successfully", extra=audit_ctx)
            
            return result
            
        except Exception as e:
            # Log failed operation
            audit_ctx.update({
                "status": "error", 
                "error": str(e)
            })
            logger.error(f"[UserClickHouseContext] Query execution failed for user {self.user_id}: {e}", extra=audit_ctx)
            raise
    
    async def execute_query(self, 
                           query: str,
                           params: Optional[Dict[str, Any]] = None,
                           timeout: Optional[float] = None,
                           max_memory_usage: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute query with additional ClickHouse-specific options.
        
        Provides compatibility with existing ClickHouse interfaces while ensuring
        user isolation and proper context tracking.
        
        Args:
            query: SQL query to execute
            params: Optional query parameters  
            timeout: Query timeout (currently for interface compatibility)
            max_memory_usage: Memory limit (currently for interface compatibility)
            
        Returns:
            Query results as list of dictionaries
        """
        # Use execute method with user context (timeout/memory limits may be added later)
        return await self.execute(query, params)
    
    async def batch_insert(self, 
                          table_name: str, 
                          data: List[Dict[str, Any]],
                          include_user_context: bool = True) -> None:
        """
        Insert batch data with optional user context inclusion.
        
        Args:
            table_name: Target table name
            data: List of records to insert
            include_user_context: If True, adds user_id to each record
        """
        if not self._initialized:
            raise ValueError("UserClickHouseContext must be initialized before use")
        
        if not data:
            return
        
        # Add user context to records if requested
        if include_user_context:
            enhanced_data = []
            for record in data:
                enhanced_record = record.copy()
                if "user_id" not in enhanced_record:
                    enhanced_record["user_id"] = self.user_id
                if "request_id" not in enhanced_record:
                    enhanced_record["request_id"] = self.request_id
                enhanced_data.append(enhanced_record)
        else:
            enhanced_data = data
        
        audit_ctx = self._create_audit_context(
            operation="clickhouse_batch_insert",
            table_name=table_name,
            record_count=len(enhanced_data),
            include_user_context=include_user_context
        )
        
        try:
            await self._clickhouse_service.batch_insert(table_name, enhanced_data)
            self._update_activity()
            
            audit_ctx["status"] = "success"
            logger.debug(f"[UserClickHouseContext] Batch insert completed", extra=audit_ctx)
            
        except Exception as e:
            audit_ctx.update({"status": "error", "error": str(e)})
            logger.error(f"[UserClickHouseContext] Batch insert failed: {e}", extra=audit_ctx)
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get user-specific cache statistics.
        
        Returns:
            Cache statistics for this user
        """
        if not self._initialized or not self._clickhouse_service:
            return {"error": "Context not initialized"}
        
        return self._clickhouse_service.get_cache_stats(user_id=self.user_id)
    
    def clear_user_cache(self) -> None:
        """Clear cache entries for this user only."""
        if self._initialized and self._clickhouse_service:
            self._clickhouse_service.clear_cache(user_id=self.user_id)
            logger.info(f"[UserClickHouseContext] Cleared cache for user {self.user_id}")
    
    async def cleanup(self) -> None:
        """Clean up ClickHouse context resources."""
        async with self._lock:
            if not self._initialized:
                return
            
            try:
                # Clear user-specific cache entries
                if self._clickhouse_service:
                    self._clickhouse_service.clear_cache(user_id=self.user_id)
                
                # Service cleanup is handled by the global service
                # Individual contexts don't own the service connection
                
                self._initialized = False
                logger.debug(f"[UserClickHouseContext] Cleaned up for user {self.user_id[:8]}...")
                
            except Exception as e:
                logger.warning(f"[UserClickHouseContext] Error during cleanup for user {self.user_id}: {e}")


class UserRedisContext(UserDataContext):
    """
    User-scoped Redis context with complete key namespacing.
    
    Wraps all Redis operations with automatic user namespacing to ensure
    complete isolation between users. All keys are prefixed with user_id
    to prevent session mixing and data leakage.
    
    Key Features:
    - Automatic key namespacing by user_id
    - User-isolated session management
    - Audit trails for all Redis operations
    - Support for all Redis data types (strings, lists, sets, hashes)
    - Thread-safe concurrent operations
    
    Usage:
        context = UserRedisContext(user_id, request_id, thread_id)
        await context.initialize()
        await context.set("session_key", "session_value")
        value = await context.get("session_key")
        await context.cleanup()
    """
    
    def __init__(self, user_id: str, request_id: str, thread_id: str):
        """Initialize Redis context with user namespacing."""
        super().__init__(user_id, request_id, thread_id)
        self._redis_service = None
    
    async def initialize(self) -> None:
        """
        Initialize Redis connection with user context.
        
        Raises:
            ConnectionError: If Redis service is unavailable
        """
        async with self._lock:
            if self._initialized:
                return
                
            try:
                # Import here to avoid circular imports
                from netra_backend.app.services.redis_service import redis_service
                
                # Get Redis service (handles real vs test connections)
                self._redis_service = redis_service
                
                # Ensure connection is established
                if not await self._redis_service.ping():
                    await self._redis_service.connect()
                
                self._initialized = True
                self._update_activity()
                
                logger.debug(f"[UserRedisContext] Initialized for user {self.user_id[:8]}...")
                
            except Exception as e:
                logger.error(f"[UserRedisContext] Failed to initialize for user {self.user_id}: {e}")
                raise ConnectionError(f"Failed to initialize Redis context: {e}") from e
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value by key with user namespacing.
        
        Args:
            key: Redis key (will be automatically namespaced by user_id)
            
        Returns:
            Value if found, None otherwise
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        audit_ctx = self._create_audit_context(operation="redis_get", key=key)
        
        try:
            # Use user_id parameter for automatic namespacing
            result = await self._redis_service.get(key, user_id=self.user_id)
            self._update_activity()
            
            audit_ctx.update({"status": "success", "found": result is not None})
            logger.debug(f"[UserRedisContext] Get operation completed", extra=audit_ctx)
            
            return result
            
        except Exception as e:
            audit_ctx.update({"status": "error", "error": str(e)})
            logger.error(f"[UserRedisContext] Get operation failed: {e}", extra=audit_ctx)
            raise
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set key-value pair with user namespacing.
        
        Args:
            key: Redis key (will be automatically namespaced by user_id)
            value: Value to store
            ex: Optional expiration time in seconds
            
        Returns:
            True if successful
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        audit_ctx = self._create_audit_context(
            operation="redis_set",
            key=key,
            has_expiry=ex is not None,
            expiry_seconds=ex
        )
        
        try:
            result = await self._redis_service.set(key, value, ex=ex, user_id=self.user_id)
            self._update_activity()
            
            audit_ctx.update({"status": "success", "result": result})
            logger.debug(f"[UserRedisContext] Set operation completed", extra=audit_ctx)
            
            return result
            
        except Exception as e:
            audit_ctx.update({"status": "error", "error": str(e)})
            logger.error(f"[UserRedisContext] Set operation failed: {e}", extra=audit_ctx)
            raise
    
    async def setex(self, key: str, time: int, value: str) -> bool:
        """
        Set key-value pair with expiration and user namespacing.
        
        Args:
            key: Redis key (will be automatically namespaced by user_id)
            time: Expiration time in seconds  
            value: Value to store
            
        Returns:
            True if successful
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.setex(key, time, value, user_id=self.user_id)
    
    async def delete(self, *keys: str) -> int:
        """
        Delete keys with user namespacing.
        
        Args:
            *keys: Redis keys to delete (will be automatically namespaced by user_id)
            
        Returns:
            Number of keys deleted
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        audit_ctx = self._create_audit_context(
            operation="redis_delete",
            key_count=len(keys)
        )
        
        try:
            result = await self._redis_service.delete(*keys, user_id=self.user_id)
            self._update_activity()
            
            audit_ctx.update({"status": "success", "deleted_count": result})
            logger.debug(f"[UserRedisContext] Delete operation completed", extra=audit_ctx)
            
            return result
            
        except Exception as e:
            audit_ctx.update({"status": "error", "error": str(e)})
            logger.error(f"[UserRedisContext] Delete operation failed: {e}", extra=audit_ctx)
            raise
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists with user namespacing.
        
        Args:
            key: Redis key (will be automatically namespaced by user_id)
            
        Returns:
            True if key exists
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.exists(key, user_id=self.user_id)
    
    async def expire(self, key: str, time: int) -> bool:
        """
        Set key expiration with user namespacing.
        
        Args:
            key: Redis key (will be automatically namespaced by user_id)
            time: Expiration time in seconds
            
        Returns:
            True if expiration was set
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.expire(key, time, user_id=self.user_id)
    
    async def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching pattern with user namespacing.
        
        Args:
            pattern: Key pattern (will be automatically namespaced by user_id)
            
        Returns:
            List of matching keys (with namespacing removed)
        """
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.keys(pattern, user_id=self.user_id)
    
    # JSON operations
    async def set_json(self, key: str, value: Dict[str, Any], ex: Optional[int] = None) -> bool:
        """Set JSON value with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.set_json(key, value, ex=ex, user_id=self.user_id)
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value with user namespacing.""" 
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.get_json(key, user_id=self.user_id)
    
    # Numeric operations
    async def incr(self, key: str) -> int:
        """Increment key value with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.incr(key, user_id=self.user_id)
    
    async def decr(self, key: str) -> int:
        """Decrement key value with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.decr(key, user_id=self.user_id)
    
    # List operations
    async def lpush(self, key: str, *values) -> int:
        """Push to left of list with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.lpush(key, *values, user_id=self.user_id)
    
    async def rpush(self, key: str, *values) -> int:
        """Push to right of list with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.rpush(key, *values, user_id=self.user_id)
    
    async def lpop(self, key: str) -> Optional[str]:
        """Pop from left of list with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.lpop(key, user_id=self.user_id)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop from right of list with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.rpop(key, user_id=self.user_id)
    
    async def llen(self, key: str) -> int:
        """Get list length with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.llen(key, user_id=self.user_id)
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get list range with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.lrange(key, start, end, user_id=self.user_id)
    
    # Set operations
    async def sadd(self, key: str, *members) -> int:
        """Add to set with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.sadd(key, *members, user_id=self.user_id)
    
    async def srem(self, key: str, *members) -> int:
        """Remove from set with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.srem(key, *members, user_id=self.user_id)
    
    async def smembers(self, key: str) -> List[str]:
        """Get set members with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.smembers(key, user_id=self.user_id)
    
    # Hash operations
    async def hset(self, key: str, field_or_mapping: Union[str, Dict[str, Any]], value: Optional[str] = None) -> int:
        """Set hash field with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.hset(key, field_or_mapping, value, user_id=self.user_id)
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.hget(key, field, user_id=self.user_id)
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.hgetall(key, user_id=self.user_id)
    
    async def ttl(self, key: str) -> int:
        """Get time to live with user namespacing."""
        if not self._initialized:
            raise ValueError("UserRedisContext must be initialized before use")
        
        return await self._redis_service.ttl(key, user_id=self.user_id)
    
    async def cleanup(self) -> None:
        """Clean up Redis context resources."""
        async with self._lock:
            if not self._initialized:
                return
            
            try:
                # Redis service cleanup is handled globally
                # Individual contexts don't own connections
                
                self._initialized = False
                logger.debug(f"[UserRedisContext] Cleaned up for user {self.user_id[:8]}...")
                
            except Exception as e:
                logger.warning(f"[UserRedisContext] Error during cleanup for user {self.user_id}: {e}")


__all__ = [
    "UserDataContext",
    "UserClickHouseContext", 
    "UserRedisContext"
]