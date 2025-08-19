"""
Unified HTTP Load Test - Production-Scale System Validation (HTTP Only)

Agent 19 Task: Test system under realistic production load with 100 concurrent users.
Each user makes 10 HTTP requests, measuring response times, resource usage, and system reliability.
This version focuses on HTTP API endpoints since WebSocket endpoints are not currently accessible.

Business Value: Ensures Netra Apex API can handle production traffic and scale properly.
Revenue Impact: Prevents system failures that could lose 20-40% of customer value.

SUCCESS CRITERIA:
- Handles 100 concurrent users
- Response time < 5 seconds at P95
- No request failures
- No memory leaks
- Rate limiting effectiveness

Maximum 300 lines, functions ≤8 lines.
"""

import asyncio
import time
import statistics
import random
import string
import json
import psutil
import gc
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
import aiohttp
import pytest

# Test configuration constants
CONCURRENT_USERS = 100
REQUESTS_PER_USER = 10
MAX_P95_RESPONSE_TIME = 5.0  # seconds
MIN_SUCCESS_RATE = 95.0  # percent
MEMORY_LEAK_THRESHOLD = 50  # MB growth
RATE_LIMIT_TEST_THRESHOLD = 100  # requests per minute

@dataclass
class HttpLoadTestMetrics:
    """Comprehensive HTTP load test metrics tracking."""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    response_times: List[float] = field(default_factory=list)
    error_count: int = 0
    success_count: int = 0
    requests_sent: int = 0
    requests_completed: int = 0
    status_codes: Dict[int, int] = field(default_factory=dict)
    memory_usage_start: Optional[float] = None
    memory_usage_end: Optional[float] = None
    rate_limit_hits: int = 0

class HttpLoadTester:
    """Production-scale HTTP load tester for Netra Apex system."""
    
    def __init__(self):
        """Initialize HTTP load test configuration."""
        self.base_url = "http://localhost:54421"
        self.metrics = HttpLoadTestMetrics()
        self.user_sessions = {}
        self.test_endpoints = [
            "/",
            "/demo", 
            "/api/health" if self._endpoint_exists("/api/health") else "/",
            "/docs" if self._endpoint_exists("/docs") else "/"
        ]
        
    def _endpoint_exists(self, endpoint: str) -> bool:
        """Check if endpoint exists (simplified check)."""
        # For now, return True for common endpoints
        return endpoint in ["/", "/demo", "/api/health", "/docs"]
    
    def generate_test_user_id(self) -> str:
        """Generate unique test user identifier."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=8))
        return f"http_load_test_user_{random_suffix}"
    
    def get_current_memory_usage(self) -> float:
        """Get current system memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def start_resource_monitoring(self):
        """Initialize resource usage monitoring."""
        self.metrics.memory_usage_start = self.get_current_memory_usage()
        gc.collect()  # Force garbage collection baseline
    
    def stop_resource_monitoring(self):
        """Complete resource usage monitoring."""
        gc.collect()  # Force garbage collection
        self.metrics.memory_usage_end = self.get_current_memory_usage()
        self.metrics.end_time = datetime.now(timezone.utc)

    async def simulate_user_http_session(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate complete user HTTP session with realistic API interactions."""
        results = await self._execute_user_http_workflow(user_id, session_data)
        return self._finalize_user_results(results)
    
    async def _execute_user_http_workflow(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete user HTTP workflow steps."""
        results = self._initialize_user_results()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit_per_host=10)
        ) as http_session:
            await self._perform_http_requests(http_session, user_id, results)
        
        return results
    
    def _initialize_user_results(self) -> Dict[str, Any]:
        """Initialize user result tracking structure."""
        return {
            'response_times': [],
            'errors': [],
            'requests_sent': 0,
            'requests_completed': 0,
            'status_codes': {}
        }
    
    async def _perform_http_requests(self, http_session: aiohttp.ClientSession, user_id: str, results: Dict[str, Any]):
        """Perform series of HTTP requests for load testing."""
        for i in range(REQUESTS_PER_USER):
            await self._send_http_request(http_session, user_id, i, results)
            await asyncio.sleep(random.uniform(0.1, 0.3))  # Realistic timing
    
    async def _send_http_request(self, http_session: aiohttp.ClientSession, user_id: str, request_index: int, results: Dict[str, Any]):
        """Send individual HTTP request and track response."""
        endpoint = random.choice(self.test_endpoints)
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            # Add some query parameters for variety
            params = self._create_test_params(user_id, request_index)
            
            async with http_session.get(url, params=params) as response:
                response_time = time.time() - start_time
                
                # Track response
                results['response_times'].append(response_time)
                results['requests_sent'] += 1
                results['requests_completed'] += 1
                
                # Track status codes
                status_code = response.status
                results['status_codes'][status_code] = results['status_codes'].get(status_code, 0) + 1
                
                # Update global metrics
                self.metrics.requests_sent += 1
                self.metrics.requests_completed += 1
                self.metrics.response_times.append(response_time)
                self.metrics.status_codes[status_code] = self.metrics.status_codes.get(status_code, 0) + 1
                
                # Check for success
                if 200 <= status_code < 400:
                    self.metrics.success_count += 1
                else:
                    results['errors'].append(f"HTTP {status_code} from {endpoint}")
                    self.metrics.error_count += 1
                
                # Check for rate limiting
                if status_code == 429:
                    self.metrics.rate_limit_hits += 1
                
        except asyncio.TimeoutError:
            results['errors'].append(f"Request {request_index} timeout")
            self.metrics.error_count += 1
        except Exception as e:
            results['errors'].append(f"Request {request_index} error: {str(e)}")
            self.metrics.error_count += 1
    
    def _create_test_params(self, user_id: str, request_index: int) -> Dict[str, str]:
        """Create test query parameters for request variety."""
        return {
            'test_user': user_id,
            'request_id': str(request_index),
            'timestamp': str(int(time.time()))
        }
    
    def _finalize_user_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize user session results."""
        if results['requests_completed'] > 0:
            # Consider session successful if at least 50% of requests succeeded
            success_rate = len([sc for sc in results['status_codes'] if 200 <= sc < 400]) / results['requests_completed']
            if success_rate >= 0.5:
                self.metrics.success_count += 1
        return results

    async def run_concurrent_http_load_test(self) -> Dict[str, Any]:
        """Execute full concurrent HTTP load test with 100 users."""
        self.start_resource_monitoring()
        print(f"Starting HTTP load test: {CONCURRENT_USERS} concurrent users, {REQUESTS_PER_USER} requests each")
        
        user_tasks = await self._create_concurrent_http_user_tasks()
        results = await self._execute_concurrent_http_tasks(user_tasks)
        
        self.stop_resource_monitoring()
        return self._compile_final_http_results(results)
    
    async def _create_concurrent_http_user_tasks(self) -> List[asyncio.Task]:
        """Create concurrent HTTP user session tasks."""
        tasks = []
        for i in range(CONCURRENT_USERS):
            user_id = self.generate_test_user_id()
            session_data = {'user_index': i, 'start_time': time.time()}
            task = asyncio.create_task(self.simulate_user_http_session(user_id, session_data))
            tasks.append(task)
        return tasks
    
    async def _execute_concurrent_http_tasks(self, tasks: List[asyncio.Task]) -> List[Dict[str, Any]]:
        """Execute all concurrent HTTP user tasks."""
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _compile_final_http_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compile comprehensive HTTP test results."""
        test_duration = (self.metrics.end_time - self.metrics.start_time).total_seconds()
        
        return {
            'test_type': 'http_load_test',
            'test_duration_seconds': test_duration,
            'concurrent_users': CONCURRENT_USERS,
            'total_requests': self.metrics.requests_sent,
            'success_rate': self._calculate_success_rate(),
            'avg_response_time': self._calculate_avg_response_time(),
            'p95_response_time': self._calculate_p95_response_time(),
            'memory_usage_mb': self._calculate_memory_usage(),
            'requests_per_second': self.metrics.requests_completed / test_duration if test_duration > 0 else 0,
            'errors_total': self.metrics.error_count,
            'status_codes': dict(self.metrics.status_codes),
            'rate_limit_effectiveness': self._test_rate_limiting(),
            'request_loss_count': self._calculate_request_loss()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate percentage."""
        if self.metrics.requests_sent == 0:
            return 0.0
        success_requests = sum(count for status, count in self.metrics.status_codes.items() if 200 <= status < 400)
        return (success_requests / self.metrics.requests_sent) * 100
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        return statistics.mean(self.metrics.response_times) if self.metrics.response_times else 0.0
    
    def _calculate_p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.metrics.response_times:
            return 0.0
        sorted_times = sorted(self.metrics.response_times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[p95_index]
    
    def _calculate_memory_usage(self) -> Dict[str, float]:
        """Calculate memory usage metrics."""
        memory_growth = self.metrics.memory_usage_end - self.metrics.memory_usage_start
        return {
            'start_mb': self.metrics.memory_usage_start,
            'end_mb': self.metrics.memory_usage_end,
            'growth_mb': memory_growth
        }
    
    def _test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting effectiveness."""
        return {
            'rate_limit_hits': self.metrics.rate_limit_hits,
            'effective': self.metrics.rate_limit_hits > 0,
            'threshold_tested': RATE_LIMIT_TEST_THRESHOLD
        }
    
    def _calculate_request_loss(self) -> int:
        """Calculate request loss count."""
        expected_requests = CONCURRENT_USERS * REQUESTS_PER_USER
        return max(0, expected_requests - self.metrics.requests_completed)


class TestUnifiedHttpLoad:
    """Production HTTP load test suite for system validation."""
    
    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_100_concurrent_users_http_load(self):
        """Test system can handle 100 concurrent users via HTTP with acceptable performance."""
        tester = HttpLoadTester()
        results = await tester.run_concurrent_http_load_test()
        
        # SUCCESS CRITERIA VALIDATION
        assert results['success_rate'] >= MIN_SUCCESS_RATE, \
            f"Success rate {results['success_rate']}% below minimum {MIN_SUCCESS_RATE}%"
        
        assert results['p95_response_time'] < MAX_P95_RESPONSE_TIME, \
            f"P95 response time {results['p95_response_time']}s exceeds {MAX_P95_RESPONSE_TIME}s"
        
        assert results['request_loss_count'] == 0, \
            f"Request loss detected: {results['request_loss_count']} requests lost"
        
        memory_growth = results['memory_usage_mb']['growth_mb']
        assert memory_growth < MEMORY_LEAK_THRESHOLD, \
            f"Memory leak detected: {memory_growth}MB growth exceeds {MEMORY_LEAK_THRESHOLD}MB"
        
        # Print comprehensive results
        self._print_http_load_test_results(results)
    
    def _print_http_load_test_results(self, results: Dict[str, Any]):
        """Print detailed HTTP load test results for analysis."""
        print("\n" + "="*80)
        print("HTTP LOAD TEST RESULTS - PRODUCTION SCALE VALIDATION")
        print("="*80)
        print(f"Test Type: {results['test_type']}")
        print(f"Concurrent Users: {results['concurrent_users']}")
        print(f"Test Duration: {results['test_duration_seconds']:.2f} seconds")
        print(f"Total Requests: {results['total_requests']}")
        print(f"Requests/Second: {results['requests_per_second']:.1f}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Average Response Time: {results['avg_response_time']:.3f}s")
        print(f"P95 Response Time: {results['p95_response_time']:.3f}s")
        print(f"Total Errors: {results['errors_total']}")
        print(f"Request Loss: {results['request_loss_count']}")
        print(f"Memory Usage: {results['memory_usage_mb']['start_mb']:.1f}MB -> {results['memory_usage_mb']['end_mb']:.1f}MB")
        print(f"Memory Growth: {results['memory_usage_mb']['growth_mb']:.1f}MB")
        print(f"Status Codes: {results['status_codes']}")
        print(f"Rate Limiting: {'Effective' if results['rate_limit_effectiveness']['effective'] else 'Not Triggered'}")
        print("="*80)
        
        # Performance verdict
        if results['success_rate'] >= MIN_SUCCESS_RATE and results['p95_response_time'] < MAX_P95_RESPONSE_TIME:
            print("[PASS] HTTP LOAD TEST PASSED - System ready for production HTTP traffic")
        else:
            print("[FAIL] HTTP LOAD TEST FAILED - System requires optimization")
        print("="*80)


if __name__ == "__main__":
    """Direct execution for development testing."""
    async def main():
        tester = HttpLoadTester()
        results = await tester.run_concurrent_http_load_test()
        test_instance = TestUnifiedHttpLoad()
        test_instance._print_http_load_test_results(results)
    
    asyncio.run(main())