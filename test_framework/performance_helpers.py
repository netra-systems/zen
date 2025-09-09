from shared.isolated_environment import get_env
"""
Performance helpers for test infrastructure.

Provides utilities for optimizing test performance and reducing flakiness.
"""

import asyncio
import functools
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Optional, TypeVar, Union, Dict, List, Tuple
from unittest.mock import patch

T = TypeVar('T')


class PerformanceTestHelper:
    """Helper class for optimizing test performance."""
    
    @staticmethod
    def mock_sleep_functions():
        """Mock all sleep functions to make tests faster."""
        return patch.multiple(
            'time',
            sleep=lambda x: None,
        ), patch.multiple(
            'asyncio',
            sleep=lambda x: asyncio.coroutine(lambda: None)(),
        )
    
    @staticmethod
    def fast_retry_config():
        """Return configuration for fast retries in tests."""
        return {
            'stop_after_attempt': 2,
            'wait_fixed': 0.01,  # 10ms instead of longer waits
            'reraise': True
        }
    
    @staticmethod
    def timeout_config(base_timeout: float = 5.0):
        """Return optimized timeout configuration for tests."""
        return {
            'connect_timeout': base_timeout,
            'read_timeout': base_timeout,
            'write_timeout': base_timeout,
            'pool_timeout': base_timeout
        }


def fast_test(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to make tests run faster by mocking sleep functions.
    
    Usage:
        @fast_test
        def test_something():
            time.sleep(1)  # This will be mocked to not actually sleep
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async def mock_async_sleep(*args, **kwargs):
                pass
            
            with patch('time.sleep'), \
                 patch('asyncio.sleep', side_effect=mock_async_sleep):
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with patch('time.sleep'):
                return func(*args, **kwargs)
        return sync_wrapper


def timeout_override(timeout_seconds: float = 1.0):
    """
    Decorator to override default timeouts in tests.
    
    Args:
        timeout_seconds: New timeout value
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Common timeout patterns to mock
            patches = [
                patch('netra_backend.app.core.config.Config.default_timeout', timeout_seconds),
                patch('netra_backend.app.core.config.Config.api_timeout', timeout_seconds),
                patch('netra_backend.app.core.config.Config.database_timeout', timeout_seconds),
            ]
            
            with patch.multiple('netra_backend.app.core.config', 
                               default_timeout=timeout_seconds,
                               api_timeout=timeout_seconds,
                               database_timeout=timeout_seconds):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def performance_monitor():
    """
    Context manager to monitor test performance and detect slow operations.
    
    Usage:
        with performance_monitor() as monitor:
            # Test code
            pass
        print(f"Test took {monitor.duration:.2f}s")
    """
    class Monitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
    
    monitor = Monitor()
    try:
        monitor.__enter__()
        yield monitor
    finally:
        monitor.__exit__(None, None, None)


@asynccontextmanager
async def async_performance_monitor():
    """
    Async context manager to monitor test performance.
    """
    class AsyncMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None
        
        async def __aenter__(self):
            self.start_time = time.time()
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
    
    monitor = AsyncMonitor()
    try:
        await monitor.__aenter__()
        yield monitor
    finally:
        await monitor.__aexit__(None, None, None)


def mock_external_dependencies():
    """
    Mock external dependencies that can cause test flakiness.
    
    Returns a context manager that mocks common external calls.
    """
    return patch.multiple(
        'netra_backend.app.core.config',
        # Mock network-dependent operations
        spec=True
    )


class FlakynessReducer:
    """Helper to reduce test flakiness."""
    
    @staticmethod
    def stable_wait(condition_func: Callable[[], bool], 
                   timeout: float = 5.0, 
                   interval: float = 0.1) -> bool:
        """
        Wait for a condition to become true, with fast polling.
        
        Args:
            condition_func: Function that returns True when condition is met
            timeout: Maximum time to wait
            interval: How often to check the condition
            
        Returns:
            True if condition was met, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    async def async_stable_wait(condition_func: Callable[[], Union[bool, Any]], 
                               timeout: float = 5.0, 
                               interval: float = 0.1) -> bool:
        """
        Async version of stable_wait.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = condition_func()
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                return True
            await asyncio.sleep(interval)
        return False
    
    @staticmethod
    def retry_on_failure(max_attempts: int = 3, delay: float = 0.1):
        """
        Decorator to retry flaky test operations.
        
        Args:
            max_attempts: Maximum number of attempts
            delay: Delay between attempts
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            time.sleep(delay)
                        continue
                raise last_exception
            return wrapper
        return decorator


def optimize_test_database():
    """
    Context manager to optimize database settings for testing.
    """
    return patch.dict('os.environ', {
        'DB_POOL_SIZE': '2',
        'DB_MAX_OVERFLOW': '1',
        'DB_POOL_TIMEOUT': '1',
        'DB_POOL_RECYCLE': '300'
    })


def fast_llm_responses():
    """
    Mock LLM responses for faster testing.
    """
    mock_response = {
        'content': 'Test response',
        'usage': {'total_tokens': 10},
        'model': 'test-model'
    }
    
    return patch.multiple(
        'netra_backend.app.llm.llm_manager',
        # Mock LLM calls to return immediately
        spec=True
    )


# Performance benchmarking utilities
class TestBenchmark:
    """Utility for benchmarking test performance."""
    
    def __init__(self):
        self.measurements = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """Measure the time taken for an operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.measurements[operation_name] = duration
    
    def get_measurements(self) -> dict:
        """Get all measurements."""
        return self.measurements.copy()
    
    def print_report(self):
        """Print a performance report."""
        print("\n=== Performance Report ===")
        for operation, duration in self.measurements.items():
            print(f"{operation}: {duration:.3f}s")
        print("=" * 25)


# Common test optimization patterns
def fast_agent_test_config():
    """Return configuration optimized for agent testing."""
    return {
        'llm_timeout': 1.0,
        'agent_timeout': 2.0,
        'max_retries': 1,
        'retry_delay': 0.01,
        'health_check_interval': 0.1
    }


def mock_time_consuming_operations():
    """Mock operations that typically take a long time in tests."""
    return patch.multiple(
        'netra_backend.app.core',
        # Add common slow operations here
        spec=True
    )


# Performance Profiling Classes for State Machine Benchmarks
class PerformanceProfiler:
    """
    Comprehensive performance profiler for benchmarking state machine operations.
    
    Provides CPU profiling, memory tracking, and execution timing for performance tests.
    Designed specifically for validating state machine performance SLAs.
    """
    
    def __init__(self):
        self.measurements = {}
        self.start_times = {}
        self.memory_baseline = 0
        
    def start_profiling(self, operation_name: str):
        """Start profiling an operation."""
        self.start_times[operation_name] = time.perf_counter()
        
    def end_profiling(self, operation_name: str) -> float:
        """End profiling and return duration in milliseconds."""
        if operation_name not in self.start_times:
            raise ValueError(f"No profiling started for operation: {operation_name}")
            
        duration = (time.perf_counter() - self.start_times[operation_name]) * 1000
        self.measurements[operation_name] = duration
        del self.start_times[operation_name]
        return duration
        
    def get_measurements(self) -> Dict[str, float]:
        """Get all recorded measurements."""
        return self.measurements.copy()
        
    def clear_measurements(self):
        """Clear all measurements."""
        self.measurements.clear()
        self.start_times.clear()


class MemoryTracker:
    """
    Memory usage tracker for state machine performance tests.
    
    Tracks memory consumption during state machine operations to ensure
    memory efficiency requirements are met.
    """
    
    def __init__(self):
        self.baseline_memory = 0
        self.peak_memory = 0
        self.memory_samples = []
        
    def set_baseline(self):
        """Set baseline memory usage."""
        try:
            import psutil
            process = psutil.Process()
            self.baseline_memory = process.memory_info().rss / (1024 * 1024)  # MB
        except ImportError:
            # Fallback if psutil not available
            self.baseline_memory = 0
            
    def record_memory_sample(self, label: str = None):
        """Record current memory usage."""
        try:
            import psutil
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024 * 1024)  # MB
            self.memory_samples.append({
                'timestamp': time.time(),
                'memory_mb': current_memory,
                'memory_from_baseline': current_memory - self.baseline_memory,
                'label': label or f'sample_{len(self.memory_samples)}'
            })
            
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory
                
        except ImportError:
            # Fallback if psutil not available
            self.memory_samples.append({
                'timestamp': time.time(),
                'memory_mb': 0,
                'memory_from_baseline': 0,
                'label': label or f'sample_{len(self.memory_samples)}'
            })
            
    def get_peak_usage(self) -> float:
        """Get peak memory usage from baseline in MB."""
        return self.peak_memory - self.baseline_memory
        
    def get_current_usage(self) -> float:
        """Get current memory usage from baseline in MB."""
        try:
            import psutil
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024 * 1024)  # MB
            return current_memory - self.baseline_memory
        except ImportError:
            return 0
            
    def get_memory_samples(self) -> List[Dict[str, Any]]:
        """Get all memory samples."""
        return self.memory_samples.copy()


class ConcurrencyBenchmark:
    """
    Concurrency benchmarker for testing state machine performance under load.
    
    Manages concurrent operations and tracks performance metrics during
    multi-threaded state machine usage.
    """
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.operation_results = []
        self.error_count = 0
        self.success_count = 0
        
    def run_concurrent_operations(self, operation_func: Callable, operation_args: List[Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Run multiple operations concurrently and collect performance metrics.
        
        Args:
            operation_func: Function to execute concurrently
            operation_args: List of argument tuples for each operation
            timeout: Maximum time to wait for all operations
            
        Returns:
            Dictionary with performance metrics
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
        
        start_time = time.perf_counter()
        operation_times = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all operations
            futures = [
                executor.submit(self._timed_operation, operation_func, args)
                for args in operation_args
            ]
            
            # Collect results
            try:
                for future in as_completed(futures, timeout=timeout):
                    try:
                        duration, result = future.result()
                        operation_times.append(duration)
                        self.operation_results.append(result)
                        self.success_count += 1
                    except Exception as e:
                        self.error_count += 1
                        self.operation_results.append({'error': str(e)})
                        
            except TimeoutError:
                self.error_count += len([f for f in futures if not f.done()])
                
        total_duration = time.perf_counter() - start_time
        
        # Calculate metrics
        if operation_times:
            import statistics
            metrics = {
                'total_operations': len(operation_args),
                'successful_operations': self.success_count,
                'failed_operations': self.error_count,
                'total_duration_seconds': total_duration,
                'operations_per_second': len(operation_args) / total_duration if total_duration > 0 else 0,
                'mean_operation_time_ms': statistics.mean(operation_times),
                'min_operation_time_ms': min(operation_times),
                'max_operation_time_ms': max(operation_times),
                'operation_times': operation_times
            }
            
            if len(operation_times) >= 2:
                metrics['stdev_operation_time_ms'] = statistics.stdev(operation_times)
                
            if len(operation_times) >= 20:
                metrics['p95_operation_time_ms'] = statistics.quantiles(operation_times, n=20)[18]
                
            if len(operation_times) >= 100:
                metrics['p99_operation_time_ms'] = statistics.quantiles(operation_times, n=100)[98]
                
        else:
            metrics = {
                'total_operations': len(operation_args),
                'successful_operations': 0,
                'failed_operations': self.error_count,
                'total_duration_seconds': total_duration,
                'operations_per_second': 0,
                'mean_operation_time_ms': 0,
                'operation_times': []
            }
            
        return metrics
        
    def _timed_operation(self, operation_func: Callable, args: Any) -> Tuple[float, Any]:
        """Execute operation with timing."""
        start_time = time.perf_counter()
        try:
            if isinstance(args, (list, tuple)):
                result = operation_func(*args)
            else:
                result = operation_func(args)
            duration_ms = (time.perf_counter() - start_time) * 1000
            return duration_ms, result
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return duration_ms, {'error': str(e)}
            
    def reset_metrics(self):
        """Reset all collected metrics."""
        self.operation_results.clear()
        self.error_count = 0
        self.success_count = 0


class StatisticalAnalyzer:
    """
    Statistical analyzer for performance test results.
    
    Provides statistical analysis of performance measurements to validate
    SLA compliance and detect performance regressions.
    """
    
    def __init__(self):
        self.samples = {}
        
    def add_samples(self, test_name: str, samples: List[float]):
        """Add performance samples for a test."""
        if test_name not in self.samples:
            self.samples[test_name] = []
        self.samples[test_name].extend(samples)
        
    def analyze_distribution(self, test_name: str) -> Dict[str, float]:
        """Analyze statistical distribution of samples."""
        if test_name not in self.samples or not self.samples[test_name]:
            return {}
            
        samples = self.samples[test_name]
        import statistics
        
        analysis = {
            'count': len(samples),
            'min': min(samples),
            'max': max(samples),
            'mean': statistics.mean(samples),
            'median': statistics.median(samples)
        }
        
        if len(samples) >= 2:
            analysis['stdev'] = statistics.stdev(samples)
            analysis['variance'] = statistics.variance(samples)
            
        if len(samples) >= 4:
            analysis['q1'] = statistics.quantiles(samples, n=4)[0]
            analysis['q3'] = statistics.quantiles(samples, n=4)[2]
            analysis['iqr'] = analysis['q3'] - analysis['q1']
            
        if len(samples) >= 20:
            quantiles = statistics.quantiles(samples, n=20)
            analysis['p90'] = quantiles[17]
            analysis['p95'] = quantiles[18]
            analysis['p99'] = quantiles[19] if len(samples) >= 100 else analysis['p95']
            
        return analysis
        
    def check_sla_compliance(self, test_name: str, sla_targets: Dict[str, float]) -> Dict[str, Any]:
        """Check if test results meet SLA targets."""
        analysis = self.analyze_distribution(test_name)
        if not analysis:
            return {'compliant': False, 'reason': 'No samples available'}
            
        violations = []
        for metric, target in sla_targets.items():
            if metric in analysis and analysis[metric] > target:
                violations.append({
                    'metric': metric,
                    'target': target,
                    'actual': analysis[metric],
                    'violation_ratio': analysis[metric] / target
                })
                
        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'analysis': analysis
        }
        
    def detect_regression(self, test_name: str, baseline_metrics: Dict[str, float], tolerance: float = 1.5) -> Dict[str, Any]:
        """Detect performance regression compared to baseline."""
        current_analysis = self.analyze_distribution(test_name)
        if not current_analysis:
            return {'regression_detected': False, 'reason': 'No current samples'}
            
        regressions = []
        for metric, baseline_value in baseline_metrics.items():
            if metric in current_analysis:
                current_value = current_analysis[metric]
                ratio = current_value / baseline_value if baseline_value > 0 else float('inf')
                
                if ratio > tolerance:
                    regressions.append({
                        'metric': metric,
                        'baseline': baseline_value,
                        'current': current_value,
                        'regression_ratio': ratio,
                        'tolerance': tolerance
                    })
                    
        return {
            'regression_detected': len(regressions) > 0,
            'regressions': regressions,
            'current_analysis': current_analysis
        }
        
    def get_all_samples(self) -> Dict[str, List[float]]:
        """Get all collected samples."""
        return {name: samples.copy() for name, samples in self.samples.items()}
        
    def clear_samples(self, test_name: str = None):
        """Clear samples for a specific test or all tests."""
        if test_name:
            self.samples.pop(test_name, None)
        else:
            self.samples.clear()
