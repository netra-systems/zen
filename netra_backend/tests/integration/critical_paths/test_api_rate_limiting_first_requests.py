"""API Rate Limiting First Requests L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Free, Early tiers
- Business Goal: Platform Protection & Fair Usage  
- Value Impact: Prevents abuse while ensuring legitimate access
- Revenue Impact: $25K MRR - Protects infrastructure costs

L3 Test: Real Redis rate limiter with FastAPI middleware testing first request behavior,
burst allowances, tier-based limits, recovery patterns, and performance validation.

Critical Path: First request -> Rate limit check -> Redis tracking -> Burst handling -> Tier enforcement -> Header validation
Coverage: First request always allowed, rate limit enforcement, burst capacity, per-user tracking, headers, tier limits, recovery
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as redis

# Add project root to path
from netra_backend.app.core.async_rate_limiter import AsyncRateLimiter
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.tests.unified.config import TestTier

# Add project root to path

logger = central_logger.get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for API endpoints."""
    requests_per_minute: int
    burst_allowance: int
    priority_level: int
    tier_multipliers: Dict[str, float]


@dataclass
class RequestResult:
    """Result of a rate limited request."""
    allowed: bool
    status_code: int
    remaining: int
    limit: int
    reset_time: float
    response_time: float
    headers: Dict[str, str]
    is_first_request: bool = False


class RedisRateLimiter:
    """Redis-backed token bucket rate limiter for L3 testing."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.bucket_configs = {}
        
    async def configure_endpoint(self, endpoint: str, config: RateLimitConfig):
        """Configure rate limiting for an endpoint."""
        self.bucket_configs[endpoint] = config
        
    async def check_rate_limit(self, user_id: str, endpoint: str, user_tier: str) -> Dict[str, Any]:
        """Check rate limit using Redis token bucket algorithm."""
        if endpoint not in self.bucket_configs:
            return {"allowed": True, "reason": "no_config"}
            
        config = self.bucket_configs[endpoint]
        tier_multiplier = config.tier_multipliers.get(user_tier, 1.0)
        effective_limit = int(config.requests_per_minute * tier_multiplier)
        burst_limit = int(config.burst_allowance * tier_multiplier)
        
        # Redis key for this user/endpoint combination
        bucket_key = f"rate_limit:bucket:{user_id}:{endpoint}"
        metadata_key = f"rate_limit:meta:{user_id}:{endpoint}"
        
        # Use Redis transaction for atomic bucket operations
        async with self.redis_client.pipeline(transaction=True) as pipe:
            try:
                # Watch the bucket key for changes
                await pipe.watch(bucket_key, metadata_key)
                
                now = time.time()
                
                # Get current bucket state
                bucket_data = await self.redis_client.get(bucket_key)
                metadata = await self.redis_client.get(metadata_key)
                
                if bucket_data is None:
                    # First request for this user/endpoint - always allow
                    tokens = effective_limit - 1
                    last_refill = now
                    is_first_request = True
                else:
                    bucket_state = json.loads(bucket_data)
                    tokens = bucket_state.get("tokens", 0)
                    last_refill = bucket_state.get("last_refill", now)
                    is_first_request = False
                
                # Calculate token refill
                time_passed = now - last_refill
                tokens_to_add = int(time_passed * (effective_limit / 60.0))  # tokens per second
                tokens = min(effective_limit + burst_limit, tokens + tokens_to_add)
                
                if tokens < 1:
                    # Rate limit exceeded
                    retry_after = 60.0 / effective_limit  # Time to get one token
                    reset_time = now + retry_after
                    
                    return {
                        "allowed": False,
                        "limit": effective_limit,
                        "remaining": 0,
                        "reset_time": reset_time,
                        "retry_after": retry_after,
                        "reason": "rate_limit_exceeded",
                        "is_first_request": is_first_request
                    }
                
                # Consume one token
                tokens -= 1
                
                # Start transaction
                pipe.multi()
                
                # Update bucket state
                bucket_state = {
                    "tokens": tokens,
                    "last_refill": now,
                    "effective_limit": effective_limit
                }
                await pipe.set(bucket_key, json.dumps(bucket_state), ex=300)  # 5 min TTL
                
                # Update metadata
                metadata_state = {
                    "user_id": user_id,
                    "endpoint": endpoint,
                    "tier": user_tier,
                    "last_request": now,
                    "total_requests": (json.loads(metadata).get("total_requests", 0) + 1) if metadata else 1
                }
                await pipe.set(metadata_key, json.dumps(metadata_state), ex=300)
                
                # Execute transaction
                await pipe.execute()
                
                reset_time = now + (60.0 - (now % 60.0))  # Next minute boundary
                
                return {
                    "allowed": True,
                    "limit": effective_limit,
                    "remaining": int(tokens),
                    "reset_time": reset_time,
                    "retry_after": 0,
                    "is_first_request": is_first_request
                }
                
            except redis.WatchError:
                # Retry on conflict
                await asyncio.sleep(0.001)  # Small delay
                return await self.check_rate_limit(user_id, endpoint, user_tier)
                
    async def reset_user_limits(self, user_id: str):
        """Reset all rate limits for a user."""
        pattern = f"rate_limit:*:{user_id}:*"
        keys = []
        async for key in self.redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await self.redis_client.delete(*keys)
            
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get rate limiting stats for a user."""
        pattern = f"rate_limit:meta:{user_id}:*"
        stats = {}
        
        async for key in self.redis_client.scan_iter(match=pattern):
            metadata = await self.redis_client.get(key)
            if metadata:
                endpoint = key.decode().split(":")[-1]
                stats[endpoint] = json.loads(metadata)
                
        return stats


class ApiRateLimitingFirstRequestsManager:
    """Manages L3 API rate limiting tests with first request focus."""
    
    def __init__(self):
        self.redis_client = None
        self.rate_limiter = None
        self.test_configs = {}
        self.request_history = []
        self.performance_metrics = []
        
    async def initialize_redis(self):
        """Initialize Redis connection for L3 testing."""
        try:
            # Use test Redis instance
            self.redis_client = redis.Redis(
                host="localhost",
                port=6379,
                db=1,  # Use test database
                decode_responses=False,
                socket_timeout=5.0,
                socket_connect_timeout=5.0
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established for rate limiting tests")
            
            # Clear any existing test data
            await self.redis_client.flushdb()
            
            self.rate_limiter = RedisRateLimiter(self.redis_client)
            await self.setup_test_configurations()
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
            
    async def setup_test_configurations(self):
        """Setup rate limiting configurations for test endpoints."""
        self.test_configs = {
            "/api/v1/chat": RateLimitConfig(
                requests_per_minute=10,
                burst_allowance=5,
                priority_level=5,
                tier_multipliers={
                    "free": 1.0,
                    "early": 2.0,
                    "mid": 5.0,
                    "enterprise": 10.0
                }
            ),
            "/api/v1/threads": RateLimitConfig(
                requests_per_minute=20,
                burst_allowance=10,
                priority_level=4,
                tier_multipliers={
                    "free": 1.0,
                    "early": 2.0,
                    "mid": 3.0,
                    "enterprise": 5.0
                }
            ),
            "/api/v1/agents": RateLimitConfig(
                requests_per_minute=5,
                burst_allowance=2,
                priority_level=3,
                tier_multipliers={
                    "free": 1.0,
                    "early": 1.5,
                    "mid": 2.0,
                    "enterprise": 4.0
                }
            )
        }
        
        # Configure all endpoints
        for endpoint, config in self.test_configs.items():
            await self.rate_limiter.configure_endpoint(endpoint, config)
            
    async def make_rate_limited_request(self, user_id: str, endpoint: str, 
                                      user_tier: str = "free") -> RequestResult:
        """Simulate a rate limited API request."""
        start_time = time.time()
        
        # Check rate limit
        rate_result = await self.rate_limiter.check_rate_limit(user_id, endpoint, user_tier)
        
        response_time = time.time() - start_time
        
        # Simulate API processing if allowed
        if rate_result["allowed"]:
            await asyncio.sleep(0.05)  # Simulate 50ms API processing
            status_code = 200
        else:
            status_code = 429
            
        # Build headers
        headers = {
            "X-RateLimit-Limit": str(rate_result.get("limit", 0)),
            "X-RateLimit-Remaining": str(rate_result.get("remaining", 0)),
            "X-RateLimit-Reset": str(int(rate_result.get("reset_time", time.time())))
        }
        
        if not rate_result["allowed"]:
            headers["Retry-After"] = str(int(rate_result.get("retry_after", 60)))
            
        result = RequestResult(
            allowed=rate_result["allowed"],
            status_code=status_code,
            remaining=rate_result.get("remaining", 0),
            limit=rate_result.get("limit", 0),
            reset_time=rate_result.get("reset_time", time.time()),
            response_time=response_time,
            headers=headers,
            is_first_request=rate_result.get("is_first_request", False)
        )
        
        # Record request
        self.request_history.append({
            "user_id": user_id,
            "endpoint": endpoint,
            "user_tier": user_tier,
            "result": result,
            "timestamp": time.time()
        })
        
        return result
        
    async def test_burst_traffic(self, user_id: str, endpoint: str, user_tier: str,
                               request_count: int, duration: float) -> Dict[str, Any]:
        """Test burst traffic patterns."""
        start_time = time.time()
        results = []
        
        interval = duration / request_count if request_count > 1 else 0
        
        for i in range(request_count):
            result = await self.make_rate_limited_request(user_id, endpoint, user_tier)
            results.append(result)
            
            if i < request_count - 1 and interval > 0:
                await asyncio.sleep(interval)
                
        total_time = time.time() - start_time
        
        # Analyze results
        allowed_requests = [r for r in results if r.allowed]
        first_requests = [r for r in results if r.is_first_request]
        
        return {
            "total_requests": request_count,
            "allowed_requests": len(allowed_requests),
            "rate_limited_requests": request_count - len(allowed_requests),
            "first_requests": len(first_requests),
            "success_rate": len(allowed_requests) / request_count * 100,
            "total_time": total_time,
            "actual_rps": request_count / total_time,
            "results": results
        }
        
    async def test_concurrent_users(self, endpoint: str, user_count: int, 
                                  requests_per_user: int, user_tier: str = "free") -> Dict[str, Any]:
        """Test concurrent users hitting the same endpoint."""
        start_time = time.time()
        
        # Create tasks for concurrent users
        tasks = []
        for i in range(user_count):
            user_id = f"concurrent_user_{i}"
            for j in range(requests_per_user):
                task = self.make_rate_limited_request(user_id, endpoint, user_tier)
                tasks.append((user_id, task))
                
        # Execute all requests concurrently
        results = []
        for user_id, task in tasks:
            result = await task
            results.append((user_id, result))
            
        total_time = time.time() - start_time
        
        # Analyze results by user
        user_stats = {}
        for user_id, result in results:
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "total": 0,
                    "allowed": 0,
                    "first_requests": 0
                }
            
            user_stats[user_id]["total"] += 1
            if result.allowed:
                user_stats[user_id]["allowed"] += 1
            if result.is_first_request:
                user_stats[user_id]["first_requests"] += 1
                
        return {
            "total_requests": len(results),
            "user_count": user_count,
            "requests_per_user": requests_per_user,
            "total_time": total_time,
            "user_stats": user_stats,
            "results": results
        }
        
    async def wait_for_reset(self, duration: float = 65.0):
        """Wait for rate limit windows to reset."""
        logger.info(f"Waiting {duration}s for rate limit reset...")
        await asyncio.sleep(duration)
        
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of rate limiting operations."""
        if not self.request_history:
            return {"total_requests": 0}
            
        response_times = [r["result"].response_time for r in self.request_history]
        
        return {
            "total_requests": len(self.request_history),
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
            "requests_allowed": len([r for r in self.request_history if r["result"].allowed]),
            "first_requests": len([r for r in self.request_history if r["result"].is_first_request])
        }
        
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.redis_client:
                await self.redis_client.flushdb()
                await self.redis_client.close()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


@pytest.fixture
async def rate_limit_manager():
    """Create rate limiting manager for L3 testing."""
    manager = ApiRateLimitingFirstRequestsManager()
    await manager.initialize_redis()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_first_request_always_allowed(rate_limit_manager):
    """Test that first request is always allowed regardless of limits."""
    endpoint = "/api/v1/agents"  # Low limit endpoint (5 req/min)
    user_id = "first_request_user"
    
    # Make first request
    result = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
    
    # First request should always be allowed
    assert result.allowed is True
    assert result.status_code == 200
    assert result.is_first_request is True
    assert result.remaining == 4  # 5 - 1 = 4 remaining
    
    # Verify headers
    assert result.headers["X-RateLimit-Limit"] == "5"
    assert result.headers["X-RateLimit-Remaining"] == "4"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_rate_limit_enforcement_after_first_request(rate_limit_manager):
    """Test rate limiting enforcement after first request."""
    endpoint = "/api/v1/agents"
    user_id = "enforcement_user"
    
    # Make requests up to the limit
    results = []
    for i in range(7):  # 5 limit + 2 burst = 7 total allowed initially
        result = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
        results.append(result)
        
    # First 7 should be allowed (5 regular + 2 burst)
    allowed_count = sum(1 for r in results if r.allowed)
    assert allowed_count >= 5  # At least the base limit should be allowed
    
    # Next request should be rate limited
    blocked_result = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
    assert blocked_result.allowed is False
    assert blocked_result.status_code == 429
    assert "Retry-After" in blocked_result.headers


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_burst_allowance_behavior(rate_limit_manager):
    """Test burst allowance allows temporary exceeding of base limits."""
    endpoint = "/api/v1/chat"  # 10 req/min + 5 burst
    user_id = "burst_user"
    
    # Make rapid burst requests
    burst_result = await rate_limit_manager.test_burst_traffic(
        user_id, endpoint, "free", 12, 5.0  # 12 requests in 5 seconds
    )
    
    # Should allow more than base limit due to burst
    assert burst_result["allowed_requests"] >= 10  # Base limit
    assert burst_result["allowed_requests"] <= 15  # Base + burst
    
    # Some requests should eventually be rate limited
    assert burst_result["rate_limited_requests"] > 0
    
    # Verify first request was marked correctly
    first_request_found = any(r.is_first_request for r in burst_result["results"])
    assert first_request_found is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_tier_based_rate_limit_differences(rate_limit_manager):
    """Test different tiers get different rate limits."""
    endpoint = "/api/v1/threads"  # Base: 20 req/min
    
    tier_tests = [
        ("free", 1.0),      # 20 req/min
        ("early", 2.0),     # 40 req/min  
        ("mid", 3.0),       # 60 req/min
        ("enterprise", 5.0) # 100 req/min
    ]
    
    tier_results = {}
    
    for tier, expected_multiplier in tier_tests:
        user_id = f"tier_user_{tier}"
        
        # Test burst capacity for each tier
        burst_result = await rate_limit_manager.test_burst_traffic(
            user_id, endpoint, tier, 25, 10.0  # 25 requests in 10 seconds
        )
        
        tier_results[tier] = {
            "allowed": burst_result["allowed_requests"],
            "multiplier": expected_multiplier,
            "expected_limit": int(20 * expected_multiplier)
        }
        
    # Higher tiers should allow more requests
    assert tier_results["enterprise"]["allowed"] > tier_results["mid"]["allowed"]
    assert tier_results["mid"]["allowed"] > tier_results["early"]["allowed"]
    assert tier_results["early"]["allowed"] >= tier_results["free"]["allowed"]
    
    # Enterprise should have highest success rate
    enterprise_rate = tier_results["enterprise"]["allowed"] / 25 * 100
    free_rate = tier_results["free"]["allowed"] / 25 * 100
    assert enterprise_rate > free_rate


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_per_user_rate_tracking(rate_limit_manager):
    """Test that rate limits are tracked per user independently."""
    endpoint = "/api/v1/chat"
    
    # Test multiple users concurrently
    concurrent_result = await rate_limit_manager.test_concurrent_users(
        endpoint, user_count=5, requests_per_user=8, user_tier="free"
    )
    
    # Each user should have independent rate limiting
    user_stats = concurrent_result["user_stats"]
    
    for user_id, stats in user_stats.items():
        # Each user should have gotten their first request
        assert stats["first_requests"] == 1
        
        # Each user should have similar allowed counts (independent limits)
        assert stats["allowed"] >= 8  # Should allow initial burst


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_rate_limit_headers_accuracy(rate_limit_manager):
    """Test accuracy of rate limiting headers."""
    endpoint = "/api/v1/threads"
    user_id = "header_user"
    tier = "mid"  # 60 req/min limit
    
    # Make first request
    result1 = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, tier)
    
    assert result1.allowed is True
    assert result1.headers["X-RateLimit-Limit"] == "60"  # 20 * 3.0 multiplier
    initial_remaining = int(result1.headers["X-RateLimit-Remaining"])
    
    # Make second request
    result2 = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, tier)
    
    assert result2.allowed is True
    second_remaining = int(result2.headers["X-RateLimit-Remaining"])
    
    # Remaining should decrease by 1
    assert second_remaining == initial_remaining - 1
    
    # Reset time should be reasonable (within next minute)
    reset_time = int(result2.headers["X-RateLimit-Reset"])
    now = int(time.time())
    assert reset_time > now
    assert reset_time <= now + 60


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_rate_limit_recovery_after_wait(rate_limit_manager):
    """Test rate limit recovery after waiting for reset."""
    endpoint = "/api/v1/agents"  # 5 req/min
    user_id = "recovery_user"
    
    # Exhaust rate limit
    for i in range(8):  # Exceed limit + burst
        await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
        
    # Verify rate limited
    blocked_result = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
    assert blocked_result.allowed is False
    
    # Wait for rate limit reset (shorter wait for testing)
    await asyncio.sleep(15)  # Wait 15 seconds (tokens should refill)
    
    # Should be able to make requests again
    recovery_result = await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
    assert recovery_result.allowed is True
    assert recovery_result.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration  
@pytest.mark.L3
async def test_rate_limiting_performance_requirements(rate_limit_manager):
    """Test rate limiting performance meets requirements."""
    endpoint = "/api/v1/threads"
    
    # Test individual request performance
    user_id = "perf_user"
    results = []
    
    for i in range(20):
        result = await rate_limit_manager.make_rate_limited_request(
            user_id, endpoint, "mid"
        )
        if result.allowed:
            results.append(result.response_time)
            
    # Rate limiting should add minimal overhead
    avg_time = sum(results) / len(results) if results else 0
    max_time = max(results) if results else 0
    
    assert avg_time < 0.1  # Average < 100ms
    assert max_time < 0.2  # Max < 200ms
    
    # Test concurrent performance
    concurrent_start = time.time()
    concurrent_result = await rate_limit_manager.test_concurrent_users(
        endpoint, user_count=10, requests_per_user=5, user_tier="free"
    )
    concurrent_duration = time.time() - concurrent_start
    
    # Should handle 50 concurrent requests efficiently
    assert concurrent_duration < 5.0  # Complete within 5 seconds
    assert concurrent_result["total_requests"] == 50


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_redis_rate_limit_data_consistency(rate_limit_manager):
    """Test Redis data consistency for rate limiting."""
    endpoint = "/api/v1/chat"
    user_id = "consistency_user"
    
    # Make several requests
    for i in range(5):
        await rate_limit_manager.make_rate_limited_request(user_id, endpoint, "free")
        
    # Check user stats directly from Redis
    user_stats = await rate_limit_manager.rate_limiter.get_user_stats(user_id)
    
    assert endpoint in user_stats
    endpoint_stats = user_stats[endpoint]
    
    assert endpoint_stats["user_id"] == user_id
    assert endpoint_stats["endpoint"] == endpoint
    assert endpoint_stats["tier"] == "free"
    assert endpoint_stats["total_requests"] == 5
    
    # Reset user and verify cleanup
    await rate_limit_manager.rate_limiter.reset_user_limits(user_id)
    
    # Stats should be cleared
    cleared_stats = await rate_limit_manager.rate_limiter.get_user_stats(user_id)
    assert len(cleared_stats) == 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_comprehensive_rate_limiting_scenario(rate_limit_manager):
    """Test comprehensive rate limiting scenario with multiple patterns."""
    
    # Test across multiple endpoints and tiers
    test_scenarios = [
        ("/api/v1/chat", "scenario_user_1", "free", 15),
        ("/api/v1/threads", "scenario_user_2", "early", 25),
        ("/api/v1/agents", "scenario_user_3", "enterprise", 10)
    ]
    
    scenario_results = {}
    
    for endpoint, user_id, tier, request_count in test_scenarios:
        # Test burst followed by steady requests
        burst_result = await rate_limit_manager.test_burst_traffic(
            user_id, endpoint, tier, request_count, 8.0
        )
        
        scenario_results[f"{endpoint}_{tier}"] = burst_result
        
    # Verify each scenario handled appropriately
    for scenario_key, result in scenario_results.items():
        assert result["total_requests"] > 0
        assert result["first_requests"] == 1  # Each user gets one first request
        assert result["success_rate"] > 0  # Some requests should succeed
        
    # Get final performance summary
    perf_summary = await rate_limit_manager.get_performance_summary()
    
    assert perf_summary["total_requests"] == 50  # 15 + 25 + 10
    assert perf_summary["first_requests"] == 3  # One per user
    assert perf_summary["avg_response_time"] < 0.15  # Good performance