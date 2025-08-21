"""
Rate Limit Types: Single Source of Truth for Rate Limiting Models

This module contains all rate limiting-related models and configurations used across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All rate limit model definitions MUST be imported from this module
- NO duplicate rate limit model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from app.schemas.rate_limit_types import RateLimitConfig, RateLimiter, TokenBucket

Business Value Justification (BVJ):
- Segment: All segments (prevents abuse across all user tiers)
- Business Goal: Protect infrastructure from abuse and ensure fair usage
- Value Impact: Prevents $100K+ infrastructure costs from abuse
- Revenue Impact: Maintains service quality for paying customers
"""

import time
import asyncio
from typing import Dict, List, Optional, Union, Protocol, Callable, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class RateLimitStatus(str, Enum):
    """Status of rate limit requests."""
    ALLOWED = "allowed"
    DENIED = "denied"
    WARNING = "warning"


class RateLimitScope(str, Enum):
    """Scope of rate limiting."""
    USER = "user"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"
    GLOBAL = "global"


class RateLimitConfig(BaseModel):
    """Unified rate limiter configuration."""
    name: str = Field(..., description="Rate limiter name")
    algorithm: RateLimitAlgorithm = Field(default=RateLimitAlgorithm.TOKEN_BUCKET)
    requests_per_second: float = Field(default=10.0, description="Requests per second limit")
    requests_per_minute: Optional[int] = Field(None, description="Requests per minute limit")
    requests_per_hour: Optional[int] = Field(None, description="Requests per hour limit")
    burst_capacity: int = Field(default=20, description="Maximum burst size")
    window_size: int = Field(default=60, description="Rate limiting window in seconds")
    enable_adaptive: bool = Field(default=True, description="Enable adaptive rate limiting")
    backoff_factor: float = Field(default=1.5, description="Backoff factor for adaptive limiting")
    cooldown_period: int = Field(default=60, description="Cooldown period after limit exceeded")
    scope: RateLimitScope = Field(default=RateLimitScope.USER, description="Rate limit scope")


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""
    allowed: bool = Field(..., description="Whether request is allowed")
    status: RateLimitStatus = Field(..., description="Rate limit status")
    remaining_requests: int = Field(default=0, description="Remaining requests in window")
    reset_time: Optional[datetime] = Field(None, description="When limit resets")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    message: Optional[str] = Field(None, description="Human-readable message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RateLimitEntry(BaseModel):
    """Rate limit tracking entry."""
    identifier: str = Field(..., description="Rate limit identifier (user ID, IP, etc.)")
    count: int = Field(default=0, description="Current request count")
    window_start: datetime = Field(..., description="Start of current window")
    last_request: datetime = Field(..., description="Timestamp of last request")
    total_requests: int = Field(default=0, description="Total requests ever")
    violations: int = Field(default=0, description="Number of violations")


@dataclass
class TokenBucket:
    """Token bucket rate limiter implementation."""
    capacity: float
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Consume tokens from bucket."""
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
    
    def get_available_tokens(self) -> float:
        """Get number of available tokens."""
        self._refill()
        return self.tokens
    
    def reset(self) -> None:
        """Reset bucket to full capacity."""
        self.tokens = self.capacity
        self.last_refill = time.time()


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiter implementations."""
    
    async def check_rate_limit(self, identifier: str) -> RateLimitResult:
        """Check if request should be rate limited."""
        ...
    
    async def acquire(self, identifier: str, tokens: int = 1) -> bool:
        """Acquire tokens from rate limiter."""
        ...
    
    async def reset(self, identifier: str) -> None:
        """Reset rate limiter state for identifier."""
        ...
    
    def get_stats(self, identifier: str) -> Dict[str, Union[int, float]]:
        """Get rate limiter statistics."""
        ...


class AdaptiveRateLimitConfig(BaseModel):
    """Configuration for adaptive rate limiting."""
    base_limit: float = Field(..., description="Base rate limit")
    max_limit: float = Field(..., description="Maximum rate limit")
    min_limit: float = Field(..., description="Minimum rate limit")
    adaptation_factor: float = Field(default=1.2, description="Adaptation factor")
    success_threshold: float = Field(default=0.95, description="Success rate threshold")
    adjustment_interval: int = Field(default=300, description="Adjustment interval in seconds")
    recovery_rate: float = Field(default=0.1, description="Recovery rate per interval")


class RateLimitViolation(BaseModel):
    """Record of rate limit violation."""
    identifier: str = Field(..., description="Rate limit identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    limit_exceeded: str = Field(..., description="Which limit was exceeded")
    actual_rate: float = Field(..., description="Actual request rate")
    configured_limit: float = Field(..., description="Configured rate limit")
    action_taken: str = Field(..., description="Action taken (blocked, throttled, etc.)")
    severity: str = Field(default="medium", description="Violation severity")


class RateLimitMetrics(BaseModel):
    """Metrics for rate limiting."""
    total_requests: int = Field(default=0, description="Total requests processed")
    allowed_requests: int = Field(default=0, description="Requests allowed")
    denied_requests: int = Field(default=0, description="Requests denied")
    violations: int = Field(default=0, description="Rate limit violations")
    average_rate: float = Field(default=0.0, description="Average request rate")
    peak_rate: float = Field(default=0.0, description="Peak request rate")
    active_identifiers: int = Field(default=0, description="Number of active identifiers")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size: int, bucket_size: int = 60):
        self.window_size = window_size
        self.bucket_size = bucket_size
        self.buckets: Dict[int, int] = defaultdict(int)
    
    def add_request(self, timestamp: float) -> None:
        """Add a request at given timestamp."""
        bucket = int(timestamp // self.bucket_size)
        self.buckets[bucket] += 1
    
    def get_count(self, timestamp: float) -> int:
        """Get request count in sliding window."""
        current_bucket = int(timestamp // self.bucket_size)
        cutoff = self._calculate_cutoff_bucket(current_bucket)
        return self._sum_valid_buckets(cutoff)
        
    def _calculate_cutoff_bucket(self, current_bucket: int) -> int:
        """Calculate cutoff bucket for sliding window."""
        return current_bucket - (self.window_size // self.bucket_size)
        
    def _sum_valid_buckets(self, cutoff: int) -> int:
        """Sum requests from valid buckets within window."""
        return sum(requests for bucket, requests in self.buckets.items() if bucket > cutoff)
    
    def cleanup(self, timestamp: float) -> None:
        """Clean up old buckets."""
        current_bucket = int(timestamp // self.bucket_size)
        cutoff = current_bucket - (self.window_size // self.bucket_size) - 1
        
        expired = [b for b in self.buckets.keys() if b < cutoff]
        for bucket in expired:
            del self.buckets[bucket]


class RateLimitMiddlewareConfig(BaseModel):
    """Configuration for rate limiting middleware."""
    enabled: bool = Field(default=True, description="Enable rate limiting")
    default_limits: Dict[str, int] = Field(default_factory=dict, description="Default limits per endpoint")
    user_limits: Dict[str, int] = Field(default_factory=dict, description="Per-user limits")
    ip_limits: Dict[str, int] = Field(default_factory=dict, description="Per-IP limits")
    bypass_keys: List[str] = Field(default_factory=list, description="API keys that bypass limits")
    error_message: str = Field(default="Rate limit exceeded", description="Error message for violations")
    headers_enabled: bool = Field(default=True, description="Include rate limit headers")


# Export all rate limit types
__all__ = [
    "RateLimitAlgorithm",
    "RateLimitStatus",
    "RateLimitScope",
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimitEntry",
    "TokenBucket",
    "RateLimiterProtocol",
    "AdaptiveRateLimitConfig",
    "RateLimitViolation",
    "RateLimitMetrics",
    "SlidingWindowCounter",
    "RateLimitMiddlewareConfig"
]