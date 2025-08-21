"""Rate Limiting with Token Bucket Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (resource protection for all users)
- Business Goal: Prevent resource abuse and ensure fair usage
- Value Impact: Protects $5K MRR from resource abuse and system overload
- Strategic Impact: Enables sustainable scaling and prevents service degradation

Critical Path: Request arrival -> Token bucket check -> Rate limit enforcement -> Request processing/rejection
Coverage: Token bucket algorithm, rate limiting enforcement, burst handling, fair usage
"""

import pytest
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.monitoring.rate_limiter import GCPRateLimiter
from redis_manager import RedisManager
import redis.asyncio as redis
from unittest.mock import MagicMock, AsyncMock

# Add project root to path

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation for testing."""
    
    def __init__(self, requests_per_second: int = 10, burst_capacity: int = 20):
        self.requests_per_second = requests_per_second
        self.burst_capacity = burst_capacity
        self.tokens = burst_capacity
        self.last_refill = time.time()
        self.token_buckets = {}  # Per-identifier buckets
        
    def _refill_tokens(self, identifier: str):
        """Refill tokens based on elapsed time."""
        now = time.time()
        bucket = self.token_buckets.get(identifier, {
            "tokens": self.burst_capacity,
            "last_refill": now
        })
        
        elapsed = now - bucket["last_refill"]
        tokens_to_add = elapsed * self.requests_per_second
        bucket["tokens"] = min(self.burst_capacity, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now
        
        self.token_buckets[identifier] = bucket
        return bucket
    
    async def check_rate_limit(self, identifier: str) -> Dict[str, Any]:
        """Check if request is allowed under rate limit."""
        bucket = self._refill_tokens(identifier)
        
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return {
                "allowed": True,
                "remaining_tokens": bucket["tokens"],
                "reset_time": bucket["last_refill"] + (self.burst_capacity / self.requests_per_second)
            }
        else:
            return {
                "allowed": False,
                "remaining_tokens": 0,
                "reset_time": bucket["last_refill"] + (1 / self.requests_per_second)
            }
    
    async def configure_limit(self, identifier: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure rate limit for identifier."""
        self.token_buckets[identifier] = {
            "tokens": config.get("burst_capacity", self.burst_capacity),
            "last_refill": time.time(),
            "requests_per_second": config.get("requests_per_second", self.requests_per_second),
            "burst_capacity": config.get("burst_capacity", self.burst_capacity)
        }
        return {"success": True}
    
    async def clear_rate_limit(self, identifier: str):
        """Clear rate limit for identifier."""
        if identifier in self.token_buckets:
            del self.token_buckets[identifier]


class RateLimitingManager:
    """Manages rate limiting testing with token bucket algorithm."""
    
    def __init__(self):
        self.rate_limiter = None
        self.redis_manager = None
        self.gcp_rate_limiter = None
        self.rate_limit_events = []
        self.request_history = []
        
    async def initialize_services(self):
        """Initialize rate limiting services."""
        self.rate_limiter = TokenBucketRateLimiter()
        
        # Initialize Redis manager for distributed rate limiting
        self.redis_manager = RedisManager()
        await self.redis_manager.initialize()
        
        # Initialize GCP rate limiter for monitoring
        self.gcp_rate_limiter = GCPRateLimiter()
    
    async def configure_rate_limit(self, identifier: str, requests_per_second: int,
                                 burst_capacity: int) -> Dict[str, Any]:
        """Configure rate limit for identifier."""
        config_start = time.time()
        
        config_result = await self.rate_limiter.configure_limit(
            identifier, 
            {
                "requests_per_second": requests_per_second,
                "burst_capacity": burst_capacity,
                "algorithm": "token_bucket"
            }
        )
        
        return {
            "identifier": identifier,
            "config": {
                "requests_per_second": requests_per_second,
                "burst_capacity": burst_capacity
            },
            "config_time": time.time() - config_start,
            "success": config_result.get("success", False)
        }
    
    async def make_rate_limited_request(self, identifier: str, request_id: str = None) -> Dict[str, Any]:
        """Make a rate-limited request and check if allowed."""
        request_start = time.time()
        
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"
        
        # Check rate limit
        rate_check = await self.rate_limiter.check_rate_limit(identifier)
        
        request_record = {
            "request_id": request_id,
            "identifier": identifier,
            "allowed": rate_check.get("allowed", False),
            "remaining_tokens": rate_check.get("remaining_tokens", 0),
            "reset_time": rate_check.get("reset_time", 0),
            "request_time": time.time() - request_start,
            "timestamp": time.time()
        }
        
        self.request_history.append(request_record)
        
        # Record rate limit event if blocked
        if not request_record["allowed"]:
            rate_limit_event = {
                "identifier": identifier,
                "blocked_request_id": request_id,
                "remaining_tokens": request_record["remaining_tokens"],
                "timestamp": time.time()
            }
            self.rate_limit_events.append(rate_limit_event)
        
        return request_record
    
    async def test_burst_capacity(self, identifier: str, burst_size: int) -> Dict[str, Any]:
        """Test burst capacity handling."""
        burst_start = time.time()
        
        # Make burst of requests simultaneously
        burst_tasks = []
        for i in range(burst_size):
            task = self.make_rate_limited_request(identifier, f"burst_req_{i}")
            burst_tasks.append(task)
        
        burst_results = await asyncio.gather(*burst_tasks)
        
        allowed_requests = [r for r in burst_results if r["allowed"]]
        blocked_requests = [r for r in burst_results if not r["allowed"]]
        
        return {
            "burst_size": burst_size,
            "allowed_count": len(allowed_requests),
            "blocked_count": len(blocked_requests),
            "burst_time": time.time() - burst_start,
            "results": burst_results
        }
    
    async def test_sustained_rate_limiting(self, identifier: str, duration_seconds: int,
                                         request_interval: float) -> Dict[str, Any]:
        """Test sustained rate limiting over time."""
        test_start = time.time()
        sustained_results = []
        
        end_time = test_start + duration_seconds
        request_count = 0
        
        while time.time() < end_time:
            request_result = await self.make_rate_limited_request(
                identifier, f"sustained_req_{request_count}"
            )
            sustained_results.append(request_result)
            request_count += 1
            
            await asyncio.sleep(request_interval)
        
        allowed_requests = [r for r in sustained_results if r["allowed"]]
        blocked_requests = [r for r in sustained_results if not r["allowed"]]
        
        return {
            "duration": duration_seconds,
            "total_requests": len(sustained_results),
            "allowed_count": len(allowed_requests),
            "blocked_count": len(blocked_requests),
            "average_rate": len(allowed_requests) / duration_seconds,
            "test_time": time.time() - test_start
        }
    
    async def test_multi_identifier_isolation(self, identifiers: List[str],
                                            requests_per_identifier: int) -> Dict[str, Any]:
        """Test isolation between different identifiers."""
        isolation_start = time.time()
        
        # Make requests for each identifier concurrently
        all_tasks = []
        for identifier in identifiers:
            for i in range(requests_per_identifier):
                task = self.make_rate_limited_request(
                    identifier, f"{identifier}_req_{i}"
                )
                all_tasks.append(task)
        
        all_results = await asyncio.gather(*all_tasks)
        
        # Group results by identifier
        results_by_identifier = {}
        for result in all_results:
            identifier = result["identifier"]
            if identifier not in results_by_identifier:
                results_by_identifier[identifier] = []
            results_by_identifier[identifier].append(result)
        
        # Analyze isolation
        isolation_analysis = {}
        for identifier, results in results_by_identifier.items():
            allowed = [r for r in results if r["allowed"]]
            blocked = [r for r in results if not r["allowed"]]
            
            isolation_analysis[identifier] = {
                "total_requests": len(results),
                "allowed_count": len(allowed),
                "blocked_count": len(blocked),
                "success_rate": len(allowed) / len(results) if results else 0
            }
        
        return {
            "identifiers": identifiers,
            "results_by_identifier": isolation_analysis,
            "isolation_time": time.time() - isolation_start,
            "properly_isolated": len(set(
                analysis["success_rate"] for analysis in isolation_analysis.values()
            )) > 1  # Different success rates indicate proper isolation
        }
    
    async def cleanup(self):
        """Clean up rate limiting test resources."""
        # Clear rate limit configurations
        for event in self.rate_limit_events:
            await self.rate_limiter.clear_rate_limit(event["identifier"])
        
        if self.redis_manager:
            await self.redis_manager.shutdown()


@pytest.fixture
async def rate_limiting_manager():
    """Create rate limiting manager for testing."""
    manager = RateLimitingManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_token_bucket_rate_limiting_basic(rate_limiting_manager):
    """Test basic token bucket rate limiting functionality."""
    manager = rate_limiting_manager
    
    # Configure rate limit: 5 requests per second, burst of 10
    identifier = "test_user_basic"
    config_result = await manager.configure_rate_limit(identifier, 5, 10)
    
    assert config_result["success"] is True
    assert config_result["config_time"] < 0.1
    
    # Make allowed requests within burst capacity
    allowed_requests = []
    for i in range(5):
        request = await manager.make_rate_limited_request(identifier)
        allowed_requests.append(request)
    
    # All should be allowed initially
    assert all(r["allowed"] for r in allowed_requests)
    assert all(r["request_time"] < 0.1 for r in allowed_requests)


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_burst_capacity_enforcement(rate_limiting_manager):
    """Test burst capacity enforcement with token bucket."""
    manager = rate_limiting_manager
    
    # Configure: 2 requests per second, burst of 5
    identifier = "test_user_burst"
    await manager.configure_rate_limit(identifier, 2, 5)
    
    # Test burst handling
    burst_result = await manager.test_burst_capacity(identifier, 8)
    
    # Should allow burst capacity (5) and block excess (3)
    assert burst_result["allowed_count"] <= 5
    assert burst_result["blocked_count"] >= 3
    assert burst_result["burst_time"] < 1.0


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_sustained_rate_limiting_performance(rate_limiting_manager):
    """Test sustained rate limiting over time."""
    manager = rate_limiting_manager
    
    # Configure: 3 requests per second
    identifier = "test_user_sustained"
    await manager.configure_rate_limit(identifier, 3, 6)
    
    # Test sustained rate for 2 seconds with requests every 0.2 seconds
    sustained_result = await manager.test_sustained_rate_limiting(
        identifier, 2, 0.2
    )
    
    # Should allow approximately 3 requests per second (6 total over 2 seconds)
    assert sustained_result["allowed_count"] <= 8  # Allow some tolerance
    assert sustained_result["average_rate"] <= 4.0  # Should be close to 3 rps
    assert sustained_result["test_time"] >= 2.0


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_multi_user_rate_limit_isolation(rate_limiting_manager):
    """Test rate limit isolation between different users."""
    manager = rate_limiting_manager
    
    # Configure different limits for different users
    users = ["user_a", "user_b", "user_c"]
    
    for user in users:
        await manager.configure_rate_limit(user, 5, 10)
    
    # Test isolation
    isolation_result = await manager.test_multi_identifier_isolation(users, 7)
    
    # Each user should have independent rate limits
    assert isolation_result["properly_isolated"] is True
    
    # Verify each user gets similar treatment
    for user, analysis in isolation_result["results_by_identifier"].items():
        assert analysis["total_requests"] == 7
        # Each should get at least some requests (not completely blocked)
        assert analysis["allowed_count"] >= 3