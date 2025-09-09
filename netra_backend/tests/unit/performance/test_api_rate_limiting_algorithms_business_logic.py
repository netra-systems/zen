"""
Test API Rate Limiting Algorithms Business Logic

Business Value Justification (BVJ):
- Segment: All customer segments (platform stability)
- Business Goal: Ensure fair resource usage and prevent service abuse
- Value Impact: Rate limiting prevents outages and maintains service quality
- Strategic Impact: Enables tiered pricing models and prevents resource exhaustion

CRITICAL REQUIREMENTS:
- Tests pure business logic for rate limiting algorithms
- Validates sliding window, token bucket, and leaky bucket implementations
- No external dependencies or infrastructure needed
- Ensures mathematical correctness of rate limiting formulas
"""

import pytest
import time
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass
from collections import deque

from netra_backend.app.services.rate_limiting.rate_limiter import (
    RateLimiter,
    RateLimitResult,
    RateLimitAlgorithm,
    WindowType
)
from netra_backend.app.services.rate_limiting.token_bucket import (
    TokenBucket,
    TokenBucketConfig,
    TokenRefillStrategy
)
from netra_backend.app.services.rate_limiting.sliding_window import (
    SlidingWindow,
    SlidingWindowConfig,
    WindowSlice
)


@dataclass
class MockAPIRequest:
    """Mock API request for rate limiting testing"""
    user_id: str
    endpoint: str
    timestamp: datetime
    request_size_bytes: int
    user_tier: str
    priority: int  # 1-5, higher is more important
    source_ip: str


@dataclass
class MockRateLimitConfig:
    """Mock rate limit configuration"""
    requests_per_minute: int
    burst_limit: int
    window_size_seconds: int
    tier_multipliers: Dict[str, float]  # Multipliers for different user tiers


class TestAPIRateLimitingAlgorithmsBusinessLogic:
    """Test API rate limiting algorithms business logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.rate_limiter = RateLimiter()
        self.test_timestamp = datetime.now(timezone.utc)
        
        # Define rate limit configurations for different scenarios
        self.rate_limit_configs = {
            "standard": MockRateLimitConfig(
                requests_per_minute=60,
                burst_limit=20,
                window_size_seconds=60,
                tier_multipliers={
                    "free": 1.0,
                    "early": 2.0,
                    "mid": 5.0,
                    "enterprise": 10.0
                }
            ),
            "strict": MockRateLimitConfig(
                requests_per_minute=30,
                burst_limit=10,
                window_size_seconds=60,
                tier_multipliers={
                    "free": 1.0,
                    "early": 1.5,
                    "mid": 3.0,
                    "enterprise": 5.0
                }
            ),
            "lenient": MockRateLimitConfig(
                requests_per_minute=120,
                burst_limit=50,
                window_size_seconds=60,
                tier_multipliers={
                    "free": 1.0,
                    "early": 2.0,
                    "mid": 4.0,
                    "enterprise": 8.0
                }
            )
        }
    
    def _generate_request_sequence(self, 
                                 user_id: str, 
                                 num_requests: int, 
                                 time_span_seconds: int,
                                 tier: str = "free",
                                 distribution: str = "uniform") -> List[MockAPIRequest]:
        """Generate a sequence of API requests for testing"""
        requests = []
        base_time = self.test_timestamp
        
        if distribution == "uniform":
            # Evenly spaced requests
            interval = time_span_seconds / num_requests if num_requests > 1 else 0
            for i in range(num_requests):
                timestamp = base_time + timedelta(seconds=i * interval)
                requests.append(MockAPIRequest(
                    user_id=user_id,
                    endpoint="/api/agents/execute",
                    timestamp=timestamp,
                    request_size_bytes=1024,
                    user_tier=tier,
                    priority=3,
                    source_ip="192.168.1.100"
                ))
        
        elif distribution == "burst":
            # All requests in rapid succession
            for i in range(num_requests):
                timestamp = base_time + timedelta(milliseconds=i * 100)  # 100ms apart
                requests.append(MockAPIRequest(
                    user_id=user_id,
                    endpoint="/api/agents/execute",
                    timestamp=timestamp,
                    request_size_bytes=1024,
                    user_tier=tier,
                    priority=3,
                    source_ip="192.168.1.100"
                ))
        
        elif distribution == "spike":
            # Most requests in a short spike, then scattered
            spike_size = int(num_requests * 0.7)  # 70% in spike
            
            # Spike requests
            for i in range(spike_size):
                timestamp = base_time + timedelta(milliseconds=i * 50)  # 50ms apart
                requests.append(MockAPIRequest(
                    user_id=user_id,
                    endpoint="/api/agents/execute",
                    timestamp=timestamp,
                    request_size_bytes=1024,
                    user_tier=tier,
                    priority=3,
                    source_ip="192.168.1.100"
                ))
            
            # Scattered requests
            remaining = num_requests - spike_size
            for i in range(remaining):
                timestamp = base_time + timedelta(seconds=10 + i * 5)  # Scattered over time
                requests.append(MockAPIRequest(
                    user_id=user_id,
                    endpoint="/api/agents/execute",
                    timestamp=timestamp,
                    request_size_bytes=1024,
                    user_tier=tier,
                    priority=3,
                    source_ip="192.168.1.100"
                ))
        
        return requests
    
    def test_token_bucket_algorithm_comprehensive(self):
        """Test token bucket rate limiting algorithm comprehensively"""
        # Test basic token bucket behavior
        bucket_config = TokenBucketConfig(
            capacity=10,  # 10 tokens maximum
            refill_rate=1.0,  # 1 token per second
            initial_tokens=10  # Start full
        )
        
        token_bucket = TokenBucket(bucket_config)
        
        # Should allow requests when tokens are available
        for i in range(10):
            result = token_bucket.try_consume(1)
            assert result.allowed is True, f"Request {i} should be allowed"
            assert result.remaining_tokens == 9 - i
            assert result.retry_after_seconds == 0
        
        # Should deny request when no tokens available
        result = token_bucket.try_consume(1)
        assert result.allowed is False
        assert result.remaining_tokens == 0
        assert result.retry_after_seconds > 0
        
        # Test token refill
        # Advance time to allow token refill
        with patch('time.time', return_value=time.time() + 5):
            # Should have refilled 5 tokens
            result = token_bucket.try_consume(1)
            assert result.allowed is True
            assert result.remaining_tokens == 4  # Had 0, refilled 5, consumed 1
        
        # Test burst handling
        burst_bucket = TokenBucket(TokenBucketConfig(
            capacity=20,
            refill_rate=2.0,  # 2 tokens per second
            initial_tokens=20
        ))
        
        # Should handle burst of requests up to capacity
        burst_requests = 15
        allowed_count = 0
        
        for i in range(burst_requests):
            result = burst_bucket.try_consume(1)
            if result.allowed:
                allowed_count += 1
        
        assert allowed_count == burst_requests  # All should be allowed initially
        
        # Additional requests should be denied
        result = burst_bucket.try_consume(1)
        while result.allowed:
            result = burst_bucket.try_consume(1)
        
        assert result.allowed is False
        assert result.remaining_tokens < 5  # Should be low on tokens
    
    def test_sliding_window_algorithm_comprehensive(self):
        """Test sliding window rate limiting algorithm comprehensively"""
        window_config = SlidingWindowConfig(
            window_size_seconds=60,  # 60-second window
            max_requests=100,  # 100 requests per window
            slice_size_seconds=10   # 10-second slices
        )
        
        sliding_window = SlidingWindow(window_config)
        
        # Test normal request pattern within limits
        normal_requests = self._generate_request_sequence(
            user_id="user_001",
            num_requests=50,  # Well under limit
            time_span_seconds=60,
            distribution="uniform"
        )
        
        allowed_count = 0
        for request in normal_requests:
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = request.timestamp
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                result = sliding_window.check_rate_limit(
                    user_id=request.user_id,
                    timestamp=request.timestamp
                )
                
                if result.allowed:
                    allowed_count += 1
        
        # All requests should be allowed
        assert allowed_count == len(normal_requests)
        
        # Test burst pattern exceeding limits
        burst_requests = self._generate_request_sequence(
            user_id="user_002",
            num_requests=120,  # Exceeds limit of 100
            time_span_seconds=30,  # In half the window
            distribution="burst"
        )
        
        allowed_count = 0
        denied_count = 0
        
        for request in burst_requests:
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = request.timestamp
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                result = sliding_window.check_rate_limit(
                    user_id=request.user_id,
                    timestamp=request.timestamp
                )
                
                if result.allowed:
                    allowed_count += 1
                    sliding_window.record_request(request.user_id, request.timestamp)
                else:
                    denied_count += 1
        
        # Should allow up to limit and deny excess
        assert allowed_count <= window_config.max_requests
        assert denied_count > 0  # Some requests should be denied
        assert allowed_count + denied_count == len(burst_requests)
    
    def test_tier_based_rate_limiting_algorithms(self):
        """Test tier-based rate limiting algorithms"""
        config = self.rate_limit_configs["standard"]
        
        # Test different user tiers
        tiers_to_test = ["free", "early", "mid", "enterprise"]
        
        for tier in tiers_to_test:
            # Calculate tier-specific limits
            base_limit = config.requests_per_minute
            tier_multiplier = config.tier_multipliers[tier]
            tier_limit = int(base_limit * tier_multiplier)
            
            # Generate requests up to tier limit
            requests = self._generate_request_sequence(
                user_id=f"user_{tier}",
                num_requests=tier_limit,
                time_span_seconds=60,
                tier=tier,
                distribution="uniform"
            )
            
            # Test tier-specific rate limiting
            allowed_count = 0
            for request in requests:
                result = self.rate_limiter.check_tier_based_limit(
                    request=request,
                    config=config
                )
                
                if result.allowed:
                    allowed_count += 1
            
            # Should allow all requests within tier limit
            assert allowed_count == tier_limit, f"Tier {tier} should allow {tier_limit} requests"
            
            # Test one additional request (should be denied)
            extra_request = MockAPIRequest(
                user_id=f"user_{tier}",
                endpoint="/api/agents/execute",
                timestamp=self.test_timestamp + timedelta(seconds=59),
                request_size_bytes=1024,
                user_tier=tier,
                priority=3,
                source_ip="192.168.1.100"
            )
            
            result = self.rate_limiter.check_tier_based_limit(
                request=extra_request,
                config=config
            )
            
            # Additional request should be denied
            assert result.allowed is False, f"Tier {tier} should deny request exceeding limit"
            assert result.retry_after_seconds > 0
            
            # Enterprise tier should have the highest limit
            if tier == "enterprise":
                enterprise_limit = tier_limit
            elif tier == "free":
                free_limit = tier_limit
        
        # Validate tier hierarchy
        assert config.tier_multipliers["enterprise"] > config.tier_multipliers["mid"]
        assert config.tier_multipliers["mid"] > config.tier_multipliers["early"]
        assert config.tier_multipliers["early"] > config.tier_multipliers["free"]
    
    def test_leaky_bucket_algorithm(self):
        """Test leaky bucket rate limiting algorithm"""
        from netra_backend.app.services.rate_limiting.leaky_bucket import (
            LeakyBucket, LeakyBucketConfig
        )
        
        # Configure leaky bucket
        bucket_config = LeakyBucketConfig(
            capacity=50,  # 50 request capacity
            leak_rate=1.0,  # 1 request per second leak rate
            overflow_strategy="reject"  # Reject when full
        )
        
        leaky_bucket = LeakyBucket(bucket_config)
        
        # Test steady rate within leak capacity
        steady_requests = self._generate_request_sequence(
            user_id="user_steady",
            num_requests=60,  # More than capacity but spread over time
            time_span_seconds=60,  # 1 request per second average
            distribution="uniform"
        )
        
        allowed_count = 0
        current_time = time.time()
        
        for i, request in enumerate(steady_requests):
            # Simulate time passage
            request_time = current_time + i
            
            with patch('time.time', return_value=request_time):
                result = leaky_bucket.add_request(request)
                
                if result.allowed:
                    allowed_count += 1
        
        # Should allow most requests at steady rate
        assert allowed_count >= 50  # Should handle most of the steady flow
        
        # Test burst scenario
        burst_requests = self._generate_request_sequence(
            user_id="user_burst",
            num_requests=100,  # High burst
            time_span_seconds=5,   # Very short time
            distribution="burst"
        )
        
        leaky_bucket_burst = LeakyBucket(bucket_config)
        burst_allowed = 0
        burst_denied = 0
        
        for request in burst_requests:
            result = leaky_bucket_burst.add_request(request)
            
            if result.allowed:
                burst_allowed += 1
            else:
                burst_denied += 1
        
        # Should allow up to capacity and deny excess
        assert burst_allowed <= bucket_config.capacity
        assert burst_denied > 0  # Some should be denied in burst scenario
        
        # Test leak behavior over time
        # Fill the bucket
        for _ in range(bucket_config.capacity):
            result = leaky_bucket.add_request(MockAPIRequest(
                "user_test", "/api/test", datetime.now(timezone.utc),
                1024, "free", 3, "127.0.0.1"
            ))
        
        # Bucket should be full
        assert leaky_bucket.current_level == bucket_config.capacity
        
        # Simulate time passage to allow leaking
        with patch('time.time', return_value=time.time() + 10):
            leaky_bucket._leak()  # Manual leak for testing
            
            # Should have leaked some requests
            assert leaky_bucket.current_level < bucket_config.capacity
    
    def test_adaptive_rate_limiting_algorithms(self):
        """Test adaptive rate limiting algorithms"""
        from netra_backend.app.services.rate_limiting.adaptive_limiter import (
            AdaptiveRateLimiter, AdaptiveLimitConfig
        )
        
        adaptive_config = AdaptiveLimitConfig(
            base_limit=100,  # Base requests per minute
            min_limit=50,    # Minimum limit
            max_limit=200,   # Maximum limit
            adaptation_factor=0.1,  # 10% adjustment
            response_time_threshold=500,  # 500ms threshold
            error_rate_threshold=0.05     # 5% error rate threshold
        )
        
        adaptive_limiter = AdaptiveRateLimiter(adaptive_config)
        
        # Test adaptation to high response times
        high_latency_metrics = {
            "avg_response_time_ms": 800,  # Above threshold
            "error_rate": 0.02,           # Below threshold
            "cpu_utilization": 0.70,
            "memory_utilization": 0.60
        }
        
        new_limit = adaptive_limiter.adapt_limit(
            current_metrics=high_latency_metrics,
            current_limit=100
        )
        
        # Should reduce limit due to high response time
        assert new_limit < 100
        assert new_limit >= adaptive_config.min_limit
        
        # Test adaptation to high error rates
        high_error_metrics = {
            "avg_response_time_ms": 200,  # Below threshold
            "error_rate": 0.08,           # Above threshold
            "cpu_utilization": 0.65,
            "memory_utilization": 0.55
        }
        
        new_limit = adaptive_limiter.adapt_limit(
            current_metrics=high_error_metrics,
            current_limit=100
        )
        
        # Should reduce limit due to high error rate
        assert new_limit < 100
        
        # Test adaptation to good performance
        good_metrics = {
            "avg_response_time_ms": 150,  # Below threshold
            "error_rate": 0.01,           # Below threshold
            "cpu_utilization": 0.40,
            "memory_utilization": 0.35
        }
        
        new_limit = adaptive_limiter.adapt_limit(
            current_metrics=good_metrics,
            current_limit=100
        )
        
        # Should increase limit due to good performance
        assert new_limit > 100
        assert new_limit <= adaptive_config.max_limit
    
    def test_distributed_rate_limiting_algorithms(self):
        """Test distributed rate limiting algorithms"""
        from netra_backend.app.services.rate_limiting.distributed_limiter import (
            DistributedRateLimiter, DistributedLimitConfig
        )
        
        distributed_config = DistributedLimitConfig(
            global_limit=1000,  # Global limit across all nodes
            local_limit=100,    # Local limit per node
            sync_interval_seconds=5,  # Sync every 5 seconds
            node_count=10       # 10 nodes in cluster
        )
        
        # Test local vs global limiting
        distributed_limiter = DistributedRateLimiter(distributed_config, node_id="node_01")
        
        # Test local rate limiting first
        local_requests = self._generate_request_sequence(
            user_id="user_distributed",
            num_requests=80,  # Under local limit
            time_span_seconds=60,
            distribution="uniform"
        )
        
        local_allowed = 0
        for request in local_requests:
            result = distributed_limiter.check_local_limit(request)
            if result.allowed:
                local_allowed += 1
                distributed_limiter.record_local_request(request)
        
        # Should allow all requests under local limit
        assert local_allowed == len(local_requests)
        
        # Test global limit coordination
        # Simulate other nodes using their share of global limit
        other_nodes_usage = {
            "node_02": 120,
            "node_03": 115,
            "node_04": 90,
            "node_05": 100,
            "node_06": 110,
            "node_07": 95,
            "node_08": 105,
            "node_09": 85,
            "node_10": 80
        }
        
        total_other_usage = sum(other_nodes_usage.values())
        remaining_global_capacity = distributed_config.global_limit - total_other_usage
        
        # Current node should be limited by remaining global capacity
        global_limit_check = distributed_limiter.check_global_limit(
            local_usage=local_allowed,
            global_usage=total_other_usage
        )
        
        if remaining_global_capacity <= 0:
            assert global_limit_check.allowed is False
        else:
            max_additional = min(remaining_global_capacity, distributed_config.local_limit - local_allowed)
            assert global_limit_check.remaining_capacity <= max_additional
    
    def test_priority_based_rate_limiting_algorithms(self):
        """Test priority-based rate limiting algorithms"""
        from netra_backend.app.services.rate_limiting.priority_limiter import (
            PriorityRateLimiter, PriorityLimitConfig
        )
        
        priority_config = PriorityLimitConfig(
            total_capacity=100,
            priority_weights={
                5: 0.4,  # High priority: 40% of capacity
                4: 0.3,  # Medium-high: 30%
                3: 0.2,  # Medium: 20%
                2: 0.1,  # Low: 10%
                1: 0.0   # Very low: 0% (only if capacity available)
            },
            spillover_enabled=True  # Allow lower priority to use unused high priority capacity
        )
        
        priority_limiter = PriorityRateLimiter(priority_config)
        
        # Generate requests with different priorities
        priority_requests = []
        priorities = [5, 4, 3, 2, 1]
        requests_per_priority = 30  # 30 requests each = 150 total (exceeds capacity)
        
        for priority in priorities:
            priority_batch = self._generate_request_sequence(
                user_id=f"user_priority_{priority}",
                num_requests=requests_per_priority,
                time_span_seconds=60,
                distribution="uniform"
            )
            
            for request in priority_batch:
                request.priority = priority
                priority_requests.append(request)
        
        # Sort by priority (highest first)
        priority_requests.sort(key=lambda r: r.priority, reverse=True)
        
        # Process requests and track by priority
        allowed_by_priority = {p: 0 for p in priorities}
        denied_by_priority = {p: 0 for p in priorities}
        
        for request in priority_requests:
            result = priority_limiter.check_priority_limit(request)
            
            if result.allowed:
                allowed_by_priority[request.priority] += 1
                priority_limiter.record_request(request)
            else:
                denied_by_priority[request.priority] += 1
        
        # Validate priority allocation
        # High priority (5) should get most of its requests
        high_priority_allowed = allowed_by_priority[5]
        expected_high_priority = int(priority_config.total_capacity * priority_config.priority_weights[5])
        
        assert high_priority_allowed >= expected_high_priority * 0.8  # At least 80% of allocation
        
        # Low priority (1) should get few or no requests when capacity is exceeded
        low_priority_allowed = allowed_by_priority[1]
        assert low_priority_allowed <= requests_per_priority * 0.2  # At most 20%
        
        # Total allowed should not exceed capacity
        total_allowed = sum(allowed_by_priority.values())
        assert total_allowed <= priority_config.total_capacity
        
        # Higher priorities should generally get more requests than lower priorities
        assert allowed_by_priority[5] >= allowed_by_priority[4]
        assert allowed_by_priority[4] >= allowed_by_priority[3]
        assert allowed_by_priority[3] >= allowed_by_priority[2]
        assert allowed_by_priority[2] >= allowed_by_priority[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])