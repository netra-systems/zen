#!/usr/bin/env python3
"""
Mission Critical Test Suite - SSOT Orchestration Performance Benchmarks
=======================================================================

This test suite benchmarks performance characteristics of the SSOT orchestration
consolidation, measuring import time improvements, caching effectiveness, and
system performance under load.

Critical Performance Areas:
1. Import time measurements and optimization validation
2. Caching effectiveness and hit rate analysis
3. Concurrent access performance benchmarking
4. Memory usage profiling and leak detection
5. Availability check performance under load
6. Configuration validation performance
7. Enum access and serialization performance
8. Thread contention and scalability testing

Business Value: Ensures SSOT orchestration consolidation provides performance
benefits and doesn't introduce performance regressions.

CRITICAL: These are performance tests with specific benchmarks. They will
FAIL if performance degrades below acceptable thresholds.
"""

import gc
import psutil
import pytest
import sys
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, patch

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import SSOT orchestration modules
try:
    from test_framework.ssot.orchestration import (
        OrchestrationConfig,
        get_orchestration_config,
        refresh_global_orchestration_config
    )
    from test_framework.ssot.orchestration_enums import (
        BackgroundTaskStatus,
        E2ETestCategory,
        ExecutionStrategy,
        ProgressOutputMode,
        OrchestrationMode,
        BackgroundTaskConfig,
        BackgroundTaskResult
    )
    SSOT_ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    SSOT_ORCHESTRATION_AVAILABLE = False
    pytest.skip(f"SSOT orchestration modules not available: {e}", allow_module_level=True)


class PerformanceBenchmark:
    """Utility class for performance benchmarking."""
    
    def __init__(self, name: str):
        self.name = name
        self.times = []
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, *args):
        if self.start_time is not None:
            elapsed = time.perf_counter() - self.start_time
            self.times.append(elapsed)
            
    @property
    def average_time(self) -> float:
        return mean(self.times) if self.times else 0.0
        
    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else 0.0
        
    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else 0.0
        
    @property
    def std_dev(self) -> float:
        return stdev(self.times) if len(self.times) > 1 else 0.0


@pytest.mark.mission_critical
class TestImportTimeOptimization:
    """Test import time improvements from SSOT consolidation - SPEED tests."""
    
    def test_orchestration_config_import_performance(self):
        """CRITICAL: Test OrchestrationConfig import time is optimized."""
        import_times = []
        
        # Benchmark import time (simulate fresh imports)
        for _ in range(10):
            # Clear import cache to simulate fresh import
            modules_to_clear = [
                'test_framework.ssot.orchestration',
                'test_framework.ssot.orchestration_enums'
            ]
            for module in modules_to_clear:
                sys.modules.pop(module, None)
            
            start_time = time.perf_counter()
            try:
                from test_framework.ssot.orchestration import OrchestrationConfig
                end_time = time.perf_counter()
                import_times.append(end_time - start_time)
            except ImportError:
                pytest.fail("Import failed during performance test")
        
        average_import_time = mean(import_times)
        max_import_time = max(import_times)
        
        # Import should be fast (< 100ms on average)
        assert average_import_time < 0.1, f"Import too slow: {average_import_time:.4f}s average"
        assert max_import_time < 0.2, f"Import too slow: {max_import_time:.4f}s max"
        
        print(f"Import performance: avg={average_import_time:.4f}s, max={max_import_time:.4f}s")
    
    def test_enum_import_performance(self):
        """CRITICAL: Test enum imports are fast and don't cause delays."""
        enum_modules = [
            'test_framework.ssot.orchestration_enums'
        ]
        
        import_benchmarks = {}
        
        for module in enum_modules:
            times = []
            
            for _ in range(20):
                # Clear module cache
                sys.modules.pop(module, None)
                
                start_time = time.perf_counter()
                try:
                    exec(f"from {module} import BackgroundTaskStatus, ExecutionStrategy, OrchestrationMode")
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                except ImportError:
                    pytest.fail(f"Enum import failed for {module}")
            
            import_benchmarks[module] = {
                'average': mean(times),
                'max': max(times),
                'min': min(times)
            }
        
        # All enum imports should be fast
        for module, benchmark in import_benchmarks.items():
            assert benchmark['average'] < 0.05, f"Enum import too slow for {module}: {benchmark['average']:.4f}s"
            assert benchmark['max'] < 0.1, f"Enum import max too slow for {module}: {benchmark['max']:.4f}s"
            
            print(f"Enum import {module}: avg={benchmark['average']:.4f}s, max={benchmark['max']:.4f}s")
    
    def test_singleton_creation_performance(self):
        """CRITICAL: Test singleton creation is fast and doesn't degrade."""
        # Reset singleton for clean test
        OrchestrationConfig._instance = None
        
        creation_times = []
        
        # Test multiple singleton creations
        for _ in range(50):
            start_time = time.perf_counter()
            config = OrchestrationConfig()
            end_time = time.perf_counter()
            creation_times.append(end_time - start_time)
            
            # Verify it's actually the singleton
            assert config is OrchestrationConfig._instance
        
        # First creation might be slower, but subsequent should be instant
        first_creation = creation_times[0]
        subsequent_creations = creation_times[1:]
        
        average_subsequent = mean(subsequent_creations)
        max_subsequent = max(subsequent_creations)
        
        # First creation should be reasonable (< 50ms)
        assert first_creation < 0.05, f"First singleton creation too slow: {first_creation:.4f}s"
        
        # Subsequent creations should be very fast (< 1ms)
        assert average_subsequent < 0.001, f"Subsequent creations too slow: {average_subsequent:.6f}s"
        assert max_subsequent < 0.005, f"Max subsequent creation too slow: {max_subsequent:.6f}s"
        
        print(f"Singleton creation: first={first_creation:.4f}s, subsequent_avg={average_subsequent:.6f}s")


@pytest.mark.mission_critical
class TestCachingEffectiveness:
    """Test caching effectiveness and hit rates - EFFICIENCY tests."""
    
    def test_availability_caching_hit_rate(self):
        """CRITICAL: Test availability caching provides high hit rate."""
        config = OrchestrationConfig()
        config.refresh_availability(force=True)
        
        # Mock availability check to count calls
        orchestrator_call_count = {'count': 0}
        master_call_count = {'count': 0}
        
        original_orchestrator = config._check_orchestrator_availability
        original_master = config._check_master_orchestration_availability
        
        def count_orchestrator_calls():
            orchestrator_call_count['count'] += 1
            return original_orchestrator()
        
        def count_master_calls():
            master_call_count['count'] += 1
            return original_master()
        
        config._check_orchestrator_availability = count_orchestrator_calls
        config._check_master_orchestration_availability = count_master_calls
        
        try:
            # First access should trigger checks
            _ = config.orchestrator_available
            _ = config.master_orchestration_available
            
            initial_orchestrator_calls = orchestrator_call_count['count']
            initial_master_calls = master_call_count['count']
            
            # Subsequent accesses should use cache
            for _ in range(100):
                _ = config.orchestrator_available
                _ = config.master_orchestration_available
            
            final_orchestrator_calls = orchestrator_call_count['count']
            final_master_calls = master_call_count['count']
            
            # Should have high cache hit rate (no additional calls)
            assert final_orchestrator_calls == initial_orchestrator_calls, "Orchestrator cache not working"
            assert final_master_calls == initial_master_calls, "Master orchestration cache not working"
            
            print(f"Cache hit rate: 100% (initial calls: {initial_orchestrator_calls}, {initial_master_calls})")
            
        finally:
            # Restore original methods
            config._check_orchestrator_availability = original_orchestrator
            config._check_master_orchestration_availability = original_master
    
    def test_import_cache_effectiveness(self):
        """CRITICAL: Test import caching reduces repeated import overhead."""
        config = OrchestrationConfig()
        
        # Simulate successful imports with caching
        mock_imports = {
            'TestOrchestratorAgent': Mock(),
            'TestOrchestrationConfig': Mock(),
            'MasterOrchestrationController': Mock()
        }
        
        # Add to import cache
        config._import_cache.update(mock_imports)
        
        # Test cache retrieval performance
        cache_access_times = []
        
        for _ in range(1000):
            start_time = time.perf_counter()
            for key in mock_imports.keys():
                _ = config.get_cached_import(key)
            end_time = time.perf_counter()
            cache_access_times.append(end_time - start_time)
        
        average_cache_time = mean(cache_access_times)
        max_cache_time = max(cache_access_times)
        
        # Cache access should be very fast
        assert average_cache_time < 0.0001, f"Cache access too slow: {average_cache_time:.6f}s"
        assert max_cache_time < 0.001, f"Max cache access too slow: {max_cache_time:.6f}s"
        
        print(f"Import cache performance: avg={average_cache_time:.6f}s, max={max_cache_time:.6f}s")
    
    def test_configuration_status_caching(self):
        """CRITICAL: Test configuration status generation is efficient."""
        config = OrchestrationConfig()
        
        # Benchmark status generation
        status_times = []
        
        for _ in range(100):
            start_time = time.perf_counter()
            status = config.get_availability_status()
            end_time = time.perf_counter()
            status_times.append(end_time - start_time)
            
            # Verify status is complete
            assert isinstance(status, dict)
            assert len(status) > 5  # Should have multiple fields
        
        average_status_time = mean(status_times)
        max_status_time = max(status_times)
        
        # Status generation should be fast
        assert average_status_time < 0.01, f"Status generation too slow: {average_status_time:.4f}s"
        assert max_status_time < 0.05, f"Max status generation too slow: {max_status_time:.4f}s"
        
        print(f"Status generation: avg={average_status_time:.4f}s, max={max_status_time:.4f}s")


@pytest.mark.mission_critical
class TestConcurrentAccessPerformance:
    """Test performance under concurrent access - SCALABILITY tests."""
    
    def test_concurrent_availability_check_performance(self):
        """CRITICAL: Test availability checks perform well under concurrent load."""
        config = OrchestrationConfig()
        
        def availability_benchmark():
            times = []
            for _ in range(50):
                start = time.perf_counter()
                result = config.orchestrator_available
                end = time.perf_counter()
                times.append(end - start)
            return times
        
        # Run concurrent availability checks
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(availability_benchmark) for _ in range(20)]
            all_times = []
            for future in as_completed(futures):
                times = future.result()
                all_times.extend(times)
        
        # Analyze performance under concurrency
        average_time = mean(all_times)
        max_time = max(all_times)
        percentile_95 = sorted(all_times)[int(len(all_times) * 0.95)]
        
        # Performance should remain good under concurrency
        assert average_time < 0.001, f"Concurrent availability check too slow: {average_time:.6f}s"
        assert percentile_95 < 0.005, f"95th percentile too slow: {percentile_95:.6f}s"
        assert max_time < 0.01, f"Max concurrent time too slow: {max_time:.6f}s"
        
        print(f"Concurrent performance: avg={average_time:.6f}s, 95th={percentile_95:.6f}s, max={max_time:.6f}s")
    
    def test_concurrent_config_creation_performance(self):
        """CRITICAL: Test singleton creation performs well under contention."""
        # Reset singleton
        OrchestrationConfig._instance = None
        
        creation_times = []
        errors = []
        
        def timed_config_creation():
            try:
                start = time.perf_counter()
                config = OrchestrationConfig()
                end = time.perf_counter()
                creation_times.append(end - start)
                return config
            except Exception as e:
                errors.append(e)
                return None
        
        # Concurrent singleton creation
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(timed_config_creation) for _ in range(100)]
            configs = [future.result() for future in as_completed(futures)]
        
        # Verify no errors
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
        
        # All configs should be the same instance
        valid_configs = [c for c in configs if c is not None]
        assert len(valid_configs) > 0
        first_config = valid_configs[0]
        for config in valid_configs:
            assert config is first_config, "Concurrent creation produced different instances"
        
        # Performance analysis
        average_creation_time = mean(creation_times)
        max_creation_time = max(creation_times)
        
        # Should handle concurrent creation efficiently
        assert average_creation_time < 0.01, f"Concurrent creation too slow: {average_creation_time:.4f}s"
        assert max_creation_time < 0.05, f"Max concurrent creation too slow: {max_creation_time:.4f}s"
        
        print(f"Concurrent creation: avg={average_creation_time:.4f}s, max={max_creation_time:.4f}s")
    
    def test_thread_contention_scalability(self):
        """CRITICAL: Test system scales well with increasing thread contention."""
        config = OrchestrationConfig()
        
        thread_counts = [1, 5, 10, 20, 40]
        scalability_results = {}
        
        for thread_count in thread_counts:
            per_thread_times = []
            
            def thread_workload():
                times = []
                for _ in range(20):
                    start = time.perf_counter()
                    _ = config.orchestrator_available
                    _ = config.get_availability_status()
                    _ = config.get_available_features()
                    end = time.perf_counter()
                    times.append(end - start)
                return times
            
            # Run with specific thread count
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(thread_workload) for _ in range(thread_count)]
                all_times = []
                for future in as_completed(futures):
                    times = future.result()
                    all_times.extend(times)
            
            scalability_results[thread_count] = mean(all_times)
        
        # Analyze scalability - should not degrade significantly
        baseline_time = scalability_results[1]
        
        for thread_count, avg_time in scalability_results.items():
            if thread_count > 1:
                degradation_ratio = avg_time / baseline_time
                assert degradation_ratio < 3.0, f"Performance degraded too much with {thread_count} threads: {degradation_ratio:.2f}x"
        
        print(f"Scalability results: {scalability_results}")


@pytest.mark.mission_critical
class TestMemoryUsageAndLeaks:
    """Test memory usage and leak prevention - EFFICIENCY tests."""
    
    def test_memory_usage_under_load(self):
        """CRITICAL: Test memory usage remains reasonable under load."""
        # Enable memory tracing
        tracemalloc.start()
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        config = OrchestrationConfig()
        
        # Generate load
        for iteration in range(200):
            # Various operations that might consume memory
            _ = config.orchestrator_available
            _ = config.get_availability_status()
            _ = config.get_import_errors()
            _ = config.validate_configuration()
            
            # Simulate cache usage
            config._import_cache[f'temp_{iteration}'] = Mock()
            config._import_errors[f'error_{iteration}'] = f'Error {iteration}'
            
            # Periodic cleanup
            if iteration % 50 == 0:
                config.refresh_availability(force=True)
                gc.collect()
        
        # Final cleanup
        gc.collect()
        final_memory = process.memory_info().rss
        
        # Memory growth should be minimal
        memory_growth = final_memory - initial_memory
        memory_growth_mb = memory_growth / (1024 * 1024)
        
        assert memory_growth_mb < 20, f"Excessive memory growth: {memory_growth_mb:.2f}MB"
        
        print(f"Memory usage: growth={memory_growth_mb:.2f}MB")
        
        # Stop tracing
        tracemalloc.stop()
    
    def test_cache_memory_efficiency(self):
        """CRITICAL: Test cache memory usage is efficient."""
        config = OrchestrationConfig()
        
        # Fill cache with known size objects
        cache_items = 1000
        item_size = 1024  # 1KB per item
        
        for i in range(cache_items):
            mock_obj = Mock()
            mock_obj.data = 'x' * item_size  # 1KB of data
            config._import_cache[f'item_{i}'] = mock_obj
        
        # Check memory usage is reasonable
        process = psutil.Process()
        memory_with_cache = process.memory_info().rss
        
        # Clear cache
        config.refresh_availability(force=True)
        gc.collect()
        
        memory_after_clear = process.memory_info().rss
        
        # Calculate cache memory usage
        cache_memory = memory_with_cache - memory_after_clear
        cache_memory_mb = cache_memory / (1024 * 1024)
        
        # Memory usage should be reasonable (allow some overhead)
        expected_memory_mb = (cache_items * item_size) / (1024 * 1024)
        memory_efficiency = cache_memory_mb / expected_memory_mb if expected_memory_mb > 0 else 1
        
        # Should not use more than 5x expected memory (allowing for Python overhead)
        assert memory_efficiency < 5.0, f"Cache memory inefficient: {memory_efficiency:.2f}x overhead"
        
        print(f"Cache memory efficiency: {memory_efficiency:.2f}x, used={cache_memory_mb:.2f}MB")
    
    def test_no_memory_leaks_in_repeated_operations(self):
        """CRITICAL: Test repeated operations don't cause memory leaks."""
        config = OrchestrationConfig()
        
        # Get baseline memory
        process = psutil.Process()
        gc.collect()  # Clean up first
        baseline_memory = process.memory_info().rss
        
        # Repeated operations that might leak memory
        operations = [
            lambda: config.orchestrator_available,
            lambda: config.get_availability_status(),
            lambda: config.validate_configuration(),
            lambda: config.refresh_availability(force=True),
            lambda: OrchestrationConfig(),  # Singleton creation
            lambda: get_orchestration_config()  # Global access
        ]
        
        # Run operations many times
        for _ in range(1000):
            for operation in operations:
                _ = operation()
            
            # Periodic memory check
            if _ % 100 == 0:
                gc.collect()
                current_memory = process.memory_info().rss
                memory_growth = current_memory - baseline_memory
                memory_growth_mb = memory_growth / (1024 * 1024)
                
                # Should not grow significantly
                if memory_growth_mb > 50:  # More than 50MB growth
                    pytest.fail(f"Potential memory leak: {memory_growth_mb:.2f}MB growth after {_} iterations")
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss
        total_growth = final_memory - baseline_memory
        total_growth_mb = total_growth / (1024 * 1024)
        
        # Total growth should be minimal
        assert total_growth_mb < 30, f"Memory leak detected: {total_growth_mb:.2f}MB total growth"
        
        print(f"Memory stability: {total_growth_mb:.2f}MB growth over 1000 operations")


@pytest.mark.mission_critical
class TestEnumPerformance:
    """Test enum access and serialization performance - SPEED tests."""
    
    def test_enum_access_performance(self):
        """CRITICAL: Test enum access is fast and doesn't degrade."""
        enums_to_test = [
            (BackgroundTaskStatus, ['QUEUED', 'RUNNING', 'COMPLETED']),
            (ExecutionStrategy, ['SEQUENTIAL', 'PARALLEL_UNLIMITED']),
            (OrchestrationMode, ['FAST_FEEDBACK', 'NIGHTLY', 'BACKGROUND'])
        ]
        
        access_times = []
        
        for enum_class, enum_names in enums_to_test:
            for _ in range(1000):
                start = time.perf_counter()
                for name in enum_names:
                    _ = getattr(enum_class, name)
                    _ = getattr(enum_class, name).value
                end = time.perf_counter()
                access_times.append(end - start)
        
        average_access_time = mean(access_times)
        max_access_time = max(access_times)
        
        # Enum access should be very fast
        assert average_access_time < 0.0001, f"Enum access too slow: {average_access_time:.6f}s"
        assert max_access_time < 0.001, f"Max enum access too slow: {max_access_time:.6f}s"
        
        print(f"Enum access performance: avg={average_access_time:.6f}s, max={max_access_time:.6f}s")
    
    def test_enum_serialization_performance(self):
        """CRITICAL: Test enum serialization in dataclasses is fast."""
        # Create configs with enums
        configs = []
        for _ in range(100):
            config = BackgroundTaskConfig(
                category=E2ETestCategory.CYPRESS,
                environment="test",
                timeout_minutes=30
            )
            configs.append(config)
        
        # Benchmark serialization
        serialization_times = []
        
        for _ in range(50):
            start = time.perf_counter()
            for config in configs:
                _ = config.to_dict()
            end = time.perf_counter()
            serialization_times.append(end - start)
        
        average_serialization_time = mean(serialization_times)
        max_serialization_time = max(serialization_times)
        
        # Serialization should be fast
        assert average_serialization_time < 0.01, f"Enum serialization too slow: {average_serialization_time:.4f}s"
        assert max_serialization_time < 0.05, f"Max serialization too slow: {max_serialization_time:.4f}s"
        
        print(f"Enum serialization: avg={average_serialization_time:.4f}s, max={max_serialization_time:.4f}s")
    
    def test_enum_comparison_performance(self):
        """CRITICAL: Test enum comparisons are optimized."""
        status1 = BackgroundTaskStatus.RUNNING
        status2 = BackgroundTaskStatus.RUNNING
        status3 = BackgroundTaskStatus.COMPLETED
        
        comparison_times = []
        
        for _ in range(10000):
            start = time.perf_counter()
            # Various comparison operations
            _ = status1 == status2
            _ = status1 != status3
            _ = status1 == BackgroundTaskStatus.RUNNING
            _ = status1.value == "running"
            end = time.perf_counter()
            comparison_times.append(end - start)
        
        average_comparison_time = mean(comparison_times)
        max_comparison_time = max(comparison_times)
        
        # Comparisons should be very fast
        assert average_comparison_time < 0.00001, f"Enum comparison too slow: {average_comparison_time:.8f}s"
        assert max_comparison_time < 0.0001, f"Max comparison too slow: {max_comparison_time:.8f}s"
        
        print(f"Enum comparison: avg={average_comparison_time:.8f}s, max={max_comparison_time:.8f}s")


if __name__ == "__main__":
    # Configure pytest for performance testing
    pytest_args = [
        __file__,
        "-v",
        "-s",  # Show print outputs
        "--tb=short",
        "-m", "mission_critical"
    ]
    
    print("Running SSOT Orchestration Performance Benchmark Tests...")
    print("=" * 80)
    print("⚡ PERFORMANCE MODE: Benchmarking speed, efficiency, scalability")
    print("📊 Measuring import times, caching, concurrency, memory usage")
    print("=" * 80)
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 80)
        print("✅ ALL PERFORMANCE BENCHMARKS PASSED")
        print("🚀 SSOT Orchestration is HIGHLY OPTIMIZED")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ PERFORMANCE BENCHMARKS FAILED")
        print("🐌 Performance issues detected - optimization needed")
        print("=" * 80)
    
    sys.exit(result)