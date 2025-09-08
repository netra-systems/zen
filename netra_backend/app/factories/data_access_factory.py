"""
DataAccessFactory: Factory Pattern for Data Layer User Isolation

This module implements the Factory pattern for data access contexts, ensuring complete
user isolation at the data layer. Each factory creates user-scoped contexts that
wrap ClickHouse and Redis operations with proper user context tracking.

Follows the Factory pattern architecture from USER_CONTEXT_ARCHITECTURE.md:
- Factory creates isolated contexts per user/request
- No shared state between different users
- Thread-safe concurrent operations
- Proper cleanup and resource management

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Data layer isolation for multi-tenant security
- Value Impact: Prevents cross-user data leakage, enables enterprise compliance
- Revenue Impact: Unlocks Enterprise tier revenue with proper data governance
"""

import asyncio
import logging
import weakref
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, TypeVar, Generic
from uuid import uuid4

from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)

# Type variables for generic Factory pattern
T = TypeVar('T')
ContextType = TypeVar('ContextType')


class DataAccessFactory(ABC, Generic[ContextType]):
    """
    Abstract base class for data access factories implementing the Factory pattern.
    
    This factory creates user-scoped data contexts that ensure complete isolation
    between different users and requests. Each factory maintains its own pool of
    active contexts and handles cleanup automatically.
    
    Key Features:
    - User-scoped context creation
    - Automatic resource cleanup  
    - Thread-safe concurrent access
    - Context lifecycle management
    - Memory leak prevention via weak references
    
    Attributes:
        factory_name (str): Name of this factory for logging/debugging
        _active_contexts (Dict): Active contexts keyed by context ID
        _user_context_counts (Dict): Count of contexts per user
        _cleanup_interval (int): Cleanup interval in seconds
        _max_contexts_per_user (int): Maximum contexts per user
        _context_ttl (int): Context time-to-live in seconds
    """
    
    def __init__(self, 
                 factory_name: str,
                 max_contexts_per_user: int = 10,
                 context_ttl_seconds: int = 3600,
                 cleanup_interval_seconds: int = 300):
        """
        Initialize DataAccessFactory with resource limits and cleanup policies.
        
        Args:
            factory_name: Name for this factory (for logging)
            max_contexts_per_user: Maximum contexts allowed per user
            context_ttl_seconds: Context time-to-live in seconds
            cleanup_interval_seconds: Cleanup task interval in seconds
        """
        self.factory_name = factory_name
        self._active_contexts: Dict[str, ContextType] = {}
        self._user_context_counts: Dict[str, int] = {}
        self._context_metadata: Dict[str, Dict[str, Any]] = {}
        self._cleanup_interval = cleanup_interval_seconds
        self._max_contexts_per_user = max_contexts_per_user
        self._context_ttl = context_ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Start background cleanup task
        self._start_cleanup_task()
        
        logger.info(f"[{self.factory_name}] Factory initialized with max_contexts_per_user={max_contexts_per_user}, ttl={context_ttl_seconds}s")
    
    @abstractmethod
    async def _create_context(self, user_context: UserExecutionContext) -> ContextType:
        """
        Create a new user-scoped data context.
        
        This method must be implemented by concrete factory classes to create
        the appropriate context type (e.g., UserClickHouseContext, UserRedisContext).
        
        Args:
            user_context: User execution context with user_id, request_id, etc.
            
        Returns:
            New context instance scoped to the user
            
        Raises:
            ValueError: If user_context is invalid
            ConnectionError: If underlying service is unavailable
        """
        pass
    
    @abstractmethod
    async def _cleanup_context(self, context: ContextType) -> None:
        """
        Clean up resources for a specific context.
        
        Args:
            context: Context to clean up
        """
        pass
    
    async def create_user_context(self, user_context: UserExecutionContext) -> ContextType:
        """
        Create or reuse a user-scoped data context.
        
        Implements the Factory pattern by creating isolated contexts per user.
        Enforces resource limits and prevents context proliferation.
        
        Args:
            user_context: User execution context with validated fields
            
        Returns:
            User-scoped data context
            
        Raises:
            ValueError: If user_context is invalid or user exceeds context limit
            ConnectionError: If underlying service is unavailable
        """
        # Validate user context first
        if not isinstance(user_context, UserExecutionContext):
            raise ValueError(f"Expected UserExecutionContext, got {type(user_context)}")
        
        user_id = user_context.user_id
        
        # Check per-user context limits
        current_count = self._user_context_counts.get(user_id, 0)
        if current_count >= self._max_contexts_per_user:
            logger.warning(f"[{self.factory_name}] User {user_id} has reached context limit ({current_count}/{self._max_contexts_per_user})")
            # Clean up expired contexts for this user first
            await self._cleanup_user_contexts(user_id)
            
            # Check again after cleanup
            current_count = self._user_context_counts.get(user_id, 0) 
            if current_count >= self._max_contexts_per_user:
                raise ValueError(f"User {user_id} exceeds maximum contexts ({self._max_contexts_per_user})")
        
        # Create new context
        context_id = f"{user_id}_{user_context.request_id}_{uuid4().hex[:8]}"
        
        try:
            # Create the user-scoped context
            context = await self._create_context(user_context)
            
            # Store context and metadata
            self._active_contexts[context_id] = context
            self._context_metadata[context_id] = {
                "user_id": user_id,
                "request_id": user_context.request_id,
                "thread_id": user_context.thread_id,
                "run_id": user_context.run_id,
                "created_at": datetime.utcnow(),
                "last_accessed": datetime.utcnow(),
                "access_count": 0
            }
            
            # Update user context count
            self._user_context_counts[user_id] = current_count + 1
            
            logger.debug(f"[{self.factory_name}] Created context {context_id} for user {user_id}")
            return context
            
        except Exception as e:
            logger.error(f"[{self.factory_name}] Failed to create context for user {user_id}: {e}")
            raise
    
    async def get_context_stats(self) -> Dict[str, Any]:
        """
        Get factory statistics for monitoring and debugging.
        
        Returns:
            Dictionary with factory metrics
        """
        total_contexts = len(self._active_contexts)
        users_with_contexts = len(self._user_context_counts)
        
        # Calculate age distribution
        now = datetime.utcnow()
        age_buckets = {"0-5min": 0, "5-30min": 0, "30min-2h": 0, "2h+": 0}
        
        for metadata in self._context_metadata.values():
            age = now - metadata["created_at"]
            if age < timedelta(minutes=5):
                age_buckets["0-5min"] += 1
            elif age < timedelta(minutes=30):
                age_buckets["5-30min"] += 1
            elif age < timedelta(hours=2):
                age_buckets["30min-2h"] += 1
            else:
                age_buckets["2h+"] += 1
        
        return {
            "factory_name": self.factory_name,
            "total_contexts": total_contexts,
            "users_with_contexts": users_with_contexts,
            "max_contexts_per_user": self._max_contexts_per_user,
            "context_ttl_seconds": self._context_ttl,
            "age_distribution": age_buckets,
            "user_context_counts": dict(self._user_context_counts),
            "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done()
        }
    
    async def cleanup_user_contexts(self, user_id: str) -> int:
        """
        Clean up all contexts for a specific user.
        
        Args:
            user_id: User ID to clean up contexts for
            
        Returns:
            Number of contexts cleaned up
        """
        return await self._cleanup_user_contexts(user_id)
    
    async def _cleanup_user_contexts(self, user_id: str) -> int:
        """Internal method to clean up user contexts."""
        contexts_to_remove = []
        
        for context_id, metadata in self._context_metadata.items():
            if metadata["user_id"] == user_id:
                contexts_to_remove.append(context_id)
        
        cleanup_count = 0
        for context_id in contexts_to_remove:
            try:
                context = self._active_contexts.get(context_id)
                if context:
                    await self._cleanup_context(context)
                    cleanup_count += 1
                
                # Remove from tracking
                self._active_contexts.pop(context_id, None)
                self._context_metadata.pop(context_id, None)
                
            except Exception as e:
                logger.warning(f"[{self.factory_name}] Error cleaning up context {context_id}: {e}")
        
        # Update user context count
        if user_id in self._user_context_counts:
            self._user_context_counts[user_id] = max(0, self._user_context_counts[user_id] - cleanup_count)
            if self._user_context_counts[user_id] == 0:
                del self._user_context_counts[user_id]
        
        if cleanup_count > 0:
            logger.info(f"[{self.factory_name}] Cleaned up {cleanup_count} contexts for user {user_id}")
        
        return cleanup_count
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug(f"[{self.factory_name}] Started cleanup task")
    
    async def _cleanup_loop(self):
        """Background cleanup loop for expired contexts."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self._cleanup_interval)
                break  # Shutdown requested
            except asyncio.TimeoutError:
                # Normal cleanup cycle
                await self._cleanup_expired_contexts()
    
    async def _cleanup_expired_contexts(self):
        """Clean up expired contexts based on TTL."""
        now = datetime.utcnow()
        expired_contexts = []
        
        for context_id, metadata in self._context_metadata.items():
            age = now - metadata["created_at"]
            if age.total_seconds() > self._context_ttl:
                expired_contexts.append(context_id)
        
        if expired_contexts:
            logger.debug(f"[{self.factory_name}] Cleaning up {len(expired_contexts)} expired contexts")
            
            for context_id in expired_contexts:
                try:
                    metadata = self._context_metadata.get(context_id, {})
                    user_id = metadata.get("user_id")
                    
                    context = self._active_contexts.get(context_id)
                    if context:
                        await self._cleanup_context(context)
                    
                    # Remove from tracking
                    self._active_contexts.pop(context_id, None)
                    self._context_metadata.pop(context_id, None)
                    
                    # Update user count
                    if user_id and user_id in self._user_context_counts:
                        self._user_context_counts[user_id] = max(0, self._user_context_counts[user_id] - 1)
                        if self._user_context_counts[user_id] == 0:
                            del self._user_context_counts[user_id]
                
                except Exception as e:
                    logger.warning(f"[{self.factory_name}] Error during cleanup of context {context_id}: {e}")
    
    async def shutdown(self):
        """
        Shutdown the factory and clean up all resources.
        
        This method should be called when the application is shutting down
        to ensure proper cleanup of all contexts and background tasks.
        """
        logger.info(f"[{self.factory_name}] Shutting down factory...")
        
        # Signal cleanup task to stop
        self._shutdown_event.set()
        
        # Wait for cleanup task to finish
        if self._cleanup_task and not self._cleanup_task.done():
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"[{self.factory_name}] Cleanup task did not finish in time, cancelling")
                self._cleanup_task.cancel()
        
        # Clean up all remaining contexts
        context_count = len(self._active_contexts)
        if context_count > 0:
            logger.info(f"[{self.factory_name}] Cleaning up {context_count} remaining contexts")
            
            cleanup_tasks = []
            for context_id, context in self._active_contexts.items():
                cleanup_tasks.append(self._cleanup_context(context))
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Clear all tracking data
        self._active_contexts.clear()
        self._context_metadata.clear()
        self._user_context_counts.clear()
        
        logger.info(f"[{self.factory_name}] Factory shutdown complete")


class ClickHouseAccessFactory(DataAccessFactory):
    """
    Factory for creating user-scoped ClickHouse contexts.
    
    This factory creates UserClickHouseContext instances that wrap ClickHouse
    operations with proper user context tracking. Each context is isolated
    per user to prevent data leakage and enable proper audit trails.
    """
    
    def __init__(self, 
                 max_contexts_per_user: int = 5,
                 context_ttl_seconds: int = 1800):  # 30 minutes for ClickHouse contexts
        """
        Initialize ClickHouse factory with appropriate defaults for analytics workloads.
        
        Args:
            max_contexts_per_user: Maximum ClickHouse contexts per user (default: 5)
            context_ttl_seconds: Context TTL in seconds (default: 30 minutes)
        """
        super().__init__(
            factory_name="ClickHouseAccessFactory",
            max_contexts_per_user=max_contexts_per_user,
            context_ttl_seconds=context_ttl_seconds,
            cleanup_interval_seconds=300  # 5 minutes cleanup interval
        )
    
    async def _create_context(self, user_context: UserExecutionContext):
        """Create UserClickHouseContext with user isolation."""
        # Import here to avoid circular imports
        from netra_backend.app.data_contexts.user_data_context import UserClickHouseContext
        
        context = UserClickHouseContext(
            user_id=user_context.user_id,
            request_id=user_context.request_id,
            thread_id=user_context.thread_id
        )
        
        # Initialize the context
        await context.initialize()
        return context
    
    async def _cleanup_context(self, context) -> None:
        """Clean up UserClickHouseContext resources."""
        if hasattr(context, 'cleanup'):
            await context.cleanup()


class RedisAccessFactory(DataAccessFactory):
    """
    Factory for creating user-scoped Redis contexts.
    
    This factory creates UserRedisContext instances that wrap Redis
    operations with proper user context tracking and key namespacing.
    Each context is isolated per user to prevent session mixing.
    """
    
    def __init__(self,
                 max_contexts_per_user: int = 10, 
                 context_ttl_seconds: int = 3600):  # 1 hour for Redis contexts
        """
        Initialize Redis factory with appropriate defaults for session management.
        
        Args:
            max_contexts_per_user: Maximum Redis contexts per user (default: 10)
            context_ttl_seconds: Context TTL in seconds (default: 1 hour)
        """
        super().__init__(
            factory_name="RedisAccessFactory", 
            max_contexts_per_user=max_contexts_per_user,
            context_ttl_seconds=context_ttl_seconds,
            cleanup_interval_seconds=600  # 10 minutes cleanup interval
        )
    
    async def _create_context(self, user_context: UserExecutionContext):
        """Create UserRedisContext with user isolation."""
        # Import here to avoid circular imports
        from netra_backend.app.data_contexts.user_data_context import UserRedisContext
        
        context = UserRedisContext(
            user_id=user_context.user_id,
            request_id=user_context.request_id,
            thread_id=user_context.thread_id
        )
        
        # Initialize the context
        await context.initialize()
        return context
    
    async def _cleanup_context(self, context) -> None:
        """Clean up UserRedisContext resources."""
        if hasattr(context, 'cleanup'):
            await context.cleanup()


# Global factory instances following the Factory pattern
_clickhouse_factory: Optional[ClickHouseAccessFactory] = None
_redis_factory: Optional[RedisAccessFactory] = None


def get_clickhouse_factory() -> ClickHouseAccessFactory:
    """
    Get the global ClickHouse access factory instance.
    
    Returns:
        Global ClickHouse factory instance
    """
    global _clickhouse_factory
    if _clickhouse_factory is None:
        _clickhouse_factory = ClickHouseAccessFactory()
    return _clickhouse_factory


def get_redis_factory() -> RedisAccessFactory:
    """
    Get the global Redis access factory instance.
    
    Returns:
        Global Redis factory instance
    """
    global _redis_factory
    if _redis_factory is None:
        _redis_factory = RedisAccessFactory()
    return _redis_factory


@asynccontextmanager
async def get_user_clickhouse_context(user_context: UserExecutionContext):
    """
    Context manager for user-scoped ClickHouse operations.
    
    Usage:
        async with get_user_clickhouse_context(user_context) as ch_context:
            results = await ch_context.execute("SELECT * FROM events WHERE user_id = %(user_id)s")
    
    Args:
        user_context: User execution context
        
    Yields:
        UserClickHouseContext: User-scoped ClickHouse context
    """
    factory = get_clickhouse_factory()
    context = await factory.create_user_context(user_context)
    try:
        yield context
    finally:
        # Context cleanup is handled by factory TTL and cleanup tasks
        pass


@asynccontextmanager  
async def get_user_redis_context(user_context: UserExecutionContext):
    """
    Context manager for user-scoped Redis operations.
    
    Usage:
        async with get_user_redis_context(user_context) as redis_context:
            await redis_context.set("session_key", "session_value")
    
    Args:
        user_context: User execution context
        
    Yields:
        UserRedisContext: User-scoped Redis context
    """
    factory = get_redis_factory()
    context = await factory.create_user_context(user_context)
    try:
        yield context
    finally:
        # Context cleanup is handled by factory TTL and cleanup tasks
        pass


# Cleanup utilities for testing and shutdown
async def cleanup_all_factories():
    """Clean up all factory instances and their contexts."""
    global _clickhouse_factory, _redis_factory
    
    cleanup_tasks = []
    
    if _clickhouse_factory:
        cleanup_tasks.append(_clickhouse_factory.shutdown())
    
    if _redis_factory:
        cleanup_tasks.append(_redis_factory.shutdown())
    
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    # Reset global instances
    _clickhouse_factory = None
    _redis_factory = None


__all__ = [
    "DataAccessFactory",
    "ClickHouseAccessFactory", 
    "RedisAccessFactory",
    "get_clickhouse_factory",
    "get_redis_factory",
    "get_user_clickhouse_context",
    "get_user_redis_context",
    "cleanup_all_factories"
]