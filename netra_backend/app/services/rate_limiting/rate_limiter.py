"""Rate Limiter Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic rate limiting functionality for tests
- Value Impact: Ensures rate limiting tests can execute without import errors
- Strategic Impact: Enables rate limiting functionality validation
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    window_size_seconds: int = 60


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float = field(default_factory=lambda: 0)
    last_refill: float = field(default_factory=time.time)
    refill_rate: float = 1.0  # tokens per second
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from the bucket."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter."""
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, identifier: str, tokens: int = 1) -> bool:
        """Check if request is allowed under rate limit."""
        async with self._lock:
            bucket = self._get_bucket(identifier)
            return bucket.consume(tokens)
    
    async def check_rate_limit(self, identifier: str, tokens: int = 1) -> Dict[str, Any]:
        """Check rate limit and return status."""
        allowed = await self.is_allowed(identifier, tokens)
        bucket = self._get_bucket(identifier)
        
        return {
            "allowed": allowed,
            "remaining_tokens": int(bucket.tokens),
            "reset_time": bucket.last_refill + (bucket.capacity / bucket.refill_rate),
            "retry_after": 0 if allowed else int((tokens - bucket.tokens) / bucket.refill_rate)
        }
    
    def _get_bucket(self, identifier: str) -> TokenBucket:
        """Get or create token bucket for identifier."""
        if identifier not in self._buckets:
            self._buckets[identifier] = TokenBucket(
                capacity=self.config.burst_size,
                tokens=self.config.burst_size,
                refill_rate=self.config.requests_per_second
            )
        return self._buckets[identifier]
    
    async def reset_limits(self, identifier: Optional[str] = None) -> None:
        """Reset rate limits for identifier or all."""
        async with self._lock:
            if identifier:
                self._buckets.pop(identifier, None)
            else:
                self._buckets.clear()


# Singleton instance for global use
default_rate_limiter = RateLimiter()