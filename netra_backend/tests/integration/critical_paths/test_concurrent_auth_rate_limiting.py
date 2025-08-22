"""L3 Integration Test: Concurrent Authentication Rate Limiting

Business Value Justification (BVJ):
- Segment: Platform protection
- Business Goal: Prevent auth DDoS attacks  
- Value Impact: $12K MRR - Prevent auth DDoS attacks
- Strategic Impact: Protects platform from auth service overload

L3 Test: Real Redis rate limiting with concurrent auth requests, per-IP/user limits,
proper error responses, and rate limit reset validation.
"""

from netra_backend.tests.test_utils import setup_test_path

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime, timezone

import redis.asyncio as redis

# Add project root to path

from netra_backend.app.schemas.rate_limit_types import RateLimitConfig, RateLimitResult, TokenBucket
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.integration.helpers.redis_l3_helpers import RedisContainer

# Add project root to path

logger = central_logger.get_logger(__name__)


class RateLimitTestScenario:
    """Test scenario for rate limiting validation."""
    
    def __init__(self, client_ip: str, user_id: str = None):
        self.client_ip = client_ip
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.attempts = []
        self.blocked_count = 0
        self.success_count = 0

    def record_attempt(self, allowed: bool, timestamp: float = None):
        """Record authentication attempt result."""
        entry = {
            "timestamp": timestamp or time.time(),
            "allowed": allowed,
            "ip": self.client_ip
        }
        self.attempts.append(entry)
        if allowed:
            self.success_count += 1
        else:
            self.blocked_count += 1


class ConcurrentAuthRateLimitManager:
    """Manages Redis-backed rate limiting for auth endpoints."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.ip_limits = {"per_minute": 10, "per_hour": 100}
        self.user_limits = {"per_minute": 20, "per_hour": 200}
        self.auth_operation_limits = {
            "login": {"per_minute": 5, "burst": 10},
            "refresh": {"per_minute": 15, "burst": 20},
            "logout": {"per_minute": 10, "burst": 15}
        }

    async def check_ip_rate_limit(self, client_ip: str) -> RateLimitResult:
        """Check rate limit for IP address."""
        now = time.time()
        window_key = f"rate_limit:ip:{client_ip}:minute"
        
        # Get current count in sliding window
        pipe = self.redis_client.pipeline()
        pipe.zadd(window_key, {str(now): now})
        pipe.zremrangebyscore(window_key, 0, now - 60)
        pipe.zcard(window_key)
        pipe.expire(window_key, 120)
        results = await pipe.execute()
        
        current_count = results[2]
        allowed = current_count <= self.ip_limits["per_minute"]
        
        return RateLimitResult(
            allowed=allowed,
            status="allowed" if allowed else "denied",
            remaining_requests=max(0, self.ip_limits["per_minute"] - current_count)
        )

    async def check_user_rate_limit(self, user_id: str) -> RateLimitResult:
        """Check rate limit for user ID."""
        now = time.time()
        window_key = f"rate_limit:user:{user_id}:minute"
        
        pipe = self.redis_client.pipeline()
        pipe.zadd(window_key, {str(now): now})
        pipe.zremrangebyscore(window_key, 0, now - 60)
        pipe.zcard(window_key)
        pipe.expire(window_key, 120)
        results = await pipe.execute()
        
        current_count = results[2]
        allowed = current_count <= self.user_limits["per_minute"]
        
        return RateLimitResult(
            allowed=allowed,
            status="allowed" if allowed else "denied",
            remaining_requests=max(0, self.user_limits["per_minute"] - current_count)
        )

    async def check_operation_rate_limit(self, client_ip: str, operation: str) -> RateLimitResult:
        """Check rate limit for specific auth operation."""
        if operation not in self.auth_operation_limits:
            return RateLimitResult(allowed=True, status="allowed", remaining_requests=999)
        
        limits = self.auth_operation_limits[operation]
        now = time.time()
        window_key = f"rate_limit:op:{operation}:{client_ip}:minute"
        
        pipe = self.redis_client.pipeline()
        pipe.zadd(window_key, {str(now): now})
        pipe.zremrangebyscore(window_key, 0, now - 60)
        pipe.zcard(window_key)
        pipe.expire(window_key, 120)
        results = await pipe.execute()
        
        current_count = results[2]
        allowed = current_count <= limits["per_minute"]
        
        return RateLimitResult(
            allowed=allowed,
            status="allowed" if allowed else "denied",
            remaining_requests=max(0, limits["per_minute"] - current_count)
        )

    async def simulate_auth_request(self, scenario: RateLimitTestScenario, 
                                  operation: str = "login") -> Dict[str, Any]:
        """Simulate authentication request with rate limiting."""
        # Check all rate limits
        ip_result = await self.check_ip_rate_limit(scenario.client_ip)
        user_result = await self.check_user_rate_limit(scenario.user_id)
        op_result = await self.check_operation_rate_limit(scenario.client_ip, operation)
        
        # Request allowed only if all limits allow it
        allowed = ip_result.allowed and user_result.allowed and op_result.allowed
        
        # Determine limiting factor
        limiting_factor = None
        if not ip_result.allowed:
            limiting_factor = "ip_limit"
        elif not user_result.allowed:
            limiting_factor = "user_limit"
        elif not op_result.allowed:
            limiting_factor = f"{operation}_limit"
        
        scenario.record_attempt(allowed)
        
        return {
            "allowed": allowed,
            "limiting_factor": limiting_factor,
            "ip_remaining": ip_result.remaining_requests,
            "user_remaining": user_result.remaining_requests,
            "operation_remaining": op_result.remaining_requests
        }

    async def wait_for_rate_limit_reset(self, wait_seconds: int = 70):
        """Wait for rate limit window to reset."""
        logger.info(f"Waiting {wait_seconds}s for rate limit reset")
        await asyncio.sleep(wait_seconds)

    async def cleanup_test_data(self):
        """Clean up Redis test data."""
        pattern_keys = [
            "rate_limit:ip:*",
            "rate_limit:user:*", 
            "rate_limit:op:*"
        ]
        
        for pattern in pattern_keys:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)


@pytest.mark.L3
@pytest.mark.integration
class TestConcurrentAuthRateLimitingL3:
    """L3 test for concurrent authentication rate limiting."""

    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container for testing."""
        container = RedisContainer()
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()

    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()

    @pytest.fixture
    async def rate_limit_manager(self, redis_client):
        """Create rate limiting manager."""
        manager = ConcurrentAuthRateLimitManager(redis_client)
        yield manager
        await manager.cleanup_test_data()

    async def test_ip_rate_limiting_enforcement(self, rate_limit_manager):
        """Test IP-based rate limiting under concurrent load."""
        scenario = RateLimitTestScenario("192.168.1.100")
        
        # Make requests up to IP limit
        for i in range(12):  # Exceed IP limit of 10/minute
            await rate_limit_manager.simulate_auth_request(scenario)
        
        # Verify rate limiting engaged
        assert scenario.blocked_count > 0
        assert scenario.success_count == 10  # Only 10 should succeed
        assert scenario.blocked_count == 2   # 2 should be blocked

    async def test_user_rate_limiting_enforcement(self, rate_limit_manager):
        """Test user-based rate limiting enforcement."""
        scenario = RateLimitTestScenario("192.168.1.101", "test_user_123")
        
        # Make requests up to user limit
        for i in range(22):  # Exceed user limit of 20/minute
            await rate_limit_manager.simulate_auth_request(scenario)
        
        # Verify user rate limiting
        assert scenario.blocked_count > 0
        assert scenario.success_count == 20  # Only 20 should succeed
        assert scenario.blocked_count == 2   # 2 should be blocked

    async def test_operation_specific_rate_limits(self, rate_limit_manager):
        """Test different rate limits per auth operation."""
        scenario = RateLimitTestScenario("192.168.1.102")
        
        # Test login operation (limit: 5/minute)
        for i in range(7):
            await rate_limit_manager.simulate_auth_request(scenario, "login")
        
        login_blocked = scenario.blocked_count
        scenario.blocked_count = 0  # Reset for next test
        scenario.success_count = 0
        
        # Test refresh operation (limit: 15/minute) 
        for i in range(17):
            await rate_limit_manager.simulate_auth_request(scenario, "refresh")
        
        refresh_blocked = scenario.blocked_count
        
        # Verify different limits enforced
        assert login_blocked == 2   # 2 login requests blocked
        assert refresh_blocked == 2 # 2 refresh requests blocked

    async def test_concurrent_multi_ip_rate_limiting(self, rate_limit_manager):
        """Test rate limiting isolation across different IPs."""
        scenarios = [
            RateLimitTestScenario(f"192.168.1.{i+110}") 
            for i in range(5)
        ]
        
        # Concurrent requests from multiple IPs
        tasks = []
        for scenario in scenarios:
            for _ in range(8):  # 8 requests per IP
                task = rate_limit_manager.simulate_auth_request(scenario)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify each IP gets fair allocation
        for scenario in scenarios:
            assert scenario.success_count == 8  # All requests should succeed
            assert scenario.blocked_count == 0  # No blocking at this volume

    async def test_rate_limit_reset_after_window(self, rate_limit_manager):
        """Test rate limit reset after time window expires."""
        scenario = RateLimitTestScenario("192.168.1.120")
        
        # Exhaust rate limit
        for i in range(15):  # Exceed IP limit
            await rate_limit_manager.simulate_auth_request(scenario)
        
        initial_blocked = scenario.blocked_count
        scenario.blocked_count = 0
        scenario.success_count = 0
        
        # Wait for window reset
        await rate_limit_manager.wait_for_rate_limit_reset(70)
        
        # Try requests after reset
        for i in range(5):
            await rate_limit_manager.simulate_auth_request(scenario)
        
        # Verify rate limit reset
        assert initial_blocked > 0      # Initially blocked
        assert scenario.blocked_count == 0  # No blocking after reset
        assert scenario.success_count == 5   # All requests succeed

    async def test_proper_error_responses_when_limited(self, rate_limit_manager):
        """Test proper error responses when rate limit exceeded."""
        scenario = RateLimitTestScenario("192.168.1.130")
        
        # Exhaust IP rate limit
        results = []
        for i in range(12):
            result = await rate_limit_manager.simulate_auth_request(scenario)
            results.append(result)
        
        # Check response structure for blocked requests
        blocked_results = [r for r in results if not r["allowed"]]
        assert len(blocked_results) == 2
        
        for result in blocked_results:
            assert result["limiting_factor"] == "ip_limit"
            assert result["ip_remaining"] == 0
            assert "operation_remaining" in result

    async def test_mixed_operation_concurrent_limiting(self, rate_limit_manager):
        """Test concurrent requests with mixed auth operations."""
        scenario = RateLimitTestScenario("192.168.1.140")
        
        # Mix of different operations
        operations = ["login", "refresh", "logout"] * 4  # 12 total requests
        
        tasks = []
        for op in operations:
            task = rate_limit_manager.simulate_auth_request(scenario, op)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify operation-specific limits enforced
        blocked_results = [r for r in results if not r["allowed"]]
        assert len(blocked_results) > 0  # Some should be blocked
        
        # Check that different operations have different limits
        login_blocks = sum(1 for r in blocked_results if r["limiting_factor"] == "login_limit")
        refresh_blocks = sum(1 for r in blocked_results if r["limiting_factor"] == "refresh_limit")
        
        # Login should block more frequently (lower limit)
        assert login_blocks >= refresh_blocks


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])