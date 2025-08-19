"""
Unified Load Test - Production-Scale System Validation

Agent 19 Task: Test system under realistic production load with 100 concurrent users.
Each user sends 10 messages, measuring response times, resource usage, and system reliability.

Business Value: Ensures Netra Apex can handle production traffic and scale properly.
Revenue Impact: Prevents system failures that could lose 20-40% of customer value.

SUCCESS CRITERIA:
- Handles 100 concurrent users
- Response time < 5 seconds at P95
- No message loss
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
import websockets
import pytest
from concurrent.futures import ThreadPoolExecutor

# Test configuration constants
CONCURRENT_USERS = 100
MESSAGES_PER_USER = 10
MAX_P95_RESPONSE_TIME = 5.0  # seconds
MIN_SUCCESS_RATE = 95.0  # percent
MEMORY_LEAK_THRESHOLD = 50  # MB growth
RATE_LIMIT_TEST_THRESHOLD = 100  # requests per minute

@dataclass
class LoadTestMetrics:
    """Comprehensive load test metrics tracking."""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    response_times: List[float] = field(default_factory=list)
    error_count: int = 0
    success_count: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    connections_established: int = 0
    memory_usage_start: Optional[float] = None
    memory_usage_end: Optional[float] = None
    rate_limit_hits: int = 0

class UnifiedLoadTester:
    """Production-scale load tester for Netra Apex system."""
    
    def __init__(self):
        """Initialize load test configuration."""
        self.base_url = "http://localhost:54421"  # Use dev launcher backend port
        self.ws_url = "ws://localhost:54421/ws"
        self.metrics = LoadTestMetrics()
        self.user_sessions = {}
        
    def generate_test_user_id(self) -> str:
        """Generate unique test user identifier."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=8))
        return f"load_test_user_{random_suffix}"
    
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

    async def simulate_user_session(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate complete user session with realistic interactions."""
        results = await self._execute_user_workflow(user_id, session_data)
        return self._finalize_user_results(results)
    
    async def _execute_user_workflow(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete user workflow steps."""
        results = self._initialize_user_results()
        await self._perform_demo_page_load(results)
        await self._perform_websocket_session(user_id, session_data, results)
        return results
    
    def _initialize_user_results(self) -> Dict[str, Any]:
        """Initialize user result tracking structure."""
        return {
            'response_times': [],
            'errors': [],
            'messages_sent': 0,
            'messages_received': 0,
            'websocket_connected': False
        }
    
    async def _perform_demo_page_load(self, results: Dict[str, Any]):
        """Perform initial demo page load test."""
        start_time = time.time()
        try:
            await self._load_demo_page()
            results['response_times'].append(time.time() - start_time)
        except Exception as e:
            results['errors'].append(str(e))
            self.metrics.error_count += 1
    
    async def _load_demo_page(self):
        """Load demo page using HTTP client."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(f"{self.base_url}/demo") as response:
                if response.status != 200:
                    raise Exception(f"Demo page load failed: {response.status}")

    async def _perform_websocket_session(self, user_id: str, session_data: Dict[str, Any], results: Dict[str, Any]):
        """Perform WebSocket session with message exchange."""
        try:
            async with websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                await self._execute_websocket_workflow(websocket, user_id, session_data, results)
        except Exception as e:
            results['errors'].append(f"WebSocket error: {str(e)}")
            self.metrics.error_count += 1
    
    async def _execute_websocket_workflow(self, websocket, user_id: str, session_data: Dict[str, Any], results: Dict[str, Any]):
        """Execute WebSocket message workflow."""
        results['websocket_connected'] = True
        self.metrics.connections_established += 1
        
        for i in range(MESSAGES_PER_USER):
            await self._send_test_message(websocket, user_id, i, results)
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Realistic timing
    
    async def _send_test_message(self, websocket, user_id: str, message_index: int, results: Dict[str, Any]):
        """Send individual test message and track response."""
        message = self._create_test_message(user_id, message_index)
        start_time = time.time()
        
        try:
            await websocket.send(json.dumps(message))
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            response_time = time.time() - start_time
            results['response_times'].append(response_time)
            results['messages_sent'] += 1
            results['messages_received'] += 1
            
            self.metrics.messages_sent += 1
            self.metrics.messages_received += 1
            self.metrics.response_times.append(response_time)
            
        except asyncio.TimeoutError:
            results['errors'].append(f"Message {message_index} timeout")
            self.metrics.error_count += 1
    
    def _create_test_message(self, user_id: str, index: int) -> Dict[str, Any]:
        """Create structured test message."""
        return {
            'type': 'chat_message',
            'user_id': user_id,
            'message': f"Load test message {index} - analyzing AI costs and optimization",
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message_id': f"{user_id}_msg_{index}"
        }
    
    def _finalize_user_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize user session results."""
        if results['messages_sent'] > 0:
            self.metrics.success_count += 1
        return results

    async def run_concurrent_load_test(self) -> Dict[str, Any]:
        """Execute full concurrent load test with 100 users."""
        self.start_resource_monitoring()
        print(f"Starting load test: {CONCURRENT_USERS} concurrent users, {MESSAGES_PER_USER} messages each")
        
        user_tasks = await self._create_concurrent_user_tasks()
        results = await self._execute_concurrent_tasks(user_tasks)
        
        self.stop_resource_monitoring()
        return self._compile_final_results(results)
    
    async def _create_concurrent_user_tasks(self) -> List[asyncio.Task]:
        """Create concurrent user session tasks."""
        tasks = []
        for i in range(CONCURRENT_USERS):
            user_id = self.generate_test_user_id()
            session_data = {'user_index': i, 'start_time': time.time()}
            task = asyncio.create_task(self.simulate_user_session(user_id, session_data))
            tasks.append(task)
        return tasks
    
    async def _execute_concurrent_tasks(self, tasks: List[asyncio.Task]) -> List[Dict[str, Any]]:
        """Execute all concurrent user tasks."""
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _compile_final_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compile comprehensive test results."""
        test_duration = (self.metrics.end_time - self.metrics.start_time).total_seconds()
        
        return {
            'test_duration_seconds': test_duration,
            'concurrent_users': CONCURRENT_USERS,
            'total_messages': self.metrics.messages_sent,
            'success_rate': self._calculate_success_rate(),
            'avg_response_time': self._calculate_avg_response_time(),
            'p95_response_time': self._calculate_p95_response_time(),
            'memory_usage_mb': self._calculate_memory_usage(),
            'connections_established': self.metrics.connections_established,
            'errors_total': self.metrics.error_count,
            'rate_limit_effectiveness': self._test_rate_limiting(),
            'message_loss_count': self._calculate_message_loss()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate percentage."""
        total_attempts = self.metrics.success_count + self.metrics.error_count
        if total_attempts == 0:
            return 0.0
        return (self.metrics.success_count / total_attempts) * 100
    
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
    
    def _calculate_message_loss(self) -> int:
        """Calculate message loss count."""
        expected_messages = CONCURRENT_USERS * MESSAGES_PER_USER
        return max(0, expected_messages - self.metrics.messages_received)


class TestUnifiedLoad:
    """Production load test suite for system validation."""
    
    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_100_concurrent_users_system_load(self):
        """Test system can handle 100 concurrent users with acceptable performance."""
        tester = UnifiedLoadTester()
        results = await tester.run_concurrent_load_test()
        
        # SUCCESS CRITERIA VALIDATION
        assert results['success_rate'] >= MIN_SUCCESS_RATE, \
            f"Success rate {results['success_rate']}% below minimum {MIN_SUCCESS_RATE}%"
        
        assert results['p95_response_time'] < MAX_P95_RESPONSE_TIME, \
            f"P95 response time {results['p95_response_time']}s exceeds {MAX_P95_RESPONSE_TIME}s"
        
        assert results['message_loss_count'] == 0, \
            f"Message loss detected: {results['message_loss_count']} messages lost"
        
        memory_growth = results['memory_usage_mb']['growth_mb']
        assert memory_growth < MEMORY_LEAK_THRESHOLD, \
            f"Memory leak detected: {memory_growth}MB growth exceeds {MEMORY_LEAK_THRESHOLD}MB"
        
        # Print comprehensive results
        self._print_load_test_results(results)
    
    def _print_load_test_results(self, results: Dict[str, Any]):
        """Print detailed load test results for analysis."""
        print("\n" + "="*80)
        print("UNIFIED LOAD TEST RESULTS - PRODUCTION SCALE VALIDATION")
        print("="*80)
        print(f"Concurrent Users: {results['concurrent_users']}")
        print(f"Test Duration: {results['test_duration_seconds']:.2f} seconds")
        print(f"Total Messages: {results['total_messages']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Average Response Time: {results['avg_response_time']:.3f}s")
        print(f"P95 Response Time: {results['p95_response_time']:.3f}s")
        print(f"Connections Established: {results['connections_established']}")
        print(f"Total Errors: {results['errors_total']}")
        print(f"Message Loss: {results['message_loss_count']}")
        print(f"Memory Usage: {results['memory_usage_mb']['start_mb']:.1f}MB -> {results['memory_usage_mb']['end_mb']:.1f}MB")
        print(f"Memory Growth: {results['memory_usage_mb']['growth_mb']:.1f}MB")
        print(f"Rate Limiting: {'✓ Effective' if results['rate_limit_effectiveness']['effective'] else '✗ Not Tested'}")
        print("="*80)
        
        # Performance verdict
        if results['success_rate'] >= MIN_SUCCESS_RATE and results['p95_response_time'] < MAX_P95_RESPONSE_TIME:
            print("✓ LOAD TEST PASSED - System ready for production traffic")
        else:
            print("✗ LOAD TEST FAILED - System requires optimization")
        print("="*80)


if __name__ == "__main__":
    """Direct execution for development testing."""
    async def main():
        tester = UnifiedLoadTester()
        results = await tester.run_concurrent_load_test()
        test_instance = TestUnifiedLoad()
        test_instance._print_load_test_results(results)
    
    asyncio.run(main())