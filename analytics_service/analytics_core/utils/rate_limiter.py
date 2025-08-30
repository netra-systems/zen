"""
Rate Limiter Utility
Simple rate limiting implementation for analytics service
"""
from typing import Optional, Callable
import logging
import time

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self, requests_per_minute: int = 60, redis_connection: Optional[Callable] = None):
        """Initialize rate limiter."""
        self.requests_per_minute = requests_per_minute
        self.redis_connection = redis_connection
        self.local_cache = {}
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        try:
            current_time = time.time()
            minute_window = int(current_time // 60)
            
            # Use local cache for simplicity
            cache_key = f"{key}:{minute_window}"
            
            if cache_key not in self.local_cache:
                self.local_cache[cache_key] = 0
            
            if self.local_cache[cache_key] >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for {key}")
                return False
            
            self.local_cache[cache_key] += 1
            
            # Clean old entries
            self._cleanup_cache(minute_window)
            
            return True
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # Fail open
    
    def _cleanup_cache(self, current_window: int):
        """Clean up old cache entries."""
        try:
            keys_to_remove = []
            for key in self.local_cache:
                if ':' in key:
                    window = int(key.split(':')[-1])
                    if window < current_window - 5:  # Keep last 5 minutes
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.local_cache[key]
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")