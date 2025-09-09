"""Rate Limiting Service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide rate limiting service functionality for tests
- Value Impact: Ensures rate limiting service tests can execute
- Strategic Impact: Enables comprehensive rate limiting validation
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Union

from netra_backend.app.services.rate_limiting.rate_limiter import (
    RateLimiter,
    RateLimitStrategy,
    RateLimitConfig,
    TokenBucket
)


class RateLimitServiceConfig(NamedTuple):
    """Configuration for rate limiting service."""
    requests_per_second: int = 10
    burst_size: int = 20


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int = 0
    reset_time: Optional[datetime] = None
    retry_after: int = 0
    limit_type: str = "default"


class RateLimitingService:
    """Service for managing rate limits across the application."""
    
    def __init__(self):
        """Initialize rate limiting service."""
        self._limiters: Dict[str, RateLimiter] = {}
        self._default_limiter = RateLimiter()
        
    def add_limiter(self, name: str, config: RateLimitConfig) -> None:
        """Add a named rate limiter."""
        self._limiters[name] = RateLimiter(config)
    
    def get_limiter(self, name: str) -> RateLimiter:
        """Get a named rate limiter."""
        return self._limiters.get(name, self._default_limiter)
    
    async def check_limit(
        self, 
        identifier: str, 
        limiter_name: str = "default",
        tokens: int = 1
    ) -> RateLimitResult:
        """Check rate limit for an identifier."""
        limiter = self.get_limiter(limiter_name)
        result = await limiter.check_rate_limit(identifier, tokens)
        
        return RateLimitResult(
            allowed=result["allowed"],
            remaining=result["remaining_tokens"],
            reset_time=datetime.fromtimestamp(result["reset_time"]) if result.get("reset_time") else None,
            retry_after=result["retry_after"],
            limit_type=limiter_name
        )
    
    async def is_allowed(
        self, 
        identifier: str, 
        limiter_name: str = "default",
        tokens: int = 1
    ) -> bool:
        """Simple check if request is allowed."""
        limiter = self.get_limiter(limiter_name)
        return await limiter.is_allowed(identifier, tokens)
    
    async def reset_limits(
        self, 
        identifier: Optional[str] = None,
        limiter_name: Optional[str] = None
    ) -> None:
        """Reset rate limits."""
        if limiter_name:
            limiter = self.get_limiter(limiter_name)
            await limiter.reset_limits(identifier)
        else:
            # Reset all limiters
            for limiter in self._limiters.values():
                await limiter.reset_limits(identifier)
            await self._default_limiter.reset_limits(identifier)
    
    def get_limiter_names(self) -> List[str]:
        """Get names of all configured limiters."""
        return list(self._limiters.keys())


# Global service instance
rate_limiting_service = RateLimitingService()