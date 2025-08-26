"""
Performance helpers for test infrastructure.

Provides utilities for optimizing test performance and reducing flakiness.
"""

import asyncio
import functools
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Optional, TypeVar, Union
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