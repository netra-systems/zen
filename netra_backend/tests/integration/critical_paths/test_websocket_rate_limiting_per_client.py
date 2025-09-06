from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3 Integration Test: WebSocket Per-Client Rate Limiting with Redis

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
    # REMOVED_SYNTAX_ERROR: - Business Goal: Stability - Prevent abuse and ensure fair resource usage
    # REMOVED_SYNTAX_ERROR: - Value Impact: Protects service availability from malicious or excessive usage
    # REMOVED_SYNTAX_ERROR: - Strategic Impact: $60K MRR - Rate limiting for enterprise service reliability

    # REMOVED_SYNTAX_ERROR: L3 Test: Uses real Redis for rate limiting state and enforcement.
    # REMOVED_SYNTAX_ERROR: Rate limiting target: 100 msgs/min per client with 99.9% accuracy.
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # Test framework import - using pytest fixtures instead
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.docker.unified_docker_manager import UnifiedDockerManager
    # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Optional
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from uuid import uuid4

    # REMOVED_SYNTAX_ERROR: import redis.asyncio as redis
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.redis_manager import RedisManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas import User
    # Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
    # REMOVED_SYNTAX_ERROR: from test_framework.real_services import get_real_services

    # REMOVED_SYNTAX_ERROR: from netra_backend.tests.integration.helpers.redis_l3_helpers import ( )

    # REMOVED_SYNTAX_ERROR: RedisContainer,

    # REMOVED_SYNTAX_ERROR: MockWebSocketForRedis,

    # REMOVED_SYNTAX_ERROR: create_test_message

    

# REMOVED_SYNTAX_ERROR: class WebSocketRateLimiter:

    # REMOVED_SYNTAX_ERROR: """Rate limiter for WebSocket connections using Redis."""

# REMOVED_SYNTAX_ERROR: def __init__(self, redis_client):

    # REMOVED_SYNTAX_ERROR: self.redis_client = redis_client

    # REMOVED_SYNTAX_ERROR: self.rate_limit_prefix = "ws_rate_limit"

    # REMOVED_SYNTAX_ERROR: self.default_limits = { )

    # REMOVED_SYNTAX_ERROR: "messages_per_minute": 100,

    # REMOVED_SYNTAX_ERROR: "burst_limit": 10,

    # REMOVED_SYNTAX_ERROR: "window_size": 60  # seconds

    

    # REMOVED_SYNTAX_ERROR: self.tier_limits = { )

    # REMOVED_SYNTAX_ERROR: "free": {"messages_per_minute": 50, "burst_limit": 5},

    # REMOVED_SYNTAX_ERROR: "early": {"messages_per_minute": 100, "burst_limit": 10},

    # REMOVED_SYNTAX_ERROR: "mid": {"messages_per_minute": 200, "burst_limit": 20},

    # REMOVED_SYNTAX_ERROR: "enterprise": {"messages_per_minute": 500, "burst_limit": 50}

    

# REMOVED_SYNTAX_ERROR: async def check_rate_limit(self, user_id: str, tier: str = "free") -> Dict[str, Any]:

    # REMOVED_SYNTAX_ERROR: """Check if user is within rate limits."""

    # REMOVED_SYNTAX_ERROR: limits = self.tier_limits.get(tier, self.default_limits)

    # REMOVED_SYNTAX_ERROR: current_time = int(time.time())

    # REMOVED_SYNTAX_ERROR: window_start = current_time - self.default_limits["window_size"]

    # Get current window key

    # REMOVED_SYNTAX_ERROR: window_key = "formatted_string"

    # Count messages in current window

    # REMOVED_SYNTAX_ERROR: current_count = await self.redis_client.get(window_key)

    # REMOVED_SYNTAX_ERROR: current_count = int(current_count) if current_count else 0

    # Check burst limit (last 10 seconds)

    # REMOVED_SYNTAX_ERROR: burst_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: burst_count = await self.redis_client.get(burst_key)

    # REMOVED_SYNTAX_ERROR: burst_count = int(burst_count) if burst_count else 0

    # Check limits

    # REMOVED_SYNTAX_ERROR: rate_limit_hit = current_count >= limits["messages_per_minute"]

    # REMOVED_SYNTAX_ERROR: burst_limit_hit = burst_count >= limits["burst_limit"]

    # REMOVED_SYNTAX_ERROR: return { )

    # REMOVED_SYNTAX_ERROR: "allowed": not (rate_limit_hit or burst_limit_hit),

    # REMOVED_SYNTAX_ERROR: "rate_limit_hit": rate_limit_hit,

    # REMOVED_SYNTAX_ERROR: "burst_limit_hit": burst_limit_hit,

    # REMOVED_SYNTAX_ERROR: "current_count": current_count,

    # REMOVED_SYNTAX_ERROR: "burst_count": burst_count,

    # REMOVED_SYNTAX_ERROR: "limits": limits,

    # REMOVED_SYNTAX_ERROR: "reset_time": (current_time // 60 + 1) * 60

    

# REMOVED_SYNTAX_ERROR: async def record_message(self, user_id: str, tier: str = "free") -> bool:

    # REMOVED_SYNTAX_ERROR: """Record a message and return if it's allowed."""

    # REMOVED_SYNTAX_ERROR: rate_check = await self.check_rate_limit(user_id, tier)

    # REMOVED_SYNTAX_ERROR: if not rate_check["allowed"]:

        # REMOVED_SYNTAX_ERROR: return False

        # REMOVED_SYNTAX_ERROR: current_time = int(time.time())

        # Increment counters

        # REMOVED_SYNTAX_ERROR: window_key = "formatted_string"

        # REMOVED_SYNTAX_ERROR: burst_key = "formatted_string"

        # Use pipeline for atomic operations

        # REMOVED_SYNTAX_ERROR: pipe = self.redis_client.pipeline()

        # REMOVED_SYNTAX_ERROR: pipe.incr(window_key)

        # REMOVED_SYNTAX_ERROR: pipe.expire(window_key, 120)  # 2 minutes TTL

        # REMOVED_SYNTAX_ERROR: pipe.incr(burst_key)

        # REMOVED_SYNTAX_ERROR: pipe.expire(burst_key, 20)   # 20 seconds TTL

        # REMOVED_SYNTAX_ERROR: await pipe.execute()

        # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def get_rate_limit_status(self, user_id: str, tier: str = "free") -> Dict[str, Any]:

    # REMOVED_SYNTAX_ERROR: """Get detailed rate limit status for user."""

    # REMOVED_SYNTAX_ERROR: limits = self.tier_limits.get(tier, self.default_limits)

    # REMOVED_SYNTAX_ERROR: current_time = int(time.time())

    # REMOVED_SYNTAX_ERROR: window_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: burst_key = "formatted_string"

    # REMOVED_SYNTAX_ERROR: current_count = await self.redis_client.get(window_key)

    # REMOVED_SYNTAX_ERROR: burst_count = await self.redis_client.get(burst_key)

    # REMOVED_SYNTAX_ERROR: current_count = int(current_count) if current_count else 0

    # REMOVED_SYNTAX_ERROR: burst_count = int(burst_count) if burst_count else 0

    # REMOVED_SYNTAX_ERROR: return { )

    # REMOVED_SYNTAX_ERROR: "user_id": user_id,

    # REMOVED_SYNTAX_ERROR: "tier": tier,

    # REMOVED_SYNTAX_ERROR: "current_count": current_count,

    # REMOVED_SYNTAX_ERROR: "burst_count": burst_count,

    # REMOVED_SYNTAX_ERROR: "limits": limits,

    # REMOVED_SYNTAX_ERROR: "remaining_messages": max(0, limits["messages_per_minute"] - current_count),

    # REMOVED_SYNTAX_ERROR: "remaining_burst": max(0, limits["burst_limit"] - burst_count),

    # REMOVED_SYNTAX_ERROR: "reset_time": (current_time // 60 + 1) * 60

    

# REMOVED_SYNTAX_ERROR: async def reset_rate_limit(self, user_id: str) -> None:

    # REMOVED_SYNTAX_ERROR: """Reset rate limit counters for user (admin function)."""

    # REMOVED_SYNTAX_ERROR: current_time = int(time.time())

    # REMOVED_SYNTAX_ERROR: keys_to_delete = []

    # Find all rate limit keys for user

    # REMOVED_SYNTAX_ERROR: pattern = "formatted_string"

    # REMOVED_SYNTAX_ERROR: async for key in self.redis_client.scan_iter(match=pattern):

        # REMOVED_SYNTAX_ERROR: keys_to_delete.append(key)

        # REMOVED_SYNTAX_ERROR: pattern = "formatted_string"

        # REMOVED_SYNTAX_ERROR: async for key in self.redis_client.scan_iter(match=pattern):

            # REMOVED_SYNTAX_ERROR: keys_to_delete.append(key)

            # REMOVED_SYNTAX_ERROR: if keys_to_delete:

                # REMOVED_SYNTAX_ERROR: await self.redis_client.delete(*keys_to_delete)

                # REMOVED_SYNTAX_ERROR: @pytest.mark.L3

                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration

# REMOVED_SYNTAX_ERROR: class TestWebSocketRateLimitingPerClientL3:

    # REMOVED_SYNTAX_ERROR: """L3 integration tests for WebSocket per-client rate limiting."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_container(self):

    # REMOVED_SYNTAX_ERROR: """Set up Redis container for rate limiting testing."""

    # REMOVED_SYNTAX_ERROR: container = RedisContainer(port=6388)

    # REMOVED_SYNTAX_ERROR: redis_url = await container.start()

    # REMOVED_SYNTAX_ERROR: yield container, redis_url

    # REMOVED_SYNTAX_ERROR: await container.stop()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def redis_client(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create Redis client for rate limiting."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # REMOVED_SYNTAX_ERROR: client = redis.Redis.from_url(redis_url, decode_responses=True)

    # REMOVED_SYNTAX_ERROR: yield client

    # REMOVED_SYNTAX_ERROR: await client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def websocket_manager(self, redis_container):

    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager with rate limiting."""

    # REMOVED_SYNTAX_ERROR: _, redis_url = redis_container

    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.websocket_manager.redis_manager') as mock_redis_mgr:

        # REMOVED_SYNTAX_ERROR: test_redis_mgr = RedisManager()

        # REMOVED_SYNTAX_ERROR: test_redis_mgr.enabled = True

        # REMOVED_SYNTAX_ERROR: test_redis_mgr.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

        # REMOVED_SYNTAX_ERROR: mock_redis_mgr.return_value = test_redis_mgr

        # REMOVED_SYNTAX_ERROR: mock_redis_mgr.get_client.return_value = test_redis_mgr.redis_client

        # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

        # REMOVED_SYNTAX_ERROR: yield manager

        # REMOVED_SYNTAX_ERROR: await test_redis_mgr.redis_client.close()

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def rate_limiter(self, redis_client):

    # REMOVED_SYNTAX_ERROR: """Create rate limiter instance."""

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return WebSocketRateLimiter(redis_client)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_users(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: """Create test users with different tiers."""

    # REMOVED_SYNTAX_ERROR: return [ )

    # REMOVED_SYNTAX_ERROR: User( )

    # REMOVED_SYNTAX_ERROR: id="formatted_string",

    # REMOVED_SYNTAX_ERROR: email="formatted_string",

    # REMOVED_SYNTAX_ERROR: username="formatted_string",

    # REMOVED_SYNTAX_ERROR: is_active=True,

    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc)

    

    # REMOVED_SYNTAX_ERROR: for i in range(5)

    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_basic_rate_limiting_enforcement(self, rate_limiter, test_users):

        # REMOVED_SYNTAX_ERROR: """Test basic rate limiting enforcement."""

        # REMOVED_SYNTAX_ERROR: user = test_users[0]

        # REMOVED_SYNTAX_ERROR: tier = "free"  # 50 messages per minute, 5 burst

        # Test burst limit

        # REMOVED_SYNTAX_ERROR: burst_results = []

        # REMOVED_SYNTAX_ERROR: for i in range(7):  # Exceed burst limit of 5

        # REMOVED_SYNTAX_ERROR: allowed = await rate_limiter.record_message(user.id, tier)

        # REMOVED_SYNTAX_ERROR: burst_results.append(allowed)

        # First 5 should be allowed, rest blocked

        # REMOVED_SYNTAX_ERROR: assert sum(burst_results[:5]) == 5  # All first 5 allowed

        # REMOVED_SYNTAX_ERROR: assert sum(burst_results[5:]) == 0  # Rest blocked

        # Reset and test rate limit

        # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

        # Spread messages over time to avoid burst limit

        # REMOVED_SYNTAX_ERROR: rate_results = []

        # REMOVED_SYNTAX_ERROR: for i in range(52):  # Exceed rate limit of 50

        # REMOVED_SYNTAX_ERROR: allowed = await rate_limiter.record_message(user.id, tier)

        # REMOVED_SYNTAX_ERROR: rate_results.append(allowed)

        # REMOVED_SYNTAX_ERROR: if i % 5 == 0:  # Brief pause every 5 messages

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

        # Should allow up to 50 messages, then block

        # REMOVED_SYNTAX_ERROR: allowed_count = sum(rate_results)

        # REMOVED_SYNTAX_ERROR: assert allowed_count <= 50  # Within rate limit

        # REMOVED_SYNTAX_ERROR: assert allowed_count >= 45  # Most messages allowed

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_tier_based_rate_limiting(self, rate_limiter, test_users):

            # REMOVED_SYNTAX_ERROR: """Test different rate limits based on user tier."""

            # REMOVED_SYNTAX_ERROR: tiers = ["free", "early", "mid", "enterprise"]

            # REMOVED_SYNTAX_ERROR: expected_limits = [50, 100, 200, 500]

            # REMOVED_SYNTAX_ERROR: for i, (tier, expected_limit) in enumerate(zip(tiers, expected_limits)):

                # REMOVED_SYNTAX_ERROR: user = test_users[i]

                # Test tier-specific limits

                # REMOVED_SYNTAX_ERROR: status = await rate_limiter.get_rate_limit_status(user.id, tier)

                # REMOVED_SYNTAX_ERROR: assert status["limits"]["messages_per_minute"] == expected_limit

                # Test enforcement

                # REMOVED_SYNTAX_ERROR: allowed_count = 0

                # REMOVED_SYNTAX_ERROR: for j in range(min(expected_limit + 10, 60)):  # Don"t test too many for higher tiers

                # REMOVED_SYNTAX_ERROR: allowed = await rate_limiter.record_message(user.id, tier)

                # REMOVED_SYNTAX_ERROR: if allowed:

                    # REMOVED_SYNTAX_ERROR: allowed_count += 1

                    # REMOVED_SYNTAX_ERROR: if j % 10 == 0:  # Pause to avoid burst limits

                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                    # Should respect tier limits

                    # REMOVED_SYNTAX_ERROR: if expected_limit <= 60:  # Only test full limit for lower tiers

                    # REMOVED_SYNTAX_ERROR: assert allowed_count <= expected_limit

                    # REMOVED_SYNTAX_ERROR: assert allowed_count >= expected_limit * 0.8  # Allow some variance

                    # Cleanup

                    # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_rate_limit_status_tracking(self, rate_limiter, test_users):

                        # REMOVED_SYNTAX_ERROR: """Test accurate rate limit status tracking."""

                        # REMOVED_SYNTAX_ERROR: user = test_users[0]

                        # REMOVED_SYNTAX_ERROR: tier = "early"  # 100 messages per minute, 10 burst

                        # Initial status

                        # REMOVED_SYNTAX_ERROR: initial_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                        # REMOVED_SYNTAX_ERROR: assert initial_status["current_count"] == 0

                        # REMOVED_SYNTAX_ERROR: assert initial_status["remaining_messages"] == 100

                        # REMOVED_SYNTAX_ERROR: assert initial_status["remaining_burst"] == 10

                        # Send some messages

                        # REMOVED_SYNTAX_ERROR: message_count = 15

                        # REMOVED_SYNTAX_ERROR: for i in range(message_count):

                            # REMOVED_SYNTAX_ERROR: await rate_limiter.record_message(user.id, tier)

                            # REMOVED_SYNTAX_ERROR: if i % 3 == 0:  # Pause to avoid burst limit

                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                            # Check updated status

                            # REMOVED_SYNTAX_ERROR: updated_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                            # REMOVED_SYNTAX_ERROR: assert updated_status["current_count"] <= message_count

                            # REMOVED_SYNTAX_ERROR: assert updated_status["remaining_messages"] <= 100 - updated_status["current_count"]

                            # Cleanup

                            # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_concurrent_rate_limiting(self, rate_limiter, test_users):

                                # REMOVED_SYNTAX_ERROR: """Test rate limiting with concurrent message sending."""

                                # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                # REMOVED_SYNTAX_ERROR: tier = "mid"  # 200 messages per minute, 20 burst

                                # Concurrent message sending

                                # REMOVED_SYNTAX_ERROR: concurrent_messages = 25  # Exceed burst limit

                                # REMOVED_SYNTAX_ERROR: tasks = []

                                # REMOVED_SYNTAX_ERROR: for i in range(concurrent_messages):

                                    # REMOVED_SYNTAX_ERROR: task = rate_limiter.record_message(user.id, tier)

                                    # REMOVED_SYNTAX_ERROR: tasks.append(task)

                                    # Execute concurrently

                                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

                                    # REMOVED_SYNTAX_ERROR: allowed_count = sum(results)

                                    # Should respect burst limit even with concurrency

                                    # REMOVED_SYNTAX_ERROR: assert allowed_count <= 20  # Burst limit

                                    # REMOVED_SYNTAX_ERROR: assert allowed_count >= 15  # Allow some variance due to timing

                                    # Check status consistency

                                    # REMOVED_SYNTAX_ERROR: final_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                                    # REMOVED_SYNTAX_ERROR: assert final_status["current_count"] >= allowed_count

                                    # Cleanup

                                    # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_rate_limit_window_reset(self, rate_limiter, test_users):

                                        # REMOVED_SYNTAX_ERROR: """Test rate limit window reset behavior."""

                                        # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                        # REMOVED_SYNTAX_ERROR: tier = "free"  # 50 messages per minute

                                        # Fill up rate limit

                                        # REMOVED_SYNTAX_ERROR: for i in range(5):  # Stay within burst limit

                                        # REMOVED_SYNTAX_ERROR: await rate_limiter.record_message(user.id, tier)

                                        # REMOVED_SYNTAX_ERROR: initial_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                                        # REMOVED_SYNTAX_ERROR: assert initial_status["current_count"] == 5

                                        # Get reset time

                                        # REMOVED_SYNTAX_ERROR: reset_time = initial_status["reset_time"]

                                        # REMOVED_SYNTAX_ERROR: current_time = int(time.time())

                                        # Reset time should be in the future

                                        # REMOVED_SYNTAX_ERROR: assert reset_time > current_time

                                        # REMOVED_SYNTAX_ERROR: assert reset_time - current_time <= 60  # Within next minute

                                        # Manual reset for testing

                                        # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                                        # Verify reset

                                        # REMOVED_SYNTAX_ERROR: post_reset_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                                        # REMOVED_SYNTAX_ERROR: assert post_reset_status["current_count"] == 0

                                        # REMOVED_SYNTAX_ERROR: assert post_reset_status["remaining_messages"] == 50

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_websocket_integration_with_rate_limiting(self, websocket_manager, rate_limiter, test_users):

                                            # REMOVED_SYNTAX_ERROR: """Test rate limiting integration with WebSocket messaging."""

                                            # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                            # REMOVED_SYNTAX_ERROR: tier = "free"

                                            # REMOVED_SYNTAX_ERROR: websocket = MockWebSocketForRedis(user.id)

                                            # Connect user

                                            # REMOVED_SYNTAX_ERROR: connection_info = await websocket_manager.connect_user(user.id, websocket)

                                            # REMOVED_SYNTAX_ERROR: assert connection_info is not None

                                            # Send messages with rate limiting checks

                                            # REMOVED_SYNTAX_ERROR: successful_sends = 0

                                            # REMOVED_SYNTAX_ERROR: rate_limited_sends = 0

                                            # REMOVED_SYNTAX_ERROR: for i in range(10):  # Test batch
                                            # Check rate limit before sending

                                            # REMOVED_SYNTAX_ERROR: allowed = await rate_limiter.record_message(user.id, tier)

                                            # REMOVED_SYNTAX_ERROR: if allowed:

                                                # REMOVED_SYNTAX_ERROR: test_message = create_test_message( )

                                                # REMOVED_SYNTAX_ERROR: "rate_limited_message",

                                                # REMOVED_SYNTAX_ERROR: user.id,

                                                # REMOVED_SYNTAX_ERROR: {"sequence": i, "allowed": True}

                                                

                                                # REMOVED_SYNTAX_ERROR: try:

                                                    # REMOVED_SYNTAX_ERROR: success = await websocket_manager.send_message_to_user(user.id, test_message)

                                                    # REMOVED_SYNTAX_ERROR: if success:

                                                        # REMOVED_SYNTAX_ERROR: successful_sends += 1

                                                        # REMOVED_SYNTAX_ERROR: except Exception:


                                                            # REMOVED_SYNTAX_ERROR: else:

                                                                # REMOVED_SYNTAX_ERROR: rate_limited_sends += 1
                                                                # Could send rate limit exceeded message

                                                                # REMOVED_SYNTAX_ERROR: rate_limit_message = create_test_message( )

                                                                # REMOVED_SYNTAX_ERROR: "rate_limit_exceeded",

                                                                # REMOVED_SYNTAX_ERROR: user.id,

                                                                # REMOVED_SYNTAX_ERROR: {"reason": "Rate limit exceeded"}

                                                                

                                                                # Should have some successful sends and possibly some rate limited

                                                                # REMOVED_SYNTAX_ERROR: assert successful_sends > 0

                                                                # Check final rate limit status

                                                                # REMOVED_SYNTAX_ERROR: final_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                                                                # REMOVED_SYNTAX_ERROR: assert final_status["current_count"] == successful_sends

                                                                # Cleanup

                                                                # REMOVED_SYNTAX_ERROR: await websocket_manager.disconnect_user(user.id, websocket)

                                                                # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_rate_limiting_accuracy_and_performance(self, rate_limiter, test_users):

                                                                    # REMOVED_SYNTAX_ERROR: """Test rate limiting accuracy and performance under load."""

                                                                    # REMOVED_SYNTAX_ERROR: user = test_users[0]

                                                                    # REMOVED_SYNTAX_ERROR: tier = "enterprise"  # 500 messages per minute, 50 burst

                                                                    # Performance test: rapid message sending

                                                                    # REMOVED_SYNTAX_ERROR: performance_start = time.time()

                                                                    # REMOVED_SYNTAX_ERROR: rapid_messages = 100

                                                                    # REMOVED_SYNTAX_ERROR: rapid_results = []

                                                                    # REMOVED_SYNTAX_ERROR: for i in range(rapid_messages):

                                                                        # REMOVED_SYNTAX_ERROR: allowed = await rate_limiter.record_message(user.id, tier)

                                                                        # REMOVED_SYNTAX_ERROR: rapid_results.append(allowed)

                                                                        # REMOVED_SYNTAX_ERROR: performance_time = time.time() - performance_start

                                                                        # REMOVED_SYNTAX_ERROR: allowed_rapid = sum(rapid_results)

                                                                        # Performance assertions

                                                                        # REMOVED_SYNTAX_ERROR: assert performance_time < 5.0  # Should complete quickly

                                                                        # REMOVED_SYNTAX_ERROR: assert allowed_rapid <= 50  # Burst limit enforcement

                                                                        # REMOVED_SYNTAX_ERROR: assert allowed_rapid >= 40  # Allow some variance

                                                                        # Reset for accuracy test

                                                                        # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                                                                        # Accuracy test: controlled message sending

                                                                        # REMOVED_SYNTAX_ERROR: accuracy_results = []

                                                                        # REMOVED_SYNTAX_ERROR: batch_size = 10

                                                                        # REMOVED_SYNTAX_ERROR: batches = 6  # 60 total messages

                                                                        # REMOVED_SYNTAX_ERROR: for batch in range(batches):

                                                                            # REMOVED_SYNTAX_ERROR: batch_results = []

                                                                            # Send batch with small delays

                                                                            # REMOVED_SYNTAX_ERROR: for i in range(batch_size):

                                                                                # REMOVED_SYNTAX_ERROR: allowed = await rate_limiter.record_message(user.id, tier)

                                                                                # REMOVED_SYNTAX_ERROR: batch_results.append(allowed)

                                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Small delay

                                                                                # REMOVED_SYNTAX_ERROR: accuracy_results.extend(batch_results)

                                                                                # Pause between batches to avoid burst limits

                                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)

                                                                                # REMOVED_SYNTAX_ERROR: total_allowed = sum(accuracy_results)

                                                                                # Accuracy assertions

                                                                                # REMOVED_SYNTAX_ERROR: assert total_allowed <= 60  # Should not exceed reasonable limit

                                                                                # REMOVED_SYNTAX_ERROR: assert total_allowed >= 50  # Should allow most messages with delays

                                                                                # Check final consistency

                                                                                # REMOVED_SYNTAX_ERROR: final_status = await rate_limiter.get_rate_limit_status(user.id, tier)

                                                                                # REMOVED_SYNTAX_ERROR: assert abs(final_status["current_count"] - total_allowed) <= 2  # Allow small variance

                                                                                # Cleanup

                                                                                # REMOVED_SYNTAX_ERROR: await rate_limiter.reset_rate_limit(user.id)

                                                                                # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":

                                                                                    # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s", "--tb=short"])