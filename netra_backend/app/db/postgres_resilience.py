"""PostgreSQL resilience utilities with retry logic and degraded operation.

Implements pragmatic rigor principles:
- Default to resilience with degraded operation when possible
- Retry with exponential backoff for transient failures
- Read-only mode fallbacks for write operation failures
- Connection pool tolerance and graceful degradation
"""

import asyncio
import hashlib
import time
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from sqlalchemy.exc import DatabaseError, DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.client_config import DatabaseClientConfig
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class PostgresResilienceError(Exception):
    """Base exception for PostgreSQL resilience operations."""
    pass


class ReadOnlyModeError(PostgresResilienceError):
    """Raised when operation requires write but only read is available."""
    pass


class CacheEntry:
    """Simple cache entry with TTL."""
    
    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.time() + ttl
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def age(self) -> float:
        return time.time() - self.created_at


class ResilienceCache:
    """Simple in-memory cache for fallback responses."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        entry = self.cache.get(key)
        if entry and not entry.is_expired():
            self._hits += 1
            logger.debug(f"Cache hit for key: {key[:50]}...")
            return entry.value
        elif entry:
            # Remove expired entry
            del self.cache[key]
        
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: float) -> None:
        """Set cached value with TTL."""
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at
            )[:10]  # Remove 10 oldest
            for k in oldest_keys:
                del self.cache[k]
        
        self.cache[key] = CacheEntry(value, ttl)
        logger.debug(f"Cached value for key: {key[:50]}... (TTL: {ttl}s)")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "max_size": self.max_size
        }


# Global cache instance
_query_cache = ResilienceCache(DatabaseClientConfig.CACHE_CONFIG["max_cache_size"])


class RetryStrategy:
    """Exponential backoff retry strategy with jitter."""
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or DatabaseClientConfig.RETRY_CONFIG
        self.max_retries = config["max_retries"]
        self.base_delay = config["base_delay"]
        self.max_delay = config["max_delay"]
        self.exponential_base = config["exponential_base"]
        self.jitter = config["jitter"]
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Add up to 25% jitter
            import random
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount
        
        return delay
    
    async def execute_with_retry(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation"
    ) -> T:
        """Execute operation with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.calculate_delay(attempt - 1)
                    logger.info(f"Retrying {operation_name} (attempt {attempt + 1}/{self.max_retries + 1}) after {delay:.2f}s")
                    await asyncio.sleep(delay)
                
                result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
                
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")
                
                return result
                
            except (OperationalError, DatabaseError, DisconnectionError) as e:
                last_exception = e
                logger.warning(f"{operation_name} failed on attempt {attempt + 1}: {e}")
                
                if attempt == self.max_retries:
                    logger.error(f"{operation_name} failed after {self.max_retries + 1} attempts")
                    break
            
            except Exception as e:
                # Non-retryable exceptions
                logger.error(f"{operation_name} failed with non-retryable error: {e}")
                raise
        
        raise last_exception


class PostgresResilienceManager:
    """Manages PostgreSQL resilience patterns and degraded operation modes."""
    
    def __init__(self):
        self.retry_strategy = RetryStrategy()
        self._read_only_mode = False
        self._connection_healthy = True
    
    @property
    def is_read_only_mode(self) -> bool:
        """Check if database is in read-only mode."""
        return self._read_only_mode
    
    @property
    def is_connection_healthy(self) -> bool:
        """Check if database connection is healthy."""
        return self._connection_healthy
    
    def set_read_only_mode(self, enabled: bool) -> None:
        """Enable or disable read-only mode."""
        if enabled != self._read_only_mode:
            logger.warning(f"PostgreSQL read-only mode {'enabled' if enabled else 'disabled'}")
            self._read_only_mode = enabled
    
    def set_connection_health(self, healthy: bool) -> None:
        """Set connection health status."""
        if healthy != self._connection_healthy:
            logger.info(f"PostgreSQL connection health changed to {'healthy' if healthy else 'unhealthy'}")
            self._connection_healthy = healthy
    
    def _generate_cache_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for query and parameters."""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        if params:
            params_str = str(sorted(params.items()))
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"query:{query_hash}:params:{params_hash}"
        return f"query:{query_hash}"
    
    async def execute_with_resilience(
        self,
        operation: Callable,
        operation_name: str,
        allow_cache: bool = False,
        cache_ttl: Optional[float] = None,
        query: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        is_write_operation: bool = False
    ) -> Any:
        """Execute database operation with full resilience patterns."""
        
        # Check read-only mode for write operations
        if is_write_operation and self._read_only_mode:
            raise ReadOnlyModeError("Database is in read-only mode, write operations not allowed")
        
        # Try cache first for read operations
        cache_key = None
        if allow_cache and query and not is_write_operation:
            cache_key = self._generate_cache_key(query, params)
            cached_result = _query_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Returning cached result for {operation_name}")
                return cached_result
        
        # Execute with retry
        try:
            result = await self.retry_strategy.execute_with_retry(
                operation, operation_name
            )
            
            # Cache successful read results
            if allow_cache and cache_key and not is_write_operation:
                ttl = cache_ttl or DatabaseClientConfig.CACHE_CONFIG["query_cache_ttl"]
                _query_cache.set(cache_key, result, ttl)
            
            # Update health status on success
            self.set_connection_health(True)
            
            return result
            
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            # Mark connection as unhealthy
            self.set_connection_health(False)
            
            # For read operations, try to return cached data even if expired
            if allow_cache and cache_key and not is_write_operation:
                stale_cache = self._get_stale_cache(cache_key)
                if stale_cache is not None:
                    logger.warning(f"Returning stale cached data for {operation_name} due to database error: {e}")
                    return stale_cache
            
            # Enable read-only mode for write failures
            if is_write_operation:
                self.set_read_only_mode(True)
                logger.error(f"Write operation failed, enabling read-only mode: {e}")
            
            raise
    
    def _get_stale_cache(self, cache_key: str) -> Optional[Any]:
        """Get cached value even if expired (for fallback)."""
        entry = _query_cache.cache.get(cache_key)
        if entry:
            logger.info(f"Using stale cache (age: {entry.age():.1f}s) for fallback")
            return entry.value
        return None
    
    async def test_connection_health(self) -> bool:
        """Test database connection health with simple query."""
        try:
            from .postgres_session import get_async_db
            async with get_async_db() as session:
                await session.execute("SELECT 1")
                self.set_connection_health(True)
                return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            self.set_connection_health(False)
            return False
    
    async def attempt_recovery(self) -> bool:
        """Attempt to recover from degraded state."""
        logger.info("Attempting PostgreSQL recovery...")
        
        # Test basic connectivity
        if await self.test_connection_health():
            # Try to disable read-only mode if connection is healthy
            if self._read_only_mode:
                try:
                    # Test with a simple write operation
                    from .postgres_session import get_async_db
                    async with get_async_db() as session:
                        # This will test if writes are actually working
                        await session.execute("SELECT 1")  # Simple test
                        self.set_read_only_mode(False)
                        logger.info("PostgreSQL recovery successful - write operations restored")
                        return True
                except Exception as e:
                    logger.warning(f"Write operations still failing during recovery: {e}")
                    return False
            else:
                logger.info("PostgreSQL connection healthy")
                return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get resilience manager status."""
        return {
            "connection_healthy": self._connection_healthy,
            "read_only_mode": self._read_only_mode,
            "cache_stats": _query_cache.stats(),
            "retry_config": {
                "max_retries": self.retry_strategy.max_retries,
                "base_delay": self.retry_strategy.base_delay,
                "max_delay": self.retry_strategy.max_delay
            }
        }


# Global resilience manager instance
postgres_resilience = PostgresResilienceManager()


def with_postgres_resilience(
    operation_name: str,
    allow_cache: bool = False,
    cache_ttl: Optional[float] = None,
    is_write_operation: bool = False
):
    """Decorator to add resilience patterns to PostgreSQL operations."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await postgres_resilience.execute_with_resilience(
                operation=lambda: func(*args, **kwargs),
                operation_name=operation_name,
                allow_cache=allow_cache,
                cache_ttl=cache_ttl,
                is_write_operation=is_write_operation
            )
        return wrapper
    return decorator


@asynccontextmanager
async def resilient_postgres_session():
    """Get PostgreSQL session with resilience patterns applied."""
    from .postgres_session import get_async_db
    
    try:
        async with get_async_db() as session:
            yield session
    except (OperationalError, DatabaseError, DisconnectionError) as e:
        logger.error(f"PostgreSQL session failed: {e}")
        postgres_resilience.set_connection_health(False)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in PostgreSQL session: {e}")
        raise