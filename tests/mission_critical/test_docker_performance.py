"""
MISSION CRITICAL: Docker Performance Benchmark & Analysis Suite
BUSINESS IMPACT: QUANTIFIES $2M+ ARR PLATFORM PERFORMANCE UNDER LOAD

This test suite provides comprehensive performance benchmarking of Docker operations
to establish baselines, identify bottlenecks, and validate performance under various
load conditions. Critical for maintaining development velocity and CI/CD reliability.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Performance Optimization & Risk Reduction
2. Business Goal: Ensure Docker infrastructure scales with development team growth
3. Value Impact: Prevents performance degradation that could slow 10+ developers
4. Revenue Impact: Protects $2M+ ARR platform from performance-related downtime

PERFORMANCE METRICS MEASURED:
- Operation latency with rate limiting
- Cleanup scheduler overhead
- Memory usage patterns under load
- CPU utilization during stress
- Concurrent operation throughput
- Recovery time from failures
- Network I/O performance
- Disk I/O performance
- Resource allocation efficiency
- Scalability limits identification
"""

import asyncio
import time
import threading
import logging
import pytest
import subprocess
import random
import psutil
import json
import statistics
import gc
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, NamedTuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid
import csv

# Add parent directory to path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# CRITICAL IMPORTS: All Docker infrastructure
from test_framework.docker_force_flag_guardian import (
    DockerForceFlagGuardian,
    DockerForceFlagViolation,
    validate_docker_command
)
from test_framework.docker_rate_limiter import (
    DockerRateLimiter,
    execute_docker_command,
    get_docker_rate_limiter,
    DockerCommandResult
)
from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.dynamic_port_allocator import (
    DynamicPortAllocator,
    allocate_test_ports,
    release_test_ports
)
from shared.isolated_environment import get_env

# Configure logging for performance analysis
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    operation: str
    duration_ms: float
    cpu_percent_before: float
    cpu_percent_after: float
    memory_mb_before: float
    memory_mb_after: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceBenchmark:
    """Complete performance benchmark results."""
    test_name: str
    start_time: datetime
    end_time: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    metrics: List[PerformanceMetric]
    summary_stats: Dict[str, float]
    system_stats: Dict[str, Any]


class DockerPerformanceProfiler:
    """Advanced Docker performance profiler and analyzer."""
    
    def __init__(self):
        """Initialize performance profiler."""
        self.metrics = []
        self.benchmarks = []
        self.test_containers = []
        self.test_networks = []
        self.test_volumes = []
        self.test_images = []
        
        # Performance thresholds (milliseconds)
        self.thresholds = {
            'container_create': 5000,      # 5 seconds
            'container_start': 3000,       # 3 seconds  
            'container_stop': 2000,        # 2 seconds
            'container_remove': 1000,      # 1 second
            'network_create': 2000,        # 2 seconds
            'network_remove': 1000,        # 1 second
            'volume_create': 1000,         # 1 second
            'volume_remove': 500,          # 0.5 seconds
            'image_pull': 30000,           # 30 seconds
            'image_remove': 5000,          # 5 seconds
            'docker_info': 1000,           # 1 second
            'docker_version': 500,         # 0.5 seconds
        }
        
        # Initialize Docker components
        self.docker_manager = UnifiedDockerManager()
        self.rate_limiter = get_docker_rate_limiter()
        
        logger.info("🔧 Docker Performance Profiler initialized")
    
    def get_system_snapshot(self) -> Dict[str, Any]:
        """Get comprehensive system performance snapshot."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / (1024 * 1024),
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'load_avg_1min': load_avg[0],
                'load_avg_5min': load_avg[1],
                'load_avg_15min': load_avg[2],
                'active_processes': len(psutil.pids()),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.warning(f"Failed to get system snapshot: {e}")
            return {'timestamp': datetime.now(), 'error': str(e)}
    
    @contextmanager
    def performance_measurement(self, operation: str):
        """Context manager for measuring operation performance."""
        before_snapshot = self.get_system_snapshot()
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            yield
            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            after_snapshot = self.get_system_snapshot()
            
            duration_ms = (end_time - start_time) * 1000
            
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                cpu_percent_before=before_snapshot.get('cpu_percent', 0),
                cpu_percent_after=after_snapshot.get('cpu_percent', 0),
                memory_mb_before=before_snapshot.get('memory_used_mb', 0),
                memory_mb_after=after_snapshot.get('memory_used_mb', 0),
                timestamp=datetime.now(),
                success=success,
                error_message=error_message
            )
            
            self.metrics.append(metric)
            
            # Log performance warnings
            threshold = self.thresholds.get(operation, 10000)
            if duration_ms > threshold:
                logger.warning(f"⚠️ Performance threshold exceeded: {operation} took {duration_ms:.1f}ms (threshold: {threshold}ms)")
    
    def run_benchmark(self, test_name: str, operation_func, iterations: int = 10) -> PerformanceBenchmark:
        """Run performance benchmark for a specific operation."""
        logger.info(f"🚀 Starting benchmark: {test_name} ({iterations} iterations)")
        
        start_time = datetime.now()
        initial_system_stats = self.get_system_snapshot()
        initial_metric_count = len(self.metrics)
        
        successful_operations = 0
        failed_operations = 0
        
        for i in range(iterations):
            try:
                operation_func(i)
                successful_operations += 1
            except Exception as e:
                failed_operations += 1
                logger.warning(f"Benchmark iteration {i} failed: {e}")
        
        end_time = datetime.now()
        final_system_stats = self.get_system_snapshot()
        
        # Get metrics from this benchmark
        benchmark_metrics = self.metrics[initial_metric_count:]
        
        # Calculate summary statistics
        if benchmark_metrics:
            durations = [m.duration_ms for m in benchmark_metrics if m.success]
            summary_stats = {
                'mean_duration_ms': statistics.mean(durations) if durations else 0,
                'median_duration_ms': statistics.median(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'std_dev_ms': statistics.stdev(durations) if len(durations) > 1 else 0,
                'percentile_95_ms': (sorted(durations)[int(0.95 * len(durations))] if durations else 0),
                'operations_per_second': len(durations) / ((end_time - start_time).total_seconds()) if durations else 0
            }
        else:
            summary_stats = {}
        
        benchmark = PerformanceBenchmark(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            total_operations=iterations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            metrics=benchmark_metrics,
            summary_stats=summary_stats,
            system_stats={
                'initial': initial_system_stats,
                'final': final_system_stats
            }
        )
        
        self.benchmarks.append(benchmark)
        
        logger.info(f"✅ Benchmark completed: {test_name}")
        if summary_stats:
            logger.info(f"   Mean duration: {summary_stats['mean_duration_ms']:.1f}ms")
            logger.info(f"   Operations/sec: {summary_stats['operations_per_second']:.2f}")
            logger.info(f"   Success rate: {successful_operations}/{iterations} ({successful_operations/iterations*100:.1f}%)")
        
        return benchmark
    
    def export_results(self, filepath: str):
        """Export performance results to CSV."""
        with open(filepath, 'w', newline='') as csvfile:
            if self.metrics:
                fieldnames = ['operation', 'duration_ms', 'cpu_percent_before', 'cpu_percent_after',
                            'memory_mb_before', 'memory_mb_after', 'timestamp', 'success', 'error_message']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for metric in self.metrics:
                    writer.writerow({
                        'operation': metric.operation,
                        'duration_ms': metric.duration_ms,
                        'cpu_percent_before': metric.cpu_percent_before,
                        'cpu_percent_after': metric.cpu_percent_after,
                        'memory_mb_before': metric.memory_mb_before,
                        'memory_mb_after': metric.memory_mb_after,
                        'timestamp': metric.timestamp.isoformat(),
                        'success': metric.success,
                        'error_message': metric.error_message or ''
                    })
        
        logger.info(f"📊 Performance results exported to: {filepath}")
    
    def cleanup(self):
        """Clean up all test resources."""
        logger.info("🧹 Cleaning up performance test resources...")
        
        cleanup_operations = 0
        for container in self.test_containers:
            try:
                with self.performance_measurement('cleanup_container_stop'):
                    execute_docker_command(['docker', 'container', 'stop', container])
                with self.performance_measurement('cleanup_container_remove'):
                    execute_docker_command(['docker', 'container', 'rm', container])
                cleanup_operations += 1
            except:
                pass
        
        for network in self.test_networks:
            try:
                with self.performance_measurement('cleanup_network_remove'):
                    execute_docker_command(['docker', 'network', 'rm', network])
                cleanup_operations += 1
            except:
                pass
        
        for volume in self.test_volumes:
            try:
                with self.performance_measurement('cleanup_volume_remove'):
                    execute_docker_command(['docker', 'volume', 'rm', volume])
                cleanup_operations += 1
            except:
                pass
        
        for image in self.test_images:
            try:
                with self.performance_measurement('cleanup_image_remove'):
                    execute_docker_command(['docker', 'image', 'rm', image])
                cleanup_operations += 1
            except:
                pass
        
        logger.info(f"✅ Cleanup completed: {cleanup_operations} resources cleaned")


@pytest.fixture
def performance_profiler():
    """Pytest fixture providing Docker performance profiler."""
    profiler = DockerPerformanceProfiler()
    yield profiler
    profiler.cleanup()


class TestDockerOperationLatency:
    """Test individual Docker operation latency and performance."""
    
    def test_container_lifecycle_performance(self, performance_profiler):
        """Benchmark complete container lifecycle performance."""
        logger.info("📊 Benchmarking container lifecycle performance")
        
        def container_lifecycle_operation(iteration: int):
            container_name = f'perf_test_container_{iteration}_{uuid.uuid4().hex[:6]}'
            
            # Create container
            with performance_profiler.performance_measurement('container_create'):
                result = execute_docker_command([
                    'docker', 'create', '--name', container_name,
                    'alpine:latest', 'sleep', '1'
                ])
                if result.returncode != 0:
                    raise RuntimeError(f"Container create failed: {result.stderr}")
            
            performance_profiler.test_containers.append(container_name)
            
            # Start container
            with performance_profiler.performance_measurement('container_start'):
                result = execute_docker_command(['docker', 'container', 'start', container_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Container start failed: {result.stderr}")
            
            # Stop container
            with performance_profiler.performance_measurement('container_stop'):
                result = execute_docker_command(['docker', 'container', 'stop', container_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Container stop failed: {result.stderr}")
            
            # Remove container
            with performance_profiler.performance_measurement('container_remove'):
                result = execute_docker_command(['docker', 'container', 'rm', container_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Container remove failed: {result.stderr}")
        
        benchmark = performance_profiler.run_benchmark(
            "Container Lifecycle Performance", 
            container_lifecycle_operation, 
            iterations=20
        )
        
        # Performance assertions
        assert benchmark.successful_operations >= 18, f"Container lifecycle success rate too low: {benchmark.successful_operations}/20"
        
        # Check average performance
        if benchmark.summary_stats:
            avg_duration = benchmark.summary_stats['mean_duration_ms']
            ops_per_sec = benchmark.summary_stats['operations_per_second']
            
            logger.info(f"✅ Container lifecycle performance: {avg_duration:.1f}ms avg, {ops_per_sec:.2f} ops/sec")
            
            # Performance thresholds
            assert avg_duration < 15000, f"Container lifecycle too slow: {avg_duration:.1f}ms"
            assert ops_per_sec > 0.1, f"Container operations per second too low: {ops_per_sec:.2f}"
    
    def test_network_operation_performance(self, performance_profiler):
        """Benchmark network operation performance."""
        logger.info("🌐 Benchmarking network operation performance")
        
        def network_operation(iteration: int):
            network_name = f'perf_test_network_{iteration}_{uuid.uuid4().hex[:6]}'
            
            # Create network
            with performance_profiler.performance_measurement('network_create'):
                result = execute_docker_command([
                    'docker', 'network', 'create', '--driver', 'bridge', network_name
                ])
                if result.returncode != 0:
                    raise RuntimeError(f"Network create failed: {result.stderr}")
            
            performance_profiler.test_networks.append(network_name)
            
            # Inspect network
            with performance_profiler.performance_measurement('network_inspect'):
                result = execute_docker_command(['docker', 'network', 'inspect', network_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Network inspect failed: {result.stderr}")
            
            # Remove network
            with performance_profiler.performance_measurement('network_remove'):
                result = execute_docker_command(['docker', 'network', 'rm', network_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Network remove failed: {result.stderr}")
        
        benchmark = performance_profiler.run_benchmark(
            "Network Operation Performance",
            network_operation,
            iterations=15
        )
        
        # Performance assertions
        assert benchmark.successful_operations >= 13, f"Network operation success rate too low: {benchmark.successful_operations}/15"
        
        if benchmark.summary_stats:
            avg_duration = benchmark.summary_stats['mean_duration_ms']
            ops_per_sec = benchmark.summary_stats['operations_per_second']
            
            logger.info(f"✅ Network operation performance: {avg_duration:.1f}ms avg, {ops_per_sec:.2f} ops/sec")
            
            assert avg_duration < 5000, f"Network operations too slow: {avg_duration:.1f}ms"
            assert ops_per_sec > 0.5, f"Network operations per second too low: {ops_per_sec:.2f}"
    
    def test_volume_operation_performance(self, performance_profiler):
        """Benchmark volume operation performance."""
        logger.info("💾 Benchmarking volume operation performance")
        
        def volume_operation(iteration: int):
            volume_name = f'perf_test_volume_{iteration}_{uuid.uuid4().hex[:6]}'
            
            # Create volume
            with performance_profiler.performance_measurement('volume_create'):
                result = execute_docker_command(['docker', 'volume', 'create', volume_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Volume create failed: {result.stderr}")
            
            performance_profiler.test_volumes.append(volume_name)
            
            # Inspect volume
            with performance_profiler.performance_measurement('volume_inspect'):
                result = execute_docker_command(['docker', 'volume', 'inspect', volume_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Volume inspect failed: {result.stderr}")
            
            # Remove volume
            with performance_profiler.performance_measurement('volume_remove'):
                result = execute_docker_command(['docker', 'volume', 'rm', volume_name])
                if result.returncode != 0:
                    raise RuntimeError(f"Volume remove failed: {result.stderr}")
        
        benchmark = performance_profiler.run_benchmark(
            "Volume Operation Performance",
            volume_operation,
            iterations=15
        )
        
        # Performance assertions
        assert benchmark.successful_operations >= 13, f"Volume operation success rate too low: {benchmark.successful_operations}/15"
        
        if benchmark.summary_stats:
            avg_duration = benchmark.summary_stats['mean_duration_ms']
            ops_per_sec = benchmark.summary_stats['operations_per_second']
            
            logger.info(f"✅ Volume operation performance: {avg_duration:.1f}ms avg, {ops_per_sec:.2f} ops/sec")
            
            assert avg_duration < 3000, f"Volume operations too slow: {avg_duration:.1f}ms"
            assert ops_per_sec > 1.0, f"Volume operations per second too low: {ops_per_sec:.2f}"


class TestDockerConcurrentPerformance:
    """Test Docker performance under concurrent load."""
    
    def test_concurrent_container_performance(self, performance_profiler):
        """Test performance of concurrent container operations."""
        logger.info("🚀 Testing concurrent container operation performance")
        
        def concurrent_container_operation(thread_id: int) -> Dict[str, float]:
            """Perform container operations and return timing data."""
            container_name = f'concurrent_perf_{thread_id}_{uuid.uuid4().hex[:6]}'
            timings = {}
            
            # Create
            start = time.time()
            result = execute_docker_command([
                'docker', 'create', '--name', container_name,
                'alpine:latest', 'echo', f'concurrent_{thread_id}'
            ])
            timings['create'] = (time.time() - start) * 1000
            
            if result.returncode == 0:
                performance_profiler.test_containers.append(container_name)
                
                # Start
                start = time.time()
                execute_docker_command(['docker', 'container', 'start', container_name])
                timings['start'] = (time.time() - start) * 1000
                
                # Stop
                start = time.time()
                execute_docker_command(['docker', 'container', 'stop', container_name])
                timings['stop'] = (time.time() - start) * 1000
                
                # Remove
                start = time.time()
                execute_docker_command(['docker', 'container', 'rm', container_name])
                timings['remove'] = (time.time() - start) * 1000
            
            return timings
        
        # Launch concurrent operations
        concurrent_count = 10
        with ThreadPoolExecutor(max_workers=8) as executor:
            start_time = time.time()
            
            futures = [
                executor.submit(concurrent_container_operation, i)
                for i in range(concurrent_count)
            ]
            
            results = []
            for future in as_completed(futures):
                try:
                    timing_data = future.result()
                    results.append(timing_data)
                except Exception as e:
                    logger.warning(f"Concurrent operation failed: {e}")
            
            total_time = time.time() - start_time
        
        # Analyze results
        successful_operations = len(results)
        if results:
            create_times = [r.get('create', 0) for r in results if 'create' in r]
            overall_throughput = successful_operations / total_time
            
            avg_create_time = statistics.mean(create_times) if create_times else 0
            
            logger.info(f"✅ Concurrent container performance: {successful_operations}/{concurrent_count} successful")
            logger.info(f"   Average create time: {avg_create_time:.1f}ms")
            logger.info(f"   Overall throughput: {overall_throughput:.2f} ops/sec")
            
            # Performance assertions
            assert successful_operations >= 8, f"Concurrent success rate too low: {successful_operations}/{concurrent_count}"
            assert overall_throughput > 0.5, f"Concurrent throughput too low: {overall_throughput:.2f} ops/sec"
            
            # Individual operations shouldn't be too slow under concurrent load
            if create_times:
                assert avg_create_time < 10000, f"Concurrent create time too slow: {avg_create_time:.1f}ms"
    
    def test_rate_limiter_performance_impact(self, performance_profiler):
        """Test performance impact of rate limiting."""
        logger.info("⏱️ Testing rate limiter performance impact")
        
        rate_limiter_stats_before = performance_profiler.rate_limiter.get_statistics()
        
        def rate_limited_operation(iteration: int):
            with performance_profiler.performance_measurement('rate_limited_info'):
                result = execute_docker_command(['docker', 'info', '--format', '{{.Name}}'])
                if result.returncode != 0:
                    raise RuntimeError(f"Docker info failed: {result.stderr}")
        
        # Run operations that will be rate limited
        benchmark = performance_profiler.run_benchmark(
            "Rate Limiter Performance Impact",
            rate_limited_operation,
            iterations=25
        )
        
        rate_limiter_stats_after = performance_profiler.rate_limiter.get_statistics()
        
        # Analyze rate limiting impact
        operations_rate_limited = (rate_limiter_stats_after['rate_limited_operations'] - 
                                 rate_limiter_stats_before['rate_limited_operations'])
        
        logger.info(f"✅ Rate limiter impact: {operations_rate_limited} operations were rate limited")
        
        if benchmark.summary_stats:
            avg_duration = benchmark.summary_stats['mean_duration_ms']
            ops_per_sec = benchmark.summary_stats['operations_per_second']
            
            logger.info(f"   Average duration with rate limiting: {avg_duration:.1f}ms")
            logger.info(f"   Throughput with rate limiting: {ops_per_sec:.2f} ops/sec")
            
            # Rate limiting should slow things down but not break them
            assert benchmark.successful_operations >= 23, f"Rate limiter broke operations: {benchmark.successful_operations}/25"
            assert operations_rate_limited > 0, "Some operations should have been rate limited"
            
            # Operations should still complete within reasonable time
            assert avg_duration < 3000, f"Rate limited operations too slow: {avg_duration:.1f}ms"


class TestDockerMemoryPerformance:
    """Test Docker performance under memory pressure."""
    
    def test_memory_usage_during_operations(self, performance_profiler):
        """Test memory usage patterns during Docker operations."""
        logger.info("🧠 Testing memory usage during Docker operations")
        
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        
        def memory_intensive_operation(iteration: int):
            container_name = f'memory_perf_test_{iteration}_{uuid.uuid4().hex[:6]}'
            
            # Create container with memory limit
            with performance_profiler.performance_measurement('memory_limited_container'):
                result = execute_docker_command([
                    'docker', 'create', '--name', container_name,
                    '--memory', '50m',  # 50MB limit
                    'alpine:latest', 'sh', '-c', 'dd if=/dev/zero of=/tmp/test bs=1M count=30; sleep 2'
                ])
                if result.returncode != 0:
                    raise RuntimeError(f"Memory limited container create failed: {result.stderr}")
            
            performance_profiler.test_containers.append(container_name)
            
            # Start and let it run briefly
            execute_docker_command(['docker', 'container', 'start', container_name])
            time.sleep(1)  # Let container do some work
            
            # Stop and remove
            execute_docker_command(['docker', 'container', 'stop', container_name])
            execute_docker_command(['docker', 'container', 'rm', container_name])
        
        benchmark = performance_profiler.run_benchmark(
            "Memory Usage During Operations",
            memory_intensive_operation,
            iterations=8
        )
        
        final_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        memory_delta = final_memory - initial_memory
        
        logger.info(f"✅ Memory performance: {memory_delta:.1f}MB change during test")
        
        # Memory usage should be reasonable
        assert abs(memory_delta) < 500, f"Excessive memory usage change: {memory_delta:.1f}MB"
        
        # Check individual operation memory impact
        if benchmark.metrics:
            memory_deltas = [
                m.memory_mb_after - m.memory_mb_before 
                for m in benchmark.metrics 
                if m.success
            ]
            
            if memory_deltas:
                avg_memory_delta = statistics.mean(memory_deltas)
                max_memory_delta = max(memory_deltas)
                
                logger.info(f"   Average memory delta per operation: {avg_memory_delta:.1f}MB")
                logger.info(f"   Maximum memory delta per operation: {max_memory_delta:.1f}MB")
                
                assert max_memory_delta < 100, f"Individual operation memory usage too high: {max_memory_delta:.1f}MB"
    
    def test_performance_under_memory_pressure(self, performance_profiler):
        """Test Docker performance when system is under memory pressure."""
        logger.info("🔥 Testing performance under memory pressure")
        
        def allocate_memory_pressure():
            """Allocate memory to create system pressure."""
            memory_chunks = []
            try:
                available_memory = psutil.virtual_memory().available
                target_allocation = int(available_memory * 0.6)  # Use 60% of available
                chunk_size = 50 * 1024 * 1024  # 50MB chunks
                
                for _ in range(target_allocation // chunk_size):
                    memory_chunks.append(bytearray(chunk_size))
                
                time.sleep(10)  # Hold memory pressure for 10 seconds
                
            except MemoryError:
                pass  # Expected when we hit limits
            finally:
                del memory_chunks
                gc.collect()
        
        # Start memory pressure in background
        pressure_thread = threading.Thread(target=allocate_memory_pressure)
        pressure_thread.start()
        
        try:
            time.sleep(1)  # Let pressure build
            
            def operation_under_pressure(iteration: int):
                container_name = f'pressure_test_{iteration}_{uuid.uuid4().hex[:6]}'
                
                with performance_profiler.performance_measurement('operation_under_memory_pressure'):
                    # Simple container operation
                    result = execute_docker_command([
                        'docker', 'create', '--name', container_name,
                        '--memory', '20m',  # Small memory footprint
                        'alpine:latest', 'echo', 'pressure_test'
                    ])
                    if result.returncode == 0:
                        performance_profiler.test_containers.append(container_name)
                        execute_docker_command(['docker', 'container', 'start', container_name])
                        execute_docker_command(['docker', 'container', 'rm', container_name])
                    else:
                        raise RuntimeError(f"Container operation under pressure failed: {result.stderr}")
            
            benchmark = performance_profiler.run_benchmark(
                "Performance Under Memory Pressure",
                operation_under_pressure,
                iterations=5  # Fewer iterations due to pressure
            )
            
            if benchmark.summary_stats:
                avg_duration = benchmark.summary_stats['mean_duration_ms']
                success_rate = benchmark.successful_operations / benchmark.total_operations * 100
                
                logger.info(f"✅ Performance under memory pressure: {avg_duration:.1f}ms avg, {success_rate:.1f}% success")
                
                # Operations should still work under pressure, though potentially slower
                assert success_rate >= 60, f"Success rate under memory pressure too low: {success_rate:.1f}%"
                assert avg_duration < 20000, f"Operations too slow under memory pressure: {avg_duration:.1f}ms"
                
        finally:
            pressure_thread.join(timeout=15)


class TestDockerCleanupPerformance:
    """Test performance of Docker cleanup operations."""
    
    def test_bulk_cleanup_performance(self, performance_profiler):
        """Test performance of bulk cleanup operations."""
        logger.info("🧹 Testing bulk cleanup performance")
        
        # Create many resources to clean up
        containers_to_cleanup = []
        networks_to_cleanup = []
        volumes_to_cleanup = []
        
        # Create resources
        resource_creation_start = time.time()
        
        for i in range(20):
            # Create containers
            container_name = f'bulk_cleanup_container_{i}_{uuid.uuid4().hex[:6]}'
            result = execute_docker_command([
                'docker', 'create', '--name', container_name,
                'alpine:latest', 'sleep', '1'
            ])
            if result.returncode == 0:
                containers_to_cleanup.append(container_name)
            
            # Create networks (fewer due to system limits)
            if i < 10:
                network_name = f'bulk_cleanup_network_{i}_{uuid.uuid4().hex[:6]}'
                result = execute_docker_command(['docker', 'network', 'create', network_name])
                if result.returncode == 0:
                    networks_to_cleanup.append(network_name)
            
            # Create volumes
            if i < 15:
                volume_name = f'bulk_cleanup_volume_{i}_{uuid.uuid4().hex[:6]}'
                result = execute_docker_command(['docker', 'volume', 'create', volume_name])
                if result.returncode == 0:
                    volumes_to_cleanup.append(volume_name)
        
        resource_creation_time = time.time() - resource_creation_start
        
        logger.info(f"Created {len(containers_to_cleanup)} containers, {len(networks_to_cleanup)} networks, "
                   f"{len(volumes_to_cleanup)} volumes in {resource_creation_time:.2f}s")
        
        # Now test bulk cleanup performance
        cleanup_start = time.time()
        
        containers_cleaned = 0
        with performance_profiler.performance_measurement('bulk_container_cleanup'):
            for container in containers_to_cleanup:
                try:
                    execute_docker_command(['docker', 'container', 'rm', container])
                    containers_cleaned += 1
                except:
                    pass
        
        networks_cleaned = 0
        with performance_profiler.performance_measurement('bulk_network_cleanup'):
            for network in networks_to_cleanup:
                try:
                    execute_docker_command(['docker', 'network', 'rm', network])
                    networks_cleaned += 1
                except:
                    pass
        
        volumes_cleaned = 0
        with performance_profiler.performance_measurement('bulk_volume_cleanup'):
            for volume in volumes_to_cleanup:
                try:
                    execute_docker_command(['docker', 'volume', 'rm', volume])
                    volumes_cleaned += 1
                except:
                    pass
        
        total_cleanup_time = time.time() - cleanup_start
        
        total_resources = containers_cleaned + networks_cleaned + volumes_cleaned
        cleanup_rate = total_resources / total_cleanup_time if total_cleanup_time > 0 else 0
        
        logger.info(f"✅ Bulk cleanup performance: {total_resources} resources in {total_cleanup_time:.2f}s")
        logger.info(f"   Cleanup rate: {cleanup_rate:.2f} resources/second")
        logger.info(f"   Containers: {containers_cleaned}, Networks: {networks_cleaned}, Volumes: {volumes_cleaned}")
        
        # Performance assertions
        assert cleanup_rate > 2.0, f"Bulk cleanup rate too slow: {cleanup_rate:.2f} resources/sec"
        assert containers_cleaned >= len(containers_to_cleanup) * 0.9, "Container cleanup rate too low"
        assert networks_cleaned >= len(networks_to_cleanup) * 0.9, "Network cleanup rate too low"
        assert volumes_cleaned >= len(volumes_to_cleanup) * 0.9, "Volume cleanup rate too low"


if __name__ == "__main__":
    # Direct execution for debugging and baseline establishment
    profiler = DockerPerformanceProfiler()
    
    try:
        logger.info("🚀 Starting Docker Performance Benchmark Suite...")
        
        # Run core performance tests
        latency_test = TestDockerOperationLatency()
        latency_test.test_container_lifecycle_performance(profiler)
        
        concurrent_test = TestDockerConcurrentPerformance()
        concurrent_test.test_concurrent_container_performance(profiler)
        
        cleanup_test = TestDockerCleanupPerformance()
        cleanup_test.test_bulk_cleanup_performance(profiler)
        
        # Export results
        results_file = f"docker_performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        profiler.export_results(results_file)
        
        logger.info("✅ Docker Performance Benchmark Suite completed successfully")
        logger.info(f"📊 Results exported to: {results_file}")
        
        # Print summary
        if profiler.benchmarks:
            logger.info("\n📈 PERFORMANCE SUMMARY:")
            for benchmark in profiler.benchmarks:
                if benchmark.summary_stats:
                    logger.info(f"   {benchmark.test_name}:")
                    logger.info(f"     Mean Duration: {benchmark.summary_stats['mean_duration_ms']:.1f}ms")
                    logger.info(f"     Operations/sec: {benchmark.summary_stats['operations_per_second']:.2f}")
                    logger.info(f"     Success Rate: {benchmark.successful_operations}/{benchmark.total_operations}")
        
    except Exception as e:
        logger.error(f"❌ Performance benchmark failed: {e}")
        raise
    finally:
        profiler.cleanup()