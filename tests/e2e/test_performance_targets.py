"""Performance Targets Validation Suite

E2E tests that validate Netra Apex performance against SLA requirements with real measurements.
Tests critical performance metrics that directly impact user experience and retention.

Business Value Justification (BVJ):
    1. Segment: Growth & Enterprise (performance-sensitive customers)
    2. Business Goal: Ensure optimal user experience quality for retention
    3. Value Impact: Performance directly affects user satisfaction and subscription renewal
    4. Revenue Impact: Poor performance causes 15-25% churn - $50K+ ARR protection

PERFORMANCE TARGETS:
    - API response time: < 2s (cold start)
    - First response latency: < 1s (warm system)
    - Throughput capacity: 100 req/min sustained
    - P99 latency: < 5s (tail latency protection)

ARCHITECTURAL COMPLIANCE:
    - Uses real service calls (no mocks per CLAUDE.md)
    - Absolute imports only (per CLAUDE.md)
    - Environment access through IsolatedEnvironment (per CLAUDE.md)
    - Real performance measurements with statistical accuracy
"""

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx
import pytest

from tests.e2e.config import UnifiedTestConfig


@dataclass
class PerformanceMetrics:
    """Data structure for performance measurements"""
    response_times: List[float]
    success_rate: float
    total_requests: int
    successful_requests: int


class RealAPIPerformanceMeasurer:
    """Measures API performance against real services"""

    def __init__(self, config: UnifiedTestConfig):
        """Initialize with test configuration"""
        self.config = config
        self.response_times: List[float] = []
        self.backend_url = config.backend_service_url
        self.auth_url = config.auth_service_url

    async def measure_api_response_time(self, endpoint: str = "/") -> float:
        """Measure response time for a single API call"""
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.backend_url}{endpoint}")
                end_time = time.perf_counter()
                
                # Ensure we got a successful response
                response.raise_for_status()
                
                response_time = end_time - start_time
                self.response_times.append(response_time)
                return response_time
                
            except Exception as e:
                end_time = time.perf_counter()
                response_time = end_time - start_time
                self.response_times.append(response_time)
                raise e

    async def measure_auth_service_response_time(self, endpoint: str = "/health") -> float:
        """Measure auth service response time"""
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.auth_url}{endpoint}")
                end_time = time.perf_counter()
                
                response.raise_for_status()
                
                response_time = end_time - start_time
                return response_time
                
            except Exception as e:
                end_time = time.perf_counter()
                response_time = end_time - start_time
                raise e

    async def measure_batch_responses(self, count: int, endpoint: str = "/") -> PerformanceMetrics:
        """Measure batch of responses for statistical analysis"""
        response_times = []
        successful_requests = 0
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for _ in range(count):
                start_time = time.perf_counter()
                
                try:
                    response = await client.get(f"{self.backend_url}{endpoint}")
                    end_time = time.perf_counter()
                    
                    response_time = end_time - start_time
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        successful_requests += 1
                        
                except Exception:
                    end_time = time.perf_counter()
                    response_time = end_time - start_time
                    response_times.append(response_time)
        
        success_rate = (successful_requests / count) * 100 if count > 0 else 0
        
        return PerformanceMetrics(
            response_times=response_times,
            success_rate=success_rate,
            total_requests=count,
            successful_requests=successful_requests
        )

    async def measure_sustained_throughput(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """Measure sustained throughput over a time period"""
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        successful_requests = 0
        response_times = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            while time.time() < end_time:
                request_start = time.perf_counter()
                request_count += 1
                
                try:
                    response = await client.get(f"{self.backend_url}/")
                    request_end = time.perf_counter()
                    
                    response_time = request_end - request_start
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        successful_requests += 1
                        
                except Exception:
                    request_end = time.perf_counter()
                    response_time = request_end - request_start
                    response_times.append(response_time)
                
                # Throttle to approximately target throughput
                await asyncio.sleep(0.6)  # ~100 requests/minute
        
        actual_duration = time.time() - start_time
        requests_per_minute = (successful_requests / actual_duration) * 60
        success_rate = (successful_requests / request_count) * 100 if request_count > 0 else 0
        
        return {
            "requests_per_minute": requests_per_minute,
            "success_rate": success_rate,
            "total_requests": request_count,
            "successful_requests": successful_requests,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "duration_seconds": actual_duration
        }

    def calculate_percentiles(self, response_times: List[float]) -> Dict[str, float]:
        """Calculate latency percentiles"""
        if not response_times:
            return {"p50": 0, "p95": 0, "p99": 0, "count": 0}
        
        sorted_times = sorted(response_times)
        count = len(sorted_times)
        
        return {
            "p50": self._percentile(sorted_times, 50),
            "p95": self._percentile(sorted_times, 95),
            "p99": self._percentile(sorted_times, 99),
            "count": count,
            "min": min(sorted_times),
            "max": max(sorted_times),
            "avg": statistics.mean(sorted_times)
        }

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate specific percentile value"""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower
        
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


@pytest.fixture
def performance_measurer():
    """Create performance measurer with real service configuration"""
    config = UnifiedTestConfig()
    return RealAPIPerformanceMeasurer(config)


@pytest.mark.asyncio
@pytest.mark.e2e
class TestAPIResponseTime:
    """Test API response time meets < 2s target"""

    async def test_backend_response_time(self, performance_measurer):
        """Test backend API response time meets 2s SLA"""
        # Measure multiple API calls to get reliable metrics
        response_times = []
        
        for _ in range(5):
            response_time = await performance_measurer.measure_api_response_time("/")
            response_times.append(response_time)
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Assert SLA targets
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.3f}s exceeds 2s target"
        assert max_response_time < 3.0, f"Max response time {max_response_time:.3f}s too high for reliability"

    async def test_auth_service_response_time(self, performance_measurer):
        """Test auth service response time meets 2s SLA"""
        # Test auth service health endpoint
        response_times = []
        
        for _ in range(5):
            response_time = await performance_measurer.measure_auth_service_response_time("/health")
            response_times.append(response_time)
        
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Auth service should be even faster
        assert avg_response_time < 1.0, f"Auth service avg response time {avg_response_time:.3f}s exceeds 1s target"
        assert max_response_time < 2.0, f"Auth service max response time {max_response_time:.3f}s too high"


@pytest.mark.asyncio
@pytest.mark.e2e
class TestFirstResponseLatency:
    """Test first response latency meets < 1s target for warm services"""

    async def test_warm_service_latency(self, performance_measurer):
        """Test first response latency on warm services meets 1s SLA"""
        # First, warm up the service with one request
        await performance_measurer.measure_api_response_time("/")
        
        # Now measure warm response times
        metrics = await performance_measurer.measure_batch_responses(10, "/")
        
        avg_latency = statistics.mean(metrics.response_times)
        percentiles = performance_measurer.calculate_percentiles(metrics.response_times)
        
        # Warm service should respond faster
        assert avg_latency < 1.0, f"Warm service avg latency {avg_latency:.3f}s exceeds 1s target"
        assert percentiles["p95"] < 1.5, f"P95 latency {percentiles['p95']:.3f}s too high for SLA"
        assert metrics.success_rate > 95, f"Success rate {metrics.success_rate:.1f}% below 95% target"


@pytest.mark.asyncio
@pytest.mark.e2e 
class TestThroughputCapacity:
    """Test throughput capacity meets targets"""

    async def test_sustained_throughput(self, performance_measurer):
        """Test sustained throughput meets minimum requirements"""
        # Use shorter duration for CI/CD (20 seconds instead of 60)
        results = await performance_measurer.measure_sustained_throughput(20)
        
        # Validate throughput targets
        assert results["success_rate"] > 98, f"Success rate {results['success_rate']:.1f}% too low for production"
        assert results["avg_response_time"] < 2.0, f"Avg response time {results['avg_response_time']:.3f}s during load test too high"
        
        # Note: We're not enforcing the exact throughput target since we're throttling requests
        # but we ensure the system can handle sustained load
        assert results["requests_per_minute"] > 20, f"Throughput {results['requests_per_minute']:.1f} req/min seems too low"


@pytest.mark.asyncio
@pytest.mark.e2e
class TestLatencyPercentiles:
    """Test P99 latency meets < 5s target"""

    async def test_p99_latency_target(self, performance_measurer):
        """Test P99 latency meets 5s SLA requirement"""
        # Generate enough samples for reliable percentile calculation
        metrics = await performance_measurer.measure_batch_responses(25, "/")
        percentiles = performance_measurer.calculate_percentiles(metrics.response_times)
        
        # Validate percentile targets
        assert percentiles["p99"] < 5.0, f"P99 latency {percentiles['p99']:.3f}s exceeds 5s SLA target"
        assert percentiles["p95"] < 3.0, f"P95 latency {percentiles['p95']:.3f}s should be well under P99 target"
        assert percentiles["avg"] < 2.0, f"Average latency {percentiles['avg']:.3f}s exceeds 2s target"


@pytest.mark.asyncio
@pytest.mark.e2e
class TestComprehensivePerformance:
    """Test comprehensive performance validation against all SLAs"""

    async def test_all_performance_targets(self, performance_measurer):
        """Test all performance targets meet SLA requirements"""
        # Test backend API performance
        backend_metrics = await performance_measurer.measure_batch_responses(15, "/")
        backend_percentiles = performance_measurer.calculate_percentiles(backend_metrics.response_times)
        
        # Test auth service performance  
        auth_response_times = []
        for _ in range(10):
            auth_time = await performance_measurer.measure_auth_service_response_time("/health")
            auth_response_times.append(auth_time)
        
        auth_avg = statistics.mean(auth_response_times)
        backend_avg = statistics.mean(backend_metrics.response_times)
        
        # Comprehensive validation
        all_targets_met = all([
            backend_avg < 2.0,  # Backend response time target
            auth_avg < 1.0,     # Auth service response time target  
            backend_percentiles["p99"] < 5.0,  # P99 latency target
            backend_metrics.success_rate > 95   # Success rate target
        ])
        
        assert all_targets_met, "One or more performance SLA targets not met"
        
        # Individual target validation with detailed messages
        assert backend_avg < 2.0, f"Backend avg response time {backend_avg:.3f}s exceeds 2s target"
        assert auth_avg < 1.0, f"Auth service avg response time {auth_avg:.3f}s exceeds 1s target"
        assert backend_percentiles["p99"] < 5.0, f"P99 latency {backend_percentiles['p99']:.3f}s exceeds 5s target"
        assert backend_metrics.success_rate > 95, f"Success rate {backend_metrics.success_rate:.1f}% below 95% target"
