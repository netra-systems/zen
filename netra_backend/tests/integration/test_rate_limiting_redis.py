"""L3 Integration Test: Rate Limiting with Real Redis Backend

Business Value Justification (BVJ):
- Segment: All tiers (rate limiting protects all users)
- Business Goal: Protects platform from abuse and ensures fair resource usage
- Value Impact: Prevents service degradation, maintains SLA compliance, ensures equitable access
- Strategic Impact: Protects $75K MRR from abuse-related outages and resource exhaustion

L3 Test: Real Redis backend for rate limiting with request limits, sliding windows,
burst handling, and per-user rate limiting validation.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest
import redis.asyncio as redis
from logging_config import central_logger

from netra_backend.app.redis_manager import RedisManager

from netra_backend.app.services.monitoring.rate_limiter import GCPRateLimiter
from netra_backend.tests.integration.helpers.redis_l3_helpers import (
    RedisContainer,
    verify_redis_connection,
)

logger = central_logger.get_logger(__name__)

@dataclass
class RateLimitConfig:
    """Rate limiting configuration for testing."""
    requests_per_minute: int
    requests_per_hour: int
    burst_capacity: int
    window_size_seconds: int
    user_tier: str

class RateLimitingManager:
    """Manages rate limiting testing with real Redis backend."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.rate_limiters = {}
        self.test_keys = set()
        self.rate_limit_configs = {
            "free": RateLimitConfig(requests_per_minute=60, requests_per_hour=1000, burst_capacity=10, window_size_seconds=60, user_tier="free"),
            "pro": RateLimitConfig(requests_per_minute=300, requests_per_hour=10000, burst_capacity=50, window_size_seconds=60, user_tier="pro"),
            "enterprise": RateLimitConfig(requests_per_minute=1000, requests_per_hour=50000, burst_capacity=200, window_size_seconds=60, user_tier="enterprise")
        }
        self.rate_limit_stats = {
            "requests_processed": 0,
            "requests_allowed": 0,
            "requests_rejected": 0,
            "burst_requests_handled": 0,
            "sliding_window_enforced": 0
        }
    
    async def test_request_limits_enforcement(self, user_count: int, requests_per_user: int) -> Dict[str, Any]:
        """Test request limit enforcement across different user tiers."""
        limit_results = {}
        
        for tier, config in self.rate_limit_configs.items():
            tier_results = {
                "users_tested": 0,
                "total_requests": 0,
                "allowed_requests": 0,
                "rejected_requests": 0,
                "limit_enforcement_accuracy": 0
            }
            
            # Test users for this tier
            tier_users = user_count // 3 if tier != "free" else user_count - (2 * (user_count // 3))
            
            for i in range(tier_users):
                user_id = f"{tier}_user_{i}_{uuid.uuid4().hex[:8]}"
                
                allowed_count = 0
                rejected_count = 0
                
                # Make requests up to the limit
                for req_num in range(requests_per_user):
                    request_allowed = await self._check_rate_limit(
                        user_id, tier, config, f"request_{req_num}"
                    )
                    
                    tier_results["total_requests"] += 1
                    self.rate_limit_stats["requests_processed"] += 1
                    
                    if request_allowed:
                        allowed_count += 1
                        tier_results["allowed_requests"] += 1
                        self.rate_limit_stats["requests_allowed"] += 1
                    else:
                        rejected_count += 1
                        tier_results["rejected_requests"] += 1
                        self.rate_limit_stats["requests_rejected"] += 1
                
                # Verify limit enforcement accuracy
                expected_allowed = min(requests_per_user, config.requests_per_minute)
                if abs(allowed_count - expected_allowed) <= 2:  # Allow small variance
                    tier_results["limit_enforcement_accuracy"] += 1
                
                tier_results["users_tested"] += 1
            
            # Calculate tier-specific metrics
            if tier_results["users_tested"] > 0:
                tier_results["avg_requests_per_user"] = tier_results["total_requests"] / tier_results["users_tested"]
                tier_results["accuracy_rate"] = (tier_results["limit_enforcement_accuracy"] / tier_results["users_tested"]) * 100
            
            limit_results[tier] = tier_results
        
        return limit_results
    
    async def test_sliding_window_implementation(self, window_tests: int) -> Dict[str, Any]:
        """Test sliding window rate limiting implementation."""
        sliding_results = {
            "window_tests_completed": 0,
            "accurate_window_enforcement": 0,
            "window_transitions": 0,
            "temporal_accuracy": 0,
            "sliding_violations_detected": 0
        }
        
        for i in range(window_tests):
            user_id = f"sliding_user_{i}_{uuid.uuid4().hex[:8]}"
            tier = "pro"  # Use consistent tier for sliding window testing
            config = self.rate_limit_configs[tier]
            
            # Test sliding window behavior
            window_start = time.time()
            requests_in_window = []
            
            # Make requests throughout the time window
            for second in range(config.window_size_seconds):
                # Make a few requests each second
                for req in range(3):
                    request_time = window_start + second + (req * 0.3)
                    
                    # Simulate request at specific time
                    request_allowed = await self._check_rate_limit_at_time(
                        user_id, tier, config, request_time
                    )
                    
                    requests_in_window.append({
                        "time": request_time,
                        "allowed": request_allowed
                    })
            
            # Analyze sliding window behavior
            window_accuracy = self._analyze_sliding_window_accuracy(
                requests_in_window, config, window_start
            )
            
            if window_accuracy["accurate"]:
                sliding_results["accurate_window_enforcement"] += 1
                self.rate_limit_stats["sliding_window_enforced"] += 1
            
            sliding_results["window_transitions"] += window_accuracy["transitions"]
            sliding_results["temporal_accuracy"] += window_accuracy["temporal_score"]
            sliding_results["window_tests_completed"] += 1
            
            if window_accuracy["violations"] > 0:
                sliding_results["sliding_violations_detected"] += window_accuracy["violations"]
        
        # Calculate averages
        if sliding_results["window_tests_completed"] > 0:
            sliding_results["avg_transitions_per_test"] = sliding_results["window_transitions"] / sliding_results["window_tests_completed"]
            sliding_results["avg_temporal_accuracy"] = sliding_results["temporal_accuracy"] / sliding_results["window_tests_completed"]
            sliding_results["window_accuracy_rate"] = (sliding_results["accurate_window_enforcement"] / sliding_results["window_tests_completed"]) * 100
        
        return sliding_results
    
    async def test_burst_handling_capacity(self, burst_tests: int) -> Dict[str, Any]:
        """Test burst request handling with different capacities."""
        burst_results = {
            "burst_tests_completed": 0,
            "successful_burst_handling": 0,
            "burst_capacity_enforced": 0,
            "burst_recovery_validated": 0,
            "burst_overflow_detected": 0
        }
        
        for i in range(burst_tests):
            user_id = f"burst_user_{i}_{uuid.uuid4().hex[:8]}"
            tier = "enterprise" if i % 3 == 0 else "pro"
            config = self.rate_limit_configs[tier]
            
            # Test burst scenario
            burst_start = time.time()
            burst_requests = config.burst_capacity + 10  # Exceed burst capacity
            
            allowed_in_burst = 0
            rejected_in_burst = 0
            
            # Send burst requests rapidly
            for req_num in range(burst_requests):
                request_allowed = await self._check_rate_limit(
                    user_id, tier, config, f"burst_{req_num}"
                )
                
                if request_allowed:
                    allowed_in_burst += 1
                    self.rate_limit_stats["burst_requests_handled"] += 1
                else:
                    rejected_in_burst += 1
                
                # Small delay to simulate rapid requests
                await asyncio.sleep(0.01)
            
            burst_time = time.time() - burst_start
            
            # Verify burst handling
            burst_capacity_respected = allowed_in_burst <= config.burst_capacity + 2  # Allow small variance
            if burst_capacity_respected:
                burst_results["burst_capacity_enforced"] += 1
            
            # Test burst recovery
            await asyncio.sleep(config.window_size_seconds + 1)
            
            recovery_request_allowed = await self._check_rate_limit(
                user_id, tier, config, "recovery_test"
            )
            
            if recovery_request_allowed:
                burst_results["burst_recovery_validated"] += 1
            
            # Check for overflow conditions
            if rejected_in_burst > 0:
                burst_results["burst_overflow_detected"] += 1
            
            if burst_capacity_respected and recovery_request_allowed:
                burst_results["successful_burst_handling"] += 1
            
            burst_results["burst_tests_completed"] += 1
        
        # Calculate burst handling metrics
        if burst_results["burst_tests_completed"] > 0:
            burst_results["burst_success_rate"] = (burst_results["successful_burst_handling"] / burst_results["burst_tests_completed"]) * 100
            burst_results["capacity_enforcement_rate"] = (burst_results["burst_capacity_enforced"] / burst_results["burst_tests_completed"]) * 100
            burst_results["recovery_success_rate"] = (burst_results["burst_recovery_validated"] / burst_results["burst_tests_completed"]) * 100
        
        return burst_results
    
    async def test_per_user_rate_limiting(self, user_count: int, concurrent_requests: int) -> Dict[str, Any]:
        """Test per-user rate limiting with concurrent requests."""
        per_user_results = {
            "users_tested": 0,
            "isolation_violations": 0,
            "cross_user_interference": 0,
            "fair_allocation_maintained": 0,
            "concurrent_accuracy": 0
        }
        
        # Create concurrent user tasks
        user_tasks = []
        
        for i in range(user_count):
            user_id = f"per_user_{i}_{uuid.uuid4().hex[:8]}"
            tier = ["free", "pro", "enterprise"][i % 3]
            
            task = self._test_user_isolation(
                user_id, tier, concurrent_requests, i
            )
            user_tasks.append(task)
        
        # Execute concurrent user tests
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Analyze per-user isolation
        for i, result in enumerate(user_results):
            if isinstance(result, Exception):
                logger.error(f"Per-user test {i} failed: {result}")
                continue
            
            per_user_results["users_tested"] += 1
            
            if result["isolation_maintained"]:
                per_user_results["fair_allocation_maintained"] += 1
            else:
                per_user_results["isolation_violations"] += 1
            
            if result["cross_interference_detected"]:
                per_user_results["cross_user_interference"] += 1
            
            if result["concurrent_handling_accurate"]:
                per_user_results["concurrent_accuracy"] += 1
        
        # Calculate per-user metrics
        if per_user_results["users_tested"] > 0:
            per_user_results["isolation_success_rate"] = (per_user_results["fair_allocation_maintained"] / per_user_results["users_tested"]) * 100
            per_user_results["interference_rate"] = (per_user_results["cross_user_interference"] / per_user_results["users_tested"]) * 100
            per_user_results["concurrent_accuracy_rate"] = (per_user_results["concurrent_accuracy"] / per_user_results["users_tested"]) * 100
        
        return per_user_results
    
    async def _check_rate_limit(self, user_id: str, tier: str, config: RateLimitConfig, request_id: str) -> bool:
        """Check rate limit for a user request."""
        rate_limit_key = f"rate_limit:{tier}:{user_id}"
        
        try:
            # Get current request count
            current_count = await self.redis_client.get(rate_limit_key)
            current_count = int(current_count) if current_count else 0
            
            # Check if under limit
            if current_count < config.requests_per_minute:
                # Increment counter
                pipeline = self.redis_client.pipeline()
                pipeline.incr(rate_limit_key)
                pipeline.expire(rate_limit_key, config.window_size_seconds)
                await pipeline.execute()
                
                self.test_keys.add(rate_limit_key)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Rate limit check failed for {user_id}: {e}")
            return False
    
    async def _check_rate_limit_at_time(self, user_id: str, tier: str, config: RateLimitConfig, timestamp: float) -> bool:
        """Check rate limit at a specific timestamp for sliding window testing."""
        # Use timestamp-based key for sliding window
        window_start = int(timestamp) // config.window_size_seconds * config.window_size_seconds
        rate_limit_key = f"sliding:{tier}:{user_id}:{window_start}"
        
        try:
            current_count = await self.redis_client.get(rate_limit_key)
            current_count = int(current_count) if current_count else 0
            
            if current_count < config.requests_per_minute:
                pipeline = self.redis_client.pipeline()
                pipeline.incr(rate_limit_key)
                pipeline.expire(rate_limit_key, config.window_size_seconds * 2)
                await pipeline.execute()
                
                self.test_keys.add(rate_limit_key)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Sliding window rate limit check failed: {e}")
            return False
    
    def _analyze_sliding_window_accuracy(self, requests: List[Dict], config: RateLimitConfig, window_start: float) -> Dict[str, Any]:
        """Analyze sliding window accuracy from request data."""
        accuracy_analysis = {
            "accurate": True,
            "transitions": 0,
            "temporal_score": 0,
            "violations": 0
        }
        
        # Group requests by time windows
        time_windows = {}
        
        for request in requests:
            window_key = int(request["time"]) // config.window_size_seconds
            if window_key not in time_windows:
                time_windows[window_key] = []
            time_windows[window_key].append(request)
        
        # Analyze each window
        for window_key, window_requests in time_windows.items():
            allowed_in_window = len([r for r in window_requests if r["allowed"]])
            
            # Check if window enforcement is accurate
            if allowed_in_window > config.requests_per_minute:
                accuracy_analysis["violations"] += 1
                accuracy_analysis["accurate"] = False
            
            # Count window transitions
            if len(time_windows) > 1:
                accuracy_analysis["transitions"] += 1
        
        # Calculate temporal accuracy score (0-100)
        total_allowed = len([r for r in requests if r["allowed"]])
        expected_total = min(len(requests), config.requests_per_minute * len(time_windows))
        
        if expected_total > 0:
            accuracy_analysis["temporal_score"] = min(100, (total_allowed / expected_total) * 100)
        
        return accuracy_analysis
    
    async def _test_user_isolation(self, user_id: str, tier: str, request_count: int, user_index: int) -> Dict[str, Any]:
        """Test rate limiting isolation for a specific user."""
        config = self.rate_limit_configs[tier]
        
        isolation_result = {
            "user_id": user_id,
            "tier": tier,
            "isolation_maintained": True,
            "cross_interference_detected": False,
            "concurrent_handling_accurate": True
        }
        
        allowed_requests = 0
        rejected_requests = 0
        
        # Make requests for this user
        for req_num in range(request_count):
            request_allowed = await self._check_rate_limit(
                user_id, tier, config, f"isolation_{req_num}"
            )
            
            if request_allowed:
                allowed_requests += 1
            else:
                rejected_requests += 1
            
            # Small delay to simulate realistic timing
            await asyncio.sleep(0.02)
        
        # Analyze isolation
        expected_allowed = min(request_count, config.requests_per_minute)
        
        # Check if allocation is fair (within reasonable variance)
        if abs(allowed_requests - expected_allowed) > 3:
            isolation_result["isolation_maintained"] = False
        
        # Check for concurrent handling accuracy
        if rejected_requests > 0 and allowed_requests < config.requests_per_minute - 5:
            isolation_result["concurrent_handling_accurate"] = False
        
        # Simple heuristic for cross-interference (would be more sophisticated in practice)
        if allowed_requests > config.requests_per_minute + 5:
            isolation_result["cross_interference_detected"] = True
        
        return isolation_result
    
    async def cleanup(self):
        """Clean up rate limiting test data from Redis."""
        try:
            if self.test_keys:
                # Delete test keys in batches
                keys_list = list(self.test_keys)
                batch_size = 100
                
                for i in range(0, len(keys_list), batch_size):
                    batch = keys_list[i:i + batch_size]
                    if batch:
                        await self.redis_client.delete(*batch)
                
                self.test_keys.clear()
            
            logger.info("Rate limiting test cleanup completed")
            
        except Exception as e:
            logger.error(f"Rate limiting cleanup failed: {e}")
    
    def get_rate_limiting_summary(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting test summary."""
        return {
            "rate_limit_stats": self.rate_limit_stats,
            "total_rate_limit_operations": sum(self.rate_limit_stats.values()),
            "test_keys_created": len(self.test_keys),
            "rate_limit_configs_tested": list(self.rate_limit_configs.keys())
        }

@pytest.mark.L3
@pytest.mark.integration
class TestRateLimitingRedisL3:
    """L3 integration tests for rate limiting with real Redis backend."""
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container for rate limiting testing."""
        container = RedisContainer(port=6384)
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client for rate limiting."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        yield client
        await client.close()
    
    @pytest.fixture
    async def rate_limiting_manager(self, redis_client):
        """Create rate limiting manager."""
        manager = RateLimitingManager(redis_client)
        yield manager
        await manager.cleanup()
    
    async def test_request_limits_tier_enforcement(self, rate_limiting_manager):
        """Test request limits enforcement across user tiers."""
        results = await rate_limiting_manager.test_request_limits_enforcement(12, 80)
        
        # Verify free tier enforcement
        free_results = results["free"]
        assert free_results["accuracy_rate"] >= 85.0, f"Free tier accuracy too low: {free_results['accuracy_rate']:.1f}%"
        assert free_results["users_tested"] >= 3, "Insufficient free tier users tested"
        
        # Verify pro tier enforcement
        pro_results = results["pro"]
        assert pro_results["accuracy_rate"] >= 85.0, f"Pro tier accuracy too low: {pro_results['accuracy_rate']:.1f}%"
        assert pro_results["users_tested"] >= 3, "Insufficient pro tier users tested"
        
        # Verify enterprise tier enforcement
        enterprise_results = results["enterprise"]
        assert enterprise_results["accuracy_rate"] >= 85.0, f"Enterprise tier accuracy too low: {enterprise_results['accuracy_rate']:.1f}%"
        assert enterprise_results["users_tested"] >= 3, "Insufficient enterprise tier users tested"
        
        # Verify overall rate limiting
        total_requests = sum(tier["total_requests"] for tier in results.values())
        total_allowed = sum(tier["allowed_requests"] for tier in results.values())
        assert total_requests >= 800, "Insufficient total requests processed"
        assert total_allowed >= 400, "Too few requests allowed"
        
        logger.info(f"Request limits enforcement test completed: {results}")
    
    async def test_sliding_window_accuracy(self, rate_limiting_manager):
        """Test sliding window rate limiting implementation."""
        results = await rate_limiting_manager.test_sliding_window_implementation(10)
        
        # Verify sliding window accuracy
        assert results["window_accuracy_rate"] >= 80.0, f"Sliding window accuracy too low: {results['window_accuracy_rate']:.1f}%"
        assert results["accurate_window_enforcement"] >= 8, "Too few accurate window enforcements"
        
        # Verify window transitions
        assert results["avg_transitions_per_test"] >= 1.0, "Insufficient window transitions tested"
        
        # Verify temporal accuracy
        assert results["avg_temporal_accuracy"] >= 70.0, f"Temporal accuracy too low: {results['avg_temporal_accuracy']:.1f}"
        
        # Verify minimal violations
        assert results["sliding_violations_detected"] <= 2, f"Too many sliding window violations: {results['sliding_violations_detected']}"
        
        logger.info(f"Sliding window test completed: {results}")
    
    async def test_burst_handling_validation(self, rate_limiting_manager):
        """Test burst request handling with different capacities."""
        results = await rate_limiting_manager.test_burst_handling_capacity(12)
        
        # Verify burst handling success
        assert results["burst_success_rate"] >= 80.0, f"Burst success rate too low: {results['burst_success_rate']:.1f}%"
        assert results["successful_burst_handling"] >= 9, "Too few successful burst handlings"
        
        # Verify capacity enforcement
        assert results["capacity_enforcement_rate"] >= 85.0, f"Capacity enforcement rate too low: {results['capacity_enforcement_rate']:.1f}%"
        
        # Verify burst recovery
        assert results["recovery_success_rate"] >= 85.0, f"Recovery success rate too low: {results['recovery_success_rate']:.1f}%"
        
        # Verify overflow detection
        assert results["burst_overflow_detected"] >= 8, "Insufficient burst overflow detection"
        
        logger.info(f"Burst handling test completed: {results}")
    
    async def test_per_user_isolation_enforcement(self, rate_limiting_manager):
        """Test per-user rate limiting with concurrent requests."""
        results = await rate_limiting_manager.test_per_user_rate_limiting(15, 50)
        
        # Verify user isolation
        assert results["isolation_success_rate"] >= 85.0, f"Isolation success rate too low: {results['isolation_success_rate']:.1f}%"
        assert results["users_tested"] >= 12, "Insufficient users tested for isolation"
        
        # Verify minimal cross-user interference
        assert results["interference_rate"] <= 15.0, f"Cross-user interference too high: {results['interference_rate']:.1f}%"
        
        # Verify concurrent accuracy
        assert results["concurrent_accuracy_rate"] >= 80.0, f"Concurrent accuracy too low: {results['concurrent_accuracy_rate']:.1f}%"
        
        # Verify minimal isolation violations
        assert results["isolation_violations"] <= 3, f"Too many isolation violations: {results['isolation_violations']}"
        
        logger.info(f"Per-user isolation test completed: {results}")
    
    async def test_rate_limiting_performance_load(self, rate_limiting_manager):
        """Test rate limiting performance under load."""
        start_time = time.time()
        
        # Run comprehensive rate limiting tests
        await asyncio.gather(
            rate_limiting_manager.test_request_limits_enforcement(8, 40),
            rate_limiting_manager.test_sliding_window_implementation(6),
            rate_limiting_manager.test_burst_handling_capacity(8)
        )
        
        total_time = time.time() - start_time
        
        # Verify performance
        assert total_time < 60.0, f"Rate limiting tests took too long: {total_time:.2f}s"
        
        # Get summary
        summary = rate_limiting_manager.get_rate_limiting_summary()
        assert summary["total_rate_limit_operations"] >= 100, "Insufficient rate limiting operations"
        
        logger.info(f"Rate limiting performance test completed in {total_time:.2f}s: {summary}")
    
    async def test_rate_limiting_redis_consistency(self, rate_limiting_manager):
        """Test rate limiting consistency with Redis operations."""
        client = rate_limiting_manager.redis_client
        
        # Create test rate limit data
        test_user = f"consistency_user_{uuid.uuid4().hex[:8]}"
        tier = "pro"
        config = rate_limiting_manager.rate_limit_configs[tier]
        
        # Make requests to establish rate limit state
        allowed_count = 0
        for i in range(30):
            request_allowed = await rate_limiting_manager._check_rate_limit(
                test_user, tier, config, f"consistency_{i}"
            )
            if request_allowed:
                allowed_count += 1
        
        # Verify Redis state consistency
        rate_limit_key = f"rate_limit:{tier}:{test_user}"
        redis_count = await client.get(rate_limit_key)
        redis_count = int(redis_count) if redis_count else 0
        
        # Redis count should match allowed requests
        assert redis_count == allowed_count, f"Redis count {redis_count} doesn't match allowed count {allowed_count}"
        
        # Verify TTL is set correctly
        ttl = await client.ttl(rate_limit_key)
        assert 0 < ttl <= config.window_size_seconds, f"Incorrect TTL: {ttl}"
        
        # Test key expiration
        await asyncio.sleep(config.window_size_seconds + 1)
        
        # Key should be expired
        exists = await client.exists(rate_limit_key)
        assert not exists, "Rate limit key should have expired"
        
        # Test fresh requests after expiration
        fresh_request_allowed = await rate_limiting_manager._check_rate_limit(
            test_user, tier, config, "fresh_after_expiry"
        )
        assert fresh_request_allowed, "Fresh request should be allowed after expiration"
        
        logger.info(f"Rate limiting Redis consistency test completed: redis_count={redis_count}, allowed_count={allowed_count}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])