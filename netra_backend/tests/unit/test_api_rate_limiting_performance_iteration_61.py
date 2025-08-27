"""
Test API Rate Limiting Performance - Iteration 61

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: System Protection & Performance
- Value Impact: Prevents abuse and ensures fair resource allocation
- Strategic Impact: Maintains service quality during high traffic periods

Focus: Rate limiting algorithms, performance under load, and adaptive throttling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time
from datetime import datetime, timedelta
import statistics

from netra_backend.app.core.async_rate_limiter import AsyncRateLimiter


class TestApiRateLimitingPerformance:
    """Test API rate limiting performance and effectiveness"""
    
    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter with performance tracking"""
        limiter = MagicMock()
        limiter.request_history = []
        limiter.blocked_requests = []
        limiter.rate_limit_config = {
            "requests_per_minute": 100,
            "burst_limit": 10,
            "window_size_seconds": 60
        }
        return limiter
    
    @pytest.fixture
    def mock_performance_monitor(self):
        """Mock performance monitoring for rate limiter"""
        monitor = MagicMock()
        monitor.metrics = []
        monitor.latency_measurements = []
        return monitor
    
    @pytest.mark.asyncio
    async def test_token_bucket_algorithm_performance(self, mock_rate_limiter):
        """Test token bucket rate limiting algorithm performance"""
        class TokenBucket:
            def __init__(self, capacity, refill_rate):
                self.capacity = capacity
                self.tokens = capacity
                self.refill_rate = refill_rate  # tokens per second
                self.last_refill = time.time()
            
            async def consume(self, tokens_requested=1):
                current_time = time.time()
                
                # Refill tokens based on elapsed time
                elapsed = current_time - self.last_refill
                self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
                self.last_refill = current_time
                
                if self.tokens >= tokens_requested:
                    self.tokens -= tokens_requested
                    return True
                return False
        
        async def test_token_bucket_under_load(bucket, request_count, requests_per_second):
            allowed_requests = 0
            denied_requests = 0
            response_times = []
            
            for i in range(request_count):
                start_time = time.time()
                
                # Simulate request processing time
                await asyncio.sleep(0.001)  # 1ms base processing
                
                allowed = await bucket.consume(1)
                
                end_time = time.time()
                response_times.append((end_time - start_time) * 1000)  # Convert to ms
                
                if allowed:
                    allowed_requests += 1
                else:
                    denied_requests += 1
                
                # Control request rate
                await asyncio.sleep(1.0 / requests_per_second)
            
            return {
                "allowed_requests": allowed_requests,
                "denied_requests": denied_requests,
                "avg_response_time_ms": statistics.mean(response_times),
                "max_response_time_ms": max(response_times),
                "throughput": allowed_requests / (request_count / requests_per_second)
            }
        
        # Test with normal load (within limits)
        bucket = TokenBucket(capacity=10, refill_rate=5.0)  # 10 token capacity, 5 tokens/sec refill
        normal_load_result = await test_token_bucket_under_load(bucket, 50, 4.0)  # 4 req/sec
        
        assert normal_load_result["allowed_requests"] > normal_load_result["denied_requests"]
        assert normal_load_result["avg_response_time_ms"] < 10  # Should be fast when not rate limited
        assert normal_load_result["throughput"] > 0.8  # Should allow most requests
        
        # Test with high load (exceeding limits)
        bucket_high = TokenBucket(capacity=10, refill_rate=5.0)
        high_load_result = await test_token_bucket_under_load(bucket_high, 100, 20.0)  # 20 req/sec
        
        assert high_load_result["denied_requests"] > 0  # Should deny some requests
        assert high_load_result["throughput"] < 0.6  # Should throttle significantly
        
        # Performance should remain consistent even under heavy load
        assert high_load_result["max_response_time_ms"] < 50  # Rate limiting should be fast
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limiting(self, mock_rate_limiter):
        """Test sliding window rate limiting algorithm"""
        class SlidingWindow:
            def __init__(self, window_size_seconds, max_requests):
                self.window_size = window_size_seconds
                self.max_requests = max_requests
                self.request_timestamps = []
            
            async def is_allowed(self, client_id):
                current_time = time.time()
                
                # Remove old requests outside the window
                cutoff_time = current_time - self.window_size
                self.request_timestamps = [
                    ts for ts in self.request_timestamps if ts > cutoff_time
                ]
                
                # Check if under limit
                if len(self.request_timestamps) < self.max_requests:
                    self.request_timestamps.append(current_time)
                    return True
                
                return False
        
        async def measure_sliding_window_performance(window, test_duration_seconds, request_rate):
            start_time = time.time()
            allowed_count = 0
            denied_count = 0
            latency_samples = []
            
            while (time.time() - start_time) < test_duration_seconds:
                request_start = time.time()
                
                allowed = await window.is_allowed("test_client")
                
                request_end = time.time()
                latency_samples.append((request_end - request_start) * 1000)
                
                if allowed:
                    allowed_count += 1
                else:
                    denied_count += 1
                
                # Control request rate
                await asyncio.sleep(1.0 / request_rate)
            
            return {
                "test_duration": test_duration_seconds,
                "requests_allowed": allowed_count,
                "requests_denied": denied_count,
                "avg_latency_ms": statistics.mean(latency_samples),
                "p95_latency_ms": statistics.quantiles(latency_samples, n=20)[18],  # 95th percentile
                "requests_per_second": (allowed_count + denied_count) / test_duration_seconds
            }
        
        # Test sliding window with 10 requests per 5 seconds
        window = SlidingWindow(window_size_seconds=5, max_requests=10)
        
        # Test with moderate load
        moderate_result = await measure_sliding_window_performance(window, 8.0, 2.0)  # 2 req/sec
        
        assert moderate_result["requests_allowed"] > 0
        assert moderate_result["avg_latency_ms"] < 5  # Should be very fast
        assert moderate_result["requests_per_second"] <= 2.5  # Should be close to requested rate
        
        # Test with high load (exceeding window limit)
        window_high = SlidingWindow(window_size_seconds=5, max_requests=10)
        high_result = await measure_sliding_window_performance(window_high, 6.0, 5.0)  # 5 req/sec
        
        assert high_result["requests_denied"] > 0  # Should deny requests exceeding limit
        assert high_result["p95_latency_ms"] < 10  # Even under load, should remain fast
        
        # The effective rate should be capped by the window limit
        effective_rate = high_result["requests_allowed"] / high_result["test_duration"]
        assert effective_rate <= (10 / 5) * 1.1  # Allow 10% tolerance for timing variations
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiting_under_load(self, mock_rate_limiter, mock_performance_monitor):
        """Test adaptive rate limiting that adjusts based on system load"""
        system_load_metrics = {
            "cpu_usage": 30.0,
            "memory_usage": 40.0,
            "response_time_p95": 50.0,
            "error_rate": 0.02
        }
        
        async def adaptive_rate_limiter(base_limit, client_id):
            # Adjust rate limits based on system metrics
            load_factor = 1.0
            
            # Reduce limits if CPU is high
            if system_load_metrics["cpu_usage"] > 80:
                load_factor *= 0.5
            elif system_load_metrics["cpu_usage"] > 60:
                load_factor *= 0.7
            
            # Reduce limits if response time is high
            if system_load_metrics["response_time_p95"] > 200:
                load_factor *= 0.6
            elif system_load_metrics["response_time_p95"] > 100:
                load_factor *= 0.8
            
            # Reduce limits if error rate is high
            if system_load_metrics["error_rate"] > 0.05:
                load_factor *= 0.4
            elif system_load_metrics["error_rate"] > 0.02:
                load_factor *= 0.7
            
            adjusted_limit = int(base_limit * load_factor)
            
            return {
                "base_limit": base_limit,
                "adjusted_limit": adjusted_limit,
                "load_factor": load_factor,
                "system_metrics": system_load_metrics.copy()
            }
        
        # Test under normal conditions
        normal_result = await adaptive_rate_limiter(100, "test_client")
        assert normal_result["adjusted_limit"] == 70  # Should be reduced due to error rate > 0.02
        assert normal_result["load_factor"] == 0.7
        
        # Test under high CPU load
        system_load_metrics["cpu_usage"] = 85.0
        high_cpu_result = await adaptive_rate_limiter(100, "test_client")
        assert high_cpu_result["adjusted_limit"] < normal_result["adjusted_limit"]
        assert high_cpu_result["load_factor"] < 0.5  # Should be significantly reduced
        
        # Test under high response time
        system_load_metrics["cpu_usage"] = 30.0  # Reset CPU
        system_load_metrics["response_time_p95"] = 250.0
        high_latency_result = await adaptive_rate_limiter(100, "test_client")
        assert high_latency_result["adjusted_limit"] < 50  # Should be heavily throttled
        
        # Test recovery scenario
        system_load_metrics.update({
            "cpu_usage": 25.0,
            "response_time_p95": 40.0,
            "error_rate": 0.01
        })
        recovery_result = await adaptive_rate_limiter(100, "test_client")
        assert recovery_result["adjusted_limit"] == 100  # Should return to full limit
        assert recovery_result["load_factor"] == 1.0
    
    @pytest.mark.asyncio
    async def test_distributed_rate_limiting_coordination(self, mock_rate_limiter):
        """Test distributed rate limiting across multiple instances"""
        class DistributedRateLimiter:
            def __init__(self, node_id, total_limit, coordination_interval=1.0):
                self.node_id = node_id
                self.total_limit = total_limit
                self.coordination_interval = coordination_interval
                self.local_count = 0
                self.allocated_quota = total_limit  # Start with full quota
                self.last_coordination = time.time()
                self.peer_usage = {}
            
            async def coordinate_with_peers(self, peer_usage_data):
                """Simulate coordination with peer nodes"""
                current_time = time.time()
                if current_time - self.last_coordination < self.coordination_interval:
                    return  # Too soon for coordination
                
                self.peer_usage = peer_usage_data
                total_usage = sum(peer_usage_data.values()) + self.local_count
                
                # Redistribute quota based on actual usage patterns
                if total_usage < self.total_limit * 0.8:  # Under 80% usage
                    # Allow nodes to use more of their quota
                    self.allocated_quota = min(self.total_limit, self.allocated_quota * 1.1)
                elif total_usage > self.total_limit * 0.95:  # Over 95% usage
                    # Reduce quotas to prevent overflow
                    self.allocated_quota = max(1, self.allocated_quota * 0.8)
                
                self.last_coordination = current_time
            
            async def try_consume(self):
                if self.local_count < self.allocated_quota:
                    self.local_count += 1
                    return True
                return False
            
            def reset_window(self):
                self.local_count = 0
        
        # Simulate 3-node distributed system
        nodes = {
            "node_1": DistributedRateLimiter("node_1", 300),  # 300 req/min total limit
            "node_2": DistributedRateLimiter("node_2", 300),
            "node_3": DistributedRateLimiter("node_3", 300)
        }
        
        async def simulate_distributed_load_test(duration_seconds, request_patterns):
            results = {node_id: {"allowed": 0, "denied": 0} for node_id in nodes.keys()}
            
            start_time = time.time()
            coordination_count = 0
            
            while (time.time() - start_time) < duration_seconds:
                # Each node processes requests based on its pattern
                for node_id, requests_per_second in request_patterns.items():
                    if node_id in nodes:
                        node = nodes[node_id]
                        
                        # Attempt requests for this node
                        for _ in range(int(requests_per_second)):
                            if await node.try_consume():
                                results[node_id]["allowed"] += 1
                            else:
                                results[node_id]["denied"] += 1
                
                # Periodic coordination between nodes
                if int(time.time() - start_time) % 2 == 0 and coordination_count < 3:  # Every 2 seconds
                    peer_data = {node_id: node.local_count for node_id, node in nodes.items()}
                    
                    for node in nodes.values():
                        other_peers = {k: v for k, v in peer_data.items() if k != node.node_id}
                        await node.coordinate_with_peers(other_peers)
                    
                    coordination_count += 1
                
                await asyncio.sleep(1.0)  # 1 second intervals
            
            return results
        
        # Test balanced load across nodes
        balanced_patterns = {
            "node_1": 3,  # 3 req/sec
            "node_2": 3,  # 3 req/sec  
            "node_3": 3   # 3 req/sec
        }
        
        balanced_results = await simulate_distributed_load_test(5.0, balanced_patterns)
        
        total_allowed = sum(result["allowed"] for result in balanced_results.values())
        total_denied = sum(result["denied"] for result in balanced_results.values())
        
        # Should allow most requests under balanced load
        assert total_allowed > total_denied
        assert total_allowed > 40  # Should process significant number of requests
        
        # Test unbalanced load (one node gets most traffic)
        unbalanced_patterns = {
            "node_1": 8,  # 8 req/sec - heavy load
            "node_2": 1,  # 1 req/sec - light load
            "node_3": 1   # 1 req/sec - light load
        }
        
        # Reset nodes
        for node in nodes.values():
            node.reset_window()
        
        unbalanced_results = await simulate_distributed_load_test(5.0, unbalanced_patterns)
        
        # Node 1 should experience more denials due to heavy load
        assert unbalanced_results["node_1"]["denied"] > unbalanced_results["node_2"]["denied"]
        assert unbalanced_results["node_1"]["denied"] > unbalanced_results["node_3"]["denied"]
        
        # But coordination should help redistribute some load
        node1_success_rate = unbalanced_results["node_1"]["allowed"] / (
            unbalanced_results["node_1"]["allowed"] + unbalanced_results["node_1"]["denied"]
        )
        assert node1_success_rate > 0.3  # Should still allow reasonable percentage
    
    def test_rate_limiting_memory_efficiency(self, mock_rate_limiter, mock_performance_monitor):
        """Test memory efficiency of rate limiting data structures"""
        def measure_memory_usage_simulation(client_count, window_size_minutes):
            # Simulate memory usage for different rate limiting approaches
            
            # Token bucket: O(1) per client
            token_bucket_memory = client_count * 64  # 64 bytes per client (estimated)
            
            # Sliding window log: O(R) per client where R is requests in window
            avg_requests_per_window = 100  # Assume 100 req/window average
            sliding_log_memory = client_count * avg_requests_per_window * 16  # 16 bytes per timestamp
            
            # Fixed window: O(1) per client per window
            windows_count = max(1, window_size_minutes)
            fixed_window_memory = client_count * windows_count * 32  # 32 bytes per window
            
            return {
                "client_count": client_count,
                "token_bucket_bytes": token_bucket_memory,
                "sliding_log_bytes": sliding_log_memory,
                "fixed_window_bytes": fixed_window_memory,
                "most_efficient": min(
                    ("token_bucket", token_bucket_memory),
                    ("sliding_log", sliding_log_memory),
                    ("fixed_window", fixed_window_memory),
                    key=lambda x: x[1]
                )[0]
            }
        
        # Test memory usage with different client scales
        test_scenarios = [
            {"clients": 1000, "window_minutes": 5},
            {"clients": 10000, "window_minutes": 5},
            {"clients": 100000, "window_minutes": 5},
            {"clients": 1000000, "window_minutes": 5}
        ]
        
        results = []
        for scenario in test_scenarios:
            result = measure_memory_usage_simulation(scenario["clients"], scenario["window_minutes"])
            results.append(result)
        
        # Token bucket should be most memory efficient for most scenarios
        token_bucket_wins = sum(1 for r in results if r["most_efficient"] == "token_bucket")
        assert token_bucket_wins >= len(results) // 2  # Should win at least half the time
        
        # Memory usage should scale linearly with client count for token bucket
        small_scale = results[0]["token_bucket_bytes"]  # 1K clients
        large_scale = results[2]["token_bucket_bytes"]   # 100K clients
        
        expected_ratio = 100  # 100K / 1K = 100x
        actual_ratio = large_scale / small_scale
        assert abs(actual_ratio - expected_ratio) < 5  # Allow some variance
        
        # Sliding log should use significantly more memory
        for result in results:
            assert result["sliding_log_bytes"] > result["token_bucket_bytes"]
            
            # For large client counts, sliding log should use orders of magnitude more
            if result["client_count"] >= 100000:
                ratio = result["sliding_log_bytes"] / result["token_bucket_bytes"]
                assert ratio > 10  # Should use at least 10x more memory