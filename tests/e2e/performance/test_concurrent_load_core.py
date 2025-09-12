"""
Core Concurrent User Load Tests
Tests basic concurrent user load scenarios.
Maximum 300 lines, functions  <= 8 lines.
"""

# Add project root to path
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from test_framework import setup_test_path


setup_test_path()

import asyncio

import pytest

from test_framework.environment_markers import env, env_requires, staging_only
# Add project root to path
from netra_backend.tests.e2e.concurrent_load_helpers import ConcurrentUserLoadTest


# Add project root to path
@env("staging")
@env_requires(
    services=["backend", "websocket", "postgres", "redis", "load_balancer"],
    features=["concurrent_user_support", "performance_metrics", "scaling"],
    data=["concurrent_test_users", "performance_baselines"]
)
@pytest.mark.e2e
class TestConcurrentLoadCore:
    """Core concurrent user load tests"""
    
    @pytest.mark.e2e
    async def test_50_concurrent_users(self):
        """Test system with 50 concurrent demo users"""
        tester = ConcurrentUserLoadTest()
        results = await tester.run_concurrent_users(50)
        
        assert results['success_rate'] > 90, f"Success rate too low: {results['success_rate']}%"
        assert results['avg_response_time'] < 2.0, f"Average response time too high: {results['avg_response_time']}s"
        assert results['p95_response_time'] < 5.0, f"P95 response time too high: {results['p95_response_time']}s"
    
    @pytest.mark.e2e
    async def test_response_time_under_load(self):
        """Verify response time stays under 2s with concurrent users"""
        tester = ConcurrentUserLoadTest()
        
        for num_users in [10, 20, 30, 40, 50]:
            tester.response_times = []
            results = await tester.run_concurrent_users(num_users)
            
            assert results['avg_response_time'] < 2.0, \
                f"Response time degraded with {num_users} users: {results['avg_response_time']}s"
    
    @pytest.mark.e2e
    async def test_gradual_load_increase(self):
        """Test system behavior with gradually increasing load"""
        tester = ConcurrentUserLoadTest()
        performance_metrics = await self._collect_gradual_load_metrics(tester)
        self.validate_gradual_performance(performance_metrics)
    
    async def _collect_gradual_load_metrics(self, tester):
        """Collect performance metrics for gradual load increase."""
        performance_metrics = []
        for num_users in [5, 10, 20, 30, 40, 50]:
            metrics = await self._run_single_load_test(tester, num_users)
            performance_metrics.append(metrics)
            await asyncio.sleep(2)
        return performance_metrics
    
    async def _run_single_load_test(self, tester, num_users: int):
        """Run single load test and collect metrics."""
        self._reset_tester_state(tester)
        results = await tester.run_concurrent_users(num_users)
        return self._create_performance_metric(num_users, results)
    
    def _reset_tester_state(self, tester):
        """Reset tester state for clean test run."""
        tester.response_times = []
        tester.error_count = 0
        tester.success_count = 0
    
    def _create_performance_metric(self, num_users: int, results: dict):
        """Create performance metric from test results."""
        return {
            'users': num_users,
            'avg_response': results['avg_response_time'],
            'success_rate': results['success_rate']
        }
    
    def validate_gradual_performance(self, metrics):
        """Validate performance doesn't degrade catastrophically."""
        for i in range(1, len(metrics)):
            self._validate_metric_pair(metrics[i-1], metrics[i])
    
    def _validate_metric_pair(self, prev_metric: dict, curr_metric: dict):
        """Validate performance between two consecutive metrics."""
        self._validate_response_time_degradation(prev_metric, curr_metric)
        self._validate_success_rate_threshold(curr_metric)
    
    def _validate_response_time_degradation(self, prev_metric: dict, curr_metric: dict):
        """Validate response time doesn't degrade too much."""
        assert curr_metric['avg_response'] < prev_metric['avg_response'] * 2.5, \
            f"Response time degraded too much: {prev_metric['avg_response']}s -> {curr_metric['avg_response']}s"
    
    def _validate_success_rate_threshold(self, curr_metric: dict):
        """Validate success rate meets minimum threshold."""
        assert curr_metric['success_rate'] > 80, \
            f"Success rate too low with {curr_metric['users']} users: {curr_metric['success_rate']}%"
    
    @pytest.mark.e2e
    async def test_burst_traffic_handling(self):
        """Test handling of sudden traffic bursts"""
        tester = ConcurrentUserLoadTest()
        baseline = await self._establish_baseline_performance(tester)
        burst_results = await self._execute_burst_test(tester)
        recovery_results = await self._execute_recovery_test(tester)
        self._validate_burst_performance(baseline, burst_results, recovery_results)
    
    async def _establish_baseline_performance(self, tester):
        """Establish baseline performance metrics."""
        return await tester.run_concurrent_users(10)
    
    async def _execute_burst_test(self, tester):
        """Execute burst traffic test."""
        tester.response_times = []
        return await tester.run_concurrent_users(50)
    
    async def _execute_recovery_test(self, tester):
        """Execute recovery test after burst."""
        await asyncio.sleep(5)
        tester.response_times = []
        return await tester.run_concurrent_users(10)
    
    def _validate_burst_performance(self, baseline: dict, burst: dict, recovery: dict):
        """Validate burst and recovery performance."""
        baseline_time = baseline['avg_response_time']
        assert burst['success_rate'] > 85, f"Burst handling failed: {burst['success_rate']}% success"
        assert burst['avg_response_time'] < baseline_time * 3, "Response time increased too much during burst"
        assert recovery['avg_response_time'] < baseline_time * 1.5, "System did not recover after burst"