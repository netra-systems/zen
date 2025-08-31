"""Rate Limiting Service for Analytics Service.

Implements user-based rate limiting using Redis with:
- Sliding window algorithm for accurate rate limiting
- User-specific rate limits (1000 events/minute by default)
- Retry-After calculation for client guidance
- Configurable time windows and limits
- Redis-based distributed rate limiting

This module follows the isolation pattern - no imports from other services.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

from analytics_core.database.redis_manager import get_redis_manager, RedisConnectionError

logger = logging.getLogger(__name__)


class RateLimitResult:
    """Result of a rate limit check."""
    
    def __init__(
        self,
        allowed: bool,
        remaining: int,
        reset_time: float,
        retry_after: Optional[int] = None,
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after
    
    def __repr__(self) -> str:
        return (
            f"RateLimitResult(allowed={self.allowed}, remaining={self.remaining}, "
            f"reset_time={self.reset_time}, retry_after={self.retry_after})"
        )


class RateLimitType(Enum):
    """Different types of rate limits."""
    USER_EVENTS = "user_events"
    API_REQUESTS = "api_requests"
    ANALYTICS_QUERIES = "analytics_queries"


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    
    Features:
    - Sliding window for accurate rate limiting
    - Per-user rate limiting with configurable limits
    - Distributed rate limiting across multiple instances
    - Retry-After calculation for proper HTTP responses
    - Automatic cleanup of expired entries
    """
    
    # Default rate limits (requests per window)
    DEFAULT_LIMITS = {
        RateLimitType.USER_EVENTS: {
            "limit": 1000,      # requests
            "window": 60,       # seconds (1 minute)
        },
        RateLimitType.API_REQUESTS: {
            "limit": 5000,      # requests
            "window": 3600,     # seconds (1 hour)
        },
        RateLimitType.ANALYTICS_QUERIES: {
            "limit": 100,       # requests
            "window": 60,       # seconds (1 minute)
        },
    }
    
    def __init__(self, redis_manager=None):
        """
        Initialize rate limiter.
        
        Args:
            redis_manager: Optional Redis manager instance. If None, uses global manager.
        """
        self.redis_manager = redis_manager or get_redis_manager()
        self._lua_script = None
    
    async def _get_lua_script(self) -> str:
        """
        Get the Lua script for atomic sliding window rate limiting.
        
        This script ensures atomic operations in Redis for accurate rate limiting
        even under high concurrency.
        """
        if self._lua_script is None:
            # Lua script for sliding window rate limiting
            # KEYS[1] = rate limit key
            # ARGV[1] = window size in seconds
            # ARGV[2] = limit
            # ARGV[3] = current timestamp
            # ARGV[4] = unique request ID
            self._lua_script = """
                local key = KEYS[1]
                local window = tonumber(ARGV[1])
                local limit = tonumber(ARGV[2])
                local now = tonumber(ARGV[3])
                local request_id = ARGV[4]
                
                -- Remove expired entries (older than window)
                local expired_time = now - window
                redis.call('ZREMRANGEBYSCORE', key, 0, expired_time)
                
                -- Count current entries in window
                local current_count = redis.call('ZCARD', key)
                
                -- Check if limit is exceeded
                if current_count >= limit then
                    -- Get the oldest entry to calculate reset time
                    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                    local reset_time = oldest[2] and (oldest[2] + window) or (now + window)
                    
                    return {
                        0,               -- not allowed
                        0,               -- remaining
                        reset_time,      -- reset time
                        current_count    -- current count
                    }
                end
                
                -- Add current request to the window
                redis.call('ZADD', key, now, request_id)
                
                -- Set expiration for cleanup (window + buffer)
                redis.call('EXPIRE', key, window + 60)
                
                -- Calculate remaining requests
                local remaining = limit - current_count - 1
                
                -- Calculate reset time (when oldest entry expires)
                local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
                local reset_time = oldest[2] and (oldest[2] + window) or (now + window)
                
                return {
                    1,               -- allowed
                    remaining,       -- remaining
                    reset_time,      -- reset time
                    current_count + 1 -- current count
                }
            """
        
        return self._lua_script
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit_type: RateLimitType = RateLimitType.USER_EVENTS,
        custom_limit: Optional[int] = None,
        custom_window: Optional[int] = None,
    ) -> RateLimitResult:
        """
        Check if a user is within their rate limit.
        
        Args:
            user_id: User identifier
            limit_type: Type of rate limit to check
            custom_limit: Override default limit
            custom_window: Override default window (seconds)
            
        Returns:
            RateLimitResult with limit check information
        """
        try:
            # Get limit configuration
            config = self.DEFAULT_LIMITS[limit_type]
            limit = custom_limit or config["limit"]
            window = custom_window or config["window"]
            
            # Build Redis key
            key = f"rate_limit:{limit_type.value}:user:{user_id}"
            
            # Generate unique request ID
            request_id = f"{time.time():.6f}:{id(asyncio.current_task())}"
            
            # Get current timestamp
            now = time.time()
            
            # Execute Lua script atomically
            async with self.redis_manager.get_connection() as redis_conn:
                lua_script = await self._get_lua_script()
                script = redis_conn.register_script(lua_script)
                
                result = await script(
                    keys=[key],
                    args=[window, limit, now, request_id]
                )
            
            # Parse results
            allowed = bool(result[0])
            remaining = max(0, int(result[1]))
            reset_time = float(result[2])
            current_count = int(result[3])
            
            # Calculate retry-after if rate limited
            retry_after = None
            if not allowed:
                retry_after = max(1, int(reset_time - now))
            
            rate_limit_result = RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} "
                    f"({limit_type.value}): {current_count}/{limit} requests "
                    f"in {window}s window. Retry after {retry_after}s."
                )
            else:
                logger.debug(
                    f"Rate limit check passed for user {user_id} "
                    f"({limit_type.value}): {current_count}/{limit} requests "
                    f"in {window}s window. {remaining} remaining."
                )
            
            return rate_limit_result
            
        except Exception as e:
            logger.error(f"Rate limit check failed for user {user_id}: {e}")
            # On error, allow the request (fail open)
            return RateLimitResult(
                allowed=True,
                remaining=0,
                reset_time=time.time() + 60,
            )
    
    async def reset_user_limits(
        self,
        user_id: str,
        limit_type: Optional[RateLimitType] = None,
    ) -> Dict[str, bool]:
        """
        Reset rate limits for a user.
        
        Args:
            user_id: User identifier
            limit_type: Specific limit type to reset, or None for all types
            
        Returns:
            Dictionary with limit type as key and success status as value
        """
        results = {}
        
        # Determine which limit types to reset
        types_to_reset = [limit_type] if limit_type else list(RateLimitType)
        
        for ltype in types_to_reset:
            try:
                key = f"rate_limit:{ltype.value}:user:{user_id}"
                
                async with self.redis_manager.get_connection() as redis_conn:
                    deleted = await redis_conn.delete(key)
                    
                results[ltype.value] = deleted > 0
                logger.info(f"Reset rate limit {ltype.value} for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to reset rate limit {ltype.value} for user {user_id}: {e}")
                results[ltype.value] = False
        
        return results
    
    async def get_user_rate_limit_status(
        self,
        user_id: str,
        limit_type: RateLimitType = RateLimitType.USER_EVENTS,
    ) -> Dict[str, any]:
        """
        Get current rate limit status for a user without consuming a request.
        
        Args:
            user_id: User identifier
            limit_type: Type of rate limit to check
            
        Returns:
            Dictionary with rate limit status information
        """
        try:
            config = self.DEFAULT_LIMITS[limit_type]
            limit = config["limit"]
            window = config["window"]
            
            key = f"rate_limit:{limit_type.value}:user:{user_id}"
            now = time.time()
            expired_time = now - window
            
            async with self.redis_manager.get_connection() as redis_conn:
                # Remove expired entries
                await redis_conn.zremrangebyscore(key, 0, expired_time)
                
                # Get current count
                current_count = await redis_conn.zcard(key)
                
                # Get oldest entry for reset time calculation
                oldest_entries = await redis_conn.zrange(key, 0, 0, withscores=True)
                
                reset_time = now + window
                if oldest_entries:
                    oldest_timestamp = oldest_entries[0][1]
                    reset_time = oldest_timestamp + window
            
            remaining = max(0, limit - current_count)
            
            return {
                "user_id": user_id,
                "limit_type": limit_type.value,
                "limit": limit,
                "window_seconds": window,
                "current_count": current_count,
                "remaining": remaining,
                "reset_time": reset_time,
                "reset_time_iso": datetime.fromtimestamp(
                    reset_time, tz=timezone.utc
                ).isoformat(),
                "is_limited": current_count >= limit,
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status for user {user_id}: {e}")
            return {
                "error": str(e),
                "user_id": user_id,
                "limit_type": limit_type.value,
            }
    
    async def get_global_rate_limit_stats(self) -> Dict[str, any]:
        """
        Get global rate limiting statistics for monitoring.
        
        Returns:
            Dictionary with global rate limiting statistics
        """
        try:
            stats = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "limit_types": {},
                "total_active_limits": 0,
            }
            
            async with self.redis_manager.get_connection() as redis_conn:
                for limit_type in RateLimitType:
                    pattern = f"rate_limit:{limit_type.value}:user:*"
                    
                    # Count active rate limit keys
                    active_count = 0
                    total_requests = 0
                    
                    async for key in redis_conn.scan_iter(match=pattern):
                        active_count += 1
                        # Get request count for this key
                        count = await redis_conn.zcard(key)
                        total_requests += count
                    
                    stats["limit_types"][limit_type.value] = {
                        "active_users": active_count,
                        "total_requests_in_windows": total_requests,
                        "default_limit": self.DEFAULT_LIMITS[limit_type]["limit"],
                        "default_window": self.DEFAULT_LIMITS[limit_type]["window"],
                    }
                    
                    stats["total_active_limits"] += active_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get global rate limit stats: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_entries(self) -> Dict[str, int]:
        """
        Cleanup expired rate limit entries across all users.
        
        This is typically run as a background task for maintenance.
        
        Returns:
            Dictionary with cleanup statistics
        """
        cleanup_stats = {
            "keys_processed": 0,
            "entries_removed": 0,
            "keys_deleted": 0,
        }
        
        try:
            now = time.time()
            
            async with self.redis_manager.get_connection() as redis_conn:
                # Process each limit type
                for limit_type in RateLimitType:
                    pattern = f"rate_limit:{limit_type.value}:user:*"
                    window = self.DEFAULT_LIMITS[limit_type]["window"]
                    expired_time = now - window
                    
                    async for key in redis_conn.scan_iter(match=pattern):
                        cleanup_stats["keys_processed"] += 1
                        
                        # Remove expired entries
                        removed_count = await redis_conn.zremrangebyscore(
                            key, 0, expired_time
                        )
                        cleanup_stats["entries_removed"] += removed_count
                        
                        # Delete key if it's empty
                        if await redis_conn.zcard(key) == 0:
                            await redis_conn.delete(key)
                            cleanup_stats["keys_deleted"] += 1
            
            logger.info(
                f"Rate limit cleanup completed: "
                f"{cleanup_stats['keys_processed']} keys processed, "
                f"{cleanup_stats['entries_removed']} entries removed, "
                f"{cleanup_stats['keys_deleted']} empty keys deleted"
            )
            
        except Exception as e:
            logger.error(f"Rate limit cleanup failed: {e}")
            cleanup_stats["error"] = str(e)
        
        return cleanup_stats


# Convenience functions for common rate limiting operations

async def check_user_events_rate_limit(user_id: str) -> RateLimitResult:
    """Check rate limit for user events (1000/minute default)."""
    limiter = RateLimiter()
    return await limiter.check_rate_limit(user_id, RateLimitType.USER_EVENTS)


async def check_api_rate_limit(user_id: str) -> RateLimitResult:
    """Check rate limit for API requests (5000/hour default)."""
    limiter = RateLimiter()
    return await limiter.check_rate_limit(user_id, RateLimitType.API_REQUESTS)


async def check_analytics_query_rate_limit(user_id: str) -> RateLimitResult:
    """Check rate limit for analytics queries (100/minute default)."""
    limiter = RateLimiter()
    return await limiter.check_rate_limit(user_id, RateLimitType.ANALYTICS_QUERIES)


async def reset_user_rate_limits(user_id: str) -> Dict[str, bool]:
    """Reset all rate limits for a user."""
    limiter = RateLimiter()
    return await limiter.reset_user_limits(user_id)