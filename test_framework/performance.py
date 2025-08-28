"""
Performance Testing Framework

Provides tools for performance testing and benchmarking.
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager
import statistics
import gc


# PerformanceMetrics moved to shared.types.performance_metrics for SSOT compliance
from shared.types.performance_metrics import PerformanceMetrics


class PerformanceMonitor:
    """Monitor system performance during test execution."""
    
    def __init__(self, sample_interval: float = 0.1):
        self.sample_interval = sample_interval
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.samples: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.process = psutil.Process()
        
    def start_monitoring(self):
        """Start performance monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.start_time = time.time()
        self.samples.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.end_time = time.time()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": self.process.cpu_percent(),
                    "memory_mb": self.process.memory_info().rss / 1024 / 1024,
                    "num_threads": self.process.num_threads()
                }
                self.samples.append(sample)
            except Exception as e:
                print(f"Monitoring error: {e}")
            
            time.sleep(self.sample_interval)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        if not self.samples:
            return {"error": "No samples collected"}
        
        cpu_values = [s["cpu_percent"] for s in self.samples]
        memory_values = [s["memory_mb"] for s in self.samples]
        
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        return {
            "duration_seconds": duration,
            "sample_count": len(self.samples),
            "cpu_stats": {
                "avg": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_stats": {
                "avg": statistics.mean(memory_values),
                "max": max(memory_values),
                "min": min(memory_values),
                "peak_mb": max(memory_values)
            },
            "thread_count": self.samples[-1]["num_threads"] if self.samples else 0
        }


class ResponseTimeTracker:
    """Track response times for performance analysis."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count = 0
        self.failure_count = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    @contextmanager
    def track_operation(self):
        """Context manager to track operation timing."""
        start_time = time.time()
        success = False
        
        try:
            yield self
            success = True
        except Exception:
            success = False
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.response_times.append(duration)
            
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get response time statistics."""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        sorted_times = sorted(self.response_times)
        
        return {
            "count": len(self.response_times),
            "min": min(self.response_times),
            "max": max(self.response_times),
            "avg": statistics.mean(self.response_times),
            "median": statistics.median(self.response_times),
            "p95": sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 1 else sorted_times[0],
            "p99": sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 1 else sorted_times[0],
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": (self.success_count / len(self.response_times)) * 100 if self.response_times else 0
        }


class LoadGenerator:
    """Generate load for performance testing."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.results: List[Dict[str, Any]] = []
    
    async def run_concurrent_operations(self, operation: Callable, 
                                      count: int,
                                      delay_between: float = 0.0) -> List[Dict[str, Any]]:
        """Run operations concurrently."""
        tasks = []
        
        for i in range(count):
            task = self._run_single_operation(operation, i)
            tasks.append(task)
            
            if delay_between > 0:
                await asyncio.sleep(delay_between)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "operation_id": i,
                    "success": False,
                    "error": str(result),
                    "duration": 0.0
                })
            else:
                processed_results.append(result)
        
        self.results.extend(processed_results)
        return processed_results
    
    async def _run_single_operation(self, operation: Callable, operation_id: int) -> Dict[str, Any]:
        """Run a single operation with resource limits."""
        async with self.semaphore:
            start_time = time.time()
            success = False
            error = None
            
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                success = True
            except Exception as e:
                error = str(e)
                result = None
            
            end_time = time.time()
            
            return {
                "operation_id": operation_id,
                "success": success,
                "error": error,
                "duration": end_time - start_time,
                "result": result
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get load generation summary."""
        if not self.results:
            return {"error": "No results recorded"}
        
        successful_ops = [r for r in self.results if r["success"]]
        failed_ops = [r for r in self.results if not r["success"]]
        durations = [r["duration"] for r in self.results]
        
        return {
            "total_operations": len(self.results),
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "success_rate": (len(successful_ops) / len(self.results)) * 100,
            "avg_duration": statistics.mean(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "throughput_ops_per_second": len(successful_ops) / sum(durations) if sum(durations) > 0 else 0
        }


class PerformanceBenchmark:
    """Main performance benchmark runner."""
    
    def __init__(self, name: str = "Performance Test"):
        self.name = name
        self.monitor = PerformanceMonitor()
        self.response_tracker = ResponseTimeTracker()
        self.load_generator = LoadGenerator()
        
    @asynccontextmanager
    async def run_benchmark(self):
        """Context manager for running benchmarks."""
        print(f"Starting benchmark: {self.name}")
        
        # Start monitoring
        self.monitor.start_monitoring()
        self.response_tracker.start_time = time.time()
        
        # Force garbage collection before test
        gc.collect()
        
        try:
            yield self
        finally:
            # Stop monitoring
            self.response_tracker.end_time = time.time()
            self.monitor.stop_monitoring()
            
            print(f"Completed benchmark: {self.name}")
    
    async def run_load_test(self, operation: Callable, 
                          concurrent_users: int = 10,
                          operations_per_user: int = 10,
                          ramp_up_time: float = 0.0) -> PerformanceMetrics:
        """Run a load test."""
        async with self.run_benchmark():
            total_operations = concurrent_users * operations_per_user
            delay_between = ramp_up_time / concurrent_users if concurrent_users > 1 else 0
            
            results = await self.load_generator.run_concurrent_operations(
                operation, total_operations, delay_between
            )
        
        return self._create_metrics_from_results(results, concurrent_users)
    
    async def run_stress_test(self, operation: Callable,
                            duration_seconds: float = 60.0,
                            concurrent_users: int = 50) -> PerformanceMetrics:
        """Run a stress test for a specific duration."""
        async with self.run_benchmark():
            start_time = time.time()
            results = []
            operation_id = 0
            
            # Set up higher concurrency for stress testing
            self.load_generator.max_concurrent = concurrent_users
            self.load_generator.semaphore = asyncio.Semaphore(concurrent_users)
            
            while (time.time() - start_time) < duration_seconds:
                batch_size = min(10, concurrent_users)  # Process in batches
                batch_results = await self.load_generator.run_concurrent_operations(
                    operation, batch_size, 0.01  # Small delay between batches
                )
                results.extend(batch_results)
                operation_id += batch_size
        
        return self._create_metrics_from_results(results, concurrent_users)
    
    def _create_metrics_from_results(self, results: List[Dict[str, Any]], 
                                   concurrent_users: int) -> PerformanceMetrics:
        """Create performance metrics from operation results."""
        if not results:
            return PerformanceMetrics()
        
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        durations = [r["duration"] for r in results]
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        p95_index = int(len(sorted_durations) * 0.95)
        p99_index = int(len(sorted_durations) * 0.99)
        
        # Get monitoring data
        monitor_summary = self.monitor.get_summary()
        
        # Calculate throughput
        total_duration = self.response_tracker.end_time - self.response_tracker.start_time if \
                        self.response_tracker.end_time and self.response_tracker.start_time else 1
        
        return PerformanceMetrics(
            duration_seconds=total_duration,
            cpu_usage_percent=monitor_summary.get("cpu_stats", {}).get("avg", 0),
            memory_usage_mb=monitor_summary.get("memory_stats", {}).get("avg", 0),
            peak_memory_mb=monitor_summary.get("memory_stats", {}).get("peak_mb", 0),
            throughput_ops_per_second=len(successful_results) / total_duration,
            success_count=len(successful_results),
            failure_count=len(failed_results),
            min_response_time=min(durations) if durations else 0,
            max_response_time=max(durations) if durations else 0,
            avg_response_time=statistics.mean(durations) if durations else 0,
            percentile_95_response_time=sorted_durations[p95_index] if sorted_durations else 0,
            percentile_99_response_time=sorted_durations[p99_index] if sorted_durations else 0,
            total_requests=len(results),
            concurrent_users=concurrent_users,
            error_rate_percent=(len(failed_results) / len(results)) * 100 if results else 0
        )
    
    def create_report(self, metrics: PerformanceMetrics) -> str:
        """Create a performance report."""
        report = f"""
Performance Benchmark Report: {self.name}
{'=' * (30 + len(self.name))}

Test Configuration:
- Concurrent Users: {metrics.concurrent_users}
- Total Requests: {metrics.total_requests}
- Duration: {metrics.duration_seconds:.2f} seconds

Performance Results:
- Throughput: {metrics.throughput_ops_per_second:.2f} ops/sec
- Success Rate: {100 - metrics.error_rate_percent:.2f}%
- Average Response Time: {metrics.avg_response_time * 1000:.2f}ms
- 95th Percentile: {metrics.percentile_95_response_time * 1000:.2f}ms
- 99th Percentile: {metrics.percentile_99_response_time * 1000:.2f}ms
- Min Response Time: {metrics.min_response_time * 1000:.2f}ms
- Max Response Time: {metrics.max_response_time * 1000:.2f}ms

System Resources:
- Average CPU Usage: {metrics.cpu_usage_percent:.1f}%
- Average Memory Usage: {metrics.memory_usage_mb:.1f}MB
- Peak Memory Usage: {metrics.peak_memory_mb:.1f}MB

Results Summary:
- Successful Operations: {metrics.success_count}
- Failed Operations: {metrics.failure_count}
- Error Rate: {metrics.error_rate_percent:.2f}%
"""
        
        return report


# Convenience functions

def create_performance_benchmark(name: str = "Performance Test") -> PerformanceBenchmark:
    """Create a performance benchmark."""
    return PerformanceBenchmark(name)

async def quick_load_test(operation: Callable, users: int = 10, 
                         operations: int = 100) -> PerformanceMetrics:
    """Run a quick load test."""
    benchmark = PerformanceBenchmark("Quick Load Test")
    return await benchmark.run_load_test(operation, users, operations)

async def quick_stress_test(operation: Callable, duration: float = 30.0,
                           users: int = 20) -> PerformanceMetrics:
    """Run a quick stress test."""
    benchmark = PerformanceBenchmark("Quick Stress Test")
    return await benchmark.run_stress_test(operation, duration, users)

@contextmanager
def measure_time():
    """Simple context manager to measure execution time."""
    start = time.time()
    yield lambda: time.time() - start
    
@asynccontextmanager
async def measure_async_time():
    """Async context manager to measure execution time."""
    start = time.time()
    yield lambda: time.time() - start

# Example usage and test helpers

async def example_async_operation():
    """Example async operation for testing."""
    await asyncio.sleep(0.1)  # Simulate work
    return {"status": "success"}

def example_sync_operation():
    """Example sync operation for testing."""
    time.sleep(0.05)  # Simulate work
    return {"status": "success"}

class BatchingTestHelper:
    """Helper class for testing batching operations."""
    
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.batches: List[List[Any]] = []
        self.processed_items = 0
        
    async def process_batch(self, items: List[Any]) -> Dict[str, Any]:
        """Process a batch of items."""
        start_time = time.time()
        
        # Simulate batch processing
        await asyncio.sleep(0.01 * len(items))  # Simulated processing time
        
        self.batches.append(items)
        self.processed_items += len(items)
        
        return {
            "batch_size": len(items),
            "processing_time": time.time() - start_time,
            "total_processed": self.processed_items,
            "batch_count": len(self.batches)
        }
    
    def create_batches(self, items: List[Any]) -> List[List[Any]]:
        """Split items into batches."""
        return [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
    
    async def process_all_batches(self, items: List[Any]) -> List[Dict[str, Any]]:
        """Process all batches sequentially."""
        batches = self.create_batches(items)
        results = []
        
        for batch in batches:
            result = await self.process_batch(batch)
            results.append(result)
        
        return results
    
    async def process_concurrent_batches(self, items: List[Any], max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """Process batches concurrently with limit."""
        batches = self.create_batches(items)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(batch):
            async with semaphore:
                return await self.process_batch(batch)
        
        tasks = [process_with_semaphore(batch) for batch in batches]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "total_batches": len(self.batches),
            "total_items": self.processed_items,
            "avg_batch_size": self.processed_items / len(self.batches) if self.batches else 0,
            "configured_batch_size": self.batch_size
        }


class PerformanceTestCase:
    """Base class for performance test cases."""
    
    def __init__(self, name: str = "Performance Test"):
        self.name = name
        self.benchmark = PerformanceBenchmark(name)
        self.metrics: Optional[PerformanceMetrics] = None
    
    async def run_load_test(self, operation: Callable, 
                          concurrent_users: int = 10,
                          operations_per_user: int = 10,
                          ramp_up_time: float = 0.0) -> PerformanceMetrics:
        """Run a load test."""
        self.metrics = await self.benchmark.run_load_test(
            operation, concurrent_users, operations_per_user, ramp_up_time
        )
        return self.metrics
    
    async def run_stress_test(self, operation: Callable,
                            duration_seconds: float = 60.0,
                            concurrent_users: int = 50) -> PerformanceMetrics:
        """Run a stress test."""
        self.metrics = await self.benchmark.run_stress_test(
            operation, duration_seconds, concurrent_users
        )
        return self.metrics
    
    def create_report(self) -> str:
        """Create a performance report from the last test run."""
        if not self.metrics:
            return "No performance metrics available. Run a test first."
        return self.benchmark.create_report(self.metrics)
    
    def assert_performance_requirements(self, 
                                      max_response_time_ms: Optional[float] = None,
                                      min_throughput_ops_per_sec: Optional[float] = None,
                                      max_error_rate_percent: Optional[float] = None,
                                      max_memory_usage_mb: Optional[float] = None):
        """Assert performance requirements."""
        if not self.metrics:
            raise AssertionError("No performance metrics available. Run a test first.")
        
        if max_response_time_ms is not None:
            actual_ms = self.metrics.avg_response_time * 1000
            assert actual_ms <= max_response_time_ms, \
                f"Average response time {actual_ms:.2f}ms exceeds limit {max_response_time_ms}ms"
        
        if min_throughput_ops_per_sec is not None:
            assert self.metrics.throughput_ops_per_second >= min_throughput_ops_per_sec, \
                f"Throughput {self.metrics.throughput_ops_per_second:.2f} ops/sec below minimum {min_throughput_ops_per_sec}"
        
        if max_error_rate_percent is not None:
            assert self.metrics.error_rate_percent <= max_error_rate_percent, \
                f"Error rate {self.metrics.error_rate_percent:.2f}% exceeds limit {max_error_rate_percent}%"
        
        if max_memory_usage_mb is not None:
            assert self.metrics.peak_memory_mb <= max_memory_usage_mb, \
                f"Peak memory usage {self.metrics.peak_memory_mb:.1f}MB exceeds limit {max_memory_usage_mb}MB"


def create_test_operations() -> Dict[str, Callable]:
    """Create test operations for benchmarking."""
    return {
        "fast_async": lambda: asyncio.sleep(0.01),
        "slow_async": lambda: asyncio.sleep(0.1),
        "fast_sync": lambda: time.sleep(0.01),
        "slow_sync": lambda: time.sleep(0.1),
        "cpu_intensive": lambda: sum(i*i for i in range(1000)),
        "mixed_operation": example_async_operation
    }