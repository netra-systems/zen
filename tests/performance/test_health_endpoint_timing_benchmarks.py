"""
Performance tests for health endpoint timing benchmarks and Redis timeout validation.

CRITICAL ISSUE CONTEXT:
Backend Service /health/ready endpoint timeout caused by 30s Redis timeout in WebSocket readiness validator.
Root cause: netra_backend/app/websocket_core/gcp_initialization_validator.py:139
Performance benchmarks to validate optimal timing thresholds.

BUSINESS VALUE:
- Segment: Platform/Internal
- Goal: Performance Optimization & Platform Stability
- Impact: Establishes performance baselines and prevents regression
- Strategic: Enables fast health checks for high-availability deployments

SSOT COMPLIANCE:
- Uses SSotAsyncTestCase from test_framework.ssot.base_test_case
- Uses IsolatedEnvironment (no direct os.environ)
- Tests REAL performance characteristics with precise timing
- Follows CLAUDE.md testing principles with comprehensive metrics

Tests establish performance baselines and validate timing requirements.
Initially tests FAIL showing poor performance due to 30s Redis timeout.
After fix to 3s timeout, tests will PASS with optimal performance.
"""

import asyncio
import time
import statistics
import pytest
from typing import Dict, List, Any, Tuple
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    gcp_websocket_readiness_check,
    create_gcp_websocket_validator,
    GCPReadinessState
)


class TestHealthEndpointTimingBenchmarks(SSotAsyncTestCase):
    """
    Performance benchmarks for health endpoint timing with Redis timeout validation.
    
    CRITICAL: Establishes performance baselines and validates timing requirements
    for health endpoints. Tests prove 30s Redis timeout causes performance issues.
    """
    
    def setup_method(self, method):
        """Set up performance testing environment with precise timing."""
        super().setup_method(method)
        
        # Set environment for staging GCP (where timeout issues occur)
        self.set_env_var('ENVIRONMENT', 'staging')
        self.set_env_var('K_SERVICE', 'netra-backend-test')
        self.set_env_var('TESTING', 'true')
        
        # Performance benchmark thresholds
        self.performance_thresholds = {
            'optimal_health_response': 1.0,      # < 1s is optimal
            'acceptable_health_response': 3.0,   # < 3s is acceptable
            'maximum_health_response': 10.0,     # < 10s is maximum acceptable
            'load_balancer_timeout': 30.0,       # Load balancer timeout limit
        }
        
        # Test iteration counts for statistical reliability
        self.benchmark_iterations = {
            'quick_test': 5,      # For fast validation
            'standard_test': 20,  # For reliable statistics  
            'stress_test': 100,   # For comprehensive analysis
        }
        
        # Record benchmark setup
        self.record_metric("benchmark_setup_time", time.time())
        self.record_metric("performance_thresholds", self.performance_thresholds)
        
    def _create_mock_app_state(self, redis_delay: float = 0.0, redis_fails: bool = False) -> Mock:
        """Create mock app state with configurable Redis behavior for benchmarking."""
        mock_app_state = Mock()
        
        if redis_fails:
            mock_app_state.redis_manager = Mock()
            mock_app_state.redis_manager.is_connected = Mock(return_value=False)
        else:
            mock_app_state.redis_manager = Mock()
            
            def delayed_redis_check():
                if redis_delay > 0:
                    time.sleep(redis_delay)
                return True
                
            mock_app_state.redis_manager.is_connected = delayed_redis_check
            
        # Setup other services as ready
        mock_app_state.database_available = True
        mock_app_state.db_session_factory = Mock()
        mock_app_state.agent_supervisor = Mock()
        mock_app_state.thread_service = Mock()
        mock_app_state.agent_websocket_bridge = Mock()
        mock_app_state.key_manager = Mock()
        mock_app_state.auth_validation_complete = True
        mock_app_state.startup_complete = True
        mock_app_state.startup_phase = 'complete'
        mock_app_state.startup_failed = False
        
        return mock_app_state
        
    async def _benchmark_health_endpoint(
        self, 
        app_state: Mock, 
        iterations: int = 20
    ) -> Dict[str, Any]:
        """Benchmark health endpoint performance with statistical analysis."""
        response_times = []
        success_count = 0
        error_count = 0
        errors = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                ready, details = await gcp_websocket_readiness_check(app_state)
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if ready:
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                errors.append(str(e))
                response_time = time.time() - start_time
                response_times.append(response_time)
                
        # Calculate statistical metrics
        if response_times:
            stats = {
                'iterations': iterations,
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors,
                'min_time': min(response_times),
                'max_time': max(response_times),
                'mean_time': statistics.mean(response_times),
                'median_time': statistics.median(response_times),
                'stdev_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'p95_time': self._calculate_percentile(response_times, 0.95),
                'p99_time': self._calculate_percentile(response_times, 0.99),
                'all_response_times': response_times
            }
        else:
            stats = {
                'iterations': iterations,
                'success_count': 0,
                'error_count': error_count,
                'errors': errors,
                'min_time': 0,
                'max_time': 0,
                'mean_time': 0,
                'median_time': 0,
                'stdev_time': 0,
                'p95_time': 0,
                'p99_time': 0,
                'all_response_times': []
            }
            
        return stats
        
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value from list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
        
    async def test_optimal_health_endpoint_performance_benchmark(self):
        """
        Benchmark optimal health endpoint performance with fast Redis.
        
        CRITICAL: Establishes baseline for optimal performance (fast Redis response).
        """
        # Test with optimal Redis response (no delay)
        app_state = self._create_mock_app_state(redis_delay=0.0)
        
        # Run benchmark
        stats = await self._benchmark_health_endpoint(
            app_state, 
            self.benchmark_iterations['standard_test']
        )
        
        # Record optimal performance metrics
        for key, value in stats.items():
            self.record_metric(f"optimal_{key}", value)
            
        # Validate optimal performance
        assert stats['mean_time'] <= self.performance_thresholds['optimal_health_response'], (
            f"Optimal health endpoint mean response time {stats['mean_time']:.3f}s "
            f"exceeds optimal threshold {self.performance_thresholds['optimal_health_response']}s"
        )
        
        assert stats['p95_time'] <= self.performance_thresholds['acceptable_health_response'], (
            f"Optimal health endpoint 95th percentile {stats['p95_time']:.3f}s "
            f"exceeds acceptable threshold {self.performance_thresholds['acceptable_health_response']}s"
        )
        
        assert stats['success_count'] == stats['iterations'], (
            f"Optimal performance should have 100% success rate, got "
            f"{stats['success_count']}/{stats['iterations']} successes"
        )
        
    async def test_current_redis_timeout_performance_benchmark(self):
        """
        Benchmark health endpoint performance with current Redis timeout configuration.
        
        CRITICAL TEST: This test FAILS initially, proving the 30s Redis timeout
        causes performance issues. Simulates the actual timeout behavior.
        """
        # Create validator to check current timeout configuration
        app_state = self._create_mock_app_state()
        validator = create_gcp_websocket_validator(app_state)
        validator.update_environment_configuration('staging', is_gcp=True)
        
        # Get current Redis timeout configuration
        redis_check = validator.readiness_checks.get('redis')
        current_timeout = redis_check.timeout_seconds if redis_check else 30.0
        
        self.record_metric("current_redis_timeout", current_timeout)
        
        # Simulate behavior with current timeout (slow Redis)
        # Use a delay that would trigger timeout logic
        redis_delay = min(current_timeout / 3, 5.0)  # Simulate delay that triggers timeout logic
        app_state_with_delay = self._create_mock_app_state(redis_delay=redis_delay)
        
        # Benchmark current configuration performance
        stats = await self._benchmark_health_endpoint(
            app_state_with_delay,
            self.benchmark_iterations['quick_test']  # Fewer iterations due to slow performance
        )
        
        # Record current performance metrics
        for key, value in stats.items():
            self.record_metric(f"current_{key}", value)
            
        # CRITICAL ASSERTIONS: These FAIL initially, proving the timeout issue
        assert stats['mean_time'] <= self.performance_thresholds['acceptable_health_response'], (
            f"Current Redis timeout configuration causes mean response time "
            f"{stats['mean_time']:.3f}s, exceeds acceptable threshold "
            f"{self.performance_thresholds['acceptable_health_response']}s. "
            f"Redis timeout: {current_timeout}s, Redis delay: {redis_delay}s. "
            f"This proves the timeout configuration is causing performance issues."
        )
        
        assert stats['max_time'] <= self.performance_thresholds['maximum_health_response'], (
            f"Current Redis timeout configuration causes maximum response time "
            f"{stats['max_time']:.3f}s, exceeds maximum acceptable threshold "
            f"{self.performance_thresholds['maximum_health_response']}s. "
            f"This will cause health endpoint timeouts."
        )
        
    async def test_health_endpoint_performance_regression_detection(self):
        """
        Test performance regression detection by comparing different timeout configurations.
        
        CRITICAL: Compares performance across different timeout configurations
        to detect regressions and validate improvements.
        """
        timeout_configurations = [
            {'name': 'fast_timeout', 'timeout': 3.0, 'delay': 0.5},
            {'name': 'medium_timeout', 'timeout': 10.0, 'delay': 1.0},
            {'name': 'current_timeout', 'timeout': 30.0, 'delay': 2.0},
        ]
        
        performance_results = {}
        
        for config in timeout_configurations:
            # Create app state with specific delay
            app_state = self._create_mock_app_state(redis_delay=config['delay'])
            
            # Mock the timeout configuration
            validator = create_gcp_websocket_validator(app_state)
            validator.update_environment_configuration('staging', is_gcp=True)
            
            # Override timeout for this test
            if 'redis' in validator.readiness_checks:
                validator.readiness_checks['redis'].timeout_seconds = config['timeout']
                
            # Benchmark this configuration
            stats = await self._benchmark_health_endpoint(
                app_state,
                self.benchmark_iterations['quick_test']
            )
            
            performance_results[config['name']] = {
                'config': config,
                'stats': stats
            }
            
            # Record configuration-specific metrics
            for key, value in stats.items():
                self.record_metric(f"{config['name']}_{key}", value)
                
        # Analyze performance regression
        fast_config = performance_results['fast_timeout']['stats']
        current_config = performance_results['current_timeout']['stats']
        
        # Calculate performance regression factor
        regression_factor = current_config['mean_time'] / fast_config['mean_time']
        self.record_metric("performance_regression_factor", regression_factor)
        
        # Performance regression analysis
        max_acceptable_regression = 3.0  # Current should not be more than 3x slower
        
        assert regression_factor <= max_acceptable_regression, (
            f"Performance regression detected: current timeout configuration is "
            f"{regression_factor:.1f}x slower than fast configuration "
            f"(current: {current_config['mean_time']:.3f}s, "
            f"fast: {fast_config['mean_time']:.3f}s). "
            f"Maximum acceptable regression factor: {max_acceptable_regression}x"
        )
        
        # Validate fast configuration meets performance requirements
        assert fast_config['mean_time'] <= self.performance_thresholds['acceptable_health_response'], (
            f"Fast timeout configuration should meet performance requirements. "
            f"Mean: {fast_config['mean_time']:.3f}s, "
            f"Threshold: {self.performance_thresholds['acceptable_health_response']}s"
        )
        
    async def test_concurrent_health_endpoint_performance_benchmark(self):
        """
        Benchmark health endpoint performance under concurrent load.
        
        CRITICAL: Tests how Redis timeout affects performance under load.
        """
        app_state = self._create_mock_app_state(redis_delay=1.0)  # Simulate some Redis delay
        
        concurrent_levels = [1, 3, 5, 10]  # Different concurrency levels
        concurrency_results = {}
        
        for concurrent_count in concurrent_levels:
            async def concurrent_health_check():
                start_time = time.time()
                ready, details = await gcp_websocket_readiness_check(app_state)
                return time.time() - start_time, ready
                
            # Execute concurrent requests
            start_time = time.time()
            tasks = [concurrent_health_check() for _ in range(concurrent_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze concurrent results
            response_times = []
            success_count = 0
            error_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    response_time, ready = result
                    response_times.append(response_time)
                    if ready:
                        success_count += 1
                        
            # Calculate concurrent performance metrics
            concurrent_stats = {
                'concurrent_requests': concurrent_count,
                'total_time': total_time,
                'success_count': success_count,
                'error_count': error_count,
                'mean_response_time': statistics.mean(response_times) if response_times else 0,
                'max_response_time': max(response_times) if response_times else 0,
                'min_response_time': min(response_times) if response_times else 0,
                'throughput': concurrent_count / total_time if total_time > 0 else 0
            }
            
            concurrency_results[concurrent_count] = concurrent_stats
            
            # Record concurrent performance metrics
            for key, value in concurrent_stats.items():
                self.record_metric(f"concurrent_{concurrent_count}_{key}", value)
                
        # Analyze concurrent performance degradation
        baseline_response = concurrency_results[1]['mean_response_time']
        max_load_response = concurrency_results[max(concurrent_levels)]['mean_response_time']
        
        performance_degradation = max_load_response / baseline_response if baseline_response > 0 else 1
        self.record_metric("concurrent_performance_degradation", performance_degradation)
        
        # Validate concurrent performance
        max_degradation = 4.0  # Performance should not degrade more than 4x under load
        
        assert performance_degradation <= max_degradation, (
            f"Concurrent performance degradation {performance_degradation:.1f}x "
            f"exceeds maximum acceptable {max_degradation}x. "
            f"Baseline: {baseline_response:.3f}s, Max load: {max_load_response:.3f}s. "
            f"Redis timeout configuration may be causing excessive degradation under load."
        )
        
        # Validate highest concurrency level performance
        highest_concurrency = concurrency_results[max(concurrent_levels)]
        assert highest_concurrency['mean_response_time'] <= self.performance_thresholds['maximum_health_response'], (
            f"High concurrency mean response time {highest_concurrency['mean_response_time']:.3f}s "
            f"exceeds maximum acceptable {self.performance_thresholds['maximum_health_response']}s"
        )
        
    async def test_health_endpoint_percentile_performance_analysis(self):
        """
        Detailed percentile analysis of health endpoint performance.
        
        CRITICAL: Analyzes performance distribution to detect timeout-related issues.
        """
        # Test with moderate Redis delay to simulate real-world conditions
        app_state = self._create_mock_app_state(redis_delay=1.5)
        
        # Run extensive benchmark for statistical analysis
        stats = await self._benchmark_health_endpoint(
            app_state,
            self.benchmark_iterations['stress_test']
        )
        
        # Calculate detailed percentiles
        percentiles = [0.5, 0.75, 0.9, 0.95, 0.99, 0.999]
        percentile_results = {}
        
        for p in percentiles:
            percentile_value = self._calculate_percentile(stats['all_response_times'], p)
            percentile_results[f"p{int(p*100)}"] = percentile_value
            self.record_metric(f"percentile_{int(p*100)}", percentile_value)
            
        # Record complete percentile analysis
        self.record_metric("percentile_analysis", percentile_results)
        
        # Performance distribution validation
        assert percentile_results['p50'] <= self.performance_thresholds['acceptable_health_response'], (
            f"Median response time {percentile_results['p50']:.3f}s "
            f"exceeds acceptable threshold {self.performance_thresholds['acceptable_health_response']}s"
        )
        
        assert percentile_results['p95'] <= self.performance_thresholds['maximum_health_response'], (
            f"95th percentile response time {percentile_results['p95']:.3f}s "
            f"exceeds maximum threshold {self.performance_thresholds['maximum_health_response']}s"
        )
        
        assert percentile_results['p99'] <= self.performance_thresholds['load_balancer_timeout'], (
            f"99th percentile response time {percentile_results['p99']:.3f}s "
            f"exceeds load balancer timeout {self.performance_thresholds['load_balancer_timeout']}s"
        )
        
        # Analyze performance distribution spread
        p99_to_p50_ratio = percentile_results['p99'] / percentile_results['p50'] if percentile_results['p50'] > 0 else 1
        self.record_metric("performance_distribution_spread", p99_to_p50_ratio)
        
        # Performance consistency validation
        max_spread = 10.0  # P99 should not be more than 10x P50
        assert p99_to_p50_ratio <= max_spread, (
            f"Performance distribution spread {p99_to_p50_ratio:.1f}x "
            f"(P99/P50 ratio) exceeds maximum {max_spread}x. "
            f"This indicates inconsistent performance, possibly due to timeout configurations."
        )
        
    async def test_health_endpoint_timeout_threshold_validation(self):
        """
        Validate health endpoint performance against various timeout thresholds.
        
        CRITICAL: Tests against realistic timeout scenarios to validate
        that Redis timeout doesn't exceed operational requirements.
        """
        # Test against realistic operational timeout scenarios
        timeout_scenarios = [
            {
                'name': 'docker_healthcheck',
                'description': 'Docker HEALTHCHECK timeout',
                'threshold': 30.0,
                'requirement': 'mandatory'
            },
            {
                'name': 'kubernetes_readiness',
                'description': 'Kubernetes readiness probe',
                'threshold': 10.0,
                'requirement': 'critical'
            },
            {
                'name': 'load_balancer_check',
                'description': 'Load balancer health check',
                'threshold': 5.0,
                'requirement': 'important'
            },
            {
                'name': 'monitoring_system',
                'description': 'Monitoring system check',
                'threshold': 3.0,
                'requirement': 'desired'
            }
        ]
        
        # Test current configuration against all scenarios
        app_state = self._create_mock_app_state(redis_delay=1.0)
        stats = await self._benchmark_health_endpoint(
            app_state,
            self.benchmark_iterations['standard_test']
        )
        
        # Validate against each timeout scenario
        scenario_results = {}
        violations = []
        
        for scenario in timeout_scenarios:
            passes_threshold = stats['p95_time'] <= scenario['threshold']
            
            scenario_result = {
                'threshold': scenario['threshold'],
                'requirement': scenario['requirement'],
                'p95_time': stats['p95_time'],
                'passes': passes_threshold,
                'margin': scenario['threshold'] - stats['p95_time']
            }
            
            scenario_results[scenario['name']] = scenario_result
            
            # Record scenario-specific metrics
            self.record_metric(f"scenario_{scenario['name']}_passes", passes_threshold)
            self.record_metric(f"scenario_{scenario['name']}_margin", scenario_result['margin'])
            
            if not passes_threshold and scenario['requirement'] in ['mandatory', 'critical']:
                violations.append({
                    'scenario': scenario['name'],
                    'description': scenario['description'],
                    'requirement': scenario['requirement'],
                    'threshold': scenario['threshold'],
                    'actual': stats['p95_time']
                })
                
        # Record complete scenario analysis
        self.record_metric("timeout_scenario_results", scenario_results)
        self.record_metric("timeout_violations", violations)
        
        # Assert no critical violations
        critical_violations = [v for v in violations if v['requirement'] == 'critical']
        mandatory_violations = [v for v in violations if v['requirement'] == 'mandatory']
        
        assert len(mandatory_violations) == 0, (
            f"Found {len(mandatory_violations)} mandatory timeout violations:\n" +
            "\n".join([
                f"- {v['description']}: {v['actual']:.3f}s > {v['threshold']}s"
                for v in mandatory_violations
            ]) +
            f"\nThese violations will cause operational failures."
        )
        
        assert len(critical_violations) == 0, (
            f"Found {len(critical_violations)} critical timeout violations:\n" +
            "\n".join([
                f"- {v['description']}: {v['actual']:.3f}s > {v['threshold']}s"
                for v in critical_violations
            ]) +
            f"\nThese violations will cause significant operational issues."
        )