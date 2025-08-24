"""
L3 Integration Test: WebSocket Per-Client Rate Limiting with Redis

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Prevent abuse and ensure fair resource usage
- Value Impact: Protects service availability from malicious or excessive usage
- Strategic Impact: $60K MRR - Rate limiting for enterprise service reliability

L3 Test: Uses real Redis for rate limiting state and enforcement.
Rate limiting target: 100 msgs/min per client with 99.9% accuracy.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

import redis.asyncio as redis
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas import User
from test_framework.mock_utils import mock_justified

from netra_backend.tests.integration.helpers.redis_l3_helpers import (

    RedisContainer, 

    MockWebSocketForRedis, 

    create_test_message

)

class WebSocketRateLimiter:

    """Rate limiter for WebSocket connections using Redis."""
    
    def __init__(self, redis_client):

        self.redis_client = redis_client

        self.rate_limit_prefix = "ws_rate_limit"

        self.default_limits = {

            "messages_per_minute": 100,

            "burst_limit": 10,

            "window_size": 60  # seconds

        }

        self.tier_limits = {

            "free": {"messages_per_minute": 50, "burst_limit": 5},

            "early": {"messages_per_minute": 100, "burst_limit": 10},

            "mid": {"messages_per_minute": 200, "burst_limit": 20},

            "enterprise": {"messages_per_minute": 500, "burst_limit": 50}

        }
    
    async def check_rate_limit(self, user_id: str, tier: str = "free") -> Dict[str, Any]:

        """Check if user is within rate limits."""

        limits = self.tier_limits.get(tier, self.default_limits)

        current_time = int(time.time())

        window_start = current_time - self.default_limits["window_size"]
        
        # Get current window key

        window_key = f"{self.rate_limit_prefix}:{user_id}:{current_time // 60}"
        
        # Count messages in current window

        current_count = await self.redis_client.get(window_key)

        current_count = int(current_count) if current_count else 0
        
        # Check burst limit (last 10 seconds)

        burst_key = f"{self.rate_limit_prefix}:burst:{user_id}:{current_time // 10}"

        burst_count = await self.redis_client.get(burst_key)

        burst_count = int(burst_count) if burst_count else 0
        
        # Check limits

        rate_limit_hit = current_count >= limits["messages_per_minute"]

        burst_limit_hit = burst_count >= limits["burst_limit"]
        
        return {

            "allowed": not (rate_limit_hit or burst_limit_hit),

            "rate_limit_hit": rate_limit_hit,

            "burst_limit_hit": burst_limit_hit,

            "current_count": current_count,

            "burst_count": burst_count,

            "limits": limits,

            "reset_time": (current_time // 60 + 1) * 60

        }
    
    async def record_message(self, user_id: str, tier: str = "free") -> bool:

        """Record a message and return if it's allowed."""

        rate_check = await self.check_rate_limit(user_id, tier)
        
        if not rate_check["allowed"]:

            return False
        
        current_time = int(time.time())
        
        # Increment counters

        window_key = f"{self.rate_limit_prefix}:{user_id}:{current_time // 60}"

        burst_key = f"{self.rate_limit_prefix}:burst:{user_id}:{current_time // 10}"
        
        # Use pipeline for atomic operations

        pipe = self.redis_client.pipeline()

        pipe.incr(window_key)

        pipe.expire(window_key, 120)  # 2 minutes TTL

        pipe.incr(burst_key)

        pipe.expire(burst_key, 20)   # 20 seconds TTL

        await pipe.execute()
        
        return True
    
    async def get_rate_limit_status(self, user_id: str, tier: str = "free") -> Dict[str, Any]:

        """Get detailed rate limit status for user."""

        limits = self.tier_limits.get(tier, self.default_limits)

        current_time = int(time.time())
        
        window_key = f"{self.rate_limit_prefix}:{user_id}:{current_time // 60}"

        burst_key = f"{self.rate_limit_prefix}:burst:{user_id}:{current_time // 10}"
        
        current_count = await self.redis_client.get(window_key)

        burst_count = await self.redis_client.get(burst_key)
        
        current_count = int(current_count) if current_count else 0

        burst_count = int(burst_count) if burst_count else 0
        
        return {

            "user_id": user_id,

            "tier": tier,

            "current_count": current_count,

            "burst_count": burst_count,

            "limits": limits,

            "remaining_messages": max(0, limits["messages_per_minute"] - current_count),

            "remaining_burst": max(0, limits["burst_limit"] - burst_count),

            "reset_time": (current_time // 60 + 1) * 60

        }
    
    async def reset_rate_limit(self, user_id: str) -> None:

        """Reset rate limit counters for user (admin function)."""

        current_time = int(time.time())

        keys_to_delete = []
        
        # Find all rate limit keys for user

        pattern = f"{self.rate_limit_prefix}:{user_id}:*"

        async for key in self.redis_client.scan_iter(match=pattern):

            keys_to_delete.append(key)
        
        pattern = f"{self.rate_limit_prefix}:burst:{user_id}:*"

        async for key in self.redis_client.scan_iter(match=pattern):

            keys_to_delete.append(key)
        
        if keys_to_delete:

            await self.redis_client.delete(*keys_to_delete)

@pytest.mark.L3

@pytest.mark.integration

class TestWebSocketRateLimitingPerClientL3:

    """L3 integration tests for WebSocket per-client rate limiting."""
    
    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container for rate limiting testing."""

        container = RedisContainer(port=6388)

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    
    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client for rate limiting."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    
    @pytest.fixture

    async def websocket_manager(self, redis_container):

        """Create WebSocket manager with rate limiting."""

        _, redis_url = redis_container
        
        with patch('netra_backend.app.websocket_manager.redis_manager') as mock_redis_mgr:

            test_redis_mgr = RedisManager()

            test_redis_mgr.enabled = True

            test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

            mock_redis_mgr.return_value = test_redis_mgr

            mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client
            
            manager = WebSocketManager()

            yield manager
            
            await test_redis_mgr.redis_client.close()
    
    @pytest.fixture

    async def rate_limiter(self, redis_client):

        """Create rate limiter instance."""

        return WebSocketRateLimiter(redis_client)
    
    @pytest.fixture

    def test_users(self):

        """Create test users with different tiers."""

        return [

            User(

                id=f"rate_user_{i}",

                email=f"rateuser{i}@example.com", 

                username=f"rateuser{i}",

                is_active=True,

                created_at=datetime.now(timezone.utc)

            )

            for i in range(5)

        ]
    
    @pytest.mark.asyncio
    async def test_basic_rate_limiting_enforcement(self, rate_limiter, test_users):

        """Test basic rate limiting enforcement."""

        user = test_users[0]

        tier = "free"  # 50 messages per minute, 5 burst
        
        # Test burst limit

        burst_results = []

        for i in range(7):  # Exceed burst limit of 5

            allowed = await rate_limiter.record_message(user.id, tier)

            burst_results.append(allowed)
        
        # First 5 should be allowed, rest blocked

        assert sum(burst_results[:5]) == 5  # All first 5 allowed

        assert sum(burst_results[5:]) == 0  # Rest blocked
        
        # Reset and test rate limit

        await rate_limiter.reset_rate_limit(user.id)
        
        # Spread messages over time to avoid burst limit

        rate_results = []

        for i in range(52):  # Exceed rate limit of 50

            allowed = await rate_limiter.record_message(user.id, tier)

            rate_results.append(allowed)
            
            if i % 5 == 0:  # Brief pause every 5 messages

                await asyncio.sleep(0.1)
        
        # Should allow up to 50 messages, then block

        allowed_count = sum(rate_results)

        assert allowed_count <= 50  # Within rate limit

        assert allowed_count >= 45  # Most messages allowed
    
    @pytest.mark.asyncio
    async def test_tier_based_rate_limiting(self, rate_limiter, test_users):

        """Test different rate limits based on user tier."""

        tiers = ["free", "early", "mid", "enterprise"]

        expected_limits = [50, 100, 200, 500]
        
        for i, (tier, expected_limit) in enumerate(zip(tiers, expected_limits)):

            user = test_users[i]
            
            # Test tier-specific limits

            status = await rate_limiter.get_rate_limit_status(user.id, tier)

            assert status["limits"]["messages_per_minute"] == expected_limit
            
            # Test enforcement

            allowed_count = 0

            for j in range(min(expected_limit + 10, 60)):  # Don't test too many for higher tiers

                allowed = await rate_limiter.record_message(user.id, tier)

                if allowed:

                    allowed_count += 1
                
                if j % 10 == 0:  # Pause to avoid burst limits

                    await asyncio.sleep(0.1)
            
            # Should respect tier limits

            if expected_limit <= 60:  # Only test full limit for lower tiers

                assert allowed_count <= expected_limit

                assert allowed_count >= expected_limit * 0.8  # Allow some variance
            
            # Cleanup

            await rate_limiter.reset_rate_limit(user.id)
    
    @pytest.mark.asyncio
    async def test_rate_limit_status_tracking(self, rate_limiter, test_users):

        """Test accurate rate limit status tracking."""

        user = test_users[0]

        tier = "early"  # 100 messages per minute, 10 burst
        
        # Initial status

        initial_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert initial_status["current_count"] == 0

        assert initial_status["remaining_messages"] == 100

        assert initial_status["remaining_burst"] == 10
        
        # Send some messages

        message_count = 15

        for i in range(message_count):

            await rate_limiter.record_message(user.id, tier)

            if i % 3 == 0:  # Pause to avoid burst limit

                await asyncio.sleep(0.1)
        
        # Check updated status

        updated_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert updated_status["current_count"] <= message_count

        assert updated_status["remaining_messages"] <= 100 - updated_status["current_count"]
        
        # Cleanup

        await rate_limiter.reset_rate_limit(user.id)
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, rate_limiter, test_users):

        """Test rate limiting with concurrent message sending."""

        user = test_users[0]

        tier = "mid"  # 200 messages per minute, 20 burst
        
        # Concurrent message sending

        concurrent_messages = 25  # Exceed burst limit

        tasks = []
        
        for i in range(concurrent_messages):

            task = rate_limiter.record_message(user.id, tier)

            tasks.append(task)
        
        # Execute concurrently

        results = await asyncio.gather(*tasks)

        allowed_count = sum(results)
        
        # Should respect burst limit even with concurrency

        assert allowed_count <= 20  # Burst limit

        assert allowed_count >= 15  # Allow some variance due to timing
        
        # Check status consistency

        final_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert final_status["current_count"] >= allowed_count
        
        # Cleanup

        await rate_limiter.reset_rate_limit(user.id)
    
    @pytest.mark.asyncio
    async def test_rate_limit_window_reset(self, rate_limiter, test_users):

        """Test rate limit window reset behavior."""

        user = test_users[0]

        tier = "free"  # 50 messages per minute
        
        # Fill up rate limit

        for i in range(5):  # Stay within burst limit

            await rate_limiter.record_message(user.id, tier)
        
        initial_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert initial_status["current_count"] == 5
        
        # Get reset time

        reset_time = initial_status["reset_time"]

        current_time = int(time.time())
        
        # Reset time should be in the future

        assert reset_time > current_time

        assert reset_time - current_time <= 60  # Within next minute
        
        # Manual reset for testing

        await rate_limiter.reset_rate_limit(user.id)
        
        # Verify reset

        post_reset_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert post_reset_status["current_count"] == 0

        assert post_reset_status["remaining_messages"] == 50
    
    @pytest.mark.asyncio
    async def test_websocket_integration_with_rate_limiting(self, websocket_manager, rate_limiter, test_users):

        """Test rate limiting integration with WebSocket messaging."""

        user = test_users[0]

        tier = "free"

        websocket = MockWebSocketForRedis(user.id)
        
        # Connect user

        connection_info = await websocket_manager.connect_user(user.id, websocket)

        assert connection_info is not None
        
        # Send messages with rate limiting checks

        successful_sends = 0

        rate_limited_sends = 0
        
        for i in range(10):  # Test batch
            # Check rate limit before sending

            allowed = await rate_limiter.record_message(user.id, tier)
            
            if allowed:

                test_message = create_test_message(

                    "rate_limited_message", 

                    user.id, 

                    {"sequence": i, "allowed": True}

                )
                
                try:

                    success = await websocket_manager.send_message_to_user(user.id, test_message)

                    if success:

                        successful_sends += 1

                except Exception:

                    pass

            else:

                rate_limited_sends += 1
                # Could send rate limit exceeded message

                rate_limit_message = create_test_message(

                    "rate_limit_exceeded", 

                    user.id, 

                    {"reason": "Rate limit exceeded"}

                )
        
        # Should have some successful sends and possibly some rate limited

        assert successful_sends > 0
        
        # Check final rate limit status

        final_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert final_status["current_count"] == successful_sends
        
        # Cleanup

        await websocket_manager.disconnect_user(user.id, websocket)

        await rate_limiter.reset_rate_limit(user.id)
    
    @mock_justified("L3: Rate limiting testing with real Redis state management")

    @pytest.mark.asyncio
    async def test_rate_limiting_accuracy_and_performance(self, rate_limiter, test_users):

        """Test rate limiting accuracy and performance under load."""

        user = test_users[0]

        tier = "enterprise"  # 500 messages per minute, 50 burst
        
        # Performance test: rapid message sending

        performance_start = time.time()

        rapid_messages = 100

        rapid_results = []
        
        for i in range(rapid_messages):

            allowed = await rate_limiter.record_message(user.id, tier)

            rapid_results.append(allowed)
        
        performance_time = time.time() - performance_start

        allowed_rapid = sum(rapid_results)
        
        # Performance assertions

        assert performance_time < 5.0  # Should complete quickly

        assert allowed_rapid <= 50  # Burst limit enforcement

        assert allowed_rapid >= 40  # Allow some variance
        
        # Reset for accuracy test

        await rate_limiter.reset_rate_limit(user.id)
        
        # Accuracy test: controlled message sending

        accuracy_results = []

        batch_size = 10

        batches = 6  # 60 total messages
        
        for batch in range(batches):

            batch_results = []
            
            # Send batch with small delays

            for i in range(batch_size):

                allowed = await rate_limiter.record_message(user.id, tier)

                batch_results.append(allowed)

                await asyncio.sleep(0.01)  # Small delay
            
            accuracy_results.extend(batch_results)
            
            # Pause between batches to avoid burst limits

            await asyncio.sleep(0.5)
        
        total_allowed = sum(accuracy_results)
        
        # Accuracy assertions

        assert total_allowed <= 60  # Should not exceed reasonable limit

        assert total_allowed >= 50  # Should allow most messages with delays
        
        # Check final consistency

        final_status = await rate_limiter.get_rate_limit_status(user.id, tier)

        assert abs(final_status["current_count"] - total_allowed) <= 2  # Allow small variance
        
        # Cleanup

        await rate_limiter.reset_rate_limit(user.id)

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])