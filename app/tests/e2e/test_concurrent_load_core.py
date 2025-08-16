"""
Core Concurrent User Load Tests
Tests basic concurrent user load scenarios.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import asyncio
from app.tests.e2e.concurrent_load_helpers import ConcurrentUserLoadTest


@pytest.mark.asyncio
class TestConcurrentLoadCore:
    """Core concurrent user load tests"""
    
    async def test_50_concurrent_users(self):
        """Test system with 50 concurrent demo users"""
        tester = ConcurrentUserLoadTest()
        results = await tester.run_concurrent_users(50)
        
        assert results['success_rate'] > 90, f"Success rate too low: {results['success_rate']}%"
        assert results['avg_response_time'] < 2.0, f"Average response time too high: {results['avg_response_time']}s"
        assert results['p95_response_time'] < 5.0, f"P95 response time too high: {results['p95_response_time']}s"
    
    async def test_response_time_under_load(self):
        """Verify response time stays under 2s with concurrent users"""
        tester = ConcurrentUserLoadTest()
        
        for num_users in [10, 20, 30, 40, 50]:
            tester.response_times = []
            results = await tester.run_concurrent_users(num_users)
            
            assert results['avg_response_time'] < 2.0, \
                f"Response time degraded with {num_users} users: {results['avg_response_time']}s"
    
    async def test_gradual_load_increase(self):
        """Test system behavior with gradually increasing load"""
        tester = ConcurrentUserLoadTest()
        performance_metrics = []
        
        for num_users in [5, 10, 20, 30, 40, 50]:
            tester.response_times = []
            tester.error_count = 0
            tester.success_count = 0
            
            results = await tester.run_concurrent_users(num_users)
            performance_metrics.append({
                'users': num_users,
                'avg_response': results['avg_response_time'],
                'success_rate': results['success_rate']
            })
            
            await asyncio.sleep(2)
        
        self.validate_gradual_performance(performance_metrics)
    
    def validate_gradual_performance(self, metrics):
        """Validate performance doesn't degrade catastrophically."""
        for i in range(1, len(metrics)):
            prev = metrics[i-1]
            curr = metrics[i]
            
            assert curr['avg_response'] < prev['avg_response'] * 2.5, \
                f"Response time degraded too much: {prev['avg_response']}s -> {curr['avg_response']}s"
            
            assert curr['success_rate'] > 80, \
                f"Success rate too low with {curr['users']} users: {curr['success_rate']}%"
    
    async def test_burst_traffic_handling(self):
        """Test handling of sudden traffic bursts"""
        tester = ConcurrentUserLoadTest()
        
        baseline = await tester.run_concurrent_users(10)
        baseline_response_time = baseline['avg_response_time']
        
        tester.response_times = []
        burst = await tester.run_concurrent_users(50)
        
        assert burst['success_rate'] > 85, f"Burst handling failed: {burst['success_rate']}% success"
        assert burst['avg_response_time'] < baseline_response_time * 3, \
            "Response time increased too much during burst"
        
        await asyncio.sleep(5)
        tester.response_times = []
        recovery = await tester.run_concurrent_users(10)
        
        assert recovery['avg_response_time'] < baseline_response_time * 1.5, \
            "System did not recover after burst"